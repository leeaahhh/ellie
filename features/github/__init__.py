from typing import TYPE_CHECKING

from .github import GitHub

if TYPE_CHECKING:
    from tools.rei import rei


async def setup(bot: "rei"):
    await bot.add_cog(GitHub(bot))
