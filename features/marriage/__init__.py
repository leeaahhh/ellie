from typing import TYPE_CHECKING

from .marriage import Marriage

if TYPE_CHECKING:
    from tools.rei import rei


async def setup(bot: "rei"):
    await bot.add_cog(Marriage(bot))
