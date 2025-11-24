#!/usr/bin/env python3
"""
Script to create a new institution in the multi-institution system.

This script creates a new institution with:
- Name and short code
- Magic word for registration
- Optional admin public key for encryption
- Settings dictionary
"""

import asyncio
import secrets
import sys
from pathlib import Path

import httpx

# Add parent directory to path to import priotag modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from priotag.services.pocketbase_service import POCKETBASE_URL
from priotag.services.service_account import authenticate_service_account


def generate_magic_word():
    """Generate a random magic word."""
    # Generate a pronounceable-ish magic word
    words = [
        "Alpha",
        "Beta",
        "Gamma",
        "Delta",
        "Epsilon",
        "Zeta",
        "Eta",
        "Theta",
        "Iota",
        "Kappa",
        "Lambda",
        "Sigma",
        "Omega",
        "Phoenix",
        "Dragon",
        "Tiger",
        "Eagle",
        "Falcon",
        "Hawk",
        "Lion",
        "Bear",
        "Wolf",
    ]
    numbers = secrets.randbelow(10000)
    word = secrets.choice(words)
    return f"{word}{numbers:04d}"


async def create_institution():
    """Main function to create an institution."""
    print("=" * 80)
    print("CREATE NEW INSTITUTION")
    print("=" * 80)
    print()

    # Get institution details from user
    institution_name = input("Enter institution name: ").strip()
    if not institution_name:
        print("Error: Institution name cannot be empty")
        return

    institution_short_code = (
        input("Enter institution short code (uppercase, e.g., 'MIT', 'STANFORD'): ")
        .strip()
        .upper()
    )
    if not institution_short_code:
        print("Error: Short code cannot be empty")
        return

    # Validate short code format
    if not institution_short_code.replace("_", "").isalnum():
        print("Error: Short code must contain only letters, numbers, and underscores")
        return

    # Generate or input magic word
    print("\nMagic word options:")
    print("1. Generate random magic word")
    print("2. Enter custom magic word")
    choice = input("Choose option (1 or 2): ").strip()

    if choice == "1":
        magic_word = generate_magic_word()
        print(f"Generated magic word: {magic_word}")
    elif choice == "2":
        magic_word = input("Enter magic word: ").strip()
        if not magic_word:
            print("Error: Magic word cannot be empty")
            return
    else:
        print("Invalid choice")
        return

    # Optional: admin public key
    print("\nAdmin public key (optional, press Enter to skip):")
    print("If you have a separate RSA public key for this institution's admins,")
    print("paste it here. Otherwise, press Enter to use the global admin key.")
    admin_public_key = input("Admin public key: ").strip()

    # Confirm before creating
    print("\n" + "=" * 80)
    print("CONFIRM INSTITUTION DETAILS")
    print("=" * 80)
    print(f"Name: {institution_name}")
    print(f"Short Code: {institution_short_code}")
    print(f"Magic Word: {magic_word}")
    print(f"Admin Public Key: {'(provided)' if admin_public_key else '(using global)'}")
    print()
    confirm = input("Create this institution? (yes/no): ").strip().lower()

    if confirm not in ["yes", "y"]:
        print("Cancelled.")
        return

    # Create institution
    async with httpx.AsyncClient() as client:
        service_token = await authenticate_service_account(client)
        if not service_token:
            print("Error: Failed to authenticate service account")
            print(
                "Make sure you're running this as a super admin or with service account credentials"
            )
            return

        headers = {"Authorization": f"Bearer {service_token}"}

        institution_data = {
            "name": institution_name,
            "short_code": institution_short_code,
            "registration_magic_word": magic_word,
            "active": True,
            "settings": {},
        }

        if admin_public_key:
            institution_data["admin_public_key"] = admin_public_key

        print("\nCreating institution...")
        response = await client.post(
            f"{POCKETBASE_URL}/api/collections/institutions/records",
            json=institution_data,
            headers=headers,
        )

        if response.status_code == 200:
            institution = response.json()
            print("\n" + "=" * 80)
            print("✓ INSTITUTION CREATED SUCCESSFULLY")
            print("=" * 80)
            print(f"ID: {institution['id']}")
            print(f"Name: {institution['name']}")
            print(f"Short Code: {institution['short_code']}")
            print(f"Magic Word: {institution['registration_magic_word']}")
            print(f"Active: {institution['active']}")
            print()
            print("Next steps:")
            print("1. Generate QR codes for registration:")
            print(
                f'   python generate_qr_codes.py --institution {institution_short_code} --magic-word "{magic_word}"'
            )
            print("2. Elevate users to institution_admin for this institution:")
            print(
                f"   python elevate_user_to_admin.py --institution-id {institution['id']}"
            )
            print()
        else:
            error_data = response.json()
            print("\n✗ ERROR CREATING INSTITUTION")
            print(f"Status: {response.status_code}")
            print(f"Details: {error_data}")
            print()
            # Print specific field errors if available
            if "data" in error_data:
                print("Field errors:")
                for field, msgs in error_data["data"].items():
                    print(f"  - {field}: {msgs}")


if __name__ == "__main__":
    asyncio.run(create_institution())
