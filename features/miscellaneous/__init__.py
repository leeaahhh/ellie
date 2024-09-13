from typing import TYPE_CHECKING

from .miscellaneous import Miscellaneous

if TYPE_CHECKING:
    from tools.rei import rei


async def setup(bot: "rei"):
    await bot.add_cog(Miscellaneous(bot))
