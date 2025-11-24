"""
Security integration tests for multi-institution data isolation.

These tests verify that institution admins CANNOT access other institutions' data
and that data isolation is properly enforced at the API level.
"""

from datetime import datetime, timedelta

import pytest

from .conftest import (
    create_institution_with_rsa_key,
    login_with_pocketbase,
    register_and_elevate_to_admin,
)


def create_user(
    test_app,
    identity,
    password,
    name,
    institution_code,
    magic_word,
    keep_logged_in=False,
):
    """Helper to create a user and return the response."""
    response = test_app.post(
        "/api/v1/auth/register-qr",
        json={
            "identity": identity,
            "password": password,
            "passwordConfirm": password,
            "name": name,
            "magic_word": magic_word,
            "institution_short_code": institution_code,
            "keep_logged_in": keep_logged_in,
        },
    )
    assert response.status_code == 200
    return response


@pytest.mark.integration
class TestInstitutionDataIsolation:
    """Test that institution admins cannot access other institutions' data."""

    def test_institution_admin_cannot_see_other_institutions_users(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that institution admin A cannot see users from institution B.

        This is a CRITICAL security test.
        """
        # Create two institutions
        create_institution_with_rsa_key(
            pocketbase_admin_client, "Institution A", "INST_A", "MagicA123"
        )
        create_institution_with_rsa_key(
            pocketbase_admin_client, "Institution B", "INST_B", "MagicB456"
        )

        # Register user in Institution A
        create_user(test_app, "user_a", "PassA123!", "User A", "INST_A", "MagicA123")

        # Register and elevate admin in Institution A
        register_and_elevate_to_admin(
            test_app=test_app,
            pocketbase_admin_client=pocketbase_admin_client,
            username="admin_a",
            password="AdminA123!",
            name="Admin A",
            institution_short_code="INST_A",
            magic_word="MagicA123",
        )

        # Register user in Institution B
        user_b_response = create_user(
            test_app, "user_b", "PassB123!", "User B", "INST_B", "MagicB456"
        )
        user_b_response_data = user_b_response.json()

        # Get user B's actual user ID and username from PocketBase
        users_b = pocketbase_admin_client.get(
            "/api/collections/users/records",
            params={"filter": f'username="{user_b_response_data["username"]}"'},
        ).json()
        user_b_id = users_b["items"][0]["id"]
        user_b_username = users_b["items"][0]["username"]

        # Try to access user B's details (should fail - different institution)
        user_b_detail_response = test_app.get(f"/api/v1/admin/users/detail/{user_b_id}")
        assert user_b_detail_response.status_code in [404, 403]

        # Try to access user B by username (should return 404/no access)
        user_b_info_response = test_app.get(
            f"/api/v1/admin/users/info/{user_b_username}"
        )
        assert user_b_info_response.status_code in [404, 403]

    def test_institution_admin_cannot_see_other_institutions_priorities(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that institution admin A cannot see priorities from institution B.

        This is a CRITICAL security test.
        """
        # Create two institutions
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution A Priority Test",
            "INST_A_PRIO",
            "MagicA789",
        )
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution B Priority Test",
            "INST_B_PRIO",
            "MagicB789",
        )

        # Register user in Institution B and create a priority
        user_b_response = create_user(
            test_app,
            "user_b_prio",
            "PassB789!",
            "User B Priority",
            "INST_B_PRIO",
            "MagicB789",
            keep_logged_in=True,
        )
        user_b_id = user_b_response.json()["id"]

        # User B creates a priority
        test_prio_month = (datetime.now() + timedelta(days=35)).strftime("%Y-%m")
        priority_response = test_app.put(
            f"/api/v1/priorities/{test_prio_month}",
            json=[
                {
                    "weekNumber": 1,
                    "monday": 1,
                    "tuesday": 2,
                    "wednesday": 3,
                    "thursday": 1,
                    "friday": 2,
                }
            ],
        )
        assert priority_response.status_code == 200

        # Get the priority ID from PocketBase
        priorities = pocketbase_admin_client.get(
            "/api/collections/priorities/records",
            params={"filter": f'userId="{user_b_id}" && month="{test_prio_month}"'},
        ).json()
        priority_b_id = priorities["items"][0]["id"]

        # Logout user B and login as admin A
        test_app.post("/api/v1/auth/logout")
        register_and_elevate_to_admin(
            test_app=test_app,
            pocketbase_admin_client=pocketbase_admin_client,
            username="admin_a_prio",
            password="AdminA789!",
            name="Admin A Priority",
            institution_short_code="INST_A_PRIO",
            magic_word="MagicA789",
        )

        # Get user submissions for the test month (should NOT include institution B's priority)
        submissions_response = test_app.get(f"/api/v1/admin/users/{test_prio_month}")
        assert submissions_response.status_code == 200
        submissions = submissions_response.json()

        # Verify that institution B's priority is NOT in the results
        priority_ids = [s["priorityId"] for s in submissions]
        assert priority_b_id not in priority_ids

    def test_institution_admin_cannot_update_other_institutions_users(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that institution admin A cannot update users from institution B.

        This is a CRITICAL security test.
        """
        # Create two institutions
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution A Update Test",
            "INST_A_UPD",
            "MagicA_upd",
        )
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution B Update Test",
            "INST_B_UPD",
            "MagicB_upd",
        )

        # Register user in Institution B
        user_b_response = create_user(
            test_app,
            "user_b_upd",
            "PassB_upd!",
            "User B Update",
            "INST_B_UPD",
            "MagicB_upd",
        )
        user_b_id = user_b_response.json()["id"]

        # Register and elevate admin in Institution A
        register_and_elevate_to_admin(
            test_app=test_app,
            pocketbase_admin_client=pocketbase_admin_client,
            username="admin_a_upd",
            password="AdminA_upd!",
            name="Admin A Update",
            institution_short_code="INST_A_UPD",
            magic_word="MagicA_upd",
        )

        # Try to update user B (should fail - different institution)
        update_response = test_app.put(
            f"/api/v1/admin/users/{user_b_id}",
            json={"username": "hacked_username"},
        )
        assert update_response.status_code in [404, 403]

    def test_institution_admin_cannot_delete_other_institutions_users(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that institution admin A cannot delete users from institution B.

        This is a CRITICAL security test.
        """
        # Create two institutions
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution A Delete Test",
            "INST_A_DEL",
            "MagicA_del",
        )
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution B Delete Test",
            "INST_B_DEL",
            "MagicB_del",
        )

        # Register user in Institution B
        user_b_response = create_user(
            test_app,
            "user_b_del",
            "PassB_del!",
            "User B Delete",
            "INST_B_DEL",
            "MagicB_del",
        )
        user_b_id = user_b_response.json()["id"]

        # Register and elevate admin in Institution A
        register_and_elevate_to_admin(
            test_app=test_app,
            pocketbase_admin_client=pocketbase_admin_client,
            username="admin_a_del",
            password="AdminA_del!",
            name="Admin A Delete",
            institution_short_code="INST_A_DEL",
            magic_word="MagicA_del",
        )

        # Try to delete user B (should fail - different institution)
        delete_response = test_app.delete(f"/api/v1/admin/users/{user_b_id}")
        assert delete_response.status_code in [404, 403]

        # Verify user B still exists
        user_check = pocketbase_admin_client.get(
            f"/api/collections/users/records/{user_b_id}"
        )
        assert user_check.status_code == 200

    def test_institution_admin_total_users_count_is_filtered(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that institution admin only sees user count from their institution.

        This is a CRITICAL security test.
        """
        # Create two institutions
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution A Count Test",
            "INST_A_CNT",
            "MagicA_cnt",
        )
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution B Count Test",
            "INST_B_CNT",
            "MagicB_cnt",
        )

        # Register 2 users in Institution A
        for i in range(2):
            create_user(
                test_app,
                f"user_a{i}",
                f"PassA{i}!",
                f"User A{i}",
                "INST_A_CNT",
                "MagicA_cnt",
            )

        # Register 3 users in Institution B
        for i in range(3):
            create_user(
                test_app,
                f"user_b{i}",
                f"PassB{i}!",
                f"User B{i}",
                "INST_B_CNT",
                "MagicB_cnt",
            )

        # Register and elevate admin in Institution A
        register_and_elevate_to_admin(
            test_app=test_app,
            pocketbase_admin_client=pocketbase_admin_client,
            username="admin_a_cnt",
            password="AdminA_cnt!",
            name="Admin A Count",
            institution_short_code="INST_A_CNT",
            magic_word="MagicA_cnt",
        )

        # Get total users (should only count institution A users)
        total_users_response = test_app.get("/api/v1/admin/total-users")
        assert total_users_response.status_code == 200
        total_users_data = total_users_response.json()

        # Should see 2 users + 1 admin = 3 total for institution A
        assert total_users_data["totalUsers"] == 3


@pytest.mark.integration
class TestSuperAdminAccess:
    """Test that super admins CAN access all institutions' data."""

    def test_super_admin_can_see_all_institutions_users(
        self, test_app, pocketbase_admin_client, pocketbase_url, clean_redis
    ):
        """
        Test that super admin can see users from all institutions.
        """
        # Create two institutions
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution A Super Test",
            "INST_A_SUP",
            "MagicA_sup",
        )
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution B Super Test",
            "INST_B_SUP",
            "MagicB_sup",
        )

        # Register user in Institution A
        user_a_response = create_user(
            test_app,
            "user_a_sup",
            "PassA_sup!",
            "User A Super",
            "INST_A_SUP",
            "MagicA_sup",
        )
        user_a_id = user_a_response.json()["id"]

        # Register user in Institution B
        user_b_response = create_user(
            test_app,
            "user_b_sup",
            "PassB_sup!",
            "User B Super",
            "INST_B_SUP",
            "MagicB_sup",
        )
        user_b_id = user_b_response.json()["id"]

        # Create super admin directly in PocketBase (no institution)
        pocketbase_admin_client.post(
            "/api/collections/users/records",
            json={
                "username": "super_admin_test",
                "password": "SuperAdmin123!",
                "passwordConfirm": "SuperAdmin123!",
                "role": "super_admin",
                "institution_id": None,
            },
        )

        # Login as super admin using helper function
        login_with_pocketbase(
            pocketbase_url=pocketbase_url,
            test_app=test_app,
            redis_client=clean_redis,
            username="super_admin_test",
            password="SuperAdmin123!",
        )

        # Super admin should be able to access user A
        user_a_detail = test_app.get(f"/api/v1/admin/users/detail/{user_a_id}")
        assert user_a_detail.status_code == 200

        # Super admin should be able to access user B
        user_b_detail = test_app.get(f"/api/v1/admin/users/detail/{user_b_id}")
        assert user_b_detail.status_code == 200

    def test_super_admin_total_users_includes_all_institutions(
        self, test_app, pocketbase_admin_client, pocketbase_url, clean_redis
    ):
        """
        Test that super admin sees total user count across all institutions.
        """
        # Create two institutions
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution A Total Test",
            "INST_A_TOT",
            "MagicA_tot",
        )
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution B Total Test",
            "INST_B_TOT",
            "MagicB_tot",
        )

        # Register 2 users in Institution A
        for i in range(2):
            create_user(
                test_app,
                f"user_a_tot{i}",
                f"PassA_tot{i}!",
                f"User A Tot {i}",
                "INST_A_TOT",
                "MagicA_tot",
            )

        # Register 3 users in Institution B
        for i in range(3):
            create_user(
                test_app,
                f"user_b_tot{i}",
                f"PassB_tot{i}!",
                f"User B Tot {i}",
                "INST_B_TOT",
                "MagicB_tot",
            )

        # Create super admin directly in PocketBase (no institution)
        pocketbase_admin_client.post(
            "/api/collections/users/records",
            json={
                "username": "super_admin_total_test",
                "password": "SuperAdminTotal123!",
                "passwordConfirm": "SuperAdminTotal123!",
                "role": "super_admin",
                "institution_id": None,
            },
        )

        # Login as super admin using helper function
        login_with_pocketbase(
            pocketbase_url=pocketbase_url,
            test_app=test_app,
            redis_client=clean_redis,
            username="super_admin_total_test",
            password="SuperAdminTotal123!",
        )

        # Get total users (should include all institutions)
        total_users_response = test_app.get("/api/v1/admin/total-users")
        assert total_users_response.status_code == 200
        total_users_data = total_users_response.json()

        # Should see at least 2 + 3 + 1 (super admin) = 6 users
        # May include service account or other system users
        assert total_users_data["totalUsers"] >= 6


@pytest.mark.integration
class TestVacationDaysIsolation:
    """Test that vacation days are properly isolated between institutions."""

    def test_institution_admin_cannot_see_other_institutions_vacation_days(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that institution admin A cannot see vacation days from institution B.

        This is a CRITICAL security test.
        """
        # Create two institutions
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution A Vacation Test",
            "INST_A_VAC",
            "MagicA_vac",
        )
        inst_b = create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution B Vacation Test",
            "INST_B_VAC",
            "MagicB_vac",
        )

        # Create vacation day for institution B directly in PocketBase
        vacation_b = pocketbase_admin_client.post(
            "/api/collections/vacation_days/records",
            json={
                "date": (datetime.now() + timedelta(days=100)).strftime("%Y-%m-%d"),
                "type": "public_holiday",
                "description": "Christmas",
                "created_by": "admin_b",
                "institution_id": inst_b["id"],
            },
        ).json()

        # Register and elevate admin in Institution A
        register_and_elevate_to_admin(
            test_app=test_app,
            pocketbase_admin_client=pocketbase_admin_client,
            username="admin_a_vac",
            password="AdminAVac!",
            name="Admin A Vacation",
            institution_short_code="INST_A_VAC",
            magic_word="MagicA_vac",
        )

        # Get all vacation days (should NOT include institution B's vacation day)
        vacation_response = test_app.get("/api/v1/admin/vacation-days")
        assert vacation_response.status_code == 200
        vacation_days = vacation_response.json()

        # Verify that institution B's vacation day is NOT in the results
        vacation_ids = [v["id"] for v in vacation_days]
        assert vacation_b["id"] not in vacation_ids

    def test_institution_admin_cannot_delete_other_institutions_vacation_days(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that institution admin A cannot delete vacation days from institution B.

        This is a CRITICAL security test.
        """
        # Create two institutions
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution A Delete Vac Test",
            "INST_A_DEL_VAC",
            "MagicA_del_vac",
        )
        inst_b = create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution B Delete Vac Test",
            "INST_B_DEL_VAC",
            "MagicB_del_vac",
        )

        # Create vacation day for institution B
        vacation_date = (datetime.now() + timedelta(days=150)).strftime("%Y-%m-%d")
        vacation_b = pocketbase_admin_client.post(
            "/api/collections/vacation_days/records",
            json={
                "date": vacation_date,
                "type": "public_holiday",
                "description": "Independence Day",
                "created_by": "admin_b",
                "institution_id": inst_b["id"],
            },
        ).json()

        # Register and elevate admin in Institution A
        register_and_elevate_to_admin(
            test_app=test_app,
            pocketbase_admin_client=pocketbase_admin_client,
            username="admin_a_del_vac",
            password="AdminADelVac!",
            name="Admin A Delete Vac",
            institution_short_code="INST_A_DEL_VAC",
            magic_word="MagicA_del_vac",
        )

        # Try to delete institution B's vacation day (should fail)
        delete_response = test_app.delete(
            f"/api/v1/admin/vacation-days/{vacation_date}"
        )
        assert delete_response.status_code in [403, 404]

        # Verify vacation day still exists
        vac_check = pocketbase_admin_client.get(
            f"/api/collections/vacation_days/records/{vacation_b['id']}"
        )
        assert vac_check.status_code == 200

    def test_institution_admin_can_create_vacation_days_for_own_institution(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that institution admin can create vacation days for their own institution.
        """
        # Create institution
        inst = create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution Create Vac Test",
            "INST_CREATE_VAC",
            "MagicCreate_vac",
        )

        # Register and elevate admin
        register_and_elevate_to_admin(
            test_app=test_app,
            pocketbase_admin_client=pocketbase_admin_client,
            username="admin_create_vac",
            password="AdminCreateVac!",
            name="Admin Create Vac",
            institution_short_code="INST_CREATE_VAC",
            magic_word="MagicCreate_vac",
        )

        # Create vacation day (should succeed)
        vacation_date = (datetime.now() + timedelta(days=200)).strftime("%Y-%m-%d")
        create_response = test_app.post(
            "/api/v1/admin/vacation-days",
            json={
                "date": vacation_date,
                "type": "vacation",
                "description": "Christmas Eve",
            },
        )
        assert create_response.status_code == 200
        created_vacation = create_response.json()

        # Verify vacation day has correct institution_id
        vac_check = pocketbase_admin_client.get(
            f"/api/collections/vacation_days/records/{created_vacation['id']}"
        )
        assert vac_check.status_code == 200
        vac_data = vac_check.json()
        assert vac_data["institution_id"] == inst["id"]

    def test_user_cannot_see_other_institutions_vacation_days(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that regular user in Institution A cannot see vacation days from Institution B.

        This is a CRITICAL security test for user-facing vacation days endpoints.
        """
        # Create two institutions
        inst_a = create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution A User Vac Test",
            "INST_A_USER_VAC",
            "MagicAUserVac",
        )
        inst_b = create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution B User Vac Test",
            "INST_B_USER_VAC",
            "MagicBUserVac",
        )

        # Create vacation day for institution B
        vac_b_date = (datetime.now() + timedelta(days=250)).strftime("%Y-%m-%d")
        pocketbase_admin_client.post(
            "/api/collections/vacation_days/records",
            json={
                "date": vac_b_date,
                "type": "public_holiday",
                "description": "New Year's Eve",
                "created_by": "admin_b",
                "institution_id": inst_b["id"],
            },
        )

        # Create vacation day for institution A
        vac_a_date = (datetime.now() + timedelta(days=260)).strftime("%Y-%m-%d")
        pocketbase_admin_client.post(
            "/api/collections/vacation_days/records",
            json={
                "date": vac_a_date,
                "type": "vacation",
                "description": "Institution A Vacation",
                "created_by": "admin_a",
                "institution_id": inst_a["id"],
            },
        )

        # Register regular user in Institution A
        create_user(
            test_app,
            "user_a_vac",
            "UserAVac123!",
            "User A Vac",
            "INST_A_USER_VAC",
            "MagicAUserVac",
            keep_logged_in=True,
        )

        # Get all vacation days as user A (should NOT include institution B's vacation day)
        query_year = (datetime.now() + timedelta(days=260)).year
        vacation_response = test_app.get(f"/api/v1/vacation-days?year={query_year}")
        assert vacation_response.status_code == 200
        vacation_days = vacation_response.json()

        # Verify user A can only see their institution's vacation days
        vacation_dates = [v["date"] for v in vacation_days]
        assert any(
            vd.startswith(vac_a_date) for vd in vacation_dates
        )  # Institution A's
        assert not any(
            vd.startswith(vac_b_date) for vd in vacation_dates
        )  # Institution B's

    def test_user_cannot_see_other_institution_vacation_days_by_date(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that regular user cannot query specific vacation days from other institutions.
        """
        # Create two institutions
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution A User Vac Single Test",
            "INST_A_USER_VAC_SINGLE",
            "MagicAUserVacSingle",
        )
        inst_b = create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution B User Vac Single Test",
            "INST_B_USER_VAC_SINGLE",
            "MagicBUserVacSingle",
        )

        # Create vacation day for institution B
        vac_b_single_date = (datetime.now() + timedelta(days=270)).strftime("%Y-%m-%d")
        pocketbase_admin_client.post(
            "/api/collections/vacation_days/records",
            json={
                "date": vac_b_single_date,
                "type": "public_holiday",
                "description": "Institution B Holiday",
                "created_by": "admin_b",
                "institution_id": inst_b["id"],
            },
        )

        # Register regular user in Institution A
        create_user(
            test_app,
            "user_a_vac_single",
            "UserAVacSingle123!",
            "User A Vac Single",
            "INST_A_USER_VAC_SINGLE",
            "MagicAUserVacSingle",
            keep_logged_in=True,
        )

        # Try to get Institution B's vacation day by date (should fail)
        vacation_response = test_app.get(f"/api/v1/vacation-days/{vac_b_single_date}")
        assert (
            vacation_response.status_code == 404
        )  # Not found (filtered by institution)

    def test_user_vacation_days_range_endpoint_filters_by_institution(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that vacation days range endpoint filters by institution.
        """
        # Create two institutions
        inst_a = create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution A Range Test",
            "INST_A_RANGE",
            "MagicARange",
        )
        inst_b = create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution B Range Test",
            "INST_B_RANGE",
            "MagicBRange",
        )

        # Create vacation days for both institutions in same date range
        vac_range_a_date = (datetime.now() + timedelta(days=280)).strftime("%Y-%m-%d")
        pocketbase_admin_client.post(
            "/api/collections/vacation_days/records",
            json={
                "date": vac_range_a_date,
                "type": "vacation",
                "description": "Institution A June Vacation",
                "created_by": "admin_a",
                "institution_id": inst_a["id"],
            },
        )

        vac_range_b_date = (datetime.now() + timedelta(days=295)).strftime("%Y-%m-%d")
        pocketbase_admin_client.post(
            "/api/collections/vacation_days/records",
            json={
                "date": vac_range_b_date,
                "type": "vacation",
                "description": "Institution B June Vacation",
                "created_by": "admin_b",
                "institution_id": inst_b["id"],
            },
        )

        # Register user in Institution A
        create_user(
            test_app,
            "user_a_range",
            "UserARange123!",
            "User A Range",
            "INST_A_RANGE",
            "MagicARange",
            keep_logged_in=True,
        )

        # Get vacation days in range (should only see Institution A's)
        start_date = (datetime.now() + timedelta(days=275)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=300)).strftime("%Y-%m-%d")
        vacation_response = test_app.get(
            f"/api/v1/vacation-days/range?start_date={start_date}&end_date={end_date}"
        )
        assert vacation_response.status_code == 200
        vacation_days = vacation_response.json()

        # Should only see Institution A's vacation day
        assert len(vacation_days) == 1
        assert vacation_days[0]["date"].startswith(vac_range_a_date)
        assert vacation_days[0]["description"] == "Institution A June Vacation"


@pytest.mark.integration
class TestPrioritiesIsolation:
    """Test that priorities are properly isolated between institutions."""

    def test_user_priority_save_includes_institution_id(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that when users save priorities, institution_id is included.
        """
        # Create institution
        inst = create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution Priority Test",
            "INST_PRIO",
            "MagicPrio123",
        )

        # Register user
        user_response = create_user(
            test_app,
            "user_prio",
            "UserPrio123!",
            "User Priority",
            "INST_PRIO",
            "MagicPrio123",
            keep_logged_in=True,
        )
        user_id = user_response.json()["id"]

        # Save priorities
        test_month = (datetime.now() + timedelta(days=35)).strftime("%Y-%m")
        save_response = test_app.put(
            f"/api/v1/priorities/{test_month}",
            json=[
                {
                    "weekNumber": 1,
                    "monday": 1,
                    "tuesday": 2,
                    "wednesday": 3,
                    "thursday": 1,
                    "friday": 2,
                }
            ],
        )
        assert save_response.status_code == 200

        # Verify priority has institution_id
        priorities = pocketbase_admin_client.get(
            "/api/collections/priorities/records",
            params={"filter": f'userId="{user_id}" && month="{test_month}"'},
        ).json()

        assert len(priorities["items"]) == 1
        assert priorities["items"][0]["institution_id"] == inst["id"]

    def test_institution_admin_cannot_update_other_institution_priorities(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that institution admin from A cannot update priorities from Institution B.

        This is a CRITICAL security test.
        """
        # Create two institutions
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution A Priority Update Test",
            "INST_A_PRIO_UPDATE",
            "MagicAPrioUpdate",
        )
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution B Priority Update Test",
            "INST_B_PRIO_UPDATE",
            "MagicBPrioUpdate",
        )

        # Create user in Institution B and their priority
        user_b_response = create_user(
            test_app,
            "user_b_prio_update",
            "UserBPrioUpdate123!",
            "User B Priority Update",
            "INST_B_PRIO_UPDATE",
            "MagicBPrioUpdate",
            keep_logged_in=True,
        )
        user_b_id = user_b_response.json()["id"]

        # User B creates a priority
        test_month_update = (datetime.now() + timedelta(days=65)).strftime("%Y-%m")
        priority_response = test_app.put(
            f"/api/v1/priorities/{test_month_update}",
            json=[
                {
                    "weekNumber": 1,
                    "monday": 1,
                    "tuesday": 2,
                    "wednesday": 3,
                    "thursday": 1,
                    "friday": 2,
                }
            ],
        )
        assert priority_response.status_code == 200

        # Get priority ID
        priorities = pocketbase_admin_client.get(
            "/api/collections/priorities/records",
            params={"filter": f'userId="{user_b_id}" && month="{test_month_update}"'},
        ).json()
        priority_id = priorities["items"][0]["id"]

        # Logout user B and register admin A
        test_app.post("/api/v1/auth/logout")
        register_and_elevate_to_admin(
            test_app=test_app,
            pocketbase_admin_client=pocketbase_admin_client,
            username="admin_a_prio_update",
            password="AdminAPrioUpdate123!",
            name="Admin A Priority Update",
            institution_short_code="INST_A_PRIO_UPDATE",
            magic_word="MagicAPrioUpdate",
        )

        # Try to update Institution B's priority (should fail)
        update_response = test_app.patch(
            f"/api/v1/admin/priorities/{priority_id}",
            json={"encrypted_fields": "tampered_data"},
        )
        assert update_response.status_code in [401, 404, 403]

    def test_institution_admin_cannot_delete_other_institution_priorities(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that institution admin from A cannot delete priorities from Institution B.

        This is a CRITICAL security test.
        """
        # Create two institutions
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution A Priority Delete Test",
            "INST_A_PRIO_DELETE",
            "MagicAPrioDelete",
        )
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution B Priority Delete Test",
            "INST_B_PRIO_DELETE",
            "MagicBPrioDelete",
        )

        # Create user in Institution B and their priority
        user_b_response = create_user(
            test_app,
            "user_b_prio_delete",
            "UserBPrioDelete123!",
            "User B Priority Delete",
            "INST_B_PRIO_DELETE",
            "MagicBPrioDelete",
            keep_logged_in=True,
        )
        user_b_id = user_b_response.json()["id"]

        # User B creates a priority
        test_month_delete = (datetime.now() + timedelta(days=35)).strftime("%Y-%m")
        priority_response = test_app.put(
            f"/api/v1/priorities/{test_month_delete}",
            json=[
                {
                    "weekNumber": 1,
                    "monday": 1,
                    "tuesday": 2,
                    "wednesday": 3,
                    "thursday": 1,
                    "friday": 2,
                }
            ],
        )
        assert priority_response.status_code == 200

        # Get priority ID
        priorities = pocketbase_admin_client.get(
            "/api/collections/priorities/records",
            params={"filter": f'userId="{user_b_id}" && month="{test_month_delete}"'},
        ).json()
        priority_id = priorities["items"][0]["id"]

        # Logout user B and register admin A
        test_app.post("/api/v1/auth/logout")
        register_and_elevate_to_admin(
            test_app=test_app,
            pocketbase_admin_client=pocketbase_admin_client,
            username="admin_a_prio_delete",
            password="AdminAPrioDelete123!",
            name="Admin A Priority Delete",
            institution_short_code="INST_A_PRIO_DELETE",
            magic_word="MagicAPrioDelete",
        )

        # Try to delete Institution B's priority (should fail)
        delete_response = test_app.delete(f"/api/v1/admin/priorities/{priority_id}")
        assert delete_response.status_code in [401, 404, 403]

        # Verify priority still exists
        verify_response = pocketbase_admin_client.get(
            f"/api/collections/priorities/records/{priority_id}"
        )
        assert verify_response.status_code == 200


@pytest.mark.integration
class TestInputValidationAndSecurityFixes:
    """Test input validation and fixes for security audit findings."""

    def test_manual_entry_delete_rejects_malicious_month(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that manual entry delete endpoint rejects malicious month parameter.
        """
        # Create institution and admin
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution Filter Injection Test",
            "INST_FILTER",
            "MagicFilter123",
        )
        register_and_elevate_to_admin(
            test_app=test_app,
            pocketbase_admin_client=pocketbase_admin_client,
            username="admin_filter",
            password="AdminFilter123!",
            name="Admin Filter",
            institution_short_code="INST_FILTER",
            magic_word="MagicFilter123",
        )

        # Try to delete with malicious month parameter (filter injection attempt)
        malicious_month = (
            f'{datetime.now().strftime("%Y-%m")}" || manual = false && userId="'
        )
        delete_response = test_app.delete(
            f"/api/v1/admin/manual-entry/{malicious_month}/test-id"
        )
        # Should reject with 422 (validation error), not execute the query
        assert delete_response.status_code == 422

    def test_manual_entry_delete_rejects_malicious_identifier(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that manual entry delete endpoint rejects malicious identifier parameter.
        """
        # Create institution and admin
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution Identifier Injection Test",
            "INST_ID_INJ",
            "MagicIdInj123",
        )
        register_and_elevate_to_admin(
            test_app=test_app,
            pocketbase_admin_client=pocketbase_admin_client,
            username="admin_id_inj",
            password="AdminIdInj123!",
            name="Admin Id Injection",
            institution_short_code="INST_ID_INJ",
            magic_word="MagicIdInj123",
        )

        # Try to delete with malicious identifier (filter injection attempt)
        malicious_identifier = 'test" || identifier!=""'
        delete_response = test_app.delete(
            f"/api/v1/admin/manual-entry/{datetime.now().strftime('%Y-%m')}/{malicious_identifier}"
        )
        # Should reject with 422 (validation error)
        assert delete_response.status_code == 422

    def test_manual_priority_create_rejects_malicious_identifier(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that manual priority create endpoint rejects malicious identifier.
        """
        # Create institution and admin
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution Manual Priority Injection Test",
            "INST_MANUAL_INJ",
            "MagicManualInj123",
        )
        register_and_elevate_to_admin(
            test_app=test_app,
            pocketbase_admin_client=pocketbase_admin_client,
            username="admin_manual_inj",
            password="AdminManualInj123!",
            name="Admin Manual Injection",
            institution_short_code="INST_MANUAL_INJ",
            magic_word="MagicManualInj123",
        )

        # Try to create manual priority with malicious identifier
        malicious_identifier = 'test" || manual = false && userId="'
        create_response = test_app.post(
            "/api/v1/admin/manual-priority",
            json={
                "identifier": malicious_identifier,
                "month": datetime.now().strftime("%Y-%m"),
                "weeks": [
                    {
                        "weekNumber": 1,
                        "monday": 1,
                        "tuesday": 2,
                        "wednesday": 3,
                        "thursday": 1,
                        "friday": 2,
                    }
                ],
            },
        )
        # Should reject with 422 (validation error)
        assert create_response.status_code == 422

    def test_get_user_for_admin_rejects_malicious_username(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that get user for admin endpoint rejects malicious username.
        """
        # Create institution and admin
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution Username Injection Test",
            "INST_USER_INJ",
            "MagicUserInj123",
        )
        register_and_elevate_to_admin(
            test_app=test_app,
            pocketbase_admin_client=pocketbase_admin_client,
            username="admin_user_inj",
            password="AdminUserInj123!",
            name="Admin User Injection",
            institution_short_code="INST_USER_INJ",
            magic_word="MagicUserInj123",
        )

        # Try to get user with malicious username (filter injection attempt)
        malicious_username = "test' || role='super_admin"
        user_response = test_app.get(f"/api/v1/admin/users/info/{malicious_username}")
        # Should reject with 422 (validation error)
        assert user_response.status_code == 422

    def test_get_manual_entries_rejects_invalid_month(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that get manual entries endpoint validates month parameter.
        """
        # Create institution and admin
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution Month Validation Test",
            "INST_MONTH_VAL",
            "MagicMonthVal123",
        )
        register_and_elevate_to_admin(
            test_app=test_app,
            pocketbase_admin_client=pocketbase_admin_client,
            username="admin_month_val",
            password="AdminMonthVal123!",
            name="Admin Month Validation",
            institution_short_code="INST_MONTH_VAL",
            magic_word="MagicMonthVal123",
        )

        # Try to get manual entries with malicious month
        malicious_month = f'{datetime.now().strftime("%Y-%m")}" || manual != true'
        entries_response = test_app.get(
            f"/api/v1/admin/manual-entries/{malicious_month}"
        )
        # Should reject with 422 (validation error)
        assert entries_response.status_code == 422

    def test_priority_get_rejects_malicious_month(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that GET /api/v1/priorities/{month} rejects malicious month values.

        Security Audit #4 Issue #1: Filter injection in priority GET endpoint.
        """
        # Create institution
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Institution Priority Get Test",
            "TEST_PRI_GET",
            "TestMagic123",
        )

        # Register a user
        create_user(
            test_app,
            "user_pri_get",
            "TestPass123!",
            "Test User",
            "TEST_PRI_GET",
            "TestMagic123",
            keep_logged_in=True,
        )

        # Try to get priorities with malicious month value
        malicious_month = f'{datetime.now().strftime("%Y-%m")}" || userId!=""'
        get_response = test_app.get(f"/api/v1/priorities/{malicious_month}")

        # Should reject with 422 (validation error)
        assert get_response.status_code == 422
        error_detail = get_response.json()["detail"].lower()
        assert (
            "monat" in error_detail
            or "format" in error_detail
            or "unconverted" in error_detail
        )

    def test_priority_delete_rejects_malicious_month(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that DELETE /api/v1/priorities/{month} rejects malicious month values.

        Security Audit #4 Issue #2: Filter injection in priority DELETE endpoint.
        """
        # Create institution
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Test Institution Priority Delete Test",
            "TEST_PRI_DEL",
            "TestMagic456",
        )

        # Register a user
        create_user(
            test_app,
            "user_pri_del",
            "TestPass456!",
            "Test User Delete",
            "TEST_PRI_DEL",
            "TestMagic456",
            keep_logged_in=True,
        )

        # Try to delete priorities with malicious month value
        malicious_month = f'{datetime.now().strftime("%Y-%m")}" || identifier!=null'
        delete_response = test_app.delete(f"/api/v1/priorities/{malicious_month}")

        # Should reject with 422 (validation error)
        assert delete_response.status_code == 422
        error_detail = delete_response.json()["detail"].lower()
        assert (
            "monat" in error_detail
            or "format" in error_detail
            or "unconverted" in error_detail
        )

    def test_vacation_day_get_rejects_malicious_date(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that GET /api/v1/admin/vacation-days/{date} rejects malicious date values.

        Security Audit #4 Issue #3: Filter injection in admin vacation day GET endpoint.
        """
        # Create institution
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Test Institution VD",
            "TEST_VD_GET",
            "TestVDGet123",
        )
        register_and_elevate_to_admin(
            test_app=test_app,
            pocketbase_admin_client=pocketbase_admin_client,
            username="admin_vd_get",
            password="AdminVD123!",
            name="Admin VD Get",
            institution_short_code="TEST_VD_GET",
            magic_word="TestVDGet123",
        )

        # Try to get vacation day with malicious date
        malicious_date = f'{(datetime.now() + timedelta(days=100)).strftime("%Y-%m-%d")}" || type="public_holiday'
        get_response = test_app.get(f"/api/v1/admin/vacation-days/{malicious_date}")

        # Should reject with 422 (validation error)
        assert get_response.status_code == 422
        error_detail = get_response.json()["detail"].lower()
        assert "format" in error_detail or "unconverted" in error_detail

    def test_vacation_day_update_rejects_malicious_date(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that PUT /api/v1/admin/vacation-days/{date} rejects malicious date values.

        Security Audit #4 Issue #4: Filter injection in admin vacation day PUT endpoint.
        """
        # Create institution
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Test Institution VD Update",
            "TEST_VD_PUT",
            "TestVDPut456",
        )
        register_and_elevate_to_admin(
            test_app=test_app,
            pocketbase_admin_client=pocketbase_admin_client,
            username="admin_vd_put",
            password="AdminVDPut456!",
            name="Admin VD Put",
            institution_short_code="TEST_VD_PUT",
            magic_word="TestVDPut456",
        )

        # Try to update vacation day with malicious date
        malicious_date = f'{(datetime.now() + timedelta(days=110)).strftime("%Y-%m-%d")}" || institution_id!=""'
        put_response = test_app.put(
            f"/api/v1/admin/vacation-days/{malicious_date}",
            json={"type": "public_holiday", "description": "Test"},
        )

        # Should reject with 422 (validation error)
        assert put_response.status_code == 422
        error_detail = put_response.json()["detail"].lower()
        assert "format" in error_detail or "unconverted" in error_detail

    def test_vacation_day_delete_rejects_malicious_date(
        self, test_app, pocketbase_admin_client
    ):
        """
        Test that DELETE /api/v1/admin/vacation-days/{date} rejects malicious date values.

        Security Audit #4 Issue #4: Filter injection in admin vacation day DELETE endpoint.
        """
        # Create institution
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Test Institution VD Delete",
            "TEST_VD_DEL",
            "TestVDDel789",
        )
        register_and_elevate_to_admin(
            test_app=test_app,
            pocketbase_admin_client=pocketbase_admin_client,
            username="admin_vd_del",
            password="AdminVDDel789!",
            name="Admin VD Del",
            institution_short_code="TEST_VD_DEL",
            magic_word="TestVDDel789",
        )

        # Try to delete vacation day with malicious date
        malicious_date = (
            f'{(datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d")}" || type=""'
        )
        delete_response = test_app.delete(
            f"/api/v1/admin/vacation-days/{malicious_date}"
        )

        # Should reject with 422 (validation error)
        assert delete_response.status_code == 422
        error_detail = delete_response.json()["detail"].lower()
        assert "format" in error_detail or "unconverted" in error_detail

    def test_change_password_invalidates_old_sessions(
        self, test_app, pocketbase_admin_client, redis_client
    ):
        """
        Test that changing password invalidates all old sessions.

        Security Audit #4 Issue #5: Session invalidation bug in change password.
        This is the MOST CRITICAL fix - ensures old sessions are invalidated.
        """
        # Create institution
        create_institution_with_rsa_key(
            pocketbase_admin_client,
            "Test Institution PW",
            "TEST_PW_CHANGE",
            "TestPWChange123",
        )

        # Register a user
        register_response = create_user(
            test_app,
            "user_pw_change",
            "OldPassword123!",
            "Test User PW",
            "TEST_PW_CHANGE",
            "TestPWChange123",
            keep_logged_in=True,
        )

        # Get the auth token from session 1
        session1_cookies = register_response.cookies

        # Verify session 1 works
        verify1_response = test_app.get("/api/v1/auth/verify")
        assert verify1_response.status_code == 200

        # Login again from "another device" (session 2)
        login2_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "user_pw_change",
                "password": "OldPassword123!",
                "keep_logged_in": True,
            },
        )
        assert login2_response.status_code == 200
        session2_cookies = login2_response.cookies

        # Verify both sessions work
        test_app.cookies.clear()
        test_app.cookies.update(session1_cookies)
        verify1_response = test_app.get("/api/v1/auth/verify")
        assert verify1_response.status_code == 200

        test_app.cookies.clear()
        test_app.cookies.update(session2_cookies)
        verify2_response = test_app.get("/api/v1/auth/verify")
        assert verify2_response.status_code == 200

        # Change password using session 2
        change_pw_response = test_app.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "OldPassword123!",
                "new_password": "NewPassword456!",
            },
        )
        assert change_pw_response.status_code == 200
        session3_cookies = (
            change_pw_response.cookies
        )  # New session after password change

        # Verify that session 1 (old session) is now INVALID
        test_app.cookies.clear()
        test_app.cookies.update(session1_cookies)
        verify_old_session_response = test_app.get("/api/v1/auth/verify")
        assert verify_old_session_response.status_code == 401, (
            f"Session 1 was expected to be invalid (401) but got {verify_old_session_response.status_code}"
        )

        # Verify that session 2 (the one that changed password) is also INVALID
        test_app.cookies.clear()
        test_app.cookies.update(session2_cookies)
        verify_pw_change_session_response = test_app.get("/api/v1/auth/verify")
        assert verify_pw_change_session_response.status_code == 401, (
            f"Session 2 was expected to be invalid (401) but got {verify_pw_change_session_response.status_code}"
        )

        # Verify that the NEW session (session 3) works
        test_app.cookies.clear()
        test_app.cookies.update(session3_cookies)
        verify_new_session_response = test_app.get("/api/v1/auth/verify")
        assert verify_new_session_response.status_code == 200, (
            f"Session 3 was expected to be valid but got {verify_new_session_response.status_code}"
        )

        # Verify we can use the new password
        test_app.post("/api/v1/auth/logout")
        login_new_pw_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "user_pw_change",
                "password": "NewPassword456!",
                "keep_logged_in": True,
            },
        )
        assert login_new_pw_response.status_code == 200
