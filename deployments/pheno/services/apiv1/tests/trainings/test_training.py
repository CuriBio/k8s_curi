from copy import deepcopy
import pytest
import boto3
import json
from freezegun import freeze_time
from unittest.mock import MagicMock

from src.endpoints import trainings
from src.lib import *
from src.lib.models import *
from tests.conftest import MOCK_TRAINING_DB_RETURN_DICT

# get trainings
def test_get_trainings__returns_list_of_trainings_updated_with_presigned_urls(client, caplog, mock_cursor):
    # mock presigned url utils return value
    mock_cursor.fetch.return_value = [
        {
            "id": num,
            "name": f"name_{num}",
            "study": f"study_{num}",
        }
        for num in range(10)
    ]
    response = client.get("/train/1")

    mock_cursor.fetch.assert_awaited()
    assert "Generating presigned urls for 10 sample images." in caplog.text
    assert response.json() == [
        {
            "id": num,
            "name": f"name_{num}",
            "study": f"study_{num}",
            "sample_url": None,  # will return None because object does not exist in s3 and no mocking
        }
        for num in range(10)
    ]


def test_get_trainings__inserts_None_as_url_if_error_and_proceeds(
    client, mock_s3_client, caplog, mock_cursor
):
    # mock s3 error
    mock_s3_client.side_effect = Exception("fail")

    # mock presigned url utils return value
    mock_cursor.fetch.return_value = [
        {
            "id": num,
            "name": f"name_{num}",
            "study": f"study_{num}",
        }
        for num in range(1)
    ]

    # make request
    response = client.get("/train/1")

    expected_err_msg = "There was an error generating presigned url for {'id': 0, 'name': 'name_0', 'study': 'study_0'}: fail"
    assert expected_err_msg in caplog.text

    mock_cursor.fetch.assert_awaited()

    assert response.json() == [
        {
            "id": 0,
            "name": f"name_0",
            "study": f"study_0",
            "sample_url": None,  # will return None because object does not exist in s3 and no mocking
        }
    ]


@pytest.mark.parametrize(
    "route",
    [
        "/train/1",
        "/train/getFiltered/1",
        "/train/downloadLog/1",
        "/train/downloadResults/1",
        "/train/newSetup/1",
        "/train/plotLog/1",
        "/train/generatePatchExamples/1",
        "/train/startBlindScore/1",
        "/train/generateImagesToScore/1",
        "/train/getBlindScoreResults/1",
    ],
)
def test_get_routes__returns_500_error_to_catch_all_other_exceptions(client, mock_cursor, route):
    # mock random db error
    mock_cursor.fetch.side_effect = Exception("fail")
    mock_cursor.fetchrow.side_effect = Exception("fail")
    # make request
    response = client.get(route)

    assert response.json() == {"detail": "Unable to process request: fail"}
    assert response.status_code == 500


# get filtered trainings
def test_get_filtered_trainings__(client, mock_cursor):
    example_rows = [
        {
            "id": num,
            "user_id": 1,
            "name": f"name_{num}",
            "study": f"study_{num}",
            "trainpatchaccuracy": f"test_{num}",
            "valpatchaccuracy": f"test_{num}",
            "trainimageaccuracy": f"test_{num}",
            "valimageaccuracy": f"test_{num}",
            "zscoretrain": f"test_{num}",
            "zscoreval": f"test_{num}",
            "isreviewed": f"test_{num}",
            "param_to_be_filtered": 0,
            "param_to_be_filtered_1": 0,
            "param_to_be_filtered_2": 0,
            "param_to_be_filtered_3": 0,
        }
        for num in range(10)
    ]
    # mock cursor return list of dict with extra params to be filtered
    mock_cursor.fetch.return_value = example_rows
    response = client.get("/train/getFiltered/1")

    mock_cursor.fetch.assert_awaited()
    assert response.json() == [Filtered_training_model(**training) for training in example_rows]
    assert response.json() == [
        {
            "id": num,
            "trainpatchaccuracy": f"test_{num}",
            "valpatchaccuracy": f"test_{num}",
            "trainimageaccuracy": f"test_{num}",
            "valimageaccuracy": f"test_{num}",
            "zscoretrain": f"test_{num}",
            "zscoreval": f"test_{num}",
            "isreviewed": f"test_{num}",  # will return None because object does not exist in s3 and no mocking
        }
        for num in range(10)
    ]


#  download log
def test_download_log__returns_presigned_url(client, mock_s3_client, mock_s3_resource, mock_cursor):
    test_url = "www.test_url.com"

    mock_cursor.fetchrow.return_value = MOCK_TRAINING_DB_RETURN_DICT
    mock_s3_resource.return_value.Object.return_value.load.return_value = True
    mock_s3_client.return_value.generate_presigned_url.return_value = test_url

    # make request
    response = client.get("/train/downloadLog/1")

    assert response.json() == test_url
    assert response.status_code == 200


# download results
def test_download_results__returns_presigned_url_for_directory(
    client, mock_s3_client, mock_cursor, mock_s3_resource
):
    test_obj = MagicMock()
    test_obj.key = "test"

    test_url = "www.test_url.com"
    mock_cursor.fetchrow.return_value = MOCK_TRAINING_DB_RETURN_DICT

    mock_s3_resource.return_value.Object.return_value.load.return_value = True
    mock_s3_resource.return_value.Bucket.return_value.objects.filter.return_value = [test_obj] * 10

    mock_s3_client.return_value.generate_presigned_url.return_value = test_url

    # make request
    response = client.get("/train/downloadResults/1")

    assert response.json() == [test_url for _ in range(10)]
    assert response.status_code == 200


# update params
def test_update_param__returns_200_status_on_success(client, mock_cursor):
    # make request
    test_params = {"field": "name", "value": "new_name"}
    response = client.post("/train/updateParam/1", json.dumps(test_params))

    mock_cursor.execute.assert_awaited_with(
        f"UPDATE trainings SET {test_params['field']}=$1 WHERE id=$2", 1, test_params["value"]
    )

    assert response.json() is None
    assert response.status_code == 200


def test_update_param__returns_500_error_to_catch_all_other_exception(client, mock_cursor):
    mock_cursor.execute.side_effect = Exception("fail")

    # make request
    test_params = {"field": "name", "value": "new_name"}
    response = client.post("/train/updateParam/1", json.dumps(test_params))

    assert response.json() == {"detail": "Unable to process request: fail"}
    assert response.status_code == 500


# new setup
def test_new_setup__returns_new_train_response_model_if_user_limit_has_not_been_reached_and_not_admin(
    client, mock_cursor
):

    # mock cursor return value
    mock_cursor.fetchrow.return_value = {"uploadlimit": 5, "type": "", "count": 2}
    mock_cursor.fetch.return_value = ["list_of_segtrainings"]

    response = client.get("/train/newSetup/1")

    assert response.json() == {
        "segtrainings": ["list_of_segtrainings"],
        "show_focus_option": False,
        "select_focus_option": False,
        "smart_patching_option": False,
        "type": "",
    }


def test_new_setup__returns_new_train_response_model_if_user_limit_has_been_reached_and_is_admin(
    client, mock_cursor
):

    # mock cursor return value
    mock_cursor.fetchrow.return_value = {"uploadlimit": 5, "type": "admin", "count": 10}
    mock_cursor.fetch.return_value = ["list_of_segtrainings"]

    response = client.get("/train/newSetup/1")

    assert response.json() == {
        "segtrainings": ["list_of_segtrainings"],
        "show_focus_option": True,
        "select_focus_option": False,
        "smart_patching_option": True,
        "type": "admin",
    }


def test_new_setup__returns_403_forbidden_error_if_user_limit_has_been_reached_and_not_admin(
    client, mock_cursor
):
    # mock cursor return value
    mock_cursor.fetchrow.return_value = {"uploadlimit": 5, "type": "", "count": 10}

    response = client.get("/train/newSetup/1")

    assert response.status_code == 403
    assert response.json() == "User has reached account limit."


# upload new train images


def test_upload_new_train_images__returns_if_no_images(client):

    test_params = {
        "name": "name",
        "class_name": "classnames",
        "study_name": "study",
        "val_or_train": "val",
        "val_data_source": "combined",
        "img_names": [],
        "md5s": [],
    }
    response = client.post("/train/uploadNewTrainImages/1", json.dumps(test_params))

    assert response.json() == "No images found"
    assert response.status_code == 200


@pytest.mark.parametrize(
    "img_type, data_source",
    [("val", "combined"), ("train", "combined"), ("val", "separate"), ("train", "separate")],
)
def test_upload_new_train_images__returns_presigned_urls_using_type_related_keys_with_combined_images(
    client, mocker, img_type, data_source, mock_s3_client
):
    # mock s3 to return test url
    test_url = "www.test_url.com"
    mocked_presigned_post = mocker.patch.object(
        mock_s3_client.return_value, "generate_presigned_post", autospec=True, return_value=test_url
    )

    test_params = {
        "name": "name",
        "class_name": "classnames",
        "study_name": "study",
        "val_or_train": img_type,
        "val_data_source": data_source,
        "img_names": ["image_1.png", "image_2.png", "image_3.png"],
        "md5s": ["md5_1", "md5_2", "md5_3"],
    }

    response = client.post("/train/uploadNewTrainImages/1", json.dumps(test_params))

    assert response.json() == [test_url] * (
        len(test_params["img_names"]) + 1
    )  # plus one for additional sample image
    assert response.status_code == 200

    for idx, call in enumerate(mocked_presigned_post.call_args_list):
        if idx == 0:
            assert call == call(
                "phenolearn",
                "trainings/1/study/name/sample.jpg",
                Fields={"Content-MD5": "md5_1"},
                Conditions=[["starts-with", "$Content-MD5", ""]],
                ExpiresIn=3600,
            )
        else:
            key = (
                f"trainings/1/{test_params['study_name']}/{test_params['name']}/{test_params['name']}/{test_params['class_name']}/{test_params['img_names'][idx - 1]}"
                if data_source == "combined"
                else f"trainings/1/{test_params['study_name']}/{test_params['name']}/{test_params['name']}/{img_type}/{test_params['class_name']}/{test_params['img_names'][idx - 1]}"
            )
            assert call == call(
                "phenolearn",
                key,
                Fields={
                    "Content-MD5": test_params["md5s"][idx - 1]
                },  # minus one to count the extra sample image at index 0
                Conditions=[["starts-with", "$Content-MD5", ""]],
                ExpiresIn=3600,
            )


def test_upload_new_train_images__returns_500_error_to_catch_all_other_exception(client, mock_s3_client):
    # mock s3 error
    mock_s3_client.side_effect = Exception("fail")

    test_params = {
        "name": "name",
        "class_name": "classnames",
        "study_name": "study",
        "val_or_train": "val",
        "val_data_source": "combined",
        "img_names": ["image_1.png", "image_2.png", "image_3.png"],
        "md5s": ["md5_1", "md5_2", "md5_3"],
    }

    response = client.post("/train/uploadNewTrainImages/1", json.dumps(test_params))
    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to process request: fail"}


# new train submit


@pytest.mark.parametrize(
    "orig_name, study_name",
    [("name with space", "name+with.spec-chars"), ("name+with.spec-chars", "name with space")],
)
def test_new_train_submit__inserts_correctly_formatted_names_to_table(
    client, orig_name, study_name, mock_cursor
):
    test_params = {
        "orig_name": orig_name,
        "study_name": study_name,
        "patch_description": "patch_description",
        "smart_patch_seg_model": "smart_patch_seg_model",
        "smart_patch_channel": "smart_patch_channel",
        "patch_size": "patch_size",
        "image_size": "image_size",
        "val_percent": 50,
        "val_data_source": "val_data_source",
        "remove_out_focus": "yes",
        "arch": "arch",
        "precrop_size": 1,
        "epochs": 150,
        "batch_size": 100,
        "learn_rate": "learn_rate",
        "momentum": "momentum",
        "weight_decay": "weight_decay",
        "checkpoint": "checkpoint",
        "transfer": "transfer",
        "augment": "augment",
        "preaugment": "preaugment",
        "stop_criteria": "stop_criteria",
        "no_scale": "no_scale",
        "convert2gray": "convert2gray",
        "weighted_sampling": "weighted_sampling",
        "mode": "mode",
        "regweight": "regweight",
        "num_workers": "num_workers",
    }
    mock_cursor.fetchrow.return_value = {"type": ""}
    res = client.post("/train/submitNewTraining/1", test_params)

    assert "successfully submitted" in res.json()

    for call in mock_cursor.execute.call_args_list:
        assert orig_name not in call.args
        assert study_name not in call.args
        assert "name_with_space" in call.args
        assert "name_with_spec_chars" in call.args


test_params = {
    "orig_name": "orig_name",
    "study_name": "study_name",
    "patch_description": "patch_description",
    "smart_patch_seg_model": "smart_patch_seg_model",
    "smart_patch_channel": "smart_patch_channel",
    "patch_size": "patch_size",
    "image_size": "image_size",
    "val_percent": 50,
    "val_data_source": "val_data_source",
    "remove_out_focus": "yes",
    "arch": "arch",
    "precrop_size": 1,
    "epochs": 150,
    "batch_size": 100,
    "learn_rate": "learn_rate",
    "momentum": "momentum",
    "weight_decay": "weight_decay",
    "checkpoint": "checkpoint",
    "transfer": "transfer",
    "augment": "augment",
    "preaugment": "preaugment",
    "stop_criteria": "stop_criteria",
    "no_scale": "no_scale",
    "convert2gray": "convert2gray",
    "weighted_sampling": "weighted_sampling",
    "mode": "mode",
    "regweight": "regweight",
    "num_workers": "num_workers",
}


@pytest.mark.parametrize(
    "user_type",
    ["admin", "mo", "tenaya", "fountain", "shadi", "juan", "charlene", "chronus", ""],
)
def test_new_train_submit__skips_review_based_on_user_type(client, user_type, mock_cursor):

    mock_cursor.fetchrow.return_value = {"type": user_type}
    res = client.post("/train/submitNewTraining/1", test_params)

    assert "successfully submitted" in res.json()

    for call in mock_cursor.execute.call_args_list:
        if user_type == "":
            assert "no" in call.args[-1]
        else:
            assert "yes" in call.args[-1]


def test_new_train_submit__returns_500_error_to_catch_all_other_exception(client, mock_cursor):
    # mock s3 error
    mock_cursor.fetchrow.side_effect = Exception("fail")

    response = client.post("/train/submitNewTraining/1", test_params)
    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to process request: fail"}


test_retrain_params = {
    "whichuser": "admin",
    "user_id": 10,
    "orig_name": "orig_name",
    "patch_description": "patch_description",
    "smart_patch_seg_model": "smart_patch_seg_model",
    "smart_patch_channel": "smart_patch_channel",
    "patch_size": "patch_size",
    "val_percent": 50,
    "val_data_source": "val_data_source",
    "remove_out_focus": "yes",
    "arch": "arch",
    "precrop_size": 1,
    "epochs": 150,
    "batch_size": 100,
    "learn_rate": "learn_rate",
    "momentum": "momentum",
    "weight_decay": "weight_decay",
    "checkpoint": "checkpoint",
    "transfer": "transfer",
    "augment": "augment",
    "preaugment": "preaugment",
    "stop_criteria": "stop_criteria",
    "no_scale": "no_scale",
    "convert2gray": "convert2gray",
    "weighted_sampling": "weighted_sampling",
    "mode": "mode",
    "regweight": "regweight",
    "num_workers": "num_workers",
}
# test retrain
@pytest.mark.parametrize(
    "whichuser",
    ["admin", "mo", "tenaya", "fountain", "shadi", "juan", "charlene", "chronus"],
)
def test_retrain_submit__skips_review_based_on_user_type(
    client,
    whichuser,
    mocker,
    mock_cursor,
):
    # mock s3 copy
    mocker.patch.object(boto3, "resource", autospec=True)

    copy_retrain_params = deepcopy(test_retrain_params)
    copy_retrain_params["whichuser"] = whichuser

    mock_cursor.fetchrow.return_value = MOCK_TRAINING_DB_RETURN_DICT
    res = client.post("/train/reTrainSubmit/1", copy_retrain_params)

    assert "successfully submitted" in res.json()

    for call in mock_cursor.execute.call_args_list:
        assert "yes" in call.args[-1]


@freeze_time("2022-01-01")
def test_retrain_submit__assert_files_get_copied_correctly_in_s3(
    client, mocker, mock_cursor, mock_s3_resource
):
    # mock s3 copy
    spied_copy = mocker.spy(mock_s3_resource.return_value.meta.client, "copy")

    mock_cursor.fetchrow.return_value = MOCK_TRAINING_DB_RETURN_DICT

    res = client.post("/train/reTrainSubmit/1", test_retrain_params)

    assert "successfully submitted" in res.json()

    # assert sample image has been copied
    sample_src = {
        "Bucket": "phenolearn",
        "Key": f"trainings/1/study_name/training_name/sample.jpg",
    }
    target = f"trainings/10/study_name/RE-10-2022-01-01-000000/sample.jpg"

    spied_copy.assert_called_with(sample_src, "phenolearn", target)


def test_retrain_submit__returns_500_error_to_catch_all_other_exceptions(client, mock_cursor):
    mock_cursor.fetchrow.side_effect = Exception("fail")

    res = client.post("/train/reTrainSubmit/1", test_retrain_params)

    assert res.status_code == 500
    assert res.json() == {"detail": "Unable to process request: fail"}


# test plot log
def test_plot_log__returns_dict_of_parsed_vals_from_file_downloaded_from_s3(
    client, mocker, mock_cursor, mock_s3_resource, mock_s3_client
):
    mock_cursor.fetchrow.return_value = MOCK_TRAINING_DB_RETURN_DICT

    # mock to return test s3 file to use for testing
    mocked_tf = mocker.patch.object(trainings.tempfile, "TemporaryDirectory", autospec=True)
    mocked_tf.return_value.__enter__.return_value = "tests/trainings/training_test_files"

    mock_s3_resource.return_value.Object.return_value.load.return_value = True
    mock_s3_client.return_value.download_file.return_value = None

    response = client.get("/train/plotLog/1")
    assert response.json() == {
        "epochs": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
        "training_accuracy": [
            "0.0000",
            "72.8330",
            "86.6334",
            "88.6674",
            "91.4459",
            "95.1614",
            "95.4260",
            "97.6384",
            "98.6645",
            "99.0184",
            "99.4784",
        ],
        "training_loss": [
            "5.0000",
            "0.8048",
            "0.3881",
            "0.2599",
            "0.2344",
            "0.1613",
            "0.0949",
            "0.0834",
            "0.0737",
            "0.0504",
            "0.0457",
        ],
        "val_accuracy": [
            "36.4568",
            "42.7526",
            "34.8463",
            "32.9429",
            "58.7116",
            "72.7672",
            "31.4788",
            "57.2474",
            "32.5037",
            "32.2108",
            "36.3104",
        ],
        "val_loss": [
            "1.1850",
            "13.4488",
            "5.8964",
            "7.4375",
            "0.8303",
            "0.8655",
            "56.3276",
            "5.2098",
            "46.9631",
            "8.5807",
            "4.2700",
        ],
    }


def test_plot_log__returns_not_found_error_if_progress_file_does_not_exist(client, mocker, mock_cursor):
    mock_cursor.fetchrow.return_value = MOCK_TRAINING_DB_RETURN_DICT
    # mock to return test s3 file to use for testing
    mocked_tf = mocker.patch.object(trainings.tempfile, "TemporaryDirectory", autospec=True)
    mocked_tf.return_value.__enter__.return_value = "tests/trainings/training_test_files"

    response = client.get("/train/plotLog/1")

    assert response.json() == "No progress file found for training_name"
    assert response.status_code == 404


# generate patch examples
def test_generate_patch_ex__returns_list_of_presigned_urls(
    client, mock_cursor, mock_s3_resource, mock_s3_client
):
    test_obj = MagicMock()
    test_obj.key = "test"

    test_url = "www.test_url.com"
    test_urls = [test_url] * 10
    mock_cursor.fetchrow.return_value = MOCK_TRAINING_DB_RETURN_DICT

    # mock s3 return values to generate presigned urls
    mock_s3_resource.return_value.Object.return_value.load.return_value = True
    mock_s3_resource.return_value.Bucket.return_value.objects.filter.return_value = [test_obj] * 10
    mock_s3_client.return_value.generate_presigned_url.return_value = test_url

    response = client.get("/train/generatePatchExamples/1")

    assert response.json() == test_urls


# start blind score
def test_start_blind_score__returns_number_of_val_images_from_csv_file(
    client, mock_cursor, mocker, mock_s3_resource, mock_s3_client
):
    copied_return_dict = deepcopy(MOCK_TRAINING_DB_RETURN_DICT)
    copied_return_dict["name"] = "TR-1-2022-01-01-120000"
    mock_cursor.fetchrow.return_value = copied_return_dict

    # mock to return test s3 file to use for testing
    mock_s3_resource.return_value.Object.return_value.load.return_value = True
    mock_s3_client.return_value.download_file.return_value = None
    mocked_tf = mocker.patch.object(trainings.tempfile, "TemporaryDirectory", autospec=True)
    mocked_tf.return_value.__enter__.return_value = "tests/trainings/training_test_files"

    response = client.get("/train/startBlindScore/1")

    assert response.json() == 4


@pytest.mark.parametrize("route", ["/train/startBlindScore/1", "/train/generateImagesToScore/1"])
def test_csv_routes__returns_404_not_found_if_no_csv_file_is_found(
    client, mock_cursor, mocker, mock_s3_resource, route
):
    copied_return_dict = deepcopy(MOCK_TRAINING_DB_RETURN_DICT)
    copied_return_dict["name"] = "TR-1-2022-01-01-120000"
    mock_cursor.fetchrow.return_value = copied_return_dict

    # mock to return test s3 file to use for testing
    mock_s3_resource.return_value.Object.return_value.load.side_effect = Exception()
    mocked_tf = mocker.patch.object(trainings.tempfile, "TemporaryDirectory", autospec=True)
    mocked_tf.return_value.__enter__.return_value = "tests/trainings/training_test_files"

    response = client.get(route)

    assert response.json() == f"No output .csv file found for {copied_return_dict['name']}"
    assert response.status_code == 404


# generate images to score
def test_generate_images_to_score__returns_number_of_val_images_from_csv_file(
    client, mock_cursor, mocker, mock_s3_resource, mock_s3_client
):
    copied_return_dict = deepcopy(MOCK_TRAINING_DB_RETURN_DICT)
    copied_return_dict["name"] = "TR-1-2022-01-01-120000"
    copied_return_dict["classnames"] = "6_mon,12_mon"
    mock_cursor.fetchrow.return_value = copied_return_dict

    test_url = "www.test_url.com"
    expected_s3_objs = [
        "Val/6mo_val_1_2f752e9c_d057f6bd.png",
        "Val/6mo_val_10_f5297f9a_93e69c3a.png",
        "Val/12mon_val_1_a65f7a5c_2871d42b.png",
        "Val/12mon_val_10_add5700e_45a48d64.png",
        "Train/6mo_train_1000_c6921061_aac087fd.png",
        "Train/6mo_train_1001_657a585d_5d2ff9da.png",
        "Train/12mon_train_1000_396d3883_3f46ab5e.png",
        "Train/12mon_train_1001_c5e7e7e2_f7d39346.png",
    ]

    test_objs = [MagicMock() for _ in range(8)]
    for idx, obj in enumerate(test_objs):
        obj.key = expected_s3_objs[idx]

    # mock s3 return values to generate presigned urls
    mock_s3_resource.return_value.Object.return_value.load.return_value = True
    mock_s3_resource.return_value.Bucket.return_value.objects.filter.return_value = test_objs
    mock_s3_client.return_value.generate_presigned_url.return_value = test_url

    # redirect to test csc file
    mocked_tf = mocker.patch.object(trainings.tempfile, "TemporaryDirectory", autospec=True)
    mocked_tf.return_value.__enter__.return_value = "tests/trainings/training_test_files"

    response = client.get("/train/generateImagesToScore/1")

    assert response.json() == {
        "urls": ["www.test_url.com", "www.test_url.com", "www.test_url.com", "www.test_url.com"],
        "num_images": 4,
        "class_names": ["6_mon", "12_mon"],
        "true_classes": ["6_mon", "6_mon", "12_mon", "12_mon", "6_mon", "6_mon", "12_mon", "12_mon"],
    }


def test_generate_images_to_score__returns_404_if_no_presigned_urls_are_returned(
    client, mock_cursor, mocker, mock_s3_resource, mock_s3_client
):
    copied_return_dict = deepcopy(MOCK_TRAINING_DB_RETURN_DICT)
    copied_return_dict["name"] = "TR-1-2022-01-01-120000"
    copied_return_dict["classnames"] = "6_mon,12_mon"
    mock_cursor.fetchrow.return_value = copied_return_dict

    test_objs = [MagicMock() for _ in range(8)]
    for obj in test_objs:
        obj.key = ""

    # mock s3 return values to generate presigned urls
    mock_s3_resource.return_value.Object.return_value.load.return_value = True
    mock_s3_resource.return_value.Bucket.return_value.objects.filter.return_value = test_objs
    mock_s3_client.return_value.generate_presigned_url.return_value = None

    # redirect to test csc file
    mocked_tf = mocker.patch.object(trainings.tempfile, "TemporaryDirectory", autospec=True)
    mocked_tf.return_value.__enter__.return_value = "tests/trainings/training_test_files"

    response = client.get("/train/generateImagesToScore/1")

    assert response.json() == f"No presigned urls returned for {copied_return_dict['name']}"
    assert response.status_code == 404


# get blind score results
def test_get_blind_score_results__returns_presigned_url_for_blindscore_csv(
    client, mock_cursor, mock_s3_resource, mock_s3_client
):
    test_url = "www.test_url.com"
    mock_cursor.fetchrow.return_value = MOCK_TRAINING_DB_RETURN_DICT
    mock_s3_resource.return_value.Object.return_value.load.return_value = True
    mock_s3_client.return_value.generate_presigned_url.return_value = test_url

    response = client.get("/train/getBlindScoreResults/1")

    assert response.json() == test_url


def test_process_blind_score_results__uploads_new_csv_to_s3_and_returns_net_scores(
    mocker, client, mock_cursor, mock_s3_resource, mock_s3_client
):
    copied_return_dict = deepcopy(MOCK_TRAINING_DB_RETURN_DICT)
    copied_return_dict["name"] = "TR-1-2022-01-01-120000"
    copied_return_dict["classnames"] = "6_mon,12_mon"
    mock_cursor.fetchrow.return_value = copied_return_dict

    # mock open in download_file_from_s3 util to return with no error
    mock_s3_resource.return_value.Object.return_value.load.return_value = True
    mock_s3_client.return_value.download_file.return_value = None

    # redirect to test csc file
    mocked_tf = mocker.patch.object(trainings.tempfile, "TemporaryDirectory", autospec=True)
    mocked_tf.return_value.__enter__.return_value = "tests/trainings/training_test_files"

    # mock put_object in upload_file_to_s3 util to return with no error
    mock_s3_client.return_value.put_object.return_value = None

    details = {
        "image_urls": [
            "www.test_url.com/6mo_val_1_2f752e9c_d057f6bd.png",
            "www.test_url.com/6mo_val_10_f5297f9a_93e69c3a.png",
            "www.test_url.com/12mon_val_1_a65f7a5c_2871d42b.png",
            "www.test_url.com/12mon_val_10_add5700e_45a48d64.png",
        ],
        "true_classes": ["6_mon", "6_mon", "12_mon", "12_mon", "6_mon", "6_mon", "12_mon", "12_mon"],
        "class_names": ["6_mon", "12_mon"],
        "scores": [0.05, 0.05, 0.75, 0.91],
    }
    response = client.post("/train/processBlindScoreResults/1", json.dumps(details))

    assert response.json() == {
        "net_score": 50,
        "net_score_per_class": [0, 50],
        "num_images_per_class": [4, 4],
        "total_images": 8,
    }


def test_process_blind_score_results__returns_404_not_found_if_no_csv_file_is_found(
    client, mock_cursor, mock_s3_resource
):
    # mock to return test s3 file to use for testing
    mock_s3_resource.return_value.Object.return_value.load.side_effect = Exception()
    mock_cursor.fetchrow.return_value = MOCK_TRAINING_DB_RETURN_DICT

    details = {
        "image_urls": [
            "www.test_url.com/6mo_val_1_2f752e9c_d057f6bd.png",
            "www.test_url.com/6mo_val_10_f5297f9a_93e69c3a.png",
            "www.test_url.com/12mon_val_1_a65f7a5c_2871d42b.png",
            "www.test_url.com/12mon_val_10_add5700e_45a48d64.png",
        ],
        "true_classes": ["6_mon", "6_mon", "12_mon", "12_mon", "6_mon", "6_mon", "12_mon", "12_mon"],
        "class_names": ["6_mon", "12_mon"],
        "scores": [0.05, 0.05, 0.75, 0.91],
    }

    response = client.post("/train/processBlindScoreResults/1", json.dumps(details))
    assert response.json() == f"No output .csv file found for {MOCK_TRAINING_DB_RETURN_DICT['name']}"
    assert response.status_code == 404
