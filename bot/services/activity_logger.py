from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, FrozenSet, Iterable, Optional, Sequence, TYPE_CHECKING, Protocol

import interactions

from .cache import TTLCache
from .logging import get_logger

if TYPE_CHECKING:
    from bot.main import ForUS


__all__ = [
    "ActivityLogger",
    "truncate_content",
    "format_attachments",
    "format_user",
    "ACTIVITY_LOG_CATEGORIES",
]


MAX_CONTENT_LENGTH = 1024
MAX_ATTACHMENT_DISPLAY = 5
ACTIVITY_LOG_CATEGORIES: Dict[str, str] = {
    "messages": "Pesan & Konten",
    "members": "Anggota",
    "voice": "Voice & Stage",
    "server": "Struktur Server",
    "reactions": "Reaksi",
    "commands": "Perintah",
}


def truncate_content(content: str, *, limit: int = MAX_CONTENT_LENGTH) -> str:
    """Potong konten agar cocok di field embed."""

    if not content:
        return ""
    content = content.strip()
    if len(content) <= limit:
        return content
    return content[: limit - 1] + "…"


class SupportsAttachmentDisplay(Protocol):
    filename: str
    url: Optional[str]


def format_attachments(attachments: Sequence[interactions.Attachment | SupportsAttachmentDisplay]) -> str | None:
    """Format daftar lampiran untuk ditampilkan dalam embed."""

    if not attachments:
        return None

    lines: list[str] = []
    total = len(attachments)
    display = min(total, MAX_ATTACHMENT_DISPLAY)

    for attachment in attachments[:display]:
        name = getattr(attachment, "filename", "lampiran")
        url = getattr(attachment, "url", None)
        if url:
            lines.append(f"[{name}]({url})")
        else:
            lines.append(name)

    if total > display:
        lines.append(f"+{total - display} lampiran lainnya")

    return "\n".join(lines)


def format_user(user: Optional[interactions.User], *, fallback: str = "Unknown") -> str:
    if user is None:
        return fallback
    mention = getattr(user, "mention", None)
    user_id = getattr(user, "id", None)
    name = getattr(user, "display_name", None) or getattr(user, "name", fallback)
    base = mention or name
    if user_id is not None:
        return f"{base} (`{user_id}`)"
    return base


@dataclass(slots=True)
class _ActivityLogConfig:
    channel_id: Optional[int]
    enabled: bool
    disabled_categories: FrozenSet[str]

    def allows(self, category: str) -> bool:
        if not self.enabled:
            return False
        return category not in self.disabled_categories


class ActivityLogger:
    def __init__(self, bot: ForUS, *, cache_ttl: int = 300) -> None:
        self.bot = bot
        self._cache = TTLCache(ttl=cache_ttl)
        self._internal_log = get_logger("ActivityLogger")

    def _cache_key(self, guild_id: int) -> str:
        return f"activity-log-config:{guild_id}"

    async def invalidate_cache(self, guild_id: int) -> None:
        await self._cache.invalidate(self._cache_key(guild_id))

    async def _get_config(self, guild: interactions.Guild) -> _ActivityLogConfig:
        cache_key = self._cache_key(guild.id)
        cached = await self._cache.get(cache_key)
        if isinstance(cached, _ActivityLogConfig):
            return cached

        if self.bot.guild_repo is None:
            config = _ActivityLogConfig(channel_id=None, enabled=False, disabled_categories=frozenset())
        else:
            settings = await self.bot.guild_repo.get(guild.id)
            if settings is None:
                config = _ActivityLogConfig(channel_id=None, enabled=False, disabled_categories=frozenset())
            else:
                config = _ActivityLogConfig(
                    channel_id=settings.effective_activity_channel(),
                    enabled=bool(settings.activity_log_enabled),
                    disabled_categories=frozenset(settings.activity_log_disabled_events),
                )

        await self._cache.set(cache_key, config)
        return config

    async def get_preferences(self, guild: interactions.Guild) -> _ActivityLogConfig:
        return await self._get_config(guild)

    async def _resolve_channel(self, guild: interactions.Guild, config: _ActivityLogConfig) -> Optional[interactions.GuildText]:
        channel_id = config.channel_id
        if not channel_id:
            return None

        channel = guild.get_channel(channel_id)
        if isinstance(channel, interactions.GuildText):
            return channel

        try:
            fetched = await guild.fetch_channel(channel_id)
        except interactions.errors.Forbidden:
            self._internal_log.warning("Tidak dapat mengakses channel log %s di guild %s", channel_id, guild.id)
            await self.invalidate_cache(guild.id)
            return None
        except interactions.errors.HTTPException:
            await self.invalidate_cache(guild.id)
            return None

        if isinstance(fetched, interactions.GuildText):
            return fetched

        await self.invalidate_cache(guild.id)
        return None

    async def get_log_channel(self, guild: interactions.Guild) -> Optional[interactions.GuildText]:
        config = await self._get_config(guild)
        if not config.enabled:
            return None
        return await self._resolve_channel(guild, config)

    async def send_embed(
        self,
        guild: interactions.Guild,
        embed: interactions.Embed,
        *,
        channel: Optional[interactions.GuildText] = None,
        files: Optional[Sequence[interactions.File]] = None,
        category: Optional[str] = None,
    ) -> bool:
        config = await self._get_config(guild)
        if category is not None and not config.allows(category):
            return False
        if category is None and not config.enabled:
            return False

        target = channel or await self._resolve_channel(guild, config)
        if target is None:
            return False
        try:
            await target.send(embed=embed, files=files or [])
        except (interactions.errors.Forbidden, interactions.errors.HTTPException) as exc:
            self._internal_log.warning("Gagal mengirim log aktivitas: %s", exc)
            await self.invalidate_cache(guild.id)
            return False
        return True

    @staticmethod
    def _base_embed(title: str, *, color: interactions.Color, description: str | None = None) -> interactions.Embed:
        embed = interactions.Embed(title=title, color=color, timestamp=datetime.now(timezone.utc))
        if description:
            embed.description = truncate_content(description, limit=2048)
        return embed

    async def log_message_sent(self, message: interactions.Message, *, channel: Optional[interactions.GuildText] = None) -> bool:
        if message.guild is None:
            return False
        embed = self._base_embed("Pesan Baru", color=interactions.Color.from_hex("#5865F2"))  # blurple
        embed.add_field(name="Pengguna", value=format_user(message.author), inline=False)
        embed.add_field(name="Channel", value=message.channel.mention)
        if message.content:
            embed.add_field(name="Isi", value=truncate_content(message.content), inline=False)
        attachments = format_attachments(message.attachments)
        if attachments:
            embed.add_field(name="Lampiran", value=attachments, inline=False)
        embed.add_field(name="Link", value=message.jump_url, inline=False)
        return await self.send_embed(message.guild, embed, channel=channel, category="messages")

    async def log_message_edit(
        self,
        before: interactions.Message,
        after: interactions.Message,
        *,
        channel: Optional[interactions.GuildText] = None,
    ) -> bool:
        if after.guild is None:
            return False
        if before.content == after.content:
            return False
        embed = self._base_embed("Pesan Diedit", color=interactions.Color.from_hex("#F1C40F"))
        embed.add_field(name="Pengguna", value=format_user(after.author), inline=False)
        embed.add_field(name="Channel", value=after.channel.mention)
        if before.content:
            embed.add_field(name="Sebelum", value=truncate_content(before.content), inline=False)
        if after.content:
            embed.add_field(name="Sesudah", value=truncate_content(after.content), inline=False)
        embed.add_field(name="Link", value=after.jump_url, inline=False)
        return await self.send_embed(after.guild, embed, channel=channel, category="messages")

    async def log_message_delete(
        self,
        message: interactions.Message,
        *,
        channel: Optional[interactions.GuildText] = None,
    ) -> bool:
        guild = message.guild
        if guild is None:
            return False
        embed = self._base_embed("Pesan Dihapus", color=interactions.Color.dark_red())
        author_field = format_user(getattr(message, "author", None), fallback="Tidak diketahui")
        embed.add_field(name="Pengguna", value=author_field, inline=False)
        embed.add_field(name="Channel", value=message.channel.mention)
        content = getattr(message, "content", None)
        if content:
            embed.add_field(name="Isi", value=truncate_content(content), inline=False)
        attachments = getattr(message, "attachments", None)
        attachment_display = format_attachments(attachments or [])
        if attachment_display:
            embed.add_field(name="Lampiran", value=attachment_display, inline=False)
        return await self.send_embed(guild, embed, channel=channel, category="messages")

    async def log_bulk_delete(
        self,
        messages: Iterable[interactions.Message],
        guild: interactions.Guild,
        channel_deleted: interactions.GuildText,
        *,
        channel: Optional[interactions.GuildText] = None,
    ) -> bool:
        count = sum(1 for _ in messages)
        embed = self._base_embed("Bulk Delete", color=interactions.Color.dark_red(), description=f"{count} pesan dihapus.")
        embed.add_field(name="Channel", value=channel_deleted.mention)
        return await self.send_embed(guild, embed, channel=channel, category="messages")

    async def log_member_join(self, member: interactions.Member, *, channel: Optional[interactions.GuildText] = None) -> bool:
        guild = member.guild
        embed = self._base_embed("Anggota Bergabung", color=interactions.Color.from_hex("#2ECC71"))  # green
        embed.add_field(name="Pengguna", value=format_user(member), inline=False)
        embed.add_field(name="Akun dibuat", value=interactions.Timestamp.fromdatetime(member.created_at).format(interactions.TimestampStyles.F))
        if member.bot:
            embed.add_field(name="Tipe", value="Bot")
        return await self.send_embed(guild, embed, channel=channel, category="members")

    async def log_member_remove(self, member: interactions.Member | interactions.User, guild: interactions.Guild, *, channel: Optional[interactions.GuildText] = None) -> bool:
        embed = self._base_embed("Anggota Keluar", color=interactions.Color.from_hex("#E67E22"))  # orange
        embed.add_field(name="Pengguna", value=format_user(member), inline=False)
        joined_at = getattr(member, "joined_at", None)
        if joined_at:
            embed.add_field(name="Bergabung", value=interactions.Timestamp.fromdatetime(joined_at).format(interactions.TimestampStyles.F))
        return await self.send_embed(guild, embed, channel=channel, category="members")

    async def log_member_update(
        self,
        before: interactions.Member,
        after: interactions.Member,
        *,
        channel: Optional[interactions.GuildText] = None,
    ) -> bool:
        changes: list[str] = []
        if before.nick != after.nick:
            before_nick = before.nick or "(none)"
            after_nick = after.nick or "(none)"
            changes.append(f"Nickname: `{before_nick}` → `{after_nick}`")

        before_roles = {role.id for role in before.roles}
        after_roles = {role.id for role in after.roles}
        added = after_roles - before_roles
        removed = before_roles - after_roles

        if added:
            role_mentions = [after.guild.get_role(role_id).mention for role_id in added if after.guild.get_role(role_id)]
            if role_mentions:
                changes.append(f"Role ditambah: {', '.join(role_mentions)}")
        if removed:
            role_mentions = [before.guild.get_role(role_id).mention for role_id in removed if before.guild.get_role(role_id)]
            if role_mentions:
                changes.append(f"Role dihapus: {', '.join(role_mentions)}")

        if not changes:
            return False

        embed = self._base_embed("Anggota Diperbarui", color=interactions.Color.blue())
        embed.add_field(name="Pengguna", value=format_user(after), inline=False)
        embed.add_field(name="Perubahan", value="\n".join(changes), inline=False)
        return await self.send_embed(after.guild, embed, channel=channel, category="members")

    async def log_voice_state(
        self,
        member: interactions.Member,
        before: interactions.VoiceState,
        after: interactions.VoiceState,
        *,
        channel: Optional[interactions.GuildText] = None,
    ) -> bool:
        guild = member.guild
        changes: list[str] = []

        if before.channel != after.channel:
            if before.channel is None and after.channel is not None:
                changes.append(f"Join {after.channel.mention}")
            elif before.channel is not None and after.channel is None:
                changes.append(f"Leave {before.channel.mention}")
            elif before.channel and after.channel:
                changes.append(f"Pindah {before.channel.mention} → {after.channel.mention}")

        if before.self_mute != after.self_mute:
            changes.append("Self mute" if after.self_mute else "Self unmute")
        if before.self_deaf != after.self_deaf:
            changes.append("Self deaf" if after.self_deaf else "Self undeaf")
        if before.self_stream != after.self_stream:
            changes.append("Streaming" if after.self_stream else "Stop streaming")
        if before.self_video != after.self_video:
            changes.append("Kamera on" if after.self_video else "Kamera off")

        if not changes:
            return False

        embed = self._base_embed("Aktivitas Voice", color=interactions.Color.from_hex("#9B59B6"))
        embed.add_field(name="Pengguna", value=format_user(member), inline=False)
        embed.add_field(name="Perubahan", value="\n".join(changes), inline=False)
        return await self.send_embed(guild, embed, channel=channel, category="voice")

    async def log_channel_event(
        self,
        guild: interactions.Guild,
        *,
        action: str,
        channel_obj: interactions.GuildChannel,
        old_name: str | None = None,
        new_name: str | None = None,
        channel: Optional[interactions.GuildText] = None,
    ) -> bool:
        embed = self._base_embed("Channel", color=interactions.Color.from_hex("#1ABC9C"))
        embed.add_field(name="Aksi", value=action)
        embed.add_field(name="Channel", value=getattr(channel_obj, "mention", channel_obj.name))
        if old_name or new_name:
            embed.add_field(name="Nama", value=f"{old_name or '-'} → {new_name or '-'}", inline=False)
        embed.add_field(name="ID", value=f"`{channel_obj.id}`")
        return await self.send_embed(guild, embed, channel=channel, category="server")

    async def log_role_event(
        self,
        guild: interactions.Guild,
        *,
        action: str,
        role: interactions.Role,
        old_name: str | None = None,
        new_name: str | None = None,
        channel: Optional[interactions.GuildText] = None,
    ) -> bool:
        embed = self._base_embed("Role", color=interactions.Color.dark_teal())
        embed.add_field(name="Aksi", value=action)
        embed.add_field(name="Role", value=role.mention)
        if old_name or new_name:
            embed.add_field(name="Nama", value=f"{old_name or '-'} → {new_name or '-'}", inline=False)
        embed.add_field(name="ID", value=f"`{role.id}`")
        return await self.send_embed(guild, embed, channel=channel, category="server")

    async def log_thread_event(
        self,
        thread: interactions.ThreadChannel,
        *,
        action: str,
        channel: Optional[interactions.GuildText] = None,
    ) -> bool:
        guild = thread.guild
        embed = self._base_embed("Thread", color=interactions.Color.blue())
        embed.add_field(name="Aksi", value=action)
        embed.add_field(name="Thread", value=thread.mention)
        parent = thread.parent
        if parent:
            embed.add_field(name="Parent", value=parent.mention)
        embed.add_field(name="ID", value=f"`{thread.id}`")
        return await self.send_embed(guild, embed, channel=channel, category="server")

    async def log_reaction(
        self,
        reaction: interactions.Reaction,
        user: interactions.User | interactions.Member,
        *,
        added: bool,
        channel: Optional[interactions.GuildText] = None,
    ) -> bool:
        message = reaction.message
        guild = message.guild
        if guild is None:
            return False
        action = "Reaksi Ditambahkan" if added else "Reaksi Dihapus"
        embed = self._base_embed(action, color=interactions.Color.dark_orange())
        embed.add_field(name="Pengguna", value=format_user(user), inline=False)
        embed.add_field(name="Channel", value=message.channel.mention)
        embed.add_field(name="Emote", value=str(reaction.emoji))
        embed.add_field(name="Link", value=message.jump_url, inline=False)
        return await self.send_embed(guild, embed, channel=channel, category="reactions")

    async def log_app_command(
        self,
        interaction: interactions.SlashContext,
        command: Optional[interactions.SlashCommand] = None,
        *,
        succeeded: bool,
        error: Optional[BaseException] = None,
        channel: Optional[interactions.GuildText] = None,
    ) -> bool:
        guild = interaction.guild
        if guild is None:
            return False
        title = "Slash Command" if succeeded else "Slash Command Error"
        color = interactions.Color.from_hex("#2ECC71") if succeeded else interactions.Color.from_hex("#ED4245")  # green : red
        embed = self._base_embed(title, color=color)
        embed.add_field(name="Pengguna", value=format_user(interaction.author), inline=False)
        if interaction.channel:
            embed.add_field(name="Channel", value=interaction.channel.mention)
        command_name = (
            command.name
            if command is not None
            else getattr(interaction.invoke_target, "name", "<unknown>")
        )
        embed.add_field(name="Perintah", value=command_name)
        if not succeeded and error:
            embed.add_field(name="Error", value=truncate_content(str(error), limit=512), inline=False)
        return await self.send_embed(guild, embed, channel=channel, category="commands")

    async def log_prefix_command(
        self,
        ctx: interactions.BaseContext,
        *,
        succeeded: bool,
        error: Optional[BaseException] = None,
        channel: Optional[interactions.GuildText] = None,
    ) -> bool:
        guild = ctx.guild
        if guild is None:
            return False
        title = "Command" if succeeded else "Command Error"
        color = interactions.Color.dark_green() if succeeded else interactions.Color.dark_red()
        embed = self._base_embed(title, color=color)
        embed.add_field(name="Pengguna", value=format_user(ctx.author), inline=False)
        if ctx.channel:
            embed.add_field(name="Channel", value=ctx.channel.mention)
        command_name = getattr(ctx.invoke_target, "name", "<unknown>") if hasattr(ctx, "invoke_target") else "<unknown>"
        embed.add_field(name="Perintah", value=command_name)
        if not succeeded and error:
            embed.add_field(name="Error", value=truncate_content(str(error), limit=512), inline=False)
        return await self.send_embed(guild, embed, channel=channel, category="commands")
