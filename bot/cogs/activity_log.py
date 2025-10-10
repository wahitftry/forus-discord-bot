from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import interactions

from bot.services.activity_logger import ACTIVITY_LOG_CATEGORIES, ActivityLogger

if TYPE_CHECKING:
    from bot.database.repositories import GuildSettingsRepository
    from bot.main import ForUS


CATEGORY_CHOICES: list[interactions.SlashCommandChoice] = [
    interactions.SlashCommandChoice(name=label, value=key) for key, label in ACTIVITY_LOG_CATEGORIES.items()
]


class ActivityLog(interactions.Extension):
    def __init__(self, bot: ForUS) -> None:
        self.bot = bot
        self.logger = ActivityLogger(bot)

    async def _ensure_context(
        self, ctx: interactions.SlashContext
    ) -> Optional[tuple[interactions.Guild, "GuildSettingsRepository"]]:
        guild = ctx.guild
        if guild is None:
            await ctx.send(
                "Perintah ini hanya bisa digunakan di dalam server.",
                ephemeral=True,
            )
            return None

        repo = self.bot.guild_repo
        if repo is None:
            await ctx.send(
                "Repositori guild belum siap. Silakan coba lagi nanti.",
                ephemeral=True,
            )
            return None

        return guild, repo

    async def _send_ephemeral(
        self,
        ctx: interactions.SlashContext,
        message: Optional[str] = None,
        *,
        embed: Optional[interactions.Embed] = None,
    ) -> None:
        if interaction.response.is_done():
            await ctx.send(content=message, embed=embed, ephemeral=True)
        else:
            await ctx.send(content=message, embed=embed, ephemeral=True)

    @interactions.slash_command(name='status', description='Tampilkan konfigurasi activity log.')
    async def status(self, ctx: interactions.SlashContext) -> None:
        context = await self._ensure_context(ctx)
        if context is None:
            return
        guild, _ = context

        config = await self.logger.get_preferences(guild)

        channel_value = "Belum disetel"
        if config.channel_id:
            channel_obj = guild.get_channel(config.channel_id)
            if isinstance(channel_obj, interactions.GuildText):
                channel_value = channel_obj.mention
            else:
                channel_value = f"<#{config.channel_id}>"

        embed = interactions.Embed(
            title="Konfigurasi Activity Log",
            color=interactions.Color.from_hex("#5865F2"),  # Discord blurple
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
            ctx,
            "Berikut status terbaru activity log:",
            embed=embed,
        )

    @interactions.slash_command(
        name="activitylog",
        description="Activity log commands",
        sub_cmd_name="set_channel",
        sub_cmd_description="Setel channel tujuan activity log.",
        default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    )
    @interactions.slash_option(
        name="channel",
        description="Channel teks yang akan menerima activity log. Kosongkan untuk menghapus pengaturan.",
        opt_type=interactions.OptionType.CHANNEL,
        required=False,
    )
    async def set_channel(
        self,
        ctx: interactions.SlashContext,
        channel: Optional[interactions.GuildText] = None,
    ) -> None:
        context = await self._ensure_context(ctx)
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

        await self._send_ephemeral(ctx, message)

    @interactions.slash_command(
        name="activitylog",
        description="Activity log commands",
        sub_cmd_name="toggle",
        sub_cmd_description="Aktifkan atau nonaktifkan activity log.",
        default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    )
    @interactions.slash_option(
        name="status",
        description="Pilih 'True' untuk mengaktifkan atau 'False' untuk menonaktifkan.",
        opt_type=interactions.OptionType.BOOLEAN,
        required=True,
    )
    async def toggle(self, ctx: interactions.SlashContext, status: bool) -> None:
        context = await self._ensure_context(ctx)
        if context is None:
            return
        guild, repo = context

        await repo.upsert(guild.id, activity_log_enabled=status)
        await self.logger.invalidate_cache(guild.id)

        message = "Activity log berhasil diaktifkan." if status else "Activity log dinonaktifkan."
        await self._send_ephemeral(ctx, message)

    @interactions.slash_command(
        name="activitylog",
        description="Activity log commands",
        sub_cmd_name="reset",
        sub_cmd_description="Reset konfigurasi activity log ke nilai awal.",
        default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    )
    async def reset(self, ctx: interactions.SlashContext) -> None:
        context = await self._ensure_context(ctx)
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
            ctx,
            "Konfigurasi activity log telah direset. Semua kategori aktif dan channel khusus dikosongkan.",
        )

    @interactions.slash_command(
        name="activitylog",
        description="Activity log commands",
        sub_cmd_name="category",
        sub_cmd_description="Aktifkan atau nonaktifkan kategori tertentu.",
        default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    )
    @interactions.slash_option(
        name="category",
        description="Kategori log yang ingin diatur.",
        opt_type=interactions.OptionType.STRING,
        required=True,
        choices=CATEGORY_CHOICES,
    )
    @interactions.slash_option(
        name="enabled",
        description="Aktifkan? Pilih False untuk menonaktifkan.",
        opt_type=interactions.OptionType.BOOLEAN,
        required=True,
    )
    async def category(
        self,
        ctx: interactions.SlashContext,
        category: str,
        enabled: bool,
    ) -> None:
        context = await self._ensure_context(ctx)
        if context is None:
            return
        guild, repo = context
        settings = await repo.get(guild.id)
        disabled = set(settings.activity_log_disabled_events if settings else [])

        if enabled:
            changed = category in disabled
            disabled.discard(category)
        else:
            changed = category not in disabled
            disabled.add(category)

        await repo.upsert(guild.id, activity_log_disabled_events=sorted(disabled))
        await self.logger.invalidate_cache(guild.id)

        if enabled:
            message = (
                f"Kategori `{category}` diaktifkan kembali untuk activity log."
                if changed
                else f"Kategori `{category}` sudah aktif."
            )
        else:
            message = (
                f"Kategori `{category}` dinonaktifkan dan tidak akan dicatat."
                if changed
                else f"Kategori `{category}` sudah nonaktif."
            )

        await self._send_ephemeral(ctx, message)

    async def _resolve_log_channel(
        self,
        guild: interactions.Guild,
        *,
        compare_channel_id: Optional[int] = None,
    ) -> tuple[Optional[interactions.GuildText], bool]:
        channel = await self.logger.get_log_channel(guild)
        if channel is None:
            return None, False
        is_same = compare_channel_id == channel.id if compare_channel_id is not None else False
        return channel, is_same

    @interactions.listen()
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

    @interactions.listen()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        guild = after.guild
        if guild is None:
            return
        log_channel, is_log_channel = await self._resolve_log_channel(guild, compare_channel_id=after.channel.id)
        if log_channel is None or is_log_channel:
            return
        await self.logger.log_message_edit(before, after, channel=log_channel)

    @interactions.listen()
    async def on_message_delete(self, message: discord.Message) -> None:
        guild = message.guild
        if guild is None:
            return
        log_channel, is_log_channel = await self._resolve_log_channel(guild, compare_channel_id=message.channel.id)
        if log_channel is None or is_log_channel:
            return
        await self.logger.log_message_delete(message, channel=log_channel)

    @interactions.listen()
    async def on_bulk_message_delete(self, messages: list[discord.Message]) -> None:
        if not messages:
            return
        guild = messages[0].guild
        channel = messages[0].channel
        if guild is None or not isinstance(channel, interactions.GuildText):
            return
        log_channel, is_log_channel = await self._resolve_log_channel(guild, compare_channel_id=channel.id)
        if log_channel is None or is_log_channel:
            return
        await self.logger.log_bulk_delete(messages, guild, channel, channel=log_channel)

    @interactions.listen()
    async def on_member_join(self, member: interactions.Member) -> None:
        log_channel, _ = await self._resolve_log_channel(member.guild)
        if log_channel is None:
            return
        await self.logger.log_member_join(member, channel=log_channel)

    @interactions.listen()
    async def on_member_remove(self, member: interactions.Member | interactions.User) -> None:
        guild = getattr(member, "guild", None)
        if guild is None:
            return
        log_channel, _ = await self._resolve_log_channel(guild)
        if log_channel is None:
            return
        await self.logger.log_member_remove(member, guild, channel=log_channel)

    @interactions.listen()
    async def on_member_update(self, before: interactions.Member, after: interactions.Member) -> None:
        log_channel, _ = await self._resolve_log_channel(after.guild)
        if log_channel is None:
            return
        await self.logger.log_member_update(before, after, channel=log_channel)

    @interactions.listen()
    async def on_voice_state_update(
        self,
        member: interactions.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        log_channel, _ = await self._resolve_log_channel(member.guild)
        if log_channel is None:
            return
        await self.logger.log_voice_state(member, before, after, channel=log_channel)

    @interactions.listen()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        guild = channel.guild
        log_channel, _ = await self._resolve_log_channel(guild)
        if log_channel is None:
            return
        await self.logger.log_channel_event(guild, action="Dibuat", channel_obj=channel, channel=log_channel)

    @interactions.listen()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        guild = channel.guild
        log_channel, is_log_channel = await self._resolve_log_channel(guild, compare_channel_id=channel.id)
        if log_channel is not None and not is_log_channel:
            await self.logger.log_channel_event(guild, action="Dihapus", channel_obj=channel, channel=log_channel)
        await self.logger.invalidate_cache(guild.id)

    @interactions.listen()
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

    @interactions.listen()
    async def on_guild_role_create(self, role: discord.Role) -> None:
        guild = role.guild
        log_channel, _ = await self._resolve_log_channel(guild)
        if log_channel is None:
            return
        await self.logger.log_role_event(guild, action="Dibuat", role=role, channel=log_channel)

    @interactions.listen()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        guild = role.guild
        log_channel, _ = await self._resolve_log_channel(guild)
        if log_channel is None:
            return
        await self.logger.log_role_event(guild, action="Dihapus", role=role, channel=log_channel)

    @interactions.listen()
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

    @interactions.listen()
    async def on_thread_create(self, thread: discord.Thread) -> None:
        guild = thread.guild
        if guild is None:
            return
        log_channel, is_log_channel = await self._resolve_log_channel(guild, compare_channel_id=thread.parent_id)
        if log_channel is None or is_log_channel:
            return
        await self.logger.log_thread_event(thread, action="Dibuat", channel=log_channel)

    @interactions.listen()
    async def on_thread_delete(self, thread: discord.Thread) -> None:
        guild = thread.guild
        if guild is None:
            return
        log_channel, _ = await self._resolve_log_channel(guild)
        if log_channel is None:
            return
        await self.logger.log_thread_event(thread, action="Dihapus", channel=log_channel)

    @interactions.listen()
    async def on_reaction_add(self, reaction: discord.Reaction, user: interactions.User | interactions.Member) -> None:
        message = reaction.message
        guild = message.guild
        if guild is None:
            return
        log_channel, is_log_channel = await self._resolve_log_channel(guild, compare_channel_id=message.channel.id)
        if log_channel is None or is_log_channel:
            return
        await self.logger.log_reaction(reaction, user, added=True, channel=log_channel)

    @interactions.listen()
    async def on_reaction_remove(self, reaction: discord.Reaction, user: interactions.User | interactions.Member) -> None:
        message = reaction.message
        guild = message.guild
        if guild is None:
            return
        log_channel, is_log_channel = await self._resolve_log_channel(guild, compare_channel_id=message.channel.id)
        if log_channel is None or is_log_channel:
            return
        await self.logger.log_reaction(reaction, user, added=False, channel=log_channel)

    @interactions.listen()
    async def on_app_command_completion(
        self,
        ctx: interactions.SlashContext,
        command: app_commands.Command,
    ) -> None:
        if ctx.guild is None:
            return
        log_channel, _ = await self._resolve_log_channel(ctx.guild)
        if log_channel is None:
            return
        await self.logger.log_app_command(ctx, command, succeeded=True, channel=log_channel)

    @interactions.listen()
    async def on_app_command_error(
        self,
        ctx: interactions.SlashContext,
        error: app_commands.AppCommandError,
    ) -> None:
        if ctx.guild is None:
            return
        log_channel, _ = await self._resolve_log_channel(ctx.guild)
        if log_channel is None:
            return
        await self.logger.log_app_command(
            ctx,
            interaction.command if isinstance(interaction.command, app_commands.Command) else None,
            succeeded=False,
            error=error,
            channel=log_channel,
        )

    @interactions.listen()
    async def on_command_completion(self, ctx: commands.Context) -> None:
        guild = ctx.guild
        if guild is None:
            return
        log_channel, _ = await self._resolve_log_channel(guild)
        if log_channel is None:
            return
        await self.logger.log_prefix_command(ctx, succeeded=True, channel=log_channel)

    @interactions.listen()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        guild = ctx.guild
        if guild is None:
            return
        log_channel, _ = await self._resolve_log_channel(guild)
        if log_channel is None:
            return
        await self.logger.log_prefix_command(ctx, succeeded=False, error=error, channel=log_channel)


def setup(bot: ForUS) -> None:
    ActivityLog(bot)
