import discord
from discord.ext import commands
import aiohttp
from typing import Optional
import config


class Roleplay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.base_url = "https://purrbot.site/api/img"

    async def _get_roleplay_image(self, endpoint: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/{endpoint}/gif") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["link"]
                return None

    @commands.command()
    async def hug(self, ctx, member: Optional[discord.Member]):
        """Hug someone!"""
        if not member:
            return await ctx.send(f"{ctx.author.mention} hugs themselves...")
            
        image = await self._get_roleplay_image("sfw/hug")
        embed = discord.Embed(
            description=f"{ctx.author.mention} hugs {member.mention}",
            color=config.Color.neutral
        )
        embed.set_image(url=image)
        await ctx.send(embed=embed)

    @commands.command() 
    async def kiss(self, ctx, member: Optional[discord.Member]):
        """Kiss someone!"""
        if not member:
            return await ctx.send(f"{ctx.author.mention} tries to kiss the air...")
            
        image = await self._get_roleplay_image("sfw/kiss")
        embed = discord.Embed(
            description=f"{ctx.author.mention} kisses {member.mention}",
            color=config.Color.neutral
        )
        embed.set_image(url=image)
        await ctx.send(embed=embed)

    @commands.command()
    async def pat(self, ctx, member: Optional[discord.Member]):
        """Pat someone!"""
        if not member:
            return await ctx.send(f"{ctx.author.mention} pats themselves...")
            
        image = await self._get_roleplay_image("sfw/pat")
        embed = discord.Embed(
            description=f"{ctx.author.mention} pats {member.mention}",
            color=config.Color.neutral
        )
        embed.set_image(url=image)
        await ctx.send(embed=embed)

    @commands.command()
    async def slap(self, ctx, member: Optional[discord.Member]):
        """Slap someone!"""
        if not member:
            return await ctx.send(f"{ctx.author.mention} slaps themselves... ouch!")
            
        image = await self._get_roleplay_image("sfw/slap")
        embed = discord.Embed(
            description=f"{ctx.author.mention} slaps {member.mention}",
            color=config.Color.neutral
        )
        embed.set_image(url=image)
        await ctx.send(embed=embed)

    @commands.command()
    async def cuddle(self, ctx, member: Optional[discord.Member]):
        """Cuddle with someone!"""
        if not member:
            return await ctx.send(f"{ctx.author.mention} cuddles with a pillow...")
            
        image = await self._get_roleplay_image("sfw/cuddle")
        embed = discord.Embed(
            description=f"{ctx.author.mention} cuddles with {member.mention}",
            color=config.Color.neutral
        )
        embed.set_image(url=image)
        await ctx.send(embed=embed)

    @commands.command()
    async def lick(self, ctx, member: Optional[discord.Member]):
        """Lick someone!"""
        if not member:
            return await ctx.send(f"{ctx.author.mention} licks... themselves?")
            
        image = await self._get_roleplay_image("sfw/lick")
        embed = discord.Embed(
            description=f"{ctx.author.mention} licks {member.mention}",
            color=config.Color.neutral
        )
        embed.set_image(url=image)
        await ctx.send(embed=embed)

    @commands.command()
    async def bite(self, ctx, member: Optional[discord.Member]):
        """Bite someone!"""
        if not member:
            return await ctx.send(f"{ctx.author.mention} bites themselves... why?")
            
        image = await self._get_roleplay_image("sfw/bite")
        embed = discord.Embed(
            description=f"{ctx.author.mention} bites {member.mention}",
            color=config.Color.neutral
        )
        embed.set_image(url=image)
        await ctx.send(embed=embed)

    @commands.command()
    async def poke(self, ctx, member: Optional[discord.Member]):
        """Poke someone!"""
        if not member:
            return await ctx.send(f"{ctx.author.mention} pokes the air...")
            
        image = await self._get_roleplay_image("sfw/poke")
        embed = discord.Embed(
            description=f"{ctx.author.mention} pokes {member.mention}",
            color=config.Color.neutral
        )
        embed.set_image(url=image)
        await ctx.send(embed=embed)

    @commands.command()
    async def tickle(self, ctx, member: Optional[discord.Member]):
        """Tickle someone!"""
        if not member:
            return await ctx.send(f"{ctx.author.mention} tickles themselves...")
            
        image = await self._get_roleplay_image("sfw/tickle")
        embed = discord.Embed(
            description=f"{ctx.author.mention} tickles {member.mention}",
            color=config.Color.neutral
        )
        embed.set_image(url=image)
        await ctx.send(embed=embed)

    @commands.command()
    async def pout(self, ctx):
        """Show that you're pouting!"""
        image = await self._get_roleplay_image("sfw/pout")
        embed = discord.Embed(
            description=f"{ctx.author.mention} pouts!",
            color=config.Color.neutral
        )
        embed.set_image(url=image)
        await ctx.send(embed=embed)

    @commands.command()
    async def cry(self, ctx):
        """Show that you're crying!"""
        image = await self._get_roleplay_image("sfw/cry")
        embed = discord.Embed(
            description=f"{ctx.author.mention} is crying...",
            color=config.Color.neutral
        )
        embed.set_image(url=image)
        await ctx.send(embed=embed)

    @commands.command()
    async def angry(self, ctx):
        """Show that you're angry!"""
        image = await self._get_roleplay_image("sfw/angry")
        embed = discord.Embed(
            description=f"{ctx.author.mention} is angry!",
            color=config.Color.neutral
        )
        embed.set_image(url=image)
        await ctx.send(embed=embed)

    @commands.command()
    async def blush(self, ctx):
        """Show that you're blushing!"""
        image = await self._get_roleplay_image("sfw/blush")
        embed = discord.Embed(
            description=f"{ctx.author.mention} is blushing!",
            color=config.Color.neutral
        )
        embed.set_image(url=image)
        await ctx.send(embed=embed)

