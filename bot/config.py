from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import os


@dataclass(slots=True)
class BotConfig:
    token: str
    guild_ids: list[int] = field(default_factory=list)
    database_url: str = "sqlite+aiosqlite:///./bot.db"
    log_level: str = "INFO"
    owner_ids: list[int] = field(default_factory=list)


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

    return BotConfig(
        token=token,
        guild_ids=guild_ids,
        database_url=db_url,
        log_level=log_level.upper(),
        owner_ids=owner_ids,
    )
