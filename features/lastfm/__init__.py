from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools import rei


async def setup(bot: "rei"):
    from .lastfm import lastfm

    await bot.add_cog(lastfm(bot))
