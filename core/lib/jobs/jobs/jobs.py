from datetime import datetime
from functools import wraps
import json
import time
from typing import Any
from uuid import UUID


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
        async def _inner(*, con, con_to_update_job_result=None):
            async with con.transaction():
                item = await con.fetchrow(query, queue)
                if not item:
                    raise EmptyQueue(queue)

                if con_to_update_job_result:
                    # if already set to running, then assume that a different worker already tried processing the job and failed
                    current_job_status = await con_to_update_job_result.fetchval(
                        "SELECT status FROM jobs_result WHERE job_id=$1", item["id"]
                    )
                    if current_job_status == "running":
                        await con_to_update_job_result.execute(
                            "UPDATE jobs_result SET status='error', meta=meta||$1::jsonb, finished_at=NOW() WHERE job_id=$2",
                            json.dumps({"error_msg": "Ran out of time/memory"}),
                            item["id"],
                        )
                        return

                    await con_to_update_job_result.execute(
                        "UPDATE jobs_result SET status='running', started_at=$1 WHERE job_id=$2",
                        datetime.now(),
                        item["id"],
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


async def get_uploads_info_for_admin(
    con,
    customer_id: UUID,
    sort_field: str | None,
    sort_direction: str | None,
    skip: int,
    limit: int,
    **filters,
):
    query = (
        "SELECT users.name AS username, uploads.*, j.created_at AS last_analyzed "
        "FROM uploads "
        "JOIN users ON uploads.user_id=users.id "
        "JOIN jobs_result j ON uploads.id=j.upload_id "
        "WHERE users.customer_id=$1 AND uploads.deleted='f'"
    )
    query_params = [customer_id]

    query, query_params = _add_upload_sorting_filtering_conds(
        query, query_params, sort_field, sort_direction, skip, limit, **filters
    )

    async with con.transaction():
        uploads = [dict(row) async for row in con.cursor(query, *query_params)]

    return uploads


async def get_uploads_info_for_rw_all_data_user(
    con,
    customer_id: UUID,
    upload_type: str,
    sort_field: str | None,
    sort_direction: str | None,
    skip: int,
    limit: int,
    **filters,
):
    query = (
        "SELECT users.name AS username, uploads.*, j.created_at AS last_analyzed "
        "FROM uploads "
        "JOIN users ON uploads.user_id=users.id "
        "JOIN jobs_result j ON uploads.id=j.upload_id "
        "WHERE users.customer_id=$1 AND uploads.type=$2 AND uploads.deleted='f'"
    )
    query_params = [customer_id, upload_type]

    query, query_params = _add_upload_sorting_filtering_conds(
        query, query_params, sort_field, sort_direction, skip, limit, **filters
    )

    async with con.transaction():
        uploads = [dict(row) async for row in con.cursor(query, *query_params)]

    return uploads


async def get_uploads_info_for_base_user(
    con,
    user_id: UUID,
    upload_type: str,
    sort_field: str | None,
    sort_direction: str | None,
    skip: int,
    limit: int,
    **filters,
):
    query = (
        "SELECT uploads.*, j.created_at AS last_analyzed "
        "FROM uploads JOIN jobs_result j ON uploads.id.j.upload_id "
        "WHERE user_id=$1 AND type=$2 AND deleted='f'"
    )
    query_params = [user_id, upload_type]

    query, query_params = _add_upload_sorting_filtering_conds(
        query, query_params, sort_field, sort_direction, skip, limit, **filters
    )

    async with con.transaction():
        uploads = [dict(row) async for row in con.cursor(query, *query_params)]

    return uploads


def _add_upload_sorting_filtering_conds(
    query, query_params, sort_field, sort_direction, skip, limit, **filters
):
    query_params = query_params.copy()

    next_placeholder_count = len(query_params) + 1

    conds = ""
    for filter_name, filter_value in filters.items():
        placeholder = f"${next_placeholder_count}"
        match filter_name:
            case "filename":
                new_cond = f"uploads.filename LIKE {placeholder}"
                filter_value = f"%{filter_value}%"
            case "id":
                new_cond = f"uploads.id LIKE {placeholder}"
                filter_value = f"%{filter_value}%"
            case "created_at_min":
                new_cond = f"uploads.created_at > {placeholder}"
            case "created_at_max":
                new_cond = f"uploads.created_at < {placeholder}"
            case "last_analyzed_min":
                new_cond = f"last_analyzed > {placeholder}"
            case "last_analyzed_max":
                new_cond = f"last_analyzed < {placeholder}"
            case _:
                continue

        query_params.append(filter_value)
        conds += f" AND {new_cond}"
        next_placeholder_count += 1
    if conds:
        query += conds

    if sort_field in ("filename", "id", "created_at", "last_analyzed", "auto_upload"):
        if sort_field != "last_analyzed":
            sort_field = f"uploads.{sort_field}"
        if sort_direction not in ("ASC", "DESC"):
            sort_direction = "DESC"
        query += f" ORDER BY {sort_field} {sort_field}"

    query += f" LIMIT ${len(query_params) + 1} OFFSET ${len(query_params) + 2}"
    query_params += [limit, skip]

    return query, query_params


async def get_uploads_download_info_for_admin(con, customer_id: UUID, upload_ids: list[UUID]):
    query_params = [customer_id]
    places = _get_placeholders_str(len(upload_ids), len(query_params) + 1)
    query = f"SELECT filename, prefix FROM uploads WHERE customer_id=$1 AND id IN ({places})"
    query_params += upload_ids

    async with con.transaction():
        uploads = [dict(row) async for row in con.cursor(query, *query_params)]

    return uploads


async def get_uploads_download_info_for_rw_all_data_user(
    con, customer_id: UUID, upload_type: str, upload_ids: list[UUID]
):
    query_params = [customer_id, upload_type]
    places = _get_placeholders_str(len(upload_ids), len(query_params) + 1)
    query = f"SELECT filename, prefix FROM uploads WHERE customer_id=$1 AND type=$2 AND id IN ({places})"
    query_params += upload_ids

    async with con.transaction():
        uploads = [dict(row) async for row in con.cursor(query, *query_params)]

    return uploads


async def get_uploads_download_info_for_base_user(
    con, user_id: UUID, upload_type: str, upload_ids: list[UUID]
):
    query_params = [user_id, upload_type]
    places = _get_placeholders_str(len(upload_ids), len(query_params) + 1)
    query = f"SELECT filename, prefix FROM uploads WHERE user_id=$1 AND type=$2 AND id IN ({places})"
    query_params += upload_ids

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


async def get_jobs(
    *, con, account_type, customer_id, user_id, job_ids=None, upload_types=None, rw_all_data_upload_types=None
):
    """Query DB for info of job(s) belonging to the admin or user account.

    If no job IDs specified for a user, will return info of all jobs accessible to the user.
    If no job IDs specified for an admin, will return info of all jobs from all users under the admin.

    If a job is marked as deleted, filter it out
    """
    # need to make sure the rw_all_data types are provided if a rw_all_data user is given
    if account_type == "rw_all_data_user" and not rw_all_data_upload_types:
        raise ValueError("rw_all_data_user must provide rw_all_data_upload_types")

    if account_type == "user":
        query = (
            "SELECT j.job_id, j.upload_id, j.status, j.created_at, j.runtime, j.object_key, j.meta AS job_meta, "
            "u.user_id, u.meta AS user_meta, u.filename, u.prefix, u.type AS upload_type "
            "FROM jobs_result AS j JOIN uploads AS u ON j.upload_id=u.id "
            "WHERE u.user_id=$1 AND j.status!='deleted'"
        )
        query_params = [user_id]
    else:
        query = (
            "SELECT j.job_id, j.upload_id, j.status, j.created_at, j.runtime, j.object_key, j.meta AS job_meta, "
            "u.user_id, u.meta AS user_meta, users.name AS username, u.filename, u.prefix, u.type AS upload_type "
            "FROM jobs_result AS j JOIN uploads AS u ON j.upload_id=u.id JOIN users ON u.user_id=users.id "
            "WHERE users.customer_id=$1 AND j.status!='deleted'"
        )
        query_params = [customer_id]

    # TODO if this ends up matching get_uploads exactly, pull it out into a function
    if account_type == "admin":
        if upload_types:
            places = _get_placeholders_str(len(upload_types), len(query_params) + 1)
            query += f" AND u.type IN ({places})"
            query_params.extend(upload_types)
    else:
        # have to consider the desired upload types and rw_all_data upload types together
        if not rw_all_data_upload_types:
            upload_types_no_id_check = upload_types
            upload_types_with_id_check = None
        elif upload_types:
            upload_types_no_id_check = [ut for ut in upload_types if ut in rw_all_data_upload_types]
            upload_types_with_id_check = [ut for ut in upload_types if ut not in rw_all_data_upload_types]
        else:
            upload_types_no_id_check = rw_all_data_upload_types
            upload_types_with_id_check = None

        conds = []
        if upload_types_no_id_check:
            places = _get_placeholders_str(len(upload_types_no_id_check), len(query_params) + 1)
            conds.append(f"u.type IN ({places})")
            query_params.extend(upload_types_no_id_check)
        if upload_types_with_id_check:
            cond = f"u.user_id=${len(query_params) + 1}"
            query_params.append(user_id)
            places = _get_placeholders_str(len(upload_types_with_id_check), len(query_params) + 1)
            cond += f" AND u.type IN ({places})"
            query_params.extend(upload_types_with_id_check)
            conds.append(f"({cond})")

        clause = " OR ".join(conds)
        query += f" AND ({clause})"

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


async def get_customer_quota(con, customer_id, service) -> dict[str, Any]:
    """Query DB and return usage limit and current usage.
    Returns:
        - Dictionary with account limits and account usage
    """
    # get service specific usage restrictions for the admin account
    # uploads limit, jobs limit, end date of plan
    usage_limit_query = "SELECT usage_restrictions->$1 AS usage FROM customers WHERE id=$2"
    # collects number of all jobs in admin account and return number of credits consumed
    # upload with 1 - 2 jobs  = 1 credit , upload with 3+ jobs = 1 credit for each upload with over 2 jobs
    current_usage_query = (
        "SELECT COUNT(*) AS total_uploads, SUM(jobs_count) AS total_jobs "
        "FROM ( SELECT ( CASE WHEN (COUNT(*) <= 2 AND COUNT(*) > 0) THEN 1 ELSE GREATEST(COUNT(*) - 1, 0) END ) AS jobs_count FROM jobs_result WHERE customer_id=$1 and type=$2 GROUP BY upload_id) dt"
    )

    usage_limit_json = await con.fetchrow(usage_limit_query, service, customer_id)
    current_usage_data = await con.fetchrow(current_usage_query, customer_id, service)

    usage_limit_dict = json.loads(usage_limit_json["usage"])

    # usage query returns none if no jobs are found but 0 if no uploads are found
    current_job_usage = int(current_usage_data.get("total_jobs", 0))
    if current_job_usage is None:
        current_job_usage = 0
    current_usage_dict = {
        "jobs": current_job_usage,
        "uploads": int(current_usage_data.get("total_uploads", 0)),
    }

    return {"limits": usage_limit_dict, "current": current_usage_dict}


async def check_customer_quota(con, customer_id, service) -> dict[str, Any]:
    """Query DB for service-specific customer account usage.

    Will be called for all account tiers, unlimited has a value of -1.
    Returns:
        - Dictionary containing boolean values for if uploads or job quotas have been reached
        - Dictionary also contains data about max usage and end date.
    """
    usage_info = await get_customer_quota(con, customer_id, service)

    is_expired = False
    # if there is an expiration date, check if we have passed it
    if expiration_date := usage_info["limits"]["expiration_date"]:
        is_expired = datetime.strptime(expiration_date, "%Y-%m-%d") < datetime.utcnow()

    # -1 means unlimited uploads/jobs allowed
    uploads_reached = {
        f"{key}_reached": (
            int(usage_info["current"][key]) >= int(usage_info["limits"][key])
            and (usage_info["limits"][key] != -1)
        )
        or is_expired
        for key in ("uploads", "jobs")
    }
    return uploads_reached | usage_info


async def create_analysis_preset(con, user_id, details):
    query = (
        "INSERT INTO analysis_presets (user_id, name, parameters) "
        "VALUES ($1, $2, $3) "
        "ON CONFLICT ON CONSTRAINT unique_name_per_user DO "
        "UPDATE SET parameters=$3 WHERE analysis_presets.user_id=$1 AND analysis_presets.name=$2"
    )

    return await con.fetchval(query, user_id, details.name, json.dumps(details.analysis_params))
