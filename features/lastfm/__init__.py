from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools import shiro


async def setup(bot: "shiro"):
    from .lastfm import lastfm

    await bot.add_cog(lastfm(bot))
