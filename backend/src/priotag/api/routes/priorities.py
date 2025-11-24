from datetime import datetime

import httpx
import redis
from cryptography.exceptions import InvalidTag
from fastapi import APIRouter, Depends, HTTPException

from priotag.middleware.metrics import (
    track_data_operation,
    track_encryption_error,
    track_priority_submission,
)
from priotag.models.auth import SessionInfo
from priotag.models.pocketbase_schemas import PriorityRecord
from priotag.models.priorities import (
    PriorityResponse,
    WeekPriority,
    get_week_start_date,
    validate_month_format_and_range,
)
from priotag.models.request import SuccessResponse
from priotag.services.encryption import EncryptionManager
from priotag.services.pocketbase_service import POCKETBASE_URL
from priotag.services.redis_service import get_redis
from priotag.utils import get_current_dek, get_current_token, verify_token

router = APIRouter()


@router.get("", response_model=list[PriorityResponse])
async def get_user_priorities(
    auth_data: SessionInfo = Depends(verify_token),
    token: str = Depends(get_current_token),
    dek: bytes = Depends(get_current_dek),
):
    """Get all priorities for the authenticated user, optionally filtered by month."""

    user_id = auth_data.id

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{POCKETBASE_URL}/api/collections/priorities/records",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "filter": f'userId = "{user_id}" && identifier = null',
                    "sort": "-month",
                    "perPage": 100,  # Get all records
                },
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Fehler beim Abrufen der Prioritäten",
                )

            data = response.json()
            items = data.get("items", [])

            # Decrypt each record
            decrypted_items = []
            for item in items:
                encrypted_record = PriorityRecord(**item)

                # Decrypt the weeks data
                try:
                    decrypted_weeks = EncryptionManager.decrypt_fields(
                        encrypted_record.encrypted_fields,
                        dek,
                    )
                except InvalidTag as e:
                    raise HTTPException(
                        status_code=500,
                        detail="Entschluesselung der Daten fehlgeschlagen",
                    ) from e

                decrypted_items.append(
                    PriorityResponse(
                        month=encrypted_record.month,
                        weeks=decrypted_weeks["weeks"],
                    )
                )

            return decrypted_items

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail="Verbindungsfehler zum Datenbankserver",
        ) from e


@router.get("/{month}", response_model=PriorityResponse)
async def get_priority(
    month: str,
    auth_data: SessionInfo = Depends(verify_token),
    token: str = Depends(get_current_token),
    dek: bytes = Depends(get_current_dek),
):
    """Get a specific priority record by ID."""

    # Validate month format to prevent filter injection
    try:
        validate_month_format_and_range(month)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    user_id = auth_data.id

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{POCKETBASE_URL}/api/collections/priorities/records",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "filter": f'userId = "{user_id}" && month = "{month}" && identifier = null',
                },
            )

            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="Priorität nicht gefunden",
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Fehler beim Abrufen der Priorität",
                )

            items = response.json()["items"]
            if len(items) == 0:
                # no records found
                return PriorityResponse(month=month, weeks=[])

            encrypted_record = PriorityRecord(**items[0])

            # Verify ownership
            if encrypted_record.userId != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Keine Berechtigung für diese Priorität",
                )

            track_data_operation("read", "priorities")

            # Decrypt weeks data
            try:
                decrypted_weeks = EncryptionManager.decrypt_fields(
                    encrypted_record.encrypted_fields,
                    dek,
                )
            except InvalidTag as e:
                track_encryption_error("decrypt")
                raise HTTPException(
                    status_code=500,
                    detail="Entschluesselung der Daten fehlgeschlagen",
                ) from e
            except Exception:
                track_encryption_error("decrypt")
                raise

            return PriorityResponse(
                month=encrypted_record.month,
                weeks=decrypted_weeks["weeks"],
            )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail="Verbindungsfehler zum Datenbankserver",
        ) from e


@router.put("/{month}", response_model=SuccessResponse)
async def save_priority(
    month: str,
    weeks: list[WeekPriority],
    auth_data: SessionInfo = Depends(verify_token),
    token: str = Depends(get_current_token),
    dek: bytes = Depends(get_current_dek),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Create or update a priority record for the authenticated user."""

    user_id = auth_data.id

    # Validate month
    try:
        validate_month_format_and_range(month)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # Check for concurrent saves - prevent duplicate submissions
    rate_limit_key = f"priority_save:{user_id}:{month}"
    if redis_client.exists(rate_limit_key):
        raise HTTPException(
            status_code=429,
            detail="Bitte warten Sie einen Moment. Ihre Prioritäten werden gespeichert.",
        )

    # Set lock for 3 seconds to prevent rapid duplicate submissions
    redis_client.setex(rate_limit_key, 3, "saving")

    try:
        async with httpx.AsyncClient() as client:
            # Check if record already exists for this month (for regular users, identifier is null)
            check_response = await client.get(
                f"{POCKETBASE_URL}/api/collections/priorities/records",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "filter": f'userId = "{user_id}" && month = "{month}" && identifier = null',
                },
            )

            existing = (
                check_response.json() if check_response.status_code == 200 else None
            )
            existing_id = None
            existing_weeks_data = {}

            if existing and existing.get("totalItems", 0) > 0:
                existing_id = existing["items"][0]["id"]

                # Decrypt existing weeks to preserve data for started weeks
                encrypted_record = PriorityRecord(**existing["items"][0])
                try:
                    decrypted_data = EncryptionManager.decrypt_fields(
                        encrypted_record.encrypted_fields,
                        dek,
                    )
                    # Create a map of weekNumber -> week data
                    for week in decrypted_data.get("weeks", []):
                        existing_weeks_data[week.get("weekNumber")] = week
                except Exception:
                    # If decryption fails, treat as no existing data
                    existing_weeks_data = {}

            # Merge weeks: use old data for started weeks, new data for future weeks
            month_date = datetime.strptime(month, "%Y-%m")
            final_weeks = []
            locked_weeks = []  # Track which weeks are locked

            for new_week in weeks:
                week_start = get_week_start_date(
                    month_date.year, month_date.month, new_week.weekNumber
                )
                # Allow changes until end of Sunday
                week_lock_time = datetime(
                    week_start.year, week_start.month, week_start.day
                )

                now = datetime.now()

                # If week's first day has passed and we have existing data, check if user is trying to change it
                if now >= week_lock_time and new_week.weekNumber in existing_weeks_data:
                    # Check if user is trying to make changes to a locked week
                    old_week = existing_weeks_data[new_week.weekNumber]
                    new_week_dict = new_week.model_dump()

                    # Compare the data to see if changes are being attempted
                    is_different = False
                    for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
                        if old_week.get(day) != new_week_dict.get(day):
                            is_different = True
                            break

                    if is_different:
                        # User is trying to change a locked week - record it
                        locked_weeks.append(new_week.weekNumber)

                    # Keep the existing week data unchanged
                    final_weeks.append(old_week)
                else:
                    # Use the new data (week hasn't started or no existing data)
                    final_weeks.append(new_week.model_dump())

            # If user tried to change locked weeks, return an error
            if locked_weeks:
                week_str = ", ".join([f"KW{w}" for w in locked_weeks])
                raise HTTPException(
                    status_code=422,
                    detail=f"Die Woche kann nicht mehr geändert werden (Änderungen nur bis Sonntag 23:59 Uhr möglich): {week_str}",
                )

            # Encrypt the weeks data (use final_weeks which has the merged data)
            try:
                encrypted_data = EncryptionManager.encrypt_fields(
                    {"weeks": final_weeks},
                    dek,
                )
            except Exception as e:
                track_encryption_error("encrypt")
                raise HTTPException(
                    status_code=500,
                    detail="Verschlüsselung der Daten fehlgeschlagen",
                ) from e

            # Create encrypted record with institution_id
            encrypted_priority = {
                "userId": user_id,
                "month": month,
                "encrypted_fields": encrypted_data,
                "identifier": None,
                "manual": False,
                "institution_id": auth_data.institution_id,
            }

            track_priority_submission(month)
            if existing_id:
                track_data_operation("update", "priorities")
                response = await client.patch(
                    f"{POCKETBASE_URL}/api/collections/priorities/records/{existing_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    json=encrypted_priority,
                )
                message = "Priorität gespeichert"
            else:
                track_data_operation("create", "priorities")
                response = await client.post(
                    f"{POCKETBASE_URL}/api/collections/priorities/records",
                    headers={"Authorization": f"Bearer {token}"},
                    json=encrypted_priority,
                )
                message = "Priorität erstellt"

            if response.status_code not in [200, 201]:
                error_data = response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_data.get("message", "Fehler beim Speichern"),
                )

            # Successfully saved - clear the rate limit lock
            redis_client.delete(rate_limit_key)
            return SuccessResponse(message=message)

    except HTTPException:
        # Don't clear rate limit key on HTTP exceptions (keeps lock for 3s)
        raise
    except httpx.RequestError as e:
        # Clear rate limit on connection errors to allow retry
        redis_client.delete(rate_limit_key)
        raise HTTPException(
            status_code=500,
            detail="Verbindungsfehler zum Datenbankserver",
        ) from e
    except Exception:
        # Clear rate limit on unexpected errors to allow retry
        redis_client.delete(rate_limit_key)
        raise


@router.delete("/{month}")
async def delete_priority(
    month: str,
    auth_data: SessionInfo = Depends(verify_token),
    token: str = Depends(get_current_token),
):
    """Delete a priority record."""

    # Validate month format to prevent filter injection
    try:
        validate_month_format_and_range(month)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    user_id = auth_data.id

    try:
        async with httpx.AsyncClient() as client:
            # Find record in database (regular users have identifier=null)
            check_response = await client.get(
                f"{POCKETBASE_URL}/api/collections/priorities/records",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "filter": f'userId = "{user_id}" && month = "{month}" && identifier = null',
                },
            )

            if check_response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="Priorität nicht gefunden",
                )

            if check_response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail="Fehler bei dem Versuch die Priorität zu löschen.",
                )

            items = check_response.json()["items"]
            if len(items) == 0:
                raise HTTPException(
                    status_code=400, detail="Priorität gefunden aber leer"
                )
            record = items[0]
            if record["userId"] != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Keine Berechtigung für diese Priorität",
                )

            record_id = record["id"]

            # Delete the record
            response = await client.delete(
                f"{POCKETBASE_URL}/api/collections/priorities/records/{record_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

            if response.status_code not in [200, 204]:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Fehler beim Löschen der Priorität",
                )

            return {"message": "Priorität erfolgreich gelöscht"}

    except HTTPException:
        raise
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail="Verbindungsfehler zum Datenbankserver",
        ) from e
