from random import randint
from fastapi.testclient import TestClient
import json
import os
import uuid
import pandas as pd
import pytest
from semver import VersionInfo

from auth import create_token
from utils.s3 import S3Error
from src import main

from labware_domain_models import LabwareDefinition
from pulse3D.constants import DEFAULT_BASELINE_WIDTHS, DEFAULT_PROMINENCE_FACTORS, DEFAULT_WIDTH_FACTORS

TWENTY_FOUR_WELL_PLATE = LabwareDefinition(row_count=4, column_count=6)


test_client = TestClient(main.app)


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

    access_token = get_token(scope=["pulse3d:user:free"], customer_id=test_customer_id, userid=test_user_id)
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


@pytest.mark.parametrize(
    "test_token_scope",
    [["pulse3d:user:paid"], ["pulse3d:customer:paid"], ["pulse3d:user:free"], ["pulse3d:customer:free"]],
)
@pytest.mark.parametrize(
    "test_upload_ids", [None, [], uuid.uuid4(), [uuid.uuid4()], [uuid.uuid4() for _ in range(3)]]
)
def test_uploads__get(test_token_scope, test_upload_ids, mocked_asyncpg_con, mocker):
    mocked_get_uploads = mocker.patch.object(main, "get_uploads", autospec=True, return_value=[])

    test_account_id = uuid.uuid4()
    account_type = "customer" if test_token_scope == ["pulse3d:customer:paid"] else "user"
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
    mocker.patch.object(
        main,
        "check_customer_quota",
        return_value={"jobs_reached": False, "uploads_reached": False},
        autospec=True,
    )
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

    access_token = get_token(scope=["pulse3d:user:paid"], customer_id=test_customer_id, userid=test_user_id)
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
        "customer_id": str(test_customer_id),
    }

    mocked_create_upload.assert_called_once_with(con=mocked_asyncpg_con, upload_params=expected_upload_params)
    mocked_gpp.assert_called_once_with(
        bucket=main.PULSE3D_UPLOADS_BUCKET,
        key=f"uploads/{test_customer_id}/{test_user_id}/{expected_upload_id}/{test_file_name}",
        md5s=test_md5s,
    )


@pytest.mark.parametrize(
    "test_token_scope",
    [["pulse3d:user:free"], ["pulse3d:customer:free"], ["pulse3d:user:paid"], ["pulse3d:customer:paid"]],
)
@pytest.mark.parametrize("test_upload_ids", [uuid.uuid4(), [uuid.uuid4()], [uuid.uuid4() for _ in range(3)]])
def test_uploads__delete(test_token_scope, test_upload_ids, mocked_asyncpg_con, mocker):
    mocked_delete_uploads = mocker.patch.object(main, "delete_uploads", autospec=True)

    test_account_id = uuid.uuid4()
    account_type = "customer" if test_token_scope == ["pulse3d:customer:free"] else "user"
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

    access_token = get_token(scope=["pulse3d:user:free"])
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
    access_token = get_token(scope=["pulse3d:user:free"], userid=test_user_id)
    kwargs = {
        "headers": {"Authorization": f"Bearer {access_token}"},
        "params": {"upload_ids": [uuid.uuid4()]},
    }

    response = test_client.delete("/uploads", **kwargs)
    assert response.status_code == 500


@pytest.mark.parametrize("download", [True, False, None])
@pytest.mark.parametrize(
    "test_token_scope",
    [["pulse3d:user:free"], ["pulse3d:customer:free"], ["pulse3d:user:paid"], ["pulse3d:customer:paid"]],
)
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
    account_type = "customer" if test_token_scope == ["pulse3d:customer:free"] else "user"
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
    access_token = get_token(scope=["pulse3d:user:free"], userid=test_user_id)

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
    access_token = get_token(scope=["pulse3d:user:free"], userid=test_user_id)

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

    access_token = get_token(scope=["pulse3d:user:free"], userid=test_user_id, customer_id=test_customer_id)

    mocked_create_job = mocker.patch.object(main, "create_job", autospec=True, return_value=expected_job_id)
    mocker.patch.object(
        main,
        "check_customer_quota",
        return_value={"jobs_reached": False, "uploads_reached": False},
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
        )
    }

    mocked_create_job.assert_called_once_with(
        con=mocked_asyncpg_con,
        upload_id=test_upload_id,
        queue=f"pulse3d-v{test_version}",
        priority=expected_job_priority,
        meta={"analysis_params": expected_analysis_params, "version": test_version},
        customer_id=str(test_customer_id),
        job_type="pulse3d",
    )


def test_jobs__post__basic_params_given(mocker):
    test_analysis_params = {"twitch_widths": [10, 20], "start_time": 0, "end_time": 1}

    access_token = get_token(scope=["pulse3d:user:free"])
    mocked_create_job = mocker.patch.object(main, "create_job", autospec=True, return_value=uuid.uuid4())
    mocker.patch.object(
        main,
        "check_customer_quota",
        return_value={"jobs_reached": False, "uploads_reached": False},
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
        )
    }
    expected_analysis_params.update(test_analysis_params)

    mocked_create_job.assert_called_once()
    assert mocked_create_job.call_args[1]["meta"]["analysis_params"] == expected_analysis_params


@pytest.mark.parametrize("param_name", ["prominence_factors", "width_factors"])
@pytest.mark.parametrize("param_tuple", [(1, 2), (None, 2), (1, None), (None, None)])
def test_jobs__post__advanced_params_given(param_name, param_tuple, mocker):
    test_analysis_params = {param_name: param_tuple}

    access_token = get_token(scope=["pulse3d:user:free"])
    mocked_create_job = mocker.patch.object(main, "create_job", autospec=True, return_value=uuid.uuid4())
    mocker.patch.object(
        main,
        "check_customer_quota",
        return_value={"jobs_reached": False, "uploads_reached": False},
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
        )
    }
    expected_analysis_params.update({param_name: format_mapping[param_tuple]})

    mocked_create_job.assert_called_once()
    assert mocked_create_job.call_args[1]["meta"]["analysis_params"] == expected_analysis_params


@pytest.mark.parametrize("param_tuple", [(1, 2), (None, 2), (1, None), (None, None)])
def test_jobs__post__with_baseline_widths_to_use(param_tuple, mocker):
    mocker.patch.object(
        main,
        "check_customer_quota",
        return_value={"jobs_reached": False, "uploads_reached": False},
        autospec=True,
    )
    test_analysis_params = {"baseline_widths_to_use": param_tuple}
    access_token = get_token(scope=["pulse3d:user:free"])
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
        )
    }

    expected_analysis_params.update({"baseline_widths_to_use": format_mapping[param_tuple]})

    mocked_create_job.assert_called_once()
    assert mocked_create_job.call_args[1]["meta"]["analysis_params"] == expected_analysis_params


@pytest.mark.parametrize("version", ["0.24.6", "0.25.0", "0.25.2", "0.25.4", "0.26.0"])
def test_jobs__post__omits_analysis_params_not_supported_by_the_selected_pulse3d_version(version, mocker):
    access_token = get_token(scope=["pulse3d:user:free"])
    mocked_create_job = mocker.patch.object(main, "create_job", autospec=True, return_value=uuid.uuid4())
    mocker.patch.object(
        main,
        "check_customer_quota",
        return_value={"jobs_reached": False, "uploads_reached": False},
        autospec=True,
    )
    kwargs = {
        "json": {"upload_id": str(uuid.uuid4()), "version": version},
        "headers": {"Authorization": f"Bearer {access_token}"},
    }
    response = test_client.post("/jobs", **kwargs)
    assert response.status_code == 200

    expected_analysis_param_keys = [
        "baseline_widths_to_use",
        "prominence_factors",
        "width_factors",
        "twitch_widths",
        "start_time",
        "end_time",
    ]

    pulse3d_semver = VersionInfo.parse(version)
    if pulse3d_semver >= "0.25.0":
        expected_analysis_param_keys.append("max_y")
    if pulse3d_semver >= "0.25.2":
        expected_analysis_param_keys.append("peaks_valleys")
    if pulse3d_semver >= "0.25.4":
        expected_analysis_param_keys.append("normalize_y_axis")
    if pulse3d_semver >= "0.26.0":
        expected_analysis_param_keys.append("stiffness_factor")

    expected_analysis_params = {param: None for param in expected_analysis_param_keys}

    mocked_create_job.assert_called_once()
    assert mocked_create_job.call_args[1]["meta"]["analysis_params"] == expected_analysis_params


@pytest.mark.parametrize(
    "test_token_scope",
    [["pulse3d:user:free"], ["pulse3d:customer:free"], ["pulse3d:user:paid"], ["pulse3d:customer:paid"]],
)
@pytest.mark.parametrize("test_job_ids", [uuid.uuid4(), [uuid.uuid4()], [uuid.uuid4() for _ in range(3)]])
def test_jobs__delete(test_token_scope, test_job_ids, mocked_asyncpg_con, mocker):
    mocked_delete_jobs = mocker.patch.object(main, "delete_jobs", autospec=True)

    test_account_id = uuid.uuid4()
    account_type = "customer" if test_token_scope == ["pulse3d:customer:free"] else "user"
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
    access_token = get_token(scope=["pulse3d:user:free"], userid=test_user_id)
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
    access_token = get_token(scope=["pulse3d:user:free"], userid=test_user_id)
    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}, "params": {"job_ids": [uuid.uuid4()]}}

    response = test_client.delete("/jobs", **kwargs)
    assert response.status_code == 500


@pytest.mark.parametrize(
    "test_token_scope",
    [["pulse3d:user:free"], ["pulse3d:customer:free"], ["pulse3d:user:paid"], ["pulse3d:customer:paid"]],
)
@pytest.mark.parametrize("test_job_ids", [[uuid.uuid4() for _ in range(r)] for r in range(1, 4)])
def test_jobs_download__post__no_duplicate_analysis_file_names(
    test_token_scope, test_job_ids, mocked_asyncpg_con, mocker
):
    test_account_id = uuid.uuid4()
    account_type = "customer" if test_token_scope == ["pulse3d:customer:free"] else "user"
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


@pytest.mark.parametrize(
    "test_token_scope",
    [["pulse3d:user:free"], ["pulse3d:customer:free"], ["pulse3d:user:paid"], ["pulse3d:customer:paid"]],
)
def test_download__post__duplicate_analysis_file_names(mocked_asyncpg_con, test_token_scope, mocker):
    test_account_id = uuid.uuid4()
    account_type = "customer" if test_token_scope == ["pulse3d:customer:free"] else "user"
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

    access_token = get_token(scope=["pulse3d:user:free"])

    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}}
    # in None case, don't even pass a param
    if test_job_ids is not None:
        kwargs["json"] = {"job_ids": test_job_ids}

    response = test_client.post("/jobs/download", **kwargs)
    assert response.status_code == test_error_code

    mocked_get_jobs.assert_not_called()
    mocked_yield_objs.assert_not_called()


@pytest.mark.parametrize("test_query_params", [f"upload_id={uuid.uuid4()}", f"job_id={uuid.uuid4()}"])
def test_waveform_data__get__no_job_or_upload_id_is_found(mocker, test_query_params):
    access_token = get_token(scope=["pulse3d:user:free"])
    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}}

    response = test_client.get(f"/jobs/waveform_data?{test_query_params}", **kwargs)

    assert response.status_code == 400


def test_waveform_data__get__getting_job_metadata_from_db_errors(mocker):
    mocker.patch.object(main, "get_jobs", autospec=True, return_value=S3Error())

    access_token = get_token(scope=["pulse3d:user:free"])
    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}}

    test_job_id = uuid.uuid4()
    test_upload_id = uuid.uuid4()

    response = test_client.get(
        f"/jobs/waveform_data?upload_id={test_upload_id}&job_id={test_job_id}", **kwargs
    )

    assert response.status_code == 500


@pytest.mark.parametrize("include_raw_data,expected_conversion", [[False, 1], [True, 1e4]])
def test_waveform_data__get__handles_time_unit_if_old_parquet_file(
    mocker, include_raw_data, expected_conversion
):
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
    # empty for this test
    expected_analysis_params["peaks_valleys"] = {}
    test_jobs = [{"job_meta": json.dumps({"analysis_params": expected_analysis_params})}]

    # set up mocked df returned from parquet file
    mocker.patch.object(main, "get_jobs", autospec=True, return_value=test_jobs)
    mocker.patch.object(main, "download_directory_from_s3", autospec=True)

    mocked_read = mocker.patch.object(
        pd, "read_parquet", autospec=True, return_value=create_test_df(include_raw_data)
    )
    mocked_df = mocked_read.return_value
    expected_time = mocked_df["Time (s)"].tolist()

    access_token = get_token(scope=["pulse3d:user:free"])
    kwargs = {"headers": {"Authorization": f"Bearer {access_token}"}}

    test_job_id = uuid.uuid4()
    test_upload_id = uuid.uuid4()

    response = test_client.get(
        f"/jobs/waveform_data?upload_id={test_upload_id}&job_id={test_job_id}", **kwargs
    )

    assert response.status_code == 200
    response_body = response.json()

    coordinates = response_body["coordinates"].values()
    # assert coordinates will be sent for each well
    assert len(coordinates) == 24
    for well_coords in response_body["coordinates"].values():
        # each time point should be contained
        assert len(well_coords) == len(expected_time)
        # old parquet time data is sent in seconds so no conversion should happen
        assert [i[0] * expected_conversion for i in enumerate(well_coords)] == expected_time


@pytest.mark.parametrize(
    "token",
    [
        get_token(["pulse3d:user:free"], account_type="user"),
        get_token(["pulse3d:customer:free"], account_type="customer"),
        get_token(["pulse3d:user:paid"], account_type="user"),
        get_token(["pulse3d:customer:paid"], account_type="customer"),
        None,
    ],
)
def test_versions__get(token, mocked_asyncpg_con, mocker):
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
        "SELECT version, state FROM pulse3d_versions WHERE state != 'deprecated' ORDER BY created_at"
    )
