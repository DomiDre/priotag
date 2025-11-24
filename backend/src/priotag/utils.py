import asyncio
import base64
import json
import logging
from datetime import UTC, datetime

import httpx
import redis
from fastapi import Cookie, Depends, HTTPException, Request, Response

from priotag.middleware.metrics import track_session_lookup
from priotag.models.auth import SessionInfo
from priotag.models.cookie import (
    COOKIE_AUTH_TOKEN,
    COOKIE_DEK,
    COOKIE_PATH,
    COOKIE_SECURE,
)
from priotag.models.pocketbase_schemas import UsersResponse
from priotag.services.pocketbase_service import POCKETBASE_URL
from priotag.services.redis_service import get_redis

# Cookie names
# Update lastSeen at most once per hour to avoid excessive database writes
LAST_SEEN_UPDATE_INTERVAL = 3600  # 1 hour in seconds


async def get_current_token(
    auth_token: str | None = Cookie(None, alias=COOKIE_AUTH_TOKEN),
) -> str:
    """Extract auth token from httpOnly cookie."""
    if not auth_token:
        raise HTTPException(
            status_code=401,
            detail="Nicht authentifiziert - keine gültige Sitzung gefunden",
        )
    return auth_token


async def get_current_dek(
    dek: str | None = Cookie(None, alias=COOKIE_DEK),
) -> bytes:
    """Extract DEK from httpOnly cookie."""
    if not dek:
        raise HTTPException(
            status_code=400,
            detail="Verschlüsselungsschlüssel nicht gefunden",
        )
    try:
        return base64.b64decode(dek)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail="Ungültiger Verschlüsselungsschlüssel",
        ) from e


async def verify_token(
    response: Response,
    token: str = Depends(get_current_token),
    redis_client: redis.Redis = Depends(get_redis),
) -> SessionInfo:
    """
    Verify authentication token from cookie.

    First checks Redis cache, then validates with PocketBase if needed.
    If PocketBase returns a new token, updates the cookie.
    """
    logger = logging.getLogger(__name__)

    # Check if token is blacklisted (logged out)
    blacklist_key = f"blacklist:{token}"
    try:
        is_blacklisted = redis_client.exists(blacklist_key)
        if is_blacklisted:
            logger.debug(f"Token is blacklisted: {token[:10]}...")
            raise HTTPException(
                status_code=401,
                detail="Token wurde durch Logout ungültig gemacht",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Failed to check blacklist: {e}")
        # Continue if blacklist check fails (don't block valid users)

    session_key = f"session:{token}"

    try:
        cached_session = redis_client.get(session_key)
        logger.debug(
            f"Redis lookup for {session_key}: {'found' if cached_session else 'not found'}"
        )
    except Exception as e:
        logger.error(f"Redis connection error: {e}")
        track_session_lookup("error")
        # If Redis fails, try PocketBase refresh
        cached_session = None

    if cached_session:
        # Session found in cache - it's valid
        track_session_lookup("cache_hit")
        try:
            session_data = (
                json.loads(cached_session)
                if isinstance(cached_session, str)
                else json.loads(str(cached_session))
            )
            session_info = SessionInfo(**session_data)

            # Update lastSeen in background (non-blocking)
            asyncio.create_task(update_last_seen(session_info.id, token, redis_client))

            return session_info
        except Exception as e:
            track_session_lookup("invalid")
            logger.error(f"Failed to parse cached session: {e}")
            # If parsing fails, fall through to PocketBase refresh

    track_session_lookup("cache_miss")
    # Session not in cache - verify with PocketBase
    logger.debug(
        f"Session not in cache, refreshing with PocketBase for token: {token[:10]}..."
    )

    async with httpx.AsyncClient() as client:
        try:
            pb_response = await client.post(
                f"{POCKETBASE_URL}/api/collections/users/auth-refresh",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0,  # Add timeout
            )

            if pb_response.status_code != 200:
                logger.warning(
                    f"PocketBase auth refresh failed: {pb_response.status_code}"
                )
                raise HTTPException(
                    status_code=401,
                    detail="Ungültiger oder abgelaufener Token",
                )

            auth_data = pb_response.json()
            new_token = auth_data["token"]
            user_data = UsersResponse(**auth_data["record"])

            # Extract session info
            session_info = extract_session_info_from_record(user_data)
            is_admin = session_info.is_admin

            # Determine TTL and cookie max_age
            if is_admin:
                ttl = 900  # 15 minutes
                cookie_max_age = 900
            else:
                # Default to "session" mode when restoring (safer)
                ttl = 8 * 3600  # 8 hours
                cookie_max_age = 8 * 3600

            # If token was refreshed, update cookie and Redis with new token
            if new_token != token:
                logger.info("Token refreshed, updating Redis and cookies")
                # Delete old session
                try:
                    redis_client.delete(session_key)
                except Exception as e:
                    logger.warning(f"Failed to delete old session from Redis: {e}")

                # Store new session with new token
                new_session_key = f"session:{new_token}"
                try:
                    redis_client.setex(
                        new_session_key,
                        ttl,
                        session_info.model_dump_json(),
                    )
                except Exception as e:
                    logger.error(f"Failed to store new session in Redis: {e}")
                    # Continue anyway - PocketBase token is valid

                # Update cookie with new token
                response.set_cookie(
                    key=COOKIE_AUTH_TOKEN,
                    value=new_token,
                    max_age=cookie_max_age,
                    httponly=True,
                    secure=COOKIE_SECURE,
                    samesite="strict",
                    path=COOKIE_PATH,
                )
            else:
                # Same token, just restore to Redis
                logger.debug("Restoring session to Redis cache")
                try:
                    redis_client.setex(
                        session_key,
                        ttl,
                        session_info.model_dump_json(),
                    )
                except Exception as e:
                    logger.error(f"Failed to restore session to Redis: {e}")
                    # Continue anyway - PocketBase token is valid

            # Update lastSeen in background (non-blocking)
            asyncio.create_task(
                update_last_seen(session_info.id, new_token, redis_client)
            )

            return session_info

        except httpx.RequestError as e:
            logger.error(f"PocketBase connection error: {e}")
            raise HTTPException(
                status_code=503,
                detail="Authentifizierungsserver nicht erreichbar",
            ) from e


async def require_admin(
    session: SessionInfo = Depends(verify_token),
) -> SessionInfo:
    """
    Dependency that requires admin role.

    Accepts: "institution_admin", "super_admin"
    """
    if session.role not in ["institution_admin", "super_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Administratorrechte erforderlich",
        )
    return session


async def require_institution_admin(
    session: SessionInfo = Depends(verify_token),
) -> SessionInfo:
    """
    Dependency that requires institution admin or super admin role.
    """
    if session.role not in ["institution_admin", "super_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Administratorrechte erforderlich",
        )
    return session


async def require_super_admin(
    session: SessionInfo = Depends(verify_token),
) -> SessionInfo:
    """
    Dependency that requires super admin role.
    """
    if session.role != "super_admin":
        raise HTTPException(
            status_code=403,
            detail="Super-Administrator-Rechte erforderlich",
        )
    return session


def extract_session_info_from_record(record: UsersResponse) -> SessionInfo:
    """Extract session info from PocketBase user record."""
    # Check for admin roles
    is_admin = record.role in ["institution_admin", "super_admin"]

    return SessionInfo(
        id=record.id,
        username=record.username,
        is_admin=is_admin,
        role=record.role,
        institution_id=record.institution_id,
    )


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    # Check for X-Forwarded-For header (when behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Check for X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct connection
    return request.client.host if request.client else "127.0.0.1"


async def update_last_seen(
    user_id: str,
    token: str,
    redis_client: redis.Redis,
) -> None:
    """
    Update the lastSeen timestamp for a user.

    Uses Redis to throttle updates to at most once per hour to avoid
    excessive database writes.
    """
    logger = logging.getLogger(__name__)

    # Check if we've updated recently
    throttle_key = f"lastseen:{user_id}"

    try:
        recently_updated = redis_client.get(throttle_key)
        if recently_updated:
            # Already updated recently, skip
            return
    except Exception as e:
        logger.warning(f"Failed to check lastSeen throttle in Redis: {e}")
        # Continue anyway to attempt update

    # Update lastSeen in PocketBase
    try:
        async with httpx.AsyncClient() as client:
            now = datetime.now(UTC).isoformat()
            response = await client.patch(
                f"{POCKETBASE_URL}/api/collections/users/records/{user_id}",
                headers={"Authorization": f"Bearer {token}"},
                json={"lastSeen": now},
                timeout=5.0,
            )

            if response.status_code == 200:
                # Set throttle for next hour
                try:
                    redis_client.setex(throttle_key, LAST_SEEN_UPDATE_INTERVAL, "1")
                except Exception as e:
                    logger.warning(f"Failed to set lastSeen throttle in Redis: {e}")

                logger.debug(f"Updated lastSeen for user {user_id}")
            else:
                logger.warning(
                    f"Failed to update lastSeen for user {user_id}: "
                    f"{response.status_code} - {response.text}"
                )
    except httpx.RequestError as e:
        logger.warning(f"Network error updating lastSeen for user {user_id}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error updating lastSeen for user {user_id}: {e}")
