import os
import tempfile
import uuid
from typing import Any

import httpx
import redis
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from priotag.models.admin import (
    ManualPriorityRecordForAdmin,
    ManualPriorityRequest,
    UpdateMagicWordRequest,
    UserPriorityRecordForAdmin,
)
from priotag.models.auth import SessionInfo
from priotag.models.pocketbase_schemas import PriorityRecord, UsersResponse
from priotag.models.priorities import validate_month_format_and_range
from priotag.services.encryption import EncryptionManager
from priotag.services.excel_generator import ExcelGenerator
from priotag.services.magic_word import (
    create_or_update_magic_word,
    get_magic_word_from_cache_or_db,
)
from priotag.services.pocketbase_service import POCKETBASE_URL
from priotag.services.redis_service import get_redis
from priotag.utils import get_current_dek, get_current_token, require_admin

router = APIRouter()


@router.get("/magic-word-info")
async def get_magic_word_info(
    token: str = Depends(get_current_token),
    _=Depends(require_admin),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Admin endpoint to check current magic word settings"""

    try:
        magic_word = await get_magic_word_from_cache_or_db(redis_client)
        if not magic_word:
            raise HTTPException(
                status_code=500, detail="No magic word initialized on database"
            )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{POCKETBASE_URL}/api/collections/system_settings/records",
                params={"filter": 'key="registration_magic_word"'},
                headers={"Authorization": f"Bearer {token}"},
            )

            last_updated = None
            last_updated_by = None

            if response.status_code == 200:
                data = response.json()
                if data.get("items") and len(data["items"]) > 0:
                    record = data["items"][0]
                    last_updated = record.get("updated")
                    last_updated_by = record.get("last_updated_by")

        return {
            "current_magic_word": magic_word,
            "last_updated": last_updated,
            "last_updated_by": last_updated_by,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/update-magic-word")
async def update_magic_word(
    request: UpdateMagicWordRequest,
    token: str = Depends(get_current_token),
    session_info: SessionInfo = Depends(require_admin),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Admin endpoint to update the magic word"""

    admin_id = session_info.username

    success = await create_or_update_magic_word(
        request.new_magic_word, token, redis_client, admin_id
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update magic word")

    return {
        "success": True,
        "message": "Magic word updated successfully",
        "updated_by": admin_id,
    }


@router.get("/total-users")
async def get_total_users(
    token: str = Depends(get_current_token),
    _=Depends(require_admin),
):
    """Get total count of registered users in the system"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{POCKETBASE_URL}/api/collections/users/records",
            params={"perPage": 1},
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=500, detail="Fehler beim Abrufen der Benutzerzahl"
            )

        data = response.json()
        return {"totalUsers": data.get("totalItems", 0)}


@router.get("/users/{month}")
async def get_user_submissions(
    month: str,
    token: str = Depends(get_current_token),
    _=Depends(require_admin),
) -> list[UserPriorityRecordForAdmin]:
    """Get all user submissions for a specific month, data is still
    encrypted and needs to be decrypted locally using admin private key
    and respective admin_wrapped_deks

    Note: This only returns regular user submissions (identifier = null).
    Manual entries (with identifier set) are excluded.
    """

    async with httpx.AsyncClient() as client:
        # Fetch priorities for the month - only regular user submissions (identifier is null)
        priorities_response = await client.get(
            f"{POCKETBASE_URL}/api/collections/priorities/records",
            params={
                "filter": f"manual = false && month='{month}' && identifier = null",
                "perPage": 500,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        if priorities_response.status_code != 200:
            raise HTTPException(
                status_code=500, detail="Fehler beim Abrufen der PrioritÃ¤ten"
            )

        priorities_data = priorities_response.json().get("items", [])

        if not priorities_data:
            # No submissions for this month
            return []

        # Get unique user IDs from priorities
        user_ids = list(
            {
                p["userId"]
                for p in priorities_data
                if ("userId" in p and p["userId"] != "")
            }
        )

        if not user_ids:
            return []

        # Fetch only the users who have submissions
        # Build filter for multiple user IDs: id="id1" || id="id2" || ...
        user_filter = " || ".join([f'id="{uid}"' for uid in user_ids])

        users_response = await client.get(
            f"{POCKETBASE_URL}/api/collections/users/records",
            params={"filter": user_filter, "perPage": 500},
            headers={"Authorization": f"Bearer {token}"},
        )

        if users_response.status_code != 200:
            raise HTTPException(
                status_code=500, detail="Fehler beim Abrufen der Benutzer"
            )

        users_data = users_response.json().get("items", [])

        # Create lookup dict for users
        users_by_id: dict[str, UsersResponse] = {
            user["id"]: UsersResponse(**user) for user in users_data
        }

        # Build user submission list
        user_submissions = []
        for priority_data in priorities_data:
            priority = PriorityRecord(**priority_data)
            user_id = priority.userId

            if user_id not in users_by_id:
                # User not found (shouldn't happen, but handle gracefully)
                continue

            user = users_by_id[user_id]

            user_submissions.append(
                UserPriorityRecordForAdmin(
                    adminWrappedDek=user.admin_wrapped_dek,
                    userName=user.username,
                    month=priority.month,
                    userEncryptedFields=user.encrypted_fields,
                    prioritiesEncryptedFields=priority.encrypted_fields,
                )
            )

        return user_submissions


@router.get("/users/info/{user_id}")
async def get_user_for_admin(
    user_id: str,
    token: str = Depends(get_current_token),
    _=Depends(require_admin),
):
    """
    Return encrypted user data.
    Server CANNOT decrypt this - admin must decrypt client-side!
    """
    async with httpx.AsyncClient() as client:
        try:
            # Fetch user details
            user_response = await client.get(
                f"{POCKETBASE_URL}/api/collections/users/records",
                params={"filter": f"username='{user_id}'"},
                headers={"Authorization": f"Bearer {token}"},
            )
            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=500, detail="Fehler beim Abrufen des Benutzer"
                )
            response_data = user_response.json()
            if "items" not in response_data or "totalItems" not in response_data:
                raise HTTPException(
                    status_code=500, detail="In Antwort fehlen erwartete Felder"
                )
            if response_data["totalItems"] != 1:
                raise HTTPException(status_code=204, detail="User nicht gefunden")

            user_record = UsersResponse(**response_data["items"][0])
        except Exception as e:
            raise HTTPException(
                status_code=500, detail="Unbekannter Fehler beim abrufen des Benutzer"
            ) from e

    return {
        "username": user_record.username,
        "admin_wrapped_dek": user_record.admin_wrapped_dek,  # RSA encrypted
        "encrypted_fields": user_record.encrypted_fields,
        "created": user_record.created,
    }


@router.post("/manual-priority")
async def create_manual_priority(
    request: ManualPriorityRequest,
    token: str = Depends(get_current_token),
    auth_data: SessionInfo = Depends(require_admin),
    dek: bytes = Depends(get_current_dek),  # Admin's DEK for encryption
):
    """
    Admin endpoint to manually enter priorities from paper submissions.

    Creates or updates a priority record with a specific identifier.
    All manual entries use the same userId (manual-submissions user) but
    are differentiated by the identifier field.

    Args:
        request: Contains identifier, month, and weeks data
        token: Admin auth token
        dek: Admin's Data Encryption Key

    Returns:
        Success message with created/updated record info
    """

    # Validate month format
    try:
        validate_month_format_and_range(request.month)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # Validate and clean identifier
    identifier = request.identifier.strip()
    if not identifier:
        raise HTTPException(
            status_code=422,
            detail="Identifier darf nicht leer sein",
        )

    # Validate that we have at least some priority data
    has_any_priority = any(
        week.monday is not None
        or week.tuesday is not None
        or week.wednesday is not None
        or week.thursday is not None
        or week.friday is not None
        for week in request.weeks
    )

    if not has_any_priority:
        raise HTTPException(
            status_code=422,
            detail="Bitte geben Sie mindestens eine Priorität ein",
        )

    async with httpx.AsyncClient() as client:
        # Check if entry already exists for this identifier + month
        check_response = await client.get(
            f"{POCKETBASE_URL}/api/collections/priorities/records",
            params={
                "filter": f'userId = null && month="{request.month}" && identifier="{identifier}"'
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        existing_id = None
        if check_response.status_code == 200:
            items = check_response.json().get("items", [])
            if len(items) > 0:
                existing_id = items[0]["id"]

        # Encrypt the weeks data using admin's DEK
        try:
            encrypted_data = EncryptionManager.encrypt_fields(
                {
                    "weeks": [week.model_dump() for week in request.weeks],
                    "name": identifier,
                },
                dek,
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Verschlüsselung fehlgeschlagen: {str(e)}",
            ) from e

        # Create priority record
        priority_data = {
            "userId": auth_data.id,
            "month": request.month,
            "identifier": uuid.uuid4().hex,
            "encrypted_fields": encrypted_data,
            "manual": True,
        }

        if existing_id:
            print(existing_id)
            # Update existing entry
            response = await client.patch(
                f"{POCKETBASE_URL}/api/collections/priorities/records/{existing_id}",
                json=priority_data,
                headers={"Authorization": f"Bearer {token}"},
            )
            message = f"Manuelle Priorität für Kennung '{identifier}' aktualisiert"
        else:
            # Create new entry
            response = await client.post(
                f"{POCKETBASE_URL}/api/collections/priorities/records",
                json=priority_data,
                headers={"Authorization": f"Bearer {token}"},
            )
            message = f"Manuelle Priorität für Kennung '{identifier}' erstellt"

        if response.status_code not in [200, 201]:
            error_data = response.json()
            raise HTTPException(
                status_code=response.status_code,
                detail=error_data.get("message", "Fehler beim Speichern"),
            )

        return {
            "success": True,
            "message": message,
            "identifier": identifier,
            "month": request.month,
        }


@router.get("/manual-entries/{month}")
async def get_manual_entries(
    month: str,
    token: str = Depends(get_current_token),
    _=Depends(require_admin),
):
    """
    Get all manual entries for a specific month.

    Returns encrypted data that must be decrypted client-side by admin.
    """
    async with httpx.AsyncClient() as client:
        # Fetch manual entries (where identifier is NOT null)
        response = await client.get(
            f"{POCKETBASE_URL}/api/collections/priorities/records",
            params={
                "filter": f'manual = true && month="{month}" && identifier!=null',
                "perPage": 500,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Fehler beim Abrufen der manuellen Einträge",
            )

        priorities_data = response.json().get("items", [])

        if not priorities_data:
            # No submissions for this month
            return []

        # Get unique user IDs from priorities
        user_ids = list(
            {
                p["userId"]
                for p in priorities_data
                if ("userId" in p and p["userId"] != "")
            }
        )

        if not user_ids:
            return []

        # Fetch only the users who have submissions
        # Build filter for multiple user IDs: id="id1" || id="id2" || ...
        user_filter = " || ".join([f'id="{uid}"' for uid in user_ids])
        users_response = await client.get(
            f"{POCKETBASE_URL}/api/collections/users/records",
            params={"filter": user_filter, "perPage": 500},
            headers={"Authorization": f"Bearer {token}"},
        )

        if users_response.status_code != 200:
            raise HTTPException(
                status_code=500, detail="Fehler beim Abrufen der Benutzer"
            )

        users_data = users_response.json().get("items", [])

        # Create lookup dict for users
        users_by_id: dict[str, UsersResponse] = {
            user["id"]: UsersResponse(**user) for user in users_data
        }

        # Build user submission list
        manual_submissions = []
        for priority_data in priorities_data:
            priority = PriorityRecord(**priority_data)
            user_id = priority.userId

            if user_id not in users_by_id:
                # User not found (shouldn't happen, but handle gracefully)
                continue

            user = users_by_id[user_id]
            manual_submissions.append(
                ManualPriorityRecordForAdmin(
                    adminWrappedDek=user.admin_wrapped_dek,
                    identifier=priority.identifier,
                    month=priority.month,
                    prioritiesEncryptedFields=priority.encrypted_fields,
                )
            )

        return manual_submissions


@router.delete("/manual-entry/{month}/{identifier}")
async def delete_manual_entry(
    month: str,
    identifier: str,
    token: str = Depends(get_current_token),
    _=Depends(require_admin),
):
    """
    Delete a specific manual entry by month and identifier.
    """
    async with httpx.AsyncClient() as client:
        # Find the entry
        check_response = await client.get(
            f"{POCKETBASE_URL}/api/collections/priorities/records",
            params={
                "filter": f'userId = null && month="{month}" && identifier="{identifier}"'
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        if check_response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Fehler beim Suchen des Eintrags",
            )

        items = check_response.json().get("items", [])
        if len(items) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Manueller Eintrag nicht gefunden (Monat: {month}, Kennung: {identifier})",
            )

        record_id = items[0]["id"]

        # Delete the entry
        delete_response = await client.delete(
            f"{POCKETBASE_URL}/api/collections/priorities/records/{record_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        if delete_response.status_code not in [200, 204]:
            raise HTTPException(
                status_code=delete_response.status_code,
                detail="Fehler beim Löschen des Eintrags",
            )

        return {
            "success": True,
            "message": f"Manueller Eintrag gelöscht (Kennung: {identifier})",
        }


@router.post("/export-excel")
async def export_priorities_to_excel(
    request: dict[str, Any],
    _=Depends(require_admin),
):
    """
    Export decrypted priority data to Excel file.

    The frontend decrypts the data client-side and sends it to this endpoint
    for Excel generation. This keeps the server from having access to
    unencrypted user data.

    Args:
        request: Dictionary containing:
            - decrypted_users: List of user data with priorities
            - month: Month string for the report title

    Returns:
        FileResponse: Excel file download
    """

    decrypted_users = request.get("decrypted_users", [])
    month = request.get("month", "Unbekannt")

    if not decrypted_users:
        raise HTTPException(
            status_code=422,
            detail="Keine Daten zum Exportieren. Bitte entschlüsseln Sie zuerst die Benutzerdaten.",
        )

    try:
        # Create temporary file for Excel export
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".xlsx", delete=False
        ) as tmp_file:
            tmp_path = tmp_file.name

        # Generate Excel file
        excel_generator = ExcelGenerator()
        excel_generator.generate_priorities_report(decrypted_users, month, tmp_path)

        # Prepare filename for download
        safe_month = month.replace("/", "-").replace("\\", "-")
        filename = f"Prioritäten_{safe_month}.xlsx"

        # Return file as download
        return FileResponse(
            path=tmp_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=filename,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            background=None,  # File cleanup handled by FastAPI
        )

    except Exception as e:
        # Clean up temp file if it exists
        if "tmp_path" in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise HTTPException(
            status_code=500,
            detail=f"Fehler beim Erstellen der Excel-Datei: {str(e)}",
        ) from e
