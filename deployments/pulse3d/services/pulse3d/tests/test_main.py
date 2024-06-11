from random import randint
from fastapi.testclient import TestClient
import json
import os
import uuid
import pandas as pd
import pytest
from semver import VersionInfo
from auth import create_token, decode_token, Scopes, ScopeTags, AccountTypes
from utils.s3 import S3Error
from src import main
import numpy as np
import tempfile

from pulse3D.constants import DataTypes
from pulse3D.rendering.utils import get_metric_display_title
from pulse3D.metrics.constants import TwitchMetrics
from labware_domain_models import LabwareDefinition
from src.models.models import GenericErrorResponse, WaveformDataResponse

TWENTY_FOUR_WELL_PLATE = LabwareDefinition(row_count=4, column_count=6)
DEFAULT_BASELINE_WIDTHS = (10, 90)
DEFAULT_PROMINENCE_FACTORS = (6, 6)
DEFAULT_WIDTH_FACTORS = (7, 7)

test_client = TestClient(main.app)

P3D_READ_SCOPES = [s for s in Scopes if ScopeTags.PULSE3D_READ in s.tags]
P3D_WRITE_SCOPES = [s for s in Scopes if ScopeTags.PULSE3D_WRITE in s.tags]


def random_semver(*, max_version="99.99.99"):
    version_components = max_version.split(".")
    if len(version_components) > 3:
        raise ValueError("max_version can only contain a major, minor, and patch version")

    return ".".join([str(randint(0, int(max))) for max in version_components])


def create_test_df(include_raw_data: bool = True):
    data = {}

    if include_raw_data:
        test_df_data = [1e4 * i for i in range(10)]
    else:
        test_df_data = [i for i in range(10)]

    data["Time (s)"] = pd.Series(test_df_data)

    for well_idx in range(24):
        well_name = TWENTY_FOUR_WELL_PLATE.get_well_name_from_well_index(well_idx)
        data[well_name] = pd.Series(test_df_data)
        if include_raw_data:
            data[f"{well_name}__raw"] = pd.Series(test_df_data)

    return pd.DataFrame(data)


def get_token(scopes, account_type=AccountTypes.USER, userid=None, customer_id=None):
    if not userid and account_type == AccountTypes.USER:
        userid = uuid.uuid4()
    if not customer_id:
        customer_id = uuid.uuid4()
    return create_token(
        userid=userid, customer_id=customer_id, scopes=scopes, account_type=account_type, refresh=False
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

    access_token = get_token(
        scopes=[Scopes.MANTARRAY__BASE], customer_id=test_customer_id, userid=test_user_id
    )
    kwargs = {
        "headers": {"Authorization": f"Bearer {access_token}"},
        "json": {"filename": test_file_name, "upload_type": "logs"},
    }
    response = test_client.post("/logs", **kwargs)
    assert response.status_code == 200

    mocked_gpp.assert_called_once_with(
        bucket=main.MANTARRAY_LOGS_BUCKET,
        key=f"{test_customer_id}/{test_user_id}/{test_file_name}",
        md5s=None,
    )


@pytest.mark.parametrize("test_token_scope", [s for s in P3D_READ_SCOPES])
def test_uploads__get(test_token_scope, mocked_asyncpg_con, mocker):
    mocked_get_uploads = mocker.patch.object(main, "get_uploads", autospec=True, return_value=[])

    account_type = AccountTypes.ADMIN if ScopeTags.ADMIN in test_token_scope.tags else AccountTypes.USER
    is_admin_account = account_type == AccountTypes.ADMIN

    test_customer_id = uuid.uuid4()
    test_user_id = None if is_admin_account else uuid.uuid4()

    access_token = get_token(
        scopes=[test_token_scope],
        account_type=account_type,
        userid=test_user_id,
        customer_id=test_customer_id,
    )

    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}}

    response = test_client.get("/uploads?name_filter=test", **kwargs)
    assert response.status_code == 200
    assert response.json() == mocked_get_uploads.return_value


def test_uploads__post_if_customer_quota_has_not_been_reached(mocked_asyncpg_con, mocker):
    mocker.patch.object(
        main,
        "check_customer_quota",
        return_value={
            "current": {"uploads": "0", "jobs": "0"},
            "jobs_reached": False,
            "limits": {"expiration_date": "", "jobs": "-1", "uploads": "-1"},
            "uploads_reached": False,
        },
        autospec=True,
    )
    mocked_asyncpg_con.transaction = mocker.MagicMock()

    expected_upload_id = uuid.uuid4()
    mocker.patch.object(uuid, "uuid4", autospec=True, return_value=expected_upload_id)
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

    access_token = get_token(
        scopes=[Scopes.MANTARRAY__BASE], customer_id=test_customer_id, userid=test_user_id
    )
    kwargs = {
        "headers": {"Authorization": f"Bearer {access_token}"},
        "json": {"filename": test_file_name, "md5s": test_md5s, "upload_type": test_upload_type},
    }
    response = test_client.post("/uploads", **kwargs)
    assert response.status_code == 200

    expected_upload_params = {
        "prefix": f"uploads/{test_customer_id}/{test_user_id}/{expected_upload_id}",
        "filename": test_file_name,
        "md5": test_md5s,
        "user_id": str(test_user_id),
        "type": test_upload_type,
        "customer_id": str(test_customer_id),
        "auto_upload": True,
        "upload_id": expected_upload_id,
    }

    mocked_create_upload.assert_called_once_with(con=mocked_asyncpg_con, upload_params=expected_upload_params)
    mocked_gpp.assert_called_once_with(
        bucket=main.PULSE3D_UPLOADS_BUCKET,
        key=f"uploads/{test_customer_id}/{test_user_id}/{expected_upload_id}/{test_file_name}",
        md5s=test_md5s,
    )


@pytest.mark.parametrize(
    "usage_dict",
    [{"jobs_reached": False, "uploads_reached": True}, {"jobs_reached": True, "uploads_reached": True}],
)
def test_uploads__post_if_customer_quota_has_been_reached(mocked_asyncpg_con, mocker, usage_dict):
    test_user_id = uuid.uuid4()
    mocked_usage_check = mocker.patch.object(
        main, "check_customer_quota", return_value=usage_dict, autospec=True
    )

    mocked_create_upload = mocker.spy(main, "create_upload")

    test_file_name = "recording_file"
    test_md5s = "testhash"
    test_upload_type = "mantarray"
    test_customer_id = uuid.uuid4()

    access_token = get_token(
        scopes=[Scopes.MANTARRAY__BASE], customer_id=test_customer_id, userid=test_user_id
    )
    kwargs = {
        "headers": {"Authorization": f"Bearer {access_token}"},
        "json": {"filename": test_file_name, "md5s": test_md5s, "upload_type": test_upload_type},
    }

    response = test_client.post("/uploads", **kwargs)
    assert response.status_code == 200
    assert (
        response.json()
        == GenericErrorResponse(message=mocked_usage_check.return_value, error="UsageError").model_dump()
    )
    mocked_create_upload.assert_not_called()


@pytest.mark.parametrize("test_token_scope", [[s] for s in P3D_READ_SCOPES])
@pytest.mark.parametrize("test_upload_ids", [uuid.uuid4(), [uuid.uuid4()], [uuid.uuid4() for _ in range(3)]])
def test_uploads__delete(test_token_scope, test_upload_ids, mocked_asyncpg_con, mocker):
    mocked_delete_uploads = mocker.patch.object(main, "delete_uploads", autospec=True)

    account_type = AccountTypes.ADMIN if ScopeTags.ADMIN in test_token_scope[0].tags else AccountTypes.USER

    test_account_id = uuid.uuid4()

    is_admin_account = account_type == AccountTypes.ADMIN
    test_customer_id = test_account_id if is_admin_account else uuid.uuid4()

    access_token = get_token(
        scopes=test_token_scope,
        account_type=account_type,
        userid=None if is_admin_account else test_account_id,
        customer_id=test_customer_id,
    )

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

    access_token = get_token(scopes=[Scopes.MANTARRAY__BASE])
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
    access_token = get_token(scopes=[Scopes.MANTARRAY__BASE], userid=test_user_id)
    kwargs = {
        "headers": {"Authorization": f"Bearer {access_token}"},
        "params": {"upload_ids": [uuid.uuid4()]},
    }

    response = test_client.delete("/uploads", **kwargs)
    assert response.status_code == 500


@pytest.mark.parametrize("download", [True, False, None])
@pytest.mark.parametrize("test_token_scope", [[s] for s in P3D_READ_SCOPES])
@pytest.mark.parametrize(
    "test_job_ids", [None, [], uuid.uuid4(), [uuid.uuid4()], [uuid.uuid4() for _ in range(3)]]
)
def test_jobs__get__jobs_found(download, test_token_scope, test_job_ids, mocked_asyncpg_con, mocker):
    account_type = AccountTypes.ADMIN if ScopeTags.ADMIN in test_token_scope[0].tags else AccountTypes.USER
    is_admin_account = account_type == AccountTypes.ADMIN

    test_account_id = uuid.uuid4()
    test_customer_id = test_account_id if is_admin_account else uuid.uuid4()

    access_token = get_token(
        scopes=test_token_scope,
        account_type=account_type,
        userid=None if is_admin_account else test_account_id,
        customer_id=test_customer_id,
    )

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
            "user_id": test_account_id,
        }
        for i, (status, job_id) in enumerate(zip(test_statuses, expected_job_ids))
    ]

    mocked_get_jobs = mocker.patch.object(main, "get_jobs", autospec=True, return_value=test_job_rows)
    mocked_generate = mocker.patch.object(main, "generate_presigned_url", autospec=True, return_value="url0")

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
        job.pop("user_id")

    # if all jobs are retrieved successfully, this should be the only key in the response dict
    assert list(response.json()) == ["jobs"]

    for response_job, expected_job in zip(response.json()["jobs"], jobs):
        assert response_job == expected_job
    # this changes after token creation

    if Scopes.MANTARRAY__RW_ALL_DATA in test_token_scope:
        account_type = "rw_all_user"
        test_account_id = test_customer_id

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
    test_user_id = uuid.uuid4()
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
            "user_id": test_user_id,
        }
        for i, job_id in enumerate(test_job_ids)
    ]

    mocked_get_jobs = mocker.patch.object(main, "get_jobs", autospec=True, return_value=test_job_rows)
    mocked_generate = mocker.patch.object(
        main, "generate_presigned_url", autospec=True, side_effect=["url0", Exception(), "url2"]
    )

    access_token = get_token(scopes=[Scopes.MANTARRAY__BASE], userid=test_user_id)

    kwargs = {
        "headers": {"Authorization": f"Bearer {access_token}"},
        "params": {"job_ids": test_job_ids, "download": True},
    }
    response = test_client.get("/jobs", **kwargs)
    assert response.status_code == 200

    jobs = [{"url": "url0"}, {"url": "Error creating download link"}, {"url": "url2"}]
    for i, job in enumerate(jobs):
        job.update(test_job_rows[i])
        # rename keys
        job["id"] = job.pop("job_id")
        job["meta"] = job.pop("job_meta")
        job.pop("user_id")

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
    access_token = get_token(scopes=[Scopes.MANTARRAY__BASE], userid=test_user_id)

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
    test_customer_id = uuid.uuid4()
    test_version = random_semver(max_version="0.24.0")

    access_token = get_token(
        scopes=[Scopes.MANTARRAY__BASE], userid=test_user_id, customer_id=test_customer_id
    )
    mocked_asyncpg_con.fetchrow.return_value = {
        "user_id": test_user_id,
        "state": "external",
        "type": "mantarray",
        "end_of_life_date": None,
    }

    mocked_create_job = mocker.patch.object(main, "create_job", autospec=True, return_value=expected_job_id)
    mocker.patch.object(
        main,
        "check_customer_quota",
        return_value={
            "current": {"uploads": "0", "jobs": "0"},
            "jobs_reached": False,
            "limits": {"expiration_date": "", "jobs": "-1", "uploads": "-1"},
            "uploads_reached": False,
        },
        autospec=True,
    )
    kwargs = {
        "json": {"upload_id": str(test_upload_id), "version": test_version},
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
        "usage_quota": {
            "current": {"uploads": "0", "jobs": "0"},
            "jobs_reached": False,
            "limits": {"expiration_date": "", "jobs": "-1", "uploads": "-1"},
            "uploads_reached": False,
        },
    }

    expected_analysis_params = {
        param: None
        for param in (
            "baseline_widths_to_use",
            "prominence_factors",
            "width_factors",
            "twitch_widths",
            "start_time",
            "end_time",
            "include_stim_protocols",
            "max_y",
            "normalize_y_axis",
        )
    }

    mocked_create_job.assert_called_once_with(
        con=mocked_asyncpg_con,
        upload_id=test_upload_id,
        queue=f"pulse3d-v{test_version}",
        priority=expected_job_priority,
        meta={"analysis_params": expected_analysis_params, "version": test_version},
        customer_id=str(test_customer_id),
        job_type="mantarray",
    )


@pytest.mark.parametrize("test_token_scope", [[s] for s in [Scopes.MANTARRAY__BASE, Scopes.MANTARRAY__BASE]])
def test_jobs__post__returns_unauthorized_error_if_user_ids_dont_match(mocked_asyncpg_con, test_token_scope):
    test_upload_id = uuid.uuid4()
    test_user_id = uuid.uuid4()
    diff_user_id = uuid.uuid4()
    test_customer_id = uuid.uuid4()
    test_version = random_semver(max_version="0.24.0")

    access_token = get_token(scopes=test_token_scope, userid=test_user_id, customer_id=test_customer_id)
    mocked_asyncpg_con.fetchrow.return_value = {
        "user_id": diff_user_id,
        "state": "external",
        "type": "mantarray",
        "end_of_life_date": None,
    }

    kwargs = {
        "json": {"upload_id": str(test_upload_id), "version": test_version},
        "headers": {"Authorization": f"Bearer {access_token}"},
    }
    response = test_client.post("/jobs", **kwargs)
    assert response.status_code == 200
    assert (
        response.json()
        == GenericErrorResponse(
            message="User does not have authorization to start this job.", error="AuthorizationError"
        ).model_dump()
    )


def test_jobs__post__basic_params_given(mocker, mocked_asyncpg_con):
    test_analysis_params = {"twitch_widths": [10, 20], "start_time": 0, "end_time": 1}
    test_user_id = uuid.uuid4()

    access_token = get_token(scopes=[Scopes.MANTARRAY__BASE], userid=test_user_id, account_type="user")
    mocked_create_job = mocker.patch.object(main, "create_job", autospec=True, return_value=uuid.uuid4())
    mocked_asyncpg_con.fetchrow.return_value = {
        "user_id": test_user_id,
        "state": "external",
        "type": "mantarray",
        "end_of_life_date": None,
    }
    mocker.patch.object(
        main,
        "check_customer_quota",
        return_value={
            "current": {"uploads": "0", "jobs": "0"},
            "jobs_reached": False,
            "limits": {"expiration_date": "", "jobs": "-1", "uploads": "-1"},
            "uploads_reached": False,
        },
        autospec=True,
    )

    kwargs = {
        "json": {
            "upload_id": str(uuid.uuid4()),
            "version": random_semver(max_version="0.24.0"),
            **test_analysis_params,
        },
        "headers": {"Authorization": f"Bearer {access_token}"},
    }
    response = test_client.post("/jobs", **kwargs)
    assert response.status_code == 200

    expected_analysis_params = {
        param: None
        for param in (
            "baseline_widths_to_use",
            "prominence_factors",
            "width_factors",
            "twitch_widths",
            "start_time",
            "end_time",
            "include_stim_protocols",
            "max_y",
            "normalize_y_axis",
        )
    }
    expected_analysis_params.update(test_analysis_params)

    mocked_create_job.assert_called_once()
    assert mocked_create_job.call_args[1]["meta"]["analysis_params"] == expected_analysis_params


def test_jobs__post__uploads_peaks_and_valleys_when_passed_into_request(mocker, mocked_asyncpg_con):
    test_peaks_valleys = dict()
    random_list = [int(x) for x in np.random.randint(low=0, high=100, size=5)]
    for x in range(24):
        test_peaks_valleys[TWENTY_FOUR_WELL_PLATE.get_well_name_from_well_index(x)] = [
            random_list,
            random_list,
        ]

    test_analysis_params = {
        "twitch_widths": [10, 20],
        "start_time": 0,
        "end_time": 1,
        "peaks_valleys": test_peaks_valleys,
    }
    test_user_id = uuid.uuid4()
    test_customer_id = uuid.uuid4()
    test_upload_id = uuid.uuid4()

    access_token = get_token(
        scopes=[Scopes.MANTARRAY__BASE],
        userid=test_user_id,
        account_type="user",
        customer_id=test_customer_id,
    )
    mocked_create_job = mocker.patch.object(main, "create_job", autospec=True, return_value=uuid.uuid4())
    mocked_upload_to_s3 = mocker.patch.object(main, "upload_file_to_s3", autospec=True)
    mocked_asyncpg_con.fetchrow.return_value = {
        "user_id": test_user_id,
        "state": "external",
        "type": "mantarray",
        "end_of_life_date": None,
    }
    spied_tempdir = mocker.spy(tempfile, "TemporaryDirectory")
    mocker.patch.object(
        main,
        "check_customer_quota",
        return_value={
            "current": {"uploads": "0", "jobs": "0"},
            "jobs_reached": False,
            "limits": {"expiration_date": "", "jobs": "-1", "uploads": "-1"},
            "uploads_reached": False,
        },
        autospec=True,
    )

    kwargs = {
        "json": {"upload_id": str(test_upload_id), "version": "0.28.2", **test_analysis_params},
        "headers": {"Authorization": f"Bearer {access_token}"},
    }

    response = test_client.post("/jobs", **kwargs)
    assert response.status_code == 200

    mocked_create_job.assert_called_once()

    expected_s3_key = f"uploads/{test_customer_id}/{test_user_id}/{test_upload_id}/{mocked_create_job.return_value}/peaks_valleys.parquet"
    expected_parquet_path = os.path.join(spied_tempdir.spy_return.name, "peaks_valleys.parquet")

    mocked_upload_to_s3.assert_called_once_with(
        bucket="test-pulse3d-uploads", key=expected_s3_key, file=expected_parquet_path
    )


@pytest.mark.parametrize(
    "usage_dict",
    [{"jobs_reached": True, "uploads_reached": True}, {"jobs_reached": True, "uploads_reached": False}],
)
def test_jobs__post__returns_error_dict_if_quota_has_been_reached(mocker, mocked_asyncpg_con, usage_dict):
    test_user_id = uuid.uuid4()
    mocked_usage_check = mocker.patch.object(
        main, "check_customer_quota", return_value=usage_dict, autospec=True
    )
    mocked_asyncpg_con.fetchrow.return_value = {
        "user_id": test_user_id,
        "state": "external",
        "type": "mantarray",
        "end_of_life_date": None,
    }

    test_analysis_params = {"twitch_widths": [10, 20], "start_time": 0, "end_time": 1}
    access_token = get_token(scopes=[Scopes.MANTARRAY__BASE], userid=test_user_id, account_type="user")
    spied_create_job = mocker.spy(main, "create_job")

    kwargs = {
        "json": {
            "upload_id": str(uuid.uuid4()),
            "version": random_semver(max_version="0.24.0"),
            **test_analysis_params,
        },
        "headers": {"Authorization": f"Bearer {access_token}"},
    }
    response = test_client.post("/jobs", **kwargs)
    assert response.status_code == 200
    assert (
        response.json()
        == GenericErrorResponse(message=mocked_usage_check.return_value, error="UsageError").model_dump()
    )
    spied_create_job.assert_not_called()


@pytest.mark.parametrize("param_name", ["prominence_factors", "width_factors"])
@pytest.mark.parametrize("param_tuple", [(1, 2), (None, 2), (1, None), (None, None)])
def test_jobs__post__advanced_params_given(param_name, mocked_asyncpg_con, param_tuple, mocker):
    test_analysis_params = {param_name: param_tuple}
    test_user_id = uuid.uuid4()
    access_token = get_token(scopes=[Scopes.MANTARRAY__BASE], userid=test_user_id)
    mocked_create_job = mocker.patch.object(main, "create_job", autospec=True, return_value=uuid.uuid4())
    mocker.patch.object(
        main,
        "check_customer_quota",
        return_value={
            "current": {"uploads": "0", "jobs": "0"},
            "jobs_reached": False,
            "limits": {"expiration_date": "", "jobs": "-1", "uploads": "-1"},
            "uploads_reached": False,
        },
        autospec=True,
    )
    mocked_asyncpg_con.fetchrow.return_value = {
        "user_id": test_user_id,
        "state": "external",
        "type": "mantarray",
        "end_of_life_date": None,
    }

    kwargs = {
        "json": {
            "upload_id": str(uuid.uuid4()),
            "version": random_semver(max_version="0.24.0"),
            **test_analysis_params,
        },
        "headers": {"Authorization": f"Bearer {access_token}"},
    }
    response = test_client.post("/jobs", **kwargs)
    assert response.status_code == 200

    expected_default_value_tuple = (
        DEFAULT_PROMINENCE_FACTORS if param_name == "prominence_factors" else DEFAULT_WIDTH_FACTORS
    )
    format_mapping = {
        (1, 2): (1, 2),
        (None, 2): (expected_default_value_tuple[0], 2),
        (1, None): (1, expected_default_value_tuple[1]),
        (None, None): None,
    }

    expected_analysis_params = {
        param: None
        for param in (
            "baseline_widths_to_use",
            "prominence_factors",
            "width_factors",
            "twitch_widths",
            "start_time",
            "end_time",
            "include_stim_protocols",
            "max_y",
            "normalize_y_axis",
        )
    }
    expected_analysis_params.update({param_name: format_mapping[param_tuple]})

    mocked_create_job.assert_called_once()
    assert mocked_create_job.call_args[1]["meta"]["analysis_params"] == expected_analysis_params


@pytest.mark.parametrize("param_tuple", [(1, 2), (None, 2), (1, None), (None, None)])
def test_jobs__post__with_baseline_widths_to_use(param_tuple, mocked_asyncpg_con, mocker):
    mocker.patch.object(
        main,
        "check_customer_quota",
        return_value={
            "current": {"uploads": "0", "jobs": "0"},
            "jobs_reached": False,
            "limits": {"expiration_date": "", "jobs": "-1", "uploads": "-1"},
            "uploads_reached": False,
        },
        autospec=True,
    )
    test_user_id = uuid.uuid4()
    mocked_asyncpg_con.fetchrow.return_value = {
        "user_id": test_user_id,
        "state": "external",
        "type": "mantarray",
        "end_of_life_date": None,
    }
    test_analysis_params = {"baseline_widths_to_use": param_tuple}
    access_token = get_token(scopes=[Scopes.MANTARRAY__BASE], userid=test_user_id)
    mocked_create_job = mocker.patch.object(main, "create_job", autospec=True, return_value=uuid.uuid4())
    kwargs = {
        "json": {
            "upload_id": str(uuid.uuid4()),
            "version": random_semver(max_version="0.24.0"),
            **test_analysis_params,
        },
        "headers": {"Authorization": f"Bearer {access_token}"},
    }
    response = test_client.post("/jobs", **kwargs)
    assert response.status_code == 200

    format_mapping = {
        (1, 2): (1, 2),
        (None, 2): (DEFAULT_BASELINE_WIDTHS[0], 2),
        (1, None): (1, DEFAULT_BASELINE_WIDTHS[1]),
        (None, None): None,
    }

    expected_analysis_params = {
        param: None
        for param in (
            "baseline_widths_to_use",
            "prominence_factors",
            "width_factors",
            "twitch_widths",
            "start_time",
            "end_time",
            "include_stim_protocols",
            "max_y",
            "normalize_y_axis",
        )
    }

    expected_analysis_params.update({"baseline_widths_to_use": format_mapping[param_tuple]})

    mocked_create_job.assert_called_once()
    assert mocked_create_job.call_args[1]["meta"]["analysis_params"] == expected_analysis_params


# Tanner (3/13/23): only really need to test versions that are live in prod or are being tested in test cluster
@pytest.mark.parametrize("version", ["0.28.3", "0.30.4", "0.33.7", "0.34.2"])
def test_jobs__post__omits_analysis_params_not_supported_by_the_selected_pulse3d_version(
    version, mocked_asyncpg_con, mocker
):
    test_user_id = uuid.uuid4()
    access_token = get_token(scopes=[Scopes.MANTARRAY__BASE], userid=test_user_id)
    mocked_create_job = mocker.patch.object(main, "create_job", autospec=True, return_value=uuid.uuid4())
    mocked_asyncpg_con.fetchrow.return_value = {
        "user_id": test_user_id,
        "type": "mantarray",
        "state": "external",
        "end_of_life_date": None,
    }
    mocker.patch.object(
        main,
        "check_customer_quota",
        return_value={
            "current": {"uploads": "0", "jobs": "0"},
            "jobs_reached": False,
            "limits": {"expiration_date": "", "jobs": "-1", "uploads": "-1"},
            "uploads_reached": False,
        },
        autospec=True,
    )
    kwargs = {
        "json": {"upload_id": str(uuid.uuid4()), "version": version},
        "headers": {"Authorization": f"Bearer {access_token}"},
    }
    response = test_client.post("/jobs", **kwargs)
    assert response.status_code == 200, response.json()

    expected_analysis_param_keys = [
        "baseline_widths_to_use",
        "width_factors",
        "twitch_widths",
        "start_time",
        "end_time",
        "max_y",
        "normalize_y_axis",
        "include_stim_protocols",
    ]

    pulse3d_semver = VersionInfo.parse(version)
    if pulse3d_semver >= "0.30.1":
        expected_analysis_param_keys.append("stiffness_factor")
        expected_analysis_param_keys.append("inverted_post_magnet_wells")
    if pulse3d_semver >= "0.30.3":
        expected_analysis_param_keys.append("well_groups")
    if pulse3d_semver >= "0.30.5":
        expected_analysis_param_keys.append("stim_waveform_format")
    if pulse3d_semver < "0.33.7":
        expected_analysis_param_keys.append("prominence_factors")
    if pulse3d_semver >= "0.33.7":
        for param in (
            "upslope_noise_allowance_duration",
            "height_factor",
            "relative_prominence_factor",
            "noise_prominence_factor",
            "max_frequency",
            "valley_search_duration",
            "upslope_duration",
        ):
            expected_analysis_param_keys.append(param)
    if pulse3d_semver >= "0.34.2":
        expected_analysis_param_keys.append("data_type")

    expected_analysis_params = {param: None for param in expected_analysis_param_keys}

    mocked_create_job.assert_called_once()
    assert mocked_create_job.call_args[1]["meta"]["analysis_params"] == expected_analysis_params


@pytest.mark.parametrize("test_token_scope", [[s] for s in P3D_READ_SCOPES])
@pytest.mark.parametrize("test_job_ids", [uuid.uuid4(), [uuid.uuid4()], [uuid.uuid4() for _ in range(3)]])
def test_jobs__delete(test_token_scope, test_job_ids, mocked_asyncpg_con, mocker):
    mocked_delete_jobs = mocker.patch.object(main, "delete_jobs", autospec=True)

    account_type = AccountTypes.ADMIN if ScopeTags.ADMIN in test_token_scope[0].tags else AccountTypes.USER
    test_account_id = uuid.uuid4()

    is_admin_account = account_type == AccountTypes.ADMIN
    test_customer_id = test_account_id if is_admin_account else uuid.uuid4()

    access_token = get_token(
        scopes=test_token_scope,
        account_type=account_type,
        userid=None if is_admin_account else test_account_id,
        customer_id=test_customer_id,
    )

    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}, "params": {"job_ids": test_job_ids}}
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
    access_token = get_token(scopes=[Scopes.MANTARRAY__BASE], userid=test_user_id)
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
    access_token = get_token(scopes=[Scopes.MANTARRAY__BASE], userid=test_user_id)
    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}, "params": {"job_ids": [uuid.uuid4()]}}

    response = test_client.delete("/jobs", **kwargs)
    assert response.status_code == 500


@pytest.mark.parametrize("test_token_scope", [[s] for s in P3D_READ_SCOPES])
@pytest.mark.parametrize("test_job_ids", [[uuid.uuid4() for _ in range(r)] for r in range(1, 4)])
def test_jobs_download__post__no_duplicate_analysis_file_names(
    test_token_scope, test_job_ids, mocked_asyncpg_con, mocker
):
    account_type = AccountTypes.ADMIN if ScopeTags.ADMIN in test_token_scope[0].tags else AccountTypes.USER

    test_account_id = uuid.uuid4()

    is_admin_account = account_type == AccountTypes.ADMIN
    test_customer_id = test_account_id if is_admin_account else uuid.uuid4()

    access_token = get_token(
        scopes=test_token_scope,
        account_type=account_type,
        userid=None if is_admin_account else test_account_id,
        customer_id=test_customer_id,
    )

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

    if Scopes.MANTARRAY__RW_ALL_DATA in test_token_scope:
        account_type = "rw_all_user"
        test_account_id = test_customer_id

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


@pytest.mark.parametrize("test_token_scope", [[s] for s in P3D_READ_SCOPES])
def test_jobs_download__post__duplicate_analysis_file_names(mocked_asyncpg_con, test_token_scope, mocker):
    account_type = AccountTypes.ADMIN if ScopeTags.ADMIN in test_token_scope[0].tags else AccountTypes.USER

    test_account_id = uuid.uuid4()

    is_admin_account = account_type == AccountTypes.ADMIN
    test_customer_id = test_account_id if is_admin_account else uuid.uuid4()

    access_token = get_token(
        scopes=test_token_scope,
        account_type=account_type,
        userid=None if is_admin_account else test_account_id,
        customer_id=test_customer_id,
    )

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

    if Scopes.MANTARRAY__RW_ALL_DATA in test_token_scope:
        account_type = "rw_all_user"
        test_account_id = test_customer_id

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
def test_jobs_download__post__no_job_ids_given(test_job_ids, test_error_code, mocker):
    mocked_get_jobs = mocker.patch.object(main, "get_jobs", autospec=True)
    mocked_yield_objs = mocker.patch.object(main, "_yield_s3_objects", autospec=True)

    access_token = get_token(scopes=[Scopes.MANTARRAY__BASE])

    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}}
    # in None case, don't even pass a param
    if test_job_ids is not None:
        kwargs["json"] = {"job_ids": test_job_ids}

    response = test_client.post("/jobs/download", **kwargs)
    assert response.status_code == test_error_code

    mocked_get_jobs.assert_not_called()
    mocked_yield_objs.assert_not_called()


@pytest.mark.parametrize("test_upload_ids,test_error_code", [(None, 422), ([], 400)])
def test_uploads_download__post__no_job_ids_given(test_upload_ids, test_error_code, mocker):
    mocked_get_uploads = mocker.patch.object(main, "get_uploads", autospec=True)
    mocked_yield_objs = mocker.patch.object(main, "_yield_s3_objects", autospec=True)

    access_token = get_token(scopes=[Scopes.MANTARRAY__BASE])

    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}}
    # in None case, don't even pass a param
    if test_upload_ids is not None:
        kwargs["json"] = {"upload_ids": test_upload_ids}

    response = test_client.post("/uploads/download", **kwargs)
    assert response.status_code == test_error_code

    mocked_get_uploads.assert_not_called()
    mocked_yield_objs.assert_not_called()


@pytest.mark.parametrize("test_token_scope", [[s] for s in P3D_READ_SCOPES])
def test_uploads_download__post__correctly_handles_single_file_downloads(
    test_token_scope, mocked_asyncpg_con, mocker
):
    test_upload_ids = [uuid.uuid4()]
    account_type = AccountTypes.ADMIN if ScopeTags.ADMIN in test_token_scope[0].tags else AccountTypes.USER

    test_account_id = uuid.uuid4()
    is_admin_account = account_type == AccountTypes.ADMIN
    test_customer_id = test_account_id if is_admin_account else uuid.uuid4()

    access_token = get_token(
        scopes=test_token_scope,
        account_type=account_type,
        userid=None if is_admin_account else test_account_id,
        customer_id=test_customer_id,
    )

    test_presigned_url = "https://s3.test-url.com/"
    test_upload_rows = [
        {"filename": f"file_{upload}zip", "prefix": "/obj/prefix/"} for upload in test_upload_ids
    ]

    mocked_get_uploads = mocker.patch.object(
        main, "get_uploads", autospec=True, return_value=test_upload_rows
    )
    mocked_yield_objs = mocker.patch.object(main, "_yield_s3_objects", autospec=True)
    mocked_presigned_url = mocker.patch.object(
        main, "generate_presigned_url", return_value=test_presigned_url, autospec=True
    )

    test_upload_ids_strs = [str(id) for id in test_upload_ids]

    kwargs = {
        "headers": {"Authorization": f"Bearer {access_token}"},
        "json": {"upload_ids": test_upload_ids_strs},
    }
    response = test_client.post("/uploads/download", **kwargs)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {
        "filename": mocked_get_uploads.return_value[0]["filename"],
        "url": mocked_presigned_url.return_value,
    }

    if Scopes.MANTARRAY__RW_ALL_DATA in test_token_scope:
        account_type = "rw_all_user"
        test_account_id = test_customer_id

    mocked_get_uploads.assert_called_once_with(
        con=mocked_asyncpg_con,
        account_type=account_type,
        account_id=str(test_account_id),
        upload_ids=test_upload_ids_strs,
    )

    mocked_yield_objs.assert_not_called()


@pytest.mark.parametrize("test_token_scope", [[s] for s in P3D_READ_SCOPES])
@pytest.mark.parametrize("test_upload_ids", [[uuid.uuid4() for _ in range(r)] for r in range(2, 4)])
def test_uploads_download__post__correctly_handles_multiple_file_downloads(
    test_token_scope, test_upload_ids, mocked_asyncpg_con, mocker
):
    test_account_id = uuid.uuid4()
    account_type = AccountTypes.ADMIN if ScopeTags.ADMIN in test_token_scope[0].tags else AccountTypes.USER
    access_token = get_token(
        scopes=[Scopes.MANTARRAY__BASE], account_type=account_type, userid=test_account_id
    )

    test_upload_rows = [
        {"filename": f"file_{upload}zip", "prefix": "/obj/prefix/"} for upload in test_upload_ids
    ]

    mocked_get_uploads = mocker.patch.object(
        main, "get_uploads", autospec=True, return_value=test_upload_rows
    )
    mocked_yield_objs = mocker.patch.object(main, "_yield_s3_objects", autospec=True)

    test_upload_ids_strs = [str(id) for id in test_upload_ids]

    kwargs = {
        "headers": {"Authorization": f"Bearer {access_token}"},
        "json": {"upload_ids": test_upload_ids_strs},
    }
    response = test_client.post("/uploads/download", **kwargs)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    mocked_get_uploads.assert_called_once_with(
        con=mocked_asyncpg_con,
        account_type=account_type,
        account_id=str(test_account_id),
        upload_ids=test_upload_ids_strs,
    )

    expected_keys = [upload_row["prefix"] + "/" + upload_row["filename"] for upload_row in test_upload_rows]

    mocked_yield_objs.assert_called_once_with(
        bucket="test-pulse3d-uploads",
        filenames=[os.path.basename(key) for key in expected_keys],
        keys=expected_keys,
    )


@pytest.mark.parametrize("test_query_params", [f"upload_id={uuid.uuid4()}", f"job_id={uuid.uuid4()}"])
def test_waveform_data__get__no_job_or_upload_id_is_found(mocker, test_query_params):
    access_token = get_token(scopes=[Scopes.MANTARRAY__BASE])
    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}}

    response = test_client.get(f"/jobs/waveform-data?{test_query_params}", **kwargs)

    assert response.status_code == 400


def test_waveform_data__get__getting_job_metadata_from_db_errors(mocker):
    mocker.patch.object(main, "get_jobs", autospec=True, return_value=S3Error())

    access_token = get_token(scopes=[Scopes.MANTARRAY__BASE])
    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}}

    test_job_id = uuid.uuid4()
    test_upload_id = uuid.uuid4()

    response = test_client.get(
        f"/jobs/waveform-data?upload_id={test_upload_id}&job_id={test_job_id}&well_name=A1&peaks_valleys=True",
        **kwargs,
    )

    assert response.status_code == 500


@pytest.mark.parametrize("pulse3d_version", [None, "1.2.3"])
@pytest.mark.parametrize("data_type", [None, ""] + list(DataTypes))
def test_waveform_data__get__time_force_parquet_found(mocker, pulse3d_version, data_type):
    test_inclusive_df = pd.DataFrame()
    mocker.patch.object(pd, "read_parquet", return_value=test_inclusive_df, autospec=True)

    test_user_id = uuid.uuid4()
    expected_presigned_url = "test-url.s3"
    test_analysis_params = {
        param: None
        for param in (
            "normalize_y_axis",
            "baseline_widths_to_use",
            "max_y",
            "include_stim_protocols",
            "prominence_factors",
            "width_factors",
            "twitch_widths",
            "start_time",
            "end_time",
        )
    }

    if data_type:
        expected_data_type = data_type
        data_type = data_type.lower()
    else:
        expected_data_type = DataTypes.FORCE
    test_analysis_params["data_type"] = data_type

    test_jobs = [
        {
            "user_id": test_user_id,
            "job_meta": json.dumps({"version": pulse3d_version, "analysis_params": test_analysis_params}),
            "filename": "test-recording.zip",
            "prefix": "/path/to/s3/object",
        }
    ]
    mocker.patch.object(main, "get_jobs", autospec=True, return_value=test_jobs)
    mocker.patch.object(main, "generate_presigned_url", autospec=True, return_value=expected_presigned_url)

    access_token = get_token(scopes=[Scopes.MANTARRAY__BASE], userid=test_user_id)
    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}}

    test_job_id = uuid.uuid4()
    test_upload_id = uuid.uuid4()

    response = test_client.get(
        f"/jobs/waveform-data?upload_id={test_upload_id}&job_id={test_job_id}", **kwargs
    )

    assert response.status_code == 200
    assert (
        response.json()
        == WaveformDataResponse(
            time_force_url=expected_presigned_url,
            peaks_valleys_url=expected_presigned_url,
            amplitude_label=get_metric_display_title(TwitchMetrics.AMPLITUDE, expected_data_type),
        ).model_dump()
    )


@pytest.mark.parametrize("pulse3d_version", [None, "1.2.3"])
def test_waveform_data__get__no_time_force_parquet_found(mocker, pulse3d_version):
    test_user_id = uuid.uuid4()

    expected_analysis_params = {
        param: None
        for param in (
            "normalize_y_axis",
            "baseline_widths_to_use",
            "max_y",
            "include_stim_protocols",
            "prominence_factors",
            "width_factors",
            "twitch_widths",
            "start_time",
            "end_time",
        )
    }

    test_jobs = [
        {
            "user_id": test_user_id,
            "job_meta": json.dumps({"version": pulse3d_version, "analysis_params": expected_analysis_params}),
            "filename": "test-recording.zip",
            "prefix": "/path/to/s3/object",
        }
    ]

    # set up mocked df returned from parquet file
    mocker.patch.object(main, "get_jobs", autospec=True, return_value=test_jobs)
    # ValueError gets raised with object isn't found
    mocker.patch.object(main, "generate_presigned_url", side_effect=ValueError)

    access_token = get_token(scopes=[Scopes.MANTARRAY__BASE], userid=test_user_id)
    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}}

    test_job_id = uuid.uuid4()
    test_upload_id = uuid.uuid4()

    response = test_client.get(
        f"/jobs/waveform-data?upload_id={test_upload_id}&job_id={test_job_id}", **kwargs
    )

    assert response.status_code == 200
    assert (
        response.json()
        == GenericErrorResponse(
            message="Parquet file was not found in S3. Reanalysis required.", error="MissingDataError"
        ).model_dump()
    )


@pytest.mark.parametrize(
    "token",
    [
        get_token([Scopes.MANTARRAY__BASE], account_type=AccountTypes.USER),
        get_token([Scopes.MANTARRAY__ADMIN], account_type=AccountTypes.ADMIN),
        None,
    ],
)
def test_versions__get(token, mocked_asyncpg_con):
    # arbitrary number of versions
    mocked_asyncpg_con.fetch.return_value = expected_version_dicts = [
        {"version": f"1.0.{i}", "state": f"state{i}"} for i in range(3)
    ]

    kwargs = {}
    if token:
        kwargs["headers"] = {"Authorization": f"Bearer {token}"}

    response = test_client.get("/versions", **kwargs)
    assert response.status_code == 200
    assert response.json() == expected_version_dicts

    mocked_asyncpg_con.fetch.assert_called_once_with(
        "SELECT version, state, end_of_life_date FROM pulse3d_versions WHERE state != 'deprecated' OR NOW() < end_of_life_date ORDER BY created_at"
    )
