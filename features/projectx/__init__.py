from typing import TYPE_CHECKING

from .projectx import ProjectX

if TYPE_CHECKING:
    from tools.rei import rei


async def setup(bot: "rei"):
    await bot.add_cog(ProjectX(bot))

