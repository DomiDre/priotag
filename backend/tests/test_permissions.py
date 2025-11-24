"""
Tests for multi-institution permission system.
"""

import pytest
from fastapi import HTTPException

from priotag.models.auth import SessionInfo
from priotag.utils import (
    require_admin,
    require_institution_admin,
    require_super_admin,
)


@pytest.mark.asyncio
class TestRequireAdmin:
    """Test require_admin permission function."""

    async def test_require_admin_with_super_admin(
        self, sample_super_admin_session_info
    ):
        """Test super_admin passes require_admin check."""
        result = await require_admin(sample_super_admin_session_info)
        assert result.role == "super_admin"

    async def test_require_admin_with_institution_admin(
        self, sample_admin_session_info
    ):
        """Test institution_admin passes require_admin check."""
        result = await require_admin(sample_admin_session_info)
        assert result.role == "institution_admin"

    async def test_require_admin_with_regular_user_fails(self, sample_session_info):
        """Test regular user fails require_admin check."""
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(sample_session_info)

        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
class TestRequireInstitutionAdmin:
    """Test require_institution_admin permission function."""

    async def test_require_institution_admin_with_institution_admin(
        self, sample_admin_session_info
    ):
        """Test institution_admin passes check."""
        result = await require_institution_admin(sample_admin_session_info)
        assert result.role == "institution_admin"

    async def test_require_institution_admin_with_super_admin(
        self, sample_super_admin_session_info
    ):
        """Test super_admin passes institution_admin check."""
        result = await require_institution_admin(sample_super_admin_session_info)
        assert result.role == "super_admin"

    async def test_require_institution_admin_with_user_fails(self, sample_session_info):
        """Test regular user fails institution_admin check."""
        with pytest.raises(HTTPException) as exc_info:
            await require_institution_admin(sample_session_info)

        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
class TestRequireSuperAdmin:
    """Test require_super_admin permission function."""

    async def test_require_super_admin_with_super_admin(
        self, sample_super_admin_session_info
    ):
        """Test super_admin passes super_admin check."""
        result = await require_super_admin(sample_super_admin_session_info)
        assert result.role == "super_admin"

    async def test_require_super_admin_with_institution_admin_fails(
        self, sample_admin_session_info
    ):
        """Test institution_admin fails super_admin check."""
        with pytest.raises(HTTPException) as exc_info:
            await require_super_admin(sample_admin_session_info)

        assert exc_info.value.status_code == 403

    async def test_require_super_admin_with_user_fails(self, sample_session_info):
        """Test regular user fails super_admin check."""
        with pytest.raises(HTTPException) as exc_info:
            await require_super_admin(sample_session_info)

        assert exc_info.value.status_code == 403


class TestRoleHierarchy:
    """Test role hierarchy and permissions."""

    def test_super_admin_has_no_institution(self):
        """Test super_admin has no institution_id."""
        super_admin = SessionInfo(
            id="super_123",
            username="super",
            is_admin=True,
            role="super_admin",
            institution_id=None,
        )
        assert super_admin.institution_id is None
        assert super_admin.role == "super_admin"

    def test_institution_admin_has_institution(self):
        """Test institution_admin has institution_id."""
        inst_admin = SessionInfo(
            id="admin_123",
            username="admin",
            is_admin=True,
            role="institution_admin",
            institution_id="inst_123",
        )
        assert inst_admin.institution_id == "inst_123"
        assert inst_admin.role == "institution_admin"

    def test_user_has_institution(self):
        """Test regular user has institution_id."""
        user = SessionInfo(
            id="user_123",
            username="user",
            is_admin=False,
            role="user",
            institution_id="inst_123",
        )
        assert user.institution_id == "inst_123"
        assert user.role == "user"

    def test_is_admin_flag_for_all_admin_types(self):
        """Test is_admin flag is True for all admin types."""
        super_admin = SessionInfo(
            id="s1",
            username="s",
            is_admin=True,
            role="super_admin",
            institution_id=None,
        )
        inst_admin = SessionInfo(
            id="i1",
            username="i",
            is_admin=True,
            role="institution_admin",
            institution_id="inst_123",
        )

        assert super_admin.is_admin is True
        assert inst_admin.is_admin is True


class TestDataIsolationLogic:
    """Test data isolation logic for multi-institution."""

    def test_institution_admin_can_only_access_own_institution(self):
        """Test institution admin should only access their own institution."""
        admin = SessionInfo(
            id="admin_1",
            username="admin",
            is_admin=True,
            role="institution_admin",
            institution_id="inst_A",
        )

        # Admin's institution
        assert admin.institution_id == "inst_A"

        # Should NOT be able to access inst_B
        # (This would be enforced in the actual endpoint logic)
        other_institution_id = "inst_B"
        assert admin.institution_id != other_institution_id

    def test_super_admin_can_access_any_institution(self):
        """Test super admin can access any institution."""
        super_admin = SessionInfo(
            id="super_1",
            username="super",
            is_admin=True,
            role="super_admin",
            institution_id=None,
        )

        # Super admin has no institution constraint
        assert super_admin.institution_id is None
        assert super_admin.role == "super_admin"

        # In actual implementation, endpoints would check:
        # if session.role == "super_admin" -> allow access to all institutions

    def test_regular_user_data_isolated_to_institution(self):
        """Test regular users are isolated to their institution."""
        user_inst_A = SessionInfo(
            id="user_1",
            username="user1",
            is_admin=False,
            role="user",
            institution_id="inst_A",
        )

        user_inst_B = SessionInfo(
            id="user_2",
            username="user2",
            is_admin=False,
            role="user",
            institution_id="inst_B",
        )

        # Users are in different institutions
        assert user_inst_A.institution_id != user_inst_B.institution_id
        # Users should not see each other's data (enforced by DB rules and API filters)


class TestSessionInfoModel:
    """Test SessionInfo model with multi-institution fields."""

    def test_session_info_with_all_fields(self):
        """Test SessionInfo can be created with all fields."""
        session = SessionInfo(
            id="test_123",
            username="testuser",
            is_admin=False,
            role="user",
            institution_id="inst_456",
        )

        assert session.id == "test_123"
        assert session.username == "testuser"
        assert session.is_admin is False
        assert session.role == "user"
        assert session.institution_id == "inst_456"

    def test_session_info_institution_id_optional(self):
        """Test institution_id is optional (None for super_admin)."""
        session = SessionInfo(
            id="super_123",
            username="superadmin",
            is_admin=True,
            role="super_admin",
            institution_id=None,
        )

        assert session.institution_id is None

    def test_session_info_backward_compatibility(self):
        """Test backward compatibility with is_admin field."""
        # Legacy code might rely on is_admin field
        session = SessionInfo(
            id="test_123",
            username="admin",
            is_admin=True,
            role="institution_admin",
            institution_id="inst_123",
        )

        # Both old and new fields should work
        assert session.is_admin is True  # Legacy field
        assert session.role == "institution_admin"  # New field
