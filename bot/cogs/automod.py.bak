from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from bot.services.automod import AutomodEngine
RULE_CHOICES: list[app_commands.Choice[str]] = [
    app_commands.Choice(name="Filter Tautan", value="link_filter"),
    app_commands.Choice(name="Batas Mention", value="mention_limit"),
    app_commands.Choice(name="Huruf Kapital", value="caps"),
]


if TYPE_CHECKING:
    from bot.main import ForUS


@app_commands.default_permissions(manage_guild=True)
class AutoMod(commands.GroupCog, name="automod"):
    def __init__(self, bot: ForUS) -> None:
        super().__init__()
        self.bot = bot
        self.engine = AutomodEngine()

    async def _ensure_repo(self, interaction: discord.Interaction) -> bool:
        if self.bot.automod_repo is None or self.bot.audit_repo is None:
            await interaction.response.send_message("Repositori automod belum siap.", ephemeral=True)
            return False
        if not interaction.guild:
            await interaction.response.send_message("Perintah ini hanya bisa digunakan dalam server.", ephemeral=True)
            return False
        return True

    @app_commands.command(name="status", description="Lihat status aturan automod yang aktif.")
    async def status(self, interaction: discord.Interaction) -> None:
        if not await self._ensure_repo(interaction):
            return
        assert interaction.guild is not None
        rules = await self.bot.automod_repo.list_rules(interaction.guild.id)
        if not rules:
            await interaction.response.send_message("Belum ada aturan automod yang dikonfigurasi.", ephemeral=True)
            return
        embed = discord.Embed(title="Status Automod", color=discord.Color.orange())
        for rule in rules:
            state = "Aktif" if rule.is_active else "Nonaktif"
            payload_lines = [f"**{key}**: {value}" for key, value in rule.payload.items()]
            payload_desc = "\n".join(payload_lines) if payload_lines else "-"
            embed.add_field(name=f"{rule.rule_type}", value=f"Status: {state}\n{payload_desc}", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="disable", description="Nonaktifkan aturan automod tertentu.")
    @app_commands.choices(rule_type=RULE_CHOICES)
    async def disable(self, interaction: discord.Interaction, rule_type: app_commands.Choice[str]) -> None:
        if not await self._ensure_repo(interaction):
            return
        assert interaction.guild is not None
        existing = await self.bot.automod_repo.get_rule(interaction.guild.id, rule_type.value)
        if existing is None:
            await interaction.response.send_message("Aturan tersebut belum dikonfigurasi.", ephemeral=True)
            return
        await self.bot.automod_repo.set_active(interaction.guild.id, rule_type.value, False)
        await self.bot.audit_repo.add_entry(
            interaction.guild.id,
            action="automod.disable",
            actor_id=interaction.user.id,
            target_id=None,
            context=rule_type.value,
        )
        self.bot.dispatch("automod_rules_updated", interaction.guild.id)
        await interaction.response.send_message(f"Aturan `{rule_type.value}` dinonaktifkan.", ephemeral=True)

    @app_commands.command(name="link", description="Aktifkan atau atur filter tautan.")
    @app_commands.describe(
        aktif="Apakah filter tautan aktif",
        allow_domains="Daftar domain yang diizinkan (pisahkan dengan koma)",
    )
    async def link(
        self,
        interaction: discord.Interaction,
        aktif: bool,
        allow_domains: str | None = None,
    ) -> None:
        if not await self._ensure_repo(interaction):
            return
        assert interaction.guild is not None
        allowlist = []
        if allow_domains:
            allowlist = [item.strip().lower() for item in allow_domains.split(",") if item.strip()]
        payload = {"allow_domains": allowlist}
        await self.bot.automod_repo.set_rule(interaction.guild.id, "link_filter", payload, is_active=aktif)
        await self.bot.audit_repo.add_entry(
            interaction.guild.id,
            action="automod.link",
            actor_id=interaction.user.id,
            context=str(payload),
        )
        self.bot.dispatch("automod_rules_updated", interaction.guild.id)
        state = "aktif" if aktif else "nonaktif"
        await interaction.response.send_message(f"Filter tautan kini {state}.", ephemeral=True)

    @app_commands.command(name="mentionlimit", description="Batasi jumlah mention dalam satu pesan.")
    async def mentionlimit(
        self,
        interaction: discord.Interaction,
        maksimum: app_commands.Range[int, 1, 20],
    ) -> None:
        if not await self._ensure_repo(interaction):
            return
        assert interaction.guild is not None
        payload = {"max_mentions": int(maksimum)}
        await self.bot.automod_repo.set_rule(interaction.guild.id, "mention_limit", payload, is_active=True)
        await self.bot.audit_repo.add_entry(
            interaction.guild.id,
            action="automod.mentionlimit",
            actor_id=interaction.user.id,
            context=str(payload),
        )
        self.bot.dispatch("automod_rules_updated", interaction.guild.id)
        await interaction.response.send_message(
            f"Batas mention diset ke {int(maksimum)} per pesan.",
            ephemeral=True,
        )

    @app_commands.command(name="caps", description="Deteksi pesan yang terlalu banyak huruf kapital.")
    @app_commands.describe(
        threshold="Rasio huruf kapital (0.1-1.0)",
        min_length="Panjang minimal pesan untuk dicek",
    )
    async def caps(
        self,
        interaction: discord.Interaction,
        threshold: app_commands.Range[float, 0.1, 1.0],
        min_length: app_commands.Range[int, 5, 200] = 15,
    ) -> None:
        if not await self._ensure_repo(interaction):
            return
        assert interaction.guild is not None
        payload = {"threshold": float(threshold), "min_length": int(min_length)}
        await self.bot.automod_repo.set_rule(interaction.guild.id, "caps", payload, is_active=True)
        await self.bot.audit_repo.add_entry(
            interaction.guild.id,
            action="automod.caps",
            actor_id=interaction.user.id,
            context=str(payload),
        )
        self.bot.dispatch("automod_rules_updated", interaction.guild.id)
        await interaction.response.send_message(
            "Aturan deteksi huruf kapital diperbarui.",
            ephemeral=True,
        )


async def setup(bot: ForUS) -> None:
    await bot.add_cog(AutoMod(bot))
