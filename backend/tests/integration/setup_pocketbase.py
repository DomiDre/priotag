"""
Setup script for PocketBase in CI mode and testcontainers.

This script initializes PocketBase and initial contents account.
It should be run from inside the backend container before tests.
"""

import os
import time

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from priotag.services import service_account


def setup_pocketbase() -> dict:
    """Set up PocketBase with required data (institution and service account)."""
    pocketbase_url = os.getenv("POCKETBASE_URL", "http://pocketbase:8090")
    superuser_login = "admin@example.com"
    superuser_password = "admintest"

    print(f"Setting up PocketBase at {pocketbase_url}...")

    # Wait for PocketBase to be ready
    print("Waiting for PocketBase to be ready...")
    for i in range(60):
        try:
            response = httpx.get(f"{pocketbase_url}/api/health", timeout=1.0)
            if response.status_code == 200:
                print("✓ PocketBase is ready")
                break
        except (httpx.RequestError, httpx.TimeoutException):
            if i % 10 == 0:
                print(f"  Still waiting... ({i}s)")
            time.sleep(1)
    else:
        raise RuntimeError("PocketBase did not become ready in time")

    client = httpx.Client(base_url=pocketbase_url, timeout=10.0)

    # Authenticate as admin
    print("Authenticating as admin...")
    response = client.post(
        "/api/collections/_superusers/auth-with-password",
        json={
            "identity": superuser_login,
            "password": superuser_password,
        },
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to authenticate as admin: {response.status_code} - {response.text}"
        )
    token = response.json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    print("✓ Authenticated as admin")

    # Create default test institution
    print("Creating default test institution...")

    # Generate a test admin keypair for the institution (save for test use)

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    admin_public_key = public_pem.decode()

    institution_data = {
        "name": "Test Institution",
        "short_code": "TEST",
        "registration_magic_word": "test",
        "admin_public_key": admin_public_key,
        "active": True,
        "settings": {},
    }
    create_response = client.post(
        "/api/collections/institutions/records",
        json=institution_data,
    )
    if create_response.status_code != 200:
        raise RuntimeError(
            f"Failed to create institution: {create_response.status_code} - {create_response.text}"
        )
    institution = create_response.json()
    print(
        f"✓ Institution created (id={institution['id']}, short_code={institution['short_code']})"
    )

    # Create service account

    print(f"Creating service account ({service_account.SERVICE_ACCOUNT_ID})...")
    service_response = client.post(
        "/api/collections/users/records",
        json={
            "username": service_account.SERVICE_ACCOUNT_ID,
            "password": service_account.SERVICE_ACCOUNT_PASSWORD,
            "passwordConfirm": service_account.SERVICE_ACCOUNT_PASSWORD,
            "role": "service",
            "institution_id": institution[
                "id"
            ],  # Associate service account with default TEST institution
        },
    )
    # Note: It's OK if this fails with 400 (duplicate) - the account may already exist
    if service_response.status_code == 200:
        print("✓ Service account created")
    else:
        print(
            f"⚠ Service account creation returned {service_response.status_code}: {service_response.text}"
        )
        print("  (This may be OK if the account already exists)")

    client.close()

    print("\n✅ PocketBase setup complete!")
    print(f"   Institution ID: {institution['id']}")
    print(f"   Institution short_code: {institution['short_code']}")
    # Return institution and keypair for tests to use
    return {
        "institution": institution,
        "institution_keypair": {
            "private_key": private_key,
            "public_pem": public_pem,
            "private_pem": private_pem,
        },
    }


if __name__ == "__main__":
    setup_pocketbase()
