from typing import TYPE_CHECKING

from .marriage import Marriage

if TYPE_CHECKING:
    from tools.ellie import ellie


async def setup(bot: "ellie"):
    await bot.add_cog(Marriage(bot))
