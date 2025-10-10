from __future__ import annotations

from typing import TYPE_CHECKING

import interactions

from bot.services.automod import AutomodEngine
RULE_CHOICES: list[interactions.SlashCommandChoice] = [
    interactions.SlashCommandChoice(name="Filter Tautan", value="link_filter"),
    interactions.SlashCommandChoice(name="Batas Mention", value="mention_limit"),
    interactions.SlashCommandChoice(name="Huruf Kapital", value="caps"),
]


if TYPE_CHECKING:
    from bot.main import ForUS


class AutoMod(interactions.Extension):
    # MANUAL REVIEW: GroupCog -> Extension with slash_command group
    def __init__(self, bot: ForUS) -> None:
        super().__init__()
        self.bot = bot
        self.engine = AutomodEngine()

    async def _ensure_repo(self, ctx: interactions.SlashContext) -> bool:
        if self.bot.automod_repo is None or self.bot.audit_repo is None:
            await ctx.send("Repositori automod belum siap.", ephemeral=True)
            return False
        if not ctx.guild:
            await ctx.send("Perintah ini hanya bisa digunakan dalam server.", ephemeral=True)
            return False
        return True

    @interactions.slash_command(name='status', description='Lihat status aturan automod yang aktif.')
    async def status(self, ctx: interactions.SlashContext) -> None:
        if not await self._ensure_repo(interaction):
            return
        assert ctx.guild is not None
        rules = await self.bot.automod_repo.list_rules(ctx.guild.id)
        if not rules:
            await ctx.send("Belum ada aturan automod yang dikonfigurasi.", ephemeral=True)
            return
        embed = interactions.Embed(title="Status Automod", color=interactions.Color.orange())
        for rule in rules:
            state = "Aktif" if rule.is_active else "Nonaktif"
            payload_lines = [f"**{key}**: {value}" for key, value in rule.payload.items()]
            payload_desc = "\n".join(payload_lines) if payload_lines else "-"
            embed.add_field(name=f"{rule.rule_type}", value=f"Status: {state}\n{payload_desc}", inline=False)
        await ctx.send(embed=embed, ephemeral=True)

    @interactions.slash_command(name='disable', description='Nonaktifkan aturan automod tertentu.')
    @app_commands.choices(rule_type=RULE_CHOICES)
    async def disable(self, ctx: interactions.SlashContext, rule_type: app_commands.Choice[str]) -> None:
        if not await self._ensure_repo(interaction):
            return
        assert ctx.guild is not None
        existing = await self.bot.automod_repo.get_rule(ctx.guild.id, rule_type.value)
        if existing is None:
            await ctx.send("Aturan tersebut belum dikonfigurasi.", ephemeral=True)
            return
        await self.bot.automod_repo.set_active(ctx.guild.id, rule_type.value, False)
        await self.bot.audit_repo.add_entry(
            ctx.guild.id,
            action="automod.disable",
            actor_id=ctx.author.id,
            target_id=None,
            context=rule_type.value,
        )
        self.bot.dispatch("automod_rules_updated", ctx.guild.id)
        await ctx.send(f"Aturan `{rule_type.value}` dinonaktifkan.", ephemeral=True)

    @interactions.slash_command(name='link', description='Aktifkan atau atur filter tautan.')
    @app_commands.describe(
        aktif="Apakah filter tautan aktif",
        allow_domains="Daftar domain yang diizinkan (pisahkan dengan koma)",
    )
    async def link(
        self,
        ctx: interactions.SlashContext,
        aktif: bool,
        allow_domains: str | None = None,
    ) -> None:
        if not await self._ensure_repo(interaction):
            return
        assert ctx.guild is not None
        allowlist = []
        if allow_domains:
            allowlist = [item.strip().lower() for item in allow_domains.split(",") if item.strip()]
        payload = {"allow_domains": allowlist}
        await self.bot.automod_repo.set_rule(ctx.guild.id, "link_filter", payload, is_active=aktif)
        await self.bot.audit_repo.add_entry(
            ctx.guild.id,
            action="automod.link",
            actor_id=ctx.author.id,
            context=str(payload),
        )
        self.bot.dispatch("automod_rules_updated", ctx.guild.id)
        state = "aktif" if aktif else "nonaktif"
        await ctx.send(f"Filter tautan kini {state}.", ephemeral=True)

    @interactions.slash_command(name='mentionlimit', description='Batasi jumlah mention dalam satu pesan.')
    async def mentionlimit(
        self,
        ctx: interactions.SlashContext,
        maksimum: app_commands.Range[int, 1, 20],
    ) -> None:
        if not await self._ensure_repo(interaction):
            return
        assert ctx.guild is not None
        payload = {"max_mentions": int(maksimum)}
        await self.bot.automod_repo.set_rule(ctx.guild.id, "mention_limit", payload, is_active=True)
        await self.bot.audit_repo.add_entry(
            ctx.guild.id,
            action="automod.mentionlimit",
            actor_id=ctx.author.id,
            context=str(payload),
        )
        self.bot.dispatch("automod_rules_updated", ctx.guild.id)
        await ctx.send(
            f"Batas mention diset ke {int(maksimum)} per pesan.",
            ephemeral=True,
        )

    @interactions.slash_command(name='caps', description='Deteksi pesan yang terlalu banyak huruf kapital.')
    @app_commands.describe(
        threshold="Rasio huruf kapital (0.1-1.0)",
        min_length="Panjang minimal pesan untuk dicek",
    )
    async def caps(
        self,
        ctx: interactions.SlashContext,
        threshold: app_commands.Range[float, 0.1, 1.0],
        min_length: app_commands.Range[int, 5, 200] = 15,
    ) -> None:
        if not await self._ensure_repo(interaction):
            return
        assert ctx.guild is not None
        payload = {"threshold": float(threshold), "min_length": int(min_length)}
        await self.bot.automod_repo.set_rule(ctx.guild.id, "caps", payload, is_active=True)
        await self.bot.audit_repo.add_entry(
            ctx.guild.id,
            action="automod.caps",
            actor_id=ctx.author.id,
            context=str(payload),
        )
        self.bot.dispatch("automod_rules_updated", ctx.guild.id)
        await ctx.send(
            "Aturan deteksi huruf kapital diperbarui.",
            ephemeral=True,
        )


def setup(bot: ForUS) -> None:
    AutoMod(bot)
