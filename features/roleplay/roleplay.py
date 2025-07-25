import discord
from discord.ext import commands
import aiohttp
from typing import Optional
import config
from discord.ext.commands import hybrid_command

# nekos.best endpoints as of 7/25/2025
NEKOS_BEST_IMAGE_CATEGORIES = [
    "husbando", "kitsune", "neko", "waifu"
]
NEKOS_BEST_GIF_CATEGORIES = [
    "angry", "baka", "bite", "blush", "bored", "cry", "cuddle", "dance", "facepalm", "feed", "handhold", "handshake", "happy", "highfive", "hug", "kick", "kiss", "laugh", "lurk", "nod", "nom", "nope", "pat", "peck", "poke", "pout", "punch", "run", "shoot", "shrug", "slap", "sleep", "smile", "smug", "stare", "think", "thumbsup", "tickle", "wave", "wink", "yawn", "yeet"
]
NEKOS_BEST_ALL_CATEGORIES = NEKOS_BEST_IMAGE_CATEGORIES + NEKOS_BEST_GIF_CATEGORIES

# owo pretty self-explanatory
SOLO_ACTIONS = [
    "smile", "wave", "wink", "blush", "bored", "cry", "dance", "facepalm", "happy", "laugh", "nod", "pout", "shrug", "sleep", "stare", "think", "thumbsup", "smug", "lurk", "nope", "run", "shoot", "yawn"
]

class Roleplay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.base_url = "https://nekos.best/api/v2"

    async def _get_neko_image(self, category: str) -> Optional[str]:
        url = f"{self.base_url}/{category}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["results"][0]["url"]
                return None

    def _get_action_description(self, action: str, author, member=None):
        # Custom descriptions for some actions
        if member:
            if action == "hug":
                return f"{author.mention} hugs {member.mention}"
            if action == "kiss":
                return f"{author.mention} kisses {member.mention}"
            if action == "pat":
                return f"{author.mention} pats {member.mention}"
            if action == "slap":
                return f"{author.mention} slaps {member.mention}"
            if action == "cuddle":
                return f"{author.mention} cuddles with {member.mention}"
            if action == "poke":
                return f"{author.mention} pokes {member.mention}"
            if action == "tickle":
                return f"{author.mention} tickles {member.mention}"
            if action == "feed":
                return f"{author.mention} feeds {member.mention}"
            if action == "handhold":
                return f"{author.mention} holds hands with {member.mention}"
            if action == "highfive":
                return f"{author.mention} high-fives {member.mention}"
            if action == "nom":
                return f"{author.mention} noms {member.mention}"
            if action == "peck":
                return f"{author.mention} gives {member.mention} a peck"
            if action == "punch":
                return f"{author.mention} punches {member.mention}"
            if action == "kick":
                return f"{author.mention} kicks {member.mention}"
            if action == "bite":
                return f"{author.mention} bites {member.mention}"
            if action == "handshake":
                return f"{author.mention} shakes hands with {member.mention}"
            if action == "yeet":
                return f"{author.mention} yeets {member.mention}!"
            # incase I forgot something
            return f"{author.mention} {action}s {member.mention}"
        else:
            # Self actions or solo
            if action == "hug":
                return f"{author.mention} hugs themselves..."
            if action == "kiss":
                return f"{author.mention} tries to kiss the air..."
            if action == "pat":
                return f"{author.mention} pats themselves..."
            if action == "slap":
                return f"{author.mention} slaps themselves... ouch!"
            if action == "cuddle":
                return f"{author.mention} cuddles with a pillow..."
            if action == "poke":
                return f"{author.mention} pokes the air..."
            if action == "tickle":
                return f"{author.mention} tickles themselves..."
            if action == "feed":
                return f"{author.mention} feeds themselves..."
            if action == "handhold":
                return f"{author.mention} holds their own hand..."
            if action == "highfive":
                return f"{author.mention} high-fives themselves..."
            if action == "nom":
                return f"{author.mention} noms themselves..."
            if action == "peck":
                return f"{author.mention} pecks the air..."
            if action == "punch":
                return f"{author.mention} shadowboxes!"
            if action == "kick":
                return f"{author.mention} kicks the air!"
            if action == "bite":
                return f"{author.mention} bites the air!"
            if action == "handshake":
                return f"{author.mention} shakes their own hand..."
            if action == "yeet":
                return f"{author.mention} yeets themselves...?"
            # incase i forgot something
            return f"{author.mention} does {action}!"

    # auto create commands for everything
    @staticmethod
    def _make_member_action(action):
        @hybrid_command(name=action)
        async def _cmd(self, ctx, member: Optional[discord.Member] = None):
            desc = self._get_action_description(action, ctx.author, member) if member else self._get_action_description(action, ctx.author)
            image = await self._get_neko_image(action)
            embed = discord.Embed(description=desc, color=config.Color.neutral)
            if image:
                embed.set_image(url=image)
            await ctx.send(embed=embed)
        return _cmd

    @staticmethod
    def _make_solo_action(action):
        @hybrid_command(name=action)
        async def _cmd(self, ctx):
            desc = self._get_action_description(action, ctx.author)
            image = await self._get_neko_image(action)
            embed = discord.Embed(description=desc, color=config.Color.neutral)
            if image:
                embed.set_image(url=image)
            await ctx.send(embed=embed)
        return _cmd

    # For image-only categories
    @staticmethod
    def _make_image_action(category):
        @hybrid_command(name=category)
        async def _cmd(self, ctx):
            image = await self._get_neko_image(category)
            embed = discord.Embed(description=f"{ctx.author.mention} gets a random {category}!", color=config.Color.neutral)
            if image:
                embed.set_image(url=image)
            await ctx.send(embed=embed)
        return _cmd

for _action in NEKOS_BEST_GIF_CATEGORIES:
    if _action in SOLO_ACTIONS:
        setattr(Roleplay, _action, Roleplay._make_solo_action(_action))
    else:
        setattr(Roleplay, _action, Roleplay._make_member_action(_action))

for _imgcat in NEKOS_BEST_IMAGE_CATEGORIES:
    setattr(Roleplay, _imgcat, Roleplay._make_image_action(_imgcat))

