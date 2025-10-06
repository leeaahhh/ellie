from typing import TYPE_CHECKING

from .fun import Fun

if TYPE_CHECKING:
    from tools.ellie import ellie


async def setup(bot: "ellie"):
    await bot.add_cog(Fun(bot))
