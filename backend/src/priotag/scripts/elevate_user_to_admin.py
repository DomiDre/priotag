#!/usr/bin/env python3
"""
Script to elevate a user to admin (institution_admin or super_admin).

Usage:
  # Elevate to institution_admin (requires institution)
  python elevate_user_to_admin.py

  # Elevate to super_admin
  python elevate_user_to_admin.py --super
"""

import argparse
import getpass
import sys

import requests

from priotag.services.pocketbase_service import POCKETBASE_URL


def main():
    parser = argparse.ArgumentParser(
        description="Elevate a user to admin (institution_admin or super_admin)"
    )
    parser.add_argument(
        "--super",
        action="store_true",
        help="Elevate to super_admin instead of institution_admin",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("ELEVATE USER TO ADMIN")
    print("=" * 80)
    print()

    # Authenticate as superuser
    print("Superuser authentication required (PocketBase admin):")
    superuser_login = input("Superuser login: ")
    superuser_password = getpass.getpass("Superuser password: ")

    try:
        pb_response = requests.post(
            f"{POCKETBASE_URL}/api/collections/_superusers/auth-with-password",
            json={
                "identity": superuser_login,
                "password": superuser_password,
            },
            timeout=10,
        )
        response_body = pb_response.json()
        token = response_body["token"]
        print("✓ Superuser authenticated\n")
    except Exception as e:
        sys.exit(f"Failed to login as superuser: {e}")

    # Get target user
    target_user = input("Enter username to elevate: ")

    response = requests.get(
        f"{POCKETBASE_URL}/api/collections/users/records",
        params={"filter": f'username="{target_user}"'},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )

    if response.status_code != 200:
        sys.exit(f"Failed to find user: {response.text}")

    users = response.json()["items"]
    if not users:
        sys.exit(f"User '{target_user}' not found")

    user_data = users[0]
    user_id = user_data["id"]

    print("\nFound user:")
    print(f"  ID: {user_id}")
    print(f"  Username: {user_data['username']}")
    print(f"  Current role: {user_data.get('role', 'user')}")
    print(f"  Institution ID: {user_data.get('institution_id', 'None')}")
    print()

    # Determine target role
    if args.super:
        new_role = "super_admin"
        update_data = {
            "role": new_role,
            "institution_id": None,  # Super admins have no institution
        }
        print("Elevating to: super_admin (no institution)")
    else:
        new_role = "institution_admin"

        # Check if user has an institution
        if not user_data.get("institution_id"):
            print("User has no institution_id assigned.")
            print("\nOptions:")
            print("1. List institutions and assign one")
            print("2. Cancel")
            choice = input("Choose option (1 or 2): ").strip()

            if choice == "1":
                # List institutions
                response = requests.get(
                    f"{POCKETBASE_URL}/api/collections/institutions/records",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10,
                )

                if response.status_code != 200:
                    sys.exit(f"Failed to fetch institutions: {response.text}")

                institutions = response.json()["items"]
                if not institutions:
                    sys.exit("No institutions found. Create one first.")

                print("\nAvailable institutions:")
                for i, inst in enumerate(institutions, 1):
                    print(
                        f"{i}. {inst['name']} ({inst['short_code']}) - ID: {inst['id']}"
                    )

                inst_choice = int(input("\nSelect institution number: ")) - 1
                if inst_choice < 0 or inst_choice >= len(institutions):
                    sys.exit("Invalid choice")

                institution_id = institutions[inst_choice]["id"]
                institution_name = institutions[inst_choice]["name"]
            else:
                sys.exit("Cancelled")
        else:
            institution_id = user_data["institution_id"]
            # Fetch institution name
            response = requests.get(
                f"{POCKETBASE_URL}/api/collections/institutions/records/{institution_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            if response.status_code == 200:
                institution_name = response.json()["name"]
            else:
                institution_name = "Unknown"

        update_data = {
            "role": new_role,
            "institution_id": institution_id,
        }
        print(f"Elevating to: institution_admin for {institution_name}")

    print()
    confirm = input("Confirm elevation? (yes/no): ").strip().lower()

    if confirm not in ["yes", "y"]:
        print("Cancelled.")
        return

    # Update user
    response = requests.patch(
        f"{POCKETBASE_URL}/api/collections/users/records/{user_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )

    if response.status_code == 200:
        print("\n" + "=" * 80)
        print("✓ USER ELEVATED SUCCESSFULLY")
        print("=" * 80)
        updated_user = response.json()
        print(f"Username: {updated_user['username']}")
        print(f"Role: {updated_user['role']}")
        print(f"Institution ID: {updated_user.get('institution_id', 'None')}")
        print()
    else:
        print("\n✗ FAILED TO ELEVATE USER")
        print(f"Status: {response.status_code}")
        print(f"Error: {response.text}")


if __name__ == "__main__":
    main()
