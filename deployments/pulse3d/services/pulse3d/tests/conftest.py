import os
import sys


JWT_SECRET_KEY = "1234"
POSTGRES_DB = "test_db"
POSTGRES_USER = "test_pg_user"
POSTGRES_PASSWORD = "test_pw"

os.environ["JWT_SECRET_KEY"] = JWT_SECRET_KEY
os.environ["POSTGRES_DB"] = "test_db"
os.environ["POSTGRES_USER"] = "test_pg_user"
os.environ["POSTGRES_PASSWORD"] = "test_pw"


# import src/ subdirectories and add to sys.modules so that main.py can find them, not sure why it can't otherwise
from src import core, models, repository, service

sys.modules["core"] = core
sys.modules["models"] = models
sys.modules["repository"] = repository
sys.modules["service"] = service
