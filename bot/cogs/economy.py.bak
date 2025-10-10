from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from bot.main import ForUS


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@app_commands.default_permissions(manage_guild=True)
class ShopAdmin(commands.GroupCog, name="shopadmin"):
    def __init__(self, bot: ForUS) -> None:
        super().__init__()
        self.bot = bot

    @app_commands.command(name="add", description="Tambah item ke shop")
    async def add_item(
        self,
        interaction: discord.Interaction,
        nama: str,
        harga: app_commands.Range[int, 0, 1_000_000],
        deskripsi: str,
        role_reward: discord.Role | None = None,
    ) -> None:
        if self.bot.shop_repo is None or interaction.guild is None:
            await interaction.response.send_message("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        await self.bot.shop_repo.add_item(interaction.guild.id, nama, harga, deskripsi, role_reward.id if role_reward else None)
        await interaction.response.send_message(f"Item {nama} ditambahkan dengan harga {harga} koin.", ephemeral=True)


class Economy(commands.Cog):
    def __init__(self, bot: ForUS) -> None:
        self.bot = bot
        self._shop_admin: ShopAdmin | None = None

    async def cog_load(self) -> None:
        self._shop_admin = ShopAdmin(self.bot)
        await self.bot.add_cog(self._shop_admin)

    async def cog_unload(self) -> None:
        await self.bot.remove_cog("ShopAdmin")
        self._shop_admin = None

    @app_commands.command(name="balance", description="Cek saldo ekonomi Anda")
    async def balance(self, interaction: discord.Interaction, pengguna: discord.User | None = None) -> None:
        if self.bot.economy_repo is None or interaction.guild is None:
            await interaction.response.send_message("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        target = pengguna or interaction.user
        saldo = await self.bot.economy_repo.get_balance(interaction.guild.id, target.id)
        await interaction.response.send_message(f"Saldo {target.mention}: {saldo:,} koin.")

    @app_commands.command(name="daily", description="Klaim hadiah harian.")
    async def daily(self, interaction: discord.Interaction) -> None:
        if self.bot.economy_repo is None or interaction.guild is None:
            await interaction.response.send_message("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        last_daily = await self.bot.economy_repo.get_daily_timestamp(interaction.guild.id, interaction.user.id)
        now = datetime.now(timezone.utc)
        if last_daily:
            last_time = datetime.fromisoformat(last_daily)
            if now - last_time < timedelta(hours=20):
                remaining = timedelta(hours=20) - (now - last_time)
                await interaction.response.send_message(
                    f"Tunggu {remaining.seconds // 3600} jam {remaining.seconds % 3600 // 60} menit lagi untuk klaim harian.",
                    ephemeral=True,
                )
                return
        amount = random.randint(150, 400)
        new_balance = await self.bot.economy_repo.update_balance(interaction.guild.id, interaction.user.id, amount)
        await self.bot.economy_repo.set_daily_timestamp(interaction.guild.id, interaction.user.id, _now_iso())
        await interaction.response.send_message(
            f"Berhasil klaim {amount} koin! Saldo Anda sekarang {new_balance}.",
            ephemeral=True,
        )

    @app_commands.command(name="transfer", description="Transfer saldo ke pengguna lain.")
    async def transfer(
        self,
        interaction: discord.Interaction,
        pengguna: discord.User,
        jumlah: app_commands.Range[int, 1, 1_000_000],
    ) -> None:
        if self.bot.economy_repo is None or interaction.guild is None:
            await interaction.response.send_message("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        if pengguna.id == interaction.user.id:
            await interaction.response.send_message("Tidak dapat transfer ke diri sendiri.", ephemeral=True)
            return
        saldo_pengirim = await self.bot.economy_repo.get_balance(interaction.guild.id, interaction.user.id)
        if saldo_pengirim < jumlah:
            await interaction.response.send_message("Saldo Anda tidak mencukupi.", ephemeral=True)
            return
        await self.bot.economy_repo.update_balance(interaction.guild.id, interaction.user.id, -jumlah)
        await self.bot.economy_repo.update_balance(interaction.guild.id, pengguna.id, jumlah)
        await interaction.response.send_message(
            f"Berhasil transfer {jumlah} koin ke {pengguna.mention}.",
            ephemeral=True,
        )

    @app_commands.command(name="leaderboard", description="Top saldo server.")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        if self.bot.economy_repo is None or interaction.guild is None:
            await interaction.response.send_message("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        top = await self.bot.economy_repo.top_balances(interaction.guild.id)
        if not top:
            await interaction.response.send_message("Belum ada data ekonomi.")
            return
        description = []
        for idx, (user_id, balance) in enumerate(top, start=1):
            member = interaction.guild.get_member(user_id) or user_id
            name = member.mention if isinstance(member, discord.Member) else f"<@{user_id}>"
            description.append(f"**{idx}.** {name} — {balance:,} koin")
        embed = discord.Embed(title="Papan Peringkat Ekonomi", description="\n".join(description), color=discord.Color.teal())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="work", description="Kerja untuk mendapatkan penghasilan.")
    async def work(self, interaction: discord.Interaction) -> None:
        if self.bot.economy_repo is None or interaction.guild is None:
            await interaction.response.send_message("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        reward = random.randint(50, 150)
        flavor = random.choice([
            "Anda membantu warga dan mendapat tip.",
            "Menyelesaikan proyek freelance.",
            "Menjual kerajinan tangan di pasar.",
        ])
        new_balance = await self.bot.economy_repo.update_balance(interaction.guild.id, interaction.user.id, reward)
        await interaction.response.send_message(f"{flavor} +{reward} koin. Saldo: {new_balance}.")

    @app_commands.command(name="gamble", description="Judikan koin Anda.")
    async def gamble(self, interaction: discord.Interaction, jumlah: app_commands.Range[int, 10, 200_000]) -> None:
        if self.bot.economy_repo is None or interaction.guild is None:
            await interaction.response.send_message("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        saldo = await self.bot.economy_repo.get_balance(interaction.guild.id, interaction.user.id)
        if saldo < jumlah:
            await interaction.response.send_message("Saldo tidak cukup.", ephemeral=True)
            return
        outcome = random.random()
        if outcome > 0.55:
            gain = jumlah
            new_balance = await self.bot.economy_repo.update_balance(interaction.guild.id, interaction.user.id, gain)
            await interaction.response.send_message(f"Anda menang! Saldo kini {new_balance}.")
        else:
            loss = -jumlah
            new_balance = await self.bot.economy_repo.update_balance(interaction.guild.id, interaction.user.id, loss)
            await interaction.response.send_message(f"Sayang sekali Anda kalah. Saldo kini {new_balance}.")

    shop = app_commands.Group(name="shop", description="Perintah toko server")

    @shop.command(name="list", description="Daftar item di toko.")
    async def shop_list(self, interaction: discord.Interaction) -> None:
        if self.bot.shop_repo is None or interaction.guild is None:
            await interaction.response.send_message("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        items = await self.bot.shop_repo.list_items(interaction.guild.id)
        if not items:
            await interaction.response.send_message("Belum ada item di toko.")
            return
        embed = discord.Embed(title="Toko Server", color=discord.Color.dark_gold())
        for item in items:
            reward = f" Role: <@&{item['role_reward_id']}>" if item.get("role_reward_id") else ""
            embed.add_field(
                name=f"{item['item_name']} — {item['price']} koin",
                value=f"{item.get('description', 'Tanpa deskripsi.')}{reward}",
                inline=False,
            )
        await interaction.response.send_message(embed=embed)

    @shop.command(name="buy", description="Beli item dari toko.")
    async def shop_buy(self, interaction: discord.Interaction, nama: str) -> None:
        if any(repo is None for repo in (self.bot.shop_repo, self.bot.economy_repo)) or interaction.guild is None:
            await interaction.response.send_message("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        item = await self.bot.shop_repo.get_item(interaction.guild.id, nama)
        if item is None:
            await interaction.response.send_message("Item tidak ditemukan.", ephemeral=True)
            return
        saldo = await self.bot.economy_repo.get_balance(interaction.guild.id, interaction.user.id)
        if saldo < item["price"]:
            await interaction.response.send_message("Saldo tidak cukup.", ephemeral=True)
            return
        await self.bot.economy_repo.update_balance(interaction.guild.id, interaction.user.id, -item["price"])
        if item.get("role_reward_id"):
            role = interaction.guild.get_role(int(item["role_reward_id"]))
            if role and isinstance(interaction.user, discord.Member):
                await interaction.user.add_roles(role, reason="Pembelian dari toko bot")
        await interaction.response.send_message(f"Berhasil membeli {item['item_name']} seharga {item['price']} koin!", ephemeral=True)


async def setup(bot: ForUS) -> None:
    await bot.add_cog(Economy(bot))
