import asyncpg
import json
import time
from functools import wraps

class EmptyQueue(Exception):
    pass

def get_item(*, queue):
    QUERY = "DELETE FROM jobs_queue WHERE id = (SELECT id FROM jobs_queue WHERE queue=$1 ORDER BY priority DESC, created_at ASC FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING id, upload_id, created_at, meta"

    def _outer(fn):
        @wraps(fn)
        async def _inner(*, con):
            async with con.transaction():
                item = await con.fetchrow(QUERY, queue)
                if item:
                    ts = time.time()
                    (status, meta) = await fn(item)
                    data = [
                        ('job_id', item.get("id")),
                        ('upload_id', item.get("upload_id")),
                        ('status', status),
                        ('runtime', (time.time() - ts)),
                        ('created_at', item.get("created_at")),
                        ('meta', json.dumps(meta)),
                    ]
                    cvs = list(zip(*data))
                    places = ", ".join([f"${i+1}" for i, _ in enumerate(data)])

                    await con.execute(f"INSERT INTO jobs_result ({', '.join(cvs[0])}) VALUES ({places})", *cvs[1])
                else:
                    raise EmptyQueue
        return _inner
    return _outer


async def create_upload(*, con, user_id, meta):
    query = "WITH row as (SELECT id FROM users where id=$1) INSERT INTO uploads (user_id, meta) SELECT id, $2 from row RETURNING id"
    async with con.transaction():
        return await con.fetchval(query, user_id, json.dumps(meta))


async def create_job(*, con, upload_id, queue, priority, meta):
    query = "WITH row AS (SELECT id FROM uploads WHERE id=$1) INSERT INTO jobs_queue (upload_id, queue, priority, meta) SELECT id, $2, $3, $4 from row RETURNING id",
    async with con.transaction():
        return await con.fetchval(query, upload_id, queue, priority, json.dumps(meta))
