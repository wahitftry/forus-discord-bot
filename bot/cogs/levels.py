from __future__ import annotations

from typing import TYPE_CHECKING

import interactions

if TYPE_CHECKING:
    from bot.main import ForUS


class Levels(interactions.Extension):
    # MANUAL REVIEW: GroupCog -> Extension with slash_command group
    def __init__(self, bot: ForUS) -> None:
        super().__init__()
        self.bot = bot

    async def _ensure_repo(self, ctx: interactions.SlashContext) -> bool:
        if self.bot.level_repo is None:
            await ctx.send("Fitur level belum siap.", ephemeral=True)
            return False
        if not ctx.guild:
            await ctx.send("Perintah ini hanya tersedia di dalam server.", ephemeral=True)
            return False
        return True

    @interactions.slash_command(name='rank', description='Lihat level dan XP Anda atau pengguna lain.')
    async def rank(self, ctx: interactions.SlashContext, pengguna: interactions.User | None = None) -> None:
        if not await self._ensure_repo(interaction):
            return
        assert ctx.guild is not None
        target = pengguna or ctx.author
        progress = await self.bot.level_repo.get_progress(ctx.guild.id, target.id)
        profile = progress.profile
        embed = interactions.Embed(
            title=f"Level {target.display_name}",
            color=interactions.Color.from_hex("#5865F2"),  # Discord blurple
        )
        embed.add_field(name="Level", value=str(profile.level))
        embed.add_field(name="Total XP", value=str(profile.xp))
        embed.add_field(
            name="Progress",
            value=f"{progress.xp_into_level}/{progress.xp_for_next_level} XP (sisa {progress.xp_remaining})",
            inline=False,
        )
        embed.set_thumbnail(url=target.display_avatar.url if target.display_avatar else interactions.Embed.Empty)
        await ctx.send(embed=embed)

    @interactions.slash_command(name='leaderboard', description='Tampilkan papan level teratas.')
    async def leaderboard(
        self,
        ctx: interactions.SlashContext,
        jumlah: app_commands.Range[int, 3, 20] = 10,
    ) -> None:
        if not await self._ensure_repo(interaction):
            return
        assert ctx.guild is not None
        records = await self.bot.level_repo.list_leaderboard(ctx.guild.id, int(jumlah))
        if not records:
            await ctx.send("Belum ada data level.")
            return
        lines: list[str] = []
        for index, record in enumerate(records, start=1):
            member = ctx.guild.get_member(record.user_id)
            name = member.display_name if member else f"Pengguna {record.user_id}"
            lines.append(f"**{index}.** {name} — Level {record.level} ({record.xp} XP)")
        embed = interactions.Embed(title="Papan Level", description="\n".join(lines), color=interactions.Color.from_hex("#2ECC71"))
        await ctx.send(embed=embed)

    @interactions.slash_command(
        name="level",
        description="Level commands",
        sub_cmd_name="rewards_set",
        sub_cmd_description="Tetapkan role hadiah untuk level tertentu.",
        default_member_permissions=interactions.Permissions.MANAGE_ROLES,
    )
    @interactions.slash_option(
        name="level",
        description="Level untuk hadiah (1-200)",
        opt_type=interactions.OptionType.INTEGER,
        min_value=1,
        max_value=200,
        required=True,
    )
    @interactions.slash_option(
        name="role",
        description="Role yang diberikan",
        opt_type=interactions.OptionType.ROLE,
        required=True,
    )
    @interactions.slash_option(
        name="sinkronisasi",
        description="Berikan role ke member yang sudah mencapai level",
        opt_type=interactions.OptionType.BOOLEAN,
        required=False,
    )
    async def rewards_set(
        self,
        ctx: interactions.SlashContext,
        level: int,
        role: interactions.Role,
        sinkronisasi: bool = False,
    ) -> None:
        if not await self._ensure_repo(interaction):
            return
        assert ctx.guild is not None
        reward = await self.bot.level_repo.set_reward(ctx.guild.id, int(level), role.id)
        if sinkronisasi:
            profiles = await self.bot.level_repo.list_profiles_with_min_level(ctx.guild.id, reward.level)
            applied = 0
            for profile in profiles:
                member = ctx.guild.get_member(profile.user_id)
                if member and role not in member.roles:
                    try:
                        await member.add_roles(role, reason="Sinkronisasi hadiah level")
                        applied += 1
                    except interactions.errors.Forbidden:
                        continue
        else:
            applied = 0
        await ctx.send(
            f"Hadiah level {reward.level} diset ke {role.mention}. Role diberikan ke {applied} anggota.",
            ephemeral=True,
        )

    @interactions.slash_command(
        name="level",
        description="Level commands",
        sub_cmd_name="rewards_remove",
        sub_cmd_description="Hapus hadiah level yang ada.",
        default_member_permissions=interactions.Permissions.MANAGE_ROLES,
    )
    @interactions.slash_option(
        name="level",
        description="Level untuk dihapus hadiahnya (1-200)",
        opt_type=interactions.OptionType.INTEGER,
        min_value=1,
        max_value=200,
        required=True,
    )
    async def rewards_remove(
        self,
        ctx: interactions.SlashContext,
        level: int,
    ) -> None:
        if not await self._ensure_repo(interaction):
            return
        assert ctx.guild is not None
        removed = await self.bot.level_repo.remove_reward(ctx.guild.id, int(level))
        if not removed:
            await ctx.send("Tidak ada hadiah untuk level tersebut.", ephemeral=True)
            return
        await ctx.send("Hadiah level dihapus.", ephemeral=True)

    @interactions.slash_command(
        name="level",
        description="Level commands",
        sub_cmd_name="rewards_list",
        sub_cmd_description="Daftar role hadiah level yang terkonfigurasi.",
        default_member_permissions=interactions.Permissions.MANAGE_ROLES,
    )
    async def rewards_list(self, ctx: interactions.SlashContext) -> None:
        if not await self._ensure_repo(interaction):
            return
        assert ctx.guild is not None
        rewards = await self.bot.level_repo.list_rewards(ctx.guild.id)
        if not rewards:
            await ctx.send("Belum ada hadiah level.", ephemeral=True)
            return
        description = []
        for reward in rewards:
            role = ctx.guild.get_role(reward.role_id)
            role_name = role.mention if role else f"Role {reward.role_id} (tidak ditemukan)"
            description.append(f"Level {reward.level} → {role_name}")
        embed = interactions.Embed(title="Hadiah Level", description="\n".join(description), color=interactions.Color.from_hex("#F1C40F"))
        await ctx.send(embed=embed, ephemeral=True)


def setup(bot: ForUS) -> None:
    Levels(bot)
