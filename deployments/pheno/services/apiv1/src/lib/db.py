
import asyncpg
import os 
from contextlib import asynccontextmanager


# TODO handle db vars
DATABASE_URL = "postgresql://luci@localhost/pheno_test"
# DATABASE_URL = os.environ.get('DATABASE_URL')
print(DATABASE_URL)

class Database():
    def __init__(self):
        self.pool = None

    async def create_pool(self):
        self.pool = await asyncpg.create_pool(
            dsn=DATABASE_URL,
            command_timeout=10,
        )

    async def close(self):
       await self.pool.close()
    
    async def get_cur(self):
        con = await self.pool.acquire()
        try:
            yield con
        finally:
            await self.pool.release(con)

    __call__ = asynccontextmanager(get_cur)

database = Database()