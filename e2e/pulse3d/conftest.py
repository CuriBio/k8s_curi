def pytest_addoption(parser):
    parser.addoption(
        "--headless", action="store_true", default=False, help="Faster, runs tests without showing browser"
    )
    parser.addoption("--slow-mo", action="store", default=3000, type=int, help="Integer in ms for pause between steps")


def pytest_generate_tests(metafunc):
    option_value = metafunc.config.option.headless
    if "headless" in metafunc.fixturenames and option_value is not None:
        metafunc.parametrize("headless", [option_value], scope="session")
    if "slow_mo" in metafunc.fixturenames and option_value is not None:
        metafunc.parametrize("slow_mo", [option_value], scope="session")
