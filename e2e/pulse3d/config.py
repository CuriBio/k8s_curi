import os

# basic
TEST_URL = os.getenv("TEST_URL")

# customer data
VALID_CUSTOMER_ID = os.getenv("VALID_CUSTOMER_ID")
VALID_USER_NAME = os.getenv("VALID_USER_NAME")
VALID_USER_PASSWORD = os.getenv("VALID_USER_PASSWORD")

# admin data
VALID_ADMIN_EMAIL = os.getenv("VALID_ADMIN_EMAIL")
VALID_ADMIN_PASSWORD = os.getenv("VALID_ADMIN_PASSWORD")

# limit reached account login
LIMIT_REACHED_NAME = os.getenv("LIMIT_REACHED_NAME")
LIMIT_REACHED_PASSWORD = os.getenv("LIMIT_REACHED_PASSWORD")

# unlimited account login
UNLIMITED_NAME = os.getenv("UNLIMITED_NAME")
UNLIMITED_PASSWORD = os.getenv("UNLIMITED_PASSWORD")

# limit not reached account login
LIMIT_NOT_REACHED_NAME = os.getenv("LIMIT_NOT_REACHED_NAME")
LIMIT_NOT_REACHED_PASSWORD = os.getenv("LIMIT_NOT_REACHED_PASSWORD")

# playwright config
HEADLESS = True
SLOWMO = False
