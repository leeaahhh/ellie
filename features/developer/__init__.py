from typing import TYPE_CHECKING

from .developer import Developer

if TYPE_CHECKING:
    from tools.shiro import shiro


async def setup(bot: "shiro"):
    await bot.add_cog(Developer(bot))
