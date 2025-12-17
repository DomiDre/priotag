"""
Utility functions for load testing.
"""

import random
from datetime import datetime, timedelta
from typing import Optional

from config import config


def generate_priority_data(month: str) -> dict:
    """
    Generate realistic priority data for a given month.

    Args:
        month: Month in YYYY-MM format

    Returns:
        Priority data with weeks
    """
    # Parse month to determine number of weeks
    year, month_num = map(int, month.split("-"))
    first_day = datetime(year, month_num, 1)

    # Calculate the number of weeks in this month
    # Assuming we need to cover all days in the month
    if month_num == 12:
        last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(year, month_num + 1, 1) - timedelta(days=1)

    # Calculate week numbers
    weeks = []
    current_date = first_day

    seen_weeks = set()
    week_num = 1
    while current_date <= last_day:
        if week_num not in seen_weeks:
            seen_weeks.add(week_num)
            weeks.append(
                {
                    "weekNumber": week_num,
                    "monday": random.choice(config.PRIORITY_VALUES),
                    "tuesday": random.choice(config.PRIORITY_VALUES),
                    "wednesday": random.choice(config.PRIORITY_VALUES),
                    "thursday": random.choice(config.PRIORITY_VALUES),
                    "friday": random.choice(config.PRIORITY_VALUES),
                }
            )
        current_date += timedelta(days=7)
        week_num += 1

    return {"weeks": weeks}


def generate_week_data(week_number: int) -> dict:
    """
    Generate priority data for a single week.

    Args:
        week_number: ISO week number

    Returns:
        Week data dictionary
    """
    return {
        "weekNumber": week_number,
        "monday": random.choice(config.PRIORITY_VALUES),
        "tuesday": random.choice(config.PRIORITY_VALUES),
        "wednesday": random.choice(config.PRIORITY_VALUES),
        "thursday": random.choice(config.PRIORITY_VALUES),
        "friday": random.choice(config.PRIORITY_VALUES),
    }


def get_current_month() -> str:
    """Get current month in YYYY-MM format."""
    return datetime.now().strftime("%Y-%m")


def get_random_month() -> str:
    """Get a random test month."""
    return random.choice(config.TEST_MONTHS)


class UserSession:
    """Helper class to manage user session data."""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.auth_token: Optional[str] = None
        self.dek: Optional[str] = None
        self.cookies: dict = {}

    def is_authenticated(self) -> bool:
        """Check if user has valid session."""
        return bool(self.cookies.get("auth_token") and self.cookies.get("dek"))

    def update_cookies(self, response):
        """Update cookies from response."""
        if hasattr(response, "cookies"):
            for cookie_name in ["auth_token", "dek"]:
                if cookie_name in response.cookies:
                    self.cookies[cookie_name] = response.cookies[cookie_name]

    def get_cookie_dict(self) -> dict:
        """Get cookies as dictionary for requests."""
        return self.cookies

    def clear_session(self):
        """Clear session data."""
        self.cookies = {}
        self.auth_token = None
        self.dek = None
