import contextlib

import discord
from discord.ext import commands
from discord.ui import Button, View  # type: ignore


class TicTacToeButton(Button):
    def __init__(
        self, label: str, style: discord.ButtonStyle, row: int, custom_id: str
    ):
        super().__init__(label=label, style=style, row=row, custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        await self.view.callback(interaction, self)


class TicTacToe(View):
    def __init__(self, ctx: commands.Context, member: discord.Member):
        super().__init__(timeout=60.0)
        self.ctx: commands.Context = ctx
        self.bot: commands.Bot = ctx.bot
        self.message: discord.Message = None
        self.member: discord.Member = member
        self.turn: discord.Member = ctx.author
        self.winner: discord.Member = None
        for i in range(9):
            self.add_item(
                TicTacToeButton(
                    label="\u200b",
                    style=discord.ButtonStyle.gray,
                    row=i // 3,
                    custom_id=f"board:{i}",
                )
            )

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.turn.id:
            return True
        await interaction.warn(f"It's {self.turn.mention}'s turn!")
        return False

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

        with contextlib.suppress(discord.HTTPException):
            await self.message.edit(
                content=f"**{self.ctx.author.name}** vs **{self.member.name}**\n\nThe game has ended due to inactivity",
                view=self,
            )

        self.stop()

    async def on_error(
        self, error: Exception, item: Button, interaction: discord.Interaction
    ):
        await self.ctx.error(f"An warn occurred while processing your action: {item}")
        self.stop()

    async def callback(self, interaction: discord.Interaction, button: TicTacToeButton):
        await interaction.response.defer()

        button.label = "X" if self.turn == self.ctx.author else "O"
        button.disabled = True
        button.style = (
            discord.ButtonStyle.red
            if self.turn == self.ctx.author
            else discord.ButtonStyle.green
        )
        if winner := await self.check_win(interaction):
            await interaction.message.edit(
                content=f"**{self.ctx.author.name}** vs **{self.member.name}**\n\n{winner}",
                view=self,
            )
            self.stop()
            return

        self.turn = self.member if self.turn == self.ctx.author else self.ctx.author
        await interaction.message.edit(
            content=(
                f"**{self.ctx.author.name}** vs **{self.member.name}**\n\n{'❌' if self.turn == self.ctx.author else '⭕'} It's {self.turn.mention}'s"
                " turn"
            ),
            view=self,
        )

    async def check_win(self, interaction: discord.Interaction):
        board = [button.label for button in self.children]
        if board[0] == board[1] == board[2] != "\u200b":
            self.winner = self.ctx.author if board[0] == "X" else self.member
        elif board[3] == board[4] == board[5] != "\u200b":
            self.winner = self.ctx.author if board[3] == "X" else self.member
        elif board[6] == board[7] == board[8] != "\u200b":
            self.winner = self.ctx.author if board[6] == "X" else self.member
        elif board[0] == board[3] == board[6] != "\u200b":
            self.winner = self.ctx.author if board[0] == "X" else self.member
        elif board[1] == board[4] == board[7] != "\u200b":
            self.winner = self.ctx.author if board[1] == "X" else self.member
        elif board[2] == board[5] == board[8] != "\u200b":
            self.winner = self.ctx.author if board[2] == "X" else self.member
        elif board[0] == board[4] == board[8] != "\u200b":
            self.winner = self.ctx.author if board[0] == "X" else self.member
        elif board[2] == board[4] == board[6] != "\u200b":
            self.winner = self.ctx.author if board[2] == "X" else self.member
        elif "\u200b" not in board:
            self.winner = "tie"

        if self.winner:
            for child in self.children:
                child.disabled = True
            return (
                f"🏆 {self.winner.mention} won!"
                if self.winner != "tie"
                else "It's a **tie**!"
            )
        return False

    async def start(self):
        """Start the TicTacToe game"""
        self.message = await self.ctx.channel.send(
            content=f"**{self.ctx.author.name}** vs **{self.member.name}**\n\n❌ It's {self.turn.mention}'s turn",
            view=self,
        )
