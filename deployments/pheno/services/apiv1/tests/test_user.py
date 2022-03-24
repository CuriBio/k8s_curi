from fastapi import HTTPException
import pytest
import sys
import os
import json
from fastapi_mail import FastMail


ROOT_DIR = os.path.dirname(os.path.abspath("src"))
sys.path.insert(0, ROOT_DIR)
from src.lib import *
from src.lib.models import *


def test_email_user_status__returns_correct_response_message(mocker, client, mock_cursor, caplog):
    # mock the sending of email because fake email will not work
    mocker.patch.object(FastMail, "send_message", autospec=True)
    mock_cursor.fetchrow.return_value = {
        "email": "test@gmail.com",
    }
    test_req_body = {
        "user_id": 1,
        "message": "test_message",
        "name": "test_name",
    }
    response = client.post("/emailUserStatus", json.dumps(test_req_body))

    # assertions for a successful repsonse
    assert "Awaiting email to be sent." in caplog.text
    assert test_req_body == Email_request_model(**test_req_body)
    assert response.json() == {"message": "Email has been sent"}
    assert response.status_code == 200
    mock_cursor.fetchrow.assert_awaited_with("SELECT email FROM users WHERE id=$1", test_req_body["user_id"])


@pytest.mark.parametrize(
    "body",
    [
        {
            "user_id": 1,
            "message": "test_message",
        },
        {
            "name": "test_name",
            "message": "test_message",
        },
        {
            "user_id": 1,
            "name": "test_name",
        },
    ],
)
def test_email_user_status__returns_400_status_code_if_incorrectly_formatted_body(client, body):
    with pytest.raises(HTTPException) as error:
        client.post("/emailUserStatus", json.dumps(body))
    
    assert error.value.status_code == 400


def test_email_user_status__returns_500_status_code_to_catch_other_errors(mocker, client, mock_cursor):
    mock_cursor.fetchrow.return_value = {
        "email": "test@gmail.com",
    }
    mocker.patch.object(
        FastMail,
        "send_message",
        autospec=True,
        side_effect=Exception("test error sending email"),
    )

    test_req_body = {
        "user_id": 1,
        "message": "test_message",
        "name": "test_name",
    }
    response = client.post("/emailUserStatus", json.dumps(test_req_body))

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Unable to process request: Email failed to send with error: test error sending email"
    }
