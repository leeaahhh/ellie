from typing import TYPE_CHECKING

from .developer import Developer

if TYPE_CHECKING:
    from tools.rei import rei


async def setup(bot: "rei"):
    await bot.add_cog(Developer(bot))
