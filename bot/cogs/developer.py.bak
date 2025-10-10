from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from bot.services.developers import DeveloperProfile, load_developer_profiles

if TYPE_CHECKING:
    from bot.main import ForUS


class Developer(commands.GroupCog, name="developer"):
    """Kumpulan perintah informasi developer bot."""

    def __init__(self, bot: ForUS) -> None:
        super().__init__()
        self.bot = bot
        self._profiles: list[DeveloperProfile] = load_developer_profiles()

    @property
    def profiles(self) -> list[DeveloperProfile]:
        if not self._profiles:
            self._profiles = load_developer_profiles()
        return self._profiles

    def _get_profile(self, developer_id: str | None) -> DeveloperProfile | None:
        if not self.profiles:
            return None
        if developer_id is None:
            return self.profiles[0]
        for profile in self.profiles:
            if profile.id == developer_id:
                return profile
        return None

    @staticmethod
    def _format_list(values: tuple[str, ...], empty: str = "Tidak tersedia") -> str:
        filtered = [value for value in values if value]
        if not filtered:
            return empty
        return "\n".join(f"• {value}" for value in filtered)

    @staticmethod
    def _format_mapping(mapping: dict[str, str], empty: str = "Tidak tersedia") -> str:
        if not mapping:
            return empty
        lines = []
        for key, value in mapping.items():
            lines.append(f"• **{key}**: {value}")
        return "\n".join(lines)

    def _build_profile_embed(self, profile: DeveloperProfile) -> discord.Embed:
        embed = discord.Embed(
            title=profile.display_name,
            description=profile.tagline,
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Discord", value=profile.discord_handle, inline=True)
        embed.add_field(name="Zona Waktu", value=profile.timezone or "-", inline=True)
        embed.add_field(name="Lokasi", value=profile.location or "-", inline=True)
        embed.add_field(name="Peran & Tanggung Jawab", value=self._format_list(profile.roles), inline=False)
        embed.add_field(name="Fokus Harian", value=self._format_list(profile.responsibilities), inline=False)
        embed.add_field(name="Stack Utama", value=self._format_list(profile.primary_stack), inline=False)
        embed.add_field(name="Tooling & Observability", value=self._format_list(profile.tooling), inline=False)
        embed.add_field(name="Highlight Karya", value=self._format_list(profile.highlights), inline=False)
        embed.add_field(name="Pencapaian", value=self._format_list(profile.achievements), inline=False)
        embed.add_field(name="Kontak", value=self._format_mapping(dict(profile.contact)), inline=False)
        embed.add_field(name="Link", value=self._format_mapping(dict(profile.links)), inline=False)
        embed.add_field(name="Jam Respons", value=self._format_mapping(dict(profile.availability)), inline=False)
        embed.add_field(name="Support Channel", value=self._format_list(profile.support_channels), inline=False)
        embed.add_field(name="Terbuka Untuk", value=self._format_list(profile.open_to), inline=False)
        embed.set_footer(text="Gunakan /ticket untuk dukungan lanjutan.")
        return embed

    @app_commands.command(name="profil", description="Detail lengkap developer ForUS.")
    @app_commands.describe(developer="ID developer. Kosongkan untuk melihat developer utama.")
    async def profile(self, interaction: discord.Interaction, developer: str | None = None) -> None:
        profile = self._get_profile(developer)
        if profile is None:
            await interaction.response.send_message(
                "Data developer belum tersedia. Hubungi admin server untuk info lebih lanjut.",
                ephemeral=True,
            )
            return
        embed = self._build_profile_embed(profile)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ringkasan", description="Ringkasan singkat setiap developer.")
    async def summary(self, interaction: discord.Interaction) -> None:
        if not self.profiles:
            await interaction.response.send_message(
                "Data developer belum tersedia. Hubungi admin server untuk info lebih lanjut.",
                ephemeral=True,
            )
            return
        embed = discord.Embed(
            title="Tim Pengembang ForUS",
            description="Gambaran singkat setiap kontributor inti.",
            color=discord.Color.brand_green(),
        )
        for profile in self.profiles:
            roles = ", ".join(profile.roles) if profile.roles else "-"
            stack = ", ".join(profile.primary_stack[:5]) if profile.primary_stack else "-"
            embed.add_field(
                name=profile.display_name,
                value=(
                    f"{profile.tagline}\n"
                    f"**Peran kunci:** {roles}\n"
                    f"**Stack inti:** {stack}\n"
                    f"**Hubungi:** {profile.discord_handle}"
                ),
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @profile.autocomplete("developer")
    async def profile_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        _ = interaction  # tidak digunakan
        current_lower = current.lower().strip()
        results: list[app_commands.Choice[str]] = []
        for profile in self.profiles:
            if not current_lower or current_lower in profile.display_name.lower() or current_lower in profile.id.lower():
                results.append(app_commands.Choice(name=profile.display_name, value=profile.id))
        return results[:25]


async def setup(bot: ForUS) -> None:
    await bot.add_cog(Developer(bot))
