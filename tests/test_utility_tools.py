from __future__ import annotations

from datetime import datetime, timedelta, timezone as dt_timezone
from types import SimpleNamespace

import pytest
from zoneinfo import ZoneInfo

from bot.services.utility_tools import (
    discord_timestamp_variants,
    format_timezone_display,
    gather_guild_statistics,
    parse_datetime_input,
    resolve_timezone,
)


def test_resolve_timezone_alias() -> None:
    tz = resolve_timezone("WIB")
    assert isinstance(tz, ZoneInfo)
    assert tz.key == "Asia/Jakarta"


def test_resolve_timezone_offset() -> None:
    tz = resolve_timezone("UTC+7")
    offset = tz.utcoffset(datetime.now(dt_timezone.utc))
    assert offset == timedelta(hours=7)


def test_resolve_timezone_fallback_alias() -> None:
    tz = resolve_timezone(None, fallback="Jakarta")
    assert isinstance(tz, ZoneInfo)
    assert tz.key == "Asia/Jakarta"


def test_parse_datetime_input_time_only() -> None:
    tz = ZoneInfo("Asia/Jakarta")
    reference = datetime(2025, 1, 1, 12, 0, tzinfo=tz)
    parsed = parse_datetime_input("23:45", tz, reference=reference)
    assert parsed.hour == 23
    assert parsed.minute == 45
    assert parsed.tzinfo == tz


def test_discord_timestamp_variants_contains_relative() -> None:
    tz = ZoneInfo("UTC")
    target = datetime(2025, 1, 1, 0, 0, tzinfo=tz)
    variants = discord_timestamp_variants(target)
    labels = {label for label, _ in variants}
    assert len(variants) == 7
    assert "Relative" in labels


def test_gather_guild_statistics_counts_components() -> None:
    members = [SimpleNamespace(bot=False), SimpleNamespace(bot=True), SimpleNamespace(bot=False)]
    guild = SimpleNamespace(
        members=members,
        member_count=len(members),
        text_channels=[1, 2, 3],
        voice_channels=[1],
        stage_channels=[1],
        forum_channels=[1, 2],
        categories=[1, 2],
        threads=[1, 2, 3, 4],
        roles=[1, 2, 3, 4, 5],
        emojis=[1, 2],
        stickers=[1],
        scheduled_events=[1, 2, 3],
        premium_subscription_count=4,
        premium_tier=2,
    )
    stats = gather_guild_statistics(guild)
    assert stats.total_members == len(members)
    assert stats.bot_members == 1
    assert stats.human_members == 2
    assert stats.text_channels == 3
    assert stats.voice_channels == 1
    assert stats.forum_channels == 2
    assert stats.categories == 2
    assert stats.thread_channels == 4
    assert stats.roles == 5
    assert stats.emoji_count == 2
    assert stats.boost_level == 2
    assert stats.boosts == 4


def test_format_timezone_display_for_offset() -> None:
    tz = dt_timezone(timedelta(hours=-3, minutes=-30))
    label = format_timezone_display(tz)
    assert label == "UTC-03:30"


def test_resolve_timezone_invalid() -> None:
    with pytest.raises(ValueError):
        resolve_timezone("INVALID_ZONE")
