from typing import TYPE_CHECKING

from .information import Information

if TYPE_CHECKING:
    from tools.ellie import ellie


async def setup(bot: "ellie"):
    await bot.add_cog(Information(bot))
