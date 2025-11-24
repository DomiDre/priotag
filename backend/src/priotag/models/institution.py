"""Pydantic models for institution-related requests and responses"""

from pydantic import BaseModel, Field


class InstitutionResponse(BaseModel):
    """Public institution information"""

    id: str
    name: str
    short_code: str


class InstitutionDetailResponse(BaseModel):
    """Detailed institution information (admin only)"""

    id: str
    name: str
    short_code: str
    registration_magic_word: str
    admin_public_key: str | None = None
    settings: dict | None = None
    active: bool
    created: str
    updated: str


class CreateInstitutionRequest(BaseModel):
    """Request to create a new institution"""

    name: str = Field(..., min_length=1, max_length=200)
    short_code: str = Field(..., min_length=1, max_length=50, pattern="^[A-Z0-9_]+$")
    registration_magic_word: str = Field(..., min_length=1)
    admin_public_key: str | None = None
    settings: dict | None = None


class UpdateInstitutionRequest(BaseModel):
    """Request to update an institution"""

    name: str | None = Field(None, min_length=1, max_length=200)
    short_code: str | None = Field(
        None, min_length=1, max_length=50, pattern="^[A-Z0-9_]+$"
    )
    admin_public_key: str | None = None
    settings: dict | None = None
    active: bool | None = None


class UpdateMagicWordRequest(BaseModel):
    """Request to update institution magic word"""

    magic_word: str = Field(..., min_length=1)
