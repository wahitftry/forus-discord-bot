from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import interactions

if TYPE_CHECKING:
    from bot.main import ForUS


class Reminders(interactions.Extension):
    # MANUAL REVIEW: GroupCog -> Extension with slash_command group
    def __init__(self, bot: ForUS) -> None:
        super().__init__()
        self.bot = bot

    async def cog_load(self) -> None:
        if self.bot.reminder_repo is None:
            return
        reminders = await self.bot.reminder_repo.all_pending()
        for reminder in reminders:
            remind_at = datetime.fromisoformat(reminder["remind_at"])
            if remind_at < datetime.now(timezone.utc):
                await self.bot.reminder_repo.delete(reminder["id"])
                continue
            await self._schedule_reminder(reminder["id"], remind_at)

    async def _schedule_reminder(self, reminder_id: int, remind_at: datetime) -> None:
        if not self.bot.scheduler:
            return
        if not self.bot.scheduler.has_job(f"reminder-{reminder_id}"):
            self.bot.scheduler.schedule_reminder(reminder_id, remind_at, self._fire_reminder)

    async def _fire_reminder(self, reminder_id: int) -> None:
        if self.bot.reminder_repo is None:
            return
        reminders = await self.bot.reminder_repo.due_reminders(datetime.now(timezone.utc).isoformat())
        for reminder in reminders:
            if reminder["id"] != reminder_id:
                continue
            guild = self.bot.get_guild(reminder["guild_id"])
            if not guild:
                continue
            channel = guild.get_channel(reminder["channel_id"]) if reminder.get("channel_id") else None
            if channel and isinstance(channel, interactions.GuildText):
                await channel.send(f"<@{reminder['user_id']}> Pengingat: {reminder['message']}")
            else:
                member = guild.get_member(reminder["user_id"])
                if member:
                    try:
                        await member.send(f"Pengingat dari {guild.name}: {reminder['message']}")
                    except discord.Forbidden:
                        pass
            await self.bot.reminder_repo.delete(reminder_id)

    @interactions.slash_command(name='create', description='Buat pengingat baru dengan durasi tertentu.')
    @app_commands.describe(durasi_menit="Durasi sebelum pengingat (1-10080 menit)", pesan="Pesan pengingat", channel="Channel tujuan (opsional)")
    async def create(
        self,
        ctx: interactions.SlashContext,
        durasi_menit: app_commands.Range[int, 1, 10_080],
        pesan: str,
        channel: interactions.GuildText | None = None,
    ) -> None:
        if self.bot.reminder_repo is None or ctx.guild is None:
            await ctx.send("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        remind_at = datetime.now(timezone.utc) + timedelta(minutes=durasi_menit)
        reminder_id = await self.bot.reminder_repo.create(
            ctx.guild.id,
            ctx.author.id,
            pesan,
            remind_at.isoformat(),
            channel.id if channel else ctx.channel_id,
        )
        await self._schedule_reminder(reminder_id, remind_at)
        await ctx.send(
            f"Pengingat dibuat! ID: {reminder_id}. Saya akan mengingatkan pada {discord.utils.format_dt(remind_at)}.",
            ephemeral=True,
        )

    @interactions.slash_command(name='list', description='Daftar pengingat Anda.')
    async def list_reminders(self, ctx: interactions.SlashContext) -> None:
        if self.bot.reminder_repo is None or ctx.guild is None:
            await ctx.send("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        reminders = await self.bot.reminder_repo.list_for_user(ctx.guild.id, ctx.author.id)
        if not reminders:
            await ctx.send("Anda belum memiliki pengingat aktif.", ephemeral=True)
            return
        embed = interactions.Embed(title="Pengingat aktif", color=interactions.Color.blue())
        for reminder in reminders:
            waktu = datetime.fromisoformat(reminder["remind_at"])
            embed.add_field(
                name=f"ID {reminder['id']} pada {discord.utils.format_dt(waktu)}",
                value=reminder["message"],
                inline=False,
            )
        await ctx.send(embed=embed, ephemeral=True)

    @interactions.slash_command(name='delete', description='Hapus pengingat berdasarkan ID.')
    async def delete(self, ctx: interactions.SlashContext, reminder_id: int) -> None:
        if self.bot.reminder_repo is None or ctx.guild is None:
            await ctx.send("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        await self.bot.reminder_repo.delete(reminder_id)
        await ctx.send(f"Pengingat dengan ID {reminder_id} dihapus.", ephemeral=True)


def setup(bot: ForUS) -> None:
    Reminders(bot)
