"""Pydantic BaseModels of admin API"""

from typing import Any

from pydantic import BaseModel, Field

from priotag.models.priorities import WeekPriority


class UpdateMagicWordRequest(BaseModel):
    new_magic_word: str = Field(..., min_length=4)


class AdminLoginRequest(BaseModel):
    identity: str  # email or username
    password: str


class AdminAuthResponse(BaseModel):
    token: str
    admin: dict[str, Any]


class MonthStatsResponse(BaseModel):
    totalSubmissions: int
    completedWeeks: int
    pendingWeeks: int
    uniqueUsers: int
    weeklyCompletion: list[dict[str, Any]]


class ManualPriorityRecordForAdmin(BaseModel):
    adminWrappedDek: str
    identifier: str
    month: str
    prioritiesEncryptedFields: str
    priorityId: str  # PocketBase priority record ID for deletion


class UserPriorityRecordForAdmin(BaseModel):
    adminWrappedDek: str
    userName: str
    userId: str  # PocketBase user ID
    month: str
    userEncryptedFields: str
    prioritiesEncryptedFields: str
    priorityId: str  # PocketBase priority record ID for deletion


class ReminderRequest(BaseModel):
    userIds: list[str]
    message: str
    month: str | None = None


class ReminderResponse(BaseModel):
    sent: int
    failed: int
    details: list[dict[str, Any]]


class ManualPriorityRequest(BaseModel):
    """Request model for manual priority entry"""

    identifier: str  # participant number, initials, etc.
    month: str  # YYYY-MM format
    weeks: list[WeekPriority]


class UpdateUserRequest(BaseModel):
    """Request model for updating user details"""

    username: str | None = None
    email: str | None = None
    role: str | None = None


class UpdatePriorityRequest(BaseModel):
    """Request model for updating a priority record"""

    encrypted_fields: str  # Re-encrypted priority data from admin
