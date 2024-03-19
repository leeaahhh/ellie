from typing import TYPE_CHECKING

from .starboard import Starboard

if TYPE_CHECKING:
    from tools.shiro import shiro


async def setup(bot: "shiro"):
    await bot.add_cog(Starboard(bot))
