from typing import TYPE_CHECKING

from .roleplay import Roleplay

if TYPE_CHECKING:
    from tools.ellie import ellie


async def setup(bot: "ellie"):
    await bot.add_cog(Roleplay(bot))

