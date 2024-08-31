token: str = "MTIwNjMwNjk4MTcwMzQ1MDY1NA.GAWbPo.ZSvynvbu7LBltWyDlBRwTQxQ1jo7HCN2gteBvA"

prefix: str = ","
owners: list[int] = [1202356249975595068, 1124385331827966032, 947204756898713721]


class Color:
    neutral: int = 0x2B2D31
    approval: int = 0xA9E97A
    error: int = 0xFFCC00


class Emoji:
    class Paginator:
        navigate: str = "<:navigate:1246615377861935156>"
        previous: str = "<:previous:1246593338996428903>"
        _next: str = "<:next:1246593340506505256>"
        cancel: str = "<:cancel:1246593950559768709>"

    class Interface:
        lock: str = "<:lock:1246592329222066207>"
        unlock: str = "<:unlock:1246592327363858555>"
        ghost: str = "<:ghost~1:1246590287225032858>"
        reveal: str = "<:reveal:1246589920139804736>"
        claim: str = "<:claim:1246590663148175360>"
        disconnect: str = "<:disconnect:1246590582944563262>"
        activity: str = "<:activity:1246589819727908915>"
        information: str = "<:information:1246589713939431557>"
        increase: str = "<:increase:1189117837051187210>"
        decrease: str = "<:decrease:1189117893976272948>"

    approve: str = "<:approve:1246590873509298300>"
    warn: str = "<:warn:1246590006219505684>"
    deny: str = "<:deny:1246590822510497832>"


class Database:
    host: str = "rei-db"
    port: int = 5432
    name: str = "rei"
    user: str = "rei"
    password: str = "pN3PqpT86Nfr"


class Webserver:
    host: str = "0.0.0.0"
    port: int = 59076


class Authorization:
    class Spotify:
        client_id: str = "7a4483c9ae964b8f946ccf4c56d5af25"
        client_secret: str = "28a9f7417338469e83607aae36ce73fc"

    removebg: str = "gypCjW9B2UwdLwZtJ6tPcoYY"
    weather: str = "gypCjW9B2UwdLwZtJ6tPcoYY"
