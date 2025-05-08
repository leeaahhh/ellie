from .ai import AI

__all__ = ['AI']

async def setup(bot):
    from .ai import AI
    await bot.add_cog(AI(bot)) 