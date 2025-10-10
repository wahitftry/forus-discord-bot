from __future__ import annotations

from datetime import datetime, timedelta, timezone as dt_timezone
from typing import TYPE_CHECKING, Any

import interactions

if TYPE_CHECKING:
    from bot.main import ForUS


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=dt_timezone.utc)
    raw = str(value)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        try:
            parsed = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_timezone.utc)
    return parsed


def _truncate(value: str | None, limit: int = 180) -> str:
    if not value:
        return "-"
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


# Permissions moved to command decorators
class Audit(interactions.Extension):
    # MANUAL REVIEW: GroupCog -> Extension with slash_command group
    def __init__(self, bot: ForUS) -> None:
        super().__init__()
        self.bot = bot

    async def _ensure_repo(self, ctx: interactions.SlashContext) -> tuple[int | None, Any]:
        guild = ctx.guild
        if guild is None:
            await ctx.send("Perintah ini hanya dapat digunakan dalam server.", ephemeral=True)
            return None, None
        repo = self.bot.audit_repo
        if repo is None:
            await ctx.send("Repositori audit belum siap.", ephemeral=True)
            return None, None
        return guild.id, repo

    @interactions.slash_command(name='recent', description='Tampilkan catatan audit internal terbaru.')
    @interactions.slash_option(
        name="jumlah",
        description="Jumlah catatan terbaru yang diambil (1-20)",
        opt_type=interactions.OptionType.INTEGER,
        min_value=1,
        max_value=20,
        required=False,
        autocomplete=True,
    )
    @interactions.slash_option(
        name="aksi",
        description="Filter prefix aksi. Kosongkan untuk menampilkan semua.",
        opt_type=interactions.OptionType.STRING,
        required=False,
        autocomplete=True,
    )
    async def recent(
        self,
        ctx: interactions.SlashContext,
        jumlah: int = 10,
        aksi: str | None = None,
    ) -> None:
        guild_id, repo = await self._ensure_repo(interaction)
        if repo is None or guild_id is None:
            return

        entries = await repo.recent_entries(guild_id, limit=int(jumlah), action_prefix=aksi.strip() if aksi else None)
        if not entries:
            await ctx.send("Belum ada log audit yang tersimpan dengan filter tersebut.", ephemeral=True)
            return

        embed = interactions.Embed(title="Log Audit Terbaru", color=interactions.Color.from_hex("#C27C0E"))
        if aksi:
            embed.description = f"Filter aksi: `{aksi.strip()}`"

        for entry in entries:
            created_at = _parse_timestamp(entry.get("created_at"))
            action = str(entry.get("action", "tidak diketahui"))
            actor_id = entry.get("actor_id")
            target_id = entry.get("target_id")
            context = _truncate(entry.get("context"))

            timestamp_text = "Waktu tidak diketahui"
            relative_text = ""
            if created_at:
                timestamp_text = discord.utils.format_dt(created_at, style="F")
                relative_text = discord.utils.format_dt(created_at, style="R")

            field_name = f"{action} — {timestamp_text}"
            field_value_parts = [
                f"Aktor: {f'<@{actor_id}>' if actor_id else 'Tidak diketahui'}",
                f"Target: {f'<@{target_id}>' if target_id else '-'}",
                f"Context: {context}",
            ]
            if relative_text:
                field_value_parts.append(f"Relative: {relative_text}")
            embed.add_field(name=field_name, value="\n".join(field_value_parts), inline=False)

        embed.set_footer(text="Data audit disimpan secara terpisah dari Audit Log Discord sebagai histori internal bot.")
        await ctx.send(embed=embed, ephemeral=True)

    @recent.autocomplete("aksi")
    async def recent_action_autocomplete(
        self,
        ctx: interactions.SlashContext,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        guild = ctx.guild
        repo = self.bot.audit_repo
        if guild is None or repo is None:
            return []
        summary = await repo.action_summary(guild.id, limit=10)
        normalized = ctx.input_text.strip().lower()
        choices: list[interactions.SlashCommandChoice] = []
        for action, _ in summary:
            if normalized and normalized not in action.lower():
                continue
            choices.append(interactions.SlashCommandChoice(name=action, value=action))
        await ctx.send(choices=choices[:25])

    @interactions.slash_command(name='stats', description='Ringkasan frekuensi aksi audit dalam periode tertentu.')
    @interactions.slash_option(
        name="hari",
        description="Jumlah hari terakhir yang dihitung (1-30)",
        opt_type=interactions.OptionType.INTEGER,
        min_value=1,
        max_value=30,
        required=False,
    )
    @interactions.slash_option(
        name="batas",
        description="Jumlah aksi teratas yang ditampilkan (1-15)",
        opt_type=interactions.OptionType.INTEGER,
        min_value=1,
        max_value=15,
        required=False,
    )
    async def stats(
        self,
        ctx: interactions.SlashContext,
        hari: int = 7,
        batas: int = 10,
    ) -> None:
        guild_id, repo = await self._ensure_repo(interaction)
        if repo is None or guild_id is None:
            return

        since_dt = datetime.now(dt_timezone.utc) - timedelta(days=hari)
        since_iso = since_dt.isoformat()

        actions = await repo.action_summary(guild_id, limit=int(batas), since=since_iso)
        if not actions:
            await ctx.send(
                "Belum ada aktivitas audit pada rentang waktu tersebut.",
                ephemeral=True,
            )
            return

        total_entries = sum(total for _, total in actions)
        actors = await repo.actor_summary(guild_id, limit=5, since=since_iso)

        embed = interactions.Embed(title="Ringkasan Audit", color=interactions.Color.from_hex("#E67E22"))
        embed.description = (
            f"Periode sejak {discord.utils.format_dt(since_dt, style='F')} "
            f"({discord.utils.format_dt(since_dt, style='R')})"
        )
        for action, total in actions:
            embed.add_field(name=action, value=str(total), inline=True)

        if actors:
            lines = []
            for actor_id, total in actors:
                mention = f"<@{actor_id}>" if actor_id else "Tidak diketahui"
                lines.append(f"{mention}: {total}")
            embed.add_field(name="Top Aktor", value="\n".join(lines), inline=False)

        embed.add_field(name="Total entri", value=str(total_entries), inline=True)
        embed.set_footer(text="Audit internal membantu melacak tindakan bot seperti automasi dan jadwal.")
        await ctx.send(embed=embed, ephemeral=True)


def setup(bot: ForUS) -> None:
    Audit(bot)
