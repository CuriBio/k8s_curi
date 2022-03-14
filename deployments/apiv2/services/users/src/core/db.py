import asyncio
import asyncpg

from core.config import DATABASE_URL

class Database():
    async def create_pool(self):
        self.pool = await asyncpg.create_pool(
            min_size=1,
            max_size=10,
            dsn=DATABASE_URL,
            command_timeout=5,
        )

    async def close(self):
        asyncio.wait_for(self.pool.close(), timeout=10.0)
