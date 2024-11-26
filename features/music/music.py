import wavelink
from discord import app_commands
from discord.ext import commands
import config


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.loop.create_task(self.connect_nodes())

    async def connect_nodes(self):
        """Connect to Lavalink nodes when the bot starts"""
        await self.bot.wait_until_ready()
        node = wavelink.Node(
            uri=f'http://{config.Authorization.Lavalink.host}:{config.Authorization.Lavalink.port}',
            password=config.Authorization.Lavalink.password
        )
        await wavelink.Pool.connect(nodes=[node], client=self.bot)

    @app_commands.command(name="play", description="Play a song")
    async def play(self, interaction: commands.Context, *, query: str):
        if not interaction.user.voice:
            return await interaction.response.send_message("You must be in a voice channel!", ephemeral=True)

        if not interaction.guild.voice_client:
            vc: wavelink.Player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
        else:
            vc: wavelink.Player = interaction.guild.voice_client

        # Search for the track
        search = await wavelink.Playable.search(query)
        if not search:
            return await interaction.response.send_message("No tracks found!", ephemeral=True)

        track = search[0]
        await vc.play(track)
        await interaction.response.send_message(f"Now playing: **{track.title}**")

    @app_commands.command(name="stop", description="Stop the current song")
    async def stop(self, interaction: commands.Context):
        if not interaction.guild.voice_client:
            return await interaction.response.send_message("I'm not playing anything!", ephemeral=True)

        vc: wavelink.Player = interaction.guild.voice_client
        await vc.stop()
        await interaction.response.send_message("Stopped the current song")

    @app_commands.command(name="skip", description="Skip the current song")
    async def skip(self, interaction: commands.Context):
        if not interaction.guild.voice_client:
            return await interaction.response.send_message("I'm not playing anything!", ephemeral=True)

        vc: wavelink.Player = interaction.guild.voice_client
        await vc.stop()
        await interaction.response.send_message("Skipped the current song")

    @app_commands.command(name="disconnect", description="Disconnect the bot from voice")
    async def disconnect(self, interaction: commands.Context):
        if not interaction.guild.voice_client:
            return await interaction.response.send_message("I'm not in a voice channel!", ephemeral=True)

        vc: wavelink.Player = interaction.guild.voice_client
        await vc.disconnect()
        await interaction.response.send_message("Disconnected from voice channel")
