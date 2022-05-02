from datetime import datetime
from functools import wraps
import json
import time


class EmptyQueue(Exception):
    pass


def get_item(*, queue):
    query = (
        "DELETE FROM jobs_queue WHERE id = "
        "(SELECT id FROM jobs_queue WHERE queue=$1 ORDER BY priority DESC, created_at ASC FOR UPDATE SKIP LOCKED LIMIT 1) "
        "RETURNING id, upload_id, created_at, meta"
    )

    def _outer(fn):
        @wraps(fn)
        async def _inner(*, con):
            async with con.transaction():
                if not (item := await con.fetchrow(query, queue)):
                    raise EmptyQueue(queue)

                ts = time.time()
                status, new_meta = await fn(con, item)
                runtime = time.time() - ts

                # update metadata
                meta = json.loads(item["meta"])
                meta.update(new_meta)

                data = {
                    "status": status,
                    "runtime": runtime,
                    "finished_at": datetime.now(),
                    "meta": json.dumps(meta),
                }
                set_clause = ", ".join(f"{key} = ${i}" for i, key in enumerate(data, 1))
                await con.execute(
                    f"UPDATE jobs_result SET {set_clause} WHERE job_id=${len(data) + 1}",
                    *data.values(),
                    item["id"],
                )

        return _inner

    return _outer


async def get_uploads(*, con, user_id, upload_ids=None):
    query = "SELECT id, user_id, created_at, object_key FROM uploads WHERE user_id=$1"
    query_params = [user_id]
    if upload_ids:
        places = ", ".join(f"${i}" for i, _ in enumerate(upload_ids, 2))
        query += f" AND id IN ({places})"
        query_params.extend(upload_ids)

    async with con.transaction():
        uploads = [dict(row) async for row in con.cursor(query, *query_params)]
    return uploads


async def create_upload(*, con, user_id, meta):
    query = (
        "WITH row as (SELECT id FROM users where id=$1) "
        "INSERT INTO uploads (user_id, meta) SELECT id, $2 from row RETURNING id"
    )
    async with con.transaction():
        return await con.fetchval(query, user_id, json.dumps(meta))


async def get_jobs(*, con, user_id, job_ids=None):
    query = (
        "SELECT j.job_id, j.upload_id, j.status, j.created_at, j.runtime, j.meta AS job_meta, u.user_id, u.meta AS user_meta "
        "FROM jobs_result AS j JOIN uploads AS u ON j.upload_id = u.id WHERE u.user_id=$1"
    )
    query_params = [user_id]
    if job_ids:
        places = ", ".join(f"${i}" for i, _ in enumerate(job_ids, 2))
        query += f" AND j.job_id IN ({places})"
        query_params.extend(job_ids)

    async with con.transaction():
        jobs = [dict(row) async for row in con.cursor(query, *query_params)]
    return jobs


async def create_job(*, con, upload_id, queue, priority, meta):
    enqueue_job_query = (
        "WITH row AS (SELECT id FROM uploads WHERE id=$1) "
        "INSERT INTO jobs_queue (upload_id, queue, priority, meta) SELECT id, $2, $3, $4 FROM row "
        "RETURNING id, created_at"  # TODO remove created_at
    )
    async with con.transaction():
        row = await con.fetchrow(enqueue_job_query, upload_id, queue, priority, json.dumps(meta))
        job_id = row["id"]

        data = {
            "job_id": job_id,
            "upload_id": upload_id,
            "status": "pending",
            "runtime": 0,
            "created_at": row["created_at"],  # TODO remove this
            "finished_at": None,
            "meta": json.dumps(meta),
        }
        cols = ", ".join(list(data))
        places = ", ".join(f"${i}" for i, _ in enumerate(data, 1))

        await con.execute(f"INSERT INTO jobs_result ({cols}) VALUES ({places})", *data.values())

    return job_id
