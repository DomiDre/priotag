"""
Integration tests for vacation days endpoints.

Tests the vacation days flow with real Redis and PocketBase.

Covers:
Admin Endpoints:
- POST /api/v1/admin/vacation-days - Create vacation day
- POST /api/v1/admin/vacation-days/bulk - Bulk create vacation days
- GET /api/v1/admin/vacation-days - Get all vacation days
- GET /api/v1/admin/vacation-days/{date} - Get vacation day by date
- PUT /api/v1/admin/vacation-days/{date} - Update vacation day
- DELETE /api/v1/admin/vacation-days/{date} - Delete vacation day

User Endpoints:
- GET /api/v1/vacation-days - Get vacation days (read-only)
- GET /api/v1/vacation-days/range - Get vacation days in date range
- GET /api/v1/vacation-days/{date} - Get specific vacation day
"""

from datetime import datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from .conftest import register_and_login_user


@pytest.mark.integration
class TestVacationDaysIntegration:
    """Integration tests for vacation days endpoints."""

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

        # Update role to admin
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
            "username": auth["username"],
            "password": auth["password"],
        }

    # ===================== Admin Endpoints =====================

    def test_create_vacation_day(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test creating a single vacation day."""
        # Setup: Create admin user
        admin_auth = self._register_and_login_admin(test_app, pocketbase_admin_client)

        # Create vacation day
        future_date = (datetime.now() + timedelta(days=100)).strftime("%Y-%m-%d")
        response = test_app.post(
            "/api/v1/admin/vacation-days",
            json={
                "date": future_date,
                "type": "public_holiday",
                "description": "Test Holiday",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # PocketBase returns dates with timestamps (e.g., '2026-02-24 00:00:00.000Z')
        assert data["date"].startswith(future_date)
        assert data["type"] == "public_holiday"
        assert data["description"] == "Test Holiday"
        assert data["created_by"] == admin_auth["username"]

    def test_create_vacation_day_duplicate(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test that creating duplicate vacation day fails."""
        # Setup: Create admin user
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        # Create vacation day
        future_date = (datetime.now() + timedelta(days=101)).strftime("%Y-%m-%d")
        response1 = test_app.post(
            "/api/v1/admin/vacation-days",
            json={
                "date": future_date,
                "type": "vacation",
                "description": "First Entry",
            },
        )
        assert response1.status_code == 200

        # Try to create duplicate
        response2 = test_app.post(
            "/api/v1/admin/vacation-days",
            json={
                "date": future_date,
                "type": "vacation",
                "description": "Duplicate Entry",
            },
        )
        assert response2.status_code == 409

    def test_create_vacation_day_unauthorized(self, test_app: TestClient):
        """Test that non-admin users cannot create vacation days."""
        # Setup: Regular user
        register_and_login_user(test_app)

        future_date = (datetime.now() + timedelta(days=102)).strftime("%Y-%m-%d")
        response = test_app.post(
            "/api/v1/admin/vacation-days",
            json={
                "date": future_date,
                "type": "vacation",
                "description": "Unauthorized",
            },
        )
        assert response.status_code == 403

    def test_bulk_create_vacation_days(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test bulk creating multiple vacation days."""
        # Setup: Create admin user
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        # Create multiple vacation days
        base_date = datetime.now() + timedelta(days=110)
        days = [
            {
                "date": (base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
                "type": "vacation",
                "description": f"Day {i + 1}",
            }
            for i in range(3)
        ]

        response = test_app.post(
            "/api/v1/admin/vacation-days/bulk",
            json={"days": days},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["created"] == 3
        assert data["skipped"] == 0
        assert len(data["errors"]) == 0

    def test_bulk_create_with_duplicates(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test bulk create skips duplicates."""
        # Setup: Create admin user
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        # Create first day
        date1 = (datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d")
        test_app.post(
            "/api/v1/admin/vacation-days",
            json={
                "date": date1,
                "type": "vacation",
                "description": "Existing Day",
            },
        )

        # Bulk create with duplicate
        date2 = (datetime.now() + timedelta(days=121)).strftime("%Y-%m-%d")
        days = [
            {"date": date1, "type": "vacation", "description": "Duplicate"},
            {"date": date2, "type": "vacation", "description": "New Day"},
        ]

        response = test_app.post(
            "/api/v1/admin/vacation-days/bulk",
            json={"days": days},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["created"] == 1
        assert data["skipped"] == 1

    def test_bulk_create_unauthorized(self, test_app: TestClient):
        """Test that non-admin users cannot bulk create vacation days."""
        # Setup: Regular user
        register_and_login_user(test_app)

        future_date = (datetime.now() + timedelta(days=130)).strftime("%Y-%m-%d")
        response = test_app.post(
            "/api/v1/admin/vacation-days/bulk",
            json={
                "days": [
                    {
                        "date": future_date,
                        "type": "vacation",
                        "description": "Unauthorized",
                    }
                ]
            },
        )
        assert response.status_code == 403

    def test_get_all_vacation_days(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test getting all vacation days."""
        # Setup: Create admin user
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        # Create some vacation days
        date1 = (datetime.now() + timedelta(days=140)).strftime("%Y-%m-%d")
        date2 = (datetime.now() + timedelta(days=141)).strftime("%Y-%m-%d")

        for date in [date1, date2]:
            test_app.post(
                "/api/v1/admin/vacation-days",
                json={
                    "date": date,
                    "type": "vacation",
                    "description": "Test",
                },
            )

        # Get all vacation days
        response = test_app.get("/api/v1/admin/vacation-days")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 2

    def test_get_vacation_days_with_filters(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test getting vacation days with year and type filters."""
        # Setup: Create admin user
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        # Create vacation days with different types
        year = datetime.now().year + 1
        test_app.post(
            "/api/v1/admin/vacation-days",
            json={
                "date": f"{year}-06-01",
                "type": "public_holiday",
                "description": "Holiday",
            },
        )
        test_app.post(
            "/api/v1/admin/vacation-days",
            json={
                "date": f"{year}-07-01",
                "type": "vacation",
                "description": "Vacation",
            },
        )

        # Filter by year and type
        response = test_app.get(
            "/api/v1/admin/vacation-days",
            params={"year": year, "type": "public_holiday"},
        )

        assert response.status_code == 200
        data = response.json()

        # Should only get public holidays
        for day in data:
            assert day["type"] == "public_holiday"
            assert day["date"].startswith(str(year))

    def test_get_vacation_days_unauthorized(self, test_app: TestClient):
        """Test that non-admin users cannot get all vacation days via admin endpoint."""
        # Setup: Regular user
        register_and_login_user(test_app)

        response = test_app.get("/api/v1/admin/vacation-days")
        assert response.status_code == 403

    def test_get_vacation_day_by_date(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test getting a specific vacation day by date."""
        # Setup: Create admin user
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        # Create vacation day
        future_date = (datetime.now() + timedelta(days=150)).strftime("%Y-%m-%d")
        test_app.post(
            "/api/v1/admin/vacation-days",
            json={
                "date": future_date,
                "type": "vacation",
                "description": "Specific Day",
            },
        )

        # Get by date
        response = test_app.get(f"/api/v1/admin/vacation-days/{future_date}")

        assert response.status_code == 200
        data = response.json()

        assert data["date"].startswith(future_date)
        assert data["type"] == "vacation"
        assert data["description"] == "Specific Day"

    def test_get_vacation_day_not_found(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test getting non-existent vacation day."""
        # Setup: Create admin user
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        response = test_app.get("/api/v1/admin/vacation-days/2099-12-31")

        assert response.status_code == 404

    def test_get_vacation_day_by_date_unauthorized(self, test_app: TestClient):
        """Test that non-admin users cannot get vacation day via admin endpoint."""
        # Setup: Regular user
        register_and_login_user(test_app)

        response = test_app.get("/api/v1/admin/vacation-days/2025-12-25")
        assert response.status_code == 403

    def test_update_vacation_day(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test updating a vacation day."""
        # Setup: Create admin user
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        # Create vacation day
        future_date = (datetime.now() + timedelta(days=160)).strftime("%Y-%m-%d")
        test_app.post(
            "/api/v1/admin/vacation-days",
            json={
                "date": future_date,
                "type": "vacation",
                "description": "Original",
            },
        )

        # Update vacation day
        response = test_app.put(
            f"/api/v1/admin/vacation-days/{future_date}",
            json={
                "type": "public_holiday",
                "description": "Updated Description",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["type"] == "public_holiday"
        assert data["description"] == "Updated Description"

    def test_update_vacation_day_partial(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test partial update of vacation day (only description)."""
        # Setup: Create admin user
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        # Create vacation day
        future_date = (datetime.now() + timedelta(days=161)).strftime("%Y-%m-%d")
        test_app.post(
            "/api/v1/admin/vacation-days",
            json={
                "date": future_date,
                "type": "vacation",
                "description": "Original",
            },
        )

        # Update only description
        response = test_app.put(
            f"/api/v1/admin/vacation-days/{future_date}",
            json={"description": "New Description"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["type"] == "vacation"  # Unchanged
        assert data["description"] == "New Description"  # Changed

    def test_update_vacation_day_not_found(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test updating non-existent vacation day."""
        # Setup: Create admin user
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        response = test_app.put(
            "/api/v1/admin/vacation-days/2099-12-31",
            json={"description": "Updated"},
        )

        assert response.status_code == 404

    def test_update_vacation_day_unauthorized(self, test_app: TestClient):
        """Test that non-admin users cannot update vacation days."""
        # Setup: Regular user
        register_and_login_user(test_app)

        response = test_app.put(
            "/api/v1/admin/vacation-days/2025-12-25",
            json={"description": "Hacked"},
        )
        assert response.status_code == 403

    def test_delete_vacation_day(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test deleting a vacation day."""
        # Setup: Create admin user
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        # Create vacation day
        future_date = (datetime.now() + timedelta(days=170)).strftime("%Y-%m-%d")
        test_app.post(
            "/api/v1/admin/vacation-days",
            json={
                "date": future_date,
                "type": "vacation",
                "description": "To Delete",
            },
        )

        # Delete vacation day
        response = test_app.delete(f"/api/v1/admin/vacation-days/{future_date}")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "gelöscht" in data["message"].lower()

        # Verify deletion
        get_response = test_app.get(f"/api/v1/admin/vacation-days/{future_date}")
        assert get_response.status_code == 404

    def test_delete_vacation_day_not_found(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test deleting non-existent vacation day."""
        # Setup: Create admin user
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        response = test_app.delete("/api/v1/admin/vacation-days/2099-12-31")

        assert response.status_code == 404

    def test_delete_vacation_day_unauthorized(self, test_app: TestClient):
        """Test that non-admin users cannot delete vacation days."""
        # Setup: Regular user
        register_and_login_user(test_app)

        response = test_app.delete("/api/v1/admin/vacation-days/2025-12-25")
        assert response.status_code == 403

    # ===================== User Endpoints =====================

    def test_user_get_vacation_days(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test users can get vacation days (read-only)."""
        # Setup: Create vacation days as admin
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        future_date = (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d")
        test_app.post(
            "/api/v1/admin/vacation-days",
            json={
                "date": future_date,
                "type": "public_holiday",
                "description": "User Visible",
            },
        )

        # Setup: Create regular user
        register_and_login_user(test_app)

        # Get vacation days as user
        response = test_app.get("/api/v1/vacation-days")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        # Verify user gets simplified response (no created_by, etc.)
        if len(data) > 0:
            assert "date" in data[0]
            assert "type" in data[0]
            assert "description" in data[0]
            assert "created_by" not in data[0]

    def test_user_get_vacation_days_with_filters(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test users can filter vacation days by year, month, type."""
        # Setup: Create vacation days as admin
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        year = datetime.now().year + 1
        test_app.post(
            "/api/v1/admin/vacation-days",
            json={
                "date": f"{year}-08-15",
                "type": "public_holiday",
                "description": "Holiday",
            },
        )

        # Setup: Create regular user
        register_and_login_user(test_app)

        # Filter by year and month
        response = test_app.get(
            "/api/v1/vacation-days",
            params={"year": year, "month": 8},
        )

        assert response.status_code == 200
        data = response.json()

        # Should get August vacation days
        for day in data:
            assert day["date"].startswith(f"{year}-08")

    def test_user_get_vacation_days_in_range(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test users can get vacation days within date range."""
        # Setup: Create vacation days as admin
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        date1 = (datetime.now() + timedelta(days=190)).strftime("%Y-%m-%d")
        date2 = (datetime.now() + timedelta(days=195)).strftime("%Y-%m-%d")
        date3 = (datetime.now() + timedelta(days=200)).strftime("%Y-%m-%d")

        for date in [date1, date2, date3]:
            create_response = test_app.post(
                "/api/v1/admin/vacation-days",
                json={"date": date, "type": "vacation", "description": "Test"},
            )
            assert create_response.status_code == 200

        # Setup: Create regular user
        register_and_login_user(test_app)

        # Get vacation days in range (date1 to date2 inclusive)
        response = test_app.get(
            "/api/v1/vacation-days/range",
            params={"start_date": date1, "end_date": date2},
        )

        assert response.status_code == 200
        data = response.json()

        # Should get date1 and date2 (2 vacation days), but not date3
        # PocketBase returns dates with timestamps, so check with startswith
        matching_dates = [
            day
            for day in data
            if day["date"].startswith(date1) or day["date"].startswith(date2)
        ]
        assert (
            len(matching_dates) >= 2
        ), f"Expected at least 2 vacation days in range, got {len(data)}: {[d['date'] for d in data]}"

        assert any(day["date"].startswith(date1) for day in data)
        assert any(day["date"].startswith(date2) for day in data)
        assert not any(day["date"].startswith(date3) for day in data)

    def test_user_get_vacation_days_in_range_invalid_dates(self, test_app: TestClient):
        """Test date range validation."""
        # Setup: Create regular user
        register_and_login_user(test_app)

        # Invalid date format
        response = test_app.get(
            "/api/v1/vacation-days/range",
            params={"start_date": "invalid", "end_date": "2025-12-31"},
        )

        assert response.status_code == 422

    def test_user_get_vacation_day_by_date(
        self, test_app: TestClient, pocketbase_admin_client: httpx.Client
    ):
        """Test users can get specific vacation day by date."""
        # Setup: Create vacation day as admin
        self._register_and_login_admin(test_app, pocketbase_admin_client)

        future_date = (datetime.now() + timedelta(days=210)).strftime("%Y-%m-%d")
        create_response = test_app.post(
            "/api/v1/admin/vacation-days",
            json={
                "date": future_date,
                "type": "vacation",
                "description": "Specific Day",
            },
        )
        assert create_response.status_code == 200

        # Setup: Create regular user
        register_and_login_user(test_app)

        # Get by date as user
        response = test_app.get(f"/api/v1/vacation-days/{future_date}")

        assert response.status_code == 200
        data = response.json()

        assert data["date"].startswith(future_date)
        assert data["type"] == "vacation"
        assert data["description"] == "Specific Day"
        assert "created_by" not in data  # Simplified response

    def test_user_get_vacation_day_not_found(self, test_app: TestClient):
        """Test user getting non-existent vacation day."""
        # Setup: Create regular user
        register_and_login_user(test_app)

        response = test_app.get("/api/v1/vacation-days/2099-12-31")

        assert response.status_code == 404

    def test_unauthenticated_access_to_user_endpoints(self, test_app: TestClient):
        """Test that unauthenticated requests to user endpoints are rejected."""
        test_app.cookies.clear()

        # Test all user endpoints
        endpoints = [
            ("GET", "/api/v1/vacation-days"),
            (
                "GET",
                "/api/v1/vacation-days/range?start_date=2025-01-01&end_date=2025-12-31",
            ),
            ("GET", "/api/v1/vacation-days/2025-12-25"),
        ]

        for method, endpoint in endpoints:
            response = test_app.get(endpoint)
            assert response.status_code in [401, 403], (
                f"Expected 401/403 for unauthenticated {method} {endpoint}, "
                f"got {response.status_code}"
            )
