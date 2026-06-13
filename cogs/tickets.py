import asyncio
import time

import discord
from discord import app_commands
from discord.ext import commands


class TicketPanel(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Open a ticket", emoji="🎫", style=discord.ButtonStyle.primary,
        custom_id="ember:ticket:open",
    )
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.create_ticket(interaction)


class TicketControls(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Close", emoji="🔒", style=discord.ButtonStyle.danger,
        custom_id="ember:ticket:close",
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.close_ticket(interaction)


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.add_view(TicketPanel(self))
        bot.add_view(TicketControls(self))

    async def create_ticket(self, interaction: discord.Interaction):
        db = self.bot.db
        existing = await (
            await db.execute(
                "SELECT channel_id FROM tickets WHERE guild_id = ? AND owner_id = ?",
                (interaction.guild_id, interaction.user.id),
            )
        ).fetchone()
        if existing:
            channel = interaction.guild.get_channel(existing["channel_id"])
            if channel:
                return await interaction.response.send_message(
                    f"You already have a ticket open: {channel.mention}", ephemeral=True
                )
            await db.execute("DELETE FROM tickets WHERE channel_id = ?", (existing["channel_id"],))
            await db.commit()

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, attach_files=True
            ),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        channel = await interaction.guild.create_text_channel(
            name=f"ticket-{interaction.user.name}"[:32],
            overwrites=overwrites,
            reason=f"Ticket for {interaction.user}",
        )

        await db.execute(
            "INSERT INTO tickets (channel_id, guild_id, owner_id, opened_at) VALUES (?, ?, ?, ?)",
            (channel.id, interaction.guild_id, interaction.user.id, time.time()),
        )
        await db.commit()

        embed = discord.Embed(
            title="Ticket opened",
            description=(
                f"{interaction.user.mention}, describe your issue and someone "
                "from the team will be with you shortly."
            ),
            color=0xFF6B35,
        )
        await channel.send(embed=embed, view=TicketControls(self))
        await interaction.response.send_message(
            f"Your ticket is ready: {channel.mention}", ephemeral=True
        )

    async def close_ticket(self, interaction: discord.Interaction):
        db = self.bot.db
        row = await (
            await db.execute(
                "SELECT owner_id FROM tickets WHERE channel_id = ?", (interaction.channel_id,)
            )
        ).fetchone()
        if not row:
            return await interaction.response.send_message(
                "This channel isn't a tracked ticket.", ephemeral=True
            )

        is_staff = interaction.user.guild_permissions.manage_channels
        if interaction.user.id != row["owner_id"] and not is_staff:
            return await interaction.response.send_message(
                "Only the ticket owner or staff can close this.", ephemeral=True
            )

        await db.execute("DELETE FROM tickets WHERE channel_id = ?", (interaction.channel_id,))
        await db.commit()
        await interaction.response.send_message("Closing in 5 seconds…")
        await asyncio.sleep(5)
        await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")

    @app_commands.command(name="ticketpanel", description="Post the ticket panel in this channel")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ticketpanel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Need help?",
            description="Hit the button below and a private channel opens just for you.",
            color=0xFF6B35,
        )
        await interaction.channel.send(embed=embed, view=TicketPanel(self))
        await interaction.response.send_message("Panel posted.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Tickets(bot))
