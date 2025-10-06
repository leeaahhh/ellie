from typing import TYPE_CHECKING

from .github import GitHub

if TYPE_CHECKING:
    from tools.ellie import ellie


async def setup(bot: "ellie"):
    await bot.add_cog(GitHub(bot))
