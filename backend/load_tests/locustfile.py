"""
Locust load testing file for Priotag backend.

This file defines user behaviors for load testing the Priotag application.
It simulates realistic user workflows including registration, authentication,
and priority management operations.

Usage:
    locust -f locustfile.py --host http://localhost:8000

Environment Variables:
    LOAD_TEST_BASE_URL: Backend URL (default: http://localhost:8000)
    LOAD_TEST_MAGIC_WORD: Institution magic word for registration
    LOAD_TEST_USER_PREFIX: Prefix for test usernames (default: loadtest_user)
    LOAD_TEST_USER_PASSWORD: Password for test users
"""

import random

from config import config
from locust import HttpUser, between, events, task
from locust.exception import RescheduleTask, StopUser
from utils import (
    UserSession,
    generate_priority_data,
    get_next_month,
    get_random_month,
)


class PriotagUser(HttpUser):
    """
    Simulates a regular Priotag user performing typical operations.

    This user will:
    1. Register (if needed)
    2. Login
    3. Create and update priorities
    4. View account information
    5. Logout
    """

    # Wait between 1-3 seconds between tasks (realistic user behavior)
    wait_time = between(config.MIN_WAIT_TIME / 1000, config.MAX_WAIT_TIME / 1000)

    # Class-level counter for unique user IDs
    user_counter = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__class__.user_counter += 1
        self.user_id = self.__class__.user_counter
        self.username, self.password = config.get_user_credentials(self.user_id)
        self.session = UserSession(self.username, self.password)
        self.registered = False
        self.month_priorities = {}  # Track which months have priorities

    def on_start(self):
        """Called when a simulated user starts."""
        # Register and login when user starts
        if not self.registered:
            self.register()
        self.login()

    def on_stop(self):
        """Called when a simulated user stops."""
        # Logout when stopping
        if self.session.is_authenticated():
            self.logout()

    def register(self):
        """Register a new user."""
        # Step 1: Verify magic word
        try:
            response = self.client.post(
                config.get_api_url("auth/verify-magic-word"),
                json={
                    "magic_word": config.MAGIC_WORD,
                    "institution_short_code": config.INSTITUTION_ID,
                },
                name="/api/v1/auth/verify-magic-word",
                timeout=10,  # Add timeout
            )
        except Exception as e:
            print(f"Connection error during magic word verification: {e}")
            raise StopUser() from e

        # Handle status code 0 (connection failed)
        if response.status_code == 0 or not response.text:
            print(f"No response from server (status: {response.status_code})")
            raise RescheduleTask()

        if response.status_code == 429:
            print(f"Hit rate limit when verifying magic word: {response.status_code}")
            raise RescheduleTask()
        elif response.status_code != 200:
            print(
                f"Failed to verify magic word: {response.status_code}, {response.text}"
            )
            raise StopUser()

        registration_token = response.json().get("token")
        if not registration_token:
            print("No registration token received")
            raise StopUser()

        # Step 2: Complete registration
        response = self.client.post(
            config.get_api_url("auth/register"),
            json={
                "registration_token": registration_token,
                "identity": self.username,
                "password": self.password,
                "passwordConfirm": self.password,
                "name": f"Load Test User {self.user_id}",
            },
            name="/api/v1/auth/register",
        )

        if response.status_code == 429:
            print(f"Hit rate limit when registering: {response.status_code}")
            raise RescheduleTask()
        elif response.status_code == 200:
            self.registered = True
            self.session.update_cookies(response)
            print(f"Registered user: {self.username}")
        elif response.status_code == 400:
            # Check if user already exists (handle different error messages)
            response_text = response.text.lower()
            if "already exists" in response_text or "unique" in response_text:
                # User already exists, that's fine - just mark as registered
                self.registered = True
                print(f"User already exists: {self.username}")
            else:
                # Some other 400 error
                print(
                    f"Failed to register user {self.username}: {response.status_code}, {response.text}"
                )
                raise StopUser()
        else:
            print(
                f"Failed to register user {self.username}: {response.status_code}, {response.text}"
            )
            raise StopUser()

    def login(self):
        """Login user."""
        response = self.client.post(
            config.get_api_url("auth/login"),
            json={
                "identity": self.username,
                "password": self.password,
                "keep_logged_in": False,
            },
            name="/api/v1/auth/login",
        )

        if response.status_code == 429:
            print(f"Hit rate limit when verifying magic work: {response.status_code}")
            raise RescheduleTask()
        elif response.status_code == 200:
            self.session.update_cookies(response)
            print(f"Logged in user: {self.username}")
        else:
            print(f"Failed to login user {self.username}: {response.status_code}")
            raise StopUser()

    def logout(self):
        """Logout user."""
        response = self.client.post(
            config.get_api_url("auth/logout"),
            cookies=self.session.get_cookie_dict(),
            name="/api/v1/auth/logout",
        )

        if response.status_code == 429:
            print(f"Hit rate limit when verifying magic work: {response.status_code}")
            raise RescheduleTask()
        elif response.status_code == 200:
            self.session.clear_session()

    @task(10)
    def create_or_update_priority(self):
        """Create or update priority data for a month."""
        if not self.session.is_authenticated():
            return

        month = get_random_month()
        priority_data = generate_priority_data(month)

        response = self.client.put(
            config.get_api_url(f"priorities/{month}"),
            json=priority_data,
            cookies=self.session.get_cookie_dict(),
            name="/api/v1/priorities/{month} [PUT]",
        )

        if response.status_code == 200:
            self.month_priorities[month] = True

    @task(5)
    def get_all_priorities(self):
        """Get all priorities for the user."""
        if not self.session.is_authenticated():
            return

        self.client.get(
            config.get_api_url("priorities"),
            cookies=self.session.get_cookie_dict(),
            name="/api/v1/priorities [GET]",
        )

    @task(3)
    def get_priority_for_month(self):
        """Get priority data for a specific month."""
        if not self.session.is_authenticated():
            return

        month = get_random_month()
        self.client.get(
            config.get_api_url(f"priorities/{month}"),
            cookies=self.session.get_cookie_dict(),
            name="/api/v1/priorities/{month} [GET]",
        )

    @task(2)
    def get_account_info(self):
        """Get account information."""
        if not self.session.is_authenticated():
            return

        self.client.get(
            config.get_api_url("account/info"),
            cookies=self.session.get_cookie_dict(),
            name="/api/v1/account/info",
        )

    @task(1)
    def get_account_data(self):
        """Get all account data including priorities."""
        if not self.session.is_authenticated():
            return

        self.client.get(
            config.get_api_url("account/data"),
            cookies=self.session.get_cookie_dict(),
            name="/api/v1/account/data",
        )

    @task(1)
    def verify_session(self):
        """Verify session is still valid."""
        if not self.session.is_authenticated():
            return

        self.client.get(
            config.get_api_url("auth/verify"),
            cookies=self.session.get_cookie_dict(),
            name="/api/v1/auth/verify",
        )

    @task(1)
    def delete_priority(self):
        """Delete a priority for a random month."""
        if not self.session.is_authenticated() or not self.month_priorities:
            return

        # Only delete if we have created priorities
        month = random.choice(list(self.month_priorities.keys()))
        response = self.client.delete(
            config.get_api_url(f"priorities/{month}"),
            cookies=self.session.get_cookie_dict(),
            name="/api/v1/priorities/{month} [DELETE]",
        )

        if response.status_code == 200:
            del self.month_priorities[month]


class IntensiveUser(HttpUser):
    """
    Simulates a more intensive user that performs operations rapidly.

    This is useful for stress testing and finding performance limits.
    """

    # Shorter wait time for intensive testing
    wait_time = between(0.1, 0.5)

    user_counter = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__class__.user_counter += 1
        self.user_id = 10000 + self.__class__.user_counter  # Different ID range
        self.username, self.password = config.get_user_credentials(self.user_id)
        self.session = UserSession(self.username, self.password)
        self.registered = False

    def on_start(self):
        """Setup intensive user."""
        if not self.registered:
            self.register()
        self.login()

    def register(self):
        """Register user (simplified)."""
        response = self.client.post(
            config.get_api_url("auth/verify-magic-word"),
            json={
                "magic_word": config.MAGIC_WORD,
                "institution_short_code": config.INSTITUTION_ID,
            },
            name="/api/v1/auth/verify-magic-word",
        )

        if response.status_code == 200:
            registration_token = response.json().get("token")
            response = self.client.post(
                config.get_api_url("auth/register"),
                json={
                    "registration_token": registration_token,
                    "identity": self.username,
                    "password": self.password,
                    "passwordConfirm": self.password,
                    "name": f"Intensive Test User {self.user_id}",
                },
                name="/api/v1/auth/register",
            )
            if response.status_code == 200:
                self.registered = True
                self.session.update_cookies(response)
                print(f"Registered intensive user: {self.username}")
            elif response.status_code == 400:
                # Likely user already exists
                response_text = response.text.lower()
                if "already exists" in response_text or "unique" in response_text:
                    self.registered = True
                    print(f"Intensive user already exists: {self.username}")

    def login(self):
        """Login intensive user."""
        response = self.client.post(
            config.get_api_url("auth/login"),
            json={
                "identity": self.username,
                "password": self.password,
                "keep_logged_in": False,
            },
            name="/api/v1/auth/login",
        )

        if response.status_code == 200:
            self.session.update_cookies(response)

    @task(20)
    def rapid_priority_updates(self):
        """Rapidly update priorities."""
        if not self.session.is_authenticated():
            return

        month = get_next_month()
        priority_data = generate_priority_data(month)

        self.client.put(
            config.get_api_url(f"priorities/{month}"),
            json=priority_data,
            cookies=self.session.get_cookie_dict(),
            name="/api/v1/priorities/{month} [PUT]",
        )

    @task(10)
    def rapid_priority_reads(self):
        """Rapidly read priorities."""
        if not self.session.is_authenticated():
            return

        self.client.get(
            config.get_api_url("priorities"),
            cookies=self.session.get_cookie_dict(),
            name="/api/v1/priorities [GET]",
        )


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """
    Called when the test stops.
    Can be used for cleanup operations.
    """
    print("\n" + "=" * 80)
    print("Load test completed!")
    print("=" * 80)
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Total failures: {environment.stats.total.num_failures}")
    print(f"Average response time: {environment.stats.total.avg_response_time:.2f}ms")
    print(f"RPS: {environment.stats.total.total_rps:.2f}")
    print("=" * 80)


@events.init_command_line_parser.add_listener
def add_custom_arguments(parser):
    """Add custom command-line arguments."""
    parser.add_argument(
        "--magic-word",
        type=str,
        default=config.MAGIC_WORD,
        help="Institution magic word for registration",
    )
    parser.add_argument(
        "--user-prefix",
        type=str,
        default=config.USER_PREFIX,
        help="Prefix for test usernames",
    )


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize test environment."""
    if environment.parsed_options:
        if environment.parsed_options.magic_word:
            config.MAGIC_WORD = environment.parsed_options.magic_word
        if environment.parsed_options.user_prefix:
            config.USER_PREFIX = environment.parsed_options.user_prefix
