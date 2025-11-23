"""
Integration tests for authentication routes.

Tests the full authentication flow with real Redis and PocketBase.
"""

import re
import secrets

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestAuthenticationIntegration:
    """Integration tests for auth endpoints."""

    def test_user_registration_and_login_flow(
        self, test_app: TestClient, pocketbase_url: str
    ):
        """
        Test complete user registration and login flow.

        This tests:
        - User registration
        - Login with credentials
        - Session creation in Redis
        - Cookie management
        """
        # Register a new user with unique username to avoid conflicts
        # (needed when using docker-compose with persistent volumes between tests)
        unique_suffix = secrets.token_hex(4)
        registration_data = {
            "username": f"testuser_{unique_suffix}",
            "password": "SecurePassword123!",
            "name": "Test User",
            "magic_word": "test",
        }

        # registration of user: magic word + register
        verify_magic_word_response = test_app.post(
            "/api/v1/auth/verify-magic-word",
            json={
                "magic_word": registration_data["magic_word"],
                "institution_short_code": "TEST",
            },
        )
        assert (
            verify_magic_word_response.status_code == 200
        ), f"Failed to assert magic word: {verify_magic_word_response.status_code} - {verify_magic_word_response.text}"
        magic_word_body = verify_magic_word_response.json()
        assert "token" in magic_word_body
        registration_data["reg_token"] = magic_word_body["token"]
        register_response = test_app.post(
            "/api/v1/auth/register",
            json={
                "identity": registration_data["username"],
                "password": registration_data["password"],
                "passwordConfirm": registration_data["password"],
                "name": registration_data["name"],
                "registration_token": registration_data["reg_token"],
            },
        )
        assert (
            register_response.status_code == 200
        ), f"Registrierung fehlgeschlagen: {register_response.status_code} - {register_response.text}"

        # Login via API
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": registration_data["username"],
                "password": registration_data["password"],
            },
        )

        assert login_response.status_code == 200

        # Extract cookies from Set-Cookie headers
        # TestClient doesn't automatically handle httpOnly cookies, so we need to extract them manually
        set_cookie_headers = login_response.headers.get_list("set-cookie")

        cookies = {}
        for cookie_header in set_cookie_headers:
            # Parse cookie name and value from "name=value; attributes..."
            cookie_match = re.match(r"([^=]+)=([^;]+)", cookie_header)
            if cookie_match:
                cookies[cookie_match.group(1)] = cookie_match.group(2)

        assert "auth_token" in cookies, "auth_token cookie not found"
        assert "dek" in cookies, "dek cookie not found"

        # Verify session endpoint - manually pass cookies
        test_app.cookies = cookies
        verify_response = test_app.get(
            "/api/v1/auth/verify",
        )
        assert (
            verify_response.status_code == 200
        ), f"Verification failed: {verify_response.text}"
        data = verify_response.json()
        assert data["username"] == registration_data["username"]
        assert data["authenticated"] is True

    def test_login_with_invalid_credentials(self, test_app: TestClient):
        """Test login with invalid credentials fails appropriately."""
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "nonexistent",
                "password": "WrongPassword123!",
            },
        )

        assert login_response.status_code in [400, 401]

        # Check Set-Cookie headers to ensure no auth_token was set
        set_cookie_headers = login_response.headers.get_list("set-cookie")
        cookies = {}
        for cookie_header in set_cookie_headers:
            cookie_match = re.match(r"([^=]+)=([^;]+)", cookie_header)
            if cookie_match:
                cookies[cookie_match.group(1)] = cookie_match.group(2)

        assert "auth_token" not in cookies

    def test_logout_clears_session(self, test_app: TestClient):
        """Test that logout properly clears session and cookies."""
        # Register a new user with unique username
        unique_suffix = secrets.token_hex(4)
        registration_data = {
            "username": f"logoutuser_{unique_suffix}",
            "password": "Password123!",
            "name": "Logout User",
            "magic_word": "test",
        }

        # Verify magic word and get registration token
        verify_magic_word_response = test_app.post(
            "/api/v1/auth/verify-magic-word",
            json={
                "magic_word": registration_data["magic_word"],
                "institution_short_code": "TEST",
            },
        )
        assert verify_magic_word_response.status_code == 200
        magic_word_body = verify_magic_word_response.json()
        registration_data["reg_token"] = magic_word_body["token"]

        # Register user
        register_response = test_app.post(
            "/api/v1/auth/register",
            json={
                "identity": registration_data["username"],
                "password": registration_data["password"],
                "passwordConfirm": registration_data["password"],
                "name": registration_data["name"],
                "registration_token": registration_data["reg_token"],
            },
        )
        assert register_response.status_code == 200

        # Login
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": registration_data["username"],
                "password": registration_data["password"],
            },
        )

        assert login_response.status_code == 200

        # Extract cookies from login
        set_cookie_headers = login_response.headers.get_list("set-cookie")
        cookies = {}
        for cookie_header in set_cookie_headers:
            cookie_match = re.match(r"([^=]+)=([^;]+)", cookie_header)
            if cookie_match:
                cookies[cookie_match.group(1)] = cookie_match.group(2)

        assert "auth_token" in cookies
        test_app.cookies = cookies

        # Logout - pass the cookies
        logout_response = test_app.post("/api/v1/auth/logout")
        assert logout_response.status_code == 200

        # Verify session is invalid - try to use the old cookies
        verify_response = test_app.get("/api/v1/auth/verify")
        assert verify_response.status_code in [401, 403]

    def test_change_password_success(self, test_app: TestClient):
        """Test successful password change flow."""
        # Register a new user with unique username
        unique_suffix = secrets.token_hex(4)
        registration_data = {
            "username": f"changepass_{unique_suffix}",
            "password": "OldPassword123!",
            "name": "Password Change User",
            "magic_word": "test",
        }

        # Verify magic word and register
        verify_magic_word_response = test_app.post(
            "/api/v1/auth/verify-magic-word",
            json={
                "magic_word": registration_data["magic_word"],
                "institution_short_code": "TEST",
            },
        )
        assert verify_magic_word_response.status_code == 200
        magic_word_body = verify_magic_word_response.json()
        registration_data["reg_token"] = magic_word_body["token"]

        register_response = test_app.post(
            "/api/v1/auth/register",
            json={
                "identity": registration_data["username"],
                "password": registration_data["password"],
                "passwordConfirm": registration_data["password"],
                "name": registration_data["name"],
                "registration_token": registration_data["reg_token"],
            },
        )
        assert register_response.status_code == 200

        # Login with old password
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": registration_data["username"],
                "password": registration_data["password"],
            },
        )
        assert login_response.status_code == 200

        # Extract cookies
        set_cookie_headers = login_response.headers.get_list("set-cookie")
        cookies = {}
        for cookie_header in set_cookie_headers:
            cookie_match = re.match(r"([^=]+)=([^;]+)", cookie_header)
            if cookie_match:
                cookies[cookie_match.group(1)] = cookie_match.group(2)

        assert "auth_token" in cookies
        test_app.cookies = cookies

        # Change password
        new_password = "NewPassword456!"
        change_password_response = test_app.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": registration_data["password"],
                "new_password": new_password,
            },
        )
        assert change_password_response.status_code == 200
        data = change_password_response.json()
        assert data["success"] is True
        assert "erfolgreich" in data["message"].lower()

        # Verify old password no longer works after password change
        test_app.cookies.clear()  # Clear cookies to force fresh login
        old_password_login = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": registration_data["username"],
                "password": registration_data["password"],
            },
        )
        assert old_password_login.status_code in [
            400,
            401,
        ], f"Login with old password should fail but got {old_password_login.status_code}"

        # Login with new password should work
        new_login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": registration_data["username"],
                "password": new_password,
            },
        )
        assert new_login_response.status_code == 200, (
            f"Login with new password failed: {new_login_response.status_code} - "
            f"{new_login_response.text}"
        )

        # Extract cookies from new login
        new_set_cookie_headers = new_login_response.headers.get_list("set-cookie")
        new_cookies = {}
        for cookie_header in new_set_cookie_headers:
            cookie_match = re.match(r"([^=]+)=([^;]+)", cookie_header)
            if cookie_match:
                new_cookies[cookie_match.group(1)] = cookie_match.group(2)

        test_app.cookies = new_cookies

        # Verify the new session works
        verify_response = test_app.get("/api/v1/auth/verify")
        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data["authenticated"] is True
        assert verify_data["username"] == registration_data["username"]

    def test_change_password_wrong_current_password(self, test_app: TestClient):
        """Test password change fails with wrong current password."""
        # Register and login
        unique_suffix = secrets.token_hex(4)
        registration_data = {
            "username": f"wrongpass_{unique_suffix}",
            "password": "CorrectPassword123!",
            "name": "Wrong Password User",
            "magic_word": "test",
        }

        # Verify magic word and register
        verify_magic_word_response = test_app.post(
            "/api/v1/auth/verify-magic-word",
            json={
                "magic_word": registration_data["magic_word"],
                "institution_short_code": "TEST",
            },
        )
        assert verify_magic_word_response.status_code == 200
        magic_word_body = verify_magic_word_response.json()

        register_response = test_app.post(
            "/api/v1/auth/register",
            json={
                "identity": registration_data["username"],
                "password": registration_data["password"],
                "passwordConfirm": registration_data["password"],
                "name": registration_data["name"],
                "registration_token": magic_word_body["token"],
            },
        )
        assert register_response.status_code == 200

        # Login
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": registration_data["username"],
                "password": registration_data["password"],
            },
        )
        assert login_response.status_code == 200

        # Extract cookies
        set_cookie_headers = login_response.headers.get_list("set-cookie")
        cookies = {}
        for cookie_header in set_cookie_headers:
            cookie_match = re.match(r"([^=]+)=([^;]+)", cookie_header)
            if cookie_match:
                cookies[cookie_match.group(1)] = cookie_match.group(2)

        test_app.cookies = cookies

        # Try to change password with wrong current password
        change_password_response = test_app.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "WrongPassword123!",
                "new_password": "NewPassword456!",
            },
        )
        assert change_password_response.status_code == 400
        data = change_password_response.json()
        assert "passwort ist falsch" in data["detail"].lower()

        # Verify session is still valid (password not changed)
        verify_response = test_app.get("/api/v1/auth/verify")
        assert verify_response.status_code == 200

        # Verify original password still works
        relogin_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": registration_data["username"],
                "password": registration_data["password"],
            },
        )
        assert relogin_response.status_code == 200

    def test_change_password_unauthenticated(self, test_app: TestClient):
        """Test password change fails without authentication."""
        # Clear any cookies
        test_app.cookies.clear()

        change_password_response = test_app.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "OldPassword123!",
                "new_password": "NewPassword456!",
            },
        )
        assert change_password_response.status_code in [401, 403]
