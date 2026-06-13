import random
import re
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

DURATION_RE = re.compile(r"(\d+)\s*([smhd])", re.I)
UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_duration(text):
    total = 0
    for amount, unit in DURATION_RE.findall(text):
        total += int(amount) * UNIT_SECONDS[unit.lower()]
    return total


class EnterButton(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Enter", emoji="🎉", style=discord.ButtonStyle.success,
        custom_id="ember:giveaway:enter",
    )
    async def enter(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.enter_giveaway(interaction)


class Giveaways(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.add_view(EnterButton(self))
        self.sweep.start()

    def cog_unload(self):
        self.sweep.cancel()

    async def enter_giveaway(self, interaction: discord.Interaction):
        db = self.bot.db
        row = await (
            await db.execute(
                "SELECT ended FROM giveaways WHERE message_id = ?", (interaction.message.id,)
            )
        ).fetchone()
        if not row or row["ended"]:
            return await interaction.response.send_message("This giveaway is over.", ephemeral=True)

        already = await (
            await db.execute(
                "SELECT 1 FROM giveaway_entries WHERE message_id = ? AND user_id = ?",
                (interaction.message.id, interaction.user.id),
            )
        ).fetchone()
        if already:
            await db.execute(
                "DELETE FROM giveaway_entries WHERE message_id = ? AND user_id = ?",
                (interaction.message.id, interaction.user.id),
            )
            await db.commit()
            return await interaction.response.send_message("Entry withdrawn.", ephemeral=True)

        await db.execute(
            "INSERT INTO giveaway_entries (message_id, user_id) VALUES (?, ?)",
            (interaction.message.id, interaction.user.id),
        )
        await db.commit()
        await interaction.response.send_message("You're in. Good luck! 🎉", ephemeral=True)

    @app_commands.command(name="giveaway", description="Start a giveaway")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(duration="e.g. 1h, 30m, 2d", prize="What's being given away")
    async def giveaway(self, interaction: discord.Interaction, duration: str, prize: str):
        seconds = parse_duration(duration)
        if seconds < 30 or seconds > 30 * 86400:
            return await interaction.response.send_message(
                "Duration must be between 30 seconds and 30 days (e.g. `45m`, `2h`, `1d`).",
                ephemeral=True,
            )

        ends_at = time.time() + seconds
        embed = discord.Embed(
            title=f"🎉 {prize}",
            description=f"Ends <t:{int(ends_at)}:R> · hosted by {interaction.user.mention}",
            color=0x5DD97C,
        )
        await interaction.response.send_message(embed=embed, view=EnterButton(self))
        message = await interaction.original_response()

        await self.bot.db.execute(
            """INSERT INTO giveaways (message_id, channel_id, guild_id, prize, ends_at, host_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (message.id, interaction.channel_id, interaction.guild_id, prize, ends_at, interaction.user.id),
        )
        await self.bot.db.commit()

    @app_commands.command(name="reroll", description="Reroll the winner of an ended giveaway")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def reroll(self, interaction: discord.Interaction, message_id: str):
        try:
            mid = int(message_id)
        except ValueError:
            return await interaction.response.send_message("That's not a message id.", ephemeral=True)
        winner = await self.pick_winner(mid)
        if winner is None:
            return await interaction.response.send_message("No entries for that giveaway.", ephemeral=True)
        await interaction.response.send_message(f"🎲 New winner: <@{winner}>")

    async def pick_winner(self, message_id):
        rows = await (
            await self.bot.db.execute(
                "SELECT user_id FROM giveaway_entries WHERE message_id = ?", (message_id,)
            )
        ).fetchall()
        if not rows:
            return None
        return random.choice(rows)["user_id"]

    @tasks.loop(seconds=20)
    async def sweep(self):
        db = self.bot.db
        due = await (
            await db.execute(
                "SELECT * FROM giveaways WHERE ended = 0 AND ends_at <= ?", (time.time(),)
            )
        ).fetchall()

        for g in due:
            await db.execute("UPDATE giveaways SET ended = 1 WHERE message_id = ?", (g["message_id"],))
            await db.commit()

            channel = self.bot.get_channel(g["channel_id"])
            if not channel:
                continue

            winner = await self.pick_winner(g["message_id"])
            if winner is None:
                await channel.send(f"Giveaway **{g['prize']}** ended with no entries.")
                continue

            await channel.send(f"🎉 **{g['prize']}** goes to <@{winner}>! Congrats!")

    @sweep.before_loop
    async def before_sweep(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Giveaways(bot))
