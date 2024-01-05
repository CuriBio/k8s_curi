import asyncio

import asyncpg


class AsyncpgPoolDep:
    def __init__(self, dsn: str, min_size: int = 1, max_size: int = 10):
        self._pool: asyncpg.pool.Pool | None = None
        self._lock = asyncio.Lock()
        self._dsn = dsn
        self._min = min_size
        self._max = max_size

    async def __call__(self):
        if self._pool is not None:
            return self._pool

        async with self._lock:
            if self._pool is not None:
                return self._pool
            self._pool = await asyncpg.create_pool(self._dsn, min_size=self._min, max_size=self._max)

        return self._pool
