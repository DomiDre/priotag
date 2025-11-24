"""Vacation days admin endpoints"""

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException

from priotag.models.auth import SessionInfo
from priotag.models.vacation_days import (
    BulkVacationDayCreate,
    BulkVacationDayResponse,
    VacationDayCreate,
    VacationDayResponse,
    VacationDayUpdate,
    VacationDayUserResponse,
    validate_date_format,
)
from priotag.services.pocketbase_service import POCKETBASE_URL
from priotag.utils import get_current_token, require_admin, verify_token

router = APIRouter()
user_router = APIRouter()  # Router for user-facing endpoints


def build_institution_filter(session: SessionInfo, base_filter: str = "") -> str:
    """
    Build filter string with institution isolation for institution admins.

    Super admins can see all data (no institution filter).
    Institution admins can only see data from their institution.

    Args:
        session: Current session info with role and institution_id
        base_filter: Existing filter string (e.g., "date >= '2025-01-01'")

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


@router.post("/vacation-days", response_model=VacationDayResponse)
async def create_vacation_day(
    request: VacationDayCreate,
    token: str = Depends(get_current_token),
    session_info: SessionInfo = Depends(require_admin),
):
    """
    Admin endpoint to create a single vacation day.

    Institution admins can only create vacation days for their institution.
    Super admins can create vacation days for any institution.

    Args:
        request: Vacation day data (date, type, description)
        token: Admin auth token
        session_info: Admin session information

    Returns:
        Created vacation day record
    """
    # Verify admin has institution_id
    if not session_info.institution_id:
        raise HTTPException(
            status_code=400,
            detail="Admin ist keiner Institution zugeordnet",
        )

    async with httpx.AsyncClient() as client:
        # Check if vacation day already exists for this date in this institution
        base_filter = f'date ~ "{request.date}"'
        filter_str = build_institution_filter(session_info, base_filter)

        check_response = await client.get(
            f"{POCKETBASE_URL}/api/collections/vacation_days/records",
            params={"filter": filter_str},
            headers={"Authorization": f"Bearer {token}"},
        )

        if check_response.status_code == 200:
            items = check_response.json().get("items", [])
            if len(items) > 0:
                raise HTTPException(
                    status_code=409,
                    detail=f"Urlaubstag für {request.date} existiert bereits",
                )

        # Create vacation day record with institution_id
        vacation_data = {
            "date": request.date,
            "type": request.type,
            "description": request.description,
            "created_by": session_info.username,
            "institution_id": session_info.institution_id,
        }

        response = await client.post(
            f"{POCKETBASE_URL}/api/collections/vacation_days/records",
            json=vacation_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code not in [200, 201]:
            error_data = response.json()
            raise HTTPException(
                status_code=response.status_code,
                detail=error_data.get(
                    "message", "Fehler beim Erstellen des Urlaubstags"
                ),
            )

        record_data = response.json()
        return VacationDayResponse(**record_data)


@router.post("/vacation-days/bulk", response_model=BulkVacationDayResponse)
async def create_vacation_days_bulk(
    request: BulkVacationDayCreate,
    token: str = Depends(get_current_token),
    session_info: SessionInfo = Depends(require_admin),
):
    """
    Admin endpoint to create multiple vacation days at once.

    Institution admins can only create vacation days for their institution.
    Super admins can create vacation days for any institution.

    Args:
        request: List of vacation days to create
        token: Admin auth token
        session_info: Admin session information

    Returns:
        Summary of created, skipped, and failed vacation days
    """
    # Verify admin has institution_id
    if not session_info.institution_id:
        raise HTTPException(
            status_code=400,
            detail="Admin ist keiner Institution zugeordnet",
        )

    created = 0
    skipped = 0
    errors = []

    async with httpx.AsyncClient() as client:
        for day in request.days:
            try:
                # Check if vacation day already exists for this date in this institution
                base_filter = f'date ~ "{day.date}"'
                filter_str = build_institution_filter(session_info, base_filter)

                check_response = await client.get(
                    f"{POCKETBASE_URL}/api/collections/vacation_days/records",
                    params={"filter": filter_str},
                    headers={"Authorization": f"Bearer {token}"},
                )

                if check_response.status_code == 200:
                    items = check_response.json().get("items", [])
                    if len(items) > 0:
                        skipped += 1
                        continue

                # Create vacation day with institution_id
                vacation_data = {
                    "date": day.date,
                    "type": day.type,
                    "description": day.description,
                    "created_by": session_info.username,
                    "institution_id": session_info.institution_id,
                }

                response = await client.post(
                    f"{POCKETBASE_URL}/api/collections/vacation_days/records",
                    json=vacation_data,
                    headers={"Authorization": f"Bearer {token}"},
                )

                if response.status_code in [200, 201]:
                    created += 1
                else:
                    error_data = response.json()
                    errors.append(
                        {
                            "date": day.date,
                            "error": error_data.get("message", "Unbekannter Fehler"),
                        }
                    )

            except Exception as e:
                errors.append({"date": day.date, "error": str(e)})

    return BulkVacationDayResponse(created=created, skipped=skipped, errors=errors)


@router.get("/vacation-days", response_model=list[VacationDayResponse])
async def get_all_vacation_days(
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(require_admin),
    year: int | None = None,
    type: str | None = None,
):
    """
    Admin endpoint to get all vacation days with optional filtering.

    Institution admins only see vacation days from their institution.
    Super admins see all vacation days.

    Args:
        token: Admin auth token
        session: Admin session information
        year: Optional year filter (e.g., 2024)
        type: Optional type filter (vacation, admin_leave, public_holiday)

    Returns:
        List of vacation day records
    """
    async with httpx.AsyncClient() as client:
        # Build base filter
        filters = []
        if year:
            filters.append(f'date >= "{year}-01-01" && date <= "{year}-12-31"')
        if type:
            filters.append(f'type="{type}"')

        base_filter = " && ".join(filters) if filters else ""

        # Add institution isolation
        filter_str = build_institution_filter(session, base_filter)

        params: dict[str, Any] = {"perPage": 500, "sort": "date"}
        if filter_str:
            params["filter"] = filter_str

        response = await client.get(
            f"{POCKETBASE_URL}/api/collections/vacation_days/records",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Fehler beim Abrufen der Urlaubstage",
            )

        vacation_days_data = response.json().get("items", [])
        return [VacationDayResponse(**day) for day in vacation_days_data]


@router.get("/vacation-days/{date}", response_model=VacationDayResponse)
async def get_vacation_day(
    date: str,
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(require_admin),
):
    """
    Admin endpoint to get a specific vacation day by date.

    Institution admins can only get vacation days from their institution.
    Super admins can get any vacation day.

    Args:
        date: Date in YYYY-MM-DD format
        token: Admin auth token
        session: Admin session information

    Returns:
        Vacation day record
    """
    # Validate date format to prevent filter injection
    try:
        validate_date_format(date)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    async with httpx.AsyncClient() as client:
        # Build filter with institution isolation
        base_filter = f'date ~ "{date}"'
        filter_str = build_institution_filter(session, base_filter)

        response = await client.get(
            f"{POCKETBASE_URL}/api/collections/vacation_days/records",
            params={"filter": filter_str},
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Fehler beim Abrufen des Urlaubstags",
            )

        items = response.json().get("items", [])
        if len(items) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Urlaubstag nicht gefunden oder keine Berechtigung: {date}",
            )

        return VacationDayResponse(**items[0])


@router.put("/vacation-days/{date}", response_model=VacationDayResponse)
async def update_vacation_day(
    date: str,
    request: VacationDayUpdate,
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(require_admin),
):
    """
    Admin endpoint to update a vacation day.

    Institution admins can only update vacation days from their institution.
    Super admins can update any vacation day.

    Args:
        date: Date in YYYY-MM-DD format
        request: Updated vacation day data
        token: Admin auth token
        session: Admin session information

    Returns:
        Updated vacation day record
    """
    # Validate date format to prevent filter injection
    try:
        validate_date_format(date)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    async with httpx.AsyncClient() as client:
        # Find the vacation day with institution filtering
        base_filter = f'date ~ "{date}"'
        filter_str = build_institution_filter(session, base_filter)

        check_response = await client.get(
            f"{POCKETBASE_URL}/api/collections/vacation_days/records",
            params={"filter": filter_str},
            headers={"Authorization": f"Bearer {token}"},
        )

        if check_response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Fehler beim Suchen des Urlaubstags",
            )

        items = check_response.json().get("items", [])
        if len(items) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Urlaubstag nicht gefunden oder keine Berechtigung: {date}",
            )

        record_id = items[0]["id"]

        # Build update data (only include non-None fields)
        update_data: dict[str, Any] = {}
        if request.type is not None:
            update_data["type"] = request.type
        if request.description is not None:
            update_data["description"] = request.description

        if not update_data:
            # No fields to update, return existing record
            return VacationDayResponse(**items[0])

        # Update the vacation day
        response = await client.patch(
            f"{POCKETBASE_URL}/api/collections/vacation_days/records/{record_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code not in [200, 201]:
            error_data = response.json()
            raise HTTPException(
                status_code=response.status_code,
                detail=error_data.get(
                    "message", "Fehler beim Aktualisieren des Urlaubstags"
                ),
            )

        record_data = response.json()
        return VacationDayResponse(**record_data)


@router.delete("/vacation-days/{date}")
async def delete_vacation_day(
    date: str,
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(require_admin),
):
    """
    Admin endpoint to delete a vacation day.

    Institution admins can only delete vacation days from their institution.
    Super admins can delete any vacation day.

    Args:
        date: Date in YYYY-MM-DD format
        token: Admin auth token
        session: Admin session information

    Returns:
        Success message
    """
    # Validate date format to prevent filter injection
    try:
        validate_date_format(date)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    async with httpx.AsyncClient() as client:
        # Find the vacation day with institution filtering
        base_filter = f'date ~ "{date}"'
        filter_str = build_institution_filter(session, base_filter)

        check_response = await client.get(
            f"{POCKETBASE_URL}/api/collections/vacation_days/records",
            params={"filter": filter_str},
            headers={"Authorization": f"Bearer {token}"},
        )

        if check_response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Fehler beim Suchen des Urlaubstags",
            )

        items = check_response.json().get("items", [])
        if len(items) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Urlaubstag nicht gefunden oder keine Berechtigung: {date}",
            )

        record_id = items[0]["id"]

        # Delete the vacation day
        delete_response = await client.delete(
            f"{POCKETBASE_URL}/api/collections/vacation_days/records/{record_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        if delete_response.status_code not in [200, 204]:
            raise HTTPException(
                status_code=delete_response.status_code,
                detail="Fehler beim Löschen des Urlaubstags",
            )

        return {
            "success": True,
            "message": f"Urlaubstag gelöscht: {date}",
        }


# ============================================================================
# User-Facing Endpoints (Read-Only)
# ============================================================================


@user_router.get("/vacation-days", response_model=list[VacationDayUserResponse])
async def get_vacation_days_for_users(
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(verify_token),
    year: int | None = None,
    month: int | None = None,
    type: str | None = None,
):
    """
    User endpoint to get vacation days with optional filtering.
    Users can only see vacation days from their own institution.

    Args:
        token: User auth token
        session: User session information
        year: Optional year filter (e.g., 2025)
        month: Optional month filter (1-12)
        type: Optional type filter (vacation, admin_leave, public_holiday)

    Returns:
        List of vacation day records (simplified for users)
    """
    # Verify user has institution_id
    if not session.institution_id:
        raise HTTPException(
            status_code=400,
            detail="Benutzer ist keiner Institution zugeordnet",
        )

    async with httpx.AsyncClient() as client:
        # Build filter with institution filtering
        filters = []

        # Add institution filter first (CRITICAL for multi-institution isolation)
        filters.append(f'institution_id="{session.institution_id}"')

        if year and month:
            # Filter by specific year and month
            filters.append(
                f'date >= "{year}-{month:02d}-01" && date < "{year}-{month:02d}-32"'
            )
        elif year:
            # Filter by year only
            filters.append(f'date >= "{year}-01-01" && date <= "{year}-12-31"')
        elif month:
            # If only month is provided, ignore it (needs year for context)
            pass

        if type:
            filters.append(f'type="{type}"')

        filter_str = " && ".join(filters)

        params: dict[str, Any] = {"perPage": 500, "sort": "date", "filter": filter_str}

        response = await client.get(
            f"{POCKETBASE_URL}/api/collections/vacation_days/records",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Fehler beim Abrufen der Urlaubstage",
            )

        vacation_days_data = response.json().get("items", [])
        # Return simplified response with only date, type, and description
        return [
            VacationDayUserResponse(
                date=day["date"], type=day["type"], description=day["description"]
            )
            for day in vacation_days_data
        ]


@user_router.get("/vacation-days/range", response_model=list[VacationDayUserResponse])
async def get_vacation_days_in_range(
    start_date: str,
    end_date: str,
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(verify_token),
    type: str | None = None,
):
    """
    User endpoint to get vacation days within a date range.
    Useful for displaying vacation days in a calendar view.
    Users can only see vacation days from their own institution.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        token: User auth token
        session: User session information
        type: Optional type filter (vacation, admin_leave, public_holiday)

    Returns:
        List of vacation day records within the date range (simplified for users)
    """
    # Validate date format
    try:
        validate_date_format(start_date)
        validate_date_format(end_date)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # Verify user has institution_id
    if not session.institution_id:
        raise HTTPException(
            status_code=400,
            detail="Benutzer ist keiner Institution zugeordnet",
        )

    async with httpx.AsyncClient() as client:
        # Build filter for date range with institution filtering
        filters = []

        # Add institution filter first (CRITICAL for multi-institution isolation)
        filters.append(f'institution_id="{session.institution_id}"')

        # Add date range filter
        # Include end_date by adding one day and using < instead of <=
        # This handles the datetime field properly (2026-06-05 00:00:00.000Z should be included)
        from datetime import datetime, timedelta

        end_date_inclusive = (
            datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        ).strftime("%Y-%m-%d")
        filters.append(f'date >= "{start_date}" && date < "{end_date_inclusive}"')

        if type:
            filters.append(f'type="{type}"')

        filter_str = " && ".join(filters)

        params: dict[str, Any] = {"perPage": 500, "sort": "date", "filter": filter_str}

        response = await client.get(
            f"{POCKETBASE_URL}/api/collections/vacation_days/records",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Fehler beim Abrufen der Urlaubstage",
            )

        vacation_days_data = response.json().get("items", [])
        # Return simplified response with only date, type, and description
        return [
            VacationDayUserResponse(
                date=day["date"], type=day["type"], description=day["description"]
            )
            for day in vacation_days_data
        ]


@user_router.get("/vacation-days/{date}", response_model=VacationDayUserResponse)
async def get_vacation_day_for_users(
    date: str,
    token: str = Depends(get_current_token),
    session: SessionInfo = Depends(verify_token),
):
    """
    User endpoint to check if a specific date is a vacation day.
    Users can only see vacation days from their own institution.

    Args:
        date: Date in YYYY-MM-DD format
        token: User auth token
        session: User session information

    Returns:
        Vacation day record if exists (simplified for users)
    """
    # Verify user has institution_id
    if not session.institution_id:
        raise HTTPException(
            status_code=400,
            detail="Benutzer ist keiner Institution zugeordnet",
        )

    async with httpx.AsyncClient() as client:
        # Build filter with institution filtering
        filter_str = f'date ~ "{date}" && institution_id="{session.institution_id}"'

        response = await client.get(
            f"{POCKETBASE_URL}/api/collections/vacation_days/records",
            params={"filter": filter_str},
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Fehler beim Abrufen des Urlaubstags",
            )

        items = response.json().get("items", [])
        if len(items) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Urlaubstag nicht gefunden: {date}",
            )

        day = items[0]
        # Return simplified response with only date, type, and description
        return VacationDayUserResponse(
            date=day["date"], type=day["type"], description=day["description"]
        )
