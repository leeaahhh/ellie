import discord
from discord.ext import commands
from discord.ui import View  # type: ignore


class ConfirmViewForUser(View):
    # Like ConfirmView, but it's for a specific member, not the author of the command
    def __init__(self, ctx: commands.Context, member: discord.Member):
        super().__init__()
        self.value = False
        self.ctx: commands.Context = ctx
        self.bot: commands.Bot = ctx.bot
        self.member = member

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, _: discord.Button):
        """Approve the action"""
        self.value = True
        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, _: discord.Button):
        """Decline the action"""
        self.value = False
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.member.id:
            return True
        await interaction.warn(
            "You aren't the **author** of this embed",
        )
        return False


class ConfirmView(View):
    def __init__(self, ctx: commands.Context):
        super().__init__()
        self.value = False
        self.ctx: commands.Context = ctx
        self.bot: commands.Bot = ctx.bot

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, _: discord.Button):
        """Approve the action"""
        self.value = True
        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, _: discord.Button):
        """Decline the action"""
        self.value = False
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.ctx.author.id:
            return True
        await interaction.warn(
            "You aren't the **author** of this embed",
        )
        return False
