from typing import TYPE_CHECKING

from .miscellaneous import Miscellaneous

if TYPE_CHECKING:
    from tools.shiro import shiro


async def setup(bot: "shiro"):
    await bot.add_cog(Miscellaneous(bot))
