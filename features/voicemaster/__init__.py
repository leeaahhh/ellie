async def setup(bot):
    from .voicemaster import VoiceMaster

    await bot.add_cog(VoiceMaster(bot))
