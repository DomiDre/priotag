"""
Integration tests for super admin endpoints.

Tests the full super admin flow with real PocketBase.

Covers:
- GET /api/v1/admin/super/institutions - List all institutions
- POST /api/v1/admin/super/institutions - Create institution
- PUT /api/v1/admin/super/institutions/{id} - Update institution
- GET /api/v1/admin/super/institutions/{institution_id}/users - List institution users
- PATCH /api/v1/admin/super/users/{user_id}/promote - Promote user to institution_admin
- PATCH /api/v1/admin/super/users/{user_id}/demote - Demote user from institution_admin
"""

import secrets

import httpx
import pytest
from starlette.testclient import TestClient

from .conftest import register_and_login_user

# Constants
DEFAULT_TEST_PASSWORD = "SecurePassword123!"

# Test RSA public key for creating institutions
TEST_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAweEop1uAnEVnfYbWVKIy
2JRFKvLEuR9j9kbr0P1tt4DIj2IiGttUDnXU/DoQDZSXyVR7o250gMv+xrgmCjBU
eU2fMJZ9+uRVXYNXLSpoHleMEp+2MfSJlvWow6xzIb02rtdq/5sjIQ0BUcw+3f5w
OoZlzk/bySJbEe67HUNOtOJM7Fsig9KfR8wrrnh+DJO51h/1AH2WE9yoM0wQWeyJ
KbJ9ka5X/EXrmErA1GA1H4hIk5pC7B9M41jwF6ZaT1jhKVIqVX2QFiE7RvGvVn5m
De5kT8SdtebGOcv7OL8TC55KJmpopsKc0Fr29aLM+n2n/aujgFegQcN7bcCVXPNg
4wIDAQAB
-----END PUBLIC KEY-----"""


def _get_user_by_username(username: str, pocketbase_admin_client: httpx.Client) -> dict:
    """Helper: Get user record by username."""
    response = pocketbase_admin_client.get(
        "/api/collections/users/records",
        params={"filter": f'username="{username}"'},
    )
    assert response.status_code == 200, f"Failed to get user: {response.text}"
    users = response.json()["items"]
    assert len(users) == 1, f"Expected 1 user, found {len(users)}"
    return users[0]


def _elevate_to_super_admin(
    username: str, pocketbase_admin_client: httpx.Client
) -> None:
    """Helper: Elevate a user to super_admin role."""
    user = _get_user_by_username(username, pocketbase_admin_client)
    response = pocketbase_admin_client.patch(
        f"/api/collections/users/records/{user['id']}",
        json={"role": "super_admin", "institution_id": None},
    )
    assert response.status_code == 200, f"Failed to elevate user: {response.text}"


def _login_as(
    test_app: TestClient, username: str, password: str = DEFAULT_TEST_PASSWORD
):
    """Helper: Login as a specific user and assert success."""
    response = test_app.post(
        "/api/v1/auth/login",
        json={
            "identity": username,
            "password": password,
            "keep_logged_in": False,
        },
    )
    assert response.status_code == 200, f"Login failed: {response.text}"


def _create_test_institution(
    pocketbase_admin_client: httpx.Client, short_code: str
) -> dict:
    """Helper: Create a test institution."""
    response = pocketbase_admin_client.post(
        "/api/collections/institutions/records",
        json={
            "name": f"Test Institution {short_code}",
            "short_code": short_code,
            "registration_magic_word": f"magic_{short_code}",
            "admin_public_key": TEST_PUBLIC_KEY,
            "active": True,
        },
    )
    assert response.status_code == 200, f"Failed to create institution: {response.text}"
    return response.json()


def _setup_super_admin(
    test_app: TestClient, pocketbase_admin_client: httpx.Client
) -> str:
    """Helper: Register a user, elevate to super_admin, and login. Returns username."""
    username = f"superadmin_{secrets.token_hex(4)}"
    register_and_login_user(test_app, username)
    _elevate_to_super_admin(username, pocketbase_admin_client)
    _login_as(test_app, username)
    return username


@pytest.mark.integration
class TestSuperAdminIntegration:
    """Integration tests for super admin endpoints."""

    def test_list_all_institutions(
        self,
        test_app: TestClient,
        pocketbase_admin_client: httpx.Client,
    ):
        """Test listing all institutions as super admin."""
        _setup_super_admin(test_app, pocketbase_admin_client)

        # List all institutions
        response = test_app.get("/api/v1/admin/super/institutions")
        assert response.status_code == 200
        institutions = response.json()
        assert isinstance(institutions, list)
        assert len(institutions) > 0

        # Verify institution structure
        inst = institutions[0]
        assert "id" in inst
        assert "name" in inst
        assert "short_code" in inst
        assert "registration_magic_word" in inst
        assert "active" in inst

    def test_create_institution(
        self,
        test_app: TestClient,
        pocketbase_admin_client: httpx.Client,
    ):
        """Test creating a new institution as super admin."""
        _setup_super_admin(test_app, pocketbase_admin_client)

        # Create new institution
        new_short_code = f"TEST_{secrets.token_hex(4).upper()}"
        response = test_app.post(
            "/api/v1/admin/super/institutions",
            json={
                "name": f"Test Institution {new_short_code}",
                "short_code": new_short_code,
                "registration_magic_word": f"magic_{new_short_code}",
                "admin_public_key": TEST_PUBLIC_KEY,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == f"Test Institution {new_short_code}"
        assert data["short_code"] == new_short_code
        assert "active" in data  # Just verify the field exists

    def test_update_institution(
        self,
        test_app: TestClient,
        pocketbase_admin_client: httpx.Client,
    ):
        """Test updating an institution as super admin."""
        _setup_super_admin(test_app, pocketbase_admin_client)

        # Create a test institution
        test_inst = _create_test_institution(
            pocketbase_admin_client, f"UPD_{secrets.token_hex(4).upper()}"
        )

        # Update institution
        response = test_app.put(
            f"/api/v1/admin/super/institutions/{test_inst['id']}",
            json={
                "name": "Updated Institution Name",
                "active": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Institution Name"
        assert data["active"] is False

    def test_list_institution_users(
        self,
        test_app: TestClient,
        pocketbase_admin_client: httpx.Client,
    ):
        """Test listing users of an institution as super admin."""
        super_admin = _setup_super_admin(test_app, pocketbase_admin_client)

        # Register another user in the same institution
        other_username = f"user_{secrets.token_hex(4)}"
        register_and_login_user(test_app, other_username)

        # Get the user's institution_id
        other_user = _get_user_by_username(other_username, pocketbase_admin_client)

        # Login again as super admin (after registering other user, which changed the session)
        _login_as(test_app, super_admin)

        # List users of the institution
        response = test_app.get(
            f"/api/v1/admin/super/institutions/{other_user['institution_id']}/users"
        )
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        assert len(users) >= 1  # At least the newly registered user

        # Verify user structure
        user = users[0]
        assert "id" in user
        assert "username" in user
        assert "role" in user
        assert "institution_id" in user

    def test_promote_user_to_institution_admin(
        self,
        test_app: TestClient,
        pocketbase_admin_client: httpx.Client,
    ):
        """Test promoting a user to institution_admin as super admin."""
        super_admin = _setup_super_admin(test_app, pocketbase_admin_client)

        # Register a regular user
        target_username = f"user_{secrets.token_hex(4)}"
        register_and_login_user(test_app, target_username)

        # Get user and verify they're a regular user
        target_user = _get_user_by_username(target_username, pocketbase_admin_client)
        assert target_user.get("role", "user") == "user"

        # Login again as super admin (after registering target user, which changed the session)
        _login_as(test_app, super_admin)

        # Promote user to institution_admin
        response = test_app.patch(
            f"/api/v1/admin/super/users/{target_user['id']}/promote"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "promoted to institution_admin" in data["message"]
        assert data["user"]["role"] == "institution_admin"

    def test_demote_user_from_institution_admin(
        self,
        test_app: TestClient,
        pocketbase_admin_client: httpx.Client,
    ):
        """Test demoting a user from institution_admin as super admin."""
        super_admin = _setup_super_admin(test_app, pocketbase_admin_client)

        # Register a user and elevate them to institution_admin
        target_username = f"instadmin_{secrets.token_hex(4)}"
        register_and_login_user(test_app, target_username)

        # Get user and elevate to institution_admin
        target_user = _get_user_by_username(target_username, pocketbase_admin_client)
        response = pocketbase_admin_client.patch(
            f"/api/collections/users/records/{target_user['id']}",
            json={"role": "institution_admin"},
        )
        assert response.status_code == 200

        # Login again as super admin (after registering target user, which changed the session)
        _login_as(test_app, super_admin)

        # Demote user back to regular user
        response = test_app.patch(
            f"/api/v1/admin/super/users/{target_user['id']}/demote"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "demoted to regular user" in data["message"]
        assert data["user"]["role"] == "user"

    def test_promote_user_without_institution_fails(
        self,
        test_app: TestClient,
        pocketbase_admin_client: httpx.Client,
    ):
        """Test that promoting a user without an institution fails."""
        super_admin = _setup_super_admin(test_app, pocketbase_admin_client)

        # Register a user
        target_username = f"user_{secrets.token_hex(4)}"
        register_and_login_user(test_app, target_username)

        # Get user and remove institution_id
        target_user = _get_user_by_username(target_username, pocketbase_admin_client)
        response = pocketbase_admin_client.patch(
            f"/api/collections/users/records/{target_user['id']}",
            json={"institution_id": None},
        )
        assert response.status_code == 200

        # Login again as super admin (after registering target user, which changed the session)
        _login_as(test_app, super_admin)

        # Try to promote user (should fail)
        response = test_app.patch(
            f"/api/v1/admin/super/users/{target_user['id']}/promote"
        )
        assert response.status_code == 400
        assert "must be associated with an institution" in response.json()["detail"]

    def test_demote_super_admin_fails(
        self,
        test_app: TestClient,
        pocketbase_admin_client: httpx.Client,
    ):
        """Test that demoting a super_admin fails."""
        super_admin = _setup_super_admin(test_app, pocketbase_admin_client)

        # Get super admin user ID
        super_admin_user = _get_user_by_username(super_admin, pocketbase_admin_client)

        # Try to demote super_admin (should fail)
        response = test_app.patch(
            f"/api/v1/admin/super/users/{super_admin_user['id']}/demote"
        )
        assert response.status_code == 400
        assert "Cannot demote super_admin" in response.json()["detail"]

    def test_non_super_admin_cannot_access_endpoints(
        self,
        test_app: TestClient,
        pocketbase_admin_client: httpx.Client,
    ):
        """Test that non-super admins cannot access super admin endpoints."""
        # Register and elevate user to institution_admin (not super_admin)
        username = f"instadmin_{secrets.token_hex(4)}"
        register_and_login_user(test_app, username)

        # Elevate to institution_admin
        user = _get_user_by_username(username, pocketbase_admin_client)
        response = pocketbase_admin_client.patch(
            f"/api/collections/users/records/{user['id']}",
            json={"role": "institution_admin"},
        )
        assert response.status_code == 200

        # Login again after elevation
        _login_as(test_app, username)

        # Try to access super admin endpoint (should fail)
        response = test_app.get("/api/v1/admin/super/institutions")
        assert response.status_code == 403
        assert "Super-Administrator-Rechte erforderlich" in response.json()["detail"]
