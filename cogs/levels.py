import random
import time

import discord
from discord import app_commands
from discord.ext import commands

from rankcard import build_rank_card

XP_COOLDOWN = 45
XP_MIN, XP_MAX = 15, 25


def xp_for_level(level):
    return 5 * level * level + 50 * level + 100


class Levels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        now = time.time()
        db = self.bot.db
        row = await (
            await db.execute(
                "SELECT xp, level, last_message FROM xp WHERE guild_id = ? AND user_id = ?",
                (message.guild.id, message.author.id),
            )
        ).fetchone()

        if row and now - row["last_message"] < XP_COOLDOWN:
            return

        gained = random.randint(XP_MIN, XP_MAX)
        xp = (row["xp"] if row else 0) + gained
        level = row["level"] if row else 0

        leveled_up = False
        while xp >= xp_for_level(level):
            xp -= xp_for_level(level)
            level += 1
            leveled_up = True

        await db.execute(
            """INSERT INTO xp (guild_id, user_id, xp, level, last_message)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT (guild_id, user_id)
               DO UPDATE SET xp = ?, level = ?, last_message = ?""",
            (message.guild.id, message.author.id, xp, level, now, xp, level, now),
        )
        await db.commit()

        if leveled_up:
            await message.channel.send(
                f"🔥 {message.author.mention} reached **level {level}**!",
                delete_after=15,
            )

    @app_commands.command(name="rank", description="Show your rank card")
    @app_commands.describe(member="Whose card to show (defaults to you)")
    async def rank(self, interaction: discord.Interaction, member: discord.Member | None = None):
        member = member or interaction.user
        db = self.bot.db

        row = await (
            await db.execute(
                "SELECT xp, level FROM xp WHERE guild_id = ? AND user_id = ?",
                (interaction.guild_id, member.id),
            )
        ).fetchone()
        if not row:
            return await interaction.response.send_message(
                f"{member.display_name} hasn't earned any XP yet.", ephemeral=True
            )

        position = await (
            await db.execute(
                """SELECT COUNT(*) + 1 AS pos FROM xp
                   WHERE guild_id = ? AND (level > ? OR (level = ? AND xp > ?))""",
                (interaction.guild_id, row["level"], row["level"], row["xp"]),
            )
        ).fetchone()

        await interaction.response.defer()
        avatar = await member.display_avatar.replace(size=256, format="png").read()
        card = build_rank_card(
            member.display_name, avatar, row["level"], row["xp"],
            xp_for_level(row["level"]), position["pos"],
        )
        await interaction.followup.send(file=discord.File(card, "rank.png"))

    @app_commands.command(name="leaderboard", description="Top 10 most active members")
    async def leaderboard(self, interaction: discord.Interaction):
        rows = await (
            await self.bot.db.execute(
                """SELECT user_id, xp, level FROM xp WHERE guild_id = ?
                   ORDER BY level DESC, xp DESC LIMIT 10""",
                (interaction.guild_id,),
            )
        ).fetchall()
        if not rows:
            return await interaction.response.send_message("No activity yet.", ephemeral=True)

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, row in enumerate(rows):
            tag = medals[i] if i < 3 else f"`#{i + 1}`"
            lines.append(f"{tag} <@{row['user_id']}> — level {row['level']} ({row['xp']:,} xp)")

        embed = discord.Embed(
            title=f"{interaction.guild.name} — Leaderboard",
            description="\n".join(lines),
            color=0xFF6B35,
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Levels(bot))
