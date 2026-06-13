import datetime
import re
import time
from collections import defaultdict, deque

import discord
from discord import app_commands
from discord.ext import commands

SPAM_WINDOW = 6
SPAM_LIMIT = 5
CAPS_MIN_LEN = 12
CAPS_RATIO = 0.75
INVITE_RE = re.compile(r"(discord\.gg|discord\.com/invite)/\w+", re.I)
WARN_TIMEOUT_THRESHOLD = 3


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.recent = defaultdict(lambda: deque(maxlen=SPAM_LIMIT))

    async def add_warning(self, guild_id, user_id, moderator_id, reason):
        db = self.bot.db
        await db.execute(
            "INSERT INTO warnings (guild_id, user_id, moderator_id, reason, created_at) VALUES (?, ?, ?, ?, ?)",
            (guild_id, user_id, moderator_id, reason, time.time()),
        )
        await db.commit()
        row = await (
            await db.execute(
                "SELECT COUNT(*) AS n FROM warnings WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            )
        ).fetchone()
        return row["n"]

    async def punish(self, message, reason):
        try:
            await message.delete()
        except discord.HTTPException:
            pass

        count = await self.add_warning(
            message.guild.id, message.author.id, self.bot.user.id, reason
        )
        note = f"⚠️ {message.author.mention} — {reason} (warning {count})"

        if count >= WARN_TIMEOUT_THRESHOLD:
            try:
                until = discord.utils.utcnow() + datetime.timedelta(minutes=10)
                await message.author.timeout(until, reason=f"Automod: {count} warnings")
                note += " · timed out for 10 minutes"
            except discord.HTTPException:
                pass

        await message.channel.send(note, delete_after=12)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        if message.author.guild_permissions.manage_messages:
            return

        if INVITE_RE.search(message.content):
            return await self.punish(message, "invite links are not allowed")

        letters = [c for c in message.content if c.isalpha()]
        if len(letters) >= CAPS_MIN_LEN:
            upper = sum(1 for c in letters if c.isupper())
            if upper / len(letters) >= CAPS_RATIO:
                return await self.punish(message, "easy on the caps lock")

        bucket = self.recent[(message.guild.id, message.author.id)]
        now = time.time()
        bucket.append(now)
        if len(bucket) == SPAM_LIMIT and now - bucket[0] < SPAM_WINDOW:
            bucket.clear()
            return await self.punish(message, "slow down, that's spam")

    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        count = await self.add_warning(
            interaction.guild_id, member.id, interaction.user.id, reason
        )
        await interaction.response.send_message(
            f"⚠️ {member.mention} warned: **{reason}** (warning {count})"
        )

    @app_commands.command(name="warnings", description="List a member's warnings")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        rows = await (
            await self.bot.db.execute(
                """SELECT reason, moderator_id, created_at FROM warnings
                   WHERE guild_id = ? AND user_id = ? ORDER BY created_at DESC LIMIT 15""",
                (interaction.guild_id, member.id),
            )
        ).fetchall()
        if not rows:
            return await interaction.response.send_message(
                f"{member.display_name} has a clean record.", ephemeral=True
            )

        lines = [
            f"• **{row['reason']}** — <@{row['moderator_id']}>, <t:{int(row['created_at'])}:R>"
            for row in rows
        ]
        embed = discord.Embed(
            title=f"Warnings — {member.display_name}",
            description="\n".join(lines),
            color=0xFFB02E,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="clear", description="Bulk delete messages")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(amount="How many messages to delete (max 100)")
    async def clear(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"Deleted {len(deleted)} messages.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
