from src import utils


def test_foo():
    assert utils.db.get_cursor is None
