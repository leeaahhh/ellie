from typing import TYPE_CHECKING

from .webserver import Webserver

if TYPE_CHECKING:
    from tools.shiro import shiro


async def setup(bot: "shiro"):
    await bot.add_cog(Webserver(bot))
