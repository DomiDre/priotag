"""
Pytest fixtures for integration tests.

Provides real Redis and PocketBase instances via testcontainers or docker-compose.
Set USE_DOCKER_SERVICES=true to use docker-compose services instead of testcontainers.
"""

import base64
import json
import os
import secrets
import time
from collections.abc import Generator
from pathlib import Path

import httpx
import pytest
import redis
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from starlette.testclient import TestClient
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from .setup_pocketbase import setup_pocketbase

# Check if we should use docker-compose services
USE_DOCKER_SERVICES = os.getenv("USE_DOCKER_SERVICES", "").lower() == "true"

# Store setup results globally for session scope
_POCKETBASE_SETUP_RESULT = None

# ---------------------------------------------------------------------------- #
#                               HELPER FUNCTIONS                               #
# ---------------------------------------------------------------------------- #


def create_institution_with_rsa_key(pocketbase_client, name, short_code, magic_word):
    """Helper to create institution with RSA keypair for testing.

    Args:
        pocketbase_client: Authenticated PocketBase admin client
        name: Institution name
        short_code: Institution short code (unique identifier)
        magic_word: Registration magic word

    Returns:
        dict: Created institution record with all fields

    Raises:
        AssertionError: If institution creation fails
    """
    # Generate RSA keypair
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    admin_public_key = public_pem.decode()

    # Create institution
    response = pocketbase_client.post(
        "/api/collections/institutions/records",
        json={
            "name": name,
            "short_code": short_code,
            "registration_magic_word": magic_word,
            "admin_public_key": admin_public_key,
            "active": True,
        },
    )

    assert response.status_code == 200, (
        f"Failed to create institution '{name}' (short_code: {short_code}): "
        f"Status {response.status_code}, Response: {response.text}"
    )

    return response.json()


def login_with_pocketbase(
    pocketbase_url: str,
    test_app: TestClient,
    redis_client: redis.Redis,
    username: str,
    password: str,
    user_record: dict | None = None,
) -> str:
    """
    Authenticate directly with PocketBase and set up session for test_app.

    This helper allows testing users created directly in PocketBase without
    going through the full registration flow with encryption setup.

    Args:
        pocketbase_url: PocketBase base URL
        test_app: FastAPI TestClient to set cookies on
        redis_client: Redis client for session storage
        username: Username to authenticate
        password: Password to authenticate
        user_record: Optional user record (if already fetched). Will be fetched if not provided.

    Returns:
        str: The authentication token

    Raises:
        AssertionError: If authentication fails
    """
    # Authenticate with PocketBase
    pb_client = httpx.Client(base_url=pocketbase_url, timeout=10.0)
    auth_response = pb_client.post(
        "/api/collections/users/auth-with-password",
        json={
            "identity": username,
            "password": password,
        },
    )
    assert auth_response.status_code == 200, (
        f"PocketBase authentication failed: {auth_response.status_code} - {auth_response.text}"
    )

    auth_data = auth_response.json()
    token = auth_data["token"]
    record = user_record or auth_data["record"]

    # Create session in Redis (mimicking what the login endpoint does)
    session_key = f"session:{token}"
    session_info = {
        "id": record["id"],
        "username": record["username"],
        "role": record["role"],
        "is_admin": record["role"] in ["institution_admin", "super_admin"],
        "institution_id": record.get("institution_id"),
    }

    # Set session TTL (15 minutes for admins, 8 hours for regular users)
    if session_info["is_admin"]:
        session_ttl = 900  # 15 minutes
    else:
        session_ttl = 8 * 3600  # 8 hours

    redis_client.setex(session_key, session_ttl, json.dumps(session_info))

    # Set cookies on test_app
    # Note: For test users without encryption data, we use a dummy DEK
    # This won't work for actual encrypted operations but is fine for testing
    # access control and authorization
    dummy_dek = b"\x00" * 32  # 32 bytes of zeros

    # TestClient uses httpx.Cookies which is a simple dict-like object
    # We can set cookies directly without domain/path parameters
    test_app.cookies["auth_token"] = token
    test_app.cookies["dek"] = base64.b64encode(dummy_dek).decode("utf-8")

    pb_client.close()
    return token


def register_and_elevate_to_admin(
    test_app: TestClient,
    pocketbase_admin_client: httpx.Client,
    username: str,
    password: str,
    name: str,
    institution_short_code: str,
    magic_word: str,
) -> str:
    """
    Register a user and elevate them to institution_admin role.

    This helper implements the register → elevate → logout → re-login pattern
    that is commonly used in security tests.

    Args:
        test_app: FastAPI TestClient
        pocketbase_admin_client: Authenticated PocketBase admin client
        username: Username for the user
        password: Password for the user
        name: Display name for the user
        institution_short_code: Institution short code
        magic_word: Registration magic word

    Returns:
        str: The user ID of the created admin user

    Raises:
        AssertionError: If registration, elevation, or login fails
    """
    # Register user via register-qr endpoint
    register_response = test_app.post(
        "/api/v1/auth/register-qr",
        json={
            "identity": username,
            "password": password,
            "passwordConfirm": password,
            "name": name,
            "institution_short_code": institution_short_code,
            "magic_word": magic_word,
            "keep_logged_in": True,
        },
    )
    assert register_response.status_code == 200, (
        f"Failed to register user '{username}': {register_response.status_code} - {register_response.text}"
    )
    user_id = register_response.json()["id"]

    # Elevate user to institution_admin
    elevate_response = pocketbase_admin_client.patch(
        f"/api/collections/users/records/{user_id}",
        json={"role": "institution_admin"},
    )
    assert elevate_response.status_code == 200, (
        f"Failed to elevate user '{username}' to institution_admin: "
        f"{elevate_response.status_code} - {elevate_response.text}"
    )

    # Logout and clear cookies
    test_app.post("/api/v1/auth/logout")
    test_app.cookies.clear()

    # Re-login to get updated role in session
    login_response = test_app.post(
        "/api/v1/auth/login",
        json={
            "identity": username,
            "password": password,
            "keep_logged_in": True,
        },
    )
    assert login_response.status_code == 200, (
        f"Failed to re-login as '{username}': {login_response.status_code} - {login_response.text}"
    )

    return user_id


def register_and_login_user(
    test_app,
    username: str | None = None,
    password: str | None = None,
    name: str | None = None,
) -> dict:
    """
    Helper function to register and login a test user.

    Args:
        test_app: FastAPI TestClient
        username: Username for the user (auto-generated if not provided)
        password: Password for the user (default: "SecurePassword123!")
        name: Display name for the user (default: "Test User")

    Returns:
        dict with:
            - username: The username used
            - password: The password used
            - name: The display name used
            - cookies: Authentication cookies from login
            - user_record: The user record from registration
    """

    # Generate unique username if not provided
    if username is None:
        unique_suffix = secrets.token_hex(4)
        username = f"testuser_{unique_suffix}"

    user_data: dict[str, str | dict] = {
        "username": username,
        "password": password or "SecurePassword123!",
        "name": name or "Test User",
        "magic_word": "test",  # Default test institution magic word
        "institution_short_code": "TEST",  # Default test institution
    }

    # Verify magic word
    verify_response = test_app.post(
        "/api/v1/auth/verify-magic-word",
        json={
            "magic_word": user_data["magic_word"],
            "institution_short_code": user_data["institution_short_code"],
        },
    )
    assert verify_response.status_code == 200, (
        f"Failed to verify magic word: {verify_response.status_code} - {verify_response.text}"
    )
    magic_word_body = verify_response.json()
    user_data["reg_token"] = magic_word_body["token"]

    # Register user
    register_response = test_app.post(
        "/api/v1/auth/register",
        json={
            "identity": user_data["username"],
            "password": user_data["password"],
            "passwordConfirm": user_data["password"],
            "name": user_data["name"],
            "registration_token": user_data["reg_token"],
        },
    )
    assert register_response.status_code == 200, (
        f"Failed to register user: {register_response.status_code} - {register_response.text}"
    )
    register_body = register_response.json()
    if "record" in register_body:
        user_data["user_record"] = register_body["record"]

    # Login
    login_response = test_app.post(
        "/api/v1/auth/login",
        json={
            "identity": user_data["username"],
            "password": user_data["password"],
        },
    )
    assert login_response.status_code == 200, (
        f"Failed to login: {login_response.status_code} - {login_response.text}"
    )
    # Cookies are automatically captured by TestClient, no need to return them
    # user_data["cookies"] = dict(login_response.cookies)

    return user_data


def _clean_pocketbase_collections(admin_client: httpx.Client) -> None:
    """Clean all test data from PocketBase collections.

    This removes all records from user-created collections while preserving
    system collections, the default test institution, and the service account.

    Args:
        admin_client: Authenticated PocketBase admin client
    """
    # Import here to avoid circular imports and to get the actual service account ID
    from priotag.services.service_account import SERVICE_ACCOUNT_ID

    # Clean priorities and vacation_days completely
    for collection in ["priorities", "vacation_days"]:
        try:
            response = admin_client.get(
                f"/api/collections/{collection}/records", params={"perPage": 500}
            )
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])

                for item in items:
                    delete_response = admin_client.delete(
                        f"/api/collections/{collection}/records/{item['id']}"
                    )
                    if delete_response.status_code not in [200, 204, 404]:
                        print(
                            f"Warning: Failed to delete {collection} record {item['id']}: {delete_response.status_code}"
                        )
        except Exception as e:
            print(f"Warning: Error cleaning {collection}: {e}")

    # Clean users but keep the service account
    try:
        response = admin_client.get(
            "/api/collections/users/records",
            params={"perPage": 500, "filter": f'username!="{SERVICE_ACCOUNT_ID}"'},
        )
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])

            for item in items:
                delete_response = admin_client.delete(
                    f"/api/collections/users/records/{item['id']}"
                )
                if delete_response.status_code not in [200, 204, 404]:
                    print(
                        f"Warning: Failed to delete user {item['id']}: {delete_response.status_code}"
                    )
    except Exception as e:
        print(f"Warning: Error cleaning users: {e}")

    # Clean institutions but keep the default TEST institution
    # Use client-side filtering for more reliability
    try:
        response = admin_client.get(
            "/api/collections/institutions/records",
            params={"perPage": 500},
        )
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])

            for item in items:
                # Skip deletion if this is the TEST institution
                if item.get("short_code") == "TEST":
                    continue

                delete_response = admin_client.delete(
                    f"/api/collections/institutions/records/{item['id']}"
                )
                if delete_response.status_code not in [200, 204, 404]:
                    print(
                        f"Warning: Failed to delete institution {item['id']}: {delete_response.status_code}"
                    )
    except Exception as e:
        print(f"Warning: Error cleaning institutions: {e}")


# ---------------------------------------------------------------------------- #
#                                   FIXTURES                                   #
# ---------------------------------------------------------------------------- #


@pytest.fixture(scope="session")
def redis_container() -> Generator[DockerContainer | None, None, None]:
    """Start a Redis container for integration tests (or skip if using docker-compose)."""
    if USE_DOCKER_SERVICES:
        # Skip testcontainers, we'll use docker-compose services
        yield None
        return

    container = (
        DockerContainer("redis:8-alpine")
        .with_bind_ports("6379/tcp", 6379)
        .waiting_for(LogMessageWaitStrategy("Ready to accept connections"))
    )
    container.start()

    yield container

    container.stop()


@pytest.fixture(scope="session")
def redis_client(
    redis_container: DockerContainer | None,
) -> Generator[redis.Redis, None, None]:
    """Get a Redis client connected to the test container or docker-compose service."""
    if USE_DOCKER_SERVICES:
        # In docker-compose mode, create an independent Redis client
        # instead of using the shared redis_service singleton
        import os

        redis_pass = open("/run/secrets/redis_pass").read().strip()
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")

        # Parse URL to get host/port
        from urllib.parse import urlparse

        parsed = urlparse(redis_url)

        client = redis.Redis(
            host=parsed.hostname or "redis",
            port=parsed.port or 6379,
            password=redis_pass,
            decode_responses=True,
        )
    else:
        # Connect to testcontainer
        assert redis_container is not None, "redis container not loaded"
        client = redis.Redis(
            host=redis_container.get_container_host_ip(),
            port=redis_container.get_exposed_port(6379),
            decode_responses=True,
        )

    # Wait for Redis to be ready
    for _ in range(30):
        try:
            client.ping()
            break
        except redis.ConnectionError:
            time.sleep(0.1)

    yield client

    # Close client connection
    client.close()


@pytest.fixture(scope="function")
def clean_redis(redis_client: redis.Redis) -> Generator[redis.Redis, None, None]:
    """Provide a clean Redis instance for each test."""
    redis_client.flushdb()
    yield redis_client
    redis_client.flushdb()


@pytest.fixture(scope="session")
def pocketbase_container(redis_client) -> Generator[DockerContainer | None, None, None]:
    """Start a PocketBase container for integration tests (or use docker-compose service)."""
    if USE_DOCKER_SERVICES:
        # Use docker-compose pocketbase service
        # NOTE: In docker-compose mode, PocketBase setup is handled by the CI script
        # (setup_pocketbase.py) before tests run, so we don't need to set it up here.
        yield None
        return

    # Start testcontainer
    superuser_login = "admin@example.com"
    superuser_password = "admintest"

    migrations_dir = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "pocketbase"
        / "pb_migrations"
    )

    print(f"Mounting migrations from: {migrations_dir}")
    print(f"Migrations exist: {migrations_dir.exists()}")
    if migrations_dir.exists():
        print(f"Migration files: {len(os.listdir(migrations_dir))}")

    container = (
        DockerContainer("ghcr.io/muchobien/pocketbase:latest")
        .with_bind_ports("8090/tcp", 8090)
        .with_env("PB_ADMIN_EMAIL", superuser_login)
        .with_env("PB_ADMIN_PASSWORD", superuser_password)
        .with_volume_mapping(migrations_dir, "/pb_migrations", mode="ro")
        .waiting_for(LogMessageWaitStrategy("Server started"))
    )
    container.start()

    host = container.get_container_host_ip()
    port = container.get_exposed_port(8090)
    pocketbase_url = f"http://{host}:{port}"
    os.environ["POCKETBASE_URL"] = pocketbase_url

    # Store setup result globally for access by fixtures
    global _POCKETBASE_SETUP_RESULT

    _POCKETBASE_SETUP_RESULT = setup_pocketbase()

    yield container

    container.stop()


@pytest.fixture(scope="function")
def pocketbase_url(monkeypatch, pocketbase_container):
    from priotag.services import pocketbase_service, service_account

    if USE_DOCKER_SERVICES:
        pocketbase_url = pocketbase_service.POCKETBASE_URL
    else:
        host = pocketbase_container.get_container_host_ip()
        port = pocketbase_container.get_exposed_port(8090)
        pocketbase_url = f"http://{host}:{port}"
        monkeypatch.setattr(pocketbase_service, "POCKETBASE_URL", pocketbase_url)
        # Also patch service_account module which imports POCKETBASE_URL directly
        monkeypatch.setattr(service_account, "POCKETBASE_URL", pocketbase_url)

        # Patch all route modules that import POCKETBASE_URL directly
        # This is necessary because Python imports create local copies of the constant
        try:
            from priotag import utils
            from priotag.api.routes import account, auth, priorities, vacation_days
            from priotag.services import institution

            monkeypatch.setattr(priorities, "POCKETBASE_URL", pocketbase_url)
            monkeypatch.setattr(vacation_days, "POCKETBASE_URL", pocketbase_url)
            monkeypatch.setattr(account, "POCKETBASE_URL", pocketbase_url)
            monkeypatch.setattr(auth, "POCKETBASE_URL", pocketbase_url)
            monkeypatch.setattr(institution, "POCKETBASE_URL", pocketbase_url)
            monkeypatch.setattr(utils, "POCKETBASE_URL", pocketbase_url)

        except (ImportError, AttributeError):
            # Modules may not be imported yet
            pass

    return pocketbase_url


@pytest.fixture(scope="session")
def test_institution_keypair(pocketbase_container):
    """
    Get the test institution's admin keypair for integration tests.

    This keypair can be used to decrypt admin_wrapped_dek fields in tests.
    Returns None in docker-compose mode (keypair not available).
    """
    if USE_DOCKER_SERVICES:
        # In docker-compose mode, we don't have access to the keypair
        return None

    global _POCKETBASE_SETUP_RESULT
    if _POCKETBASE_SETUP_RESULT is None:
        return None

    return _POCKETBASE_SETUP_RESULT.get("institution_keypair")


@pytest.fixture(scope="function")
def pocketbase_admin_client(pocketbase_url: str) -> Generator[httpx.Client, None, None]:
    """
    Create an authenticated admin client for PocketBase.

    Sets up an admin user and returns an authenticated client.
    """
    client = httpx.Client(base_url=pocketbase_url, timeout=10.0)

    # Create admin user (PocketBase in --dev mode allows this)
    superuser_login = "admin@example.com"
    superuser_password = "admintest"

    response = client.post(
        "/api/collections/_superusers/auth-with-password",
        json={
            "identity": superuser_login,
            "password": superuser_password,
        },
    )
    assert response.status_code == 200
    response_body = response.json()
    token = response_body["token"]

    client.headers["Authorization"] = f"Bearer {token}"

    # Clean collections before test
    _clean_pocketbase_collections(client)

    yield client

    # Clean collections after test
    _clean_pocketbase_collections(client)
    client.close()


@pytest.fixture(scope="function", autouse=True)
def reset_redis_singleton():
    """
    Reset Redis service singleton state before each integration test.

    This is necessary because unit tests may have already imported and
    initialized the redis_service module, leaving stale state.
    """
    from priotag.services import redis_service

    # Reset singleton state
    redis_service._redis_service._redis_url = None
    redis_service._redis_service._pool = None

    yield

    # Clean up after test
    redis_service.close_redis()


@pytest.fixture(scope="function")
def test_app(pocketbase_url: str, clean_redis: redis.Redis):
    """
    Create a FastAPI test application with real dependencies.

    Uses the real PocketBase and Redis containers.
    """
    # Import app fresh to avoid stale state from unit tests
    import sys

    from fastapi.testclient import TestClient

    from priotag.services.redis_service import get_redis

    # Remove cached module if it exists
    if "priotag.main" in sys.modules:
        del sys.modules["priotag.main"]

    # Import fresh app instance
    from priotag.main import app

    # Override get_redis dependency BEFORE creating TestClient
    # This ensures the dependency override is in place before lifespan runs
    if not USE_DOCKER_SERVICES:

        def get_test_redis():
            return clean_redis

        app.dependency_overrides[get_redis] = get_test_redis

    # Create test client (this triggers lifespan startup)
    client = TestClient(app)

    yield client

    # Clean up dependency overrides
    if not USE_DOCKER_SERVICES:
        app.dependency_overrides.clear()
