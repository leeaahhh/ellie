import asyncio

import aiohttp_cors
from aiohttp.web import Application, Request, Response, _run_app, json_response
from discord.ext.commands import Cog, Group
from orjson import dumps

from tools.managers.regex import DISCORD_ID
from tools.shiro import shiro


class Webserver(Cog):
    def __init__(self: "Webserver", bot: shiro):
        self.bot: shiro = bot

        self.app = Application()
        self.app.router.add_get("/", self.index)
        self.app.router.add_get("/names/{user_id}", self.names)
        self.app.router.add_get("/commands", self.commands)
        self.cors = aiohttp_cors.setup(
            self.app,
            defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                )
            },
        )
        self.loop = asyncio.get_event_loop()

        for route in list(self.app.router.routes()):
            self.cors.add(route)

    async def cog_load(self: "Webserver"):
        self.loop.create_task(
            _run_app(
                self.app,
                host="0.0.0.0",
                port=59076,
                access_log=None,
                print=None,
            )
        )

    async def cog_unload(self: "Webserver"):
        await self.app.shutdown()
        await self.app.cleanup()

    async def names(self: "Webserver", request: Request) -> Response:
        if not DISCORD_ID.match(str(request.match_info["user_id"])):
            return json_response({"error": "Invalid user ID"}, status=400)

        names = await self.bot.db.fetch(
            "SELECT name, timestamp FROM metrics.names WHERE user_id = $1 ORDER BY timestamp DESC",
            int(request.match_info["user_id"]),
        )
        if not names:
            return json_response({"error": "User not found"}, status=404)

        return json_response(
            {
                "user_id": int(request.match_info["user_id"]),
                "names": [name["name"] for name in names],
                "user": {
                    "name": user.name,
                    "avatar": user.display_avatar.url,
                }
                if (user := self.bot.get_user(int(request.match_info["user_id"])))
                else {
                    "name": "Unknown User",
                    "avatar": self.bot.user.display_avatar.url,
                },
            },
            dumps=lambda x: dumps(x, option=2).decode(),
        )

    def walk_commands(self: "Webserver") -> list:
        for command in self.bot.walk_commands():
            if (
                (cog := command.cog_name)
                and cog.lower() in ("jishaku", "developer", "webserver")
                or command.hidden
            ):
                continue

            yield command

    async def commands(self: "Webserver", request: Request) -> Response:
        output = "\n"

        for name, cog in sorted(self.bot.cogs.items(), key=lambda c: c[0].lower()):
            if name.lower() in ("jishaku", "developer", "webserver"):
                continue

            _commands = []
            for command in cog.walk_commands():
                if command.hidden:
                    continue

                usage = f" {command.usage}" if command.usage else ""
                aliases = (
                    "[" + "|".join(command.aliases) + "]" if command.aliases else ""
                )
                if isinstance(command, Group) and not command.root_parent:
                    _commands.append(
                        f"|    ├── {command.name}{aliases}: {command.short_doc or 'No description'}"
                    )
                elif not isinstance(command, Group) and command.root_parent:
                    _commands.append(
                        f"|    |   ├── {command.qualified_name}{aliases}{usage}: {command.short_doc or 'No description'}"
                    )
                elif isinstance(command, Group):
                    _commands.append(
                        f"|    |   ├── {command.qualified_name}{aliases}: {command.short_doc or 'No description'}"
                    )
                else:
                    _commands.append(
                        f"|    ├── {command.qualified_name}{aliases}{usage}: {command.short_doc or 'No description'}"
                    )

            if _commands:
                output += f"┌── {name}\n" + "\n".join(_commands) + "\n"

        return json_response(
            {
                "bot": {
                    "name": self.bot.user.name,
                    "avatar": self.bot.user.display_avatar.url,
                },
                "commands": output,
            },
            dumps=lambda x: dumps(x, option=2).decode(),
        )

    async def index(self: "Webserver", request: Request) -> Response:
        return json_response(
            {
                "bot": {
                    "name": self.bot.user.name,
                    "avatar": self.bot.user.display_avatar.url,
                },
                "commands": f"{request.url}commands",
                "names": f"{request.url}names/<user_id>",
            },
            dumps=lambda x: dumps(x, option=3).decode(),
        )
