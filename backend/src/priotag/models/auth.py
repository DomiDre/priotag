"""Pydantic models for auth routes"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from priotag.models.pocketbase_schemas import UsersResponse

SecurityMode = Literal["session", "persistent"]


class MagicWordRequest(BaseModel):
    magic_word: str = Field(..., min_length=1)
    institution_short_code: str = Field(..., min_length=1)


class MagicWordResponse(BaseModel):
    success: bool
    token: str | None = None
    message: str | None = None


class RegisterRequest(BaseModel):
    identity: str = Field(
        ...,
        min_length=1,
        description="Username (must not contain @ symbol)",
    )
    password: str = Field(..., min_length=1)
    passwordConfirm: str
    name: str = Field(..., min_length=1)
    registration_token: str
    keep_logged_in: bool = False

    @field_validator("identity")
    @classmethod
    def validate_identity(cls, v: str) -> str:
        """Validate that identity doesn't contain @ symbol (reserved for email)."""
        if "@" in v:
            raise ValueError(
                "Username must not contain @ symbol. Use a simple username instead of an email address."
            )
        return v


class QRRegisterRequest(BaseModel):
    """Request for QR code-based registration (all-in-one)"""

    identity: str = Field(
        ...,
        min_length=1,
        description="Username (must not contain @ symbol)",
    )
    password: str = Field(..., min_length=1)
    passwordConfirm: str
    name: str = Field(..., min_length=1)
    magic_word: str = Field(..., min_length=1)
    institution_short_code: str = Field(..., min_length=1)
    keep_logged_in: bool = False

    @field_validator("identity")
    @classmethod
    def validate_identity(cls, v: str) -> str:
        """Validate that identity doesn't contain @ symbol (reserved for email)."""
        if "@" in v:
            raise ValueError(
                "Username must not contain @ symbol. Use a simple username instead of an email address."
            )
        return v


class DatabaseLoginResponse(BaseModel):
    """Response from pocketbase upon login request"""

    token: str
    record: UsersResponse


class LoginRequest(BaseModel):
    identity: str = Field(..., min_length=1, description="Username")
    password: str = Field(..., min_length=1)
    keep_logged_in: bool = False


class LoginResponse(BaseModel):
    """Response by fastapi upon a successful login request"""

    message: str


class SessionInfo(BaseModel):
    id: str
    username: str
    is_admin: bool  # Kept for backward compatibility
    role: Literal["user", "institution_admin", "super_admin", "service"]
    institution_id: str | None = None  # None for super_admin


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=1)
