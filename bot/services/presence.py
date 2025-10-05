from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import discord
from discord.ext import commands

from ..config import PresenceActivityConfig, RichPresenceConfig
from .logging import get_logger


@dataclass(slots=True)
class PresenceSnapshot:
    guild_count: int
    member_count: int
    human_count: int
    bot_count: int
    commands_count: int
    cog_count: int
    latency_ms: float
    shard_count: int
    scheduler_jobs: int
    pending_reminders: int
    owner_count: int
    uptime: timedelta
    database_connected: bool
    version: str

    @property
    def uptime_seconds(self) -> int:
        return int(self.uptime.total_seconds())

    def to_context(self) -> dict[str, Any]:
        uptime_human = _humanize_timedelta(self.uptime)
        return {
            "guild_count": self.guild_count,
            "member_count": self.member_count,
            "human_count": self.human_count,
            "bot_count": self.bot_count,
            "commands_count": self.commands_count,
            "cog_count": self.cog_count,
            "latency_ms": round(self.latency_ms, 2),
            "shard_count": self.shard_count,
            "scheduler_jobs": self.scheduler_jobs,
            "pending_reminders": self.pending_reminders,
            "owner_count": self.owner_count,
            "uptime_seconds": self.uptime_seconds,
            "uptime_human": uptime_human,
            "database_status": "🟢 tersambung" if self.database_connected else "🔴 putus",
            "version": self.version,
            "activity_pool": self.scheduler_jobs + self.pending_reminders,
        }


class RichPresenceManager:
    def __init__(self, bot: commands.Bot, config: RichPresenceConfig, *, version: str = "dev") -> None:
        self.bot = bot
        self.config = config
        self.version = version
        self.log = get_logger("RichPresence")
        self._task: asyncio.Task[None] | None = None
        self._current_index: int = 0
        self._refresh_event = asyncio.Event()
        self._refresh_event.set()
        self._last_snapshot: PresenceSnapshot | None = None

    def start(self) -> None:
        if not self.config.enabled:
            self.log.info("Rich presence dinonaktifkan lewat konfigurasi.")
            return
        if not self.config.activities:
            self.log.warning("Rich presence diaktifkan tetapi tidak ada aktivitas terdaftar.")
            return
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop(), name="forus-rich-presence")

    async def close(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

    def request_refresh(self) -> None:
        if not self.config.enabled:
            return
        self._refresh_event.set()

    async def _loop(self) -> None:
        await self.bot.wait_until_ready()
        self.log.info("Memulai loop rich presence (%d aktivitas, interval %d detik)", len(self.config.activities), self.config.rotation_seconds)
        timeout = max(5, self.config.rotation_seconds)
        while not self.bot.is_closed():
            await self._apply_next_presence()
            try:
                await asyncio.wait_for(self._refresh_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                continue
            else:
                self._refresh_event.clear()

    async def _apply_next_presence(self) -> None:
        template = self._pick_next_activity()
        context = await self._build_context()
        name = _format_template(template.text, context)
        details = _format_template(template.details, context)
        state = _format_template(template.state, context)
        status = _resolve_status(template.status) or _resolve_status(self.config.default_status)
        try:
            activity = _build_activity(template, name, details, state)
        except Exception:  # noqa: BLE001
            self.log.exception("Gagal membuat aktivitas rich presence dari template %s", template.type)
            return

        try:
            await self.bot.change_presence(activity=activity, status=status)
        except Exception:  # noqa: BLE001
            self.log.exception("Gagal memperbarui rich presence menjadi '%s'", name)

    def _pick_next_activity(self) -> PresenceActivityConfig:
        total = len(self.config.activities)
        if total == 0:
            raise RuntimeError("Tidak ada aktivitas rich presence yang tersedia.")
        template = self.config.activities[self._current_index % total]
        self._current_index = (self._current_index + 1) % total
        return template

    async def _build_context(self) -> dict[str, Any]:
        snapshot = await self._collect_snapshot()
        self._last_snapshot = snapshot
        base_context = snapshot.to_context()
        base_context.update({
            "activity_index": (self._current_index or len(self.config.activities)) ,
            "activity_total": len(self.config.activities),
        })
        return base_context

    async def _collect_snapshot(self) -> PresenceSnapshot:
        guilds = list(getattr(self.bot, "guilds", []))
        guild_count = len(guilds)
        total_members = 0
        human_members = 0
        bot_members = 0
        for guild in guilds:
            total, human, bots = _resolve_guild_counts(guild)
            total_members += total
            human_members += human
            bot_members += bots

        commands_count = 0
        try:
            commands_count = len(self.bot.tree.get_commands())  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            commands_count = 0

        cog_count = len(getattr(self.bot, "cogs", {}))

        latency = float(getattr(self.bot, "latency", 0.0) or 0.0) * 1000
        shard_count = int(getattr(self.bot, "shard_count", 1) or 1)

        scheduler = getattr(self.bot, "scheduler", None)
        scheduler_jobs = scheduler.job_count() if scheduler is not None else 0

        pending_reminders = await _count_pending_reminders(getattr(self.bot, "reminder_repo", None))

        owner_ids = getattr(getattr(self.bot, "config", None), "owner_ids", []) or []
        owner_count = len(owner_ids)

        started_at: Optional[datetime] = getattr(self.bot, "started_at", None)
        if started_at is None:
            uptime = timedelta()
        else:
            now = datetime.now(timezone.utc)
            uptime = now - started_at

        database_connected = getattr(self.bot, "db", None) is not None

        return PresenceSnapshot(
            guild_count=guild_count,
            member_count=total_members,
            human_count=human_members or max(total_members - bot_members, 0),
            bot_count=bot_members,
            commands_count=commands_count,
            cog_count=cog_count,
            latency_ms=latency,
            shard_count=shard_count,
            scheduler_jobs=scheduler_jobs,
            pending_reminders=pending_reminders,
            owner_count=owner_count,
            uptime=uptime,
            database_connected=database_connected,
            version=self.version,
        )

    @property
    def last_snapshot(self) -> PresenceSnapshot | None:
        return self._last_snapshot


def _resolve_status(value: Optional[str]) -> discord.Status | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    mapping = {
        "online": discord.Status.online,
        "idle": discord.Status.idle,
        "dnd": discord.Status.do_not_disturb,
        "do_not_disturb": discord.Status.do_not_disturb,
        "busy": discord.Status.do_not_disturb,
        "away": discord.Status.idle,
        "invisible": discord.Status.invisible,
        "offline": discord.Status.offline,
    }
    return mapping.get(normalized, discord.Status.online)


def _build_activity(template: PresenceActivityConfig, name: str, details: Optional[str], state: Optional[str]) -> discord.BaseActivity:
    activity_type = (template.type or "playing").lower()
    if activity_type == "streaming":
        return discord.Streaming(name=name, url=template.url or "https://twitch.tv")
    if activity_type == "custom":
        emoji = None
        if template.emoji:
            try:
                emoji = discord.PartialEmoji.from_str(template.emoji)
            except Exception:  # noqa: BLE001
                emoji = None
        return discord.CustomActivity(name=name, emoji=emoji)

    mapped = _activity_mapping().get(activity_type, discord.ActivityType.playing)
    kwargs: dict[str, Any] = {"name": name, "type": mapped}
    if template.url and mapped is discord.ActivityType.streaming:
        kwargs["url"] = template.url
    if details:
        kwargs["details"] = details
    if state:
        kwargs["state"] = state
    return discord.Activity(**kwargs)


_activity_map_cache: dict[str, discord.ActivityType] | None = None


def _activity_mapping() -> dict[str, discord.ActivityType]:
    global _activity_map_cache
    if _activity_map_cache is None:
        _activity_map_cache = {
            "playing": discord.ActivityType.playing,
            "watching": discord.ActivityType.watching,
            "listening": discord.ActivityType.listening,
            "competing": discord.ActivityType.competing,
            "streaming": discord.ActivityType.streaming,
        }
    return _activity_map_cache


async def _count_pending_reminders(repository: Any) -> int:
    if repository is None:
        return 0
    try:
        pending = await repository.all_pending()
    except Exception:  # noqa: BLE001
        return 0
    return len(pending)


def _resolve_guild_counts(guild: Any) -> tuple[int, int, int]:
    total = getattr(guild, "member_count", None)
    members = getattr(guild, "members", None)
    members_list = list(members) if members else []
    if total is None or total <= 0:
        total = len(members_list)
    bot_members = sum(1 for member in members_list if getattr(member, "bot", False))
    human_members = len(members_list) - bot_members if members_list else max((total or 0) - bot_members, 0)
    return int(total or 0), int(max(human_members, 0)), int(bot_members)


def _format_template(template: Optional[str], context: dict[str, Any]) -> str:
    if not template:
        return ""
    formatter = _PresenceDict(context)
    return template.format_map(formatter)


class _PresenceDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _humanize_timedelta(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        total_seconds = 0

    if total_seconds == 0:
        return "baru saja"

    units = [
        ("hari", 86_400),
        ("jam", 3_600),
        ("menit", 60),
        ("detik", 1),
    ]

    parts: list[str] = []
    remainder = total_seconds
    for label, size in units:
        value, remainder = divmod(remainder, size)
        if value:
            parts.append(f"{value} {label}")
        if len(parts) == 2:
            break

    return " ".join(parts)