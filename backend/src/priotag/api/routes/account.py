import httpx
import redis
from fastapi import APIRouter, Depends, HTTPException, Response

from priotag.models.auth import SessionInfo
from priotag.services.encryption import EncryptionManager
from priotag.services.pocketbase_service import POCKETBASE_URL
from priotag.services.redis_service import get_redis
from priotag.utils import get_current_dek, get_current_token, verify_token

router = APIRouter()


@router.get(
    "/info",
    status_code=200,
    summary="Account info",
    description="Get account information including username, email, and account dates",
)
async def account_info(
    token: str = Depends(get_current_token),
    dek: bytes = Depends(get_current_dek),
    session: SessionInfo = Depends(verify_token),
):
    """Get account information for the authenticated user."""
    async with httpx.AsyncClient() as client:
        try:
            # Fetch user record from PocketBase
            response = await client.get(
                f"{POCKETBASE_URL}/api/collections/users/records/{session.id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to fetch user information",
                )

            user_data = response.json()

            # Decrypt encrypted fields (like name)
            decrypted_fields = {}
            if user_data.get("encrypted_fields"):
                try:
                    decrypted_fields = EncryptionManager.decrypt_fields(
                        user_data["encrypted_fields"], dek
                    )
                except Exception:
                    # If decryption fails, just return empty fields
                    pass

            return {
                "username": user_data.get("username", ""),
                "name": decrypted_fields.get("name", ""),
                "created": user_data.get("created", ""),
                "lastSeen": user_data.get("lastSeen", ""),
            }

        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail="Could not connect to authentication server",
            ) from e


@router.get(
    "/data",
    status_code=200,
    summary="Get all information associated with account",
    description="Get all user data including priorities",
)
async def account_data(
    token: str = Depends(get_current_token),
    dek: bytes = Depends(get_current_dek),
    session: SessionInfo = Depends(verify_token),
):
    """Get all data associated with the user account."""
    async with httpx.AsyncClient() as client:
        try:
            # Fetch user record
            user_response = await client.get(
                f"{POCKETBASE_URL}/api/collections/users/records/{session.id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0,
            )

            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=user_response.status_code,
                    detail="Failed to fetch user information",
                )

            user_data = user_response.json()

            # Decrypt user's encrypted fields
            decrypted_fields = {}
            if user_data.get("encrypted_fields"):
                try:
                    decrypted_fields = EncryptionManager.decrypt_fields(
                        user_data["encrypted_fields"], dek
                    )
                except Exception:
                    pass

            # Fetch all priorities for this user
            priorities_response = await client.get(
                f"{POCKETBASE_URL}/api/collections/priorities/records",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "filter": f'userId="{session.id}" && manual != true',
                    "perPage": 500,  # Fetch up to 500 priorities
                },
                timeout=10.0,
            )

            priorities = []
            if priorities_response.status_code == 200:
                priorities_data = priorities_response.json()
                # Decrypt priority fields
                for priority in priorities_data.get("items", []):
                    try:
                        if priority.get("encrypted_fields"):
                            decrypted_priority_fields = (
                                EncryptionManager.decrypt_fields(
                                    priority["encrypted_fields"], dek
                                )
                            )
                            priorities.append(
                                {
                                    "id": priority.get("id"),
                                    "identifier": priority.get("identifier"),
                                    "month": priority.get("month"),
                                    "manual": priority.get("manual"),
                                    "created": priority.get("created"),
                                    "updated": priority.get("updated"),
                                    **decrypted_priority_fields,
                                }
                            )
                    except Exception:
                        # Skip priorities that can't be decrypted
                        continue

            return {
                "user": {
                    "username": user_data.get("username", ""),
                    "email": user_data.get("email"),
                    "name": decrypted_fields.get("name", ""),
                    "role": user_data.get("role", "user"),
                    "created": user_data.get("created", ""),
                    "updated": user_data.get("updated", ""),
                    "verified": user_data.get("verified", False),
                },
                "priorities": priorities,
                "priority_count": len(priorities),
            }

        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail="Could not connect to authentication server",
            ) from e


@router.delete(
    "/delete",
    status_code=200,
    summary="Delete account",
    description="Permanently delete user account and all associated data",
)
async def delete_account(
    response: Response,
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(verify_token),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Permanently delete user account and all associated data.

    This will:
    1. Delete all user priorities
    2. Delete the user record
    3. Invalidate the session
    4. Clear authentication cookies
    """
    # Rate limiting: Prevent rapid deletion attempts (1 per minute per user)
    rate_limit_key = f"rate_limit:delete_account:{session.id}"
    if redis_client.exists(rate_limit_key):
        raise HTTPException(
            status_code=429,
            detail="Zu viele Versuche. Bitte warten Sie eine Minute.",
        )

    redis_client.setex(rate_limit_key, 60, "deleting")

    # Service accounts cannot be deleted via this endpoint
    if session.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin accounts cannot be deleted via this endpoint",
        )

    async with httpx.AsyncClient() as client:
        try:
            # Delete all priorities associated with this user
            priorities_response = await client.get(
                f"{POCKETBASE_URL}/api/collections/priorities/records",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "filter": f'userId="{session.id}"',
                    "perPage": 500,
                },
                timeout=10.0,
            )

            if priorities_response.status_code == 200:
                priorities_data = priorities_response.json()
                for priority in priorities_data.get("items", []):
                    # Delete each priority
                    await client.delete(
                        f"{POCKETBASE_URL}/api/collections/priorities/records/{priority['id']}",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=10.0,
                    )

            # Delete the user record (user can delete their own account)
            delete_response = await client.delete(
                f"{POCKETBASE_URL}/api/collections/users/records/{session.id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0,
            )

            if delete_response.status_code not in [200, 204]:
                raise HTTPException(
                    status_code=delete_response.status_code,
                    detail="Failed to delete user account",
                )

            # Invalidate session in Redis
            session_key = f"session:{token}"
            redis_client.delete(session_key)

            # Clear authentication cookies
            from priotag.api.routes.auth import clear_auth_cookies

            clear_auth_cookies(response)

            return {
                "success": True,
                "message": "Account successfully deleted",
            }

        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail="Could not connect to authentication server",
            ) from e
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred while deleting account",
            ) from e
