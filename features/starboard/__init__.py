from typing import TYPE_CHECKING

from .starboard import Starboard

if TYPE_CHECKING:
    from tools.rei import rei


async def setup(bot: "rei"):
    await bot.add_cog(Starboard(bot))
