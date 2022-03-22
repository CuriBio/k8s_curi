import sys
import os
import pytest
from fastapi.testclient import TestClient
import inspect

ROOT_DIR = os.path.dirname(os.path.abspath("src"))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from main import app
from lib.db import Database

import asyncpg


class Cursor:
    def execute(query, params):
        pass
    def fetchrow(query, params):
        pass

@pytest.fixture
def client(mocker):
    # mock db class
    mocker.patch.object(Database, "create_pool")
    # mocker.patch.object(Database, "close")
    # mocker.patch.object(Database, "get_cur")
    

    with TestClient(app) as c:
        for i in inspect.getmembers(Database):
            if not i[0].startswith('_'):
                    
                    # To remove other methods that
                    # doesnot start with a underscore
                    if not inspect.ismethod(i[1]): 
                        print(i)
        yield c
