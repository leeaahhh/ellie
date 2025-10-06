from typing import TYPE_CHECKING

from .miscellaneous import Miscellaneous

if TYPE_CHECKING:
    from tools.ellie import ellie


async def setup(bot: "ellie"):
    await bot.add_cog(Miscellaneous(bot))
