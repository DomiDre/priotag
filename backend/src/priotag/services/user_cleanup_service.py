"""Background service for cleaning up inactive user accounts"""

import logging
import os
import time
from datetime import datetime

import httpx
from dateutil.relativedelta import relativedelta

from priotag.middleware.metrics import track_user_cleanup_run
from priotag.services.pocketbase_service import POCKETBASE_URL
from priotag.services.service_account import authenticate_service_account

logger = logging.getLogger(__name__)

# Default: 6 months of inactivity before deletion
USER_INACTIVITY_MONTHS = int(os.getenv("USER_INACTIVITY_MONTHS", "6"))


async def cleanup_inactive_users():
    """
    Delete user accounts that have been inactive for more than the configured period.

    A user is considered inactive if their lastSeen timestamp is older than
    USER_INACTIVITY_MONTHS (default: 6 months).

    This function also deletes all associated user data (priorities, etc.).
    """
    start_time = time.time()
    total_deleted = 0
    total_failed = 0
    success = False

    try:
        # Calculate cutoff date
        now = datetime.now()
        cutoff_date = now - relativedelta(months=USER_INACTIVITY_MONTHS)
        cutoff_iso = cutoff_date.isoformat()

        logger.info(
            f"Starting cleanup of inactive users (last seen before {cutoff_date.strftime('%Y-%m-%d')}, "
            f"inactivity threshold: {USER_INACTIVITY_MONTHS} months)"
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Authenticate as service account to access all records
            service_token = await authenticate_service_account(client)

            if not service_token:
                logger.error(
                    "Cannot proceed with user cleanup without service account authentication"
                )
                return

            headers = {"Authorization": f"Bearer {service_token}"}

            # Query for inactive users
            # Note: We exclude admin and service accounts from cleanup
            page = 1

            while True:
                response = await client.get(
                    f"{POCKETBASE_URL}/api/collections/users/records",
                    headers=headers,
                    params={
                        "filter": f'lastSeen < "{cutoff_iso}" && role != "institution_admin" && role != "super_admin" && role != "service"',
                        "perPage": 50,  # Process in smaller batches
                        "page": page,
                    },
                )

                if response.status_code != 200:
                    logger.error(
                        f"Failed to fetch inactive users (page {page}): "
                        f"{response.status_code} - {response.text}"
                    )
                    break

                data = response.json()
                items = data.get("items", [])

                if not items:
                    # No more records to process
                    break

                logger.info(
                    f"Processing page {page}: found {len(items)} inactive users to delete"
                )

                # Delete each inactive user
                for user in items:
                    user_id = user["id"]
                    username = user.get("username", "unknown")
                    last_seen = user.get("lastSeen", "unknown")

                    try:
                        # First, delete all user's priorities
                        priorities_response = await client.get(
                            f"{POCKETBASE_URL}/api/collections/priorities/records",
                            headers=headers,
                            params={
                                "filter": f'userId = "{user_id}"',
                                "perPage": 500,
                            },
                        )

                        if priorities_response.status_code == 200:
                            priorities = priorities_response.json().get("items", [])
                            for priority in priorities:
                                await client.delete(
                                    f"{POCKETBASE_URL}/api/collections/priorities/records/{priority['id']}",
                                    headers=headers,
                                )
                            logger.debug(
                                f"Deleted {len(priorities)} priorities for user {username}"
                            )

                        # Delete the user account
                        delete_response = await client.delete(
                            f"{POCKETBASE_URL}/api/collections/users/records/{user_id}",
                            headers=headers,
                        )

                        if delete_response.status_code in [200, 204]:
                            total_deleted += 1
                            logger.info(
                                f"Deleted inactive user {username} (ID: {user_id}, "
                                f"last seen: {last_seen})"
                            )
                        else:
                            total_failed += 1
                            logger.warning(
                                f"Failed to delete user {username}: "
                                f"{delete_response.status_code} - {delete_response.text}"
                            )
                    except Exception as e:
                        total_failed += 1
                        logger.error(f"Error deleting user {username}: {e}")

                # Check if there are more pages
                if len(items) < 50:
                    # Last page
                    break

                page += 1

            if total_deleted == 0 and total_failed == 0:
                logger.info("No inactive users to clean up")
            else:
                logger.info(
                    f"User cleanup complete: {total_deleted} deleted, {total_failed} failed"
                )

            # Mark as successful if we completed without exceptions
            success = True

    except httpx.RequestError as e:
        logger.error(f"Network error during user cleanup: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during user cleanup: {e}")
    finally:
        # Track metrics regardless of success/failure
        duration = time.time() - start_time
        track_user_cleanup_run(success, total_deleted, total_failed, duration)
