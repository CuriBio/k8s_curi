import os
import sys

JWT_SECRET_KEY = "1234"
POSTGRES_DB = "test_db"
POSTGRES_USER = "test_pg_user"
POSTGRES_PASSWORD = "test_pw"
CURIBIO_EMAIL = "curibio@gmail.com"
CURIBIO_EMAIL_PASSWORD = "test_pw"

os.environ["JWT_SECRET_KEY"] = JWT_SECRET_KEY
os.environ["POSTGRES_DB"] = "test_db"
os.environ["POSTGRES_USER"] = "test_pg_user"
os.environ["POSTGRES_PASSWORD"] = "test_pw"
os.environ["CURIBIO_EMAIL"] = CURIBIO_EMAIL
os.environ["CURIBIO_EMAIL_PASSWORD"] = CURIBIO_EMAIL_PASSWORD


# import core and models and add to sys.modules so that main.py can find them, not sure why it can't otherwise
from src import core, models

sys.modules["core"] = core
sys.modules["models"] = models
