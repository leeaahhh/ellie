from asyncio import sleep
from random import choice, randint
from typing import Literal

from discord import Member
from discord.ext.commands import BucketType, command, cooldown, group, max_concurrency

from tools import services
from tools.managers.cog import Cog
from tools.managers.context import Context
from tools.utilities.text import Plural


class Fun(Cog):
    """Cog for Fun"""

    @command(
        name="8ball",
        usage="(question)",
        example="am I pretty?",
        aliases=["8b"],
    )
    async def eightball(self, ctx: Context, *, question: str):
        """Ask the magic 8ball a question"""
        await ctx.load("Shaking the **magic 8ball**..")

        shakes = randint(1, 5)
        response = choice(list(self.bot.eightball_responses.keys()))
        await sleep(shakes)

        await getattr(ctx, ("approve" if response is True else "error"))(
            f"The **magic 8ball** says: `{response}` after {Plural(shakes):shake} ({question})"
        )

    @command(name="roll", usage="(sides)", example="6", aliases=["dice"])
    async def roll(self: "Fun", ctx: Context, sides: int = 6):
        """Roll a dice"""
        await ctx.load(f"Rolling a **{sides}** sided dice..")

        await ctx.approve(f"You rolled a **{randint(1, sides)}**")

    @command(
        name="coinflip",
        usage="<heads/tails>",
        example="heads",
        aliases=["flipcoin", "cf", "fc"],
    )
    async def coinflip(
        self: "Fun", ctx: Context, *, side: Literal["heads", "tails"] = None
    ):
        """Flip a coin"""
        await ctx.load(
            f"Flipping a coin{f' and guessing **:coin: {side}**' if side else ''}.."
        )

        coin = choice(["heads", "tails"])
        await getattr(ctx, ("approve" if (not side or side == coin) else "error"))(
            f"The coin landed on **:coin: {coin}**"
            + (f", you **{'won' if side == coin else 'lost'}**!" if side else "!")
        )

    @command(name="tictactoe", usage="(member)", example="igna", aliases=["ttt"])
    @max_concurrency(1, BucketType.member)
    async def tictactoe(self: "Fun", ctx: Context, member: Member):
        """Play TicTacToe with another member"""
        if member == ctx.author:
            return await ctx.error("You can't play against **yourself**")
        if member.bot:
            return await ctx.error("You can't play against **bots**")

        await services.TicTacToe(ctx, member).start()

    @command(
        name="marry",
        usage="(member)",
        example="igna",
        aliases=["propose", "proposal"],
    )
    @max_concurrency(1, BucketType.member)
    @cooldown(1, 60, BucketType.member)
    async def marry(self: "Fun", ctx: Context, member: Member):
        """Propose to another member"""
        marriage = await self.bot.db.fetchrow(
            "SELECT * FROM marriages WHERE user_id = $1 OR partner_id = $1",
            member.id,
        )
        if marriage:
            return await ctx.error(
                f"**{member.name}** is already married to **{self.bot.get_user(marriage.get('user_id')).name}**"
            )

        marriage = await self.bot.db.fetchrow(
            "SELECT * FROM marriages WHERE user_id = $1 OR partner_id = $1",
            ctx.author.id,
        )
        if marriage:
            return await ctx.error(
                f"You're already married to **{self.bot.get_user(marriage.get('user_id')).name}**"
            )

        if member == ctx.author:
            return await ctx.error("You can't marry **yourself**")

        if member.bot:
            return await ctx.error("You can't marry **bots**")

        if not await ctx.prompt(
            f"**{member.name}**, do you accept **{ctx.author.name}**'s proposal?",
            member=member,
        ):
            return await ctx.error(f"**{member.name}** denied your proposal")

        await self.bot.db.execute(
            "INSERT INTO marriages (user_id, partner_id) VALUES ($1, $2)",
            ctx.author.id,
            member.id,
        )

        return await ctx.neutral(
            f"**{ctx.author.name}** and **{member.name}** are now married!"
        )

    @command(
        name="divorce",
        aliases=["breakup"],
    )
    @max_concurrency(1, BucketType.member)
    @cooldown(1, 60, BucketType.member)
    async def divorce(self: "Fun", ctx: Context):
        """Divorce your partner"""
        marriage = await self.bot.db.fetchrow(
            "SELECT * FROM marriages WHERE user_id = $1 OR partner_id = $1",
            ctx.author.id,
        )
        if not marriage:
            return await ctx.error("You're not **married** to anyone")

        await ctx.prompt(
            f"Are you sure you want to divorce **{self.bot.get_user(marriage.get('partner_id')).name}**?",
        )

        await self.bot.db.execute(
            "DELETE FROM marriages WHERE user_id = $1 OR partner_id = $1",
            ctx.author.id,
        )
        return await ctx.neutral("You are now **divorced**")

    @command(
        name="partner",
        aliases=["spouse"],
    )
    @max_concurrency(1, BucketType.member)
    async def partner(self: "Fun", ctx: Context):
        """Check who you're married to"""
        marriage = await self.bot.db.fetchrow(
            "SELECT * FROM marriages WHERE user_id = $1 OR partner_id = $1",
            ctx.author.id,
        )
        if not marriage:
            return await ctx.error("You're not **married** to anyone")

        partner = self.bot.get_user(marriage.get("partner_id"))
        return await ctx.neutral(f"You're married to **{partner}**")

    @group(
        name="blunt",
        usage="(subcommand) <args>",
        example="pass igna",
        aliases=["joint"],
        invoke_without_command=True,
        hidden=False,
    )
    async def blunt(self: "Fun", ctx: Context):
        """Smoke a blunt"""
        await ctx.send_help()

    @blunt.command(
        name="light",
        aliases=["roll"],
        hidden=False,
    )
    async def blunt_light(self: "Fun", ctx: Context):
        """Light up a blunt"""
        blunt = await self.bot.db.fetchrow(
            "SELECT * FROM blunt WHERE guild_id = $1",
            ctx.guild.id,
        )
        if blunt:
            user = ctx.guild.get_member(blunt.get("user_id"))
            return await ctx.error(
                f"A **blunt** is already held by **{user or blunt.get('user_id')}**\n> It has been hit"
                f" {Plural(blunt.get('hits')):time} by {Plural(blunt.get('members')):member}",
            )

        await self.bot.db.execute(
            "INSERT INTO blunt (guild_id, user_id) VALUES($1, $2)",
            ctx.guild.id,
            ctx.author.id,
        )

        await ctx.load(
            "Rolling the **blunt**..", emoji="<:lighter:1180106328165863495>"
        )
        await sleep(2)
        await ctx.approve(
            f"Lit up a **blunt**\n> Use `{ctx.prefix}blunt hit` to smoke it",
            emoji="🚬",
        )

    @blunt.command(
        name="pass",
        usage="(member)",
        example="igna",
        aliases=["give"],
        hidden=False,
    )
    async def blunt_pass(self: "Fun", ctx: Context, *, member: Member):
        """Pass the blunt to another member"""
        blunt = await self.bot.db.fetchrow(
            "SELECT * FROM blunt WHERE guild_id = $1",
            ctx.guild.id,
        )
        if not blunt:
            return await ctx.error(
                f"There is no **blunt** to pass\n> Use `{ctx.prefix}blunt light` to roll one up"
            )
        if blunt.get("user_id") != ctx.author.id:
            member = ctx.guild.get_member(blunt.get("user_id"))
            return await ctx.error(
                f"You don't have the **blunt**!\n> Steal it from **{member or blunt.get('user_id')}** first"
            )
        if member == ctx.author:
            return await ctx.error("You can't pass the **blunt** to **yourself**")

        await self.bot.db.execute(
            "UPDATE blunt SET user_id = $2, passes = passes + 1 WHERE guild_id = $1",
            ctx.guild.id,
            member.id,
        )

        await ctx.approve(
            f"The **blunt** has been passed to **{member}**!\n> It has been passed around"
            f" **{Plural(blunt.get('passes') + 1):time}**",
            emoji="🚬",
        )

    @blunt.command(
        name="steal",
        aliases=["take"],
        hidden=False,
    )
    @cooldown(1, 5, BucketType.member)
    async def blunt_steal(self: "Fun", ctx: Context):
        """Steal the blunt from another member"""
        blunt = await self.bot.db.fetchrow(
            "SELECT * FROM blunt WHERE guild_id = $1",
            ctx.guild.id,
        )
        if not blunt:
            return await ctx.error(
                f"There is no **blunt** to steal\n> Use `{ctx.prefix}blunt light` to roll one up"
            )
        if blunt.get("user_id") == ctx.author.id:
            return await ctx.error(
                f"You already have the **blunt**!\n> Use `{ctx.prefix}blunt pass` to pass it to someone else"
            )

        member = ctx.guild.get_member(blunt.get("user_id"))

        if randint(1, 100) <= 50:
            return await ctx.error(
                f"**{member or blunt.get('user_id')}** is hogging the **blunt**!"
            )

        await self.bot.db.execute(
            "UPDATE blunt SET user_id = $2 WHERE guild_id = $1",
            ctx.guild.id,
            ctx.author.id,
        )

        await ctx.approve(
            f"You just stole the **blunt** from **{member or blunt.get('user_id')}**!",
            emoji="🚬",
        )

    @blunt.command(
        name="hit",
        aliases=["smoke", "chief"],
        hidden=False,
    )
    @max_concurrency(1, BucketType.guild)
    async def blunt_hit(self: "Fun", ctx: Context):
        """Hit the blunt"""
        blunt = await self.bot.db.fetchrow(
            "SELECT * FROM blunt WHERE guild_id = $1",
            ctx.guild.id,
        )
        if not blunt:
            return await ctx.error(
                f"There is no **blunt** to hit\n> Use `{ctx.prefix}blunt light` to roll one up"
            )
        if blunt.get("user_id") != ctx.author.id:
            member = ctx.guild.get_member(blunt.get("user_id"))
            return await ctx.error(
                f"You don't have the **blunt**!\n> Steal it from **{member or blunt.get('user_id')}** first"
            )

        if ctx.author.id not in blunt.get("members"):
            blunt["members"].append(ctx.author.id)

        await ctx.load(
            "Hitting the **blunt**..",
            emoji="🚬",
        )
        await sleep(randint(1, 2))

        if blunt["hits"] + 1 >= 10 and randint(1, 100) <= 25:
            await self.bot.db.execute(
                "DELETE FROM blunt WHERE guild_id = $1",
                ctx.guild.id,
            )
            return await ctx.error(
                f"The **blunt** burned out after {Plural(blunt.get('hits') + 1):hit} by"
                f" **{Plural(blunt.get('members')):member}**"
            )

        await self.bot.db.execute(
            "UPDATE blunt SET hits = hits + 1, members = $2 WHERE guild_id = $1",
            ctx.guild.id,
            blunt["members"],
        )

        await ctx.approve(
            f"You just hit the **blunt**!\n> It has been hit **{Plural(blunt.get('hits') + 1):time}** by"
            f" **{Plural(blunt.get('members')):member}**",
            emoji="🌬",
        )

    @command(
        name="slots",
        aliases=["slot", "spin"],
    )
    @max_concurrency(1, BucketType.member)
    async def slots(self: "Fun", ctx: Context):
        """Play the slot machine"""
        await ctx.load("Spinning the **slot machine**..")

        slots = [choice(["🍒", "🍊", "🍋", "🍉", "🍇"]) for _ in range(3)]
        if len(set(slots)) == 1:
            await ctx.approve(
                f"You won the **slot machine**!\n\n `{slots[0]}` `{slots[1]}` `{slots[2]}`"
            )
        else:
            await ctx.error(
                f"You lost the **slot machine**\n\n `{slots[0]}` `{slots[1]}` `{slots[2]}`"
            )

    @command(
        name="poker",
        usage="(red/black)",
        example="red",
        aliases=["cards"],
    )
    @max_concurrency(1, BucketType.member)
    async def poker(self: "Fun", ctx: Context, *, color: Literal["red", "black"]):
        """Play a game of poker"""
        await ctx.load("Shuffling the **deck**..")

        cards = [
            choice(
                [
                    "🂡",
                    "🂢",
                    "🂣",
                    "🂤",
                    "🂥",
                    "🂦",
                    "🂧",
                    "🂨",
                    "🂩",
                    "🂪",
                    "🂫",
                    "🂭",
                    "🂮",
                ]
            )
            for _ in range(2)
        ]
        if color == "red":
            if cards[0] in ["🂡", "🂣", "🂥", "🂨", "🂩", "🂫", "🂮"]:
                await ctx.approve(
                    f"You won the **poker**!\n\n > `{cards[0]}` `{cards[1]}`"
                )
            else:
                await ctx.error(
                    f"You lost the **poker**\n\n > `{cards[0]}` `{cards[1]}`"
                )
        else:
            if cards[0] in ["🂢", "🂤", "🂦", "🂪", "🂬", "🂰"]:
                await ctx.approve(
                    f"You won the **poker**!\n\n > `{cards[0]}` `{cards[1]}`"
                )
            else:
                await ctx.error(
                    f"You lost the **poker**\n\n > `{cards[0]}` `{cards[1]}`"
                )
