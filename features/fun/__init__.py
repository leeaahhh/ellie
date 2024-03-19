from typing import TYPE_CHECKING

from .fun import Fun

if TYPE_CHECKING:
    from tools.shiro import shiro


async def setup(bot: "shiro"):
    await bot.add_cog(Fun(bot))
