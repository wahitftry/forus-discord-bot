from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, time as dt_time, timedelta, timezone as dt_timezone, tzinfo
from typing import Any, Iterable, Sequence

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

__all__ = [
    "GuildStatistics",
    "resolve_timezone",
    "parse_datetime_input",
    "discord_timestamp_variants",
    "gather_guild_statistics",
    "process_resource_snapshot",
    "format_timezone_display",
]

SUPPORTED_TIME_FORMATS: Sequence[str] = (
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%d/%m/%Y %H:%M",
    "%Y/%m/%d %H:%M",
    "%H:%M",
    "%H:%M:%S",
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
)

_DATE_ONLY_FORMATS = {
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
}

_TIME_ONLY_FORMATS = {
    "%H:%M",
    "%H:%M:%S",
}

_TZ_ALIAS = {
    "WIB": "Asia/Jakarta",
    "WITA": "Asia/Makassar",
    "WIT": "Asia/Jayapura",
    "JAKARTA": "Asia/Jakarta",
    "JKT": "Asia/Jakarta",
    "ICT": "Asia/Bangkok",
    "SGP": "Asia/Singapore",
    "MAL": "Asia/Kuala_Lumpur",
    "KUALA": "Asia/Kuala_Lumpur",
    "UTC": "UTC",
    "GMT": "UTC",
}

_OFFSET_RE = re.compile(r"^(?:UTC|GMT)?\s*([+-])\s*(\d{1,2})(?::?(\d{2}))?$", re.IGNORECASE)


@dataclass(slots=True)
class GuildStatistics:
    total_members: int
    human_members: int
    bot_members: int
    text_channels: int
    voice_channels: int
    stage_channels: int
    forum_channels: int
    categories: int
    thread_channels: int
    roles: int
    emoji_count: int
    sticker_count: int
    scheduled_events: int
    boosts: int
    boost_level: int


def _to_timezone(value: tzinfo | str | None) -> tzinfo:
    if value is None:
        raise ValueError("Zona waktu tidak boleh kosong.")
    if isinstance(value, tzinfo):
        return value
    return ZoneInfo(str(value))


def resolve_timezone(name: str | None, *, fallback: tzinfo | str | None = "UTC") -> tzinfo:
    """Resolve nama zona waktu ke objek tzinfo.

    Mendukung alias umum (WIB, WITA, WIT) dan format offset seperti UTC+7 atau GMT-03:30.
    """

    if not name or not str(name).strip():
        return _to_timezone(fallback)

    candidate = str(name).strip()
    alias_key = candidate.upper()
    if alias_key in _TZ_ALIAS:
        candidate = _TZ_ALIAS[alias_key]

    try:
        return ZoneInfo(candidate)
    except ZoneInfoNotFoundError as exc:
        match = _OFFSET_RE.fullmatch(candidate)
        if not match:
            raise ValueError(f"Zona waktu '{name}' tidak dikenali.") from exc
        sign = 1 if match.group(1) == "+" else -1
        hours = int(match.group(2))
        minutes = int(match.group(3) or 0)
        if hours > 23 or minutes > 59:
            raise ValueError(f"Offset zona waktu '{name}' tidak valid.") from exc
        delta = timedelta(hours=hours, minutes=minutes) * sign
        return dt_timezone(delta)


def _try_parse_iso(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    else:
        if parsed.tzinfo is None:
            return parsed
        return parsed


def parse_datetime_input(value: str, tz: tzinfo, *, reference: datetime | None = None) -> datetime:
    if not value or not value.strip():
        raise ValueError("Waktu tidak boleh kosong.")

    reference = reference or datetime.now(tz)
    raw = value.strip()

    iso = _try_parse_iso(raw)
    if iso is not None:
        if iso.tzinfo is None:
            return iso.replace(tzinfo=tz)
        return iso.astimezone(tz)

    for fmt in SUPPORTED_TIME_FORMATS:
        try:
            parsed = datetime.strptime(raw, fmt)
        except ValueError:
            continue
        if fmt in _DATE_ONLY_FORMATS:
            return datetime.combine(parsed.date(), dt_time(), tz)
        if fmt in _TIME_ONLY_FORMATS:
            return datetime.combine(reference.date(), parsed.time(), tz)
        return parsed.replace(tzinfo=tz)

    raise ValueError(
        "Format waktu tidak dikenali. Gunakan format seperti '2025-01-31 19:45' atau '31-01-2025 19:45'."
    )


def discord_timestamp_variants(dt: datetime) -> list[tuple[str, str]]:
    aware = dt if dt.tzinfo is not None else dt.replace(tzinfo=dt_timezone.utc)
    unix_timestamp = int(aware.timestamp())
    variants = [
        ("Short Time", f"<t:{unix_timestamp}:t>"),
        ("Long Time", f"<t:{unix_timestamp}:T>"),
        ("Short Date", f"<t:{unix_timestamp}:d>"),
        ("Long Date", f"<t:{unix_timestamp}:D>"),
        ("Short Date & Time", f"<t:{unix_timestamp}:f>"),
        ("Long Date & Time", f"<t:{unix_timestamp}:F>"),
        ("Relative", f"<t:{unix_timestamp}:R>"),
    ]
    return variants


def gather_guild_statistics(guild: Any) -> GuildStatistics:
    members: list[Any] = list(getattr(guild, "members", []) or [])
    member_count = getattr(guild, "member_count", None)
    total_members = member_count if isinstance(member_count, int) and member_count > 0 else len(members)
    if total_members == 0 and members:
        total_members = len(members)

    bot_members = sum(1 for member in members if getattr(member, "bot", False))
    human_members = len(members) - bot_members if members else max(total_members - bot_members, 0)

    text_channels = len(getattr(guild, "text_channels", []) or [])
    voice_channels = len(getattr(guild, "voice_channels", []) or [])
    stage_channels = len(getattr(guild, "stage_channels", []) or [])
    forum_channels = len(getattr(guild, "forum_channels", []) or [])
    categories = len(getattr(guild, "categories", []) or [])
    thread_channels = len(getattr(guild, "threads", []) or [])
    roles = len(getattr(guild, "roles", []) or [])
    emoji_count = len(getattr(guild, "emojis", []) or [])
    sticker_count = len(getattr(guild, "stickers", []) or [])
    scheduled_events = len(getattr(guild, "scheduled_events", []) or [])

    boosts = getattr(guild, "premium_subscription_count", 0) or 0
    boost_level = getattr(guild, "premium_tier", 0) or 0

    return GuildStatistics(
        total_members=total_members,
        human_members=human_members,
        bot_members=bot_members,
        text_channels=text_channels,
        voice_channels=voice_channels,
        stage_channels=stage_channels,
        forum_channels=forum_channels,
        categories=categories,
        thread_channels=thread_channels,
        roles=roles,
        emoji_count=emoji_count,
        sticker_count=sticker_count,
        scheduled_events=scheduled_events,
        boosts=boosts,
        boost_level=boost_level,
    )


def process_resource_snapshot() -> dict[str, Any]:
    memory_mb: float | None = None
    try:
        import resource  # type: ignore

        usage = resource.getrusage(resource.RUSAGE_SELF)
        if sys.platform.startswith("darwin"):
            memory_mb = usage.ru_maxrss / (1024 * 1024)
        else:
            memory_mb = usage.ru_maxrss / 1024
    except (ImportError, AttributeError):
        memory_mb = None

    try:
        load_avg = os.getloadavg()
    except (AttributeError, OSError):
        load_avg = (None, None, None)

    return {
        "memory_mb": memory_mb,
        "load_average": load_avg,
    }


def format_timezone_display(tz: tzinfo, *, reference: datetime | None = None) -> str:
    if isinstance(tz, ZoneInfo):
        return tz.key
    reference = reference or datetime.now(dt_timezone.utc)
    offset = tz.utcoffset(reference)
    if offset is None:
        return str(tz)
    total_seconds = int(offset.total_seconds())
    sign = "+" if total_seconds >= 0 else "-"
    total_seconds = abs(total_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    return f"UTC{sign}{hours:02d}:{minutes:02d}"
