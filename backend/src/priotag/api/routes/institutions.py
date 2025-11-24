"""API routes for institution management"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException

from priotag.models.auth import SessionInfo
from priotag.models.institution import (
    CreateInstitutionRequest,
    InstitutionDetailResponse,
    UpdateInstitutionRequest,
    UpdateMagicWordRequest,
)
from priotag.services.institution import InstitutionService
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
