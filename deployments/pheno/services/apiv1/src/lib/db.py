
import asyncpg

#figure out how to handle db vars
DATABASE_URL = "postgresql://luci@localhost/pheno_test"
# DATABASE_URL = os.enviorn.get('DATABASE_URL')

class Database():
    async def create_pool(self):
        self.pool = await asyncpg.create_pool(
            dsn=DATABASE_URL,
            command_timeout=10,
        )

    async def close(self):
       await self.pool.close()