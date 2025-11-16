"""Pydantic models for auth routes"""

from typing import Literal

from pydantic import BaseModel, Field

from priotag.models.pocketbase_schemas import UsersResponse

SecurityMode = Literal["session", "persistent"]


class MagicWordRequest(BaseModel):
    magic_word: str = Field(..., min_length=1)


class MagicWordResponse(BaseModel):
    success: bool
    token: str | None = None
    message: str | None = None


class RegisterRequest(BaseModel):
    identity: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    passwordConfirm: str
    name: str = Field(..., min_length=1)
    registration_token: str
    keep_logged_in: bool = False


class QRRegisterRequest(BaseModel):
    """Request for QR code-based registration (all-in-one)"""

    identity: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    passwordConfirm: str
    name: str = Field(..., min_length=1)
    magic_word: str = Field(..., min_length=1)
    keep_logged_in: bool = False


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
    is_admin: bool


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=1)
