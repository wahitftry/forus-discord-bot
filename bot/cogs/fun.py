from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING

import aiohttp
import interactions

from bot.services.cache import TTLCache

if TYPE_CHECKING:
    from bot.main import ForUS


class Fun(interactions.Extension):
    def __init__(self, bot: ForUS) -> None:
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.cache = TTLCache(ttl=120)

    def drop(self) -> None:
        """Called when extension is unloaded"""
        asyncio.create_task(self.session.close())

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

    @interactions.slash_command(name="meme", description="Menampilkan meme acak.")
    async def meme(self, ctx: interactions.SlashContext) -> None:
        data = await self._fetch_json("https://meme-api.com/gimme")
        embed = interactions.Embed(title=data.get("title", "Meme"), color=interactions.Color.random())
        if "url" in data:
            embed.set_image(url=str(data["url"]))
        embed.set_footer(text=f"Sumber: r/{data.get('subreddit', 'unknown')}")
        await ctx.send(embed=embed)

    @interactions.slash_command(name="quote", description="Kutipan motivasi acak.")
    async def quote(self, ctx: interactions.SlashContext) -> None:
        data = await self._fetch_json("https://zenquotes.io/api/random")
        if isinstance(data, list) and data:
            quote_data = data[0]
            quote = quote_data.get("q", "Tetap semangat!")
            author = quote_data.get("a", "Anonim")
        else:
            quote = "Teruslah melangkah meski perlahan."
            author = "Anonim"
        await ctx.send(f'"{quote}" — {author}')

    @interactions.slash_command(name="joke", description="Lelucon acak.")
    async def joke(self, ctx: interactions.SlashContext) -> None:
        data = await self._fetch_json("https://v2.jokeapi.dev/joke/Any?lang=en")
        if data.get("type") == "single":
            text = data.get("joke", "Saya tidak punya lelucon kali ini.")
        else:
            text = f"{data.get('setup', '')}\n\n{data.get('delivery', '')}".strip()
        await ctx.send(text)

    @interactions.slash_command(name="dice", description="Lempar dadu.")
    @interactions.slash_option(
        name="sisi",
        description="Jumlah sisi dadu (2-100)",
        opt_type=interactions.OptionType.INTEGER,
        min_value=2,
        max_value=100,
        required=False,
    )
    async def dice(self, ctx: interactions.SlashContext, sisi: int = 6) -> None:
        hasil = random.randint(1, sisi)
        await ctx.send(f"🎲 Dadu {sisi} menghasilkan: **{hasil}**")

    @interactions.slash_command(name="8ball", description="Tanyakan sesuatu ke bola ajaib.")
    @interactions.slash_option(
        name="pertanyaan",
        description="Pertanyaan Anda",
        opt_type=interactions.OptionType.STRING,
        required=True,
    )
    async def eight_ball(self, ctx: interactions.SlashContext, pertanyaan: str) -> None:
        jawaban = random.choice([
            "Pasti!",
            "Sepertinya iya.",
            "Coba lagi nanti.",
            "Saya ragu.",
            "Tidak mungkin.",
        ])
        await ctx.send(f"❓ {pertanyaan}\n🔮 {jawaban}")

    @interactions.slash_command(name="ship", description="Seberapa cocok dua orang?")
    @interactions.slash_option(
        name="orang1",
        description="Orang pertama",
        opt_type=interactions.OptionType.USER,
        required=True,
    )
    @interactions.slash_option(
        name="orang2",
        description="Orang kedua",
        opt_type=interactions.OptionType.USER,
        required=True,
    )
    async def ship(self, ctx: interactions.SlashContext, orang1: interactions.User, orang2: interactions.User) -> None:
        skor = random.randint(0, 100)
        hati = "❤️" * (skor // 20 + 1)
        await ctx.send(
            f"{orang1.mention} ❤️ {orang2.mention} = {skor}% {hati}"
        )


def setup(bot: ForUS) -> None:
    Fun(bot)
