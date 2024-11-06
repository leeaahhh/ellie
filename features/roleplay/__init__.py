from typing import TYPE_CHECKING

from .roleplay import Roleplay

if TYPE_CHECKING:
    from tools.rei import rei


async def setup(bot: "rei"):
    await bot.add_cog(Roleplay(bot))

