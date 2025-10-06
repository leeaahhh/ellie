from typing import TYPE_CHECKING

from .moderation import Moderation

if TYPE_CHECKING:
    from tools.ellie import ellie


async def setup(bot: "ellie"):
    await bot.add_cog(Moderation(bot))
