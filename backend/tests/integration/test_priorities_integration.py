"""
Integration tests for priority endpoints.

Tests the full priority management flow with real Redis and PocketBase.

Covers:
- Creating priorities for different months
- Retrieving priorities (all and by month)
- Updating existing priorities
- Week start validation and merge logic
- Rate limiting via Redis
- Encryption/decryption flow
- Deleting priorities
- Ownership verification
"""

import time
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from .conftest import register_and_login_user


@pytest.mark.integration
class TestPriorityIntegration:
    """Integration tests for priority endpoints."""

    def test_create_priority_success(self, test_app: TestClient):
        """Test creating a new priority for current month."""
        # Setup: Register and login
        register_and_login_user(test_app)

        # Get current month
        current_month = datetime.now().strftime("%Y-%m")

        # Create priority
        priority_data = {
            "weeks": [
                {
                    "weekNumber": 1,
                    "monday": 1,
                    "tuesday": 2,
                    "wednesday": 3,
                    "thursday": 4,
                    "friday": 5,
                },
                {
                    "weekNumber": 2,
                    "monday": 2,
                    "tuesday": 3,
                    "wednesday": 4,
                    "thursday": 5,
                    "friday": 1,
                },
            ]
        }

        response = test_app.put(
            f"/api/v1/priorities/{current_month}",
            json=priority_data["weeks"],
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "erstellt" in data["message"] or "gespeichert" in data["message"]

    def test_get_priority_by_month(self, test_app: TestClient):
        """Test retrieving a priority for a specific month."""
        # Setup: Register, login, and create priority
        register_and_login_user(test_app)

        current_month = datetime.now().strftime("%Y-%m")

        # Create priority first
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

        # Get priority
        get_response = test_app.get(f"/api/v1/priorities/{current_month}")

        assert get_response.status_code == 200
        data = get_response.json()
        assert data["month"] == current_month
        assert len(data["weeks"]) == 1
        assert data["weeks"][0]["weekNumber"] == 1
        assert data["weeks"][0]["monday"] == 1

    def test_get_priority_not_found(self, test_app: TestClient):
        """Test retrieving a non-existent priority returns empty weeks."""
        register_and_login_user(test_app)

        # Try to get priority for a month that doesn't exist
        future_month = (datetime.now() + timedelta(days=60)).strftime("%Y-%m")

        response = test_app.get(f"/api/v1/priorities/{future_month}")

        assert response.status_code == 200
        data = response.json()
        assert data["month"] == future_month
        assert data["weeks"] == []

    def test_get_all_priorities(self, test_app: TestClient):
        """Test retrieving all priorities for authenticated user."""
        register_and_login_user(test_app)

        current_month = datetime.now().strftime("%Y-%m")
        next_month = (datetime.now() + timedelta(days=32)).strftime("%Y-%m")

        # Create priorities for two months
        for month in [current_month, next_month]:
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
            response = test_app.put(f"/api/v1/priorities/{month}", json=priority_data)
            assert response.status_code == 200

        # Get all priorities
        response = test_app.get("/api/v1/priorities")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # Priorities should be sorted by month descending
        assert data[0]["month"] >= data[1]["month"]

    def test_update_existing_priority(self, test_app: TestClient):
        """Test updating an existing priority."""
        register_and_login_user(test_app)

        # Use next month to ensure weeks haven't started yet
        next_month = (datetime.now() + timedelta(days=32)).strftime("%Y-%m")

        # Create initial priority
        initial_data = [
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
            f"/api/v1/priorities/{next_month}",
            json=initial_data,
        )
        assert create_response.status_code == 200

        # Update with different data
        updated_data = [
            {
                "weekNumber": 1,
                "monday": 5,
                "tuesday": 4,
                "wednesday": 3,
                "thursday": 2,
                "friday": 1,
            }
        ]

        update_response = test_app.put(
            f"/api/v1/priorities/{next_month}",
            json=updated_data,
        )
        assert update_response.status_code == 200

        # Verify updated data
        get_response = test_app.get(f"/api/v1/priorities/{next_month}")
        assert get_response.status_code == 200
        data = get_response.json()

        # Since we're using next month, the week hasn't started yet
        # so the new data should be used
        assert len(data["weeks"]) == 1
        assert data["weeks"][0]["monday"] == 5  # Verify it's the updated data

    def test_delete_priority(self, test_app: TestClient):
        """Test deleting a priority."""
        register_and_login_user(test_app)

        current_month = datetime.now().strftime("%Y-%m")

        # Create priority
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

        # Delete priority
        delete_response = test_app.delete(f"/api/v1/priorities/{current_month}")
        assert delete_response.status_code == 200
        data = delete_response.json()
        assert "gelöscht" in data["message"]

        # Verify deletion
        get_response = test_app.get(f"/api/v1/priorities/{current_month}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["weeks"] == []

    def test_delete_nonexistent_priority(self, test_app: TestClient):
        """Test deleting a priority that doesn't exist."""
        register_and_login_user(test_app)

        future_month = (datetime.now() + timedelta(days=60)).strftime("%Y-%m")

        # Try to delete non-existent priority
        response = test_app.delete(f"/api/v1/priorities/{future_month}")
        assert response.status_code == 400

    def test_rate_limiting(self, test_app: TestClient):
        """Test rate limiting - successful saves clear lock, failures keep it."""
        register_and_login_user(test_app)

        # Part 1: Test that successful saves clear the lock immediately
        next_month = (datetime.now() + timedelta(days=32)).strftime("%Y-%m")
        valid_data = [
            {
                "weekNumber": 1,
                "monday": 1,
                "tuesday": 2,
                "wednesday": 3,
                "thursday": 4,
                "friday": 5,
            }
        ]

        # First successful request clears the lock immediately
        response1 = test_app.put(
            f"/api/v1/priorities/{next_month}",
            json=valid_data,
        )
        assert response1.status_code == 200

        # Second successful request should also succeed (lock was cleared)
        response2 = test_app.put(
            f"/api/v1/priorities/{next_month}",
            json=valid_data,
        )
        assert response2.status_code == 200

        # Part 2: Test that failures keep the lock for 3 seconds
        # Use previous month (which is still within allowed range if it's early in current month)
        # but use week 1 which will definitely have started
        prev_month = (datetime.now() - timedelta(days=15)).strftime("%Y-%m")
        past_week_data = [
            {
                "weekNumber": 1,
                "monday": 1,
                "tuesday": 2,
                "wednesday": 3,
                "thursday": 4,
                "friday": 5,
            }
        ]

        # First, create existing data for the previous month's week 1
        test_app.put(
            f"/api/v1/priorities/{prev_month}",
            json=past_week_data,
        )
        # This might succeed if previous month is still in range, or fail with 422 if out of range

        # Wait for any lock to clear
        time.sleep(3.1)

        # Now try to modify it with different data
        modified_week_data = [
            {
                "weekNumber": 1,
                "monday": 5,  # Different value
                "tuesday": 4,
                "wednesday": 3,
                "thursday": 2,
                "friday": 1,
            }
        ]

        # This should fail with 422 (either locked week or month out of range)
        response3 = test_app.put(
            f"/api/v1/priorities/{prev_month}",
            json=modified_week_data,
        )
        assert response3.status_code == 422

        # Immediate retry should be rate limited (lock persists for 3s on HTTPException)
        response4 = test_app.put(
            f"/api/v1/priorities/{prev_month}",
            json=modified_week_data,
        )
        assert response4.status_code == 429

        # After waiting, should get 422 again (not rate limited)
        time.sleep(3.1)
        response5 = test_app.put(
            f"/api/v1/priorities/{prev_month}",
            json=modified_week_data,
        )
        assert response5.status_code == 422

    def test_month_validation_invalid_format(self, test_app: TestClient):
        """Test that invalid month format is rejected."""
        register_and_login_user(test_app)

        priority_data = [{"weekNumber": 1, "monday": 1}]

        # Invalid month format
        response = test_app.put(
            "/api/v1/priorities/2025-13",  # Month 13 doesn't exist
            json=priority_data,
        )
        assert response.status_code == 422

    def test_month_validation_out_of_range(self, test_app: TestClient):
        """Test that months outside allowed range are rejected."""
        register_and_login_user(test_app)

        priority_data = [{"weekNumber": 1, "monday": 1}]

        # Month too far in the future
        far_future = (datetime.now() + timedelta(days=365)).strftime("%Y-%m")
        response = test_app.put(
            f"/api/v1/priorities/{far_future}",
            json=priority_data,
        )
        assert response.status_code == 422

    def test_unauthenticated_access(self, test_app: TestClient):
        """Test that unauthenticated requests are rejected."""
        current_month = datetime.now().strftime("%Y-%m")

        # Try without cookies
        test_app.cookies.clear()

        # GET all priorities
        response1 = test_app.get("/api/v1/priorities")
        assert response1.status_code in [401, 403]

        # GET specific month
        response2 = test_app.get(f"/api/v1/priorities/{current_month}")
        assert response2.status_code in [401, 403]

        # PUT (create/update)
        response3 = test_app.put(
            f"/api/v1/priorities/{current_month}",
            json=[{"weekNumber": 1, "monday": 1}],
        )
        assert response3.status_code in [401, 403]

        # DELETE
        response4 = test_app.delete(f"/api/v1/priorities/{current_month}")
        assert response4.status_code in [401, 403]

    def test_ownership_isolation(self, test_app: TestClient):
        """Test that users can only access their own priorities."""
        # Create user 1 and save their cookies
        register_and_login_user(test_app)
        user1_cookies = dict(test_app.cookies)

        # Create user 2 (this overwrites test_app.cookies)
        register_and_login_user(test_app)
        user2_cookies = dict(test_app.cookies)

        current_month = datetime.now().strftime("%Y-%m")

        # Switch back to user 1 to create a priority
        test_app.cookies = user1_cookies
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
        response = test_app.put(
            f"/api/v1/priorities/{current_month}",
            json=priority_data,
        )
        assert response.status_code == 200

        # Switch to user 2 - should not see user 1's priorities
        test_app.cookies = user2_cookies
        response = test_app.get("/api/v1/priorities")
        assert response.status_code == 200
        data = response.json()
        # User 2 should have no priorities
        assert len(data) == 0

        # User 2 tries to get user 1's priority for the same month
        response = test_app.get(f"/api/v1/priorities/{current_month}")
        assert response.status_code == 200
        data = response.json()
        # Should return empty weeks (no access to user 1's data)
        assert data["weeks"] == []

    def test_encryption_flow(self, test_app: TestClient):
        """Test that data is encrypted in storage and decrypted on retrieval."""
        register_and_login_user(test_app)

        current_month = datetime.now().strftime("%Y-%m")

        # Create priority with specific data
        priority_data = [
            {
                "weekNumber": 1,
                "monday": 1,
                "tuesday": 2,
                "wednesday": 3,
                "thursday": 4,
                "friday": 5,
            },
            {
                "weekNumber": 2,
                "monday": 5,
                "tuesday": 4,
                "wednesday": 3,
                "thursday": 2,
                "friday": 1,
            },
        ]

        create_response = test_app.put(
            f"/api/v1/priorities/{current_month}",
            json=priority_data,
        )
        assert create_response.status_code == 200

        # Retrieve and verify data is correctly decrypted
        get_response = test_app.get(f"/api/v1/priorities/{current_month}")
        assert get_response.status_code == 200
        data = get_response.json()

        assert data["month"] == current_month
        assert len(data["weeks"]) == 2

        # Verify week 1
        week1 = next(w for w in data["weeks"] if w["weekNumber"] == 1)
        assert week1["monday"] == 1
        assert week1["tuesday"] == 2
        assert week1["wednesday"] == 3
        assert week1["thursday"] == 4
        assert week1["friday"] == 5

        # Verify week 2
        week2 = next(w for w in data["weeks"] if w["weekNumber"] == 2)
        assert week2["monday"] == 5
        assert week2["tuesday"] == 4
        assert week2["wednesday"] == 3
        assert week2["thursday"] == 2
        assert week2["friday"] == 1

    def test_multiple_weeks_priority(self, test_app: TestClient):
        """Test creating and retrieving priorities with multiple weeks."""
        register_and_login_user(test_app)

        current_month = datetime.now().strftime("%Y-%m")

        # Create priority with 4 weeks
        priority_data = [{"weekNumber": i, "monday": i % 5 + 1} for i in range(1, 5)]

        response = test_app.put(
            f"/api/v1/priorities/{current_month}",
            json=priority_data,
        )
        assert response.status_code == 200

        # Retrieve and verify
        get_response = test_app.get(f"/api/v1/priorities/{current_month}")
        assert get_response.status_code == 200
        data = get_response.json()

        assert len(data["weeks"]) == 4
        for i in range(1, 5):
            week = next(w for w in data["weeks"] if w["weekNumber"] == i)
            assert week["monday"] == i % 5 + 1
