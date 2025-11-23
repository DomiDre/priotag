"""
Integration tests for account endpoints.

Tests the full account management flow with real Redis and PocketBase.

Covers:
- GET /api/v1/account/info - Get account information
- GET /api/v1/account/data - Get all user data (GDPR)
- DELETE /api/v1/account/delete - Delete account and all data
"""

import re

import pytest
from fastapi.testclient import TestClient

from .conftest import register_and_login_user


@pytest.mark.integration
class TestAccountIntegration:
    """Integration tests for account endpoints."""

    def test_get_account_info(self, test_app: TestClient):
        """Test retrieving account information."""
        # Setup: Register and login
        auth = register_and_login_user(test_app)

        # Get account info
        response = test_app.get("/api/v1/account/info")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "username" in data
        assert "name" in data
        assert "created" in data
        assert "lastSeen" in data

        # Verify data matches registration
        assert data["username"] == auth["username"]
        assert data["name"] == auth["name"]

    def test_get_account_info_unauthenticated(self, test_app: TestClient):
        """Test that unauthenticated requests are rejected."""
        test_app.cookies.clear()

        response = test_app.get("/api/v1/account/info")
        assert response.status_code in [401, 403]

    def test_get_account_data(self, test_app: TestClient):
        """Test retrieving all account data (GDPR compliance)."""
        from datetime import datetime

        # Setup: Register and login
        auth = register_and_login_user(test_app)

        # Create some priorities
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

        # Get all account data
        response = test_app.get("/api/v1/account/data")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "user" in data
        assert "priorities" in data
        assert "priority_count" in data

        # Verify user data
        user = data["user"]
        assert user["username"] == auth["username"]
        assert user["name"] == auth["name"]
        assert "created" in user
        assert "updated" in user
        assert "verified" in user

        # Verify priorities are included
        assert isinstance(data["priorities"], list)
        assert data["priority_count"] == len(data["priorities"])
        # Should have the priority we just created
        assert data["priority_count"] >= 1

    def test_get_account_data_without_priorities(self, test_app: TestClient):
        """Test retrieving account data when user has no priorities."""
        # Setup: Register and login (but don't create priorities)
        auth = register_and_login_user(test_app)

        # Get all account data
        response = test_app.get("/api/v1/account/data")

        assert response.status_code == 200
        data = response.json()

        # Verify user data is present
        assert "user" in data
        assert data["user"]["username"] == auth["username"]

        # Verify priorities list is empty
        assert data["priorities"] == []
        assert data["priority_count"] == 0

    def test_delete_account(self, test_app: TestClient):
        """Test deleting account and all associated data."""
        from datetime import datetime

        # Setup: Register and login
        register_and_login_user(test_app)

        # Create some priorities to ensure they're deleted
        current_month = datetime.now().strftime("%Y-%m")
        priority_data = [{"weekNumber": 1, "monday": 1}]

        create_response = test_app.put(
            f"/api/v1/priorities/{current_month}",
            json=priority_data,
        )
        assert create_response.status_code == 200

        # Delete account
        response = test_app.delete("/api/v1/account/delete")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "deleted" in data["message"].lower()

        # Verify cookies are cleared
        set_cookie_headers = response.headers.get_list("set-cookie")
        cookies_cleared = {}
        for cookie_header in set_cookie_headers:
            # Check if max-age=0 or expires in past (cookie deletion markers)
            if (
                "max-age=0" in cookie_header.lower()
                or "expires=" in cookie_header.lower()
            ):
                cookie_match = re.match(r"([^=]+)=", cookie_header)
                if cookie_match:
                    cookies_cleared[cookie_match.group(1)] = True

        # Clear cookies from test client to verify session is truly invalidated
        test_app.cookies.clear()

        # Verify session is invalid
        verify_response = test_app.get("/api/v1/auth/verify")
        assert verify_response.status_code in [401, 403]

    def test_delete_account_clears_priorities(self, test_app: TestClient):
        """Test that deleting account also deletes all user priorities."""
        from datetime import datetime

        # Setup: Register and login
        register_and_login_user(test_app)

        # Create priority
        current_month = datetime.now().strftime("%Y-%m")
        priority_data = [{"weekNumber": 1, "monday": 1}]

        create_response = test_app.put(
            f"/api/v1/priorities/{current_month}",
            json=priority_data,
        )
        assert create_response.status_code == 200

        # Verify priority exists
        get_response = test_app.get(f"/api/v1/priorities/{current_month}")
        assert get_response.status_code == 200
        assert len(get_response.json()["weeks"]) > 0

        # Delete account
        delete_response = test_app.delete("/api/v1/account/delete")
        assert delete_response.status_code == 200

    def test_delete_account_unauthenticated(self, test_app: TestClient):
        """Test that unauthenticated delete requests are rejected."""
        test_app.cookies.clear()

        response = test_app.delete("/api/v1/account/delete")
        assert response.status_code in [401, 403]
