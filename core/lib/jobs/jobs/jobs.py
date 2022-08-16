from datetime import datetime
from functools import wraps
import json
import time
import uuid


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
                status, new_meta, object_key = await fn(con, item)
                runtime = time.time() - ts

                # update metadata
                meta = json.loads(item["meta"])
                meta.update(new_meta)

                data = {
                    "status": status,
                    "runtime": runtime,
                    "finished_at": datetime.now(),
                    "meta": json.dumps(meta),
                    "object_key": object_key,
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
    """Query DB for info of a user's upload(s).

    If no uploads specified, will return info of all the user's uploads
    """
    # filter deleted uploads
    query = "SELECT * FROM uploads WHERE user_id=$1 AND deleted='f';"
    query_params = [user_id]
    if upload_ids:
        places = ", ".join(f"${i}" for i, _ in enumerate(upload_ids, 2))
        query += f" AND id IN ({places})"
        query_params.extend(upload_ids)

    async with con.transaction():
        uploads = [dict(row) async for row in con.cursor(query, *query_params)]

    return uploads


async def create_upload(*, con, upload_params):
    # generating uuid here instead of letting PG handle it so that it can be inserted into the prefix more easily
    upload_id = uuid.uuid4()

    # the WITH clause in this query is necessary to make sure the given user_id actually exists
    query = (
        "WITH row AS (SELECT id AS user_id FROM users WHERE id=$1) "
        "INSERT INTO uploads (user_id, id, md5, prefix, filename, type) "
        "SELECT user_id, $2, $3, $4, $5, $6 FROM row "
        "RETURNING id"
    )

    async with con.transaction():
        return await con.fetchval(
            query,
            upload_params["user_id"],
            upload_id,
            upload_params["md5"],
            upload_params["prefix"].format(upload_id=upload_id),
            upload_params["filename"],
            upload_params["type"],
        )


async def get_jobs(*, con, user_id, job_ids=None):
    """Query DB for info of a user's job(s).

    If no jobs specified, will return info of all jobs created by the user
    """
    query = (
        "SELECT j.job_id, j.upload_id, j.status, j.created_at, j.runtime, j.object_key, j.meta AS job_meta, u.user_id, u.meta AS user_meta "
        "FROM jobs_result AS j JOIN uploads AS u ON j.upload_id = u.id WHERE u.user_id=$1 AND j.status!='deleted'"
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
    # the WITH clause in this query is necessary to make sure the given upload_id actually exists
    enqueue_job_query = (
        "WITH row AS (SELECT id FROM uploads WHERE id=$1) "
        "INSERT INTO jobs_queue (upload_id, queue, priority, meta) SELECT id, $2, $3, $4 FROM row "
        "RETURNING id"
    )
    async with con.transaction():
        # add job to queue
        row = await con.fetchrow(enqueue_job_query, upload_id, queue, priority, json.dumps(meta))

        job_id = row["id"]
        data = {
            "job_id": job_id,
            "upload_id": upload_id,
            "status": "pending",
            "runtime": 0,
            "finished_at": None,
            "meta": json.dumps(meta),
        }
        
        cols = ", ".join(list(data))
        places = ", ".join(f"${i}" for i, _ in enumerate(data, 1))

        # insert job info result table with 'pending' status
        await con.execute(f"INSERT INTO jobs_result ({cols}) VALUES ({places})", *data.values())

    return job_id


async def delete_jobs(*, con, job_ids):
    """Query DB to update job status to deleted."""
    
    query = "UPDATE jobs_result SET status='deleted' WHERE job_id=$1"
    async with con.transaction():
        for id in job_ids:
            await con.execute(query, id)

async def delete_uploads(*, con, upload_ids):
    """Query DB to update upload deleted state to true."""
    
    query = "UPDATE uploads SET deleted='t' WHERE id=$1"
    async with con.transaction():
        for id in upload_ids:
            await con.execute(query, id)