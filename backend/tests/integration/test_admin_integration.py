"""
Integration tests for admin endpoints.

Tests the full admin flow with real Redis and PocketBase.

Covers:
- GET /api/v1/admin/magic-word-info - Get magic word information
- POST /api/v1/admin/update-magic-word - Update magic word
- GET /api/v1/admin/total-users - Get total user count
- GET /api/v1/admin/users/{month} - Get user submissions for month
- GET /api/v1/admin/users/info/{user_id} - Get user info
- POST /api/v1/admin/manual-priority - Create/update manual priority
- GET /api/v1/admin/manual-entries/{month} - Get manual entries
- DELETE /api/v1/admin/manual-entry/{month}/{identifier} - Delete manual entry
"""

import secrets
from datetime import datetime

import httpx
import pytest
from fastapi.testclient import TestClient

from .conftest import register_and_login_user


@pytest.mark.integration
class TestAdminIntegration:
    """Integration tests for admin endpoints."""

    def _elevate_to_admin(
        self, username: str, pocketbase_admin_client: httpx.Client
    ) -> None:
        """Helper: Elevate a user to admin role."""
        # Find user by username
        response = pocketbase_admin_client.get(
            "/api/collections/users/records",
            params={"filter": f'username="{username}"'},
        )
        assert response.status_code == 200
        users = response.json()["items"]
        assert len(users) == 1

        user_id = users[0]["id"]

        # Update role to institution_admin
        response = pocketbase_admin_client.patch(
            f"/api/collections/users/records/{user_id}",
            json={"role": "institution_admin"},
        )
        assert response.status_code == 200

    def _register_and_login_admin(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ) -> dict:
        """Helper: Register a user, elevate to admin, and login."""
        auth = register_and_login_user(test_app)

        # Elevate to admin
        self._elevate_to_admin(auth["username"], pocketbase_admin_client)

        # Login again to get admin session
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": auth["username"],
                "password": auth["password"],
            },
        )
        assert login_response.status_code == 200

        return {
            "cookies": dict(login_response.cookies),
            "username": auth["username"],
            "password": auth["password"],
        }

    def test_get_total_users(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test getting total user count."""
        # Setup: Create admin user and login
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        # Get total users
        response = test_app.get("/api/v1/admin/total-users")

        assert response.status_code == 200
        data = response.json()

        assert "totalUsers" in data
        assert isinstance(data["totalUsers"], int)
        assert data["totalUsers"] >= 1  # At least the admin user

    def test_get_total_users_unauthorized(self, test_app: TestClient):
        """Test that non-admin users cannot get total user count."""
        # Setup: Regular user
        register_and_login_user(test_app)

        response = test_app.get("/api/v1/admin/total-users")
        assert response.status_code == 403

    def test_get_user_submissions(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test retrieving user submissions for a month."""
        # Setup: Create regular user with priorities
        user_auth = register_and_login_user(test_app)

        current_month = datetime.now().strftime("%Y-%m")
        priority_data = [
            {
                "weekNumber": 1,
                "monday": 1,
                "tuesday": 2,
                "wednesday": 3,
                "thursday": 4,
                "friday": 5,
            }
        ]

        create_response = test_app.put(
            f"/api/v1/priorities/{current_month}",
            json=priority_data,
        )
        assert create_response.status_code == 200

        # Setup: Create admin and login
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        # Get user submissions for current month
        response = test_app.get(f"/api/v1/admin/users/{current_month}")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 1

        # Verify submission structure
        submission = next(
            (s for s in data if s["userName"] == user_auth["username"]),
            None,
        )
        assert submission is not None
        assert "adminWrappedDek" in submission
        assert "userName" in submission
        assert "month" in submission
        assert submission["month"] == current_month
        assert "userEncryptedFields" in submission
        assert "prioritiesEncryptedFields" in submission

    def test_get_user_submissions_empty_month(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test retrieving submissions for a month with no data."""
        # Setup: Create admin and login
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        # Get submissions for future month (no data)
        future_month = "2099-12"
        response = test_app.get(f"/api/v1/admin/users/{future_month}")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_user_submissions_unauthorized(self, test_app: TestClient):
        """Test that non-admin users cannot get user submissions."""
        # Setup: Regular user
        register_and_login_user(test_app)

        current_month = datetime.now().strftime("%Y-%m")
        response = test_app.get(f"/api/v1/admin/users/{current_month}")
        assert response.status_code == 403

    def test_get_user_info(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test retrieving user info by user ID."""
        # Setup: Create a regular user
        user_auth = register_and_login_user(test_app)

        # Setup: Create admin and login
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        # Get user info
        response = test_app.get(f"/api/v1/admin/users/info/{user_auth['username']}")

        assert response.status_code == 200
        data = response.json()

        assert "username" in data
        assert data["username"] == user_auth["username"]
        assert "admin_wrapped_dek" in data
        assert "encrypted_fields" in data
        assert "created" in data

    def test_get_user_info_not_found(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test retrieving info for non-existent user."""
        # Setup: Create admin and login
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        # Try to get non-existent user
        response = test_app.get("/api/v1/admin/users/info/nonexistent_user_12345")

        assert response.status_code == 404

    def test_get_user_info_unauthorized(self, test_app: TestClient):
        """Test that non-admin users cannot get user info."""
        # Setup: Regular user
        auth = register_and_login_user(test_app)

        response = test_app.get(f"/api/v1/admin/users/info/{auth['username']}")
        assert response.status_code == 403

    def test_create_manual_priority(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test creating a manual priority entry."""
        # Setup: Create admin and login
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        current_month = datetime.now().strftime("%Y-%m")
        identifier = f"paper_{secrets.token_hex(4)}"

        # Create manual priority
        response = test_app.post(
            "/api/v1/admin/manual-priority",
            json={
                "identifier": identifier,
                "month": current_month,
                "weeks": [
                    {
                        "weekNumber": 1,
                        "monday": 1,
                        "tuesday": 2,
                        "wednesday": 3,
                        "thursday": 4,
                        "friday": 5,
                    }
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "erstellt" in data["message"].lower()
        assert data["identifier"] == identifier
        assert data["month"] == current_month

    def test_update_manual_priority(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test updating an existing manual priority entry."""
        # Setup: Create admin and login
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        current_month = datetime.now().strftime("%Y-%m")
        identifier = f"paper_{secrets.token_hex(4)}"

        # Create initial entry
        create_response = test_app.post(
            "/api/v1/admin/manual-priority",
            json={
                "identifier": identifier,
                "month": current_month,
                "weeks": [{"weekNumber": 1, "monday": 1}],
            },
        )
        assert create_response.status_code == 200

        # Update the entry
        update_response = test_app.post(
            "/api/v1/admin/manual-priority",
            json={
                "identifier": identifier,
                "month": current_month,
                "weeks": [
                    {
                        "weekNumber": 1,
                        "monday": 5,
                        "tuesday": 4,
                        "wednesday": 3,
                        "thursday": 2,
                        "friday": 1,
                    }
                ],
            },
        )

        assert update_response.status_code == 200
        data = update_response.json()

        assert data["success"] is True
        assert "aktualisiert" in data["message"].lower()

    def test_create_manual_priority_validation(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test manual priority validation."""
        # Setup: Create admin and login
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        current_month = datetime.now().strftime("%Y-%m")

        # Test empty identifier
        response1 = test_app.post(
            "/api/v1/admin/manual-priority",
            json={
                "identifier": "   ",
                "month": current_month,
                "weeks": [{"weekNumber": 1, "monday": 1}],
            },
        )
        assert response1.status_code == 422

        # Test no priority data
        response2 = test_app.post(
            "/api/v1/admin/manual-priority",
            json={
                "identifier": "test",
                "month": current_month,
                "weeks": [{"weekNumber": 1}],  # No days set
            },
        )
        assert response2.status_code == 422

    def test_create_manual_priority_unauthorized(self, test_app: TestClient):
        """Test that non-admin users cannot create manual priorities."""
        # Setup: Regular user
        register_and_login_user(test_app)

        current_month = datetime.now().strftime("%Y-%m")
        response = test_app.post(
            "/api/v1/admin/manual-priority",
            json={
                "identifier": "paper_1",
                "month": current_month,
                "weeks": [{"weekNumber": 1, "monday": 1}],
            },
        )
        assert response.status_code == 403

    def test_get_manual_entries(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test retrieving manual entries for a month."""
        # Setup: Create admin and login
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        current_month = datetime.now().strftime("%Y-%m")
        identifier = f"paper_{secrets.token_hex(4)}"

        # Create a manual entry
        create_response = test_app.post(
            "/api/v1/admin/manual-priority",
            json={
                "identifier": identifier,
                "month": current_month,
                "weeks": [{"weekNumber": 1, "monday": 1}],
            },
        )
        assert create_response.status_code == 200

        # Get manual entries
        response = test_app.get(f"/api/v1/admin/manual-entries/{current_month}")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        # Should find our manual entry
        assert len(data) >= 1

        # Verify entry structure
        entry = data[0]
        assert "adminWrappedDek" in entry
        assert "identifier" in entry
        assert "month" in entry
        assert entry["month"] == current_month
        assert "prioritiesEncryptedFields" in entry

    def test_get_manual_entries_empty(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test retrieving manual entries for month with no entries."""
        from datetime import datetime, timedelta

        # Setup: Create admin and login
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        # Get entries for next month (no data, but within valid range)
        next_month = (datetime.now() + timedelta(days=32)).strftime("%Y-%m")
        response = test_app.get(f"/api/v1/admin/manual-entries/{next_month}")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_manual_entries_unauthorized(self, test_app: TestClient):
        """Test that non-admin users cannot get manual entries."""
        # Setup: Regular user
        register_and_login_user(test_app)

        current_month = datetime.now().strftime("%Y-%m")
        response = test_app.get(f"/api/v1/admin/manual-entries/{current_month}")
        assert response.status_code == 403

    def test_delete_manual_entry(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test deleting a manual entry."""
        # Setup: Create admin and login
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        current_month = datetime.now().strftime("%Y-%m")
        identifier = f"paper_{secrets.token_hex(4)}"

        # Create a manual entry
        create_response = test_app.post(
            "/api/v1/admin/manual-priority",
            json={
                "identifier": identifier,
                "month": current_month,
                "weeks": [{"weekNumber": 1, "monday": 1}],
            },
        )
        assert create_response.status_code == 200

        # Delete the entry using the identifier we created it with
        delete_response = test_app.delete(
            f"/api/v1/admin/manual-entry/{current_month}/{identifier}"
        )

        assert delete_response.status_code == 200
        data = delete_response.json()

        assert data["success"] is True
        assert "gelöscht" in data["message"].lower()

    def test_delete_manual_entry_not_found(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test deleting a non-existent manual entry."""
        # Setup: Create admin and login
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        current_month = datetime.now().strftime("%Y-%m")
        response = test_app.delete(
            f"/api/v1/admin/manual-entry/{current_month}/nonexistent_id"
        )

        assert response.status_code == 404

    def test_delete_manual_entry_unauthorized(self, test_app: TestClient):
        """Test that non-admin users cannot delete manual entries."""
        # Setup: Regular user
        register_and_login_user(test_app)

        current_month = datetime.now().strftime("%Y-%m")
        response = test_app.delete(
            f"/api/v1/admin/manual-entry/{current_month}/some_id"
        )
        assert response.status_code == 403

    def test_unauthenticated_access_to_admin_endpoints(self, test_app: TestClient):
        """Test that unauthenticated requests to admin endpoints are rejected."""
        test_app.cookies.clear()

        current_month = datetime.now().strftime("%Y-%m")

        # Test existing admin endpoints
        endpoints: list[tuple[str, str, dict] | tuple[str, str]] = [
            ("GET", "/api/v1/admin/total-users"),
            ("GET", f"/api/v1/admin/users/{current_month}"),
            ("GET", "/api/v1/admin/users/info/test_user"),
            (
                "POST",
                "/api/v1/admin/manual-priority",
                {
                    "identifier": "test",
                    "month": current_month,
                    "weeks": [{"weekNumber": 1, "monday": 1}],
                },
            ),
            ("GET", f"/api/v1/admin/manual-entries/{current_month}"),
            ("DELETE", f"/api/v1/admin/manual-entry/{current_month}/test_id"),
        ]

        for method, endpoint, *args in endpoints:
            json_data = args[0] if args else None
            if method == "GET":
                response = test_app.get(endpoint)
            elif method == "POST":
                response = test_app.post(endpoint, json=json_data)
            elif method == "DELETE":
                response = test_app.delete(endpoint)

            assert response.status_code in [401, 403], (
                f"Expected 401/403 for unauthenticated {method} {endpoint}, "
                f"got {response.status_code}"
            )
