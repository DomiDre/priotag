"""
Configuration for load testing the Priotag backend.
"""

import os


class LoadTestConfig:
    """Configuration for load testing."""

    # Backend URL
    BASE_URL = os.getenv("LOAD_TEST_BASE_URL", "http://localhost:8000")
    API_PREFIX = "/api/v1"

    # Institution configuration
    MAGIC_WORD = os.getenv("LOAD_TEST_MAGIC_WORD", "test-magic-word")
    INSTITUTION_ID = os.getenv("LOAD_TEST_INSTITUTION_ID", None)

    # Test user configuration
    USER_PREFIX = os.getenv("LOAD_TEST_USER_PREFIX", "loadtest_user")
    USER_PASSWORD = os.getenv("LOAD_TEST_USER_PASSWORD", "TestPassword123!")

    # Load test parameters
    MIN_WAIT_TIME = int(os.getenv("LOAD_TEST_MIN_WAIT", "1000"))  # milliseconds
    MAX_WAIT_TIME = int(os.getenv("LOAD_TEST_MAX_WAIT", "3000"))  # milliseconds

    # Priority data configuration
    PRIORITY_VALUES = [1, 2, 3, 4, 5, None]  # Valid priority values

    # Test months to use
    TEST_MONTHS = ["2026-01", "2026-02"]

    # Cleanup configuration
    CLEANUP_USERS = os.getenv("LOAD_TEST_CLEANUP", "true").lower() == "true"

    @classmethod
    def get_api_url(cls, endpoint: str) -> str:
        """Construct full API URL for an endpoint."""
        endpoint = endpoint.lstrip("/")
        return f"{cls.BASE_URL}{cls.API_PREFIX}/{endpoint}"

    @classmethod
    def get_user_credentials(cls, user_index: int) -> tuple[str, str]:
        """Generate username and password for a test user."""
        username = f"{cls.USER_PREFIX}_{user_index}"
        return username, cls.USER_PASSWORD


# Export singleton instance
config = LoadTestConfig()
