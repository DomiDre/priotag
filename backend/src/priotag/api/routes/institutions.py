"""API routes for institution management"""

import json
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException

from priotag.models.auth import SessionInfo
from priotag.models.institution import (
    CreateInstitutionRequest,
    InstitutionDetailResponse,
    UpdateInstitutionRequest,
    UpdateMagicWordRequest,
)
from priotag.services.institution import InstitutionService
from priotag.services.pocketbase_service import POCKETBASE_URL
from priotag.utils import get_current_token, require_super_admin, verify_token

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# PUBLIC ENDPOINTS
# ============================================================================
# NOTE: Public institution listing endpoint removed for security/privacy reasons.
# Institution information is now provided via registration URLs with institution
# parameters. This prevents enumeration of all institutions using the system.


# ============================================================================
# SUPER ADMIN ENDPOINTS
# ============================================================================


@router.get("/admin/super/institutions", response_model=list[InstitutionDetailResponse])
async def list_all_institutions_admin(
    session: SessionInfo = Depends(require_super_admin),
    token: str = Depends(get_current_token),
):
    """
    List all institutions (including inactive).

    This endpoint is for super admins only and returns detailed information
    about all institutions.
    """
    try:
        institutions = await InstitutionService.list_all_institutions(auth_token=token)

        # Return detailed fields for super admin
        return [
            InstitutionDetailResponse(
                id=inst.id,
                name=inst.name,
                short_code=inst.short_code,
                registration_magic_word=inst.registration_magic_word,
                admin_public_key=inst.admin_public_key,
                settings=inst.settings,
                active=inst.active,
                created=inst.created,
                updated=inst.updated,
            )
            for inst in institutions
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing institutions for admin: {e}")
        raise HTTPException(status_code=500, detail="Error listing institutions") from e


@router.post("/admin/super/institutions", response_model=InstitutionDetailResponse)
async def create_institution(
    data: CreateInstitutionRequest,
    session: SessionInfo = Depends(require_super_admin),
    token: str = Depends(get_current_token),
):
    """
    Create a new institution.

    This endpoint is for super admins only.
    """
    try:
        institution = await InstitutionService.create_institution(
            data, auth_token=token
        )

        return InstitutionDetailResponse(
            id=institution.id,
            name=institution.name,
            short_code=institution.short_code,
            registration_magic_word=institution.registration_magic_word,
            admin_public_key=institution.admin_public_key,
            settings=institution.settings,
            active=institution.active,
            created=institution.created,
            updated=institution.updated,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating institution: {e}")
        raise HTTPException(status_code=500, detail="Error creating institution") from e


@router.put(
    "/admin/super/institutions/{institution_id}",
    response_model=InstitutionDetailResponse,
)
async def update_institution(
    institution_id: str,
    data: UpdateInstitutionRequest,
    session: SessionInfo = Depends(require_super_admin),
    token: str = Depends(get_current_token),
):
    """
    Update an institution.

    This endpoint is for super admins only.
    """
    try:
        institution = await InstitutionService.update_institution(
            institution_id, data, auth_token=token
        )

        return InstitutionDetailResponse(
            id=institution.id,
            name=institution.name,
            short_code=institution.short_code,
            registration_magic_word=institution.registration_magic_word,
            admin_public_key=institution.admin_public_key,
            settings=institution.settings,
            active=institution.active,
            created=institution.created,
            updated=institution.updated,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating institution {institution_id}: {e}")
        raise HTTPException(status_code=500, detail="Error updating institution") from e


# ============================================================================
# INSTITUTION ADMIN ENDPOINTS
# ============================================================================


@router.get("/admin/institution/info", response_model=InstitutionDetailResponse)
async def get_my_institution(
    session: SessionInfo = Depends(verify_token),
    token: str = Depends(get_current_token),
):
    """
    Get detailed information about the current user's institution.

    This endpoint is for authenticated users to view their institution details.
    Super admins can view any institution, institution admins can view their own.
    """
    if not session.institution_id:
        raise HTTPException(
            status_code=400, detail="User is not associated with an institution"
        )

    try:
        institution = await InstitutionService.get_institution(
            session.institution_id, auth_token=token
        )

        # Institution admins can see detailed info about their own institution
        if session.role in ["institution_admin", "super_admin"]:
            return InstitutionDetailResponse(
                id=institution.id,
                name=institution.name,
                short_code=institution.short_code,
                registration_magic_word=institution.registration_magic_word,
                admin_public_key=institution.admin_public_key,
                settings=institution.settings,
                active=institution.active,
                created=institution.created,
                updated=institution.updated,
            )
        else:
            # Regular users see limited info
            return InstitutionDetailResponse(
                id=institution.id,
                name=institution.name,
                short_code=institution.short_code,
                registration_magic_word="",  # Don't expose to regular users
                admin_public_key=institution.admin_public_key,
                settings={},  # Don't expose settings to regular users
                active=institution.active,
                created=institution.created,
                updated=institution.updated,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching institution info: {e}")
        raise HTTPException(
            status_code=500, detail="Error fetching institution info"
        ) from e


@router.patch("/admin/institution/magic-word", response_model=InstitutionDetailResponse)
async def update_institution_magic_word(
    data: UpdateMagicWordRequest,
    session: SessionInfo = Depends(verify_token),
    token: str = Depends(get_current_token),
):
    """
    Update the magic word for the current user's institution.

    This endpoint is for institution admins to update their own institution's magic word.
    Institution admins can only update their own institution.
    Super admins should use the super admin endpoint instead.
    """
    # Only institution_admin can use this endpoint
    if session.role not in ["institution_admin"]:
        raise HTTPException(
            status_code=403,
            detail="This endpoint is for institution admins only. Super admins should use /admin/super/institutions/{institution_id}",
        )

    if not session.institution_id:
        raise HTTPException(
            status_code=400, detail="User is not associated with an institution"
        )

    try:
        institution = await InstitutionService.update_magic_word(
            session.institution_id, data.magic_word, auth_token=token
        )

        return InstitutionDetailResponse(
            id=institution.id,
            name=institution.name,
            short_code=institution.short_code,
            registration_magic_word=institution.registration_magic_word,
            admin_public_key=institution.admin_public_key,
            settings=institution.settings,
            active=institution.active,
            created=institution.created,
            updated=institution.updated,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating magic word: {e}")
        raise HTTPException(status_code=500, detail="Error updating magic word") from e


@router.get("/admin/institution/qr-data")
async def get_qr_registration_data(
    session: SessionInfo = Depends(verify_token),
    token: str = Depends(get_current_token),
):
    """
    Get QR code registration data for the current institution.

    This endpoint returns the data needed to generate a QR code for user registration.
    The QR code contains the institution's short code and magic word, which can be
    scanned by users to pre-fill the registration form.

    Only institution admins can access this endpoint.
    """
    # Only institution_admin and super_admin can use this endpoint
    if session.role not in ["institution_admin", "super_admin"]:
        raise HTTPException(
            status_code=403,
            detail="This endpoint is for institution admins only",
        )

    if not session.institution_id:
        raise HTTPException(
            status_code=400, detail="User is not associated with an institution"
        )

    try:
        institution = await InstitutionService.get_institution(
            session.institution_id, auth_token=token
        )

        # Return data formatted for QR code generation
        qr_data = {
            "type": "priotag_registration",
            "version": "1.0",
            "institution_name": institution.name,
            "institution_short_code": institution.short_code,
            "magic_word": institution.registration_magic_word,
            "registration_url": f"/register?institution={institution.short_code}",
        }

        return {
            "success": True,
            "data": qr_data,
            "json_string": json.dumps(qr_data),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching QR registration data: {e}")
        raise HTTPException(
            status_code=500, detail="Error fetching QR registration data"
        ) from e


# ============================================================================
# USER MANAGEMENT ENDPOINTS (SUPER ADMIN)
# ============================================================================


@router.get("/admin/super/institutions/{institution_id}/users")
async def list_institution_users(
    institution_id: str,
    session: SessionInfo = Depends(require_super_admin),
    token: str = Depends(get_current_token),
):
    """
    List all users belonging to a specific institution.

    This endpoint is for super admins only.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Fetch users for this institution
            response = await client.get(
                f"{POCKETBASE_URL}/api/collections/users/records",
                params={
                    "filter": f"institution_id='{institution_id}'",
                    "perPage": 500,
                    "sort": "username",
                },
                headers={"Authorization": f"Bearer {token}"},
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=500, detail="Error fetching users for institution"
                )

            users_data = response.json().get("items", [])

            # Return user info (sanitized - no encrypted fields)
            return [
                {
                    "id": user["id"],
                    "username": user["username"],
                    "email": user.get("email", ""),
                    "role": user.get("role", "user"),
                    "institution_id": user.get("institution_id"),
                    "created": user.get("created"),
                    "updated": user.get("updated"),
                    "lastSeen": user.get("lastSeen"),
                }
                for user in users_data
            ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing users for institution {institution_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Error listing users for institution"
        ) from e


@router.patch("/admin/super/users/{user_id}/promote")
async def promote_user_to_institution_admin(
    user_id: str,
    session: SessionInfo = Depends(require_super_admin),
    token: str = Depends(get_current_token),
):
    """
    Promote a user to institution_admin role.

    This endpoint is for super admins only.
    The user must already be associated with an institution.
    """
    try:
        async with httpx.AsyncClient() as client:
            # First, fetch the user to verify they exist and have an institution
            user_response = await client.get(
                f"{POCKETBASE_URL}/api/collections/users/records/{user_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

            if user_response.status_code == 404:
                raise HTTPException(status_code=404, detail="User not found")

            if user_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Error fetching user")

            user_data = user_response.json()

            # Verify user has an institution
            if not user_data.get("institution_id"):
                raise HTTPException(
                    status_code=400,
                    detail="User must be associated with an institution to be promoted to institution_admin",
                )

            # Check if already an admin
            current_role = user_data.get("role", "user")
            if current_role in ["institution_admin", "super_admin"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"User is already an admin (current role: {current_role})",
                )

            # Update user role to institution_admin
            update_response = await client.patch(
                f"{POCKETBASE_URL}/api/collections/users/records/{user_id}",
                json={"role": "institution_admin"},
                headers={"Authorization": f"Bearer {token}"},
            )

            if update_response.status_code != 200:
                error_data = update_response.json()
                raise HTTPException(
                    status_code=update_response.status_code,
                    detail=error_data.get("message", "Error promoting user"),
                )

            updated_user = update_response.json()

            return {
                "success": True,
                "message": f"User '{updated_user['username']}' promoted to institution_admin",
                "user": {
                    "id": updated_user["id"],
                    "username": updated_user["username"],
                    "role": updated_user["role"],
                    "institution_id": updated_user["institution_id"],
                },
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error promoting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Error promoting user") from e


@router.patch("/admin/super/users/{user_id}/demote")
async def demote_user_from_institution_admin(
    user_id: str,
    session: SessionInfo = Depends(require_super_admin),
    token: str = Depends(get_current_token),
):
    """
    Demote an institution_admin back to regular user role.

    This endpoint is for super admins only.
    Cannot demote super_admins.
    """
    try:
        async with httpx.AsyncClient() as client:
            # First, fetch the user to verify they exist
            user_response = await client.get(
                f"{POCKETBASE_URL}/api/collections/users/records/{user_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

            if user_response.status_code == 404:
                raise HTTPException(status_code=404, detail="User not found")

            if user_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Error fetching user")

            user_data = user_response.json()
            current_role = user_data.get("role", "user")

            # Verify user is an institution_admin
            if current_role == "super_admin":
                raise HTTPException(
                    status_code=400, detail="Cannot demote super_admin users"
                )

            if current_role != "institution_admin":
                raise HTTPException(
                    status_code=400,
                    detail=f"User is not an institution_admin (current role: {current_role})",
                )

            # Update user role to regular user
            update_response = await client.patch(
                f"{POCKETBASE_URL}/api/collections/users/records/{user_id}",
                json={"role": "user"},
                headers={"Authorization": f"Bearer {token}"},
            )

            if update_response.status_code != 200:
                error_data = update_response.json()
                raise HTTPException(
                    status_code=update_response.status_code,
                    detail=error_data.get("message", "Error demoting user"),
                )

            updated_user = update_response.json()

            return {
                "success": True,
                "message": f"User '{updated_user['username']}' demoted to regular user",
                "user": {
                    "id": updated_user["id"],
                    "username": updated_user["username"],
                    "role": updated_user["role"],
                    "institution_id": updated_user["institution_id"],
                },
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error demoting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Error demoting user") from e
