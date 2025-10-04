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
    bot.tree.clear_commands = MagicMock()
    bot.tree.sync = AsyncMock()

    try:
        await bot._synchronize_global_commands_only()

        assert bot.tree.clear_commands.call_count == len(guild_ids) * 2
        cleared_guild_ids = {call.kwargs["guild"].id for call in bot.tree.clear_commands.call_args_list}
        assert cleared_guild_ids == set(guild_ids)

        sync_calls = bot.tree.sync.await_args_list
        assert len(sync_calls) == len(guild_ids) + 1

        for index, guild_id in enumerate(guild_ids):
            kwargs = sync_calls[index].kwargs
            assert kwargs["guild"].id == guild_id

        final_sync_kwargs = sync_calls[-1].kwargs
        assert "guild" not in final_sync_kwargs

    finally:
        await bot.close()
