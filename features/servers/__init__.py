from typing import TYPE_CHECKING

from .servers import Servers

if TYPE_CHECKING:
    from tools.ellie import ellie


async def setup(bot: "ellie"):
    await bot.add_cog(Servers(bot))
