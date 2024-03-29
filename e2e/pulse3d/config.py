import os

# basic
DASHBOARD_URL = os.getenv("DASHBOARD_URL")

# user data + unlimite usage
VALID_CUSTOMER_ID = os.getenv("VALID_CUSTOMER_ID")
VALID_USER_NAME = os.getenv("VALID_USER_NAME")
VALID_USER_PASSWORD = os.getenv("VALID_USER_PASSWORD")

# admin data
VALID_ADMIN_EMAIL = os.getenv("VALID_ADMIN_EMAIL")
VALID_ADMIN_PASSWORD = os.getenv("VALID_ADMIN_PASSWORD")


# usage limit reached admin data
LIMIT_REACHED_EMAIL = os.getenv("LIMIT_REACHED_NAME")
LIMIT_REACHED_PASSWORD = os.getenv("LIMIT_REACHED_PASSWORD")

# usage limit not reached admin data
LIMIT_NOT_REACHED_EMAIL = os.getenv("LIMIT_NOT_REACHED_NAME")
LIMIT_NOT_REACHED_PASSWORD = os.getenv("LIMIT_NOT_REACHED_PASSWORD")
