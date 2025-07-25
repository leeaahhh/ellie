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
    """Roleplay commands using nekos.best API."""

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

    # --- Command Definitions ---

    # --- GIF actions (with or without member) ---
    @hybrid_command(
        name="angry",
        usage="(member)",
        example="@user",
        description="Get angry at someone or yourself."
    )
    async def angry(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("angry", ctx.author, member)
        image = await self._get_neko_image("angry")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="baka",
        usage="(member)",
        example="@user",
        description="Call someone or yourself a baka."
    )
    async def baka(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("baka", ctx.author, member)
        image = await self._get_neko_image("baka")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="bite",
        usage="(member)",
        example="@user",
        description="Bite someone or yourself."
    )
    async def bite(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("bite", ctx.author, member)
        image = await self._get_neko_image("bite")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="blush",
        usage="(member)",
        example="@user",
        description="Blush at someone or yourself."
    )
    async def blush(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("blush", ctx.author, member)
        image = await self._get_neko_image("blush")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="bored",
        usage="(member)",
        example="@user",
        description="Be bored with someone or yourself."
    )
    async def bored(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("bored", ctx.author, member)
        image = await self._get_neko_image("bored")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="cry",
        usage="(member)",
        example="@user",
        description="Cry with someone or yourself."
    )
    async def cry(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("cry", ctx.author, member)
        image = await self._get_neko_image("cry")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="cuddle",
        usage="(member)",
        example="@user",
        description="Cuddle someone or yourself."
    )
    async def cuddle(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("cuddle", ctx.author, member)
        image = await self._get_neko_image("cuddle")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="dance",
        usage="(member)",
        example="@user",
        description="Dance with someone or yourself."
    )
    async def dance(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("dance", ctx.author, member)
        image = await self._get_neko_image("dance")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="facepalm",
        usage="(member)",
        example="@user",
        description="Facepalm at someone or yourself."
    )
    async def facepalm(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("facepalm", ctx.author, member)
        image = await self._get_neko_image("facepalm")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="feed",
        usage="(member)",
        example="@user",
        description="Feed someone or yourself."
    )
    async def feed(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("feed", ctx.author, member)
        image = await self._get_neko_image("feed")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="handhold",
        usage="(member)",
        example="@user",
        description="Hold hands with someone or yourself."
    )
    async def handhold(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("handhold", ctx.author, member)
        image = await self._get_neko_image("handhold")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="handshake",
        usage="(member)",
        example="@user",
        description="Handshake with someone or yourself."
    )
    async def handshake(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("handshake", ctx.author, member)
        image = await self._get_neko_image("handshake")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="happy",
        usage="(member)",
        example="@user",
        description="Be happy with someone or yourself."
    )
    async def happy(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("happy", ctx.author, member)
        image = await self._get_neko_image("happy")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="highfive",
        usage="(member)",
        example="@user",
        description="Highfive someone or yourself."
    )
    async def highfive(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("highfive", ctx.author, member)
        image = await self._get_neko_image("highfive")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="hug",
        usage="(member)",
        example="@user",
        description="Hug someone or yourself."
    )
    async def hug(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("hug", ctx.author, member)
        image = await self._get_neko_image("hug")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="kiss",
        usage="(member)",
        example="@user",
        description="Kiss someone or yourself."
    )
    async def kiss(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("kiss", ctx.author, member)
        image = await self._get_neko_image("kiss")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="laugh",
        usage="(member)",
        example="@user",
        description="Laugh with someone or yourself."
    )
    async def laugh(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("laugh", ctx.author, member)
        image = await self._get_neko_image("laugh")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="lurk",
        usage="(member)",
        example="@user",
        description="Lurk with someone or yourself."
    )
    async def lurk(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("lurk", ctx.author, member)
        image = await self._get_neko_image("lurk")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="nod",
        usage="(member)",
        example="@user",
        description="Nod at someone or yourself."
    )
    async def nod(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("nod", ctx.author, member)
        image = await self._get_neko_image("nod")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="nom",
        usage="(member)",
        example="@user",
        description="Nom someone or yourself."
    )
    async def nom(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("nom", ctx.author, member)
        image = await self._get_neko_image("nom")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="nope",
        usage="(member)",
        example="@user",
        description="Nope at someone or yourself."
    )
    async def nope(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("nope", ctx.author, member)
        image = await self._get_neko_image("nope")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="pat",
        usage="(member)",
        example="@user",
        description="Pat someone or yourself."
    )
    async def pat(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("pat", ctx.author, member)
        image = await self._get_neko_image("pat")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="peck",
        usage="(member)",
        example="@user",
        description="Peck someone or yourself."
    )
    async def peck(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("peck", ctx.author, member)
        image = await self._get_neko_image("peck")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="poke",
        usage="(member)",
        example="@user",
        description="Poke someone or yourself."
    )
    async def poke(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("poke", ctx.author, member)
        image = await self._get_neko_image("poke")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="pout",
        usage="(member)",
        example="@user",
        description="Pout at someone or yourself."
    )
    async def pout(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("pout", ctx.author, member)
        image = await self._get_neko_image("pout")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="punch",
        usage="(member)",
        example="@user",
        description="Punch someone or yourself."
    )
    async def punch(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("punch", ctx.author, member)
        image = await self._get_neko_image("punch")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="run",
        usage="(member)",
        example="@user",
        description="Run with someone or yourself."
    )
    async def run(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("run", ctx.author, member)
        image = await self._get_neko_image("run")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="shoot",
        usage="(member)",
        example="@user",
        description="Shoot at someone or yourself."
    )
    async def shoot(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("shoot", ctx.author, member)
        image = await self._get_neko_image("shoot")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="shrug",
        usage="(member)",
        example="@user",
        description="Shrug at someone or yourself."
    )
    async def shrug(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("shrug", ctx.author, member)
        image = await self._get_neko_image("shrug")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="slap",
        usage="(member)",
        example="@user",
        description="Slap someone or yourself."
    )
    async def slap(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("slap", ctx.author, member)
        image = await self._get_neko_image("slap")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="sleep",
        usage="(member)",
        example="@user",
        description="Sleep with someone or yourself."
    )
    async def sleep(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("sleep", ctx.author, member)
        image = await self._get_neko_image("sleep")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="smile",
        usage="(member)",
        example="@user",
        description="Smile at someone or yourself."
    )
    async def smile(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("smile", ctx.author, member)
        image = await self._get_neko_image("smile")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="smug",
        usage="(member)",
        example="@user",
        description="Be smug with someone or yourself."
    )
    async def smug(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("smug", ctx.author, member)
        image = await self._get_neko_image("smug")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="stare",
        usage="(member)",
        example="@user",
        description="Stare at someone or yourself."
    )
    async def stare(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("stare", ctx.author, member)
        image = await self._get_neko_image("stare")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="think",
        usage="(member)",
        example="@user",
        description="Think with someone or yourself."
    )
    async def think(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("think", ctx.author, member)
        image = await self._get_neko_image("think")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="thumbsup",
        usage="(member)",
        example="@user",
        description="Give a thumbs up to someone or yourself."
    )
    async def thumbsup(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("thumbsup", ctx.author, member)
        image = await self._get_neko_image("thumbsup")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="tickle",
        usage="(member)",
        example="@user",
        description="Tickle someone or yourself."
    )
    async def tickle(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("tickle", ctx.author, member)
        image = await self._get_neko_image("tickle")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="wave",
        usage="(member)",
        example="@user",
        description="Wave at someone or yourself."
    )
    async def wave(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("wave", ctx.author, member)
        image = await self._get_neko_image("wave")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="wink",
        usage="(member)",
        example="@user",
        description="Wink at someone or yourself."
    )
    async def wink(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("wink", ctx.author, member)
        image = await self._get_neko_image("wink")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="yawn",
        usage="(member)",
        example="@user",
        description="Yawn with someone or yourself."
    )
    async def yawn(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("yawn", ctx.author, member)
        image = await self._get_neko_image("yawn")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="yeet",
        usage="(member)",
        example="@user",
        description="Yeet someone or yourself."
    )
    async def yeet(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("yeet", ctx.author, member)
        image = await self._get_neko_image("yeet")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    # --- Image-only categories ---
    @hybrid_command(
        name="neko",
        description="Get a random neko image."
    )
    async def neko(self, ctx):
        image = await self._get_neko_image("neko")
        embed = discord.Embed(description=f"{ctx.author.mention} gets a random neko!", color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="waifu",
        description="Get a random waifu image."
    )
    async def waifu(self, ctx):
        image = await self._get_neko_image("waifu")
        embed = discord.Embed(description=f"{ctx.author.mention} gets a random waifu!", color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="kitsune",
        description="Get a random kitsune image."
    )
    async def kitsune(self, ctx):
        image = await self._get_neko_image("kitsune")
        embed = discord.Embed(description=f"{ctx.author.mention} gets a random kitsune!", color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="husbando",
        description="Get a random husbando image."
    )
    async def husbando(self, ctx):
        image = await self._get_neko_image("husbando")
        embed = discord.Embed(description=f"{ctx.author.mention} gets a random husbando!", color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    # You can add more commands for each action/category as needed, following the above pattern.

