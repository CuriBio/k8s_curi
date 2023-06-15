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


# playwright config
HEADLESS = True
