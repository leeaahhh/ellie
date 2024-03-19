from re import IGNORECASE, compile

DISCORD_MESSAGE = compile(
    r"(?:https?://)?(?:canary\.|ptb\.|www\.)?discord(?:app)?.(?:com/channels|gg)/(?P<guild_id>[0-9]{17,22})/(?P<channel_id>[0-9]{17,22})/(?P<message_id>[0-9]{17,22})"
)
TIME = compile(r"(?P<time>\d+)(?P<unit>[smhdw])")

URL = compile(r"(?:http\:|https\:)?\/\/[^\s]*")
IMAGE_URL = compile(r"(?:http\:|https\:)?\/\/.*\.(?P<mime>png|jpg|jpeg|webp|gif)")
MEDIA_URL = compile(
    r"(?:http\:|https\:)?\/\/.*\.(?P<mime>mp3|mp4|mpeg|mpga|m4a|wav|mov|webm)"
)
DISCORD_ATTACHMENT = compile(
    r"(https://|http://)?(cdn\.|media\.)discord(app)?\.(com|net)/(attachments|avatars|icons|banners|splashes)/[0-9]{17,22}/([0-9]{17,22}/(?P<filename>.{1,256})|(?P<hash>.{32}))\.(?P<mime>[0-9a-zA-Z]{2,4})?"
)

PERCENTAGE = compile(r"(?P<percentage>\d+)%")
BITRATE = compile(r"(?P<bitrate>\d+)kbps")
DISCORD_ROLE_MENTION = compile(r"<@&(\d+)>")
DISCORD_ID = compile(r"^[0-9]{17,}$")
DISCORD_EMOJI = compile(r"<(?P<animated>a)?:(?P<name>[a-zA-Z0-9_]+):(?P<id>\d+)>")
DISCORD_USER_MENTION = compile(r"<@?(\d+)>")
DISCORD_INVITE = compile(
    r"(?:https?://)?discord(?:app)?.(?:com/invite|gg)/[a-zA-Z0-9]+/?"
)
STRING = compile(r"[a-zA-Z0-9 ]+")
TIME = compile(r"(?P<time>\d+)(?P<unit>[smhdw])")
TIME_HHMMSS = compile(r"(?P<h>\d{1,2}):(?P<m>\d{1,2}):(?P<s>\d{1,2})")
TIME_SS = compile(r"(?P<m>\d{1,2}):(?P<s>\d{1,2})")
TIME_HUMAN = compile(r"(?:(?P<m>\d+)\s*m\s*)?(?P<s>\d+)\s*[sm]")
TIME_OFFSET = compile(r"(?P<s>(?:\-|\+)\d+)\s*s", IGNORECASE)


class Position:
    HH_MM_SS = compile(r"(?P<h>\d{1,2}):(?P<m>\d{1,2}):(?P<s>\d{1,2})")
    MM_SS = compile(r"(?P<m>\d{1,2}):(?P<s>\d{1,2})")
    HUMAN = compile(r"(?:(?P<m>\d+)\s*m\s*)?(?P<s>\d+)\s*[sm]")
    OFFSET = compile(r"(?P<s>(?:\-|\+)\d+)\s*s")
