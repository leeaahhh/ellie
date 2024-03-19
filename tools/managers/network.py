from typing import Any

import aiohttp
from aiohttp import ClientSession as Session
from aiohttp import ClientTimeout
from bs4 import BeautifulSoup
from discord.ext.commands import CommandError
from munch import DefaultMunch
from yarl import URL


class ClientSession(Session):
    def __init__(self: "ClientSession", *args, **kwargs):
        super().__init__(timeout=ClientTimeout(total=15), raise_for_status=True)

    async def request(self: "ClientSession", *args, **kwargs) -> Any:
        args = list(args)
        args[1] = URL(args[1])
        raise_for = kwargs.pop("raise_for", {})
        raw = kwargs.pop("raw", False)

        args = tuple(args)

        try:
            response = await super().request(*args, **kwargs)
        except aiohttp.ClientResponseError as e:
            if error_message := raise_for.get(e.status):
                raise CommandError(error_message) from e

            raise

        if raw:
            return response

        if response.content_type == "text/html":
            return BeautifulSoup(await response.text(), "html.parser")

        if response.content_type.startswith(("image/", "video/", "audio/")):
            return await response.read()

        if response.content_type in ("application/json", "text/javascript"):
            data: dict = await response.json(content_type=response.content_type)
            return DefaultMunch.fromDict(data)
        return response
