from typing import TYPE_CHECKING

from .starboard import Starboard

if TYPE_CHECKING:
    from tools.ellie import ellie


async def setup(bot: "ellie"):
    await bot.add_cog(Starboard(bot))
