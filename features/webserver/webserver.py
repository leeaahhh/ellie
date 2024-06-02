from datetime import datetime
from functools import wraps
from typing import Callable, Dict, List

from aiohttp.abc import AbstractAccessLogger
from aiohttp.web import (Application, BaseRequest, Request, Response,
                         StreamResponse)
from aiohttp.web import _run_app as web
from aiohttp.web import json_response
from discord.ext.commands import Cog

import config
from tools.managers import logging
from tools.shiro import shiro

log = logging.getLogger(__name__)


class AccessLogger(AbstractAccessLogger):
    def log(
        self: "AccessLogger",
        request: BaseRequest,
        response: StreamResponse,
        time: float,
    ) -> None:
        self.logger.info(
            f"Request for {request.path!r} with status of {response.status!r}. (Took {time * 1000:.2f}ms.)"
        )


def route(pattern: str, method: str = "GET") -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self: "Webserver", request: Request) -> None:
            return await func(self, request)

        wrapper.pattern = pattern
        wrapper.method = method
        return wrapper

    return decorator


class Webserver(Cog):
    def __init__(self, bot: shiro):
        self.bot: shiro = bot
        self.app = Application(
            logger=log,
        )
        self.app.router.add_get(
            "/",
            lambda _: json_response(
                {
                    "commands": self.bot.command_count,
                    "latency": self.bot.latency * 1000,
                    "cache": {
                        "guilds": len(self.bot.guilds),
                        "users": len(self.bot.users),
                    },
                }
            ),
        )
        for module in dir(self):
            route = getattr(self, module)
            if not hasattr(route, "pattern"):
                continue

            self.app.router.add_route(route.method, route.pattern, route)
            log.info(f"Added route for {route.pattern!r} ({route.method}).")

    async def cog_load(self: "Webserver") -> None:
        host = config.Webserver.host
        port = config.Webserver.port

        self.bot.loop.create_task(
            web(
                self.app,
                host=host,
                port=port,
                print=None,
                access_log=log,
                access_log_class=AccessLogger,
            ),
            name="Internal-API",
        )
        log.info(f"Started the internal API on {host}:{port}.")

    async def cog_unload(self: "Webserver") -> None:
        await self.app.shutdown()
        await self.app.cleanup()

        log.info("Gracefully shutdown the API")

    @route("/avatars/{user_id}")
    async def avatars(self: "Webserver", request: Request) -> Response:
        """
        Selects avatars from the database for /history endpoint.
        """

        try:
            user_id = int(request.match_info["user_id"])
        except ValueError:
            return json_response({"error": "Invalid user ID."}, status=400)

        user = self.bot.get_user(user_id)
        avatars: List[Dict[str, str | datetime]] = await self.bot.db.fetch(
            """
            SELECT asset, updated_at
            FROM metrics.avatars
            WHERE user_id = $1
            ORDER BY updated_at DESC
            """,
            user_id,
        )

        return json_response(
            {
                "user": {
                    "id": user_id,
                    "name": user.name,
                    "avatar": user.display_avatar.url,
                }
                if user
                else None,
                "avatars": [
                    {
                        "asset": avatar["asset"],
                        "updated_at": avatar["updated_at"].timestamp(),
                    }
                    for avatar in avatars
                ],
            }
        )
