from datetime import datetime
from functools import wraps
import json
import time
from typing import Dict, Any


class EmptyQueue(Exception):
    pass


def get_item(*, queue):
    query = (
        "DELETE FROM jobs_queue "
        "WHERE id = (SELECT id FROM jobs_queue WHERE queue=$1 ORDER BY priority DESC, created_at ASC FOR UPDATE SKIP LOCKED LIMIT 1) "
        "RETURNING id, upload_id, created_at, meta"
    )

    def _outer(fn):
        @wraps(fn)
        async def _inner(*, con, con_to_set_job_running=None):
            async with con.transaction():
                item = await con.fetchrow(query, queue)
                if not item:
                    raise EmptyQueue(queue)

                if con_to_set_job_running:
                    await con_to_set_job_running.execute(
                        "UPDATE jobs_result SET status='running' WHERE job_id=$1", item["id"]
                    )

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


async def get_uploads(*, con, account_type, account_id, upload_ids=None):
    """Query DB for info of upload(s) belonging to the customer or user account.

    If no uploads specified, will return info of all the user's uploads

    If an upload is marked as deleted, filter out it
    """
    query_params = [account_id]
    if account_type == "user":
        query = "SELECT * FROM uploads WHERE user_id=$1 AND deleted='f'"
    else:
        query = (
            "SELECT users.name AS username, uploads.* "
            "FROM uploads JOIN users ON uploads.user_id=users.id "
            "WHERE users.customer_id=$1 AND uploads.deleted='f'"
        )
    if upload_ids:
        places = _get_placeholders_str(len(upload_ids), len(query_params) + 1)
        query += f" AND uploads.id IN ({places})"
        query_params.extend(upload_ids)

    async with con.transaction():
        uploads = [dict(row) async for row in con.cursor(query, *query_params)]

    return uploads


async def create_upload(*, con, upload_params):
    # the WITH clause in this query is necessary to make sure the given user_id actually exists
    query = (
        "WITH row AS (SELECT id AS user_id FROM users WHERE id=$1) "
        "INSERT INTO uploads (user_id, id, md5, prefix, filename, type, customer_id, auto_upload) "
        "SELECT user_id, $2, $3, $4, $5, $6, $7, $8 FROM row "
        "RETURNING id"
    )

    return await con.fetchval(
        query,
        upload_params["user_id"],
        upload_params["upload_id"],
        upload_params["md5"],
        upload_params["prefix"],
        upload_params["filename"],
        upload_params["type"],
        upload_params["customer_id"],
        upload_params["auto_upload"],
    )


async def delete_uploads(*, con, account_type, account_id, upload_ids):
    """Query DB to update upload deleted state to true for uploads with the given IDs.

    Performs a join on users table so that one user cannot delete uploads belonging to a different user.
    """
    query_params = [account_id]
    places = _get_placeholders_str(len(upload_ids), len(query_params) + 1)
    if account_type == "user":
        query = f"UPDATE uploads SET deleted='t' WHERE user_id=$1 AND id IN ({places})"
    else:
        # this is essentially doing a JOIN on users WHERE uploads.user_id=users.id
        query = (
            "UPDATE uploads SET deleted='t' FROM users "
            f"WHERE uploads.user_id=users.id AND users.customer_id=$1 AND uploads.id IN ({places})"
        )
    query_params.extend(upload_ids)
    await con.execute(query, *query_params)


async def get_jobs(*, con, account_type, account_id, job_ids=None):
    """Query DB for info of job(s) belonging to the customer or user account.

    If no jobs specified, will return info of all jobs created by the user
    or all jobs across all users under to the given customer ID

    If a job is marked as deleted, filter out it
    """
    query_params = [account_id]
    if account_type == "user":
        query = (
            "SELECT j.job_id, j.upload_id, j.status, j.created_at, j.runtime, j.object_key, j.meta AS job_meta, "
            "u.user_id, u.meta AS user_meta, u.filename, u.prefix "
            "FROM jobs_result AS j JOIN uploads AS u ON j.upload_id=u.id "
            "WHERE u.user_id=$1 AND j.status!='deleted'"
        )
    else:
        query = (
            "SELECT j.job_id, j.upload_id, j.status, j.created_at, j.runtime, j.object_key, j.meta AS job_meta, "
            "u.user_id, u.meta AS user_meta, users.name AS username "
            "FROM jobs_result AS j JOIN uploads AS u ON j.upload_id=u.id JOIN users ON u.user_id=users.id "
            "WHERE users.customer_id=$1 AND j.status!='deleted'"
        )

    if job_ids:
        places = _get_placeholders_str(len(job_ids), len(query_params) + 1)
        query += f" AND j.job_id IN ({places})"
        query_params.extend(job_ids)

    async with con.transaction():
        return [dict(row) async for row in con.cursor(query, *query_params)]


async def create_job(*, con, upload_id, queue, priority, meta, customer_id, job_type):
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
            "customer_id": customer_id,
            "type": job_type,
        }

        cols = ", ".join(list(data))
        places = _get_placeholders_str(len(data))

        # insert job info result table with 'pending' status
        await con.execute(f"INSERT INTO jobs_result ({cols}) VALUES ({places})", *data.values())

    return job_id


async def delete_jobs(*, con, account_type, account_id, job_ids):
    """Query DB to update job status to deleted for jobs with the given IDs.

    Performs a join on users and uploads tables so that one user cannot delete jobs belonging to a different user.
    """

    query_params = [account_id]
    places = _get_placeholders_str(len(job_ids), len(query_params) + 1)
    if account_type == "user":
        query = (
            "UPDATE jobs_result AS j SET status='deleted' FROM uploads "
            f"WHERE j.upload_id=uploads.id AND uploads.user_id=$1 AND job_id IN ({places})"
        )
    else:
        # this is essentially doing a JOIN on uploads WHERE jobs_result.upload_id=uploads.id
        # and JOIN on users WHERE uploads.user_id=users.id
        query = (
            "UPDATE jobs_result AS j SET status='deleted' FROM uploads, users "
            f"WHERE j.upload_id=uploads.id AND uploads.user_id=users.id AND users.customer_id=$1 AND job_id IN ({places})"
        )
    query_params.extend(job_ids)
    await con.execute(query, *query_params)


def _get_placeholders_str(num_placeholders, start=1):
    if num_placeholders < 1:
        raise ValueError("Must have at least 1 placeholder")
    if start < 1:
        raise ValueError("Initial placeholder value must be >= 1")
    return ", ".join(f"${i}" for i in range(start, start + num_placeholders))


async def get_customer_quota(con, customer_id, service) -> Dict[str, Any]:
    """Query DB and return usage limit and current usage.
    Returns:
        - Dictionary with account limits and account usage
    """
    # get service specific usage restrictions for the customer account
    # uploads limit, jobs limit, end date of plan
    usage_limit_query = "SELECT usage_restrictions->$1 AS usage FROM customers WHERE id=$2"
    # collects number of all jobs in customer account and return number of credits consumed
    # upload with 1 - 2 jobs  = 1 credit , upload with 3+ jobs = 1 credit for each upload with over 2 jobs
    current_usage_query = "SELECT COUNT(*) AS total_uploads, SUM(jobs_count) AS total_jobs FROM ( SELECT ( CASE WHEN (COUNT(*) <= 2 AND COUNT(*) > 0) THEN 1 ELSE GREATEST(COUNT(*) - 1, 0) END ) AS jobs_count FROM jobs_result WHERE customer_id=$1 and type=$2 GROUP BY upload_id) dt"

    async with con.transaction():
        usage_limit_json = await con.fetchrow(usage_limit_query, service, customer_id)
        current_usage_data = await con.fetchrow(current_usage_query, customer_id, service)

    usage_limit_dict = json.loads(usage_limit_json["usage"])

    # usage query returns none if no jobs are found but 0 if no uploads are found.
    current_usage_dict = {
        "jobs": current_usage_data.get("total_jobs", 0)
        if current_usage_data.get("total_jobs", 0) is not None
        else 0,
        "uploads": current_usage_data.get("total_uploads ", 0),
    }

    return {"limits": usage_limit_dict, "current": current_usage_dict}


async def check_customer_quota(con, customer_id, service) -> Dict[str, Any]:
    """Query DB for service-specific customer account usage.

    Will be called for all account tiers, unlimited has a value of -1.
    Returns:
        - Dictionary containing boolean values for if uploads or job quotas have been reached
        - Dictionary also contains data about max usage and end date.
    """
    usage_info = await get_customer_quota(con, customer_id, service)
    # check current date has not passed end date
    is_expired = (
        datetime.strptime(usage_info["limits"]["expiration_date"], "%Y-%m-%d") < datetime.utcnow()
        if usage_info["limits"]["expiration_date"]
        else False
    )
    # return boolean values if reached, -1 means infinite uploads/jobs allowed for paid account
    uploads_reached = {
        f"{key}_reached": (
            int(usage_info["current"][key]) >= int(usage_info["limits"][key])
            and (usage_info["limits"][key] != -1)
        )
        or is_expired
        for key in ("uploads", "jobs")
    }
    uploads_reached.update(usage_info)
    return uploads_reached


async def create_analysis_preset(con, user_id, details):
    query = (
        "WITH row AS (SELECT id AS user_id FROM users WHERE id=$1) "
        "INSERT INTO analysis_presets (user_id, name, parameters) "
        "SELECT user_id, $2, $3 FROM row "
        "RETURNING id"
    )

    return await con.fetchval(query, user_id, details.name, json.dumps(details.analysis_params))
