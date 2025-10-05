from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import discord
import pytest

from bot.config import PresenceActivityConfig, RichPresenceConfig
from bot.services.presence import (
    RichPresenceManager,
    _build_activity,
    _format_template,
    _humanize_timedelta,
)


class DummyReminderRepository:
    async def all_pending(self):  # noqa: D401
        """Simulasi daftar pengingat."""
        return [object(), object(), object()]


class DummyScheduler:
    def job_count(self) -> int:
        return 4


class DummyTree:
    def get_commands(self):  # noqa: D401
        """Kembalikan daftar perintah terdaftar."""
        return [1, 2, 3, 4, 5]


class DummyGuild:
    def __init__(self, member_count: int, human: int, bots: int) -> None:
        humans = [SimpleNamespace(bot=False) for _ in range(human)]
        bots_members = [SimpleNamespace(bot=True) for _ in range(bots)]
        self.member_count = member_count
        self.members = humans + bots_members


class DummyBot:
    def __init__(self) -> None:
        self.guilds = [DummyGuild(25, 18, 7), DummyGuild(40, 30, 10)]
        self.tree = DummyTree()
        self.cogs = {"utility": object(), "moderation": object(), "fun": object()}
        self.latency = 0.123
        self.shard_count = 2
        self.scheduler = DummyScheduler()
        self.reminder_repo = DummyReminderRepository()
        self.config = SimpleNamespace(owner_ids=[111, 222, 333])
        self.started_at = datetime.now(timezone.utc) - timedelta(hours=2, minutes=15)
        self.db = object()


@pytest.mark.asyncio()
async def test_collect_snapshot_compiles_metrics() -> None:
    config = RichPresenceConfig(
        enabled=True,
        rotation_seconds=30,
        default_status="online",
        activities=[PresenceActivityConfig(type="playing", text="Test")],
    )
    manager = RichPresenceManager(DummyBot(), config, version="1.2.3")
    snapshot = await manager._collect_snapshot()

    assert snapshot.guild_count == 2
    assert snapshot.member_count == 65
    # 18 + 30 humans dari definisi DummyGuild
    assert snapshot.human_count == 48
    assert snapshot.bot_count == 17
    assert snapshot.commands_count == 5
    assert snapshot.cog_count == 3
    assert snapshot.scheduler_jobs == 4
    assert snapshot.pending_reminders == 3
    assert snapshot.owner_count == 3
    assert snapshot.version == "1.2.3"
    assert snapshot.database_connected is True
    assert snapshot.latency_ms == pytest.approx(123.0, rel=0.01)
    assert snapshot.uptime.total_seconds() >= 2 * 3600


def test_build_activity_variants() -> None:
    playing = _build_activity(
        PresenceActivityConfig(type="playing", text="Game", details="det", state="state"),
        "Main game",
        "Detail",
        "State",
    )
    assert isinstance(playing, discord.Activity)
    assert playing.name == "Main game"

    streaming = _build_activity(
        PresenceActivityConfig(type="streaming", text="Live", url="https://example.com"),
        "Live Now",
        None,
        None,
    )
    assert isinstance(streaming, discord.Streaming)
    assert streaming.url == "https://example.com"

    custom = _build_activity(
        PresenceActivityConfig(type="custom", text="Status", emoji="🔥"),
        "Status Custom",
        None,
        None,
    )
    assert isinstance(custom, discord.CustomActivity)
    assert getattr(custom, "name", None) == "Status Custom"


def test_format_template_handles_missing_keys() -> None:
    result = _format_template("Halo {nama} – {unknown}", {"nama": "ForUS"})
    assert result == "Halo ForUS – {unknown}"


def test_humanize_timedelta_output() -> None:
    human = _humanize_timedelta(timedelta(hours=1, minutes=30, seconds=10))
    assert human.startswith("1 jam")
