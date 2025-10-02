from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from bot.main import ForUS


class Reminders(commands.GroupCog, name="reminder"):
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
            if channel and isinstance(channel, discord.TextChannel):
                await channel.send(f"<@{reminder['user_id']}> Pengingat: {reminder['message']}")
            else:
                member = guild.get_member(reminder["user_id"])
                if member:
                    try:
                        await member.send(f"Pengingat dari {guild.name}: {reminder['message']}")
                    except discord.Forbidden:
                        pass
            await self.bot.reminder_repo.delete(reminder_id)

    @app_commands.command(name="create", description="Buat pengingat baru dengan durasi tertentu.")
    @app_commands.describe(durasi_menit="Durasi sebelum pengingat (1-10080 menit)", pesan="Pesan pengingat", channel="Channel tujuan (opsional)")
    async def create(
        self,
        interaction: discord.Interaction,
        durasi_menit: app_commands.Range[int, 1, 10_080],
        pesan: str,
        channel: discord.TextChannel | None = None,
    ) -> None:
        if self.bot.reminder_repo is None or interaction.guild is None:
            await interaction.response.send_message("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        remind_at = datetime.now(timezone.utc) + timedelta(minutes=durasi_menit)
        reminder_id = await self.bot.reminder_repo.create(
            interaction.guild.id,
            interaction.user.id,
            pesan,
            remind_at.isoformat(),
            channel.id if channel else interaction.channel_id,
        )
        await self._schedule_reminder(reminder_id, remind_at)
        await interaction.response.send_message(
            f"Pengingat dibuat! ID: {reminder_id}. Saya akan mengingatkan pada {discord.utils.format_dt(remind_at)}.",
            ephemeral=True,
        )

    @app_commands.command(name="list", description="Daftar pengingat Anda.")
    async def list_reminders(self, interaction: discord.Interaction) -> None:
        if self.bot.reminder_repo is None or interaction.guild is None:
            await interaction.response.send_message("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        reminders = await self.bot.reminder_repo.list_for_user(interaction.guild.id, interaction.user.id)
        if not reminders:
            await interaction.response.send_message("Anda belum memiliki pengingat aktif.", ephemeral=True)
            return
        embed = discord.Embed(title="Pengingat aktif", color=discord.Color.blue())
        for reminder in reminders:
            waktu = datetime.fromisoformat(reminder["remind_at"])
            embed.add_field(
                name=f"ID {reminder['id']} pada {discord.utils.format_dt(waktu)}",
                value=reminder["message"],
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="delete", description="Hapus pengingat berdasarkan ID.")
    async def delete(self, interaction: discord.Interaction, reminder_id: int) -> None:
        if self.bot.reminder_repo is None or interaction.guild is None:
            await interaction.response.send_message("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        await self.bot.reminder_repo.delete(reminder_id)
        await interaction.response.send_message(f"Pengingat dengan ID {reminder_id} dihapus.", ephemeral=True)


async def setup(bot: ForUS) -> None:
    await bot.add_cog(Reminders(bot))
