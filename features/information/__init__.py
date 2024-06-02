from typing import TYPE_CHECKING

from .information import Information

if TYPE_CHECKING:
    from tools.shiro import shiro


async def setup(bot: "shiro"):
    await bot.add_cog(Information(bot))
