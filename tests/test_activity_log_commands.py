from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from discord import app_commands

from bot.cogs.activity_log import ActivityLog


class DummyResponse:
    def __init__(self) -> None:
        self._done = False
        self.messages: list[dict[str, object | None]] = []

    def is_done(self) -> bool:
        return self._done

    async def send_message(self, content: str | None = None, *, embed=None, ephemeral: bool = False) -> None:
        self._done = True
        self.messages.append({"content": content, "embed": embed, "ephemeral": ephemeral})


class DummyFollowup:
    def __init__(self) -> None:
        self.messages: list[dict[str, object | None]] = []

    async def send(self, content: str | None = None, *, embed=None, ephemeral: bool = False) -> None:
        self.messages.append({"content": content, "embed": embed, "ephemeral": ephemeral})


class DummyInteraction:
    def __init__(self, guild) -> None:
        self.guild = guild
        self.response = DummyResponse()
        self.followup = DummyFollowup()


class DummyGuild:
    def __init__(self, guild_id: int) -> None:
        self.id = guild_id

    def get_channel(self, channel_id: int):  # noqa: ARG002 - interface compatibility
        return None


class DummyRepo:
    def __init__(self, *, disabled: list[str] | None = None, enabled: bool = True, channel_id: int | None = None) -> None:
        self._settings = SimpleNamespace(
            activity_log_disabled_events=list(disabled or []),
            activity_log_enabled=enabled,
            activity_log_channel_id=channel_id,
            log_channel_id=None,
        )
        self.upsert_calls: list[tuple[int, dict[str, object]]] = []

    async def upsert(self, guild_id: int, **kwargs):
        self.upsert_calls.append((guild_id, kwargs))
        if "activity_log_disabled_events" in kwargs:
            self._settings.activity_log_disabled_events = list(kwargs["activity_log_disabled_events"])
        if "activity_log_enabled" in kwargs:
            self._settings.activity_log_enabled = bool(kwargs["activity_log_enabled"])
        if "activity_log_channel_id" in kwargs:
            self._settings.activity_log_channel_id = kwargs["activity_log_channel_id"]

    async def get(self, guild_id: int):  # noqa: ARG002 - match repository API
        return self._settings


class DummyBot:
    def __init__(self, repo: DummyRepo) -> None:
        self.guild_repo = repo


@pytest.mark.asyncio()
async def test_set_channel_updates_repository_and_cache():
    repo = DummyRepo()
    bot = DummyBot(repo)
    cog = ActivityLog(bot)
    cog.logger.invalidate_cache = AsyncMock()

    guild = DummyGuild(101)
    interaction = DummyInteraction(guild)
    channel = SimpleNamespace(id=555, mention="#aktivitas")

    await ActivityLog.set_channel.callback(cog, interaction, channel)

    assert repo.upsert_calls == [(101, {"activity_log_channel_id": 555})]
    cog.logger.invalidate_cache.assert_awaited_once_with(101)
    assert interaction.response.messages[0]["ephemeral"] is True
    assert "aktivitas" in str(interaction.response.messages[0]["content"])


@pytest.mark.asyncio()
async def test_category_toggle_updates_disabled_list():
    repo = DummyRepo(disabled=["messages"], enabled=True)
    bot = DummyBot(repo)
    cog = ActivityLog(bot)
    cog.logger.invalidate_cache = AsyncMock()

    guild = DummyGuild(202)
    interaction_disable = DummyInteraction(guild)
    choice_voice = app_commands.Choice(name="Voice", value="voice")

    await ActivityLog.category.callback(cog, interaction_disable, choice_voice, False)

    assert repo.upsert_calls[-1] == (202, {"activity_log_disabled_events": ["messages", "voice"]})
    assert repo._settings.activity_log_disabled_events == ["messages", "voice"]
    assert cog.logger.invalidate_cache.await_count == 1
    assert cog.logger.invalidate_cache.await_args_list[0].args == (202,)
    assert interaction_disable.response.messages[0]["ephemeral"] is True
    assert "dinonaktifkan" in str(interaction_disable.response.messages[0]["content"])

    interaction_enable = DummyInteraction(guild)
    await ActivityLog.category.callback(cog, interaction_enable, choice_voice, True)

    assert repo.upsert_calls[-1] == (202, {"activity_log_disabled_events": ["messages"]})
    assert repo._settings.activity_log_disabled_events == ["messages"]
    assert interaction_enable.response.messages[0]["ephemeral"] is True
    assert "diaktifkan" in str(interaction_enable.response.messages[0]["content"])
    assert cog.logger.invalidate_cache.await_count == 2
    assert cog.logger.invalidate_cache.await_args_list[-1].args == (202,)