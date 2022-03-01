from immutabledict import immutabledict
from src import utils


def test_aws_get_db_secrets__returns_correct_values():
    # mock is performed in conftest.py
    assert utils.aws.get_db_secrets() == {
        "reader_endpoint": "reader_endpoint",
        "writer_endpoint": "writer_endpoint",
        "user": "user",
    }


def test_db__stores_aws_secrets_correctly():
    # utils.aws.get_db_secrets also mocked in conftest.py
    assert utils.db.DB_SECRETS_DICT == immutabledict(utils.aws.get_db_secrets())


def test_db__connection_pools_dict_is_created_correctly():
    assert utils.db.CONNECTION_POOLS == immutabledict(
        {
            "reader": utils.db.ThreadedConnectionPool.return_value,
            "writer": utils.db.ThreadedConnectionPool.return_value,
        }
    )
    utils.db.ThreadedConnectionPool.assert_any_call(
        1, 3, database="postgres", **utils.db.get_db_connect_info("reader")
    )
    utils.db.ThreadedConnectionPool.assert_any_call(
        1, 1, database="postgres", **utils.db.get_db_connect_info("writer")
    )


def test_db_get_cursor__return_function__gets_cursor_correct_from_thread_pool(mocker):
    reader_mock = mocker.MagicMock()
    writer_mock = mocker.MagicMock()
    mocker.patch.object(utils.db, "CONNECTION_POOLS", {"reader": reader_mock, "writer": writer_mock})

    reader_conn = reader_mock.getconn.return_value
    writer_conn = writer_mock.getconn.return_value

    # test reader first
    reader_cursor_gen = utils.db.get_cursor("reader")
    next(reader_cursor_gen())
    # make sure reader was accessed
    reader_mock.getconn.assert_called_once_with()
    reader_conn.cursor.assert_called_once_with(cursor_factory=utils.db.DictCursor)
    # make sure writer wasn't accessed
    writer_mock.getconn.assert_not_called()
    writer_conn.cursor.assert_not_called()
    # test writer
    writer_cursor_gen = utils.db.get_cursor("writer")
    next(writer_cursor_gen())
    # make sure reader wasn't accessed again
    reader_mock.getconn.assert_called_once_with()
    reader_conn.cursor.assert_called_once_with(cursor_factory=utils.db.DictCursor)
    # make sure writer was accessed
    writer_mock.getconn.assert_called_once_with()
    writer_conn.cursor.assert_called_once_with(cursor_factory=utils.db.DictCursor)


def test_db_get_cursor__return_function__closes_cursor(mocker):
    reader_mock = mocker.MagicMock()
    writer_mock = mocker.MagicMock()
    mocker.patch.object(utils.db, "CONNECTION_POOLS", {"reader": reader_mock, "writer": writer_mock})

    # arbitrarily choosing to use reader pool for this test
    reader_conn = reader_mock.getconn.return_value
    reader_cursor = reader_conn.cursor.return_value

    reader_cursor_gen = utils.db.get_cursor("reader")
    next(reader_cursor_gen())

    reader_cursor.close.assert_called_once_with()


def test_db_get_cursor__return_function__releases_db_connection(mocker):
    reader_mock = mocker.MagicMock()
    writer_mock = mocker.MagicMock()
    mocker.patch.object(utils.db, "CONNECTION_POOLS", {"reader": reader_mock, "writer": writer_mock})

    # arbitrarily choosing to use writer pool for this test
    writer_conn = writer_mock.getconn.return_value

    writer_cursor_gen = utils.db.get_cursor("writer")
    next(writer_cursor_gen())

    writer_mock.putconn.assert_called_once_with(writer_conn)
