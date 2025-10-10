from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import interactions

if TYPE_CHECKING:
    from bot.main import ForUS


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ShopAdmin(interactions.Extension):
    # MANUAL REVIEW: GroupCog -> Extension with slash_command group
    def __init__(self, bot: ForUS) -> None:
        super().__init__()
        self.bot = bot

    @interactions.slash_command(
        name='shopadmin',
        description='Tambah item ke shop',
        default_member_permissions=interactions.Permissions.MANAGE_GUILD,
    )
    @interactions.slash_option(
        name="nama",
        description="Nama item",
        opt_type=interactions.OptionType.STRING,
        required=True,
    )
    @interactions.slash_option(
        name="harga",
        description="Harga item (0-1000000)",
        opt_type=interactions.OptionType.INTEGER,
        min_value=0,
        max_value=1_000_000,
        required=True,
    )
    @interactions.slash_option(
        name="deskripsi",
        description="Deskripsi item",
        opt_type=interactions.OptionType.STRING,
        required=True,
    )
    @interactions.slash_option(
        name="role_reward",
        description="Role yang diberikan saat membeli",
        opt_type=interactions.OptionType.ROLE,
        required=False,
    )
    async def add_item(
        self,
        ctx: interactions.SlashContext,
        nama: str,
        harga: int,
        deskripsi: str,
        role_reward: interactions.Role | None = None,
    ) -> None:
        if self.bot.shop_repo is None or ctx.guild is None:
            await ctx.send("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        await self.bot.shop_repo.add_item(ctx.guild.id, nama, harga, deskripsi, role_reward.id if role_reward else None)
        await ctx.send(f"Item {nama} ditambahkan dengan harga {harga} koin.", ephemeral=True)


class Economy(interactions.Extension):
    def __init__(self, bot: ForUS) -> None:
        self.bot = bot
        self._shop_admin: ShopAdmin | None = None

    @interactions.slash_command(name='balance', description='Cek saldo ekonomi Anda')
    @interactions.slash_option(
        name="pengguna",
        description="Pengguna yang ingin dicek saldonya (kosongkan untuk diri sendiri)",
        opt_type=interactions.OptionType.USER,
        required=False,
    )
    async def balance(self, ctx: interactions.SlashContext, pengguna: interactions.User | None = None) -> None:
        if self.bot.economy_repo is None or ctx.guild is None:
            await ctx.send("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        target = pengguna or ctx.author
        saldo = await self.bot.economy_repo.get_balance(ctx.guild.id, target.id)
        await ctx.send(f"Saldo {target.mention}: {saldo:,} koin.")

    @interactions.slash_command(name='daily', description='Klaim hadiah harian.')
    async def daily(self, ctx: interactions.SlashContext) -> None:
        if self.bot.economy_repo is None or ctx.guild is None:
            await ctx.send("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        last_daily = await self.bot.economy_repo.get_daily_timestamp(ctx.guild.id, ctx.author.id)
        now = datetime.now(timezone.utc)
        if last_daily:
            last_time = datetime.fromisoformat(last_daily)
            if now - last_time < timedelta(hours=20):
                remaining = timedelta(hours=20) - (now - last_time)
                await ctx.send(
                    f"Tunggu {remaining.seconds // 3600} jam {remaining.seconds % 3600 // 60} menit lagi untuk klaim harian.",
                    ephemeral=True,
                )
                return
        amount = random.randint(150, 400)
        new_balance = await self.bot.economy_repo.update_balance(ctx.guild.id, ctx.author.id, amount)
        await self.bot.economy_repo.set_daily_timestamp(ctx.guild.id, ctx.author.id, _now_iso())
        await ctx.send(
            f"Berhasil klaim {amount} koin! Saldo Anda sekarang {new_balance}.",
            ephemeral=True,
        )

    @interactions.slash_command(name='transfer', description='Transfer saldo ke pengguna lain.')
    @interactions.slash_option(
        name="pengguna",
        description="Pengguna tujuan",
        opt_type=interactions.OptionType.USER,
        required=True,
    )
    @interactions.slash_option(
        name="jumlah",
        description="Jumlah yang ditransfer (1-1000000)",
        opt_type=interactions.OptionType.INTEGER,
        min_value=1,
        max_value=1_000_000,
        required=True,
    )
    async def transfer(
        self,
        ctx: interactions.SlashContext,
        pengguna: interactions.User,
        jumlah: int,
    ) -> None:
        if self.bot.economy_repo is None or ctx.guild is None:
            await ctx.send("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        if pengguna.id == ctx.author.id:
            await ctx.send("Tidak dapat transfer ke diri sendiri.", ephemeral=True)
            return
        saldo_pengirim = await self.bot.economy_repo.get_balance(ctx.guild.id, ctx.author.id)
        if saldo_pengirim < jumlah:
            await ctx.send("Saldo Anda tidak mencukupi.", ephemeral=True)
            return
        await self.bot.economy_repo.update_balance(ctx.guild.id, ctx.author.id, -jumlah)
        await self.bot.economy_repo.update_balance(ctx.guild.id, pengguna.id, jumlah)
        await ctx.send(
            f"Berhasil transfer {jumlah} koin ke {pengguna.mention}.",
            ephemeral=True,
        )

    @interactions.slash_command(name='leaderboard', description='Top saldo server.')
    async def leaderboard(self, ctx: interactions.SlashContext) -> None:
        if self.bot.economy_repo is None or ctx.guild is None:
            await ctx.send("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        top = await self.bot.economy_repo.top_balances(ctx.guild.id)
        if not top:
            await ctx.send("Belum ada data ekonomi.")
            return
        description = []
        for idx, (user_id, balance) in enumerate(top, start=1):
            member = ctx.guild.get_member(user_id) or user_id
            name = member.mention if isinstance(member, interactions.Member) else f"<@{user_id}>"
            description.append(f"**{idx}.** {name} — {balance:,} koin")
        embed = interactions.Embed(title="Papan Peringkat Ekonomi", description="\n".join(description), color=interactions.Color.from_hex("#1ABC9C"))
        await ctx.send(embed=embed)

    @interactions.slash_command(name='work', description='Kerja untuk mendapatkan penghasilan.')
    async def work(self, ctx: interactions.SlashContext) -> None:
        if self.bot.economy_repo is None or ctx.guild is None:
            await ctx.send("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        reward = random.randint(50, 150)
        flavor = random.choice([
            "Anda membantu warga dan mendapat tip.",
            "Menyelesaikan proyek freelance.",
            "Menjual kerajinan tangan di pasar.",
        ])
        new_balance = await self.bot.economy_repo.update_balance(ctx.guild.id, ctx.author.id, reward)
        await ctx.send(f"{flavor} +{reward} koin. Saldo: {new_balance}.")

    @interactions.slash_command(name='gamble', description='Judikan koin Anda.')
    @interactions.slash_option(
        name="jumlah",
        description="Jumlah yang dijudikan (10-200000)",
        opt_type=interactions.OptionType.INTEGER,
        min_value=10,
        max_value=200_000,
        required=True,
    )
    async def gamble(self, ctx: interactions.SlashContext, jumlah: int) -> None:
        if self.bot.economy_repo is None or ctx.guild is None:
            await ctx.send("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        saldo = await self.bot.economy_repo.get_balance(ctx.guild.id, ctx.author.id)
        if saldo < jumlah:
            await ctx.send("Saldo tidak cukup.", ephemeral=True)
            return
        outcome = random.random()
        if outcome > 0.55:
            gain = jumlah
            new_balance = await self.bot.economy_repo.update_balance(ctx.guild.id, ctx.author.id, gain)
            await ctx.send(f"Anda menang! Saldo kini {new_balance}.")
        else:
            loss = -jumlah
            new_balance = await self.bot.economy_repo.update_balance(ctx.guild.id, ctx.author.id, loss)
            await ctx.send(f"Sayang sekali Anda kalah. Saldo kini {new_balance}.")

    @interactions.slash_command(
        name="shop",
        description="Perintah toko server",
        sub_cmd_name="list",
        sub_cmd_description="Daftar item di toko.",
    )
    async def shop_list(self, ctx: interactions.SlashContext) -> None:
        if self.bot.shop_repo is None or ctx.guild is None:
            await ctx.send("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        items = await self.bot.shop_repo.list_items(ctx.guild.id)
        if not items:
            await ctx.send("Belum ada item di toko.")
            return
        embed = interactions.Embed(title="Toko Server", color=interactions.Color.from_hex("#C27C0E"))
        for item in items:
            reward = f" Role: <@&{item['role_reward_id']}>" if item.get("role_reward_id") else ""
            embed.add_field(
                name=f"{item['item_name']} — {item['price']} koin",
                value=f"{item.get('description', 'Tanpa deskripsi.')}{reward}",
                inline=False,
            )
        await ctx.send(embed=embed)

    @interactions.slash_command(
        name="shop",
        description="Perintah toko server",
        sub_cmd_name="buy",
        sub_cmd_description="Beli item dari toko.",
    )
    @interactions.slash_option(
        name="nama",
        description="Nama item yang ingin dibeli",
        opt_type=interactions.OptionType.STRING,
        required=True,
    )
    async def shop_buy(self, ctx: interactions.SlashContext, nama: str) -> None:
        if any(repo is None for repo in (self.bot.shop_repo, self.bot.economy_repo)) or ctx.guild is None:
            await ctx.send("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        item = await self.bot.shop_repo.get_item(ctx.guild.id, nama)
        if item is None:
            await ctx.send("Item tidak ditemukan.", ephemeral=True)
            return
        saldo = await self.bot.economy_repo.get_balance(ctx.guild.id, ctx.author.id)
        if saldo < item["price"]:
            await ctx.send("Saldo tidak cukup.", ephemeral=True)
            return
        await self.bot.economy_repo.update_balance(ctx.guild.id, ctx.author.id, -item["price"])
        if item.get("role_reward_id"):
            role = ctx.guild.get_role(int(item["role_reward_id"]))
            if role and isinstance(ctx.author, interactions.Member):
                await ctx.author.add_roles(role, reason="Pembelian dari toko bot")
        await ctx.send(f"Berhasil membeli {item['item_name']} seharga {item['price']} koin!", ephemeral=True)


def setup(bot: ForUS) -> None:
    Economy(bot)
