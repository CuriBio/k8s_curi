def pytest_addoption(parser):
    parser.addoption("--view", action="store_true", default=False)
    parser.addoption("--noSlowmo", action="store_true", default=False)


def pytest_generate_tests(metafunc):
    meta_view = metafunc.config.option.view
    meta_noSlowmo = metafunc.config.option.noSlowmo
    if "view" in metafunc.fixturenames and meta_view is not None:
        metafunc.parametrize("view", [meta_view], scope="session")
    if "noSlowmo" in metafunc.fixturenames and meta_noSlowmo is not None:
        metafunc.parametrize("noSlowmo", [meta_noSlowmo], scope="session")
