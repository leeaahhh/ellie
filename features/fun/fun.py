from asyncio import sleep
from random import choice, randint
from typing import Literal
import aiohttp
import config
import io
import discord
from discord import File
from PIL import Image, ImageDraw, ImageFont
import os

from discord import (Embed, Member, Color, )
from discord.ext.commands import (BucketType, command, cooldown, group,
                                  max_concurrency, is_owner)

from tools import services
from tools.managers.cog import Cog
from tools.managers.context import Context
from tools.utilities.text import Plural
from discord import app_commands
from discord.ext.commands import hybrid_command

class Fun(Cog):
    """Cog for Fun commands."""

    @hybrid_command(
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
        await sleep(shakes * 0.5)

        await getattr(ctx, ("approve" if response is True else "error"))(
            f"The **magic 8ball** says: `{response}` after {Plural(shakes):shake} ({question})"
        )

    @hybrid_command(name="roll", usage="(sides)", example="6", aliases=["dice"])
    async def roll(self: "Fun", ctx: Context, sides: int = 6):
        """Roll a dice"""
        await ctx.load(f"Rolling a **{sides}** sided dice..")

        await ctx.approve(f"You rolled a **{randint(1, sides)}**")

    @hybrid_command(
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

    @hybrid_command(name="tictactoe", usage="(member)", example="igna", aliases=["ttt"])
    @max_concurrency(1, BucketType.member)
    async def tictactoe(self: "Fun", ctx: Context, member: Member):
        """Play TicTacToe with another member"""
        if member == ctx.author:
            return await ctx.error("You can't play against **yourself**")
        if member.bot:
            return await ctx.error("You can't play against **bots**")

        await services.TicTacToe(ctx, member).start()


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

    @hybrid_command(
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

    @hybrid_command(
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
    @group(
        name="lovense",
        usage="<subcommand>",
        example="power 75",
        aliases=["dildo", "vibrator"],
        invoke_without_command=True
    )
    async def lovense(self: "Fun", ctx: Context):
        """Control a virtual device"""
        await ctx.send_help(ctx.command)

    @lovense.command(
        name="power",
        usage="<level>",
        example="75"
    )
    @max_concurrency(1, BucketType.member)
    async def lovense_power(self: "Fun", ctx: Context, power: int):
        """Control the power level of the virtual device"""
        if not hasattr(self, "device_status"):
            self.device_status = False

        if not self.device_status:
            return await ctx.error("Device is currently powered off! Owner must turn it on first.")

        if not 0 <= power <= 100:
            return await ctx.error("Power must be between 0 and 100!")

        await ctx.load(f"Setting power to **{power}%**...")

        if power == 0:
            message = "Device powered down"
            emoji = "💤"
        elif power < 25:
            message = "Low vibration mode"
            emoji = "📉" 
        elif power < 50:
            message = "Medium vibration mode"
            emoji = "📊"
        elif power < 75:
            message = "High vibration mode" 
            emoji = "📈"
        else:
            message = "MAXIMUM POWER MODE"
            emoji = "⚡"

        filled = "▰" * (power // 10)
        empty = "▱" * ((100 - power) // 10)
        
        await ctx.approve(
            f"{emoji} **{message}**\n"
            f"> Power: [{filled}{empty}] {power}%"
        )

    @lovense.command(name="on")
    @is_owner()
    async def lovense_on(self: "Fun", ctx: Context):
        """Turn on the virtual device (Owner only)"""
        if hasattr(self, "device_status") and self.device_status:
            return await ctx.error("Device is already powered on!")
        
        self.device_status = True
        await ctx.approve("Device powered on and ready for use! 🟢")

    @lovense.command(name="off")
    @is_owner()
    async def lovense_off(self: "Fun", ctx: Context):
        """Turn off the virtual device (Owner only)"""
        if not hasattr(self, "device_status") or not self.device_status:
            return await ctx.error("Device is already powered off!")
        
        self.device_status = False
        await ctx.approve("Device powered off! 🔴")

    @hybrid_command(
        name="howbig",
        usage="<member>",
        example="@user",
        aliases=["size", "length"]
    )
    @cooldown(1, 10, BucketType.member)
    async def howbig(self: "Fun", ctx: Context, member: Member = None):
        """Check how big someone is"""
        member = member or ctx.author
        
        #consistent random size for each user
        if await self.bot.is_owner(member):
            size = 50
        else:
            seed = member.id % 35
            size = seed + 1  # 1-36 range
        
        shaft = "=" * size
        tip = "Đ"
        
        await ctx.neutral(
            f"**{member.name}**'s size:\n"
            f"# 8{shaft}{tip} ({size + 3}cm)"
        )

    @hybrid_command(
        name="howgay",
        usage="<member>",
        example="@user",
        aliases=["gay"]
    )
    @cooldown(1, 10, BucketType.member)
    async def howgay(self: "Fun", ctx: Context, member: Member = None):
        """Check how gay someone is"""
        member = member or ctx.author

        gay_levels = {
            947204756898713721: 101,  # userid: percentage,
            945104190617845790: 999,
        }
        
        # consistent percentage
        if member.id in gay_levels:
            percentage = gay_levels[member.id]
        else:
            seed = member.id % 101
            percentage = seed
        
        filled = "█" * (percentage // 10) 
        empty = "░" * ((100 - percentage) // 10)
        
        await ctx.neutral(
            f"**{member.name}** is **{percentage}%** gay\n"
            f"[{filled}{empty}]"
        )

    @hybrid_command(
        name="ship",
        usage="(member1) [member2]",
        example="igna mars",
        aliases=["love", "compatibility"]
    )
    async def ship(self: "Fun", ctx: Context, member1: Member, member2: Member = None):
        """Calculate love compatibility between two members"""
        if member2 is None:
            member2 = ctx.author
        
        if member1 == member2:
            return await ctx.error("You can't ship someone with themselves!")

        # Generate a consistent compatibility percentage based on member IDs
        compatibility = ((member1.id + member2.id) % 100) + 1
        
        # Create embed
        embed = Embed(
            title="💕 Love Calculator 💕",
            description=f"**{member1.name}** x **{member2.name}**\n**{compatibility}%**",
            color=Color.pink()
        )

        # Download avatars
        async with aiohttp.ClientSession() as session:
            async with session.get(str(member1.display_avatar.url)) as resp:
                avatar1_data = await resp.read()
            async with session.get(str(member2.display_avatar.url)) as resp:
                avatar2_data = await resp.read()

        def create_circular_mask(size):
            mask = Image.new('L', size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0) + size, fill=255)
            return mask

        # Create the ship image
        with Image.open(io.BytesIO(avatar1_data)) as avatar1_img, \
             Image.open(io.BytesIO(avatar2_data)) as avatar2_img, \
             Image.open("assets/heart.png") as heart_img:
            
            # Resize avatars to 128x128
            size = (128, 128)
            avatar1_img = avatar1_img.convert('RGBA').resize(size)
            avatar2_img = avatar2_img.convert('RGBA').resize(size)
            
            # Create circular mask and apply to avatars
            mask = create_circular_mask(size)
            avatar1_circle = Image.new('RGBA', size, (0, 0, 0, 0))
            avatar2_circle = Image.new('RGBA', size, (0, 0, 0, 0))
            avatar1_circle.paste(avatar1_img, (0, 0), mask)
            avatar2_circle.paste(avatar2_img, (0, 0), mask)
            
            # Create base image (adjusted width)
            base = Image.new('RGBA', (350, 170), (0, 0, 0, 0))
            
            # Calculate positions for closer avatars
            avatar1_pos = (30, 0)
            avatar2_pos = (192, 0)
            
            # Create progress bar (thinner and lower)
            bar_width = 200
            bar_height = 16
            bar_pos = (75, 140)  # Positioned under avatars
            
            # Draw background bar
            draw = ImageDraw.Draw(base)
            draw.rectangle(
                (bar_pos[0], bar_pos[1], bar_pos[0] + bar_width, bar_pos[1] + bar_height),
                fill=(100, 100, 100, 255),
                outline=(255, 255, 255, 255),
                width=1
            )
            
            # Draw filled portion based on compatibility
            filled_width = int(bar_width * (compatibility / 100))
            draw.rectangle(
                (bar_pos[0], bar_pos[1], bar_pos[0] + filled_width, bar_pos[1] + bar_height),
                fill=(255, 192, 203, 255)  # Pink fill
            )
            
            # Add percentage text on slider
            try:
                font = ImageFont.truetype("assets/font.ttf", 20)  # You'll need to add a font file
            except:
                font = ImageFont.load_default()
                
            text = f"{compatibility}%"
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_x = bar_pos[0] + (bar_width - text_width) // 2
            text_y = bar_pos[1] + (bar_height - text_bbox[3]) // 2
            draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 255))
            
            # Paste avatars
            base.paste(avatar1_circle, avatar1_pos)
            base.paste(avatar2_circle, avatar2_pos)
            
            # Resize heart and paste in middle of progress bar
            heart_size = (48, 48)
            heart_img = heart_img.resize(heart_size)
            heart_pos = (bar_pos[0] + (bar_width // 2) - (heart_size[0] // 2), 
                        bar_pos[1] - (heart_size[1] // 2))
            base.paste(heart_img, heart_pos, heart_img)
            
            # Save to buffer
            buffer = io.BytesIO()
            base.save(buffer, 'PNG')
            buffer.seek(0)
            
            # Send embed with image
            file = File(buffer, 'ship.png')
            embed.set_image(url="attachment://ship.png")
            await ctx.send(embed=embed, file=file)

# TODO : webhook logging


