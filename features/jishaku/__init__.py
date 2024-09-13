from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools import rei


async def setup(bot: "rei"):
    from .jishaku import Jishaku

    await bot.add_cog(Jishaku(bot=bot))
