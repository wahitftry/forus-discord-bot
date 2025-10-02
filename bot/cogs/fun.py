from __future__ import annotations

import random
from typing import TYPE_CHECKING

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from bot.services.cache import TTLCache

if TYPE_CHECKING:
    from bot.main import ForUS


class Fun(commands.Cog):
    def __init__(self, bot: ForUS) -> None:
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.cache = TTLCache(ttl=120)

    async def cog_unload(self) -> None:
        await self.session.close()

    async def _fetch_json(self, url: str) -> object:
        async def _request() -> object:
            async with self.session.get(url, timeout=10) as resp:
                resp.raise_for_status()
                return await resp.json()

        cached = await self.cache.get(url)
        if cached:
            return cached  # type: ignore[return-value]
        data = await _request()
        await self.cache.set(url, data)
        return data

    @app_commands.command(name="meme", description="Menampilkan meme acak.")
    async def meme(self, interaction: discord.Interaction) -> None:
        data = await self._fetch_json("https://meme-api.com/gimme")
        embed = discord.Embed(title=data.get("title", "Meme"), color=discord.Color.random())
        if "url" in data:
            embed.set_image(url=str(data["url"]))
        embed.set_footer(text=f"Sumber: r/{data.get('subreddit', 'unknown')}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="quote", description="Kutipan motivasi acak.")
    async def quote(self, interaction: discord.Interaction) -> None:
        data = await self._fetch_json("https://zenquotes.io/api/random")
        if isinstance(data, list) and data:
            quote_data = data[0]
            quote = quote_data.get("q", "Tetap semangat!")
            author = quote_data.get("a", "Anonim")
        else:
            quote = "Teruslah melangkah meski perlahan."
            author = "Anonim"
        await interaction.response.send_message(f"“{quote}” — {author}")

    @app_commands.command(name="joke", description="Lelucon acak.")
    async def joke(self, interaction: discord.Interaction) -> None:
        data = await self._fetch_json("https://v2.jokeapi.dev/joke/Any?lang=es")
        if data.get("type") == "single":
            text = data.get("joke", "Saya tidak punya lelucon kali ini.")
        else:
            text = f"{data.get('setup', '')}\n\n{data.get('delivery', '')}".strip()
        await interaction.response.send_message(text)

    @app_commands.command(name="dice", description="Lempar dadu.")
    async def dice(self, interaction: discord.Interaction, sisi: app_commands.Range[int, 2, 100] = 6) -> None:
        hasil = random.randint(1, sisi)
        await interaction.response.send_message(f"🎲 Dadu {sisi} menghasilkan: **{hasil}**")

    @app_commands.command(name="8ball", description="Tanyakan sesuatu ke bola ajaib.")
    async def eight_ball(self, interaction: discord.Interaction, pertanyaan: str) -> None:
        jawaban = random.choice([
            "Pasti!",
            "Sepertinya iya.",
            "Coba lagi nanti.",
            "Saya ragu.",
            "Tidak mungkin.",
        ])
        await interaction.response.send_message(f"❓ {pertanyaan}\n🔮 {jawaban}")

    @app_commands.command(name="ship", description="Seberapa cocok dua orang?")
    async def ship(self, interaction: discord.Interaction, orang1: discord.User, orang2: discord.User) -> None:
        skor = random.randint(0, 100)
        hati = "❤️" * (skor // 20 + 1)
        await interaction.response.send_message(
            f"{orang1.mention} ❤️ {orang2.mention} = {skor}% {hati}"
        )


async def setup(bot: ForUS) -> None:
    await bot.add_cog(Fun(bot))
