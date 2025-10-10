from __future__ import annotations

import random
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Optional, Sequence

import interactions

if TYPE_CHECKING:
    from bot.main import ForUS

LOVE_COOLDOWN = timedelta(hours=20)
LOVE_SYNC_WINDOW = timedelta(hours=6)
LOVE_SYNC_BONUS = 12
MAX_OPTIONAL_MESSAGE = 240
MAX_PROFILE_BIO = 500
MAX_MEMORY_BODY = 600
MAX_MEMORIES = 50
CHECKIN_BASE_REWARD = 22
CHECKIN_STREAK_BONUS = 6
CHECKIN_MAX_BONUS = 48

GIFT_CATALOG: list[dict[str, object]] = [
    {
        "key": "flowers",
        "name": "Bukiet Bunga",
        "emoji": "💐",
        "cost": 250,
        "love": 35,
        "description": "Harum bunga pilihan untuk mengawali hari pasanganmu.",
    },
    {
        "key": "chocolate",
        "name": "Cokelat Artisan",
        "emoji": "🍫",
        "cost": 420,
        "love": 55,
        "description": "Sekotak cokelat premium dengan kartu ucapan manis.",
    },
    {
        "key": "stars",
        "name": "Lampu Bintang",
        "emoji": "🌟",
        "cost": 650,
        "love": 75,
        "description": "Proyektor galaksi untuk menemani malam panjang kalian.",
    },
    {
        "key": "ring",
        "name": "Cincin Janji",
        "emoji": "💍",
        "cost": 900,
        "love": 110,
        "description": "Simbol komitmen baru yang penuh makna.",
    },
    {
        "key": "vacation",
        "name": "Staycation Romantis",
        "emoji": "🏖️",
        "cost": 1400,
        "love": 150,
        "description": "Liburan singkat untuk mengisi ulang energi cinta kalian.",
    },
]
GIFT_LOOKUP = {gift["key"]: gift for gift in GIFT_CATALOG}

MILESTONE_DEFINITIONS: Sequence[dict[str, object]] = (
    {
        "key": "love_200",
        "type": "love_points",
        "threshold": 200,
        "title": "Benih Cinta",
        "description": "Mengumpulkan 200 love points pertama kalian.",
    },
    {
        "key": "love_500",
        "type": "love_points",
        "threshold": 500,
        "title": "Cinta Membara",
        "description": "Menembus 500 love points!",
    },
    {
        "key": "love_1000",
        "type": "love_points",
        "threshold": 1000,
        "title": "Legenda Asmara",
        "description": "1.000 love points, bukti cinta yang tak tergoyahkan.",
    },
    {
        "key": "streak_3",
        "type": "streak",
        "threshold": 3,
        "title": "Trio Hari Bahagia",
        "description": "Check-in bareng selama 3 hari berturut-turut.",
    },
    {
        "key": "streak_7",
        "type": "streak",
        "threshold": 7,
        "title": "Minggu Mesra",
        "description": "Menjaga check-in harian selama satu minggu penuh.",
    },
    {
        "key": "memory_5",
        "type": "memories",
        "threshold": 5,
        "title": "Album Kasih",
        "description": "Mencatat 5 memori romantis dalam jurnal cinta.",
    },
    {
        "key": "memory_15",
        "type": "memories",
        "threshold": 15,
        "title": "Sejuta Cerita",
        "description": "Mencapai 15 memori penuh kehangatan.",
    },
)

DATE_IDEAS: Sequence[str] = (
    "Masak resep baru bersama sambil memutar playlist nostalgia.",
    "Tulis surat cinta lalu bacakan bergantian di voice channel.",
    "Jadwalkan movie night dengan voting film favorit komunitas.",
    "Keliling kota virtual dengan mengganti foto profil dan status tematik.",
    "Lakukan sesi foto screenshot lucu di server dengan filter bot kamera.",
    "Mainkan truth or dare ringan khusus pasangan di channel privat.",
    "Buat daftar impian masa depan kalian dan pin di memori pasangan.",
    "Adakan piknik digital: share wallpaper pemandangan dan cerita kenangan.",
    "Bangun playlist duet dan dengarkan bareng.",
    "Susun bucket list traveling dan voting destinasi favorit komunitas.",
)

COMPATIBILITY_MESSAGES: Sequence[tuple[int, str]] = (
    (30, "Chemistry kalian masih perlu dipupuk, tapi potensinya besar!"),
    (60, "Sudah lumayan serasi—tetap rajin check-in ya!"),
    (80, "Kalian pasangan yang solid dan saling memahami."),
    (95, "Soulmate alert! Cinta kalian bikin server iri."),
    (101, "Definisi pasangan goals. Jagalah kebersamaan ini selamanya!"),
)


def _now() -> datetime:
    return datetime.now(UTC)


def _format_timedelta(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours} jam")
    if minutes:
        parts.append(f"{minutes} menit")
    if not parts:
        parts.append(f"{seconds} detik")
    return " ".join(parts)


def _format_duration_since(start: datetime, now: datetime) -> str:
    delta = now - start
    days = delta.days
    years, remaining_days = divmod(days, 365)
    months, days = divmod(remaining_days, 30)
    parts: list[str] = []
    if years:
        parts.append(f"{years} tahun")
    if months:
        parts.append(f"{months} bulan")
    if days:
        parts.append(f"{days} hari")
    if not parts:
        parts.append("baru saja")
    return ", ".join(parts)


def _normalize_hex_color(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = value.strip().lstrip("#")
    if len(cleaned) not in {3, 6}:
        return None
    if len(cleaned) == 3:
        cleaned = "".join(ch * 2 for ch in cleaned)
    if not all(ch in "0123456789abcdefABCDEF" for ch in cleaned):
        return None
    return f"#{cleaned.upper()}"


def _color_from_hex(value: Optional[str]) -> interactions.Color:
    if value is None:
        return interactions.Color.blurple()
    try:
        return interactions.Color(int(value.lstrip("#"), 16))
    except ValueError:
        return interactions.Color.blurple()


class Couples(interactions.Extension):
    # MANUAL REVIEW: GroupCog -> Extension with slash_command group
    def __init__(self, bot: ForUS) -> None:
        super().__init__()
        self.bot = bot

    async def _get_repo(self, ctx: interactions.SlashContext) -> Optional[tuple[int, ForUS]]:
        if ctx.guild is None:
            await ctx.send("Perintah ini hanya bisa dipakai di dalam server.", ephemeral=True)
            return None
        if self.bot.couple_repo is None:
            await ctx.send("Repositori pasangan belum siap. Coba lagi nanti.", ephemeral=True)
            return None
        return ctx.guild.id, self.bot

    async def _get_active_record(self, guild_id: int, ctx: interactions.SlashContext) -> Optional[object]:
        repo = self.bot.couple_repo
        assert repo is not None
        record = await repo.get_relationship(guild_id, ctx.author.id, statuses=("active",))
        if record is None:
            await ctx.send("Kamu belum memiliki pasangan aktif.", ephemeral=True)
            return None
        return record

    async def _check_milestones(self, record, *, profile=None, total_memories: Optional[int] = None) -> list[tuple[str, str]]:
        repo = self.bot.couple_repo
        assert repo is not None
        if profile is None:
            profile = await repo.get_profile(record.id)
        newly_unlocked: list[tuple[str, str]] = []
        achieved_keys = {milestone.milestone_key for milestone in await repo.list_milestones(record.id)}
        memories_count = total_memories
        for milestone in MILESTONE_DEFINITIONS:
            key = milestone["key"]
            if key in achieved_keys:
                continue
            m_type = milestone["type"]
            threshold = milestone["threshold"]
            achieved = False
            if m_type == "love_points":
                achieved = record.love_points >= threshold  # type: ignore[operator]
            elif m_type == "streak":
                achieved = profile.checkin_streak >= threshold  # type: ignore[operator]
            elif m_type == "memories":
                if memories_count is None:
                    memories_count = await repo.count_memories(record.id)
                achieved = memories_count >= threshold  # type: ignore[operator]
            if achieved:
                await repo.record_milestone(record.id, key)
                newly_unlocked.append((milestone["title"], milestone["description"]))
        return newly_unlocked

    def _gift_choices(self) -> Sequence[app_commands.Choice[str]]:
        return [
            app_commands.Choice(
                name=f"{gift['emoji']} {gift['name']} — {gift['cost']} koin",
                value=str(gift["key"]),
            )
            for gift in GIFT_CATALOG
        ]

    def _build_milestone_progress(self, record, profile, achieved_keys: set[str]) -> tuple[Optional[dict[str, object]], list[dict[str, object]]]:
        upcoming = None
        achievements: list[dict[str, object]] = []
        for milestone in MILESTONE_DEFINITIONS:
            entry = {
                "key": milestone["key"],
                "title": milestone["title"],
                "description": milestone["description"],
            }
            if entry["key"] in achieved_keys:
                achievements.append(entry)
                continue
            if upcoming is None:
                upcoming = entry
        return upcoming, achievements

    async def _build_status_embed(
        self,
        ctx: interactions.SlashContext,
        viewer: discord.abc.User,
        record,
    ) -> interactions.Embed:
        repo = self.bot.couple_repo
        assert repo is not None
        profile = await repo.get_profile(record.id)
        partner_id = record.partner_id(viewer.id)
        partner = await self._resolve_member(ctx.guild, partner_id) if partner_id else None
        embed = interactions.Embed(title="Status Pasangan", color=_color_from_hex(profile.theme_color))
        embed.add_field(name="Pengguna", value=viewer.mention, inline=True)
        partner_value = partner.mention if partner else (f"<@{partner_id}>" if partner_id else "-")
        embed.add_field(name="Pasangan", value=partner_value, inline=True)
        embed.add_field(name="Status", value=record.status.capitalize(), inline=True)

        if profile.title:
            embed.add_field(name="Julukan Cinta", value=profile.title, inline=True)
        if profile.current_mood:
            embed.add_field(name="Mood", value=profile.current_mood, inline=True)
        if profile.love_song:
            embed.add_field(name="Lagu Favorit", value=profile.love_song, inline=False)

        embed.add_field(name="Love Points", value=str(record.love_points), inline=True)

        now = _now()
        if record.anniversary:
            try:
                ann_date = datetime.fromisoformat(record.anniversary)
                embed.add_field(name="Tanggal Anniversary", value=record.anniversary, inline=True)
                embed.add_field(name="Lama Bersama", value=_format_duration_since(ann_date, now), inline=True)
            except ValueError:
                embed.add_field(name="Tanggal Anniversary", value=record.anniversary, inline=True)

        last_user = record.last_affection_for(viewer.id)
        partner_last = record.last_affection_for(partner_id or 0) if partner_id else None
        if last_user:
            try:
                last_dt = datetime.fromisoformat(last_user)
                embed.add_field(name="Afirmasi Terakhirmu", value=_format_timedelta(now - last_dt), inline=True)
            except ValueError:
                pass
        if partner_last:
            try:
                partner_dt = datetime.fromisoformat(partner_last)
                embed.add_field(name="Afirmasi Dari Pasangan", value=_format_timedelta(now - partner_dt), inline=True)
            except ValueError:
                pass

        if profile.checkin_streak:
            streak_value = f"{profile.checkin_streak} hari"
            if profile.last_checkin_date:
                streak_value += f" (terakhir {profile.last_checkin_date})"
            embed.add_field(name="Streak Check-in", value=streak_value, inline=True)

        latest_memory = await repo.get_latest_memory(record.id)
        if latest_memory:
            memory_display = f"**{latest_memory.title}** — {latest_memory.description or 'Tanpa deskripsi'}"
            embed.add_field(name="Memori Terbaru", value=memory_display[:1024], inline=False)

        achieved = await repo.list_milestones(record.id)
        achieved_keys = {milestone.milestone_key for milestone in achieved}
        upcoming, achievements = self._build_milestone_progress(record, profile, achieved_keys)
        if achievements:
            lines = [f"✅ {entry['title']}" for entry in achievements[-3:]]
            embed.add_field(name="Milestone Tercapai", value="\n".join(lines), inline=False)
        if upcoming:
            embed.add_field(name="Target Berikutnya", value=f"🎯 {upcoming['title']} — {upcoming['description']}", inline=False)

        if profile.bio:
            embed.add_field(name="Bio", value=profile.bio[:1024], inline=False)

        return embed

    async def _resolve_member(self, guild: interactions.Guild, user_id: int) -> Optional[interactions.Member]:
        member = guild.get_member(user_id)
        if member is None:
            try:
                member = await guild.fetch_member(user_id)
            except discord.HTTPException:
                return None
        return member

    @interactions.slash_command(name='propose', description='Ajukan pasangan kepada seseorang spesial.')
    @app_commands.describe(pasangan="Pengguna yang ingin diajak menjadi pasangan", pesan="Pesan manis opsional")
    async def propose(self, ctx: interactions.SlashContext, pasangan: interactions.User, pesan: Optional[str] = None) -> None:
        repo_info = await self._get_repo(interaction)
        if repo_info is None:
            return
        guild_id, bot = repo_info
        repo = bot.couple_repo
        assert ctx.guild is not None
        assert repo is not None

        if pasangan.bot:
            await ctx.send("Kamu tidak bisa berpasangan dengan bot.", ephemeral=True)
            return
        if pasangan.id == ctx.author.id:
            await ctx.send("Cinta diri itu penting, tapi pilihlah pasangan lain.", ephemeral=True)
            return
        if pesan and len(pesan) > MAX_OPTIONAL_MESSAGE:
            await ctx.send("Pesan terlalu panjang (maksimal 240 karakter).", ephemeral=True)
            return

        # Cek apakah kedua pihak masih kosong
        if await repo.user_has_active_or_pending(guild_id, ctx.author.id):
            await ctx.send("Kamu sudah memiliki pasangan atau lamaran yang belum selesai.", ephemeral=True)
            return
        if await repo.user_has_active_or_pending(guild_id, pasangan.id):
            await ctx.send(f"{pasangan.mention} sudah memiliki pasangan atau lamaran lain.", ephemeral=True)
            return

        existing = await repo.get_pair(guild_id, ctx.author.id, pasangan.id)
        if existing and existing.status == "pending":
            await ctx.send("Lamaranmu sebelumnya masih menunggu jawaban.", ephemeral=True)
            return
        if existing and existing.status == "active":
            await ctx.send("Kalian sudah resmi menjadi pasangan!", ephemeral=True)
            return

        record = await repo.create_proposal(guild_id, ctx.author.id, pasangan.id, pesan)
        embed = interactions.Embed(
            title="💝 Lamaran Baru!",
            description=f"{ctx.author.mention} mengajak {pasangan.mention} menjadi pasangan!",
            color=interactions.Color.magenta(),
        )
        if pesan:
            embed.add_field(name="Pesan", value=pesan, inline=False)
        embed.set_footer(text="Gunakan /couple respond untuk menjawab lamaran.")

        await ctx.send(
            embed=embed,
            allowed_mentions=discord.AllowedMentions(users=[ctx.author, pasangan]),
        )

        try:
            await pasangan.send(
                f"{ctx.author.display_name} mengajakmu jadi pasangan di server {ctx.guild.name}! Gunakan /couple respond di server untuk menjawab."
            )
        except discord.Forbidden:
            pass

    @app_commands.choices(keputusan=[
        app_commands.Choice(name="Terima", value="accept"),
        app_commands.Choice(name="Tolak", value="reject"),
    ])
    @app_commands.describe(keputusan="Jawabanmu atas lamaran", pesan="Pesan opsional untuk pasangan")
    @interactions.slash_command(name='respond', description='Jawab lamaran pasangan yang masuk.')
    async def respond(self, ctx: interactions.SlashContext, keputusan: app_commands.Choice[str], pesan: Optional[str] = None) -> None:
        repo_info = await self._get_repo(interaction)
        if repo_info is None:
            return
        guild_id, bot = repo_info
        repo = bot.couple_repo
        assert ctx.guild is not None
        assert repo is not None

        if pesan and len(pesan) > MAX_OPTIONAL_MESSAGE:
            await ctx.send("Pesan terlalu panjang (maksimal 240 karakter).", ephemeral=True)
            return

        pending = await repo.get_pending_for_target(guild_id, ctx.author.id)
        if pending is None:
            await ctx.send("Tidak ada lamaran yang perlu kamu jawab saat ini.", ephemeral=True)
            return

        initiator_id = pending.partner_id(ctx.author.id)
        initiator = await self._resolve_member(ctx.guild, initiator_id) if initiator_id else None

        if keputusan.value == "accept":
            updated = await repo.accept_proposal(pending.id)
            if updated is None or updated.status != "active":
                await ctx.send("Lamaran sudah tidak berlaku.", ephemeral=True)
                return
            now = _now()
            anniversary = updated.anniversary
            ann_display = "hari ini" if not anniversary else anniversary
            embed = interactions.Embed(
                title="💞 Selamat!",
                description=f"{ctx.author.mention} menerima lamaran {initiator.mention if initiator else '<pasangan>'}!",
                color=interactions.Color.magenta(),
            )
            embed.add_field(name="Tanggal Anniversary", value=ann_display, inline=True)
            embed.add_field(name="Love Points", value=str(updated.love_points), inline=True)
            embed.set_footer(text="Kirim /couple affection setiap hari untuk menambah love points!")
            await ctx.send(
                embed=embed,
                allowed_mentions=discord.AllowedMentions(users=[ctx.author] + ([initiator] if initiator else [])),
            )
            if initiator:
                dm_message = f"{ctx.author.display_name} menerima lamaranmu!"
                if pesan:
                    dm_message += f" Pesannya: {pesan}"
                try:
                    await initiator.send(dm_message)
                except discord.Forbidden:
                    pass
        else:
            updated = await repo.reject_proposal(pending.id, ctx.author.id)
            await ctx.send("Lamaran telah ditolak. Semoga kamu nyaman dengan keputusanmu.", ephemeral=True)
            if initiator:
                message = f"{ctx.author.display_name} menolak lamarannya."
                if pesan:
                    message += f" Pesannya: {pesan}"
                try:
                    await initiator.send(message)
                except discord.Forbidden:
                    pass

    @app_commands.describe(target="Cek status pasangan untuk pengguna tertentu (opsional)")
    @interactions.slash_command(name='status', description='Lihat status hubunganmu atau orang lain.')
    async def status(self, ctx: interactions.SlashContext, target: Optional[interactions.User] = None) -> None:
        repo_info = await self._get_repo(interaction)
        if repo_info is None:
            return
        guild_id, bot = repo_info
        repo = bot.couple_repo
        assert ctx.guild is not None
        assert repo is not None

        user = target or ctx.author
        record = await repo.get_relationship(guild_id, user.id, statuses=("pending", "active"))
        if record is None:
            await ctx.send("Belum ada data pasangan untuk pengguna tersebut.", ephemeral=True)
            return
        embed = await self._build_status_embed(interaction, user, record)
        await ctx.send(embed=embed, ephemeral=True)

    anniversary = app_commands.Group(name="anniversary", description="Kelola tanggal anniversary pasangan")

    @anniversary.command(name="set", description="Atur tanggal anniversary (format YYYY-MM-DD)")
    async def anniversary_set(self, ctx: interactions.SlashContext, tanggal: str) -> None:
        repo_info = await self._get_repo(interaction)
        if repo_info is None:
            return
        guild_id, bot = repo_info
        repo = bot.couple_repo
        assert ctx.guild is not None
        assert repo is not None

        record = await repo.get_relationship(guild_id, ctx.author.id, statuses=("active",))
        if record is None:
            await ctx.send("Kamu belum memiliki pasangan aktif untuk mengatur anniversary.", ephemeral=True)
            return

        try:
            parsed = datetime.fromisoformat(tanggal)
        except ValueError:
            await ctx.send("Format tanggal tidak valid. Gunakan YYYY-MM-DD.", ephemeral=True)
            return

        updated = await repo.update_anniversary(record.id, parsed.date().isoformat())
        if updated is None:
            await ctx.send("Gagal memperbarui tanggal anniversary.", ephemeral=True)
            return

        await ctx.send(
            f"Tanggal anniversary diperbarui menjadi {parsed.date().isoformat()}.",
            ephemeral=True,
        )

    profile = app_commands.Group(name="profile", description="Atur profil cinta kalian")

    @profile.command(name="view", description="Lihat profil romantis pasanganmu.")
    async def profile_view(self, ctx: interactions.SlashContext) -> None:
        repo_info = await self._get_repo(interaction)
        if repo_info is None:
            return
        guild_id, _ = repo_info
        record = await self._get_active_record(guild_id, interaction)
        if record is None:
            return
        embed = await self._build_status_embed(interaction, ctx.author, record)
        embed.title = "Profil Cinta"
        await ctx.send(embed=embed, ephemeral=True)

    @profile.command(name="edit", description="Perbarui profil cinta kalian.")
    @app_commands.describe(
        title="Julukan romantis kalian",
        theme_color="Warna tema (hex, contoh #FF66AA)",
        love_song="Lagu favorit berdua",
        bio="Deskripsi singkat hubungan (maks 500 karakter)",
        mood="Mood hari ini",
    )
    async def profile_edit(
        self,
        ctx: interactions.SlashContext,
        title: Optional[str] = None,
        theme_color: Optional[str] = None,
        love_song: Optional[str] = None,
        bio: Optional[str] = None,
        mood: Optional[str] = None,
    ) -> None:
        repo_info = await self._get_repo(interaction)
        if repo_info is None:
            return
        guild_id, _ = repo_info
        repo = self.bot.couple_repo
        assert repo is not None
        record = await self._get_active_record(guild_id, interaction)
        if record is None:
            return

        updates: dict[str, object] = {}
        if title is not None:
            if len(title) > 80:
                await ctx.send("Judul terlalu panjang (maksimal 80 karakter).", ephemeral=True)
                return
            updates["title"] = title
        if theme_color is not None:
            normalized = _normalize_hex_color(theme_color)
            if normalized is None:
                await ctx.send("Warna tidak valid. Gunakan format hex seperti #FF6699.", ephemeral=True)
                return
            updates["theme_color"] = normalized
        if love_song is not None:
            if len(love_song) > 200:
                await ctx.send("Lagu favorit terlalu panjang (maksimal 200 karakter).", ephemeral=True)
                return
            updates["love_song"] = love_song
        if bio is not None:
            if len(bio) > MAX_PROFILE_BIO:
                await ctx.send("Bio terlalu panjang (maksimal 500 karakter).", ephemeral=True)
                return
            updates["bio"] = bio
        if mood is not None:
            if len(mood) > 50:
                await ctx.send("Mood terlalu panjang (maksimal 50 karakter).", ephemeral=True)
                return
            updates["current_mood"] = mood

        if not updates:
            await ctx.send("Tidak ada perubahan yang diberikan.", ephemeral=True)
            return

        profile = await repo.update_profile(record.id, **updates)
        await ctx.send("Profil cinta berhasil diperbarui!", ephemeral=True)

        embed = await self._build_status_embed(interaction, ctx.author, record)
        embed.title = "Profil Cinta Terbaru"
        embed.colour = _color_from_hex(profile.theme_color)
        await ctx.send(embed=embed, ephemeral=True)

    memory = app_commands.Group(name="memory", description="Kelola jurnal memori kalian")

    @memory.command(name="add", description="Tambahkan memori romantis ke jurnal.")
    async def memory_add(self, ctx: interactions.SlashContext, judul: str, cerita: Optional[str] = None) -> None:
        repo_info = await self._get_repo(interaction)
        if repo_info is None:
            return
        guild_id, _ = repo_info
        repo = self.bot.couple_repo
        assert repo is not None
        record = await self._get_active_record(guild_id, interaction)
        if record is None:
            return

        if len(judul) > 80:
            await ctx.send("Judul memori terlalu panjang (maksimal 80 karakter).", ephemeral=True)
            return
        if cerita and len(cerita) > MAX_MEMORY_BODY:
            await ctx.send("Cerita terlalu panjang (maksimal 600 karakter).", ephemeral=True)
            return
        total_memories = await repo.count_memories(record.id)
        if total_memories >= MAX_MEMORIES:
            await ctx.send("Album memori penuh. Hapus memori lama sebelum menambah yang baru.", ephemeral=True)
            return

        memory_entry = await repo.add_memory(record.id, judul, cerita, ctx.author.id)
        await ctx.send("Memori baru tersimpan!", ephemeral=True)

        unlocked = await self._check_milestones(record, total_memories=total_memories + 1)
        if unlocked:
            lines = [f"🏆 {title}\n→ {desc}" for title, desc in unlocked]
            await ctx.send("\n".join(lines), ephemeral=True)

        partner_id = record.partner_id(ctx.author.id)
        if partner_id:
            partner = await self._resolve_member(ctx.guild, partner_id) if ctx.guild else None
            if partner:
                try:
                    preview = memory_entry.description or "Tanpa deskripsi tambahan"
                    await partner.send(
                        f"{ctx.author.display_name} menambahkan memori baru: **{memory_entry.title}**\n{preview[:200]}"
                    )
                except discord.Forbidden:
                    pass

    @memory.command(name="list", description="Tampilkan memori terbaru kalian.")
    async def memory_list(self, ctx: interactions.SlashContext, jumlah: app_commands.Range[int, 1, 10] = 5) -> None:
        repo_info = await self._get_repo(interaction)
        if repo_info is None:
            return
        guild_id, _ = repo_info
        repo = self.bot.couple_repo
        assert repo is not None
        record = await repo.get_relationship(guild_id, ctx.author.id, statuses=("active", "ended"))
        if record is None:
            await ctx.send("Belum ada memori yang bisa ditampilkan.", ephemeral=True)
            return

        memories = await repo.list_memories(record.id, limit=jumlah)
        if not memories:
            await ctx.send("Album memori masih kosong.", ephemeral=True)
            return

        embed = interactions.Embed(title="Memori Romantis", color=interactions.Color.gold())
        for mem in memories:
            value = mem.description or "(Tanpa deskripsi)"
            embed.add_field(name=f"#{mem.id} — {mem.title}", value=value[:1024], inline=False)
        await ctx.send(embed=embed, ephemeral=True)

    @memory.command(name="delete", description="Hapus memori berdasarkan ID.")
    async def memory_delete(self, ctx: interactions.SlashContext, memori_id: int) -> None:
        repo_info = await self._get_repo(interaction)
        if repo_info is None:
            return
        guild_id, _ = repo_info
        repo = self.bot.couple_repo
        assert repo is not None
        record = await self._get_active_record(guild_id, interaction)
        if record is None:
            return

        success = await repo.delete_memory(record.id, memori_id)
        if success:
            await ctx.send("Memori berhasil dihapus.", ephemeral=True)
        else:
            await ctx.send("Memori tidak ditemukan.", ephemeral=True)

    @interactions.slash_command(name='affection', description='Tambahkan love points harian bersama pasangan.')
    async def affection(self, ctx: interactions.SlashContext) -> None:
        repo_info = await self._get_repo(interaction)
        if repo_info is None:
            return
        guild_id, bot = repo_info
        repo = bot.couple_repo
        assert ctx.guild is not None
        assert repo is not None

        record = await repo.get_relationship(guild_id, ctx.author.id, statuses=("active",))
        if record is None:
            await ctx.send("Kamu belum memiliki pasangan aktif.", ephemeral=True)
            return

        now = _now()
        last_str = record.last_affection_for(ctx.author.id)
        if last_str:
            try:
                last_dt = datetime.fromisoformat(last_str)
            except ValueError:
                last_dt = None
            if last_dt and now - last_dt < LOVE_COOLDOWN:
                remaining = LOVE_COOLDOWN - (now - last_dt)
                await ctx.send(
                    f"Kamu bisa mengirim love point lagi dalam {_format_timedelta(remaining)}.",
                    ephemeral=True,
                )
                return

        partner_id = record.partner_id(ctx.author.id)
        partner_last = record.last_affection_for(partner_id or 0) if partner_id else None
        base_points = random.randint(18, 40)
        bonus = 0
        if partner_last:
            try:
                partner_dt = datetime.fromisoformat(partner_last)
                if abs((now - partner_dt).total_seconds()) <= LOVE_SYNC_WINDOW.total_seconds():
                    bonus = LOVE_SYNC_BONUS
            except ValueError:
                bonus = 0

        total = base_points + bonus
        updated = await repo.add_love_points(record.id, total)
        if updated is None:
            await ctx.send("Gagal memperbarui love points.", ephemeral=True)
            return
        await repo.update_last_affection(updated, ctx.author.id, now.isoformat())

        description = f"Love points bertambah **{total}**"
        if bonus:
            description += f" (bonus {bonus})"
        description += f". Total sekarang **{updated.love_points}**."
        if partner_last and bonus:
            description += " Kamu mendapat bonus karena kompak dengan pasangan!"
        await ctx.send(description, ephemeral=True)

        unlocked = await self._check_milestones(updated)
        if unlocked:
            lines = [f"🏆 {title}\n→ {desc}" for title, desc in unlocked]
            await ctx.send("\n".join(lines), ephemeral=True)

    @interactions.slash_command(name='leaderboard', description='Lihat pasangan paling romantis di server.')
    async def leaderboard(self, ctx: interactions.SlashContext) -> None:
        repo_info = await self._get_repo(interaction)
        if repo_info is None:
            return
        guild_id, bot = repo_info
        repo = bot.couple_repo
        assert ctx.guild is not None
        assert repo is not None

        records = await repo.list_leaderboard(guild_id, limit=10)
        if not records:
            await ctx.send("Belum ada pasangan aktif di server ini.")
            return

        lines: list[str] = []
        for idx, record in enumerate(records, start=1):
            one = await self._resolve_member(ctx.guild, record.member_one_id)
            two = await self._resolve_member(ctx.guild, record.member_two_id)
            name_one = one.mention if one else f"<@{record.member_one_id}>"
            name_two = two.mention if two else f"<@{record.member_two_id}>"
            crown = "👑 " if idx == 1 else ""
            lines.append(f"{crown}**{idx}.** {name_one} ❤️ {name_two} — {record.love_points} LP")

        embed = interactions.Embed(title="Papan Cinta Server", description="\n".join(lines), color=interactions.Color.red())
        await ctx.send(embed=embed)

    @interactions.slash_command(name='breakup', description='Akhiri hubungan dengan pasangan saat ini.')
    @app_commands.describe(alasan="Alasan opsional untuk pasanganmu")
    async def breakup(self, ctx: interactions.SlashContext, alasan: Optional[str] = None) -> None:
        repo_info = await self._get_repo(interaction)
        if repo_info is None:
            return
        guild_id, bot = repo_info
        repo = bot.couple_repo
        assert ctx.guild is not None
        assert repo is not None

        if alasan and len(alasan) > MAX_OPTIONAL_MESSAGE:
            await ctx.send("Alasan terlalu panjang (maksimal 240 karakter).", ephemeral=True)
            return

        record = await repo.get_relationship(guild_id, ctx.author.id, statuses=("active",))
        if record is None:
            await ctx.send("Tidak ada hubungan aktif yang bisa diakhiri.", ephemeral=True)
            return

        updated = await repo.end_relationship(record.id, ctx.author.id)
        if updated is None:
            await ctx.send("Terjadi kesalahan saat mengakhiri hubungan.", ephemeral=True)
            return

        partner_id = record.partner_id(ctx.author.id)
        partner = await self._resolve_member(ctx.guild, partner_id) if partner_id else None
        await ctx.send("Hubungan telah diakhiri. Semoga keputusanmu membawa kebaikan.", ephemeral=True)

        if partner:
            reason = f" Pesan darinya: {alasan}" if alasan else ""
            try:
                await partner.send(
                    f"{ctx.author.display_name} mengakhiri hubungan kalian di server {ctx.guild.name}.{reason}"
                )
            except discord.Forbidden:
                pass


def setup(bot: ForUS) -> None:
    Couples(bot)
