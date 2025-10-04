from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bot.cogs.developer import Developer
from bot.services import developers


def test_load_developer_profiles_returns_data():
    developers.clear_cache()
    profiles = developers.load_developer_profiles()
    assert profiles, "Profil developer kosong"
    primary = profiles[0]
    assert primary.id == "wahitftry"
    assert any("Python" in item for item in primary.primary_stack)


@pytest.mark.asyncio()
async def test_developer_embed_contains_key_sections():
    developers.clear_cache()
    bot = MagicMock()
    cog = Developer(bot)
    profile = cog.profiles[0]
    embed = cog._build_profile_embed(profile)

    field_map = {field.name: field.value for field in embed.fields}

    assert embed.title == profile.display_name
    assert "Stack Utama" in field_map and "Python" in field_map["Stack Utama"]
    assert "Kontak" in field_map and "support@forus.bot" in field_map["Kontak"]
    assert "Support Channel" in field_map and "ticket" in field_map["Support Channel"].lower()