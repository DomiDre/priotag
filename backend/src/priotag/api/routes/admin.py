import httpx
from fastapi import APIRouter, Depends, HTTPException

from priotag.models.admin import (
    ManualPriorityRecordForAdmin,
    ManualPriorityRequest,
    UpdatePriorityRequest,
    UpdateUserRequest,
    UserPriorityRecordForAdmin,
)
from priotag.models.auth import SessionInfo
from priotag.models.pocketbase_schemas import PriorityRecord, UsersResponse
from priotag.models.priorities import validate_month_format_and_range
from priotag.services.encryption import EncryptionManager
from priotag.services.pocketbase_service import POCKETBASE_URL
from priotag.utils import get_current_dek, get_current_token, require_admin

router = APIRouter()


def build_institution_filter(session: SessionInfo, base_filter: str = "") -> str:
    """
    Build filter string with institution isolation for institution admins.

    Super admins can see all data (no institution filter).
    Institution admins can only see data from their institution.

    Args:
        session: Current session info with role and institution_id
        base_filter: Existing filter string (e.g., "month='2025-01'")

    Returns:
        Filter string with institution_id added if needed

    Raises:
        HTTPException: If user is institution_admin but has no institution_id
    """
    if session.role == "super_admin":
        # Super admin sees everything
        return base_filter

    # Institution admin or regular admin - must filter by institution
    if not session.institution_id:
        raise HTTPException(
            status_code=400,
            detail="User not associated with an institution",
        )

    # Add institution_id filter
    institution_filter = f"institution_id='{session.institution_id}'"

    if base_filter:
        return f"{base_filter} && {institution_filter}"
    else:
        return institution_filter


async def verify_user_belongs_to_institution(
    user_id: str,
    session: SessionInfo,
    token: str,
) -> UsersResponse:
    """
    Verify that a user belongs to the admin's institution (or allow if super_admin).

    Args:
        user_id: User ID to check
        session: Current session info
        token: Auth token

    Returns:
        UsersResponse if user belongs to institution

    Raises:
        HTTPException: If user not found or doesn't belong to institution
    """
    async with httpx.AsyncClient() as client:
        user_response = await client.get(
            f"{POCKETBASE_URL}/api/collections/users/records/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        if user_response.status_code == 404:
            raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")

        if user_response.status_code != 200:
            raise HTTPException(
                status_code=500, detail="Fehler beim Abrufen des Benutzers"
            )

        user_data = user_response.json()
        user = UsersResponse(**user_data)

        # Super admin can access any user
        if session.role == "super_admin":
            return user

        # Institution admin can only access users from their institution
        if user.institution_id != session.institution_id:
            raise HTTPException(
                status_code=403,
                detail="Sie haben keine Berechtigung auf diesen Benutzer zuzugreifen",
            )

        return user


@router.get("/total-users")
async def get_total_users(
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(require_admin),
):
    """
    Get total count of registered users.

    Institution admins see only users from their institution.
    Super admins see all users.
    """
    async with httpx.AsyncClient() as client:
        # Build filter with institution isolation
        filter_str = build_institution_filter(session, "")

        params: dict[str, int | str] = {"perPage": 1}
        if filter_str:
            params["filter"] = filter_str

        response = await client.get(
            f"{POCKETBASE_URL}/api/collections/users/records",
            params=params,
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
    session: SessionInfo = Depends(require_admin),
) -> list[UserPriorityRecordForAdmin]:
    """Get all user submissions for a specific month, data is still
    encrypted and needs to be decrypted locally using admin private key
    and respective admin_wrapped_deks

    Note: This only returns regular user submissions (identifier = null).
    Manual entries (with identifier set) are excluded.

    Institution admins only see submissions from their institution.
    Super admins see all submissions.
    """

    async with httpx.AsyncClient() as client:
        # Build filter with institution isolation
        base_filter = f"manual = false && month='{month}' && identifier = null"
        filter_str = build_institution_filter(session, base_filter)

        # Fetch priorities for the month - only regular user submissions (identifier is null)
        priorities_response = await client.get(
            f"{POCKETBASE_URL}/api/collections/priorities/records",
            params={
                "filter": filter_str,
                "perPage": 500,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        if priorities_response.status_code != 200:
            raise HTTPException(
                status_code=500, detail="Fehler beim Abrufen der Prioritäten"
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
        user_id_filter = " || ".join([f'id="{uid}"' for uid in user_ids])

        # Add institution filtering to user query
        # Wrap user_id_filter in parentheses if adding institution filter
        if session.role != "super_admin" and session.institution_id:
            user_filter = (
                f"({user_id_filter}) && institution_id='{session.institution_id}'"
            )
        else:
            user_filter = user_id_filter

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
                    userId=user.id,
                    month=priority.month,
                    userEncryptedFields=user.encrypted_fields,
                    prioritiesEncryptedFields=priority.encrypted_fields,
                    priorityId=priority.id,
                )
            )

        return user_submissions


@router.get("/users/info/{user_id}")
async def get_user_for_admin(
    user_id: str,
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(require_admin),
):
    """
    Return encrypted user data.
    Server CANNOT decrypt this - admin must decrypt client-side!

    Institution admins can only access users from their institution.
    Super admins can access any user.
    """
    # Validate username format to prevent filter injection
    import re

    if not re.match(r"^[a-zA-Z0-9.@_-]+$", user_id):
        raise HTTPException(
            status_code=422,
            detail="Ungültiges Benutzernamen-Format",
        )

    async with httpx.AsyncClient() as client:
        try:
            # Build filter with institution isolation
            base_filter = f"username='{user_id}'"
            filter_str = build_institution_filter(session, base_filter)

            # Fetch user details
            user_response = await client.get(
                f"{POCKETBASE_URL}/api/collections/users/records",
                params={"filter": filter_str},
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
                raise HTTPException(
                    status_code=404,
                    detail="Benutzer nicht gefunden oder keine Berechtigung",
                )

            user_record = UsersResponse(**response_data["items"][0])
        except HTTPException:
            # Re-raise HTTPExceptions (like the 404 from above)
            raise
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

    # Validate and sanitize identifier to prevent filter injection
    import re

    identifier = request.identifier.strip()
    if not identifier:
        raise HTTPException(
            status_code=422,
            detail="Identifier darf nicht leer sein",
        )
    if not re.match(r"^[a-zA-Z0-9_-]+$", identifier):
        raise HTTPException(
            status_code=422,
            detail="Identifier darf nur Buchstaben, Zahlen, Bindestriche und Unterstriche enthalten",
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

    # Verify admin has institution_id
    if not auth_data.institution_id:
        raise HTTPException(
            status_code=400,
            detail="Admin ist keiner Institution zugeordnet",
        )

    async with httpx.AsyncClient() as client:
        # Check if entry already exists for this identifier + month + institution
        base_check_filter = (
            f'manual = true && month="{request.month}" && identifier="{identifier}"'
        )
        check_filter = build_institution_filter(auth_data, base_check_filter)

        check_response = await client.get(
            f"{POCKETBASE_URL}/api/collections/priorities/records",
            params={"filter": check_filter},
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

        # Create priority record with institution_id
        priority_data = {
            "userId": auth_data.id,
            "month": request.month,
            "identifier": identifier,
            "encrypted_fields": encrypted_data,
            "manual": True,
            "institution_id": auth_data.institution_id,
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
    session: SessionInfo = Depends(require_admin),
):
    """
    Get all manual entries for a specific month.

    Returns encrypted data that must be decrypted client-side by admin.

    Institution admins only see manual entries from their institution.
    Super admins see all manual entries.
    """
    # Validate month format to prevent filter injection
    try:
        validate_month_format_and_range(month)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    async with httpx.AsyncClient() as client:
        # Build filter with institution isolation
        base_filter = f'manual = true && month="{month}" && identifier!=null'
        filter_str = build_institution_filter(session, base_filter)

        # Fetch manual entries (where identifier is NOT null)
        response = await client.get(
            f"{POCKETBASE_URL}/api/collections/priorities/records",
            params={
                "filter": filter_str,
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
        user_id_filter = " || ".join([f'id="{uid}"' for uid in user_ids])

        # Add institution filtering to user query
        # Wrap user_id_filter in parentheses if adding institution filter
        if session.role != "super_admin" and session.institution_id:
            user_filter = (
                f"({user_id_filter}) && institution_id='{session.institution_id}'"
            )
        else:
            user_filter = user_id_filter

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
                    priorityId=priority.id,
                )
            )

        return manual_submissions


@router.delete("/manual-entry/{month}/{identifier}")
async def delete_manual_entry(
    month: str,
    identifier: str,
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(require_admin),
):
    """
    Delete a specific manual entry by month and identifier.

    Institution admins can only delete manual entries from their institution.
    Super admins can delete any manual entry.
    """
    # Validate month format to prevent filter injection
    try:
        validate_month_format_and_range(month)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # Sanitize identifier to prevent filter injection
    import re

    identifier = identifier.strip()
    if not identifier:
        raise HTTPException(
            status_code=422,
            detail="Identifier darf nicht leer sein",
        )
    if not re.match(r"^[a-zA-Z0-9_-]+$", identifier):
        raise HTTPException(
            status_code=422,
            detail="Identifier darf nur Buchstaben, Zahlen, Bindestriche und Unterstriche enthalten",
        )

    async with httpx.AsyncClient() as client:
        # Find the entry with institution filtering
        base_filter = f'manual = true && month="{month}" && identifier="{identifier}"'
        filter_str = build_institution_filter(session, base_filter)

        check_response = await client.get(
            f"{POCKETBASE_URL}/api/collections/priorities/records",
            params={"filter": filter_str},
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
                detail=f"Manueller Eintrag nicht gefunden oder keine Berechtigung (Monat: {month}, Kennung: {identifier})",
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


@router.get("/users/detail/{user_id}")
async def get_user_detail(
    user_id: str,
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(require_admin),
):
    """
    Get detailed user information by user ID.
    Returns encrypted user data that must be decrypted client-side.

    Institution admins can only access users from their institution.
    Super admins can access any user.
    """
    # Verify user belongs to institution (or allow if super_admin)
    user = await verify_user_belongs_to_institution(user_id, session, token)

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "admin_wrapped_dek": user.admin_wrapped_dek,
        "encrypted_fields": user.encrypted_fields,
        "created": user.created,
        "updated": user.updated,
        "lastSeen": user.lastSeen,
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(require_admin),
):
    """
    Update user details (username, email, role).
    Note: This only updates basic fields. Encrypted data cannot be modified here.

    Institution admins can only update users from their institution.
    Super admins can update any user.
    """
    # Verify user belongs to institution (or allow if super_admin)
    await verify_user_belongs_to_institution(user_id, session, token)

    async with httpx.AsyncClient() as client:
        # Build update payload with only provided fields
        update_data = {}
        if request.username is not None:
            update_data["username"] = request.username
        if request.email is not None:
            update_data["email"] = request.email
        if request.role is not None:
            raise HTTPException(
                status_code=422,
                detail="Es ist nicht erlaubt die Rolle zu ändern.",
            )

        if not update_data:
            raise HTTPException(
                status_code=422,
                detail="Keine Aktualisierungsdaten bereitgestellt",
            )

        response = await client.patch(
            f"{POCKETBASE_URL}/api/collections/users/records/{user_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="Benutzer nicht gefunden",
            )

        if response.status_code != 200:
            error_data = response.json()
            raise HTTPException(
                status_code=response.status_code,
                detail=error_data.get(
                    "message", "Fehler beim Aktualisieren des Benutzers"
                ),
            )

        return {
            "success": True,
            "message": f"Benutzer '{request.username or user_id}' erfolgreich aktualisiert",
        }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(require_admin),
):
    """
    Delete a user and all their associated priority records.
    This is a cascading delete operation.

    Institution admins can only delete users from their institution.
    Super admins can delete any user.
    """
    # Verify user belongs to institution (or allow if super_admin)
    user = await verify_user_belongs_to_institution(user_id, session, token)
    username = user.username

    async with httpx.AsyncClient() as client:
        # Delete all priorities associated with this user
        # Add institution filter to priorities query for extra safety
        base_priority_filter = f'userId="{user_id}"'
        priority_filter = build_institution_filter(session, base_priority_filter)

        priorities_response = await client.get(
            f"{POCKETBASE_URL}/api/collections/priorities/records",
            params={"filter": priority_filter, "perPage": 500},
            headers={"Authorization": f"Bearer {token}"},
        )

        deleted_priorities = 0
        if priorities_response.status_code == 200:
            priorities = priorities_response.json().get("items", [])
            for priority in priorities:
                delete_priority_response = await client.delete(
                    f"{POCKETBASE_URL}/api/collections/priorities/records/{priority['id']}",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if delete_priority_response.status_code in [200, 204]:
                    deleted_priorities += 1

        # Delete the user
        delete_response = await client.delete(
            f"{POCKETBASE_URL}/api/collections/users/records/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        if delete_response.status_code not in [200, 204]:
            raise HTTPException(
                status_code=delete_response.status_code,
                detail="Fehler beim Löschen des Benutzers",
            )

        return {
            "success": True,
            "message": f"Benutzer '{username}' und {deleted_priorities} zugehörige Prioritäten gelöscht",
            "deletedPriorities": deleted_priorities,
        }


@router.patch("/priorities/{priority_id}")
async def update_priority(
    priority_id: str,
    request: UpdatePriorityRequest,
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(require_admin),
):
    """
    Update a priority record's encrypted fields.
    The client must decrypt, modify, and re-encrypt the data before sending.

    Institution admins can only update priorities from their institution.
    Super admins can update any priority.
    """
    async with httpx.AsyncClient() as client:
        # Fetch priority first to verify institution ownership
        get_response = await client.get(
            f"{POCKETBASE_URL}/api/collections/priorities/records/{priority_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        if get_response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="Prioritätsdatensatz nicht gefunden",
            )

        if get_response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Fehler beim Abrufen der Priorität",
            )

        priority = get_response.json()

        # Verify institution ownership (super admins bypass this check)
        if session.role != "super_admin":
            if priority.get("institution_id") != session.institution_id:
                raise HTTPException(
                    status_code=403,
                    detail="Keine Berechtigung für diese Priorität",
                )

        # Now update the priority
        response = await client.patch(
            f"{POCKETBASE_URL}/api/collections/priorities/records/{priority_id}",
            json={"encrypted_fields": request.encrypted_fields},
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="Prioritätsdatensatz nicht gefunden",
            )

        if response.status_code != 200:
            error_data = response.json()
            raise HTTPException(
                status_code=response.status_code,
                detail=error_data.get(
                    "message", "Fehler beim Aktualisieren der Priorität"
                ),
            )

        return {
            "success": True,
            "message": "Priorität erfolgreich aktualisiert",
        }


@router.delete("/priorities/{priority_id}")
async def delete_priority(
    priority_id: str,
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(require_admin),
):
    """
    Delete a specific priority record by its ID.

    Institution admins can only delete priorities from their institution.
    Super admins can delete any priority.
    """
    async with httpx.AsyncClient() as client:
        # Get priority details for response message
        priority_response = await client.get(
            f"{POCKETBASE_URL}/api/collections/priorities/records/{priority_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        if priority_response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="Prioritätsdatensatz nicht gefunden",
            )

        if priority_response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Fehler beim Abrufen des Prioritätsdatensatzes",
            )

        priority_data = priority_response.json()

        # Verify institution ownership (super admins bypass this check)
        if session.role != "super_admin":
            if priority_data.get("institution_id") != session.institution_id:
                raise HTTPException(
                    status_code=403,
                    detail="Keine Berechtigung für diese Priorität",
                )

        month = priority_data.get("month", "unknown")

        # Delete the priority record
        delete_response = await client.delete(
            f"{POCKETBASE_URL}/api/collections/priorities/records/{priority_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        if delete_response.status_code not in [200, 204]:
            raise HTTPException(
                status_code=delete_response.status_code,
                detail="Fehler beim Löschen der Priorität",
            )

        return {
            "success": True,
            "message": f"Priorität für Monat {month} erfolgreich gelöscht",
        }
