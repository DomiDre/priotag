"""
Tests for institution service.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from priotag.models.institution import (
    CreateInstitutionRequest,
    UpdateInstitutionRequest,
)
from priotag.models.pocketbase_schemas import InstitutionRecord
from priotag.services.institution import InstitutionService


@pytest.mark.asyncio
@patch("priotag.services.institution.httpx.AsyncClient")
async def test_get_institution_success(mock_client_class, sample_institution_data):
    """Test successfully retrieving an institution by ID."""
    # Setup mock client
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = AsyncMock()

    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = sample_institution_data
    mock_client.get.return_value = mock_response

    mock_client_class.return_value = mock_client

    # Test
    result = await InstitutionService.get_institution(
        "institution_123", auth_token="test_token"
    )

    # Verify
    assert isinstance(result, InstitutionRecord)
    assert result.id == "institution_123"
    assert result.name == "Test University"
    assert result.short_code == "TEST_UNIV"


@pytest.mark.asyncio
@patch("priotag.services.institution.httpx.AsyncClient")
async def test_get_institution_not_found(mock_client_class):
    """Test getting non-existent institution raises 404."""
    # Setup mock client
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False  # Don't suppress exceptions

    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not found"
    mock_client.get.return_value = mock_response

    mock_client_class.return_value = mock_client

    # Test and verify
    with pytest.raises(HTTPException) as exc_info:
        await InstitutionService.get_institution("nonexistent", auth_token="test_token")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
@patch("priotag.services.institution.httpx.AsyncClient")
async def test_get_by_short_code_success(mock_client_class, sample_institution_data):
    """Test successfully retrieving an institution by short code."""
    # Setup mock client
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = AsyncMock()

    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": [sample_institution_data]}
    mock_client.get.return_value = mock_response

    mock_client_class.return_value = mock_client

    # Test
    result = await InstitutionService.get_by_short_code(
        "TEST_UNIV", auth_token="test_token"
    )

    # Verify
    assert isinstance(result, InstitutionRecord)
    assert result.short_code == "TEST_UNIV"
    assert result.name == "Test University"


@pytest.mark.asyncio
@patch("priotag.services.institution.httpx.AsyncClient")
async def test_get_by_short_code_not_found(mock_client_class):
    """Test getting institution by non-existent short code raises 404."""
    # Setup mock client
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False  # Don't suppress exceptions

    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": []}
    mock_client.get.return_value = mock_response

    mock_client_class.return_value = mock_client

    # Test and verify
    with pytest.raises(HTTPException) as exc_info:
        await InstitutionService.get_by_short_code(
            "NONEXISTENT", auth_token="test_token"
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
@patch("priotag.services.institution.httpx.AsyncClient")
async def test_list_institutions_active_only(
    mock_client_class, sample_institution_data, sample_institution_data_2
):
    """Test listing only active institutions."""
    # Setup mock client
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = AsyncMock()

    # Setup mock response - InstitutionView records (no magic_word field)
    from priotag.models.pocketbase_schemas import InstitutionViewRecord

    view_data_1 = {
        k: v
        for k, v in sample_institution_data.items()
        if k != "registration_magic_word"
    }
    view_data_2 = {
        k: v
        for k, v in sample_institution_data_2.items()
        if k != "registration_magic_word"
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": [view_data_1, view_data_2]}
    mock_client.get.return_value = mock_response

    mock_client_class.return_value = mock_client

    # Test - list_institutions returns InstitutionViewRecords (active only by default)
    result = await InstitutionService.list_institutions(auth_token="test_token")

    # Verify
    assert len(result) == 2
    assert all(isinstance(inst, InstitutionViewRecord) for inst in result)
    assert result[0].short_code == "TEST_UNIV"
    assert result[1].short_code == "SECOND_UNIV"


@pytest.mark.asyncio
@patch("priotag.services.institution.httpx.AsyncClient")
async def test_list_institutions_all(mock_client_class, sample_institution_data):
    """Test listing all institutions including inactive."""
    # Setup mock client
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = AsyncMock()

    # Setup mock response
    inactive_institution = sample_institution_data.copy()
    inactive_institution["active"] = False
    inactive_institution["id"] = "institution_inactive"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [sample_institution_data, inactive_institution]
    }
    mock_client.get.return_value = mock_response

    mock_client_class.return_value = mock_client

    # Test - use list_all_institutions for all institutions including inactive
    result = await InstitutionService.list_all_institutions(auth_token="test_token")

    # Verify
    assert len(result) == 2


@pytest.mark.asyncio
@patch("priotag.services.institution.httpx.AsyncClient")
async def test_create_institution_success(mock_client_class, sample_institution_data):
    """Test successfully creating an institution."""
    # Setup mock client
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = AsyncMock()

    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = sample_institution_data
    mock_client.post.return_value = mock_response

    mock_client_class.return_value = mock_client

    # Test
    create_data = CreateInstitutionRequest(
        name="Test University",
        short_code="TEST_UNIV",
        registration_magic_word="TestMagic123",
        admin_public_key="-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA\n-----END PUBLIC KEY-----",
    )
    result = await InstitutionService.create_institution(
        create_data, auth_token="test_token"
    )

    # Verify
    assert isinstance(result, InstitutionRecord)
    assert result.name == "Test University"
    assert result.short_code == "TEST_UNIV"


@pytest.mark.asyncio
@patch("priotag.services.institution.httpx.AsyncClient")
async def test_create_institution_duplicate_short_code(mock_client_class):
    """Test creating institution with duplicate short code fails."""
    # Setup mock client
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False  # Don't suppress exceptions

    # Setup mock response for duplicate
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Duplicate short_code"
    mock_client.post.return_value = mock_response

    mock_client_class.return_value = mock_client

    # Test and verify
    create_data = CreateInstitutionRequest(
        name="Duplicate Uni",
        short_code="EXISTING",
        registration_magic_word="Magic123",
        admin_public_key="-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----",
    )

    with pytest.raises(HTTPException) as exc_info:
        await InstitutionService.create_institution(
            create_data, auth_token="test_token"
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
@patch("priotag.services.institution.httpx.AsyncClient")
async def test_update_institution_success(mock_client_class, sample_institution_data):
    """Test successfully updating an institution."""
    # Setup mock client
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = AsyncMock()

    # Setup mock response
    updated_data = sample_institution_data.copy()
    updated_data["name"] = "Updated University Name"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = updated_data
    mock_client.patch.return_value = mock_response

    mock_client_class.return_value = mock_client

    # Test
    update_data = UpdateInstitutionRequest(name="Updated University Name")
    result = await InstitutionService.update_institution(
        "institution_123", update_data, auth_token="test_token"
    )

    # Verify
    assert isinstance(result, InstitutionRecord)
    assert result.name == "Updated University Name"
    assert result.id == "institution_123"


@pytest.mark.asyncio
@patch("priotag.services.institution.httpx.AsyncClient")
async def test_update_magic_word_success(mock_client_class, sample_institution_data):
    """Test successfully updating institution magic word."""
    # Setup mock client
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = AsyncMock()

    # Setup mock response
    updated_data = sample_institution_data.copy()
    updated_data["registration_magic_word"] = "NewMagic456"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = updated_data
    mock_client.patch.return_value = mock_response

    mock_client_class.return_value = mock_client

    # Test
    result = await InstitutionService.update_magic_word(
        "institution_123", "NewMagic456", auth_token="test_token"
    )

    # Verify
    assert isinstance(result, InstitutionRecord)
    assert result.registration_magic_word == "NewMagic456"


@pytest.mark.asyncio
@patch("priotag.services.institution.httpx.AsyncClient")
async def test_update_magic_word_not_found(mock_client_class):
    """Test updating magic word for non-existent institution fails."""
    # Setup mock client
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False  # Don't suppress exceptions

    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not found"
    mock_client.patch.return_value = mock_response

    mock_client_class.return_value = mock_client

    # Test and verify
    with pytest.raises(HTTPException) as exc_info:
        await InstitutionService.update_magic_word(
            "nonexistent", "NewMagic", auth_token="test_token"
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
@patch("priotag.services.institution.authenticate_service_account")
@patch("priotag.services.institution.httpx.AsyncClient")
async def test_get_institution_without_auth_token(
    mock_client_class, mock_auth_service, sample_institution_data
):
    """Test getting institution without auth token uses service account."""
    # Setup mock client
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = AsyncMock()

    # Mock service account authentication (must be async)
    mock_auth_service.return_value = "service_token"

    # Setup mock response for institution
    inst_response = MagicMock()
    inst_response.status_code = 200
    inst_response.json.return_value = sample_institution_data
    mock_client.get.return_value = inst_response

    mock_client_class.return_value = mock_client

    # Test
    result = await InstitutionService.get_institution(
        "institution_123", auth_token=None
    )

    # Verify
    assert isinstance(result, InstitutionRecord)
    # Verify service account was used
    assert mock_auth_service.called


@pytest.mark.asyncio
@patch("priotag.services.institution.httpx.AsyncClient")
async def test_update_institution_partial_update(
    mock_client_class, sample_institution_data
):
    """Test partial update only sends provided fields."""
    # Setup mock client
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = AsyncMock()

    # Setup mock response
    updated_data = sample_institution_data.copy()
    updated_data["active"] = False

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = updated_data
    mock_client.patch.return_value = mock_response

    mock_client_class.return_value = mock_client

    # Test - only update active status
    update_data = UpdateInstitutionRequest(active=False)
    await InstitutionService.update_institution(
        "institution_123", update_data, auth_token="test_token"
    )

    # Verify only active field was sent
    call_json = mock_client.patch.call_args[1]["json"]
    assert "active" in call_json
    assert call_json["active"] is False
    # Verify other fields were not sent (exclude_none=True)
    assert "name" not in call_json
    assert "short_code" not in call_json
