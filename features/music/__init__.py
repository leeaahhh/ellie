from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools.ellie import ellie


async def setup(bot: "ellie"):
    from .cog import Music

    await bot.add_cog(Music(bot))
