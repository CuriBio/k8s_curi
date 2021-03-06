from fastapi.testclient import TestClient
import json
import uuid

import pytest

from auth import create_token
from src import main

test_client = TestClient(main.app)

# TODO add tests for other routes


def get_token(scope, userid=None, customer_id=None, refresh=False):
    if not userid:
        userid = uuid.uuid4()
    if not customer_id:
        customer_id = uuid.uuid4()
    return create_token(
        userid=userid, customer_id=customer_id, scope=scope, account_type="user", refresh=refresh
    ).token


@pytest.fixture(scope="function", name="mocked_asyncpg_con", autouse=True)
async def fixture_mocked_asyncpg_con(mocker):
    mocked_asyncpg_pool = mocker.patch.object(main, "asyncpg_pool", autospec=True)

    mocked_asyncpg_pool_coroutine = mocker.AsyncMock()
    mocked_asyncpg_pool_coroutine.return_value = mocker.MagicMock()
    mocked_asyncpg_pool.return_value = mocked_asyncpg_pool_coroutine()

    mocked_asyncpg_con = await mocked_asyncpg_pool_coroutine.return_value.acquire().__aenter__()
    yield mocked_asyncpg_con


@pytest.mark.parametrize(
    "test_upload_ids", (None, [], uuid.uuid4(), [uuid.uuid4()], [uuid.uuid4() for _ in range(3)])
)
def test_uploads__get(test_upload_ids, mocked_asyncpg_con, mocker):
    mocked_get_uploads = mocker.patch.object(main, "get_uploads", autospec=True, return_value=[])

    test_user_id = uuid.uuid4()
    access_token = get_token(scope=["users:free"], userid=test_user_id)

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
        con=mocked_asyncpg_con, user_id=str(test_user_id), upload_ids=expected_upload_ids
    )


@pytest.mark.parametrize("download", [True, False])
@pytest.mark.parametrize("test_job_ids", (uuid.uuid4(), [uuid.uuid4()], [uuid.uuid4() for _ in range(3)]))
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


@pytest.mark.parametrize("test_job_ids", (None, []))
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
