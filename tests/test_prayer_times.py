from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import discord
from discord import app_commands
from discord.ext import commands
from zoneinfo import ZoneInfo

from bot.cogs.utility import Utility


@pytest.mark.asyncio()
async def test_jadwalsholat_indonesia_builds_embed(monkeypatch):
    bot = SimpleNamespace(latency=0.0, guilds=[], users=[], log=MagicMock())
    utility = Utility(bot)

    month_payload = {
        "lokasi": "KOTA KEDIRI",
        "daerah": "JAWA TIMUR",
        "jadwal": [
            {
                "date": "2024-06-03",
                "tanggal": "Senin, 03/06/2024",
                "imsak": "04:09",
                "subuh": "04:19",
                "terbit": "05:36",
                "dhuha": "06:05",
                "dzuhur": "11:34",
                "ashar": "14:53",
                "maghrib": "17:24",
                "isya": "18:38",
            }
        ],
    }

    monkeypatch.setattr(utility, "_fetch_month_indonesia", AsyncMock(return_value=month_payload))

    interaction = MagicMock()
    interaction.response = MagicMock()
    interaction.response.is_done.return_value = False
    interaction.response.send_message = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()

    choice = app_commands.Choice(name="Indonesia", value="indonesia")

    try:
        await Utility.jadwalsholat.callback(
            utility,
            interaction,
            choice,
            "1632",
            tahun=2024,
            bulan=6,
            tanggal=3,
        )
    finally:
        await utility.cog_unload()

    interaction.response.send_message.assert_awaited()
    kwargs = interaction.response.send_message.await_args.kwargs
    assert "embed" in kwargs
    embed = kwargs["embed"]
    fields = {field.name: field.value for field in embed.fields}
    assert fields["Subuh"] == "04:19"
    assert fields["Maghrib"] == "17:24"
    assert "ID Kota" in embed.footer.text


@pytest.mark.asyncio()
async def test_jadwalsholat_malaysia_builds_embed(monkeypatch):
    bot = SimpleNamespace(latency=0.0, guilds=[], users=[], log=MagicMock())
    utility = Utility(bot)

    tz = ZoneInfo("Asia/Kuala_Lumpur")
    def stamp(hour: int, minute: int) -> int:
        return int(datetime(2025, 6, 1, hour, minute, tzinfo=tz).timestamp())

    month_payload = {
        "zone": "SGR01",
        "zone_detail": {
            "jakimCode": "SGR01",
            "negeri": "Selangor",
            "daerah": "Gombak, Petaling, Sepang, Hulu Langat, Hulu Selangor, Shah Alam",
        },
        "prayers": [
            {
                "day": 1,
                "hijri": "1446-12-04",
                "fajr": stamp(5, 31),
                "syuruk": stamp(6, 47),
                "dhuhr": stamp(13, 12),
                "asr": stamp(16, 30),
                "maghrib": stamp(19, 24),
                "isha": stamp(20, 40),
            }
        ],
    }

    monkeypatch.setattr(utility, "_fetch_month_malaysia", AsyncMock(return_value=month_payload))

    interaction = MagicMock()
    interaction.response = MagicMock()
    interaction.response.is_done.return_value = False
    interaction.response.send_message = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()

    choice = app_commands.Choice(name="Malaysia", value="malaysia")

    try:
        await Utility.jadwalsholat.callback(
            utility,
            interaction,
            choice,
            "SGR01",
            tahun=2025,
            bulan=6,
            tanggal=1,
        )
    finally:
        await utility.cog_unload()

    interaction.response.send_message.assert_awaited()
    embed = interaction.response.send_message.await_args.kwargs["embed"]
    fields = {field.name: field.value for field in embed.fields}
    assert fields["Subuh"] == "05:31"
    assert fields["Maghrib"] == "19:24"
    assert fields["Isya"] == "20:40"
    assert any(field.name == "Tanggal Hijriah" for field in embed.fields)
    assert "Selangor" in embed.title
    assert "Gombak" in embed.description
    assert "SGR01" in embed.footer.text


@pytest.mark.asyncio()
async def test_jadwalsholat_rejects_invalid_month():
    bot = SimpleNamespace(latency=0.0, guilds=[], users=[], log=MagicMock())
    utility = Utility(bot)

    interaction = MagicMock()
    interaction.response = MagicMock()
    interaction.response.is_done.return_value = False
    interaction.response.send_message = AsyncMock()

    choice = app_commands.Choice(name="Indonesia", value="indonesia")

    try:
        await Utility.jadwalsholat.callback(
            utility,
            interaction,
            choice,
            "1632",
            tahun=2024,
            bulan=13,
            tanggal=1,
        )
    finally:
        await utility.cog_unload()

    interaction.response.send_message.assert_awaited()
    args = interaction.response.send_message.await_args
    assert "Bulan harus di antara 1-12." in args.args[0]
    assert args.kwargs.get("ephemeral") is True


@pytest.mark.asyncio()
async def test_jadwalsholat_command_registered_in_tree():
    intents = discord.Intents.none()
    bot = commands.Bot(command_prefix="!", intents=intents, application_id=123456789012345678)
    bot.log = MagicMock()

    cog = Utility(bot)
    try:
        await bot.add_cog(cog)
        command = bot.tree.get_command("jadwalsholat")
        assert command is not None
        assert command.description
    finally:
        await bot.remove_cog("Utility")
        await cog.session.close()
        await bot.close()


@pytest.mark.asyncio()
async def test_carijadwalsholat_indonesia_returns_embed(monkeypatch):
    bot = SimpleNamespace(latency=0.0, guilds=[], users=[], log=MagicMock())
    utility = Utility(bot)

    results = [
        {"id": "1632", "lokasi": "KOTA KEDIRI"},
        {"id": "1609", "lokasi": "KAB. KEDIRI"},
    ]

    monkeypatch.setattr(utility, "_search_indonesia_locations", AsyncMock(return_value=results))

    interaction = MagicMock()
    interaction.response = MagicMock()
    interaction.response.send_message = AsyncMock()

    choice = app_commands.Choice(name="Indonesia", value="indonesia")

    try:
        await Utility.carijadwalsholat.callback(
            utility,
            interaction,
            choice,
            keyword="kediri",
            batas=5,
        )
    finally:
        await utility.cog_unload()

    interaction.response.send_message.assert_awaited()
    kwargs = interaction.response.send_message.await_args.kwargs
    embed = kwargs["embed"]
    assert embed.fields[0].value == "ID Kota: `1632`"
    assert "kediri" in embed.fields[0].name.lower()


@pytest.mark.asyncio()
async def test_carijadwalsholat_no_results(monkeypatch):
    bot = SimpleNamespace(latency=0.0, guilds=[], users=[], log=MagicMock())
    utility = Utility(bot)

    monkeypatch.setattr(utility, "_search_malaysia_zones", AsyncMock(return_value=[]))

    interaction = MagicMock()
    interaction.response = MagicMock()
    interaction.response.send_message = AsyncMock()

    choice = app_commands.Choice(name="Malaysia", value="malaysia")

    try:
        await Utility.carijadwalsholat.callback(
            utility,
            interaction,
            choice,
            keyword="zon tidak ada",
            batas=5,
        )
    finally:
        await utility.cog_unload()

    interaction.response.send_message.assert_awaited()
    args = interaction.response.send_message.await_args
    assert "Tidak ada hasil" in args.args[0]
    assert args.kwargs.get("ephemeral") is True


@pytest.mark.asyncio()
async def test_jadwalsholat_autocomplete_indonesia(monkeypatch):
    bot = SimpleNamespace(latency=0.0, guilds=[], users=[], log=MagicMock())
    utility = Utility(bot)

    monkeypatch.setattr(
        utility,
        "_search_indonesia_locations",
        AsyncMock(return_value=[{"id": "1632", "lokasi": "KOTA KEDIRI"}]),
    )

    interaction = MagicMock()
    interaction.namespace = SimpleNamespace(negara=app_commands.Choice(name="Indonesia", value="indonesia"))

    try:
        choices = await Utility.jadwalsholat_lokasi_autocomplete(utility, interaction, "ked")
    finally:
        await utility.cog_unload()

    assert choices
    assert choices[0].value == "1632"
    assert "KOTA" in choices[0].name


@pytest.mark.asyncio()
async def test_jadwalsholat_autocomplete_malaysia(monkeypatch):
    bot = SimpleNamespace(latency=0.0, guilds=[], users=[], log=MagicMock())
    utility = Utility(bot)

    monkeypatch.setattr(
        utility,
        "_search_malaysia_zones",
        AsyncMock(return_value=[{"jakimCode": "SGR01", "negeri": "Selangor", "daerah": "Gombak"}]),
    )

    interaction = MagicMock()
    interaction.namespace = SimpleNamespace(negara=app_commands.Choice(name="Malaysia", value="malaysia"))

    try:
        choices = await Utility.jadwalsholat_lokasi_autocomplete(utility, interaction, "sgr")
    finally:
        await utility.cog_unload()

    assert choices
    assert choices[0].value == "SGR01"
    assert "Selangor" in choices[0].name or "SGR01" in choices[0].name
