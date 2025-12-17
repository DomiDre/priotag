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
import requests
import time

from config import config


def cleanup_load_test_users(
    host: str, prefix: str, max_users: int = 1000, dry_run: bool = False
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

    # Try to delete users from 1 to max_users
    for i in range(1, max_users + 1):
        username = f"{prefix}_{i}"

        # Create a new session for each user to avoid connection issues
        session = requests.Session()

        try:
            # Try to login as the user to check if it exists
            login_url = f"{host}{config.API_PREFIX}/auth/login"
            response = session.post(
                login_url,
                json={
                    "identity": username,
                    "password": config.USER_PASSWORD,
                    "keep_logged_in": False,
                },
                timeout=10,
            )

            if response.status_code != 200:
                # User doesn't exist or wrong password
                failed_count += 1
                if failed_count > 10:  # Stop if we fail too often
                    print(f"\nNo more users found after {username}")
                    break
                continue

            if dry_run:
                print(f"[DRY RUN] Would delete user: {username}")
                deleted_count += 1
            else:
                # Delete the user using the same session
                delete_url = f"{host}{config.API_PREFIX}/account/delete"
                delete_response = session.delete(delete_url, timeout=10)

                if delete_response.status_code == 200:
                    print(f"Deleted user: {username}")
                    deleted_count += 1
                else:
                    print(f"Failed to delete {username}: {delete_response.status_code}")
                    failed_count += 1

        except requests.exceptions.RequestException as e:
            print(f"Connection error for {username}: {e}")
            failed_count += 1
        finally:
            # Always close the session
            session.close()

        # Small delay to avoid overwhelming the server
        time.sleep(0.1)

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
        help=f"Username prefix to match (default: {config.USER_PREFIX})",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=config.BASE_URL,
        help=f"Backend host URL (default: {config.BASE_URL})",
    )
    parser.add_argument(
        "--max-users",
        type=int,
        default=1000,
        help="Maximum number of users to check (default: 1000)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )

    args = parser.parse_args()

    cleanup_load_test_users(
        host=args.host,
        prefix=args.prefix,
        max_users=args.max_users,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
