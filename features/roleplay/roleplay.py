import discord
from discord.ext import commands
import aiohttp
from typing import Optional
import config
from discord.ext.commands import command  # change from hybrid_command

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
    @command(
        name="angry",
        usage="(member)",
        help="Get angry at someone or yourself."
    )
    async def angry(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("angry", ctx.author, member)
        image = await self._get_neko_image("angry")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="baka",
        usage="(member)",
        help="Call someone or yourself a baka."
    )
    async def baka(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("baka", ctx.author, member)
        image = await self._get_neko_image("baka")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="bite",
        usage="(member)",
        help="Bite someone or yourself."
    )
    async def bite(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("bite", ctx.author, member)
        image = await self._get_neko_image("bite")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="blush",
        usage="(member)",
        help="Blush at someone or yourself."
    )
    async def blush(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("blush", ctx.author, member)
        image = await self._get_neko_image("blush")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="bored",
        usage="(member)",
        help="Be bored with someone or yourself."
    )
    async def bored(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("bored", ctx.author, member)
        image = await self._get_neko_image("bored")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="cry",
        usage="(member)",
        help="Cry with someone or yourself."
    )
    async def cry(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("cry", ctx.author, member)
        image = await self._get_neko_image("cry")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="cuddle",
        usage="(member)",
        help="Cuddle someone or yourself."
    )
    async def cuddle(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("cuddle", ctx.author, member)
        image = await self._get_neko_image("cuddle")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="dance",
        usage="(member)",
        help="Dance with someone or yourself."
    )
    async def dance(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("dance", ctx.author, member)
        image = await self._get_neko_image("dance")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="facepalm",
        usage="(member)",
        help="Facepalm at someone or yourself."
    )
    async def facepalm(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("facepalm", ctx.author, member)
        image = await self._get_neko_image("facepalm")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="feed",
        usage="(member)",
        help="Feed someone or yourself."
    )
    async def feed(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("feed", ctx.author, member)
        image = await self._get_neko_image("feed")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="handhold",
        usage="(member)",
        help="Hold hands with someone or yourself."
    )
    async def handhold(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("handhold", ctx.author, member)
        image = await self._get_neko_image("handhold")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="handshake",
        usage="(member)",
        help="Handshake with someone or yourself."
    )
    async def handshake(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("handshake", ctx.author, member)
        image = await self._get_neko_image("handshake")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="happy",
        usage="(member)",
        help="Be happy with someone or yourself."
    )
    async def happy(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("happy", ctx.author, member)
        image = await self._get_neko_image("happy")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="highfive",
        usage="(member)",
        help="Highfive someone or yourself."
    )
    async def highfive(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("highfive", ctx.author, member)
        image = await self._get_neko_image("highfive")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="hug",
        usage="(member)",
        help="Hug someone or yourself."
    )
    async def hug(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("hug", ctx.author, member)
        image = await self._get_neko_image("hug")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)
    

    @command(
        name="kiss",
        usage="(member)",
        help="Kiss someone or yourself."
    )
    async def kiss(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("kiss", ctx.author, member)
        image = await self._get_neko_image("kiss")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="laugh",
        usage="(member)",
        help="Laugh with someone or yourself."
    )
    async def laugh(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("laugh", ctx.author, member)
        image = await self._get_neko_image("laugh")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="lurk",
        usage="(member)",
        help="Lurk with someone or yourself."
    )
    async def lurk(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("lurk", ctx.author, member)
        image = await self._get_neko_image("lurk")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="nod",
        usage="(member)",
        help="Nod at someone or yourself."
    )
    async def nod(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("nod", ctx.author, member)
        image = await self._get_neko_image("nod")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="nom",
        usage="(member)",
        help="Nom someone or yourself."
    )
    async def nom(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("nom", ctx.author, member)
        image = await self._get_neko_image("nom")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="nope",
        usage="(member)",
        help="Nope at someone or yourself."
    )
    async def nope(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("nope", ctx.author, member)
        image = await self._get_neko_image("nope")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="pat",
        usage="(member)",
        help="Pat someone or yourself."
    )
    async def pat(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("pat", ctx.author, member)
        image = await self._get_neko_image("pat")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="peck",
        usage="(member)",
        help="Peck someone or yourself."
    )
    async def peck(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("peck", ctx.author, member)
        image = await self._get_neko_image("peck")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="poke",
        usage="(member)",
        help="Poke someone or yourself."
    )
    async def poke(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("poke", ctx.author, member)
        image = await self._get_neko_image("poke")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="pout",
        usage="(member)",
        help="Pout at someone or yourself."
    )
    async def pout(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("pout", ctx.author, member)
        image = await self._get_neko_image("pout")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="punch",
        usage="(member)",
        help="Punch someone or yourself."
    )
    async def punch(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("punch", ctx.author, member)
        image = await self._get_neko_image("punch")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="run",
        usage="(member)",
        help="Run with someone or yourself."
    )
    async def run(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("run", ctx.author, member)
        image = await self._get_neko_image("run")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="shoot",
        usage="(member)",
        help="Shoot at someone or yourself."
    )
    async def shoot(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("shoot", ctx.author, member)
        image = await self._get_neko_image("shoot")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="shrug",
        usage="(member)",
        help="Shrug at someone or yourself."
    )
    async def shrug(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("shrug", ctx.author, member)
        image = await self._get_neko_image("shrug")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="slap",
        usage="(member)",
        help="Slap someone or yourself."
    )
    async def slap(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("slap", ctx.author, member)
        image = await self._get_neko_image("slap")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="sleep",
        usage="(member)",
        help="Sleep with someone or yourself."
    )
    async def sleep(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("sleep", ctx.author, member)
        image = await self._get_neko_image("sleep")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="smile",
        usage="(member)",
        help="Smile at someone or yourself."
    )
    async def smile(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("smile", ctx.author, member)
        image = await self._get_neko_image("smile")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="smug",
        usage="(member)",
        help="Be smug with someone or yourself."
    )
    async def smug(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("smug", ctx.author, member)
        image = await self._get_neko_image("smug")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="stare",
        usage="(member)",
        help="Stare at someone or yourself."
    )
    async def stare(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("stare", ctx.author, member)
        image = await self._get_neko_image("stare")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="think",
        usage="(member)",
        help="Think with someone or yourself."
    )
    async def think(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("think", ctx.author, member)
        image = await self._get_neko_image("think")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="thumbsup",
        usage="(member)",
        help="Give a thumbs up to someone or yourself."
    )
    async def thumbsup(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("thumbsup", ctx.author, member)
        image = await self._get_neko_image("thumbsup")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="tickle",
        usage="(member)",
        help="Tickle someone or yourself."
    )
    async def tickle(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("tickle", ctx.author, member)
        image = await self._get_neko_image("tickle")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="wave",
        usage="(member)",
        help="Wave at someone or yourself."
    )
    async def wave(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("wave", ctx.author, member)
        image = await self._get_neko_image("wave")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="wink",
        usage="(member)",
        help="Wink at someone or yourself."
    )
    async def wink(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("wink", ctx.author, member)
        image = await self._get_neko_image("wink")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="yawn",
        usage="(member)",
        help="Yawn with someone or yourself."
    )
    async def yawn(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("yawn", ctx.author, member)
        image = await self._get_neko_image("yawn")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="yeet",
        usage="(member)",
        help="Yeet someone or yourself."
    )
    async def yeet(self, ctx, member: discord.Member = None):
        desc = self._get_action_description("yeet", ctx.author, member)
        image = await self._get_neko_image("yeet")
        embed = discord.Embed(description=desc, color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    # --- Image-only categories ---
    @command(
        name="neko",
        help="Get a random neko image."
    )
    async def neko(self, ctx):
        image = await self._get_neko_image("neko")
        embed = discord.Embed(description=f"{ctx.author.mention} gets a random neko!", color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="waifu",
        help="Get a random waifu image."
    )
    async def waifu(self, ctx):
        image = await self._get_neko_image("waifu")
        embed = discord.Embed(description=f"{ctx.author.mention} gets a random waifu!", color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="kitsune",
        help="Get a random kitsune image."
    )
    async def kitsune(self, ctx):
        image = await self._get_neko_image("kitsune")
        embed = discord.Embed(description=f"{ctx.author.mention} gets a random kitsune!", color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    @command(
        name="husbando",
        help="Get a random husbando image."
    )
    async def husbando(self, ctx):
        image = await self._get_neko_image("husbando")
        embed = discord.Embed(description=f"{ctx.author.mention} gets a random husbando!", color=config.Color.neutral)
        if image:
            embed.set_image(url=image)
        await ctx.send(embed=embed)

    # You can add more commands for each action/category as needed, following the above pattern.

