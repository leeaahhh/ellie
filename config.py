
token: str = (
    "MTIwNjMwNjk4MTcwMzQ1MDY1NA.GAWbPo.ZSvynvbu7LBltWyDlBRwTQxQ1jo7HCN2gteBvA"

)

prefix: str = ","
owners: list[int] = [
    1202356249975595068,
    1188222472441561179,
    1164949148974469210,
]


class Color:
    neutral: int = 0x2B2D31
    approval: int = 0xA9E97A
    error: int = 0xFFCC00


class Emoji:
    class Paginator:
        navigate: str = "<:navigate:1181084168696889414>"
        previous: str = "<:previous:1181084179337846937>"
        _next: str = "<:next:1181084172614369360>"
        cancel: str = "<:cancel:1181084167048548422>"

    class Interface:
        lock: str = "<:lock:1179363835791036416>"
        unlock: str = "<:unlock:1179363822276976650>"
        ghost: str = "<:hide:1179365329089081386>"
        reveal: str = "<:reveal:1179365289855565886>"
        claim: str = "<:claim:1179365898516172851>"
        disconnect: str = "<:disconnect:1179365873262272552>"
        activity: str = "<:activity:1179366270316073031>"
        information: str = "<:information:1179366091995217940>"
        increase: str = "<:increase:1179366475308478568>"
        decrease: str = "<:decrease:1179366580962992209>"

    approve: str = "<:approve:1179325570589401112>"
    warn: str = "<:warn:1179324619992350740>"
    deny: str = "<:deny:1179367117154431026>"
    cooldown: str = ":notepad_spiral:"


class Database:
    host: str = "localhost"
    port: int = 5432
    name: str = "lain"
    user: str = "postgres"
    password: str = "iqYY50VZRlbdc0n"


class Lavalink:
    host: str = "localhost"
    port: int = 2333
    password: str = "youshallnotpass"
    secure: bool = False


class Authorization:
    class Spotify:
        client_id: str = "7a4483c9ae964b8f946ccf4c56d5af25"
        client_secret: str = "28a9f7417338469e83607aae36ce73fc"

    lastfm: list[str] = [
        "f53a9b12f455c8a1c97f875f8cea0978",
    ]
    removebg: str = "gypCjW9B2UwdLwZtJ6tPcoYY"
    weather: str = "gypCjW9B2UwdLwZtJ6tPcoYY"
