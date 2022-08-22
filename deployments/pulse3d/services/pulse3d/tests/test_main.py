from fastapi.testclient import TestClient
import json
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


def test__uploads__post(mocked_asyncpg_con, mocker):
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


@pytest.mark.parametrize("test_upload_ids", [uuid.uuid4(), [uuid.uuid4()], [uuid.uuid4() for _ in range(3)]])
def test_uploads__delete(test_upload_ids, mocked_asyncpg_con, mocker):
    if isinstance(test_upload_ids, uuid.UUID):
        # fastapi automatically converts a single UUID to a list
        test_upload_ids = [test_upload_ids]

    expected_upload_ids = [str(test_id) for test_id in test_upload_ids]

    mocked_delete_uploads = mocker.patch.object(main, "delete_uploads", autospec=True)

    test_account_id = uuid.uuid4()
    access_token = get_token(scope=["users:free"], userid=test_account_id)
    kwargs = {
        "headers": {"Authorization": f"Bearer {access_token}"},
        "params": {"upload_ids": test_upload_ids},
    }

    response = test_client.delete("/uploads", **kwargs)
    assert response.status_code == 200

    mocked_delete_uploads.assert_called_once_with(
        con=mocked_asyncpg_con, account_id=str(test_account_id), upload_ids=expected_upload_ids
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


@pytest.mark.parametrize("download", [True, False])
@pytest.mark.parametrize("test_job_ids", [uuid.uuid4(), [uuid.uuid4()], [uuid.uuid4() for _ in range(3)]])
def test_jobs__get__jobs_found(download, test_job_ids, mocked_asyncpg_con, mocker):
    if isinstance(test_job_ids, uuid.UUID):
        # fastapi automatically converts a single UUID to a list
        test_job_ids = [test_job_ids]

    expected_job_ids = [str(test_id) for test_id in test_job_ids]
    test_statuses = ["finished", "pending", "error"]
    test_upload_rows = [
        {
            "status": status,
            "job_id": f"upload{i}",
            "upload_id": str(job_id),
            "created_at": i,
            "job_meta": json.dumps({"error": f"e{i}"}),
            "object_key": f"obj{i}",
        }
        for i, (status, job_id) in enumerate(zip(test_statuses, test_job_ids))
    ]

    mocked_get_jobs = mocker.patch.object(main, "get_jobs", autospec=True, return_value=test_upload_rows)
    mocked_generate = mocker.patch.object(main, "generate_presigned_url", autospec=True, return_value="url0")

    test_user_id = uuid.uuid4()
    access_token = get_token(scope=["users:free"], userid=test_user_id)

    kwargs = {
        "headers": {"Authorization": f"Bearer {access_token}"},
        "params": {"job_ids": test_job_ids, "download": download},
    }
    response = test_client.get("/jobs", **kwargs)
    assert response.status_code == 200

    job0 = {"status": "finished"}
    if download:
        job0["url"] = mocked_generate.return_value
    jobs = [job0]
    if len(expected_job_ids) > 1:
        jobs.extend([{"status": "pending"}, {"status": "error", "error_info": "e2"}])
    for i, job in enumerate(jobs):
        job.update(test_upload_rows[i])
        job["id"] = job.pop("job_id")
        job["meta"] = job["job_meta"]
        del job["job_meta"]

    assert list(response.json()) == ["jobs"]
    for response_job, expected_job in zip(response.json()["jobs"], jobs):
        assert response_job == expected_job

    mocked_get_jobs.assert_called_once_with(
        con=mocked_asyncpg_con, user_id=str(test_user_id), job_ids=expected_job_ids
    )
    if download:
        mocked_generate.assert_called_once_with(
            main.PULSE3D_UPLOADS_BUCKET, test_upload_rows[0]["object_key"]
        )
    else:
        mocked_generate.assert_not_called()


def test_jobs__get__error_with_creating_presigned_url_for_single_file(mocked_asyncpg_con, mocker):
    test_num_jobs = 3
    test_job_ids = [uuid.uuid4() for _ in range(test_num_jobs)]
    expected_job_ids = [str(test_id) for test_id in test_job_ids]
    # use job_ids as upload_ids to make testing easier
    test_upload_rows = [
        {
            "status": "finished",
            "job_id": f"upload{i}",
            "upload_id": str(job_id),
            "created_at": i,
            "job_meta": json.dumps({"error": f"e{i}"}),
            "object_key": f"obj{i}",
        }
        for i, job_id in enumerate(test_job_ids)
    ]

    mocked_get_jobs = mocker.patch.object(main, "get_jobs", autospec=True, return_value=test_upload_rows)
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
        job.update(test_upload_rows[i])
        job["id"] = job.pop("job_id")
        job["meta"] = job["job_meta"]
        del job["job_meta"]

    assert list(response.json()) == ["jobs"]
    for response_job, expected_job in zip(response.json()["jobs"], jobs):
        assert response_job == expected_job

    mocked_get_jobs.assert_called_once_with(
        con=mocked_asyncpg_con, user_id=str(test_user_id), job_ids=expected_job_ids
    )
    assert mocked_generate.call_args_list == [
        mocker.call(main.PULSE3D_UPLOADS_BUCKET, test_upload_rows[i]["object_key"])
        for i in range(test_num_jobs)
    ]


@pytest.mark.parametrize("test_job_ids", [None, []])
def test_jobs__get__no_jobs_found(test_job_ids, mocked_asyncpg_con, mocker):
    # falsey query params are automatically converted to None
    expected_job_ids = None
    test_upload_rows = []

    mocked_get_jobs = mocker.patch.object(main, "get_jobs", autospec=True, return_value=test_upload_rows)
    mocked_get_uploads = mocker.patch.object(main, "get_uploads", autospec=True)

    test_user_id = uuid.uuid4()
    access_token = get_token(scope=["users:free"], userid=test_user_id)

    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}}
    # in None case, don't even pass a query param
    if test_job_ids is not None:
        kwargs["params"] = {"job_ids": test_job_ids}

    response = test_client.get("/jobs", **kwargs)
    assert response.status_code == 200
    assert response.json() == {"error": "No jobs found", "jobs": []}

    mocked_get_jobs.assert_called_once_with(
        con=mocked_asyncpg_con, user_id=str(test_user_id), job_ids=expected_job_ids
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
        for param in ("prominence_factors", "width_factors", "twitch_widths", "start_time", "end_time")
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
        for param in ("prominence_factors", "width_factors", "twitch_widths", "start_time", "end_time")
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
        for param in ("prominence_factors", "width_factors", "twitch_widths", "start_time", "end_time")
    }
    expected_analysis_params.update({param_name: format_mapping[param_tuple]})

    mocked_create_job.assert_called_once()
    assert mocked_create_job.call_args[1]["meta"]["analysis_params"] == expected_analysis_params


@pytest.mark.parametrize("test_job_ids", [uuid.uuid4(), [uuid.uuid4()], [uuid.uuid4() for _ in range(3)]])
def test_jobs__delete(test_job_ids, mocked_asyncpg_con, mocker):
    if isinstance(test_job_ids, uuid.UUID):
        # fastapi automatically converts a single UUID to a list
        test_job_ids = [test_job_ids]

    expected_job_ids = [str(test_id) for test_id in test_job_ids]

    mocked_delete_jobs = mocker.patch.object(main, "delete_jobs", autospec=True)

    test_account_id = uuid.uuid4()
    access_token = get_token(scope=["users:free"], userid=test_account_id)
    kwargs = {
        "headers": {"Authorization": f"Bearer {access_token}"},
        "params": {"job_ids": test_job_ids},
    }

    response = test_client.delete("/jobs", **kwargs)
    assert response.status_code == 200

    mocked_delete_jobs.assert_called_once_with(
        con=mocked_asyncpg_con, account_id=str(test_account_id), job_ids=expected_job_ids
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
