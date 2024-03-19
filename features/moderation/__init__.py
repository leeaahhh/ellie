from typing import TYPE_CHECKING

from .moderation import Moderation

if TYPE_CHECKING:
    from tools.shiro import shiro


async def setup(bot: "shiro"):
    await bot.add_cog(Moderation(bot))
