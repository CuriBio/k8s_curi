from fastapi.testclient import TestClient
import json
import os
import uuid

import pytest

from auth import create_token
from src import main

test_client = TestClient(main.app)


def get_token(scope, account_type="user", userid=None, customer_id=None):
    if not userid:
        userid = uuid.uuid4()
    if account_type == "user" and not customer_id:
        customer_id = uuid.uuid4()
    return create_token(
        userid=userid, customer_id=customer_id, scope=scope, account_type=account_type, refresh=False
    ).token


@pytest.fixture(scope="function", name="mocked_asyncpg_con", autouse=True)
async def fixture_mocked_asyncpg_con(mocker):
    mocked_asyncpg_pool = mocker.patch.object(main, "asyncpg_pool", autospec=True)

    mocked_asyncpg_pool_coroutine = mocker.AsyncMock()
    mocked_asyncpg_pool_coroutine.return_value = mocker.MagicMock()
    mocked_asyncpg_pool.return_value = mocked_asyncpg_pool_coroutine()

    mocked_asyncpg_con = await mocked_asyncpg_pool_coroutine.return_value.acquire().__aenter__()
    yield mocked_asyncpg_con


def test_logs__post(mocker):
    expected_params = {"key": "val"}
    mocked_gpp = mocker.patch.object(
        main, "generate_presigned_post", autospec=True, return_value=expected_params
    )

    test_file_name = "log_file"
    test_user_id = uuid.uuid4()
    test_customer_id = uuid.uuid4()

    access_token = get_token(scope=["users:free"], customer_id=test_customer_id, userid=test_user_id)
    kwargs = {
        "headers": {"Authorization": f"Bearer {access_token}"},
        "json": {"filename": test_file_name, "upload_type": "logs"},
    }
    response = test_client.post("/logs", **kwargs)
    assert response.status_code == 200

    mocked_gpp.assert_called_once_with(
        bucket=main.MANTARRAY_LOGS_BUCKET,
        key=f"uploads/{test_customer_id}/{test_user_id}/{test_file_name}",
        md5s=None,
    )


@pytest.mark.parametrize("test_token_scope", [["users:free"], ["users:admin"]])
@pytest.mark.parametrize(
    "test_upload_ids", [None, [], uuid.uuid4(), [uuid.uuid4()], [uuid.uuid4() for _ in range(3)]]
)
def test_uploads__get(test_token_scope, test_upload_ids, mocked_asyncpg_con, mocker):
    mocked_get_uploads = mocker.patch.object(main, "get_uploads", autospec=True, return_value=[])

    test_account_id = uuid.uuid4()
    account_type = "customer" if test_token_scope == ["users:admin"] else "user"
    access_token = get_token(scope=test_token_scope, account_type=account_type, userid=test_account_id)

    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}}
    # in None case, don't even pass a query param
    if test_upload_ids is not None:
        kwargs["params"] = {"upload_ids": test_upload_ids}

    response = test_client.get("/uploads", **kwargs)
    assert response.status_code == 200
    assert response.json() == mocked_get_uploads.return_value

    if test_upload_ids:
        if isinstance(test_upload_ids, uuid.UUID):
            # fastapi automatically converts a single UUID to a list
            test_upload_ids = [test_upload_ids]
        expected_upload_ids = [str(test_id) for test_id in test_upload_ids]
    else:
        # falsey query params are automatically converted to None
        expected_upload_ids = None

    mocked_get_uploads.assert_called_once_with(
        con=mocked_asyncpg_con,
        account_type=account_type,
        account_id=str(test_account_id),
        upload_ids=expected_upload_ids,
    )


def test_uploads__post(mocked_asyncpg_con, mocker):
    mocked_asyncpg_con.transaction = mocker.MagicMock()

    expected_upload_id = uuid.uuid4()
    mocked_create_upload = mocker.patch.object(
        main, "create_upload", autospec=True, return_value=expected_upload_id
    )
    expected_params = {"key": "val"}
    mocked_gpp = mocker.patch.object(
        main, "generate_presigned_post", autospec=True, return_value=expected_params
    )

    test_file_name = "recording_file"
    test_md5s = "testhash"
    test_upload_type = "mantarray"
    test_user_id = uuid.uuid4()
    test_customer_id = uuid.uuid4()

    access_token = get_token(scope=["users:free"], customer_id=test_customer_id, userid=test_user_id)
    kwargs = {
        "headers": {"Authorization": f"Bearer {access_token}"},
        "json": {"filename": test_file_name, "md5s": test_md5s, "upload_type": test_upload_type},
    }
    response = test_client.post("/uploads", **kwargs)
    assert response.status_code == 200

    expected_upload_params = {
        "prefix": f"uploads/{test_customer_id}/{test_user_id}/{{upload_id}}",
        "filename": test_file_name,
        "md5": test_md5s,
        "user_id": str(test_user_id),
        "type": test_upload_type,
    }

    mocked_create_upload.assert_called_once_with(con=mocked_asyncpg_con, upload_params=expected_upload_params)
    mocked_gpp.assert_called_once_with(
        bucket=main.PULSE3D_UPLOADS_BUCKET,
        key=f"uploads/{test_customer_id}/{test_user_id}/{expected_upload_id}/{test_file_name}",
        md5s=test_md5s,
    )


@pytest.mark.parametrize("test_token_scope", [["users:free"], ["users:admin"]])
@pytest.mark.parametrize("test_upload_ids", [uuid.uuid4(), [uuid.uuid4()], [uuid.uuid4() for _ in range(3)]])
def test_uploads__delete(test_token_scope, test_upload_ids, mocked_asyncpg_con, mocker):
    mocked_delete_uploads = mocker.patch.object(main, "delete_uploads", autospec=True)

    test_account_id = uuid.uuid4()
    account_type = "customer" if test_token_scope == ["users:admin"] else "user"
    access_token = get_token(scope=test_token_scope, account_type=account_type, userid=test_account_id)
    kwargs = {
        "headers": {"Authorization": f"Bearer {access_token}"},
        "params": {"upload_ids": test_upload_ids},
    }

    response = test_client.delete("/uploads", **kwargs)
    assert response.status_code == 200

    if isinstance(test_upload_ids, uuid.UUID):
        # fastapi automatically converts a single UUID to a list
        test_upload_ids = [test_upload_ids]

    expected_upload_ids = [str(test_id) for test_id in test_upload_ids]

    mocked_delete_uploads.assert_called_once_with(
        con=mocked_asyncpg_con,
        account_type=account_type,
        account_id=str(test_account_id),
        upload_ids=expected_upload_ids,
    )


@pytest.mark.parametrize("test_upload_ids", [None, []])
def test_uploads__delete__no_upload_ids_given(test_upload_ids, mocker):
    mocked_delete_uploads = mocker.patch.object(main, "delete_uploads", autospec=True)

    access_token = get_token(scope=["users:free"])
    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}}

    # in None case, don't even pass a query param
    if test_upload_ids is not None:
        kwargs["params"] = {"upload_ids": test_upload_ids}

    response = test_client.delete("/uploads", **kwargs)
    assert response.status_code == 400

    mocked_delete_uploads.assert_not_called()


def test_uploads__delete__failure_to_delete_uploads(mocker):
    mocker.patch.object(main, "delete_uploads", autospec=True, side_effect=Exception())

    test_user_id = uuid.uuid4()
    access_token = get_token(scope=["users:free"], userid=test_user_id)
    kwargs = {
        "headers": {"Authorization": f"Bearer {access_token}"},
        "params": {"upload_ids": [uuid.uuid4()]},
    }

    response = test_client.delete("/uploads", **kwargs)
    assert response.status_code == 500


@pytest.mark.parametrize("download", [True, False, None])
@pytest.mark.parametrize("test_token_scope", [["users:free"], ["users:admin"]])
@pytest.mark.parametrize(
    "test_job_ids", [None, [], uuid.uuid4(), [uuid.uuid4()], [uuid.uuid4() for _ in range(3)]]
)
def test_jobs__get__jobs_found(download, test_token_scope, test_job_ids, mocked_asyncpg_con, mocker):
    if test_job_ids:
        if isinstance(test_job_ids, uuid.UUID):
            # fastapi automatically converts a single UUID to a list
            expected_job_ids = [str(test_job_ids)]
        else:
            expected_job_ids = [str(test_id) for test_id in test_job_ids]
    else:
        # if no job IDs given, then all jobs are returned
        expected_job_ids = [str(uuid.uuid4()) for _ in range(3)]

    test_statuses = ["finished", "pending", "error"]
    test_job_rows = [
        {
            "status": status,
            "job_id": f"job{i}",
            "upload_id": str(job_id),
            "created_at": i,
            "job_meta": json.dumps({"error": f"e{i}"}),
            "object_key": f"obj{i}",
        }
        for i, (status, job_id) in enumerate(zip(test_statuses, expected_job_ids))
    ]

    mocked_get_jobs = mocker.patch.object(main, "get_jobs", autospec=True, return_value=test_job_rows)
    mocked_generate = mocker.patch.object(main, "generate_presigned_url", autospec=True, return_value="url0")

    test_account_id = uuid.uuid4()
    account_type = "customer" if test_token_scope == ["users:admin"] else "user"
    access_token = get_token(scope=test_token_scope, account_type=account_type, userid=test_account_id)

    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}, "params": {}}
    # in None case, don't even pass a query param
    if test_job_ids is not None:
        kwargs["params"]["job_ids"] = test_job_ids
    if download is not None:
        kwargs["params"]["download"] = download

    response = test_client.get("/jobs", **kwargs)
    assert response.status_code == 200

    job0 = {"status": "finished"}
    if download is not False:
        # deafult value is True, so if download is True or None (not given) then a url will be returned
        job0["url"] = mocked_generate.return_value
    jobs = [job0]

    if expected_job_ids and len(expected_job_ids) > 1:
        jobs.extend([{"status": test_statuses[1]}, {"status": test_statuses[2], "error_info": "e2"}])
    for job, job_row in zip(jobs, test_job_rows):
        job.update(job_row)
        # rename keys
        job["id"] = job.pop("job_id")
        job["meta"] = job.pop("job_meta")

    # if all jobs are retrieved successfully, this should be the only key in the response dict
    assert list(response.json()) == ["jobs"]

    for response_job, expected_job in zip(response.json()["jobs"], jobs):
        assert response_job == expected_job

    expected_job_id_arg = None if not test_job_ids else expected_job_ids
    mocked_get_jobs.assert_called_once_with(
        con=mocked_asyncpg_con,
        account_type=account_type,
        account_id=str(test_account_id),
        job_ids=expected_job_id_arg,
    )
    # download param defaults to true, so the only time this function won't be called is if False is explicity passed
    if download is False:
        mocked_generate.assert_not_called()
    else:
        mocked_generate.assert_called_once_with(main.PULSE3D_UPLOADS_BUCKET, test_job_rows[0]["object_key"])


def test_jobs__get__error_with_creating_presigned_url_for_single_file(mocked_asyncpg_con, mocker):
    test_num_jobs = 3
    test_job_ids = [uuid.uuid4() for _ in range(test_num_jobs)]
    expected_job_ids = [str(test_id) for test_id in test_job_ids]
    # use job_ids as upload_ids to make testing easier
    test_job_rows = [
        {
            "status": "finished",
            "job_id": f"job{i}",
            "upload_id": str(job_id),
            "created_at": i,
            "job_meta": json.dumps({"error": f"e{i}"}),
            "object_key": f"obj{i}",
        }
        for i, job_id in enumerate(test_job_ids)
    ]

    mocked_get_jobs = mocker.patch.object(main, "get_jobs", autospec=True, return_value=test_job_rows)
    mocked_generate = mocker.patch.object(
        main, "generate_presigned_url", autospec=True, side_effect=["url0", Exception(), "url2"]
    )

    test_user_id = uuid.uuid4()
    access_token = get_token(scope=["users:free"], userid=test_user_id)

    kwargs = {
        "headers": {"Authorization": f"Bearer {access_token}"},
        "params": {"job_ids": test_job_ids, "download": True},
    }
    response = test_client.get("/jobs", **kwargs)
    assert response.status_code == 200

    jobs = [
        {"url": "url0"},
        {"url": "Error creating download link"},
        {"url": "url2"},
    ]
    for i, job in enumerate(jobs):
        job.update(test_job_rows[i])
        # rename keys
        job["id"] = job.pop("job_id")
        job["meta"] = job.pop("job_meta")

    assert list(response.json()) == ["jobs"]
    for response_job, expected_job in zip(response.json()["jobs"], jobs):
        assert response_job == expected_job

    mocked_get_jobs.assert_called_once_with(
        con=mocked_asyncpg_con, account_type="user", account_id=str(test_user_id), job_ids=expected_job_ids
    )
    assert mocked_generate.call_args_list == [
        mocker.call(main.PULSE3D_UPLOADS_BUCKET, test_job_rows[i]["object_key"]) for i in range(test_num_jobs)
    ]


def test_jobs__get__no_jobs_found(mocked_asyncpg_con, mocker):
    # falsey query params are automatically converted to None
    expected_job_ids = None

    mocked_get_jobs = mocker.patch.object(main, "get_jobs", autospec=True, return_value=[])
    mocked_get_uploads = mocker.patch.object(main, "get_uploads", autospec=True)

    test_user_id = uuid.uuid4()
    access_token = get_token(scope=["users:free"], userid=test_user_id)

    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}}
    response = test_client.get("/jobs", **kwargs)
    assert response.status_code == 200
    assert response.json() == {"error": "No jobs found", "jobs": []}

    mocked_get_jobs.assert_called_once_with(
        con=mocked_asyncpg_con, account_type="user", account_id=str(test_user_id), job_ids=expected_job_ids
    )
    mocked_get_uploads.assert_not_called()


def test_jobs__post__no_params_given(mocked_asyncpg_con, mocker):
    expected_job_id = uuid.uuid4()
    expected_job_priority = 10
    test_upload_id = uuid.uuid4()
    test_user_id = uuid.uuid4()

    access_token = get_token(scope=["users:free"], userid=test_user_id)

    mocked_create_job = mocker.patch.object(main, "create_job", autospec=True, return_value=expected_job_id)

    kwargs = {
        "json": {"upload_id": str(test_upload_id)},
        "headers": {"Authorization": f"Bearer {access_token}"},
    }
    response = test_client.post("/jobs", **kwargs)
    assert response.status_code == 200
    assert response.json() == {
        "id": str(expected_job_id),
        "user_id": str(test_user_id),
        "upload_id": str(test_upload_id),
        "status": "pending",
        "priority": expected_job_priority,
    }

    expected_analysis_params = {
        param: None
        for param in (
            "normalize_y_axis",
            "baseline_widths_to_use",
            "max_y",
            "prominence_factors",
            "width_factors",
            "twitch_widths",
            "start_time",
            "end_time",
        )
    }

    mocked_create_job.assert_called_once_with(
        con=mocked_asyncpg_con,
        upload_id=test_upload_id,
        queue="pulse3d",
        priority=expected_job_priority,
        meta={"analysis_params": expected_analysis_params},
    )


def test_jobs__post__basic_params_given(mocker):
    expected_job_id = uuid.uuid4()
    test_upload_id = uuid.uuid4()
    test_user_id = uuid.uuid4()
    test_analysis_params = {"twitch_widths": [10, 20], "start_time": 0, "end_time": 1}

    access_token = get_token(scope=["users:free"], userid=test_user_id)

    mocked_create_job = mocker.patch.object(main, "create_job", autospec=True, return_value=expected_job_id)

    kwargs = {
        "json": {"upload_id": str(test_upload_id), **test_analysis_params},
        "headers": {"Authorization": f"Bearer {access_token}"},
    }
    response = test_client.post("/jobs", **kwargs)
    assert response.status_code == 200

    expected_analysis_params = {
        param: None
        for param in (
            "normalize_y_axis",
            "baseline_widths_to_use",
            "max_y",
            "prominence_factors",
            "width_factors",
            "twitch_widths",
            "start_time",
            "end_time",
        )
    }
    expected_analysis_params.update(test_analysis_params)

    mocked_create_job.assert_called_once()
    assert mocked_create_job.call_args[1]["meta"]["analysis_params"] == expected_analysis_params


@pytest.mark.parametrize("param_name", ["prominence_factors", "width_factors"])
@pytest.mark.parametrize("param_tuple", [(1, 2), (None, 2), (1, None), (None, None)])
def test_jobs__post__advanced_params_given(param_name, param_tuple, mocker):
    expected_job_id = uuid.uuid4()
    test_upload_id = uuid.uuid4()
    test_user_id = uuid.uuid4()
    test_analysis_params = {param_name: param_tuple}

    access_token = get_token(scope=["users:free"], userid=test_user_id)

    mocked_create_job = mocker.patch.object(main, "create_job", autospec=True, return_value=expected_job_id)

    kwargs = {
        "json": {"upload_id": str(test_upload_id), **test_analysis_params},
        "headers": {"Authorization": f"Bearer {access_token}"},
    }
    response = test_client.post("/jobs", **kwargs)
    assert response.status_code == 200

    expected_default_value = 6 if param_name == "prominence_factors" else 7
    format_mapping = {
        (1, 2): (1, 2),
        (None, 2): (expected_default_value, 2),
        (1, None): (1, expected_default_value),
        (None, None): None,
    }

    expected_analysis_params = {
        param: None
        for param in (
            "normalize_y_axis",
            "baseline_widths_to_use",
            "max_y",
            "prominence_factors",
            "width_factors",
            "twitch_widths",
            "start_time",
            "end_time",
        )
    }
    expected_analysis_params.update({param_name: format_mapping[param_tuple]})

    mocked_create_job.assert_called_once()
    assert mocked_create_job.call_args[1]["meta"]["analysis_params"] == expected_analysis_params


@pytest.mark.parametrize("param_tuple", [(1, 2), (None, 2), (1, None), (None, None)])
def test_jobs__post__with_baseline_widths_to_use(param_tuple, mocker):
    expected_job_id = uuid.uuid4()
    test_upload_id = uuid.uuid4()
    test_user_id = uuid.uuid4()
    test_analysis_params = {"baseline_widths_to_use": param_tuple}

    access_token = get_token(scope=["users:free"], userid=test_user_id)

    mocked_create_job = mocker.patch.object(main, "create_job", autospec=True, return_value=expected_job_id)

    kwargs = {
        "json": {"upload_id": str(test_upload_id), **test_analysis_params},
        "headers": {"Authorization": f"Bearer {access_token}"},
    }
    response = test_client.post("/jobs", **kwargs)
    assert response.status_code == 200

    format_mapping = {
        (1, 2): (1, 2),
        (None, 2): (10, 2),
        (1, None): (1, 90),
        (None, None): None,
    }

    expected_analysis_params = {
        param: None
        for param in (
            "normalize_y_axis",
            "baseline_widths_to_use",
            "max_y",
            "prominence_factors",
            "width_factors",
            "twitch_widths",
            "start_time",
            "end_time",
        )
    }

    expected_analysis_params.update({"baseline_widths_to_use": format_mapping[param_tuple]})

    mocked_create_job.assert_called_once()
    assert mocked_create_job.call_args[1]["meta"]["analysis_params"] == expected_analysis_params


@pytest.mark.parametrize("test_token_scope", [["users:free"], ["users:admin"]])
@pytest.mark.parametrize("test_job_ids", [uuid.uuid4(), [uuid.uuid4()], [uuid.uuid4() for _ in range(3)]])
def test_jobs__delete(test_token_scope, test_job_ids, mocked_asyncpg_con, mocker):
    mocked_delete_jobs = mocker.patch.object(main, "delete_jobs", autospec=True)

    test_account_id = uuid.uuid4()
    account_type = "customer" if test_token_scope == ["users:admin"] else "user"
    access_token = get_token(scope=test_token_scope, account_type=account_type, userid=test_account_id)
    kwargs = {
        "headers": {"Authorization": f"Bearer {access_token}"},
        "params": {"job_ids": test_job_ids},
    }

    response = test_client.delete("/jobs", **kwargs)
    assert response.status_code == 200

    if isinstance(test_job_ids, uuid.UUID):
        # fastapi automatically converts a single UUID to a list
        test_job_ids = [test_job_ids]

    expected_job_ids = [str(test_id) for test_id in test_job_ids]

    mocked_delete_jobs.assert_called_once_with(
        con=mocked_asyncpg_con,
        account_type=account_type,
        account_id=str(test_account_id),
        job_ids=expected_job_ids,
    )


@pytest.mark.parametrize("test_job_ids", [None, []])
def test_jobs__delete__no_job_ids_given(test_job_ids, mocker):
    mocked_delete_jobs = mocker.patch.object(main, "delete_jobs", autospec=True)

    test_user_id = uuid.uuid4()
    access_token = get_token(scope=["users:free"], userid=test_user_id)
    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}}

    # in None case, don't even pass a query param
    if test_job_ids is not None:
        kwargs["params"] = {"job_ids": test_job_ids}

    response = test_client.delete("/jobs", **kwargs)
    assert response.status_code == 400

    mocked_delete_jobs.assert_not_called()


def test_jobs__delete__failure_to_delete_jobs(mocker):
    mocker.patch.object(main, "delete_jobs", autospec=True, side_effect=Exception())

    test_user_id = uuid.uuid4()
    access_token = get_token(scope=["users:free"], userid=test_user_id)
    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}, "params": {"job_ids": [uuid.uuid4()]}}

    response = test_client.delete("/jobs", **kwargs)
    assert response.status_code == 500


@pytest.mark.parametrize("test_token_scope", [["users:free"], ["users:admin"]])
@pytest.mark.parametrize("test_job_ids", [[uuid.uuid4() for _ in range(r)] for r in range(1, 4)])
def test_jobs_download__post__no_duplicate_analysis_file_names(
    test_token_scope, test_job_ids, mocked_asyncpg_con, mocker
):
    test_account_id = uuid.uuid4()
    account_type = "customer" if test_token_scope == ["users:admin"] else "user"
    access_token = get_token(scope=test_token_scope, account_type=account_type, userid=test_account_id)

    test_statuses = ["finished", "finished", "pending", "error"]
    test_job_rows = [
        {
            "status": status,
            "job_id": f"job{i}",
            "upload_id": str(job_id),
            "created_at": i,
            "job_meta": f"jmeta{i}",
            "object_key": f"/obj/prefix/file{i}.xlsx",
        }
        for i, (status, job_id) in enumerate(zip(test_statuses, test_job_ids))
    ]

    mocked_get_jobs = mocker.patch.object(main, "get_jobs", autospec=True, return_value=test_job_rows)
    mocked_yield_objs = mocker.patch.object(main, "_yield_s3_objects", autospec=True)

    test_job_ids_strs = [str(job_id) for job_id in test_job_ids]

    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}, "json": {"job_ids": test_job_ids_strs}}
    response = test_client.post("/jobs/download", **kwargs)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    mocked_get_jobs.assert_called_once_with(
        con=mocked_asyncpg_con,
        account_type=account_type,
        account_id=str(test_account_id),
        job_ids=test_job_ids_strs,
    )

    expected_keys = [job_row["object_key"] for job_row in test_job_rows if job_row["status"] == "finished"]
    mocked_yield_objs.assert_called_once_with(
        bucket="test-pulse3d-uploads",
        filenames=[os.path.basename(key) for key in expected_keys],
        keys=expected_keys,
    )


@pytest.mark.parametrize("test_token_scope", [["users:free"], ["users:admin"]])
def test_download__post__duplicate_analysis_file_names(mocked_asyncpg_con, test_token_scope, mocker):
    test_account_id = uuid.uuid4()
    account_type = "customer" if test_token_scope == ["users:admin"] else "user"
    access_token = get_token(scope=test_token_scope, account_type=account_type, userid=test_account_id)

    test_job_ids = [uuid.uuid4() for _ in range(3)]

    test_job_rows = [
        {
            "status": "finished",
            "job_id": f"job{i}",
            "upload_id": str(job_id),
            "created_at": i,
            "job_meta": f"jmeta{i}",
            "object_key": f"/prefix/{i}/file.xlsx",
        }
        for i, job_id in enumerate(test_job_ids)
    ]

    mocked_get_jobs = mocker.patch.object(main, "get_jobs", autospec=True, return_value=test_job_rows)
    mocked_yield_objs = mocker.patch.object(main, "_yield_s3_objects", autospec=True)

    test_job_ids_strs = [str(job_id) for job_id in test_job_ids]

    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}, "json": {"job_ids": test_job_ids_strs}}
    response = test_client.post("/jobs/download", **kwargs)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    mocked_get_jobs.assert_called_once_with(
        con=mocked_asyncpg_con,
        account_type=account_type,
        account_id=str(test_account_id),
        job_ids=test_job_ids_strs,
    )

    expected_keys = [job_row["object_key"] for job_row in test_job_rows]
    mocked_yield_objs.assert_called_once_with(
        bucket="test-pulse3d-uploads",
        filenames=["file.xlsx", "file_(1).xlsx", "file_(2).xlsx"],
        keys=expected_keys,
    )


@pytest.mark.parametrize("test_job_ids,test_error_code", [(None, 422), ([], 400)])
def test_download__post__no_job_ids_given(test_job_ids, test_error_code, mocker):
    mocked_get_jobs = mocker.patch.object(main, "get_jobs", autospec=True)
    mocked_yield_objs = mocker.patch.object(main, "_yield_s3_objects", autospec=True)

    access_token = get_token(scope=["users:free"])

    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}}
    # in None case, don't even pass a param
    if test_job_ids is not None:
        kwargs["json"] = {"job_ids": test_job_ids}

    response = test_client.post("/jobs/download", **kwargs)
    assert response.status_code == test_error_code

    mocked_get_jobs.assert_not_called()
    mocked_yield_objs.assert_not_called()
