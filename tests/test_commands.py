from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.config import BotConfig
from bot.main import ForUS


@pytest.mark.asyncio()
async def test_synchronize_global_commands_only_cleans_guild_commands():
    config = BotConfig(
        token="dummy",
        guild_ids=[],
        database_url="sqlite+aiosqlite:///./test.db",
        log_level="INFO",
        owner_ids=[],
    )
    bot = ForUS(config)

    guild_ids = [111, 222]

    async def fetch_guilds_stub(limit=None):  # noqa: ARG001
        for guild_id in guild_ids:
            yield SimpleNamespace(id=guild_id)

    bot.fetch_guilds = fetch_guilds_stub
    call_order: list[tuple[str, int | None]] = []

    def _record(name: str):
        def _callback(*args, **kwargs):
            guild = kwargs.get("guild")
            guild_id = getattr(guild, "id", None) if guild is not None else None
            call_order.append((name, guild_id))
        return _callback

    bot.tree.clear_commands = MagicMock(side_effect=_record("clear"))
    bot.tree.copy_global_to = MagicMock(side_effect=_record("copy"))

    async def _sync_mock(*args, **kwargs):
        _record("sync")(*args, **kwargs)

    bot.tree.sync = AsyncMock(side_effect=_sync_mock)
    bot.tree.get_commands = MagicMock(return_value=[object()])

    try:
        await bot._synchronize_global_commands_only()

        assert bot.tree.clear_commands.call_count == len(guild_ids)
        assert bot.tree.copy_global_to.call_count == len(guild_ids)
        cleared_guild_ids = {call.kwargs["guild"].id for call in bot.tree.clear_commands.call_args_list}
        assert cleared_guild_ids == set(guild_ids)

        sync_calls = bot.tree.sync.await_args_list
        assert len(sync_calls) == len(guild_ids) + 1

        for index, guild_id in enumerate(guild_ids):
            kwargs = sync_calls[index].kwargs
            assert kwargs["guild"].id == guild_id

        final_sync_kwargs = sync_calls[-1].kwargs
        assert "guild" not in final_sync_kwargs

        for guild_id in guild_ids:
            clear_index = call_order.index(("clear", guild_id))
            copy_index = call_order.index(("copy", guild_id))
            assert clear_index < copy_index

    finally:
        await bot.close()


@pytest.mark.asyncio()
async def test_synchronize_guild_commands_deduplicates_ids():
    config = BotConfig(
        token="dummy",
        guild_ids=[111, 111, 222],
        database_url="sqlite+aiosqlite:///./test.db",
        log_level="INFO",
        owner_ids=[],
    )
    bot = ForUS(config)

    bot.tree.clear_commands = MagicMock()
    bot.tree.copy_global_to = MagicMock()
    bot.tree.get_commands = MagicMock(return_value=[object()])

    async def _sync_stub(*args, **kwargs):  # noqa: ARG001
        return None

    bot.tree.sync = AsyncMock(side_effect=_sync_stub)

    try:
        await bot._synchronize_guild_commands([111, 111, 222])

        guild_clear_calls = [
            call for call in bot.tree.clear_commands.call_args_list if call.kwargs.get("guild") is not None
        ]
        assert len(guild_clear_calls) == 2

        copy_calls = bot.tree.copy_global_to.call_args_list
        assert len(copy_calls) == 2

        sync_calls = bot.tree.sync.await_args_list
        guild_syncs = [call for call in sync_calls if call.kwargs.get("guild") is not None]
        assert len(guild_syncs) == 2
        assert sync_calls[-1].kwargs.get("guild") is None
    finally:
        await bot.close()
