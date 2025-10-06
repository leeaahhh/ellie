from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools import ellie


async def setup(bot: "ellie"):
    from .lastfm import lastfm

    await bot.add_cog(lastfm(bot))
