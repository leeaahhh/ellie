from typing import TYPE_CHECKING

from .moderation import Moderation

if TYPE_CHECKING:
    from tools.rei import rei


async def setup(bot: "rei"):
    await bot.add_cog(Moderation(bot))
