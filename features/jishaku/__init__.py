from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools import shiro


async def setup(bot: "shiro"):
    from .jishaku import Jishaku

    await bot.add_cog(Jishaku(bot=bot))
