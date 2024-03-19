from typing import TYPE_CHECKING

from .music import Music

if TYPE_CHECKING:
    from tools.shiro import shiro


async def setup(bot: "shiro"):
    await bot.add_cog(Music(bot))
