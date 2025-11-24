"""
Unit tests for priority endpoints.

Tests cover:
- GET /api/v1/priorities (get all priorities)
- GET /api/v1/priorities/{month} (get specific month)
- PUT /api/v1/priorities/{month} (create/update)
- DELETE /api/v1/priorities/{month} (delete)

Tests use mocked dependencies (no real PocketBase/Redis).
"""

import base64
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import Response

from priotag.api.routes.priorities import (
    delete_priority,
    get_priority,
    get_user_priorities,
    save_priority,
)
from priotag.models.priorities import WeekPriority
from priotag.services.encryption import EncryptionManager


@pytest.mark.unit
class TestGetUserPriorities:
    """Test GET /api/v1/priorities endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_priorities_success(
        self, sample_session_info, test_dek, mock_httpx_client
    ):
        """Should return all priorities for authenticated user."""
        # Use current month to ensure valid date
        current_month = datetime.now().strftime("%Y-%m")

        # Prepare encrypted data
        weeks_data = {
            "weeks": [
                {
                    "weekNumber": 1,
                    "monday": 1,
                    "tuesday": 2,
                    "wednesday": 3,
                    "thursday": 4,
                    "friday": 5,
                }
            ]
        }
        encrypted_fields = EncryptionManager.encrypt_fields(weeks_data, test_dek)

        # Mock PocketBase response
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "id": "priority_1",
                    "userId": sample_session_info.id,
                    "month": current_month,
                    "encrypted_fields": encrypted_fields,
                    "identifier": "",
                    "manual": False,
                    "collectionId": "priorities_collection",
                    "collectionName": "priorities",
                    "created": "2025-01-01T00:00:00Z",
                    "updated": "2025-01-01T00:00:00Z",
                }
            ]
        }
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        # Execute
        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_httpx_client
            result = await get_user_priorities(
                auth_data=sample_session_info,
                token="test_token",
                dek=test_dek,
            )

        # Verify
        assert len(result) == 1
        assert result[0].month == current_month
        assert len(result[0].weeks) == 1
        assert result[0].weeks[0].weekNumber == 1
        assert result[0].weeks[0].monday == 1

    @pytest.mark.asyncio
    async def test_get_user_priorities_empty(
        self, sample_session_info, test_dek, mock_httpx_client
    ):
        """Should return empty list when no priorities exist."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_httpx_client
            result = await get_user_priorities(
                auth_data=sample_session_info,
                token="test_token",
                dek=test_dek,
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_get_user_priorities_decryption_failure(
        self, sample_session_info, test_dek, mock_httpx_client
    ):
        """Should raise HTTPException when decryption fails."""
        current_month = datetime.now().strftime("%Y-%m")

        # Mock PocketBase response with invalid encrypted data
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "id": "priority_1",
                    "userId": sample_session_info.id,
                    "month": current_month,
                    "encrypted_fields": "invalid_encrypted_data",
                    "identifier": "",
                    "manual": False,
                    "collectionId": "priorities_collection",
                    "collectionName": "priorities",
                    "created": "2025-01-01T00:00:00Z",
                    "updated": "2025-01-01T00:00:00Z",
                }
            ]
        }
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_httpx_client
            with pytest.raises(HTTPException) as exc_info:
                await get_user_priorities(
                    auth_data=sample_session_info,
                    token="test_token",
                    dek=test_dek,
                )

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_user_priorities_pocketbase_error(
        self, sample_session_info, test_dek, mock_httpx_client
    ):
        """Should raise HTTPException when PocketBase returns error."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 500
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_httpx_client
            with pytest.raises(HTTPException) as exc_info:
                await get_user_priorities(
                    auth_data=sample_session_info,
                    token="test_token",
                    dek=test_dek,
                )

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_user_priorities_connection_error(
        self, sample_session_info, test_dek
    ):
        """Should raise HTTPException when connection to PocketBase fails."""
        import httpx

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(
                side_effect=httpx.RequestError("Connection failed")
            )
            mock_client.return_value.__aenter__.return_value = mock_async_client

            with pytest.raises(HTTPException) as exc_info:
                await get_user_priorities(
                    auth_data=sample_session_info,
                    token="test_token",
                    dek=test_dek,
                )

            assert exc_info.value.status_code == 500
            assert "Verbindungsfehler" in exc_info.value.detail


@pytest.mark.unit
class TestGetPriority:
    """Test GET /api/v1/priorities/{month} endpoint."""

    @pytest.mark.asyncio
    async def test_get_priority_success(
        self, sample_session_info, test_dek, mock_httpx_client
    ):
        """Should return priority for specific month."""
        current_month = datetime.now().strftime("%Y-%m")

        weeks_data = {
            "weeks": [
                {
                    "weekNumber": 1,
                    "monday": 1,
                    "tuesday": 2,
                    "wednesday": 3,
                    "thursday": 4,
                    "friday": 5,
                }
            ]
        }
        encrypted_fields = EncryptionManager.encrypt_fields(weeks_data, test_dek)

        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "id": "priority_1",
                    "userId": sample_session_info.id,
                    "month": current_month,
                    "encrypted_fields": encrypted_fields,
                    "identifier": "",
                    "manual": False,
                    "collectionId": "priorities_collection",
                    "collectionName": "priorities",
                    "created": "2025-01-01T00:00:00Z",
                    "updated": "2025-01-01T00:00:00Z",
                }
            ]
        }
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_httpx_client
            result = await get_priority(
                month=current_month,
                auth_data=sample_session_info,
                token="test_token",
                dek=test_dek,
            )

        assert result.month == current_month
        assert len(result.weeks) == 1
        assert result.weeks[0].weekNumber == 1

    @pytest.mark.asyncio
    async def test_get_priority_not_found(
        self, sample_session_info, test_dek, mock_httpx_client
    ):
        """Should return empty weeks list when priority not found."""
        current_month = datetime.now().strftime("%Y-%m")

        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_httpx_client
            result = await get_priority(
                month=current_month,
                auth_data=sample_session_info,
                token="test_token",
                dek=test_dek,
            )

        assert result.month == current_month
        assert result.weeks == []

    @pytest.mark.asyncio
    async def test_get_priority_ownership_verification(
        self, sample_session_info, test_dek, mock_httpx_client
    ):
        """Should raise 403 when user doesn't own the priority."""
        current_month = datetime.now().strftime("%Y-%m")

        weeks_data: dict[str, list] = {"weeks": []}
        encrypted_fields = EncryptionManager.encrypt_fields(weeks_data, test_dek)

        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "id": "priority_1",
                    "userId": "different_user_id",
                    "month": current_month,
                    "encrypted_fields": encrypted_fields,
                    "identifier": "",
                    "manual": False,
                    "collectionId": "priorities_collection",
                    "collectionName": "priorities",
                    "created": "2025-01-01T00:00:00Z",
                    "updated": "2025-01-01T00:00:00Z",
                }
            ]
        }
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_httpx_client
            with pytest.raises(HTTPException) as exc_info:
                await get_priority(
                    month=current_month,
                    auth_data=sample_session_info,
                    token="test_token",
                    dek=test_dek,
                )

            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_priority_decryption_failure(
        self, sample_session_info, test_dek, mock_httpx_client
    ):
        """Should raise 500 when decryption fails."""
        current_month = datetime.now().strftime("%Y-%m")

        # Create properly base64 encoded but invalid encrypted data
        invalid_encrypted_data = base64.b64encode(b"invalid_encrypted_content").decode()

        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "id": "priority_1",
                    "userId": sample_session_info.id,
                    "month": current_month,
                    "encrypted_fields": invalid_encrypted_data,
                    "identifier": "",
                    "manual": False,
                    "collectionId": "priorities_collection",
                    "collectionName": "priorities",
                    "created": "2025-01-01T00:00:00Z",
                    "updated": "2025-01-01T00:00:00Z",
                }
            ]
        }
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_httpx_client
            with pytest.raises(HTTPException) as exc_info:
                await get_priority(
                    month=current_month,
                    auth_data=sample_session_info,
                    token="test_token",
                    dek=test_dek,
                )

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_priority_404_response(
        self, sample_session_info, test_dek, mock_httpx_client
    ):
        """Should raise 404 when PocketBase returns 404."""
        current_month = datetime.now().strftime("%Y-%m")

        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 404
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_httpx_client
            with pytest.raises(HTTPException) as exc_info:
                await get_priority(
                    month=current_month,
                    auth_data=sample_session_info,
                    token="test_token",
                    dek=test_dek,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_priority_non_200_response(
        self, sample_session_info, test_dek, mock_httpx_client
    ):
        """Should raise HTTPException for non-200 responses."""
        current_month = datetime.now().strftime("%Y-%m")

        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 503
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_httpx_client
            with pytest.raises(HTTPException) as exc_info:
                await get_priority(
                    month=current_month,
                    auth_data=sample_session_info,
                    token="test_token",
                    dek=test_dek,
                )

            assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_get_priority_connection_error(self, sample_session_info, test_dek):
        """Should raise HTTPException when connection fails."""
        import httpx

        current_month = datetime.now().strftime("%Y-%m")

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(
                side_effect=httpx.RequestError("Connection failed")
            )
            mock_client.return_value.__aenter__.return_value = mock_async_client

            with pytest.raises(HTTPException) as exc_info:
                await get_priority(
                    month=current_month,
                    auth_data=sample_session_info,
                    token="test_token",
                    dek=test_dek,
                )

            assert exc_info.value.status_code == 500
            assert "Verbindungsfehler" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_priority_generic_exception_during_decryption(
        self, sample_session_info, test_dek, mock_httpx_client
    ):
        """Should re-raise generic exception during decryption (after tracking error)."""
        current_month = datetime.now().strftime("%Y-%m")

        weeks_data: dict[str, list[WeekPriority]] = {"weeks": []}
        encrypted_fields = EncryptionManager.encrypt_fields(weeks_data, test_dek)

        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "id": "priority_1",
                    "userId": sample_session_info.id,
                    "month": current_month,
                    "encrypted_fields": encrypted_fields,
                    "identifier": "",
                    "manual": False,
                    "collectionId": "priorities_collection",
                    "collectionName": "priorities",
                    "created": "2025-01-01T00:00:00Z",
                    "updated": "2025-01-01T00:00:00Z",
                }
            ]
        }
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_httpx_client
            # Mock EncryptionManager.decrypt_fields to raise a generic exception
            with patch(
                "priotag.api.routes.priorities.EncryptionManager.decrypt_fields"
            ) as mock_decrypt:
                mock_decrypt.side_effect = Exception("Generic decryption error")

                # Generic exceptions are re-raised, not wrapped in HTTPException
                with pytest.raises(Exception) as exc_info:
                    await get_priority(
                        month=current_month,
                        auth_data=sample_session_info,
                        token="test_token",
                        dek=test_dek,
                    )

                assert "Generic decryption error" in str(exc_info.value)


@pytest.mark.unit
class TestSavePriority:
    """Test PUT /api/v1/priorities/{month} endpoint."""

    @pytest.mark.asyncio
    async def test_save_priority_create_new(
        self, sample_session_info, test_dek, mock_httpx_client, fake_redis
    ):
        """Should create new priority when none exists."""
        weeks = [
            WeekPriority(
                weekNumber=1,
                monday=1,
                tuesday=2,
                wednesday=3,
                thursday=4,
                friday=5,
            )
        ]

        # Mock PocketBase responses
        check_response = MagicMock(spec=Response)
        check_response.status_code = 200
        check_response.json.return_value = {"totalItems": 0, "items": []}

        create_response = MagicMock(spec=Response)
        create_response.status_code = 201
        create_response.json.return_value = {"id": "new_priority_1"}

        mock_httpx_client.get = AsyncMock(return_value=check_response)
        mock_httpx_client.post = AsyncMock(return_value=create_response)

        # Use current month to pass validation
        current_month = datetime.now().strftime("%Y-%m")

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_httpx_client
            result = await save_priority(
                month=current_month,
                weeks=weeks,
                auth_data=sample_session_info,
                token="test_token",
                dek=test_dek,
                redis_client=fake_redis,
            )

        assert "erstellt" in result.message or "gespeichert" in result.message

    @pytest.mark.asyncio
    async def test_save_priority_update_existing(
        self, sample_session_info, test_dek, mock_httpx_client, fake_redis
    ):
        """Should update existing priority."""
        # Use next month to ensure weeks are not locked (editable)
        next_month = (datetime.now() + timedelta(days=32)).strftime("%Y-%m")

        weeks = [
            WeekPriority(
                weekNumber=1,
                monday=2,
                tuesday=3,
                wednesday=4,
                thursday=5,
                friday=1,
            )
        ]

        # Mock existing priority
        existing_weeks_data = {
            "weeks": [
                {
                    "weekNumber": 1,
                    "monday": 1,
                    "tuesday": 2,
                    "wednesday": 3,
                    "thursday": 4,
                    "friday": 5,
                }
            ]
        }
        encrypted_fields = EncryptionManager.encrypt_fields(
            existing_weeks_data, test_dek
        )

        check_response = MagicMock(spec=Response)
        check_response.status_code = 200
        check_response.json.return_value = {
            "totalItems": 1,
            "items": [
                {
                    "id": "existing_priority_1",
                    "userId": sample_session_info.id,
                    "month": next_month,
                    "encrypted_fields": encrypted_fields,
                    "identifier": "",
                    "manual": False,
                    "collectionId": "priorities_collection",
                    "collectionName": "priorities",
                    "created": "2025-01-01T00:00:00Z",
                    "updated": "2025-01-01T00:00:00Z",
                }
            ],
        }

        update_response = MagicMock(spec=Response)
        update_response.status_code = 200
        update_response.json.return_value = {"id": "existing_priority_1"}

        mock_httpx_client.get = AsyncMock(return_value=check_response)
        mock_httpx_client.patch = AsyncMock(return_value=update_response)

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_httpx_client
            result = await save_priority(
                month=next_month,
                weeks=weeks,
                auth_data=sample_session_info,
                token="test_token",
                dek=test_dek,
                redis_client=fake_redis,
            )

        assert "gespeichert" in result.message or "erstellt" in result.message

    @pytest.mark.asyncio
    async def test_save_priority_invalid_month_format(
        self, sample_session_info, test_dek, fake_redis
    ):
        """Should raise 422 for invalid month format."""
        weeks = [WeekPriority(weekNumber=1, monday=1)]

        with pytest.raises(HTTPException) as exc_info:
            await save_priority(
                month="2025-13",  # Invalid month
                weeks=weeks,
                auth_data=sample_session_info,
                token="test_token",
                dek=test_dek,
                redis_client=fake_redis,
            )

        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_save_priority_month_out_of_range(
        self, sample_session_info, test_dek, fake_redis
    ):
        """Should raise 422 for month outside allowed range."""
        weeks = [WeekPriority(weekNumber=1, monday=1)]

        # Get a month that's too far in the future
        future_month = "2030-01"

        with pytest.raises(HTTPException) as exc_info:
            await save_priority(
                month=future_month,
                weeks=weeks,
                auth_data=sample_session_info,
                token="test_token",
                dek=test_dek,
                redis_client=fake_redis,
            )

        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_save_priority_rate_limiting(
        self, sample_session_info, test_dek, fake_redis
    ):
        """Should enforce rate limiting."""
        weeks = [WeekPriority(weekNumber=1, monday=1)]
        current_month = datetime.now().strftime("%Y-%m")

        # Set rate limit key (matches the actual key used in the route)
        rate_limit_key = f"priority_save:{sample_session_info.id}:{current_month}"
        fake_redis.setex(rate_limit_key, 3, "saving")

        with pytest.raises(HTTPException) as exc_info:
            await save_priority(
                month=current_month,
                weeks=weeks,
                auth_data=sample_session_info,
                token="test_token",
                dek=test_dek,
                redis_client=fake_redis,
            )

        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_save_priority_encryption_failure(
        self, sample_session_info, test_dek, mock_httpx_client, fake_redis
    ):
        """Should raise 500 when encryption fails."""
        weeks = [WeekPriority(weekNumber=1, monday=1)]
        current_month = datetime.now().strftime("%Y-%m")

        check_response = MagicMock(spec=Response)
        check_response.status_code = 200
        check_response.json.return_value = {"totalItems": 0, "items": []}

        mock_httpx_client.get = AsyncMock(return_value=check_response)

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_httpx_client
            with patch(
                "priotag.api.routes.priorities.EncryptionManager.encrypt_fields"
            ) as mock_encrypt:
                mock_encrypt.side_effect = Exception("Encryption failed")

                with pytest.raises(HTTPException) as exc_info:
                    await save_priority(
                        month=current_month,
                        weeks=weeks,
                        auth_data=sample_session_info,
                        token="test_token",
                        dek=test_dek,
                        redis_client=fake_redis,
                    )

                assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_save_priority_pocketbase_error_response(
        self, sample_session_info, test_dek, mock_httpx_client, fake_redis
    ):
        """Should raise HTTPException when PocketBase returns error during save."""
        weeks = [WeekPriority(weekNumber=1, monday=1)]
        current_month = datetime.now().strftime("%Y-%m")

        check_response = MagicMock(spec=Response)
        check_response.status_code = 200
        check_response.json.return_value = {"totalItems": 0, "items": []}

        create_response = MagicMock(spec=Response)
        create_response.status_code = 400
        create_response.json.return_value = {"message": "Invalid data"}

        mock_httpx_client.get = AsyncMock(return_value=check_response)
        mock_httpx_client.post = AsyncMock(return_value=create_response)

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_httpx_client
            with pytest.raises(HTTPException) as exc_info:
                await save_priority(
                    month=current_month,
                    weeks=weeks,
                    auth_data=sample_session_info,
                    token="test_token",
                    dek=test_dek,
                    redis_client=fake_redis,
                )

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_save_priority_connection_error(
        self, sample_session_info, test_dek, fake_redis
    ):
        """Should raise HTTPException when connection to PocketBase fails."""
        import httpx

        weeks = [WeekPriority(weekNumber=1, monday=1)]
        current_month = datetime.now().strftime("%Y-%m")

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(
                side_effect=httpx.RequestError("Connection failed")
            )
            mock_client.return_value.__aenter__.return_value = mock_async_client

            with pytest.raises(HTTPException) as exc_info:
                await save_priority(
                    month=current_month,
                    weeks=weeks,
                    auth_data=sample_session_info,
                    token="test_token",
                    dek=test_dek,
                    redis_client=fake_redis,
                )

            assert exc_info.value.status_code == 500
            assert "Verbindungsfehler" in exc_info.value.detail


@pytest.mark.unit
class TestDeletePriority:
    """Test DELETE /api/v1/priorities/{month} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_priority_success(
        self, sample_session_info, mock_httpx_client
    ):
        """Should delete priority successfully."""
        # Mock check response
        current_month = datetime.now().strftime("%Y-%m")
        check_response = MagicMock(spec=Response)
        check_response.status_code = 200
        check_response.json.return_value = {
            "items": [
                {
                    "id": "priority_1",
                    "userId": sample_session_info.id,
                    "month": current_month,
                }
            ]
        }

        # Mock delete response
        delete_response = MagicMock(spec=Response)
        delete_response.status_code = 204

        mock_httpx_client.get = AsyncMock(return_value=check_response)
        mock_httpx_client.delete = AsyncMock(return_value=delete_response)

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_httpx_client
            result = await delete_priority(
                month=current_month,
                auth_data=sample_session_info,
                token="test_token",
            )

        assert "gelöscht" in result["message"] or "gelöscht" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_priority_not_found(
        self, sample_session_info, mock_httpx_client
    ):
        """Should raise 400 when priority doesn't exist."""
        current_month = datetime.now().strftime("%Y-%m")
        check_response = MagicMock(spec=Response)
        check_response.status_code = 200
        check_response.json.return_value = {"items": []}

        mock_httpx_client.get = AsyncMock(return_value=check_response)

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_httpx_client
            with pytest.raises(HTTPException) as exc_info:
                await delete_priority(
                    month=current_month,
                    auth_data=sample_session_info,
                    token="test_token",
                )

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_priority_ownership_check(
        self, sample_session_info, mock_httpx_client
    ):
        """Should raise 403 when user doesn't own the priority."""
        current_month = datetime.now().strftime("%Y-%m")
        check_response = MagicMock(spec=Response)
        check_response.status_code = 200
        check_response.json.return_value = {
            "items": [
                {
                    "id": "priority_1",
                    "userId": "different_user_id",
                    "month": current_month,
                }
            ]
        }

        mock_httpx_client.get = AsyncMock(return_value=check_response)

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_httpx_client
            with pytest.raises(HTTPException) as exc_info:
                await delete_priority(
                    month=current_month,
                    auth_data=sample_session_info,
                    token="test_token",
                )

            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_priority_pocketbase_error(
        self, sample_session_info, mock_httpx_client
    ):
        """Should raise HTTPException when PocketBase returns error."""
        current_month = datetime.now().strftime("%Y-%m")
        check_response = MagicMock(spec=Response)
        check_response.status_code = 200
        check_response.json.return_value = {
            "items": [
                {
                    "id": "priority_1",
                    "userId": sample_session_info.id,
                    "month": current_month,
                }
            ]
        }

        delete_response = MagicMock(spec=Response)
        delete_response.status_code = 500

        mock_httpx_client.get = AsyncMock(return_value=check_response)
        mock_httpx_client.delete = AsyncMock(return_value=delete_response)

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_httpx_client
            with pytest.raises(HTTPException) as exc_info:
                await delete_priority(
                    month=current_month,
                    auth_data=sample_session_info,
                    token="test_token",
                )

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_delete_priority_404_response(
        self, sample_session_info, mock_httpx_client
    ):
        """Should raise 404 when PocketBase returns 404."""
        current_month = datetime.now().strftime("%Y-%m")
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 404
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_httpx_client
            with pytest.raises(HTTPException) as exc_info:
                await delete_priority(
                    month=current_month,
                    auth_data=sample_session_info,
                    token="test_token",
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_priority_non_200_response(
        self, sample_session_info, mock_httpx_client
    ):
        """Should raise HTTPException for non-200 responses."""
        current_month = datetime.now().strftime("%Y-%m")
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 503
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_httpx_client
            with pytest.raises(HTTPException) as exc_info:
                await delete_priority(
                    month=current_month,
                    auth_data=sample_session_info,
                    token="test_token",
                )

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_priority_connection_error(self, sample_session_info):
        """Should raise HTTPException when connection fails."""
        import httpx

        with patch("priotag.api.routes.priorities.httpx.AsyncClient") as mock_client:
            current_month = datetime.now().strftime("%Y-%m")
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(
                side_effect=httpx.RequestError("Connection failed")
            )
            mock_client.return_value.__aenter__.return_value = mock_async_client

            with pytest.raises(HTTPException) as exc_info:
                await delete_priority(
                    month=current_month,
                    auth_data=sample_session_info,
                    token="test_token",
                )

            assert exc_info.value.status_code == 500
            assert "Verbindungsfehler" in exc_info.value.detail
