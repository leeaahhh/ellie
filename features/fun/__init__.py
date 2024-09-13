from typing import TYPE_CHECKING

from .fun import Fun

if TYPE_CHECKING:
    from tools.rei import rei


async def setup(bot: "rei"):
    await bot.add_cog(Fun(bot))
