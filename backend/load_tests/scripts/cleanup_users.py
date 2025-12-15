#!/usr/bin/env python3
"""
Cleanup script for removing load test users.

This script removes all users created during load testing.
Use this after running tests to clean up the database.

Usage:
    python scripts/cleanup_users.py [--prefix loadtest_user] [--dry-run]

Options:
    --prefix: User prefix to match (default: from config)
    --dry-run: Show what would be deleted without actually deleting
    --host: Backend host URL (default: from config)
"""

import argparse
import sys
import requests
from typing import List

# Add parent directory to path to import config
sys.path.insert(0, '..')

from config import config


def get_admin_token(host: str, admin_username: str, admin_password: str) -> tuple[dict, bool]:
    """
    Login as admin and get auth token.

    Returns:
        Tuple of (cookies dict, success bool)
    """
    url = f"{host}{config.API_PREFIX}/auth/login"
    response = requests.post(
        url,
        json={
            "identity": admin_username,
            "password": admin_password,
            "keep_logged_in": False,
        }
    )

    if response.status_code == 200:
        return dict(response.cookies), True
    else:
        print(f"Failed to login as admin: {response.status_code}")
        print(response.text)
        return {}, False


def list_users(host: str, cookies: dict) -> List[dict]:
    """
    Get list of all users (requires admin privileges).

    Note: This may need to be adapted based on your actual admin API.
    """
    # This would require an admin endpoint to list users
    # Since we don't have one in the API, we'll work with known user IDs
    return []


def delete_user_by_username(host: str, cookies: dict, username: str, dry_run: bool = False) -> bool:
    """
    Delete a user account by username.

    Note: This requires logging in as that user or using admin privileges.
    """
    if dry_run:
        print(f"[DRY RUN] Would delete user: {username}")
        return True

    # Login as the user
    login_url = f"{host}{config.API_PREFIX}/auth/login"
    response = requests.post(
        login_url,
        json={
            "identity": username,
            "password": config.USER_PASSWORD,
            "keep_logged_in": False,
        }
    )

    if response.status_code != 200:
        print(f"Failed to login as {username}: {response.status_code}")
        return False

    user_cookies = dict(response.cookies)

    # Delete the account
    delete_url = f"{host}{config.API_PREFIX}/account/delete"
    response = requests.delete(delete_url, cookies=user_cookies)

    if response.status_code == 200:
        print(f"Deleted user: {username}")
        return True
    else:
        print(f"Failed to delete {username}: {response.status_code}")
        return False


def cleanup_load_test_users(
    host: str,
    prefix: str,
    max_users: int = 1000,
    dry_run: bool = False
):
    """
    Clean up load test users by attempting to delete accounts with the given prefix.

    Args:
        host: Backend host URL
        prefix: Username prefix to match
        max_users: Maximum number of users to attempt (default: 1000)
        dry_run: If True, only show what would be deleted
    """
    print(f"Cleaning up load test users with prefix: {prefix}")
    print(f"Host: {host}")
    print(f"Max users to check: {max_users}")
    if dry_run:
        print("[DRY RUN MODE - No actual deletions will occur]")
    print("")

    deleted_count = 0
    failed_count = 0
    not_found_count = 0

    # Try to delete users from 1 to max_users
    for i in range(1, max_users + 1):
        username = f"{prefix}_{i}"

        # Try to login as the user to check if it exists
        login_url = f"{host}{config.API_PREFIX}/auth/login"
        response = requests.post(
            login_url,
            json={
                "identity": username,
                "password": config.USER_PASSWORD,
                "keep_logged_in": False,
            }
        )

        if response.status_code == 401:
            # User doesn't exist or wrong password
            not_found_count += 1
            if not_found_count > 20:  # Stop if we haven't found users for a while
                print(f"\nNo more users found after {username}")
                break
            continue
        elif response.status_code != 200:
            failed_count += 1
            continue

        # User exists, reset not_found counter
        not_found_count = 0

        # Delete the user
        user_cookies = dict(response.cookies)

        if dry_run:
            print(f"[DRY RUN] Would delete user: {username}")
            deleted_count += 1
        else:
            delete_url = f"{host}{config.API_PREFIX}/account/delete"
            response = requests.delete(delete_url, cookies=user_cookies)

            if response.status_code == 200:
                print(f"Deleted user: {username}")
                deleted_count += 1
            else:
                print(f"Failed to delete {username}: {response.status_code}")
                failed_count += 1

    print("\n" + "=" * 60)
    print("Cleanup Summary")
    print("=" * 60)
    print(f"Users deleted: {deleted_count}")
    print(f"Failed deletions: {failed_count}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Clean up load test users from the database"
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default=config.USER_PREFIX,
        help=f"Username prefix to match (default: {config.USER_PREFIX})"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=config.BASE_URL,
        help=f"Backend host URL (default: {config.BASE_URL})"
    )
    parser.add_argument(
        "--max-users",
        type=int,
        default=1000,
        help="Maximum number of users to check (default: 1000)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )

    args = parser.parse_args()

    cleanup_load_test_users(
        host=args.host,
        prefix=args.prefix,
        max_users=args.max_users,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
