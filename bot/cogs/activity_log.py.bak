from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot.services.activity_logger import ACTIVITY_LOG_CATEGORIES, ActivityLogger

if TYPE_CHECKING:
    from bot.database.repositories import GuildSettingsRepository
    from bot.main import ForUS


CATEGORY_CHOICES: list[app_commands.Choice[str]] = [
    app_commands.Choice(name=label, value=key) for key, label in ACTIVITY_LOG_CATEGORIES.items()
]


@app_commands.default_permissions(administrator=True)
class ActivityLog(commands.GroupCog, name="activitylog", description="Kelola activity log server."):
    guild_only = True

    def __init__(self, bot: ForUS) -> None:
        super().__init__()
        self.bot = bot
        self.logger = ActivityLogger(bot)

    async def _ensure_context(
        self, interaction: discord.Interaction
    ) -> Optional[tuple[discord.Guild, "GuildSettingsRepository"]]:
        guild = interaction.guild
        if guild is None:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "Perintah ini hanya bisa digunakan di dalam server.",
                    ephemeral=True,
                )
            return None

        repo = self.bot.guild_repo
        if repo is None:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "Repositori guild belum siap. Silakan coba lagi nanti.",
                    ephemeral=True,
                )
            return None

        return guild, repo

    async def _send_ephemeral(
        self,
        interaction: discord.Interaction,
        message: Optional[str] = None,
        *,
        embed: Optional[discord.Embed] = None,
    ) -> None:
        if interaction.response.is_done():
            await interaction.followup.send(content=message, embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(content=message, embed=embed, ephemeral=True)

    @app_commands.command(name="status", description="Tampilkan konfigurasi activity log.")
    async def status(self, interaction: discord.Interaction) -> None:
        context = await self._ensure_context(interaction)
        if context is None:
            return
        guild, _ = context

        config = await self.logger.get_preferences(guild)

        channel_value = "Belum disetel"
        if config.channel_id:
            channel_obj = guild.get_channel(config.channel_id)
            if isinstance(channel_obj, discord.TextChannel):
                channel_value = channel_obj.mention
            else:
                channel_value = f"<#{config.channel_id}>"

        embed = discord.Embed(
            title="Konfigurasi Activity Log",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Status", value="Aktif" if config.enabled else "Nonaktif", inline=False)
        embed.add_field(name="Channel", value=channel_value, inline=False)

        category_lines = []
        for key, label in ACTIVITY_LOG_CATEGORIES.items():
            emoji = "✅" if key not in config.disabled_categories else "❌"
            category_lines.append(f"{emoji} {label} (`{key}`)")

        embed.add_field(
            name="Kategori",
            value="\n".join(category_lines) if category_lines else "Belum ada kategori",
            inline=False,
        )

        if not config.enabled:
            embed.set_footer(text="Activity log saat ini dinonaktifkan.")

        await self._send_ephemeral(
            interaction,
            "Berikut status terbaru activity log:",
            embed=embed,
        )

    @app_commands.command(name="set-channel", description="Setel channel tujuan activity log.")
    @app_commands.describe(channel="Channel teks yang akan menerima activity log. Kosongkan untuk menghapus pengaturan.")
    async def set_channel(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
    ) -> None:
        context = await self._ensure_context(interaction)
        if context is None:
            return
        guild, repo = context

        await repo.upsert(guild.id, activity_log_channel_id=channel.id if channel else None)
        await self.logger.invalidate_cache(guild.id)

        if channel is None:
            message = (
                "Channel activity log dihapus. Bot akan menggunakan channel log umum jika tersedia."
            )
        else:
            message = f"Channel activity log diset ke {channel.mention}. Pastikan bot dapat mengirim pesan di sana."

        await self._send_ephemeral(interaction, message)

    @app_commands.command(name="toggle", description="Aktifkan atau nonaktifkan activity log.")
    @app_commands.describe(status="Pilih 'True' untuk mengaktifkan atau 'False' untuk menonaktifkan.")
    async def toggle(self, interaction: discord.Interaction, status: bool) -> None:
        context = await self._ensure_context(interaction)
        if context is None:
            return
        guild, repo = context

        await repo.upsert(guild.id, activity_log_enabled=status)
        await self.logger.invalidate_cache(guild.id)

        message = "Activity log berhasil diaktifkan." if status else "Activity log dinonaktifkan."
        await self._send_ephemeral(interaction, message)

    @app_commands.command(name="reset", description="Reset konfigurasi activity log ke nilai awal.")
    async def reset(self, interaction: discord.Interaction) -> None:
        context = await self._ensure_context(interaction)
        if context is None:
            return
        guild, repo = context

        await repo.upsert(
            guild.id,
            activity_log_channel_id=None,
            activity_log_enabled=True,
            activity_log_disabled_events=[],
        )
        await self.logger.invalidate_cache(guild.id)

        await self._send_ephemeral(
            interaction,
            "Konfigurasi activity log telah direset. Semua kategori aktif dan channel khusus dikosongkan.",
        )

    @app_commands.command(name="category", description="Aktifkan atau nonaktifkan kategori tertentu.")
    @app_commands.describe(category="Kategori log yang ingin diatur.", enabled="Aktifkan? Pilih False untuk menonaktifkan.")
    @app_commands.choices(category=CATEGORY_CHOICES)
    async def category(
        self,
        interaction: discord.Interaction,
        category: app_commands.Choice[str],
        enabled: bool,
    ) -> None:
        context = await self._ensure_context(interaction)
        if context is None:
            return
        guild, repo = context
        settings = await repo.get(guild.id)
        disabled = set(settings.activity_log_disabled_events if settings else [])

        if enabled:
            changed = category.value in disabled
            disabled.discard(category.value)
        else:
            changed = category.value not in disabled
            disabled.add(category.value)

        await repo.upsert(guild.id, activity_log_disabled_events=sorted(disabled))
        await self.logger.invalidate_cache(guild.id)

        if enabled:
            message = (
                f"Kategori `{category.value}` diaktifkan kembali untuk activity log."
                if changed
                else f"Kategori `{category.value}` sudah aktif."
            )
        else:
            message = (
                f"Kategori `{category.value}` dinonaktifkan dan tidak akan dicatat."
                if changed
                else f"Kategori `{category.value}` sudah nonaktif."
            )

        await self._send_ephemeral(interaction, message)

    async def _resolve_log_channel(
        self,
        guild: discord.Guild,
        *,
        compare_channel_id: Optional[int] = None,
    ) -> tuple[Optional[discord.TextChannel], bool]:
        channel = await self.logger.get_log_channel(guild)
        if channel is None:
            return None, False
        is_same = compare_channel_id == channel.id if compare_channel_id is not None else False
        return channel, is_same

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        guild = message.guild
        if guild is None:
            return
        log_channel, is_log_channel = await self._resolve_log_channel(guild, compare_channel_id=message.channel.id)
        if log_channel is None or is_log_channel:
            return
        if message.type is not discord.MessageType.default:
            return
        await self.logger.log_message_sent(message, channel=log_channel)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        guild = after.guild
        if guild is None:
            return
        log_channel, is_log_channel = await self._resolve_log_channel(guild, compare_channel_id=after.channel.id)
        if log_channel is None or is_log_channel:
            return
        await self.logger.log_message_edit(before, after, channel=log_channel)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        guild = message.guild
        if guild is None:
            return
        log_channel, is_log_channel = await self._resolve_log_channel(guild, compare_channel_id=message.channel.id)
        if log_channel is None or is_log_channel:
            return
        await self.logger.log_message_delete(message, channel=log_channel)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: list[discord.Message]) -> None:
        if not messages:
            return
        guild = messages[0].guild
        channel = messages[0].channel
        if guild is None or not isinstance(channel, discord.TextChannel):
            return
        log_channel, is_log_channel = await self._resolve_log_channel(guild, compare_channel_id=channel.id)
        if log_channel is None or is_log_channel:
            return
        await self.logger.log_bulk_delete(messages, guild, channel, channel=log_channel)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        log_channel, _ = await self._resolve_log_channel(member.guild)
        if log_channel is None:
            return
        await self.logger.log_member_join(member, channel=log_channel)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member | discord.User) -> None:
        guild = getattr(member, "guild", None)
        if guild is None:
            return
        log_channel, _ = await self._resolve_log_channel(guild)
        if log_channel is None:
            return
        await self.logger.log_member_remove(member, guild, channel=log_channel)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        log_channel, _ = await self._resolve_log_channel(after.guild)
        if log_channel is None:
            return
        await self.logger.log_member_update(before, after, channel=log_channel)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        log_channel, _ = await self._resolve_log_channel(member.guild)
        if log_channel is None:
            return
        await self.logger.log_voice_state(member, before, after, channel=log_channel)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        guild = channel.guild
        log_channel, _ = await self._resolve_log_channel(guild)
        if log_channel is None:
            return
        await self.logger.log_channel_event(guild, action="Dibuat", channel_obj=channel, channel=log_channel)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        guild = channel.guild
        log_channel, is_log_channel = await self._resolve_log_channel(guild, compare_channel_id=channel.id)
        if log_channel is not None and not is_log_channel:
            await self.logger.log_channel_event(guild, action="Dihapus", channel_obj=channel, channel=log_channel)
        await self.logger.invalidate_cache(guild.id)

    @commands.Cog.listener()
    async def on_guild_channel_update(
        self,
        before: discord.abc.GuildChannel,
        after: discord.abc.GuildChannel,
    ) -> None:
        guild = after.guild
        log_channel, is_log_channel = await self._resolve_log_channel(guild, compare_channel_id=after.id)
        if log_channel is None or is_log_channel:
            return
        if getattr(before, "name", None) != getattr(after, "name", None):
            await self.logger.log_channel_event(
                guild,
                action="Diubah",
                channel_obj=after,
                old_name=getattr(before, "name", None),
                new_name=getattr(after, "name", None),
                channel=log_channel,
            )

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role) -> None:
        guild = role.guild
        log_channel, _ = await self._resolve_log_channel(guild)
        if log_channel is None:
            return
        await self.logger.log_role_event(guild, action="Dibuat", role=role, channel=log_channel)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        guild = role.guild
        log_channel, _ = await self._resolve_log_channel(guild)
        if log_channel is None:
            return
        await self.logger.log_role_event(guild, action="Dihapus", role=role, channel=log_channel)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role) -> None:
        guild = after.guild
        log_channel, _ = await self._resolve_log_channel(guild)
        if log_channel is None:
            return
        if before.name != after.name:
            await self.logger.log_role_event(
                guild,
                action="Diubah",
                role=after,
                old_name=before.name,
                new_name=after.name,
                channel=log_channel,
            )

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread) -> None:
        guild = thread.guild
        if guild is None:
            return
        log_channel, is_log_channel = await self._resolve_log_channel(guild, compare_channel_id=thread.parent_id)
        if log_channel is None or is_log_channel:
            return
        await self.logger.log_thread_event(thread, action="Dibuat", channel=log_channel)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread) -> None:
        guild = thread.guild
        if guild is None:
            return
        log_channel, _ = await self._resolve_log_channel(guild)
        if log_channel is None:
            return
        await self.logger.log_thread_event(thread, action="Dihapus", channel=log_channel)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User | discord.Member) -> None:
        message = reaction.message
        guild = message.guild
        if guild is None:
            return
        log_channel, is_log_channel = await self._resolve_log_channel(guild, compare_channel_id=message.channel.id)
        if log_channel is None or is_log_channel:
            return
        await self.logger.log_reaction(reaction, user, added=True, channel=log_channel)

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction: discord.Reaction, user: discord.User | discord.Member) -> None:
        message = reaction.message
        guild = message.guild
        if guild is None:
            return
        log_channel, is_log_channel = await self._resolve_log_channel(guild, compare_channel_id=message.channel.id)
        if log_channel is None or is_log_channel:
            return
        await self.logger.log_reaction(reaction, user, added=False, channel=log_channel)

    @commands.Cog.listener()
    async def on_app_command_completion(
        self,
        interaction: discord.Interaction,
        command: app_commands.Command,
    ) -> None:
        if interaction.guild is None:
            return
        log_channel, _ = await self._resolve_log_channel(interaction.guild)
        if log_channel is None:
            return
        await self.logger.log_app_command(interaction, command, succeeded=True, channel=log_channel)

    @commands.Cog.listener()
    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if interaction.guild is None:
            return
        log_channel, _ = await self._resolve_log_channel(interaction.guild)
        if log_channel is None:
            return
        await self.logger.log_app_command(
            interaction,
            interaction.command if isinstance(interaction.command, app_commands.Command) else None,
            succeeded=False,
            error=error,
            channel=log_channel,
        )

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context) -> None:
        guild = ctx.guild
        if guild is None:
            return
        log_channel, _ = await self._resolve_log_channel(guild)
        if log_channel is None:
            return
        await self.logger.log_prefix_command(ctx, succeeded=True, channel=log_channel)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        guild = ctx.guild
        if guild is None:
            return
        log_channel, _ = await self._resolve_log_channel(guild)
        if log_channel is None:
            return
        await self.logger.log_prefix_command(ctx, succeeded=False, error=error, channel=log_channel)


async def setup(bot: ForUS) -> None:
    await bot.add_cog(ActivityLog(bot))
