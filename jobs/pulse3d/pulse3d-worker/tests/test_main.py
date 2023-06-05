from src import main


async def test_main__calls_process(mocker):
    mocked_create_pool = mocker.patch.object(main.asyncpg, "create_pool", autospec=True)
    mocked_create_pool.return_value.__aenter__.return_value.acquire = mocker.MagicMock()

    mocked_process = mocker.patch.object(main, "process", side_effect=Exception())

    await main.main()

    mocked_process.assert_awaited_once()
