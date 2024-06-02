from datetime import datetime, timedelta

import aiohttp
import dateparser
import discord
import humanize
from discord import Emoji, Member, User
from discord.ext.commands import (BadArgument, CommandError, Converter,
                                  MemberConverter, MemberNotFound,
                                  MessageConverter, MessageNotFound,
                                  RoleConverter, RoleNotFound)
from orjson import dumps

import config
from tools.converters.color import get_color
from tools.managers import regex
from tools.managers.context import Context
from tools.utilities import human_join

activity_types = [
    {
        "id": 755827207812677713,
        "name": "Poker Night",
        "emoji": "♠",
    },
    {
        "id": 902271654783242291,
        "name": "Sketch Heads",
        "emoji": "🎨",
    },
    {
        "id": 880218394199220334,
        "name": "Watch Togther",
        "emoji": "🎥",
    },
    {
        "id": 832025144389533716,
        "name": "Blazing 8s",
        "emoji": "🎴",
    },
    {
        "id": 832012774040141894,
        "name": "Chess in the Park",
        "emoji": "♟",
    },
    {
        "id": 832013003968348200,
        "name": "Checkers in the Park",
        "emoji": "⚪",
    },
    {
        "id": 879863686565621790,
        "name": "Letter League",
        "emoji": "🅰",
    },
    {
        "id": 879863976006127627,
        "name": "Word Snacks",
        "emoji": "🍬",
    },
    {
        "id": 852509694341283871,
        "name": "Spell Cast",
        "emoji": "🪄",
    },
    {
        "id": 945737671223947305,
        "name": "Putt Party",
        "emoji": "⛳",
    },
    {
        "id": 903769130790969345,
        "name": "Land-io",
        "emoji": "👁",
    },
    {
        "id": 947957217959759964,
        "name": "Bobble League",
        "emoji": "⚽",
    },
]


regions = [
    "brazil",
    "hongkong",
    "india",
    "japan",
    "rotterdam",
    "russia",
    "singapore",
    "south-korea",
    "southafrica",
    "sydney",
    "us-central",
    "us-east",
    "us-south",
    "us-west",
]


class SynthEngine(Converter):
    @staticmethod
    async def convert(ctx: Context, argument: str) -> str:
        voices = dict(
            male="en_au_002",
            ghostface="en_us_ghostface",
            chewbacca="en_us_chewbacca",
            stormtrooper="en_us_stormtrooper",
            stitch="en_us_stitch",
            narrator="en_male_narration",
            peaceful="en_female_emotional",
            glorious="en_female_ht_f08_glorious",
            chipmunk="en_male_m2_xhxs_m03_silly",
            chipmunks="en_male_m2_xhxs_m03_silly",
        )

        if voice := voices.get(argument.lower()):
            return voice

        raise CommandError(f"Synth engine **{argument}** not found")


def time(value: timedelta, short: bool = False):
    value = (
        humanize.precisedelta(value, format="%0.f")
        .replace("ago", "")
        .replace("from now", "")
    )
    if value.endswith("s") and value[:-1].isdigit() and int(value[:-1]) == 1:
        value = value[:-1]

    if short:
        value = " ".join(value.split(" ", 2)[:2])
        return value.removesuffix(",")
    return value


class Time:
    def __init__(self, seconds: int):
        self.seconds: int = seconds
        self.minutes: int = (self.seconds % 3600) // 60
        self.hours: int = (self.seconds % 86400) // 3600
        self.days: int = self.seconds // 86400
        self.weeks: int = self.days // 7
        self.delta: timedelta = timedelta(seconds=self.seconds)
        self.from_now: datetime = discord.utils.utcnow() + self.delta

    def __str__(self):
        return time(self.delta)


class TimeConverter(Converter):
    @staticmethod
    def _convert(argument: str):
        if matches := regex.TIME.findall(argument):
            seconds = 0
            units = dict(
                s=1,
                m=60,
                h=3600,
                d=86400,
                w=604800,
            )
            for time, unit in matches:
                try:
                    seconds += units[unit] * int(time)
                except KeyError as e:
                    raise CommandError(f"Invalid time unit `{unit}`") from e

            return seconds

    async def convert(self, ctx: Context, argument: str):
        if seconds := self._convert(argument):
            return Time(seconds)
        raise CommandError("Please **specify** a valid time - `1h 30m`")


class Location(Converter):
    @staticmethod
    async def convert(ctx: Context, argument: str) -> str:
        async with ctx.typing(), aiohttp.ClientSession(
            json_serialize=lambda x: dumps(x).decode()
        ) as session:
            response = await session.get(
                "https://api.weatherapi.com/v1/timezone.json",
                params=dict(key=config.Authorization.weather, q=argument),
            )
            if response.status == 200:
                data = await response.json()
                return data.get("location")
            raise CommandError(f"Location **{argument}** not found")


class Emoji:  # noqa: F811
    def __init__(self, name: str, url: str, **kwargs):
        self.name: str = name
        self.url: str = url
        self.id: int = int(kwargs.get("id", 0))
        self.animated: bool = kwargs.get("animated", False)

    async def read(self):
        async with aiohttp.ClientSession() as session, session.get(
            self.url
        ) as response:
            return await response.read()

    def __str__(self):
        if self.id:
            return f"<{'a' if self.animated else ''}:{self.name}:{self.id}>"
        return self.name

    def __repr__(self):
        return f"<name={self.name!r} url={self.url!r}>"


class EmojiFinder(Converter):
    @staticmethod
    async def convert(ctx: Context, argument: str):
        if match := regex.DISCORD_EMOJI.match(argument):
            return Emoji(
                match.group("name"),
                "https://cdn.discordapp.com/emojis/"
                + match.group("id")
                + (".gif" if match.group("animated") else ".png"),
                id=int(match.group("id")),
                animated=bool(match.group("animated")),
            )
        characters = [hex(ord(character))[2:] for character in argument]
        if len(characters) == 2 and "fe0f" in characters:
            characters.remove("fe0f")
        if "20e3" in characters:
            characters.remove("20e3")

        hexcode = "-".join(characters)
        url = f"https://cdn.notsobot.com/twemoji/512x512/{hexcode}.png"
        await ctx.bot.session.request(
            "GET",
            url,
            raise_for={404: ("I wasn't able to find that **emoji**")},
        )
        return Emoji(argument, url)


LANGUAGES = {
    "afrikaans": "af",
    "albanian": "sq",
    "amharic": "am",
    "arabic": "ar",
    "armenian": "hy",
    "azerbaijani": "az",
    "basque": "eu",
    "belarusian": "be",
    "bengali": "bn",
    "bosnian": "bs",
    "bulgarian": "bg",
    "catalan": "ca",
    "cebuano": "ceb",
    "chichewa": "ny",
    "chinese": "zh-cn",
    "chinese (simplified)": "zh-cn",
    "chinese (traditional)": "zh-tw",
    "corsican": "co",
    "croatian": "hr",
    "czech": "cs",
    "danish": "da",
    "dutch": "nl",
    "english": "en",
    "esperanto": "eo",
    "estonian": "et",
    "filipino": "tl",
    "finnish": "fi",
    "french": "fr",
    "frisian": "fy",
    "galician": "gl",
    "georgian": "ka",
    "german": "de",
    "greek": "el",
    "gujarati": "gu",
    "haitian creole": "ht",
    "hausa": "ha",
    "hawaiian": "haw",
    "hebrew": "he",
    "hindi": "hi",
    "hmong": "hmn",
    "hungarian": "hu",
    "icelandic": "is",
    "igbo": "ig",
    "indonesian": "id",
    "irish": "ga",
    "italian": "it",
    "japanese": "ja",
    "javanese": "jw",
    "kannada": "kn",
    "kazakh": "kk",
    "khmer": "km",
    "korean": "ko",
    "kurdish (kurmanji)": "ku",
    "kyrgyz": "ky",
    "lao": "lo",
    "latin": "la",
    "latvian": "lv",
    "lithuanian": "lt",
    "luxembourgish": "lb",
    "macedonian": "mk",
    "malagasy": "mg",
    "malay": "ms",
    "malayalam": "ml",
    "maltese": "mt",
    "maori": "mi",
    "marathi": "mr",
    "mongolian": "mn",
    "myanmar (burmese)": "my",
    "nepali": "ne",
    "norwegian": "no",
    "odia": "or",
    "pashto": "ps",
    "persian": "fa",
    "polish": "pl",
    "portuguese": "pt",
    "punjabi": "pa",
    "romanian": "ro",
    "russian": "ru",
    "samoan": "sm",
    "scots gaelic": "gd",
    "serbian": "sr",
    "sesotho": "st",
    "shona": "sn",
    "sindhi": "sd",
    "sinhala": "si",
    "slovak": "sk",
    "slovenian": "sl",
    "somali": "so",
    "spanish": "es",
    "sundanese": "su",
    "swahili": "sw",
    "swedish": "sv",
    "tajik": "tg",
    "tamil": "ta",
    "telugu": "te",
    "thai": "th",
    "turkish": "tr",
    "ukrainian": "uk",
    "urdu": "ur",
    "uyghur": "ug",
    "uzbek": "uz",
    "vietnamese": "vi",
    "welsh": "cy",
    "xhosa": "xh",
    "yiddish": "yi",
    "yoruba": "yo",
    "zulu": "zu",
}


class Percentage(Converter):
    @staticmethod
    async def convert(ctx: Context, argument: str):
        if argument.isdigit():
            argument = int(argument)
        elif match := regex.PERCENTAGE.match(argument):
            argument = int(match.group("percentage"))
        else:
            argument = 0

        if argument < 0 or argument > 100:
            raise CommandError("Please **specify** a valid percentage")

        return argument


def get_language(value: str):
    value = value.lower()
    if value not in LANGUAGES:
        return None if value not in LANGUAGES.values() else value
    return LANGUAGES[value]


class Language(Converter):
    @staticmethod
    async def convert(ctx: Context, argument: str):
        if language := get_language(argument):
            return language
        raise CommandError(f"Language **{argument}** not found")


DANGEROUS_PERMISSIONS = [
    "administrator",
    "kick_members",
    "ban_members",
    "manage_guild",
    "manage_roles",
    "manage_channels",
    "manage_emojis",
    "manage_webhooks",
    "manage_nicknames",
    "mention_everyone",
]


class Role(RoleConverter):
    @staticmethod
    async def convert(ctx: Context, argument: str):
        role = None
        if match := regex.DISCORD_ID.match(argument):
            role = ctx.guild.get_role(int(match.group(1)))
        elif match := regex.DISCORD_ROLE_MENTION.match(argument):
            role = ctx.guild.get_role(int(match.group(1)))
        else:
            role = (
                discord.utils.find(
                    lambda r: r.name.lower() == argument.lower(),
                    ctx.guild.roles,
                )
                or discord.utils.find(
                    lambda r: argument.lower() in r.name.lower(),
                    ctx.guild.roles,
                )
                or discord.utils.find(
                    lambda r: r.name.lower().startswith(argument.lower()),
                    ctx.guild.roles,
                )
            )
        if not role or role.is_default():
            raise RoleNotFound(argument)
        return role

    @staticmethod
    async def manageable(ctx: Context, role: discord.Role, booster: bool = False):
        if role.managed and not booster:
            raise CommandError(f"You're unable to manage {role.mention}")
        if not role.is_assignable() and not booster:
            raise CommandError(f"I'm unable to manage {role.mention}")
        if role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner.id:
            raise CommandError(f"You're unable to manage {role.mention}")

        return True

    @staticmethod
    async def dangerous(ctx: Context, role: discord.Role, _: str = "manage"):
        if (
            permissions := list(
                filter(
                    lambda permission: getattr(role.permissions, permission),
                    DANGEROUS_PERMISSIONS,
                )
            )
        ) and ctx.author.id != ctx.guild.owner_id:
            raise CommandError(
                f"You're unable to {_} {role.mention} because it has the `{permissions[0]}` permission"
            )

        return False


class Roles(RoleConverter):
    @staticmethod
    async def convert(ctx: Context, argument: str):
        roles = []
        for role in argument.split(","):
            try:
                role = await Role().convert(ctx, role.strip())
                if role not in roles:
                    roles.append(role)
            except RoleNotFound:
                continue

        if not roles:
            raise RoleNotFound(argument)
        return roles

    @staticmethod
    async def manageable(
        ctx: Context, roles: list[discord.Role], booster: bool = False
    ):
        for role in roles:
            await Role().manageable(ctx, role, booster)

        return True

    @staticmethod
    async def dangerous(ctx: Context, roles: list[discord.Role], _: str = "manage"):
        for role in roles:
            await Role().dangerous(ctx, role, _)


class Member(MemberConverter):
    async def convert(self, ctx: Context, argument: str) -> Member:
        return await super().convert(ctx, argument)

    @staticmethod
    async def hierarchy(ctx: Context, user: Member, author: bool = False):
        if isinstance(user, User):
            return True
        if ctx.guild.me.top_role <= user.top_role:
            raise CommandError(
                f"I'm unable to **{ctx.command.qualified_name}** {user.mention}"
            )
        if ctx.author.id == user.id and not author:
            raise CommandError(
                f"You're unable to **{ctx.command.qualified_name}** yourself"
            )
        if ctx.author.id == user.id:
            return True
        if ctx.author.id == ctx.guild.owner_id:
            return True
        if user.id == ctx.guild.owner_id:
            raise CommandError(
                f"You're unable to **{ctx.command.qualified_name}** the **server owner**"
            )
        if ctx.author.top_role.is_default():
            raise CommandError(
                f"You're unable to **{ctx.command.qualified_name}** {user.mention} because your **highest role** is {ctx.guild.default_role.mention}"
            )
        if ctx.author.top_role == user.top_role:
            raise CommandError(
                f"You're unable to **{ctx.command.qualified_name}** {user.mention} because they have the **same role** as you"
            )
        if ctx.author.top_role < user.top_role:
            raise CommandError(
                f"You're unable to **{ctx.command.qualified_name}** {user.mention} because they have a **higher role** than you"
            )
        return True


class ImageFinder(Converter):
    @staticmethod
    async def convert(ctx: Context, argument: str):
        try:
            member = await Member().convert(ctx, argument)
            if member:
                return member.display_avatar.url
        except Exception:
            pass

        if match := regex.DISCORD_ATTACHMENT.match(argument):
            if match.group("mime") not in (
                "png",
                "jpg",
                "jpeg",
                "webp",
                "gif",
            ):
                raise CommandError(f"Invalid image format: **{match.group('mime')}**")
            return match.group()
        if match := regex.IMAGE_URL.match(argument):
            return match.group()
        raise CommandError("Couldn't find an **image**")

    async def search(self, history: bool = True):
        if message := self.replied_message:
            for attachment in message.attachments:
                if attachment.content_type.split("/", 1)[1] in (
                    "png",
                    "jpg",
                    "jpeg",
                    "webp",
                    "gif",
                ):
                    return attachment.url
            for embed in message.embeds:
                if image := embed.image:
                    if match := regex.DISCORD_ATTACHMENT.match(image.url):
                        if match.group("mime") not in (
                            "png",
                            "jpg",
                            "jpeg",
                            "webp",
                            "gif",
                        ):
                            raise CommandError(
                                f"Invalid image format: **{match.group('mime')}**"
                            )
                        return match.group()
                    if match := regex.IMAGE_URL.match(image.url):
                        return match.group()
                elif thumbnail := embed.thumbnail:
                    if match := regex.DISCORD_ATTACHMENT.match(thumbnail.url):
                        if match.group("mime") not in (
                            "png",
                            "jpg",
                            "jpeg",
                            "webp",
                            "gif",
                        ):
                            raise CommandError(
                                f"Invalid image format: **{match.group('mime')}**"
                            )
                        return match.group()
                    if match := regex.IMAGE_URL.match(thumbnail.url):
                        return match.group()

        if self.message.attachments:
            for attachment in self.message.attachments:
                if attachment.content_type.split("/", 1)[1] in (
                    "png",
                    "jpg",
                    "jpeg",
                    "webp",
                    "gif",
                ):
                    return attachment.url

        if history:
            async for message in self.channel.history(limit=50):
                if message.attachments:
                    for attachment in message.attachments:
                        if attachment.content_type.split("/", 1)[1] in (
                            "png",
                            "jpg",
                            "jpeg",
                            "webp",
                            "gif",
                        ):
                            return attachment.url
                if message.embeds:
                    for embed in message.embeds:
                        if image := embed.image:
                            if match := regex.DISCORD_ATTACHMENT.match(image.url):
                                if match.group("mime") not in (
                                    "png",
                                    "jpg",
                                    "jpeg",
                                    "webp",
                                    "gif",
                                ):
                                    raise CommandError(
                                        f"Invalid image format: **{match.group('mime')}**"
                                    )
                                return match.group()
                            if match := regex.IMAGE_URL.match(image.url):
                                return match.group()
                        elif thumbnail := embed.thumbnail:
                            if match := regex.DISCORD_ATTACHMENT.match(thumbnail.url):
                                if match.group("mime") not in (
                                    "png",
                                    "jpg",
                                    "jpeg",
                                    "webp",
                                    "gif",
                                ):
                                    raise CommandError(
                                        f"Invalid image format: **{match.group('mime')}**"
                                    )
                                return match.group()
                            if match := regex.IMAGE_URL.match(thumbnail.url):
                                return match.group()

        raise CommandError("Please **provide** an image")


class Bitrate(Converter):
    @staticmethod
    async def convert(ctx: Context, argument: str) -> int:
        if argument.isdigit():
            argument = int(argument)

        elif match := regex.BITRATE.match(argument):
            argument = int(match.group(1))

        else:
            argument = 0

        if argument < 8:
            raise CommandError("**Bitrate** cannot be less than `8 kbps`!")

        if argument > int(ctx.guild.bitrate_limit / 1000):
            raise CommandError(
                f"`{argument}kbps` cannot be **greater** than `{int(ctx.guild.bitrate_limit / 1000)}kbps`!"
            )

        return argument


class Region(Converter):
    @staticmethod
    async def convert(ctx: Context, argument: str) -> int:
        argument = argument.lower().replace(" ", "-")
        if argument not in regions:
            raise CommandError(
                "**Voice region** must be one of "
                + human_join([f"`{region}`" for region in regions])
            )

        return argument


class ChartSize(Converter):
    @staticmethod
    async def convert(ctx: Context, argument: str):
        if "x" not in argument:
            raise CommandError(
                "Collage size **incorrectly formatted** - example: `6x6`"
            )
        if len(argument.split("x")) != 2:
            raise CommandError(
                "Collage size **incorrectly formatted** - example: `6x6`"
            )
        row, col = argument.split("x")
        if not row.isdigit() or not col.isdigit():
            raise CommandError(
                "Collage size **incorrectly formatted** - example: `6x6`"
            )
        if (int(row) + int(col)) < 2:
            raise CommandError("Collage size **too small**\n> Minimum size is `1x1`")
        if (int(row) + int(col)) > 20:
            raise CommandError("Collage size **too large**\n> Maximum size is `10x10`")

        return f"{row}x{col}"


class MemberStrict(MemberConverter):
    @staticmethod
    async def convert(ctx: Context, argument: str):
        member = None
        if match := regex.DISCORD_ID.match(argument):
            member = ctx.guild.get_member(int(match.group(1)))
        elif match := regex.DISCORD_USER_MENTION.match(argument):
            member = ctx.guild.get_member(int(match.group(1)))

        if not member:
            raise MemberNotFound(argument)
        return member


class Date(Converter):
    @staticmethod
    async def convert(ctx: Context, argument: str):
        if date := dateparser.parse(argument):
            return date
        raise CommandError("Date not recognized - Example: `December 5th`")


class Command(Converter):
    @staticmethod
    async def convert(ctx: Context, argument: str):
        if command := ctx.bot.get_command(argument):
            return command
        raise CommandError(f"Command `{argument}` doesn't exist")


class ImageFinderStrict(Converter):
    @staticmethod
    async def convert(ctx: Context, argument: str):
        # try:
        #     member = await Member().convert(ctx, argument)
        #     if member and not member.display_avatar.is_animated():
        #         return member.display_avatar.url
        # except:
        #     pass

        if match := regex.DISCORD_ATTACHMENT.match(argument):
            if match.group("mime") not in ("png", "jpg", "jpeg", "webp"):
                raise CommandError(f"Invalid image format: **{match.group('mime')}**")
            return match.group()
        if match := regex.IMAGE_URL.match(argument):
            if match.group("mime") == "gif":
                raise CommandError(f"Invalid image format: **{match.group('mime')}**")
            return match.group()
        raise CommandError("Couldn't find an **image**")

    async def search(self, history: bool = True):
        if message := self.replied_message:
            for attachment in message.attachments:
                if attachment.content_type.split("/", 1)[1] in (
                    "png",
                    "jpg",
                    "jpeg",
                    "webp",
                ):
                    return attachment.url
            for embed in message.embeds:
                if image := embed.image:
                    if match := regex.DISCORD_ATTACHMENT.match(image.url):
                        if match.group("mime") not in (
                            "png",
                            "jpg",
                            "jpeg",
                            "webp",
                        ):
                            raise CommandError(
                                f"Invalid image format: **{match.group('mime')}**"
                            )
                        return match.group()
                    if match := regex.IMAGE_URL.match(image.url):
                        if match.group("mime") == "gif":
                            continue
                        return match.group()
                elif thumbnail := embed.thumbnail:
                    if match := regex.DISCORD_ATTACHMENT.match(thumbnail.url):
                        if match.group("mime") not in (
                            "png",
                            "jpg",
                            "jpeg",
                            "webp",
                        ):
                            raise CommandError(
                                f"Invalid image format: **{match.group('mime')}**"
                            )
                        return match.group()
                    if match := regex.IMAGE_URL.match(thumbnail.url):
                        if match.group("mime") == "gif":
                            continue
                        return match.group()

        if self.message.attachments:
            for attachment in self.message.attachments:
                if attachment.content_type.split("/", 1)[1] in (
                    "png",
                    "jpg",
                    "jpeg",
                    "webp",
                ):
                    return attachment.url

        if history:
            async for message in self.channel.history(limit=50):
                if message.attachments:
                    for attachment in message.attachments:
                        if attachment.content_type.split("/", 1)[1] in (
                            "png",
                            "jpg",
                            "jpeg",
                            "webp",
                        ):
                            return attachment.url
                if message.embeds:
                    for embed in message.embeds:
                        if image := embed.image:
                            if match := regex.DISCORD_ATTACHMENT.match(image.url):
                                if match.group("mime") not in (
                                    "png",
                                    "jpg",
                                    "jpeg",
                                    "webp",
                                ):
                                    continue
                                return match.group()
                            if match := regex.IMAGE_URL.match(image.url):
                                if match.group("mime") == "gif":
                                    continue
                                return match.group()
                        elif thumbnail := embed.thumbnail:
                            if match := regex.DISCORD_ATTACHMENT.match(thumbnail.url):
                                if match.group("mime") not in (
                                    "png",
                                    "jpg",
                                    "jpeg",
                                    "webp",
                                ):
                                    continue
                                return match.group()
                            if match := regex.IMAGE_URL.match(thumbnail.url):
                                if match.group("mime") == "gif":
                                    continue
                                return match.group()

        raise CommandError("Please **provide** an image")


class Position(Converter):
    @staticmethod
    async def convert(ctx: Context, argument: str) -> int:
        argument = argument.lower()
        player = ctx.voice_client
        ms: int = 0

        if ctx.invoked_with == "ff" and not argument.startswith("+"):
            argument = f"+{argument}"

        elif ctx.invoked_with == "rw" and not argument.startswith("-"):
            argument = f"-{argument}"

        if match := regex.Position.HH_MM_SS.fullmatch(argument):
            ms += (
                int(match.group("h")) * 3600000
                + int(match.group("m")) * 60000
                + int(match.group("s")) * 1000
            )

        elif match := regex.Position.MM_SS.fullmatch(argument):
            ms += int(match.group("m")) * 60000 + int(match.group("s")) * 1000

        elif (match := regex.Position.OFFSET.fullmatch(argument)) and player:
            ms += player.position + int(match.group("s")) * 1000

        elif match := regex.Position.HUMAN.fullmatch(argument):
            if m := match.group("m"):
                if match.group("s") and argument.endswith("m"):
                    raise CommandError(f"Position `{argument}` is not valid")

                ms += int(m) * 60000

            elif s := match.group("s"):
                ms += int(s) * 60000 if argument.endswith("m") else int(s) * 1000
        else:
            raise CommandError(f"Position `{argument}` is not valid")

        return ms


class Status(Converter):
    async def convert(self, ctx: Context, argument: str) -> bool:
        if argument.lower() in (
            "enable",
            "true",
            "yes",
            "on",
        ):
            return True

        if argument.lower() in (
            "disable",
            "false",
            "none",
            "null",
            "off",
            "no",
        ):
            return False
        raise CommandError("Please specify **yes** or **no**")


class State(Converter):
    @staticmethod
    async def convert(ctx: Context, argument: str):
        if argument.lower() in {"on", "yes", "true", "enable"}:
            return True
        if argument.lower() in {
            "off",
            "no",
            "none",
            "null",
            "false",
            "disable",
        }:
            return False
        raise CommandError("Please **specify** a valid state - `on` or `off`")


class StickerFinder(Converter):
    @staticmethod
    async def convert(ctx: Context, argument: str):
        try:
            message = await MessageConverter().convert(ctx, argument)
        except MessageNotFound:
            pass
        else:
            if message.stickers:
                sticker = await message.stickers[0].fetch()
                if isinstance(sticker, discord.StandardSticker):
                    raise CommandError("Sticker **must** be a nitro sticker")
                return sticker
            raise CommandError(
                f"[**Message**]({message.jump_url}) doesn't contain a sticker"
            )

        if sticker := discord.utils.get(ctx.guild.stickers, name=argument):
            return sticker
        raise CommandError("That **sticker** doesn't exist in this server")

    async def search(self):
        if self.message.stickers:
            sticker = await self.message.stickers[0].fetch()
        elif self.replied_message:
            if self.replied_message.stickers:
                sticker = await self.replied_message.stickers[0].fetch()
            else:
                raise CommandError(
                    f"[**Message**]({self.replied_message.jump_url}) doesn't contain a sticker"
                )
        else:
            raise CommandError("Please **specify** a sticker")

        if isinstance(sticker, discord.StandardSticker):
            raise CommandError("Sticker **must** be a nitro sticker")
        return sticker


class MediaFinder(Converter):
    @staticmethod
    async def convert(ctx: Context, argument: str):
        try:
            member = await Member().convert(ctx, argument)
            if member:
                return member.display_avatar.url
        except Exception:
            pass

        if match := regex.DISCORD_ATTACHMENT.match(argument):
            if match.group("mime") not in (
                "mp3",
                "mp4",
                "mpeg",
                "mpga",
                "m4a",
                "wav",
                "mov",
                "webm",
                "quicktime",
            ):
                raise CommandError(f"Invalid media format: **{match.group('mime')}**")
            return match.group()
        if match := regex.MEDIA_URL.match(argument):
            return match.group()
        raise CommandError("Couldn't find any **media**")

    async def search(self, history: bool = True):
        if message := self.replied_message:
            for attachment in message.attachments:
                if attachment.content_type.split("/", 1)[1] in (
                    "mp3",
                    "mp4",
                    "mpeg",
                    "mpga",
                    "m4a",
                    "wav",
                    "mov",
                    "webp",
                    "quicktime",
                ):
                    return attachment.url

        if self.message.attachments:
            for attachment in self.message.attachments:
                if attachment.content_type.split("/", 1)[1] in (
                    "mp3",
                    "mp4",
                    "mpeg",
                    "mpga",
                    "m4a",
                    "wav",
                    "mov",
                    "webp",
                    "quicktime",
                ):
                    return attachment.url

        if history:
            async for message in self.channel.history(limit=50):
                if message.attachments:
                    for attachment in message.attachments:
                        if attachment.content_type.split("/", 1)[1] in (
                            "mp3",
                            "mp4",
                            "mpeg",
                            "mpga",
                            "m4a",
                            "wav",
                            "mov",
                            "webp",
                        ):
                            return attachment.url

        raise CommandError("Please **provide** a media file")


class Color(Converter):
    @staticmethod
    async def convert(ctx: Context, argument: str) -> discord.Color:
        if argument.lower() == "random":
            return discord.Color.random()

        try:
            return (await MemberConverter().convert(ctx, argument)).color
        except BadArgument:
            pass

        try:
            return (await RoleConverter().convert(ctx, argument)).color
        except BadArgument:
            pass

        if not (color := get_color(argument)):
            raise CommandError(f"**#{argument}** is an invalid hex code")

        return color

    @staticmethod
    def from_str(color: str) -> discord.Color:
        color = color.removeprefix("#")
        return discord.Color(int(color, 16))
