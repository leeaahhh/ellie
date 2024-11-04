from typing import TYPE_CHECKING

from .webserver import Webserver
from aiohttp.web import Application, json_response, Request, Response

if TYPE_CHECKING:
    from tools.rei import rei

def route(pattern: str, *, method: str = "GET"):
    """Decorator to register a route handler."""
    def decorator(func):
        func.pattern = pattern
        func.method = method
        return func
    return decorator

async def setup(bot: "rei"):
    await bot.add_cog(Webserver(bot))
