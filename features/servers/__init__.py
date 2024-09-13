from typing import TYPE_CHECKING

from .servers import Servers

if TYPE_CHECKING:
    from tools.rei import rei


async def setup(bot: "rei"):
    await bot.add_cog(Servers(bot))
