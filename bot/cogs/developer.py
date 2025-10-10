from __future__ import annotations

from typing import TYPE_CHECKING

import interactions

from bot.services.developers import DeveloperProfile, load_developer_profiles

if TYPE_CHECKING:
    from bot.main import ForUS


class Developer(interactions.Extension):
    # MANUAL REVIEW: GroupCog -> Extension with slash_command group
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

    def _build_profile_embed(self, profile: DeveloperProfile) -> interactions.Embed:
        embed = interactions.Embed(
            title=profile.display_name,
            description=profile.tagline,
            color=interactions.Color.from_hex("#5865F2"),  # Discord blurple
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

    @interactions.slash_command(name='profil', description='Detail lengkap developer ForUS.')
    @interactions.slash_option(
        name="developer",
        description="ID developer. Kosongkan untuk melihat developer utama.",
        opt_type=interactions.OptionType.STRING,
        required=False,
        autocomplete=True,
    )
    async def profile(self, ctx: interactions.SlashContext, developer: str | None = None) -> None:
        profile = self._get_profile(developer)
        if profile is None:
            await ctx.send(
                "Data developer belum tersedia. Hubungi admin server untuk info lebih lanjut.",
                ephemeral=True,
            )
            return
        embed = self._build_profile_embed(profile)
        await ctx.send(embed=embed, ephemeral=True)

    @interactions.slash_command(name='ringkasan', description='Ringkasan singkat setiap developer.')
    async def summary(self, ctx: interactions.SlashContext) -> None:
        if not self.profiles:
            await ctx.send(
                "Data developer belum tersedia. Hubungi admin server untuk info lebih lanjut.",
                ephemeral=True,
            )
            return
        embed = interactions.Embed(
            title="Tim Pengembang ForUS",
            description="Gambaran singkat setiap kontributor inti.",
            color=interactions.Color.from_hex("#57F287"),
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
        await ctx.send(embed=embed, ephemeral=True)

    @profile.autocomplete("developer")
    async def profile_autocomplete(
        self,
        ctx: interactions.AutocompleteContext,
    ) -> None:
        current = ctx.input_text.strip().lower()
        results: list[interactions.SlashCommandChoice] = []
        for profile in self.profiles:
            if not current or current in profile.display_name.lower() or current in profile.id.lower():
                results.append(interactions.SlashCommandChoice(name=profile.display_name, value=profile.id))
                if len(results) >= 25:
                    break
        await ctx.send(choices=results)


def setup(bot: ForUS) -> None:
    Developer(bot)
