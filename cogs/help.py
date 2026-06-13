import discord
from discord import app_commands
from discord.ext import commands


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="Show all available commands")
    async def help_cmd(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="📖 Ember Bot — Commands",
            description="Here's everything you can do:",
            colour=0x5865F2,
        )

        embed.add_field(
            name="📊 Levels",
            value=(
                "`/rank [member]` — See your or someone's rank card\n"
                "`/leaderboard` — Top 10 most active members"
            ),
            inline=False,
        )

        embed.add_field(
            name="🛡️ Moderation",
            value=(
                "`/warn <member> <reason>` — Warn a member\n"
                "`/warnings <member>` — List a member's warnings\n"
                "`/clear <amount>` — Bulk delete messages (max 100)"
            ),
            inline=False,
        )

        embed.add_field(
            name="🎫 Tickets",
            value="`/ticketpanel` — Post the ticket panel in this channel",
            inline=False,
        )

        embed.add_field(
            name="🎉 Giveaways",
            value=(
                "`/giveaway <duration> <prize>` — Start a giveaway (e.g. `1h`, `30m`, `2d`)\n"
                "`/reroll <message_id>` — Reroll the winner of an ended giveaway"
            ),
            inline=False,
        )

        embed.set_footer(text="Tip: You earn XP by chatting — keep talking to level up!")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Help(bot))
