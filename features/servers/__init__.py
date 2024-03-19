from typing import TYPE_CHECKING

from .servers import Servers

if TYPE_CHECKING:
    from tools.shiro import shiro


async def setup(bot: "shiro"):
    await bot.add_cog(Servers(bot))
