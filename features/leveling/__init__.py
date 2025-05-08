from .leveling import Leveling

async def setup(bot):
    await bot.add_cog(Leveling(bot)) 