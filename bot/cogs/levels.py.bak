from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from bot.main import ForUS


class Levels(commands.GroupCog, name="level"):
    def __init__(self, bot: ForUS) -> None:
        super().__init__()
        self.bot = bot

    async def _ensure_repo(self, interaction: discord.Interaction) -> bool:
        if self.bot.level_repo is None:
            await interaction.response.send_message("Fitur level belum siap.", ephemeral=True)
            return False
        if not interaction.guild:
            await interaction.response.send_message("Perintah ini hanya tersedia di dalam server.", ephemeral=True)
            return False
        return True

    @app_commands.command(name="rank", description="Lihat level dan XP Anda atau pengguna lain.")
    async def rank(self, interaction: discord.Interaction, pengguna: discord.User | None = None) -> None:
        if not await self._ensure_repo(interaction):
            return
        assert interaction.guild is not None
        target = pengguna or interaction.user
        progress = await self.bot.level_repo.get_progress(interaction.guild.id, target.id)
        profile = progress.profile
        embed = discord.Embed(
            title=f"Level {target.display_name}",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Level", value=str(profile.level))
        embed.add_field(name="Total XP", value=str(profile.xp))
        embed.add_field(
            name="Progress",
            value=f"{progress.xp_into_level}/{progress.xp_for_next_level} XP (sisa {progress.xp_remaining})",
            inline=False,
        )
        embed.set_thumbnail(url=target.display_avatar.url if target.display_avatar else discord.Embed.Empty)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="Tampilkan papan level teratas.")
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        jumlah: app_commands.Range[int, 3, 20] = 10,
    ) -> None:
        if not await self._ensure_repo(interaction):
            return
        assert interaction.guild is not None
        records = await self.bot.level_repo.list_leaderboard(interaction.guild.id, int(jumlah))
        if not records:
            await interaction.response.send_message("Belum ada data level.")
            return
        lines: list[str] = []
        for index, record in enumerate(records, start=1):
            member = interaction.guild.get_member(record.user_id)
            name = member.display_name if member else f"Pengguna {record.user_id}"
            lines.append(f"**{index}.** {name} — Level {record.level} ({record.xp} XP)")
        embed = discord.Embed(title="Papan Level", description="\n".join(lines), color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    rewards = app_commands.Group(name="rewards", description="Kelola hadiah level")

    @rewards.command(name="set", description="Tetapkan role hadiah untuk level tertentu.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def rewards_set(
        self,
        interaction: discord.Interaction,
        level: app_commands.Range[int, 1, 200],
        role: discord.Role,
        sinkronisasi: bool = False,
    ) -> None:
        if not await self._ensure_repo(interaction):
            return
        assert interaction.guild is not None
        reward = await self.bot.level_repo.set_reward(interaction.guild.id, int(level), role.id)
        if sinkronisasi:
            profiles = await self.bot.level_repo.list_profiles_with_min_level(interaction.guild.id, reward.level)
            applied = 0
            for profile in profiles:
                member = interaction.guild.get_member(profile.user_id)
                if member and role not in member.roles:
                    try:
                        await member.add_roles(role, reason="Sinkronisasi hadiah level")
                        applied += 1
                    except discord.Forbidden:
                        continue
        else:
            applied = 0
        await interaction.response.send_message(
            f"Hadiah level {reward.level} diset ke {role.mention}. Role diberikan ke {applied} anggota.",
            ephemeral=True,
        )

    @rewards.command(name="remove", description="Hapus hadiah level yang ada.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def rewards_remove(
        self,
        interaction: discord.Interaction,
        level: app_commands.Range[int, 1, 200],
    ) -> None:
        if not await self._ensure_repo(interaction):
            return
        assert interaction.guild is not None
        removed = await self.bot.level_repo.remove_reward(interaction.guild.id, int(level))
        if not removed:
            await interaction.response.send_message("Tidak ada hadiah untuk level tersebut.", ephemeral=True)
            return
        await interaction.response.send_message("Hadiah level dihapus.", ephemeral=True)

    @rewards.command(name="list", description="Daftar role hadiah level yang terkonfigurasi.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def rewards_list(self, interaction: discord.Interaction) -> None:
        if not await self._ensure_repo(interaction):
            return
        assert interaction.guild is not None
        rewards = await self.bot.level_repo.list_rewards(interaction.guild.id)
        if not rewards:
            await interaction.response.send_message("Belum ada hadiah level.", ephemeral=True)
            return
        description = []
        for reward in rewards:
            role = interaction.guild.get_role(reward.role_id)
            role_name = role.mention if role else f"Role {reward.role_id} (tidak ditemukan)"
            description.append(f"Level {reward.level} → {role_name}")
        embed = discord.Embed(title="Hadiah Level", description="\n".join(description), color=discord.Color.gold())
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: ForUS) -> None:
    await bot.add_cog(Levels(bot))
