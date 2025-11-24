import getpass
import sys

import requests

from priotag.services.pocketbase_service import POCKETBASE_URL
from priotag.services.redis_service import get_redis
from priotag.services.service_account import (
    SERVICE_ACCOUNT_ID,
    SERVICE_ACCOUNT_PASSWORD,
)

superuser_login = input("Enter superuser login: ")
superuser_password = getpass.getpass()
redis_client = get_redis()

try:
    pb_response = requests.post(
        f"{POCKETBASE_URL}/api/collections/_superusers/auth-with-password",
        json={
            "identity": superuser_login,
            "password": superuser_password,
        },
    )
    response_body = pb_response.json()
    token = response_body["token"]
except Exception:
    sys.exit("Failed to login as superuser")


try:
    requests.post(
        f"{POCKETBASE_URL}/api/collections/users/records",
        json={
            "username": SERVICE_ACCOUNT_ID,
            "password": SERVICE_ACCOUNT_PASSWORD,
            "passwordConfirm": SERVICE_ACCOUNT_PASSWORD,
            "role": "service",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

except Exception:
    sys.exit("Failed to setup service account")
