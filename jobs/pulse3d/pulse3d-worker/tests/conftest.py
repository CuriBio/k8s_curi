import os
import sys


os.environ["POSTGRES_DB"] = "test_db"
os.environ["POSTGRES_USER"] = "test_pg_user"
os.environ["POSTGRES_PASSWORD"] = "test_pw"
os.environ["POSTGRES_SERVER"] = "test_server"


# import lib and add to sys.modules so that main.py can find them, not sure why it can't otherwise
from src import lib

sys.modules["lib"] = lib
