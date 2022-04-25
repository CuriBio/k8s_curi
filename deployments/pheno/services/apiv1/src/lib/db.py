import asyncpg
import os

# TODO handle db vars
DATABASE_URL = os.environ.get("DATABASE_URL")


class Database:
    def __init__(self):
        self.pool = None

    async def create_pool(self):
        self.pool = await asyncpg.create_pool(
            dsn=DATABASE_URL,
            command_timeout=10,
        )

    async def close(self):
        await self.pool.close()


async def get_cur():
    conn = await database.pool.acquire()
    try:
        yield conn
    finally:
        await database.pool.release(conn)


database = Database()
