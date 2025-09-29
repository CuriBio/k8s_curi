from datetime import datetime
from functools import wraps
import json
import os
import time
from typing import Any


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


def get_advanced_item(*, queue):
    query = (
        "DELETE FROM jobs_queue "
        "WHERE id = (SELECT id FROM jobs_queue WHERE queue=$1 ORDER BY priority DESC, created_at ASC FOR UPDATE SKIP LOCKED LIMIT 1) "
        "RETURNING id, sources, created_at, meta"
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
                        "SELECT status FROM advanced_analysis_result WHERE id=$1", item["id"]
                    )
                    if current_job_status == "running":
                        await con_to_update_job_result.execute(
                            "UPDATE advanced_analysis_result SET status='error', meta=meta||$1::jsonb, finished_at=NOW() WHERE id=$2",
                            json.dumps({"error_msg": "Ran out of time/memory"}),
                            item["id"],
                        )
                        return

                    await con_to_update_job_result.execute(
                        "UPDATE advanced_analysis_result SET status='running', started_at=$1 WHERE id=$2",
                        datetime.now(),
                        item["id"],
                    )

                ts = time.time()
                status, new_meta, object_key = await fn(con, item)
                runtime = time.time() - ts

                # update metadata
                meta = json.loads(item["meta"])
                meta.update(new_meta)

                s3_prefix = None
                name = None
                if object_key is not None:
                    s3_prefix = os.path.dirname(object_key)
                    name = os.path.basename(object_key)

                data = {
                    "status": status,
                    "runtime": runtime,
                    "finished_at": datetime.now(),
                    "meta": json.dumps(meta),
                    "s3_prefix": s3_prefix,
                    "name": name,
                }
                set_clause = ", ".join(f"{key} = ${i}" for i, key in enumerate(data, 1))
                await con.execute(
                    f"UPDATE advanced_analysis_result SET {set_clause} WHERE id=${len(data) + 1}",
                    *data.values(),
                    item["id"],
                )

        return _inner

    return _outer


async def get_uploads_info_for_admin(
    con,
    customer_id: str,
    sort_field: str | None,
    sort_direction: str | None,
    skip: int,
    limit: int,
    **filters,
):
    query = (
        "SELECT users.name AS username, uploads.*, j.last_analyzed "
        "FROM uploads "
        "JOIN users ON uploads.user_id=users.id "
        "JOIN (SELECT upload_id, max(created_at) AS last_analyzed FROM jobs_result WHERE status!='deleted' GROUP BY upload_id) AS j ON uploads.id=j.upload_id "
        "WHERE users.customer_id=$1 AND uploads.deleted='f' AND uploads.multipart_upload_id IS NULL"
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
    customer_id: str,
    upload_type: str,
    sort_field: str | None,
    sort_direction: str | None,
    skip: int,
    limit: int,
    **filters,
):
    query = (
        "SELECT users.name AS username, uploads.*, j.last_analyzed "
        "FROM uploads "
        "JOIN users ON uploads.user_id=users.id "
        "JOIN (SELECT upload_id, max(created_at) AS last_analyzed FROM jobs_result WHERE status!='deleted' GROUP BY upload_id) AS j ON uploads.id=j.upload_id "
        "WHERE users.customer_id=$1 AND uploads.type=$2 AND uploads.deleted='f' AND uploads.multipart_upload_id IS NULL"
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
    user_id: str,
    upload_type: str,
    sort_field: str | None,
    sort_direction: str | None,
    skip: int,
    limit: int,
    **filters,
):
    query = (
        "SELECT uploads.*, j.last_analyzed "
        "FROM uploads "
        "JOIN (SELECT upload_id, max(created_at) AS last_analyzed FROM jobs_result WHERE status!='deleted' GROUP BY upload_id) AS j ON uploads.id=j.upload_id "
        "WHERE user_id=$1 AND uploads.type=$2 AND uploads.deleted='f' AND uploads.multipart_upload_id IS NULL"
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
            case "username":
                new_cond = f"users.name LIKE {placeholder}"
                filter_value = f"%{filter_value}%"
            case "filename":
                new_cond = f"LOWER(uploads.filename) LIKE LOWER({placeholder})"
                filter_value = f"%{filter_value}%"
            case "id":
                new_cond = f"uploads.id::text LIKE {placeholder}"
                filter_value = f"%{filter_value}%"
            case "created_at_min":
                new_cond = f"uploads.created_at >= to_timestamp({placeholder}, 'YYYY-MM-DD\"T\"HH:MI:SS.MSZ')"
            case "created_at_max":
                new_cond = f"uploads.created_at <= to_timestamp({placeholder}, 'YYYY-MM-DD\"T\"HH:MI:SS.MSZ')"
            case "last_analyzed_min":
                new_cond = f"j.last_analyzed >= to_timestamp({placeholder}, 'YYYY-MM-DD\"T\"HH:MI:SS.MSZ')"
            case "last_analyzed_max":
                new_cond = f"j.last_analyzed <= to_timestamp({placeholder}, 'YYYY-MM-DD\"T\"HH:MI:SS.MSZ')"
            case _:
                continue

        query_params.append(filter_value)
        conds += f" AND {new_cond}"
        next_placeholder_count += 1
    if conds:
        query += conds

    if sort_field in ("filename", "id", "created_at", "last_analyzed", "auto_upload", "username"):
        if sort_field == "last_analyzed":
            sort_field = f"j.{sort_field}"
        elif sort_field == "username":
            sort_field = "users.name"
        else:
            sort_field = f"uploads.{sort_field}"
        if sort_direction not in ("ASC", "DESC"):
            sort_direction = "DESC"
        sort_direction = sort_direction.upper()
        query += f" ORDER BY {sort_field} {sort_direction}"

    query += f" LIMIT ${len(query_params) + 1} OFFSET ${len(query_params) + 2}"
    query_params += [limit, skip]

    return query, query_params


async def get_uploads_download_info_for_admin(con, customer_id: str, upload_ids: list[str]):
    query_params = [customer_id]
    places = _get_placeholders_str(len(upload_ids), len(query_params) + 1)
    query = f"SELECT filename, prefix FROM uploads WHERE deleted='f' AND multipart_upload_id IS NULL AND customer_id=$1 AND id IN ({places})"
    query_params += upload_ids

    async with con.transaction():
        uploads = [dict(row) async for row in con.cursor(query, *query_params)]

    return uploads


async def get_uploads_download_info_for_rw_all_data_user(
    con, customer_id: str, upload_type: str, upload_ids: list[str]
):
    query_params = [customer_id, upload_type]
    places = _get_placeholders_str(len(upload_ids), len(query_params) + 1)
    query = f"SELECT filename, prefix FROM uploads WHERE deleted='f' AND multipart_upload_id IS NULL AND customer_id=$1 AND type=$2 AND id IN ({places})"
    query_params += upload_ids

    async with con.transaction():
        uploads = [dict(row) async for row in con.cursor(query, *query_params)]

    return uploads


async def get_uploads_download_info_for_base_user(con, user_id: str, upload_type: str, upload_ids: list[str]):
    query_params = [user_id, upload_type]
    places = _get_placeholders_str(len(upload_ids), len(query_params) + 1)
    query = f"SELECT filename, prefix FROM uploads WHERE deleted='f' AND multipart_upload_id IS NULL AND user_id=$1 AND type=$2 AND id IN ({places})"
    query_params += upload_ids

    async with con.transaction():
        uploads = [dict(row) async for row in con.cursor(query, *query_params)]

    return uploads


async def create_upload(*, con, upload_params):
    # TODO is this note below true? Shouldn't user_id be a foreign key referencing the users table?
    # the WITH clause in this query is necessary to make sure the given user_id actually exists
    query = (
        "WITH row AS (SELECT id AS user_id FROM users WHERE id=$1) "
        "INSERT INTO uploads (user_id, id, md5, prefix, filename, type, customer_id, auto_upload, multipart_upload_id) "
        "SELECT user_id, $2, $3, $4, $5, $6, $7, $8, $9 FROM row "
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
        upload_params.get("multipart_upload_id"),  # won't be present if upload is not multipart
    )


async def delete_uploads(*, con, account_type, account_id, upload_ids):
    """Query DB to update upload deleted state to true for uploads with the given IDs.

    Performs a join on users table so that one user cannot delete uploads belonging to a different user.
    """
    query_params = [account_id]
    places = _get_placeholders_str(len(upload_ids), len(query_params) + 1)
    if account_type == "user":
        query = f"UPDATE uploads SET deleted='t' WHERE user_id=$1 AND multipart_upload_id IS NULL AND id IN ({places})"
    else:
        # this is essentially doing a JOIN on users WHERE uploads.user_id=users.id
        query = (
            "UPDATE uploads SET deleted='t' FROM users "
            f"WHERE uploads.user_id=users.id AND uploads.multipart_upload_id IS NULL AND users.customer_id=$1 AND uploads.id IN ({places})"
        )
    query_params.extend(upload_ids)
    await con.execute(query, *query_params)


async def get_jobs_of_uploads_for_admin(con, customer_id: str, upload_ids: list[str]):
    query_params = [customer_id]
    places = _get_placeholders_str(len(upload_ids), len(query_params) + 1)
    query = (
        "SELECT j.job_id AS id, j.upload_id, j.status, j.created_at, j.object_key, (j.meta - 'error') AS meta, "
        "u.user_id, u.type AS upload_type "
        "FROM jobs_result AS j JOIN uploads AS u ON j.upload_id=u.id "
        f"WHERE j.customer_id=$1 AND j.status!='deleted' AND u.deleted='f' AND u.multipart_upload_id IS NULL AND u.id IN ({places})"
    )
    query_params += upload_ids

    async with con.transaction():
        jobs = [dict(row) async for row in con.cursor(query, *query_params)]

    return jobs


async def get_jobs_of_uploads_for_rw_all_data_user(
    con, customer_id: str, upload_ids: list[str], upload_type: str
):
    query_params = [customer_id, upload_type]
    places = _get_placeholders_str(len(upload_ids), len(query_params) + 1)
    query = (
        "SELECT j.job_id AS id, j.upload_id, j.status, j.created_at, j.object_key, (j.meta - 'error') AS meta, "
        "u.user_id, u.type AS upload_type "
        "FROM jobs_result AS j JOIN uploads AS u ON j.upload_id=u.id "
        f"WHERE j.customer_id=$1 AND j.status!='deleted' AND u.deleted='f' AND u.multipart_upload_id IS NULL AND u.type=$2 AND u.id IN ({places})"
    )
    query_params += upload_ids

    async with con.transaction():
        jobs = [dict(row) async for row in con.cursor(query, *query_params)]

    return jobs


async def get_jobs_of_uploads_for_base_user(con, user_id: str, upload_ids: list[str], upload_type: str):
    query_params = [user_id, upload_type]
    places = _get_placeholders_str(len(upload_ids), len(query_params) + 1)
    query = (
        "SELECT j.job_id AS id, j.upload_id, j.status, j.created_at, j.object_key, (j.meta - 'error') AS meta, "
        "u.user_id, u.type AS upload_type "
        "FROM jobs_result AS j JOIN uploads AS u ON j.upload_id=u.id "
        f"WHERE j.customer_id=u.customer_id AND u.user_id=$1 AND j.status!='deleted' AND u.deleted='f' AND u.multipart_upload_id IS NULL AND u.type=$2 AND u.id IN ({places})"
    )
    query_params += upload_ids

    async with con.transaction():
        jobs = [dict(row) async for row in con.cursor(query, *query_params)]

    return jobs


async def get_jobs_info_for_admin(
    con,
    customer_id: str,
    upload_type: str,
    sort_field: str | None,
    sort_direction: str | None,
    skip: int,
    limit: int,
    **filters,
):
    query_params = [customer_id, upload_type]
    query = (
        "SELECT j.job_id AS id, j.status, j.created_at, (j.meta  - 'error') AS job_meta, reverse(split_part(reverse(j.object_key), '/', 1)) AS filename, "
        "u.meta AS upload_meta, u.user_id, u.type AS upload_type, users.name AS username "
        "FROM jobs_result AS j "
        "JOIN uploads AS u ON j.upload_id=u.id "
        "JOIN users ON users.id=u.user_id "
        "WHERE j.customer_id=$1 AND j.status!='deleted' AND u.deleted='f' AND u.multipart_upload_id IS NULL AND u.type=$2"
    )

    query, query_params = _add_job_sorting_filtering_conds(
        query, query_params, sort_field, sort_direction, skip, limit, **filters
    )

    async with con.transaction():
        jobs = [dict(row) async for row in con.cursor(query, *query_params)]

    return jobs


async def get_jobs_info_for_rw_all_data_user(
    con,
    customer_id: str,
    upload_type: str,
    sort_field: str | None,
    sort_direction: str | None,
    skip: int,
    limit: int,
    **filters,
):
    query_params = [customer_id, upload_type]
    query = (
        "SELECT j.job_id AS id, j.status, j.created_at, (j.meta  - 'error') AS job_meta, reverse(split_part(reverse(j.object_key), '/', 1)) AS filename, "
        "u.meta AS upload_meta, u.user_id, u.type AS upload_type, users.name AS username "
        "FROM jobs_result AS j "
        "JOIN uploads AS u ON j.upload_id=u.id "
        "JOIN users ON users.id=u.user_id "
        "WHERE j.customer_id=$1 AND j.status!='deleted' AND u.deleted='f' AND u.multipart_upload_id IS NULL AND u.type=$2"
    )

    query, query_params = _add_job_sorting_filtering_conds(
        query, query_params, sort_field, sort_direction, skip, limit, **filters
    )

    async with con.transaction():
        jobs = [dict(row) async for row in con.cursor(query, *query_params)]

    return jobs


async def get_jobs_info_for_base_user(
    con,
    user_id: str,
    upload_type: str,
    sort_field: str | None,
    sort_direction: str | None,
    skip: int,
    limit: int,
    **filters,
):
    query_params = [user_id, upload_type]
    query = (
        "SELECT j.job_id AS id, j.status, j.created_at, (j.meta  - 'error') AS job_meta, reverse(split_part(reverse(j.object_key), '/', 1)) AS filename, "
        "u.meta AS upload_meta, u.user_id, u.type AS upload_type "
        "FROM jobs_result AS j JOIN uploads AS u ON j.upload_id=u.id "
        "WHERE j.customer_id=u.customer_id AND u.user_id=$1 AND j.status!='deleted' AND u.deleted='f' AND u.multipart_upload_id IS NULL AND j.object_key IS NOT NULL AND u.type=$2"
    )

    query, query_params = _add_job_sorting_filtering_conds(
        query, query_params, sort_field, sort_direction, skip, limit, **filters
    )

    async with con.transaction():
        jobs = [dict(row) async for row in con.cursor(query, *query_params)]

    return jobs


def _add_job_sorting_filtering_conds(query, query_params, sort_field, sort_direction, skip, limit, **filters):
    query_params = query_params.copy()

    next_placeholder_count = len(query_params) + 1

    conds = ""
    for filter_name, filter_value in filters.items():
        placeholder = f"${next_placeholder_count}"
        match filter_name:
            case "job_ids":
                new_cond = f"j.job_id=ANY({placeholder}::uuid[])"
            case "status":
                new_cond = f"j.status={placeholder}"
            case "filename":
                new_cond = (
                    f"LOWER(reverse(split_part(reverse(j.object_key), '/', 1))) LIKE LOWER({placeholder})"
                )
                filter_value = f"{filter_value}%"
            case "include_prerelease_versions":
                if filter_value:
                    # if including prerelease versions, no need to add a filter
                    continue
                new_cond = f"j.meta->>'version' NOT LIKE {placeholder}"
                filter_value = "%rc%"
            case "version_min":
                new_cond = f"regexp_split_to_array(j.meta->>'version', '\\.')::int[] >= regexp_split_to_array({placeholder}, '\\.')::int[]"
            case "version_max":
                new_cond = f"regexp_split_to_array(j.meta->>'version', '\\.')::int[] <= regexp_split_to_array({placeholder}, '\\.')::int[]"
            case _:
                continue

        query_params.append(filter_value)
        conds += f" AND {new_cond}"
        next_placeholder_count += 1
    if conds:
        query += conds

    if sort_field in ("id", "created_at", "filename"):
        if sort_field == "created_at":
            sort_field = f"j.{sort_field}"
        if sort_direction not in ("ASC", "DESC"):
            sort_direction = "DESC"
        sort_direction = sort_direction.upper()
        query += f" ORDER BY {sort_field} {sort_direction}"

    query += f" LIMIT ${len(query_params) + 1} OFFSET ${len(query_params) + 2}"
    query_params += [limit, skip]

    return query, query_params


async def get_legacy_jobs_info_for_user(con, user_id: str, job_ids: list[str]):
    query_params = [user_id]
    places = _get_placeholders_str(len(job_ids), len(query_params) + 1)
    query = (
        "SELECT j.job_id, j.upload_id, j.status, j.created_at, j.runtime, j.object_key, j.meta AS job_meta, "
        "u.user_id, u.meta AS user_meta, u.filename, u.prefix, u.type AS upload_type "
        "FROM jobs_result AS j JOIN uploads AS u ON j.upload_id=u.id "
        f"WHERE u.user_id=$1 AND j.status!='deleted' AND u.deleted='f' AND u.multipart_upload_id IS NULL AND j.job_id IN ({places})"
    )
    query_params += job_ids
    async with con.transaction():
        jobs = [dict(row) async for row in con.cursor(query, *query_params)]

    return jobs


async def get_jobs_download_info_for_admin(con, customer_id: str, job_ids: list[str]):
    query_params = [customer_id]
    places = _get_placeholders_str(len(job_ids), len(query_params) + 1)
    query = (
        "SELECT object_key, j.id, j.created_at FROM jobs_result AS j JOIN uploads AS u ON j.upload_id=u.id "
        f"WHERE j.customer_id=$1 AND j.status!='deleted' AND u.deleted='f' AND u.multipart_upload_id IS NULL AND j.job_id IN ({places})"
    )
    query_params += job_ids

    async with con.transaction():
        jobs = [dict(row) async for row in con.cursor(query, *query_params)]

    return jobs


async def get_jobs_download_info_for_rw_all_data_user(
    con, customer_id: str, job_ids: list[str], upload_type: str
):
    query_params = [customer_id, upload_type]
    places = _get_placeholders_str(len(job_ids), len(query_params) + 1)
    query = (
        "SELECT object_key, j.id, j.created_at FROM jobs_result AS j JOIN uploads AS u ON j.upload_id=u.id "
        f"WHERE j.customer_id=$1 AND u.type=$2 AND j.status!='deleted' AND u.deleted='f' AND u.multipart_upload_id IS NULL AND j.job_id IN ({places})"
    )
    query_params += job_ids

    async with con.transaction():
        jobs = [dict(row) async for row in con.cursor(query, *query_params)]

    return jobs


async def get_jobs_download_info_for_base_user(con, user_id: str, job_ids: list[str], upload_type: str):
    query_params = [user_id, upload_type]
    places = _get_placeholders_str(len(job_ids), len(query_params) + 1)
    query = (
        "SELECT object_key, j.id, j.created_at FROM jobs_result AS j JOIN uploads AS u ON j.upload_id=u.id "
        f"WHERE j.customer_id=u.customer_id AND u.user_id=$1 AND u.type=$2 AND j.status!='deleted' AND u.deleted='f' AND u.multipart_upload_id IS NULL AND j.job_id IN ({places})"
    )
    query_params += job_ids

    async with con.transaction():
        jobs = [dict(row) async for row in con.cursor(query, *query_params)]

    return jobs


async def get_job_waveform_data_for_admin_user(con, customer_id: str, job_id: str):
    query_params = [customer_id, job_id]
    query = (
        "SELECT u.prefix, u.filename, (j.meta - 'error') AS job_meta FROM jobs_result AS j JOIN uploads AS u ON j.upload_id=u.id "
        "WHERE j.customer_id=$1 AND j.status!='deleted' AND u.deleted='f' AND u.multipart_upload_id IS NULL AND j.job_id=$2"
    )

    return await con.fetchrow(query, *query_params)


async def get_job_waveform_data_for_rw_all_data_user(con, customer_id: str, job_id: str, upload_type: str):
    query_params = [customer_id, upload_type, job_id]
    query = (
        "SELECT u.prefix, u.filename, (j.meta - 'error') AS job_meta FROM jobs_result AS j JOIN uploads AS u ON j.upload_id=u.id "
        "WHERE j.customer_id=$1 AND u.type=$2 AND j.status!='deleted' AND u.deleted='f' AND u.multipart_upload_id IS NULL AND j.job_id=$3"
    )

    return await con.fetchrow(query, *query_params)


async def get_job_waveform_data_for_base_user(con, user_id: str, job_id: str, upload_type: str):
    query_params = [user_id, upload_type, job_id]
    query = (
        "SELECT u.prefix, u.filename, (j.meta - 'error') AS job_meta FROM jobs_result AS j JOIN uploads AS u ON j.upload_id=u.id "
        "WHERE j.customer_id=u.customer_id AND u.user_id=$1 AND u.type=$2 AND j.status!='deleted' AND u.deleted='f' AND u.multipart_upload_id IS NULL AND j.job_id=$3"
    )

    return await con.fetchrow(query, *query_params)


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


async def get_customer_pulse3d_usage(con, customer_id, upload_type) -> dict[str, Any]:
    """Query DB and return usage limit and current usage.
    Returns:
        - Dictionary with account limits and account usage
    """
    # get upload-type specific usage restrictions for the admin account
    # uploads limit, jobs limit, end date of plan
    usage_limit_query = "SELECT usage_restrictions->$1 AS usage FROM customers WHERE id=$2"
    # collects number of all jobs in admin account and return number of credits consumed
    # upload with 1 - 2 jobs  = 1 credit , upload with 3+ jobs = 1 credit for each upload with over 2 jobs
    current_usage_query = (
        "SELECT COUNT(*) AS total_uploads, SUM(jobs_count) AS total_jobs "
        "FROM ( SELECT ( CASE WHEN (COUNT(*) <= 2 AND COUNT(*) > 0) THEN 1 ELSE GREATEST(COUNT(*) - 1, 0) END ) AS jobs_count FROM jobs_result WHERE customer_id=$1 and type=$2 GROUP BY upload_id) dt"
    )

    usage_limit_json = await con.fetchrow(usage_limit_query, upload_type, customer_id)
    current_usage_data = await con.fetchrow(current_usage_query, customer_id, upload_type)

    usage_limit_dict = json.loads(usage_limit_json["usage"])

    # usage query returns none if no jobs are found but 0 if no uploads are found
    current_job_usage = current_usage_data.get("total_jobs", 0)
    if current_job_usage is None:
        current_job_usage = 0
    current_usage_dict = {
        "jobs": current_job_usage,
        "uploads": int(current_usage_data.get("total_uploads", 0)),
    }

    return {"limits": usage_limit_dict, "current": current_usage_dict}


async def check_customer_pulse3d_usage(con, customer_id, upload_type) -> dict[str, Any]:
    """Query DB for upload-type-specific customer account usage.

    Will be called for all account tiers, unlimited has a value of -1.
    Returns:
        - Dictionary containing boolean values for if uploads or job quotas have been reached
        - Dictionary also contains data about max usage and end date.
    """
    usage_info = await get_customer_pulse3d_usage(con, customer_id, upload_type)

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
        "INSERT INTO analysis_presets (user_id, name, parameters, type) "
        "VALUES ($1, $2, $3, $4) "
        "ON CONFLICT ON CONSTRAINT unique_name_type_per_user DO "
        "UPDATE SET parameters=$3 WHERE analysis_presets.user_id=$1 AND analysis_presets.name=$2 AND analysis_presets.type=$4"
    )

    return await con.fetchval(
        query, user_id, details.name, json.dumps(details.analysis_params), details.upload_type
    )


async def check_customer_advanced_analysis_usage(con, customer_id):
    usage_limits_json = await con.fetchval(
        "SELECT usage_restrictions->'advanced_analysis' FROM customers WHERE id=$1", customer_id
    )
    current_job_count = await con.fetchval(
        "SELECT COUNT(*) FROM advanced_analysis_result WHERE customer_id=$1", customer_id
    )
    current_job_count = int(current_job_count)

    usage_limits = json.loads(usage_limits_json)

    is_expired = False
    # if there is an expiration date, check if we have passed it
    if expiration_date := usage_limits["expiration_date"]:
        is_expired = datetime.strptime(expiration_date, "%Y-%m-%d") < datetime.utcnow()

    jobs_count_reached = False
    if (job_limit := usage_limits["jobs"]) != -1:
        jobs_count_reached = current_job_count >= job_limit

    return {
        "limits": usage_limits,
        "current": {"jobs": current_job_count},
        "jobs_reached": is_expired or jobs_count_reached,
    }


async def get_advanced_analyses_for_admin(
    con,
    customer_id: str,
    sort_field: str | None,
    sort_direction: str | None,
    skip: int,
    limit: int,
    **filters,
):
    query = (
        "SELECT id, type, status, sources, (meta - 'error') AS meta, created_at, name "
        "FROM advanced_analysis_result "
        "WHERE customer_id=$1 AND status!='deleted'"
    )
    query_params = [customer_id]

    query, query_params = _add_advanced_analysis_sorting_filtering_conds(
        query, query_params, sort_field, sort_direction, skip, limit, **filters
    )

    async with con.transaction():
        advanced_analyses = [dict(row) async for row in con.cursor(query, *query_params)]

    return advanced_analyses


async def get_advanced_analyses_for_base_user(
    con, user_id: str, sort_field: str | None, sort_direction: str | None, skip: int, limit: int, **filters
):
    query = (
        "SELECT id, type, status, sources, (meta - 'error') AS meta, created_at, name "
        "FROM advanced_analysis_result "
        "WHERE user_id=$1 AND status!='deleted'"
    )
    query_params = [user_id]

    query, query_params = _add_advanced_analysis_sorting_filtering_conds(
        query, query_params, sort_field, sort_direction, skip, limit, **filters
    )

    async with con.transaction():
        advanced_analyses = [dict(row) async for row in con.cursor(query, *query_params)]

    return advanced_analyses


def _add_advanced_analysis_sorting_filtering_conds(
    query, query_params, sort_field, sort_direction, skip, limit, **filters
):
    query_params = query_params.copy()

    next_placeholder_count = len(query_params) + 1

    conds = ""
    for filter_name, filter_value in filters.items():
        placeholder = f"${next_placeholder_count}"
        match filter_name:
            case "name":
                new_cond = f"LOWER(name) LIKE LOWER({placeholder})"
                filter_value = f"%{filter_value}%"
            case "id":
                new_cond = f"id::text LIKE {placeholder}"
                filter_value = f"%{filter_value}%"
            case "type":
                new_cond = f"type = LOWER({placeholder})"
            case "created_at_min":
                new_cond = f"created_at >= to_timestamp({placeholder}, 'YYYY-MM-DD\"T\"HH:MI:SS.MSZ')"
            case "created_at_max":
                new_cond = f"created_at <= to_timestamp({placeholder}, 'YYYY-MM-DD\"T\"HH:MI:SS.MSZ')"
            case "status":
                new_cond = f"status={placeholder}"
            case _:
                continue

        query_params.append(filter_value)
        conds += f" AND {new_cond}"
        next_placeholder_count += 1
    if conds:
        query += conds

    if sort_field in ("name", "id", "created_at", "type", "status"):
        if sort_direction not in ("ASC", "DESC"):
            sort_direction = "DESC"
        sort_direction = sort_direction.upper()
        query += f" ORDER BY {sort_field} {sort_direction}"

    query += f" LIMIT ${len(query_params) + 1} OFFSET ${len(query_params) + 2}"
    query_params += [limit, skip]

    return query, query_params


async def create_advanced_analysis_job(
    *, con, sources, queue, priority, meta, user_id, customer_id, job_type
):
    # the WITH clause in this query is necessary to make sure the given upload_id actually exists
    enqueue_job_query = (
        "INSERT INTO jobs_queue (sources, queue, priority, meta) VALUES ($1, $2, $3, $4) RETURNING id"
    )
    async with con.transaction():
        # add job to queue
        job_id = await con.fetchval(enqueue_job_query, sources, queue, priority, json.dumps(meta))

        data = {
            "id": job_id,
            "user_id": user_id,
            "customer_id": customer_id,
            "type": job_type,
            "status": "pending",
            "sources": sources,
            "meta": json.dumps(meta),
        }

        cols = ", ".join(list(data))
        places = _get_placeholders_str(len(data))

        # add job to the result table
        await con.execute(f"INSERT INTO advanced_analysis_result ({cols}) VALUES ({places})", *data.values())

    return job_id


async def delete_advanced_analyses(*, con, user_id, job_ids):
    await con.execute(
        "UPDATE advanced_analysis_result SET status='deleted' WHERE user_id=$1 AND id=ANY($2::uuid[])",
        user_id,
        job_ids,
    )


async def get_advanced_analyses_download_info_for_base_user(*, con, user_id, job_ids):
    query = (
        "SELECT id, s3_prefix, name, created_at FROM advanced_analysis_result "
        "WHERE user_id=$1 AND status='finished' AND id=ANY($2::uuid[])"
    )

    async with con.transaction():
        jobs = [dict(row) async for row in con.cursor(query, user_id, job_ids)]

    return jobs


async def get_advanced_analyses_download_info_for_admin(*, con, customer_id, job_ids):
    query = (
        "SELECT id, s3_prefix, name, created_at FROM advanced_analysis_result "
        "WHERE customer_id=$1 AND status='finished' AND id=ANY($2::uuid[])"
    )

    async with con.transaction():
        jobs = [dict(row) async for row in con.cursor(query, customer_id, job_ids)]

    return jobs
