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
    --max-retries: Maximum number of retries per request (default: 3)
    --slow-mode: Use slower delays to avoid rate limiting
"""

import argparse
import time

import requests
from config import config


def retry_request(
    func,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    rate_limit_delay: float = 60.0,
) -> requests.Response | None:
    """
    Retry a request function with exponential backoff and rate limit handling.

    Args:
        func: Function that makes the request
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay after each retry
        rate_limit_delay: Base delay when rate limited

    Returns:
        Response object or None if all retries failed
    """
    delay = initial_delay

    for attempt in range(max_retries + 1):  # +1 for rate limit retries
        try:
            response = func()

            # Handle rate limiting
            if response.status_code == 429:
                # Try to get Retry-After header
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait_time = float(retry_after)
                    except ValueError:
                        wait_time = rate_limit_delay
                else:
                    wait_time = rate_limit_delay

                print(f"    Rate limited (429), waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                # Don't count rate limits against retry count
                continue

            return response

        except requests.exceptions.ConnectionError as e:
            if attempt < max_retries:
                print(
                    f"    Connection error (attempt {attempt + 1}/{max_retries}), retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
                delay *= backoff_factor
            else:
                print(f"    Connection failed after {max_retries} attempts: {e}")
                return None
        except requests.exceptions.Timeout as e:
            if attempt < max_retries:
                print(
                    f"    Timeout (attempt {attempt + 1}/{max_retries}), retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
                delay *= backoff_factor
            else:
                print(f"    Timeout after {max_retries} attempts: {e}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"    Request error: {e}")
            return None

    return None


def cleanup_user_range(
    host: str,
    prefix: str,
    start: int,
    end: int,
    dry_run: bool = False,
    max_retries: int = 3,
    delay_between_users: float = 0.5,
    rate_limit_delay: float = 5.0,
) -> tuple[int, int, int]:
    """
    Clean up users in a specific ID range.

    Args:
        host: Backend host URL
        prefix: Username prefix to match
        start: Starting user ID
        end: Ending user ID
        dry_run: If True, only show what would be deleted
        max_retries: Maximum retries per request
        delay_between_users: Delay between user operations in seconds
        rate_limit_delay: Delay when rate limited

    Returns:
        Tuple of (deleted_count, failed_count, skipped_count)
    """
    deleted_count = 0
    failed_count = 0
    skipped_count = 0
    consecutive_failures = 0
    rate_limit_count = 0

    for i in range(start, end + 1):
        username = f"{prefix}_{i}"

        # Create a new session for each user to avoid connection issues
        session = requests.Session()
        # Configure session with longer timeout and retry adapter
        session.mount("http://", requests.adapters.HTTPAdapter(max_retries=0))
        session.mount("https://", requests.adapters.HTTPAdapter(max_retries=0))

        try:
            # Try to login as the user to check if it exists
            login_url = f"{host}{config.API_PREFIX}/auth/login"

            def login_request(session=session, login_url=login_url, username=username):
                return session.post(
                    login_url,
                    json={
                        "identity": username,
                        "password": config.USER_PASSWORD,
                        "keep_logged_in": False,
                    },
                    timeout=15,
                )

            response = retry_request(
                login_request,
                max_retries=max_retries,
                rate_limit_delay=rate_limit_delay,
            )

            if response is None:
                # All retries failed, skip this user
                print(f"  Skipping {username} due to connection issues")
                skipped_count += 1
                consecutive_failures += 1
                if consecutive_failures > 50:
                    print("  Too many consecutive failures, stopping range")
                    break
                continue

            if response.status_code == 429:
                # Still rate limited after retries
                print(f"  Still rate limited for {username}, increasing delay...")
                rate_limit_count += 1
                # Exponentially increase delay if we keep hitting rate limits
                time.sleep(rate_limit_delay * (1.5**rate_limit_count))
                # Don't count as consecutive failure
                continue
            elif response.status_code == 401 or response.status_code == 404:
                # User doesn't exist
                consecutive_failures += 1
                if consecutive_failures > 20:
                    print(f"  No more users found after {username}")
                    break
                continue
            elif response.status_code != 200:
                # Other error
                print(f"  Login failed for {username}: {response.status_code}")
                consecutive_failures += 1
                if consecutive_failures > 30:
                    print("  Too many consecutive failures, stopping range")
                    break
                continue

            # Reset consecutive failures counter
            consecutive_failures = 0
            rate_limit_count = max(
                0, rate_limit_count - 1
            )  # Gradually decrease if successful

            if dry_run:
                print(f"  [DRY RUN] Would delete user: {username}")
                deleted_count += 1
            else:
                # Delete the user using the same session
                delete_url = f"{host}{config.API_PREFIX}/account/delete"

                def delete_request(session=session, delete_url=delete_url):
                    return session.delete(delete_url, timeout=15)

                delete_response = retry_request(
                    delete_request,
                    max_retries=max_retries,
                    rate_limit_delay=rate_limit_delay,
                )

                if delete_response is None:
                    print(f"  Failed to delete {username} due to connection issues")
                    failed_count += 1
                elif delete_response.status_code == 429:
                    print(f"  Rate limited when deleting {username}, will retry later")
                    skipped_count += 1
                    rate_limit_count += 1
                    time.sleep(rate_limit_delay * (1.5**rate_limit_count))
                elif delete_response.status_code == 200:
                    print(f"  ✓ Deleted user: {username}")
                    deleted_count += 1
                else:
                    print(
                        f"  Failed to delete {username}: {delete_response.status_code}"
                    )
                    failed_count += 1

        except Exception as e:
            print(f"  Unexpected error for {username}: {e}")
            failed_count += 1
        finally:
            # Always close the session
            session.close()

        # Delay to avoid overwhelming the server and rate limiting
        time.sleep(delay_between_users)

    return deleted_count, failed_count, skipped_count


def cleanup_load_test_users(
    host: str,
    prefix: str,
    max_users: int = 1000,
    dry_run: bool = False,
    max_retries: int = 3,
    delay_between_users: float = 0.5,
    rate_limit_delay: float = 60.0,
    slow_mode: bool = False,
):
    """
    Clean up load test users by attempting to delete accounts with the given prefix.

    Args:
        host: Backend host URL
        prefix: Username prefix to match
        max_users: Maximum number of users to attempt per range (default: 1000)
        dry_run: If True, only show what would be deleted
        max_retries: Maximum retries per request (default: 3)
        delay_between_users: Delay between user operations (default: 0.5s)
        rate_limit_delay: Delay when rate limited (default: 5.0s)
        slow_mode: Use slower delays to avoid rate limiting
    """
    if slow_mode:
        delay_between_users = max(2.0, delay_between_users)
        rate_limit_delay = max(10.0, rate_limit_delay)
        print("🐢 SLOW MODE ENABLED - Using conservative delays to avoid rate limiting")

    print(f"Cleaning up load test users with prefix: {prefix}")
    print(f"Host: {host}")
    print(f"Max users per range: {max_users}")
    print(f"Max retries per request: {max_retries}")
    print(f"Delay between users: {delay_between_users}s")
    print(f"Rate limit delay: {rate_limit_delay}s")
    if dry_run:
        print("[DRY RUN MODE - No actual deletions will occur]")
    print("")

    total_deleted = 0
    total_failed = 0
    total_skipped = 0

    # Cleanup regular users (PriotagUser - range 1 to max_users)
    print(f"Checking regular users (ID range: 1-{max_users})...")
    deleted, failed, skipped = cleanup_user_range(
        host,
        prefix,
        1,
        max_users,
        dry_run,
        max_retries,
        delay_between_users,
        rate_limit_delay,
    )
    total_deleted += deleted
    total_failed += failed
    total_skipped += skipped

    print("")

    # Add a longer pause between ranges to avoid rate limiting
    if not dry_run and deleted > 0:
        pause_time = 10.0 if slow_mode else 5.0
        print(f"Pausing {pause_time}s before next range to avoid rate limiting...")
        time.sleep(pause_time)

    # Cleanup intensive users (IntensiveUser - range 10001 to 10000+max_users)
    print(f"Checking intensive users (ID range: 10001-{10000 + max_users})...")
    deleted, failed, skipped = cleanup_user_range(
        host,
        prefix,
        10001,
        10000 + max_users,
        dry_run,
        max_retries,
        delay_between_users,
        rate_limit_delay,
    )
    total_deleted += deleted
    total_failed += failed
    total_skipped += skipped

    print("\n" + "=" * 60)
    print("Cleanup Summary")
    print("=" * 60)
    print(f"Total users deleted:  {total_deleted}")
    print(f"Total failed:         {total_failed}")
    print(f"Total skipped:        {total_skipped}")
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
        help="Maximum number of users to check per range (default: 1000)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of retries per request (default: 3)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between user operations in seconds (default: 0.5)",
    )
    parser.add_argument(
        "--rate-limit-delay",
        type=float,
        default=60.0,
        help="Delay when rate limited in seconds (default: 60.0)",
    )
    parser.add_argument(
        "--slow-mode",
        action="store_true",
        help="Use slower, more conservative delays to avoid rate limiting",
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
        max_retries=args.max_retries,
        delay_between_users=args.delay,
        rate_limit_delay=args.rate_limit_delay,
        slow_mode=args.slow_mode,
    )


if __name__ == "__main__":
    main()
