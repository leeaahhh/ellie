import re
from datetime import timedelta
from io import BytesIO
from typing import Any, List, Optional, TypedDict

from discord import Emoji, Guild, TextChannel, User
from discord.ext.commands import CommandError, Converter
from discord.state import ConnectionState
from discord.types.snowflake import Snowflake
from discord.utils import get
from typing_extensions import NotRequired, Type
from yarl import URL

from tools.managers import Context
from tools.utilities import human_join

__all__ = (
    "Username",
    "Domain",
    "Duration",
    "Attachment",
    "Image",
    "Sound",
)

URL_VALIDATION_PATTERN = r"(?:http\:|https\:)?\/\/[^\s]*"
USERNAME_VALIDATION_PATTERN = r"^[a-zA-Z0-9_-]"
DISCORD_FILE_PATTERN = r"(https://|http://)?(cdn\.|media\.)discord(app)?\.(com|net)/(attachments|avatars|icons|banners|splashes)/[0-9]{17,22}/([0-9]{17,22}/(?P<filename>.{1,256})|(?P<hash>.{32}))\.(?P<mime>[0-9a-zA-Z]{2,4})?"
DURATION_PATTERN = r"\s?".join(
    [
        r"((?P<years>\d+?)\s?(years?|y))?",
        r"((?P<months>\d+?)\s?(months?|mo))?",
        r"((?P<weeks>\d+?)\s?(weeks?|w))?",
        r"((?P<days>\d+?)\s?(days?|d))?",
        r"((?P<hours>\d+?)\s?(hours?|hrs|hr?))?",
        r"((?P<minutes>\d+?)\s?(minutes?|mins?|m(?!o)))?",
        r"((?P<seconds>\d+?)\s?(seconds?|secs?|s))?",
    ]
)
NSFW_FILTERS = [
    "economy-simulator",
    "pornhub",
    "pikwy",
    "liveleak",
    "gore",
    "horse",
    "gay",
    "4chan",
    "lesbian",
    "sex",
    "kekma",
    "pornhub",
    "xvideos",
    "xhamster",
    "xnxx",
    "eporner",
    "daftsex",
    "hqporner",
    "beeg",
    "yourporn",
    "spankbang",
    "porntrex",
    "xmoviesforyou",
    "porngo",
    "youjizz",
    "motherless",
    "redtube",
    "youporn",
    "pornone",
    "4tube",
    "porntube",
    "3movs",
    "tube8",
    "porndig",
    "cumlouder",
    "txxx",
    "porndoe",
    "pornhat",
    "ok.xxx",
    "porn00",
    "pornhits",
    "goodporn",
    "bellesa",
    "pornhd3x",
    "xxxfiles",
    "pornktube",
    "tubxporn",
    "tnaflix",
    "porndish",
    "fullporner",
    "porn4days",
    "whoreshub",
    "paradisehill",
    "trendyporn",
    "pornhd8k",
    "xfreehd",
    "porn300",
    "anysex",
    "vxxx",
    "veporn",
    "drtuber",
    "netfapx",
    "letsjerk",
    "pornobae",
    "pornmz",
    "xmegadrive",
    "brazzers3x",
    "pornky",
    "hitprn",
    "porndune",
    "czechvideo",
    "joysporn",
    "watchxxxfree",
    "hdporn92",
    "yespornpleasexxx",
    "reddit",
    "fuxnxx",
    "4kporn",
    "watchpeople",
    "gore",
    "porn",
    "watchporn",
    "plusone8",
    "povaddict",
    "latest",
    "porn",
    "inporn",
    "freeomovie",
    "porntop",
    "pornxp",
    "netfapx.net",
    "anyporn",
    "cliphunter",
    "severeporn",
    "collectionofbestporn",
    "coom",
    "onlyfan",
    "xtapes",
    "xkeezmovies",
    "sextvx",
    "yourdailypornvideos",
    "pornovideoshub",
    "pandamovies",
    "palimas",
    "fullxxxmovies",
    "iceporncasting",
    "pussyspace",
    "pornvibe",
    "siska",
    "xxx",
    "scenes",
    "megatube",
    "fakings",
    "justfullporn",
    "xxvideoss",
    "thepornarea",
    "analdin",
    "xozilla",
    "empflix",
    "eroticmv",
    "erome",
    "vidoz8",
    "perverzija",
    "streamporn",
    "pornhoarder",
    "swingerpornfun",
    "thepornfull",
    "pornfeat",
    "pornwex",
    "pornvideobb",
    "secretstash",
    "mangoporn",
    "castingpornotube",
    "fapmeifyoucan",
    "thepervs",
    "latestporn",
    "pornwis",
    "gimmeporn",
    "whereismyporn",
    "pornoflix",
    "tubeorigin",
    "pornez.cam",
    "euroxxx",
    "americass",
    "sextu",
    "yespornvip",
    "galaxyporn",
    "taxi69",
    "fux.com",
    "sexu",
    "definebabe",
    "hutporner",
    "pornseed",
    "titfap",
    "hd-easyporn",
    "dvdtrailertube",
    "chaturbate",
    "xxx",
]


class Sound(Converter["SoundboardSound"]):
    @staticmethod
    async def convert(ctx: Context, argument: str) -> "SoundboardSound":
        await ctx.bot.ws.send_as_json({"op": 31, "d": {"guild_ids": [ctx.guild.id]}})
        data = await ctx.bot.ws.wait_for(
            "SOUNDBOARD_SOUNDS",
            lambda data: data["guild_id"] == str(ctx.guild.id),
        )

        sounds = [
            SoundboardSound(
                data=sound,
                guild=ctx.guild,
                state=ctx.bot._get_state(),
            )
            for sound in data["soundboard_sounds"]
        ]
        sound = get(sounds, name=argument)
        if not sound:
            raise CommandError("The sound provided doesn't exist!")

        return sound


class Username(Converter[str]):
    def __init__(self: "Username", min: int = 2, max: int = 30):
        self.min = min
        self.max = max

    async def convert(self: "Username", ctx: Context, argument: str) -> str:
        if not (
            re.match(USERNAME_VALIDATION_PATTERN, argument)
            and len(argument) >= self.min
            and len(argument) <= self.max
        ):
            raise CommandError("The username provided didn't pass validation!")

        return argument


class Domain(Converter[URL]):
    def __init__(self: "Domain", filter: bool = True):
        self.filter = filter

    async def convert(self: "Domain", ctx: Context, argument: str) -> URL:
        if not (_ := re.match(URL_VALIDATION_PATTERN, argument)):
            raise CommandError("The URL provided didn't pass validation!")

        if self.filter and (
            isinstance(ctx.channel, TextChannel) and not ctx.channel.nsfw
        ):
            if any(filter in argument for filter in NSFW_FILTERS):
                raise CommandError(
                    f"Host [`{argument.split('/')[2]}`]({argument}) contains NSFW content!"
                )

        return URL(argument)


class Duration(Converter[timedelta]):
    def __init__(
        self: "Duration",
        min: Optional[timedelta] = None,
        max: Optional[timedelta] = None,
        units: Optional[List[str]] = None,
    ):
        self.min = min
        self.max = max
        self.units = units or [
            "weeks",
            "days",
            "hours",
            "minutes",
            "seconds",
        ]

    async def convert(self: "Duration", ctx: Context, argument: str) -> timedelta:
        if not (matches := re.fullmatch(DURATION_PATTERN, argument, re.IGNORECASE)):
            raise CommandError("The duration provided didn't pass validation!")

        units = {
            unit: int(amount) for unit, amount in matches.groupdict().items() if amount
        }
        for unit in units.keys():
            if unit not in self.units:
                raise CommandError(f"The unit `{unit}` is not valid for this command!")

        try:
            duration = timedelta(**units)
        except OverflowError:
            raise CommandError("The duration provided is too long!")

        if self.min and duration < self.min:
            raise CommandError("The duration provided is too short!")

        if self.max and duration > self.max:
            raise CommandError("The duration provided is too long!")

        return duration


class Attachment:
    def __init__(self: "Attachment", fp: bytes, url: str, filename: str):
        self.fp = fp
        self.url = url
        self.filename = filename

    @property
    def buffer(self: "Attachment") -> BytesIO:
        buffer = BytesIO(self.fp)
        buffer.name = self.filename

        return buffer

    @classmethod
    async def fallback(cls: Type["Attachment"], ctx: Context) -> "Attachment":
        message = ctx.message
        if not message.attachments:
            raise CommandError("You must provide an attachment!")

        options = ("video", "audio")
        attachment = message.attachments[0]
        if not attachment.content_type:
            raise CommandError(
                f"The [attachment]({attachment.url}) provided is invalid!"
            )

        if not attachment.content_type.startswith(options):
            human_options = human_join([f"`{option}`" for option in options])

            raise CommandError(
                f"The [attachment]({attachment.url}) provided must be a {human_options} file."
            )

        buffer = await attachment.read()
        return cls(
            fp=buffer,
            url=attachment.url,
            filename=attachment.filename,
        )

    @classmethod
    async def convert(
        cls: Type["Attachment"], ctx: Context, argument: str
    ) -> "Attachment":
        if not (match := re.match(DISCORD_FILE_PATTERN, argument)):
            raise CommandError("The URL provided doesn't match the **Discord** regex!")

        options = ("video", "audio")
        response = await ctx.bot.session.get(match.group())
        if not response.content_type.startswith(options):
            human_options = human_join([f"`{option}`" for option in options])

            raise CommandError(
                f"The [URL]({argument}) provided must be a {human_options} file."
            )

        buffer = await response.read()
        return cls(
            fp=buffer,
            url=match.group(),
            filename=match["filename"],
        )


class Image:
    def __init__(self: "Image", fp: bytes, url: str, filename: str):
        self.fp = fp
        self.url = url
        self.filename = filename

    @property
    def buffer(self: "Image") -> BytesIO:
        buffer = BytesIO(self.fp)
        buffer.name = self.filename

        return buffer

    @classmethod
    async def fallback(cls: Type["Image"], ctx: Context) -> "Image":
        message = ctx.message
        if not message.attachments:
            raise CommandError("You must provide an image!")

        attachment = message.attachments[0]
        if not attachment.content_type:
            raise CommandError(
                f"The [attachment]({attachment.url}) provided is invalid!"
            )

        if not attachment.content_type.startswith("image"):
            raise CommandError(
                f"The [attachment]({attachment.url}) provided must be an image file."
            )

        buffer = await attachment.read()
        return cls(
            fp=buffer,
            url=attachment.url,
            filename=attachment.filename,
        )

    @classmethod
    async def convert(cls: Type["Image"], ctx: Context, argument: str) -> "Image":
        if not (match := re.match(DISCORD_FILE_PATTERN, argument)):
            raise CommandError("The URL provided doesn't match the **Discord** regex!")

        response = await ctx.bot.session.get(match.group())
        if not response.content_type.startswith("image"):
            raise CommandError(f"The [URL]({argument}) provided must be an image file.")

        buffer = await response.read()
        return cls(
            fp=buffer,
            url=match.group(),
            filename=match.group("filename") or match.group("hash"),
        )


class SoundboardSoundPayload(TypedDict):
    name: str
    sound_id: Snowflake
    id: Optional[Snowflake]
    volume: float
    emoji_id: Optional[Snowflake]
    emoji_name: Optional[str]
    override_path: Optional[str]
    guild_id: NotRequired[Snowflake]
    user_id: Snowflake
    available: NotRequired[bool]
    user: NotRequired[User]


class SoundboardSound:
    __slots__ = (
        "_state",
        "name",
        "id",
        "volume",
        "emoji_id",
        "emoji_name",
        "guild_id",
        "guild",
        "user_id",
        "user",
        "available",
    )

    def __init__(
        self,
        data: SoundboardSoundPayload,
        guild: Guild,
        state: ConnectionState,
    ):
        self._state: ConnectionState = state

        self._update(data, guild, state)

    def _update(
        self,
        data: SoundboardSoundPayload,
        guild: Guild,
        state: ConnectionState,
    ):
        self.name: str = data["name"]
        self.id: int = int(data["sound_id"])
        self.volume: float = data["volume"]

        self.emoji_id: Optional[int] = (
            int(data["emoji_id"]) if data["emoji_id"] else None
        )
        self.emoji_name: Optional[str] = data["emoji_name"]

        self.guild_id: Optional[int] = (
            int(data["guild_id"]) if "guild_id" in data else None
        )
        self.guild = guild

        self.user_id: int = int(data["user_id"])
        self.user: Optional[User] = (
            User(state=state, data=data["user"]) if "user" in data else None
        )
        self.available: bool = data.get("available", True)

    @property
    def emoji(self) -> Optional[Emoji]:
        return self._state.get_emoji(self.emoji_id)

    @property
    def sound(self) -> Any:
        raise NotImplementedError
