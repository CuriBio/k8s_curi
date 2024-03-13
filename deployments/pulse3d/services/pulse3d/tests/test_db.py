import pytest
from jobs import get_uploads


@pytest.mark.parametrize(
    "account_type,customer_id,user_id,upload_ids,upload_types,rw_all_data_upload_types,expected_query,expected_query_params",
    [
        (
            "rw_all_data_user",
            "test_customer_id",
            "test_user_id",
            ["id1", "id2"],
            ["up1", "up2", "up3", "up4"],
            ["up3", "up4", "upX"],
            "SELECT users.name AS username, uploads.* "
            "FROM uploads JOIN users ON uploads.user_id=users.id "
            "WHERE users.customer_id=$1 AND uploads.deleted='f' "
            "AND (uploads.type IN ($2, $3) OR (uploads.user_id=$4 AND uploads.type IN ($5, $6))) "
            "AND uploads.id IN ($7, $8)",
            ["test_customer_id", "up3", "up4", "test_user_id", "up1", "up2", "id1", "id2"],
        ),
        (
            "rw_all_data_user",
            "test_customer_id",
            "test_user_id",
            ["id1", "id2"],
            None,
            ["up1", "up2"],
            "SELECT users.name AS username, uploads.* "
            "FROM uploads JOIN users ON uploads.user_id=users.id "
            "WHERE users.customer_id=$1 AND uploads.deleted='f' "
            "AND (uploads.type IN ($2, $3)) "
            "AND uploads.id IN ($4, $5)",
            ["test_customer_id", "up1", "up2", "id1", "id2"],
        ),
        (
            "admin",
            "test_customer_id",
            None,
            None,
            ["up1", "up2"],
            None,
            "SELECT users.name AS username, uploads.* "
            "FROM uploads JOIN users ON uploads.user_id=users.id "
            "WHERE users.customer_id=$1 AND uploads.deleted='f' "
            "AND uploads.type IN ($2, $3)",
            ["test_customer_id", "up1", "up2"],
        ),
        (
            "user",
            None,
            "test_user_id",
            None,
            None,
            ["up1", "up2"],
            "SELECT * FROM uploads WHERE user_id=$1 AND deleted='f' AND (uploads.type IN ($2, $3))",
            ["test_user_id", "up1", "up2"],
        ),
        (
            "user",
            None,
            "test_user_id",
            None,
            ["up1", "up2"],
            None,
            "SELECT * FROM uploads WHERE user_id=$1 AND deleted='f' AND (uploads.type IN ($2, $3))",
            ["test_user_id", "up1", "up2"],
        ),
    ],
)
async def test_get_uploads__uses_correct_query(
    account_type,
    customer_id,
    user_id,
    upload_ids,
    upload_types,
    rw_all_data_upload_types,
    expected_query,
    expected_query_params,
    mocker,
):
    mocked_con = mocker.MagicMock()

    await get_uploads(
        con=mocked_con,
        account_type=account_type,
        customer_id=customer_id,
        user_id=user_id,
        upload_ids=upload_ids,
        upload_types=upload_types,
        rw_all_data_upload_types=rw_all_data_upload_types,
    )

    mocked_con.cursor.assert_called_once_with(expected_query, *expected_query_params)
