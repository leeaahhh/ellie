from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools import ellie


async def setup(bot: "ellie"):
    from .jishaku import Jishaku

    await bot.add_cog(Jishaku(bot=bot))
