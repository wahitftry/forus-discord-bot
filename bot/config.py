from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
import os


def _env_bool(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    normalized = value.strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def _clean_optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    candidate = str(value).strip()
    return candidate or None


@dataclass(slots=True)
class PresenceActivityConfig:
    type: str
    text: str
    status: Optional[str] = None
    url: Optional[str] = None
    emoji: Optional[str] = None
    details: Optional[str] = None
    state: Optional[str] = None


@dataclass(slots=True)
class RichPresenceConfig:
    enabled: bool = True
    rotation_seconds: int = 45
    default_status: str = "online"
    activities: list[PresenceActivityConfig] = field(default_factory=list)


_DEFAULT_PRESENCE_CONFIG: dict[str, Any] = {
    "enabled": True,
    "rotation_seconds": 45,
    "status": "online",
    "activities": [
        {
            "type": "watching",
            "text": "👁️ {guild_count} server • {member_count} anggota aktif",
        },
        {
            "type": "listening",
            "text": "🎧 /help • {commands_count} perintah terpasang",
        },
        {
            "type": "playing",
            "text": "🛠️ ForUS v{version} • uptime {uptime_human}",
        },
        {
            "type": "competing",
            "text": "⚔️ {scheduler_jobs} jadwal • {pending_reminders} pengingat",
        },
        {
            "type": "custom",
            "text": "🚀 Dikelola {owner_count} developer • {database_status}",
            "status": "idle",
            "emoji": "🚀",
        },
        {
            "type": "streaming",
            "text": "🔴 Liputan event komunitas • shard {shard_count}",
            "url": "https://twitch.tv/foruscommunity",
        },
    ],
}


def _parse_presence_activities(data: Any) -> list[PresenceActivityConfig]:
    activities: list[PresenceActivityConfig] = []
    if not isinstance(data, list):
        return activities

    for raw in data:
        if not isinstance(raw, dict):
            continue
        text = _clean_optional_str(raw.get("text"))
        if not text:
            continue
        activity_type = _clean_optional_str(raw.get("type")) or "playing"
        activities.append(
            PresenceActivityConfig(
                type=activity_type.lower(),
                text=text,
                status=_clean_optional_str(raw.get("status")),
                url=_clean_optional_str(raw.get("url")),
                emoji=_clean_optional_str(raw.get("emoji")),
                details=_clean_optional_str(raw.get("details")),
                state=_clean_optional_str(raw.get("state")),
            )
        )

    return activities


def _load_presence_config(base_path: Path | None) -> RichPresenceConfig:
    config_data: dict[str, Any] = dict(_DEFAULT_PRESENCE_CONFIG)
    activities_override: list[dict[str, Any]] | None = None

    if base_path and base_path.exists():
        try:
            with base_path.open("r", encoding="utf-8") as fp:
                file_data = json.load(fp)
            if isinstance(file_data, dict):
                config_data.update({k: v for k, v in file_data.items() if v is not None})
        except (OSError, json.JSONDecodeError):
            pass

    env_json = _clean_optional_str(os.getenv("PRESENCE_ACTIVITIES_JSON"))
    if env_json:
        try:
            decoded = json.loads(env_json)
            if isinstance(decoded, list):
                activities_override = decoded  # type: ignore[assignment]
        except json.JSONDecodeError:
            pass

    enabled = _env_bool("PRESENCE_ENABLED", bool(config_data.get("enabled", True)))
    rotation_env = _clean_optional_str(os.getenv("PRESENCE_ROTATION_SECONDS"))
    default_rotation = int(config_data.get("rotation_seconds", 45) or 45)
    try:
        rotation = int(rotation_env) if rotation_env is not None else default_rotation
    except ValueError:
        rotation = default_rotation
    rotation = max(10, rotation)

    status_env = _clean_optional_str(os.getenv("PRESENCE_STATUS"))
    default_status = _clean_optional_str(config_data.get("status")) or "online"
    merged_status = (status_env or default_status).lower()

    activities_raw = activities_override if activities_override is not None else config_data.get("activities")
    activities = _parse_presence_activities(activities_raw)
    if not activities:
        activities = _parse_presence_activities(_DEFAULT_PRESENCE_CONFIG.get("activities"))

    return RichPresenceConfig(
        enabled=enabled,
        rotation_seconds=rotation,
        default_status=merged_status,
        activities=activities,
    )


@dataclass(slots=True)
class BotConfig:
    token: str
    guild_ids: list[int] = field(default_factory=list)
    database_url: str = "sqlite+aiosqlite:///./bot.db"
    log_level: str = "INFO"
    owner_ids: list[int] = field(default_factory=list)
    bot_version: str = "dev"
    presence: RichPresenceConfig = field(default_factory=RichPresenceConfig)


def load_config(env_path: Optional[Path] = None) -> BotConfig:
    """Memuat konfigurasi bot dari file .env atau environment."""
    if env_path is None:
        env_path = Path(".env")

    if env_path.exists():
        load_dotenv(env_path)

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN tidak ditemukan. Tambahkan pada file .env atau environment variable.")

    raw_guilds = os.getenv("DISCORD_GUILD_IDS", "")
    guild_ids = [int(item.strip()) for item in raw_guilds.split(",") if item.strip()]

    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db")
    log_level = os.getenv("LOG_LEVEL", "INFO")

    raw_owner_ids = os.getenv("OWNER_IDS", "")
    owner_ids = [int(item.strip()) for item in raw_owner_ids.split(",") if item.strip()]

    version = os.getenv("BOT_VERSION", "dev").strip() or "dev"

    presence_path_env = _clean_optional_str(os.getenv("PRESENCE_CONFIG_PATH"))
    presence_path = Path(presence_path_env) if presence_path_env else Path("bot/data/presence.json")
    presence_config = _load_presence_config(presence_path)

    return BotConfig(
        token=token,
        guild_ids=guild_ids,
        database_url=db_url,
        log_level=log_level.upper(),
        owner_ids=owner_ids,
        bot_version=version,
        presence=presence_config,
    )
