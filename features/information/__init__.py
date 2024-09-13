from typing import TYPE_CHECKING

from .information import Information

if TYPE_CHECKING:
    from tools.rei import rei


async def setup(bot: "rei"):
    await bot.add_cog(Information(bot))
