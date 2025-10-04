from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot.services.activity_logger import ActivityLogger

if TYPE_CHECKING:
    from bot.main import ForUS


class ActivityLog(commands.Cog):
    def __init__(self, bot: ForUS) -> None:
        self.bot = bot
        self.logger = ActivityLogger(bot)

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
