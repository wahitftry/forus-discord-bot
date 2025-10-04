from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping
import json


@dataclass(slots=True)
class DeveloperProfile:
    id: str
    display_name: str
    tagline: str
    discord_handle: str
    timezone: str
    location: str
    roles: tuple[str, ...]
    primary_stack: tuple[str, ...]
    tooling: tuple[str, ...]
    responsibilities: tuple[str, ...]
    achievements: tuple[str, ...]
    highlights: tuple[str, ...]
    contact: Mapping[str, str]
    links: Mapping[str, str]
    availability: Mapping[str, str]
    support_channels: tuple[str, ...]
    open_to: tuple[str, ...]

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "DeveloperProfile":
        def _tuple(value: Iterable[str] | None) -> tuple[str, ...]:
            if not value:
                return ()
            return tuple(str(item) for item in value)

        def _mapping(value: Mapping[str, Any] | None) -> Mapping[str, str]:
            if not value:
                return {}
            return {str(key): str(val) for key, val in value.items()}

        required_keys = [
            "id",
            "display_name",
            "tagline",
            "discord_handle",
        ]
        for key in required_keys:
            if key not in payload or not str(payload[key]).strip():
                raise ValueError(f"Kolom '{key}' wajib diisi pada data developer.")

        return cls(
            id=str(payload["id"]),
            display_name=str(payload["display_name"]),
            tagline=str(payload["tagline"]),
            discord_handle=str(payload["discord_handle"]),
            timezone=str(payload.get("timezone", "-")),
            location=str(payload.get("location", "-")),
            roles=_tuple(payload.get("roles")),
            primary_stack=_tuple(payload.get("primary_stack")),
            tooling=_tuple(payload.get("tooling")),
            responsibilities=_tuple(payload.get("responsibilities")),
            achievements=_tuple(payload.get("achievements")),
            highlights=_tuple(payload.get("highlights")),
            contact=_mapping(payload.get("contact")),
            links=_mapping(payload.get("links")),
            availability=_mapping(payload.get("availability")),
            support_channels=_tuple(payload.get("support_channels")),
            open_to=_tuple(payload.get("open_to")),
        )


def _default_data_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "developers.json"


@lru_cache(maxsize=8)
def _load_profiles(path: str) -> tuple[DeveloperProfile, ...]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File data developer tidak ditemukan: {file_path}")
    with file_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, list):
        raise ValueError("Struktur file developers.json harus berupa list.")
    profiles = [DeveloperProfile.from_mapping(item) for item in raw]
    return tuple(profiles)


def load_developer_profiles(path: Path | None = None) -> list[DeveloperProfile]:
    data_path = path or _default_data_path()
    profiles = _load_profiles(str(data_path))
    return list(profiles)


def clear_cache() -> None:
    _load_profiles.cache_clear()