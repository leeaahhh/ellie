from typing import TYPE_CHECKING

from .developer import Developer

if TYPE_CHECKING:
    from tools.ellie import ellie


async def setup(bot: "ellie"):
    await bot.add_cog(Developer(bot))
