"""Institution service for managing institutions"""

import logging

import httpx
from fastapi import HTTPException

from priotag.models.institution import (
    CreateInstitutionRequest,
    UpdateInstitutionRequest,
)
from priotag.models.pocketbase_schemas import InstitutionRecord, InstitutionViewRecord
from priotag.services.pocketbase_service import POCKETBASE_URL
from priotag.services.service_account import authenticate_service_account

logger = logging.getLogger(__name__)


class InstitutionService:
    """Service for managing institutions"""

    @staticmethod
    async def get_institution(
        institution_id: str, auth_token: str | None = None
    ) -> InstitutionRecord:
        """
        Get an institution by ID.

        Args:
            institution_id: The institution ID
            auth_token: Optional authentication token

        Returns:
            Institution record

        Raises:
            HTTPException: If institution not found or access denied
        """
        try:
            async with httpx.AsyncClient() as client:
                headers = {}
                if auth_token:
                    headers["Authorization"] = f"Bearer {auth_token}"
                else:
                    # Use service account if no auth token provided
                    service_token = await authenticate_service_account(client)
                    if service_token:
                        headers["Authorization"] = f"Bearer {service_token}"

                response = await client.get(
                    f"{POCKETBASE_URL}/api/collections/institutions/records/{institution_id}",
                    headers=headers,
                )

                if response.status_code == 200:
                    return InstitutionRecord(**response.json())
                elif response.status_code == 404:
                    raise HTTPException(status_code=404, detail="Institution not found")
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error fetching institution: {response.text}",
                    )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching institution {institution_id}: {e}")
            raise HTTPException(
                status_code=500, detail="Error fetching institution"
            ) from e

    @staticmethod
    async def get_by_short_code(
        short_code: str, auth_token: str | None = None
    ) -> InstitutionRecord:
        """
        Get an institution by short code.

        Args:
            short_code: The institution short code
            auth_token: Optional authentication token

        Returns:
            Institution record

        Raises:
            HTTPException: If institution not found or access denied
        """
        try:
            async with httpx.AsyncClient() as client:
                headers = {}
                if auth_token:
                    headers["Authorization"] = f"Bearer {auth_token}"
                else:
                    # Use service account if no auth token provided
                    service_token = await authenticate_service_account(client)
                    if service_token:
                        headers["Authorization"] = f"Bearer {service_token}"

                response = await client.get(
                    f"{POCKETBASE_URL}/api/collections/institutions/records",
                    params={"filter": f'short_code="{short_code}"'},
                    headers=headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    if items:
                        return InstitutionRecord(**items[0])
                    else:
                        raise HTTPException(
                            status_code=404, detail="Institution not found"
                        )
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error fetching institution: {response.text}",
                    )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching institution by short_code {short_code}: {e}")
            raise HTTPException(
                status_code=500, detail="Error fetching institution"
            ) from e

    @staticmethod
    async def list_institutions(
        auth_token: str | None = None, list_all=False
    ) -> list[InstitutionViewRecord]:
        """
        List all active institutions.

        Args:
            auth_token: Optional authentication token

        Returns:
            List of institution records
        """
        try:
            async with httpx.AsyncClient() as client:
                if not auth_token:
                    auth_token = await authenticate_service_account(client)

                headers = {}
                headers["Authorization"] = f"Bearer {auth_token}"
                response = await client.get(
                    f"{POCKETBASE_URL}/api/collections/institutionsView/records",
                    headers=headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    return [InstitutionViewRecord(**item) for item in items]
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error listing institutions: {response.text}",
                    )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error listing institutions: {e}")
            raise HTTPException(
                status_code=500, detail="Error listing institutions"
            ) from e

    @staticmethod
    async def list_all_institutions(
        auth_token: str | None = None,
    ) -> list[InstitutionRecord]:
        """
        Get all institutions (also inactive) including their magic keys.

        Args:
            auth_token: Optional authentication token

        Returns:
            List of institution records
        """
        try:
            async with httpx.AsyncClient() as client:
                if not auth_token:
                    auth_token = await authenticate_service_account(client)

                headers = {}
                headers["Authorization"] = f"Bearer {auth_token}"
                response = await client.get(
                    f"{POCKETBASE_URL}/api/collections/institutions/records",
                    headers=headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    return [InstitutionRecord(**item) for item in items]
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error listing institutions: {response.text}",
                    )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error listing institutions: {e}")
            raise HTTPException(
                status_code=500, detail="Error listing institutions"
            ) from e

    @staticmethod
    async def create_institution(
        data: CreateInstitutionRequest, auth_token: str
    ) -> InstitutionRecord:
        """
        Create a new institution.

        Args:
            data: Institution creation data
            auth_token: Authentication token (must be super_admin)

        Returns:
            Created institution record

        Raises:
            HTTPException: If creation fails
        """
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {auth_token}"}

                response = await client.post(
                    f"{POCKETBASE_URL}/api/collections/institutions/records",
                    json=data.model_dump(),
                    headers=headers,
                )

                if response.status_code == 200:
                    return InstitutionRecord(**response.json())
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error creating institution: {response.text}",
                    )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating institution: {e}")
            raise HTTPException(
                status_code=500, detail="Error creating institution"
            ) from e

    @staticmethod
    async def update_institution(
        institution_id: str, data: UpdateInstitutionRequest, auth_token: str
    ) -> InstitutionRecord:
        """
        Update an institution.

        Args:
            institution_id: The institution ID
            data: Institution update data
            auth_token: Authentication token

        Returns:
            Updated institution record

        Raises:
            HTTPException: If update fails
        """
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {auth_token}"}

                # Only include non-None fields
                update_data = data.model_dump(exclude_none=True)

                response = await client.patch(
                    f"{POCKETBASE_URL}/api/collections/institutions/records/{institution_id}",
                    json=update_data,
                    headers=headers,
                )

                if response.status_code == 200:
                    return InstitutionRecord(**response.json())
                elif response.status_code == 404:
                    raise HTTPException(status_code=404, detail="Institution not found")
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error updating institution: {response.text}",
                    )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating institution {institution_id}: {e}")
            raise HTTPException(
                status_code=500, detail="Error updating institution"
            ) from e

    @staticmethod
    async def update_magic_word(
        institution_id: str, magic_word: str, auth_token: str
    ) -> InstitutionRecord:
        """
        Update an institution's magic word.

        Args:
            institution_id: The institution ID
            magic_word: New magic word
            auth_token: Authentication token

        Returns:
            Updated institution record

        Raises:
            HTTPException: If update fails
        """
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {auth_token}"}

                response = await client.patch(
                    f"{POCKETBASE_URL}/api/collections/institutions/records/{institution_id}",
                    json={"registration_magic_word": magic_word},
                    headers=headers,
                )

                if response.status_code == 200:
                    return InstitutionRecord(**response.json())
                elif response.status_code == 404:
                    raise HTTPException(status_code=404, detail="Institution not found")
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error updating magic word: {response.text}",
                    )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Error updating magic word for institution {institution_id}: {e}"
            )
            raise HTTPException(
                status_code=500, detail="Error updating magic word"
            ) from e
