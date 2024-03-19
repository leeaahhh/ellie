import random
from contextlib import suppress
from typing import Literal

from discord import Embed, HTTPException, Member, VoiceState
from discord.ext.commands import CommandError, command
from pomice import NodePool, Playlist, Track

import config
from tools.managers.cog import Cog
from tools.managers.context import Context
from tools.managers.regex import TIME_HHMMSS, TIME_HUMAN, TIME_OFFSET, TIME_SS
from tools.services.spotify import song
from tools.shiro import shiro
from tools.utilities.text import Plural

from .player import Player


class Music(Cog):
    def __init__(self, bot: shiro):
        self.bot: shiro = bot
        self.bot.loop.create_task(self.authenticate_node())

    async def authenticate_node(self):
        if not hasattr(self.bot, "node"):
            try:
                self.bot.node = await NodePool().create_node(
                    bot=self.bot,
                    host=config.Lavalink.host,
                    port=config.Lavalink.port,
                    password=config.Lavalink.password,
                    secure=config.Lavalink.secure,
                    spotify_client_id=config.Authorization.Spotify.client_id,
                    spotify_client_secret=config.Authorization.Spotify.client_secret,
                    apple_music=True,
                    identifier=f"shiro-{random.randint(1, 1000)}",
                )
            except Exception as e:
                raise e

    @Cog.listener()
    async def on_pomice_track_end(self, player: Player, track: Track, reason: str):
        await player.next_track()

    @Cog.listener()
    async def on_voice_state_update(
        self,
        member: Member,
        before: VoiceState,
        after: VoiceState,
    ):
        if member.id != self.bot.user.id:
            return

        if (
            not hasattr(self.bot, "node")
            or (player := self.bot.node.get_player(member.guild.id)) is None
        ):
            return

        if not after.channel:
            await player.destroy()

    async def get_player(self, ctx: Context, *, connect: bool = True):
        if not hasattr(self.bot, "node"):
            raise CommandError("The **Lavalink** node hasn't been **initialized** yet")

        if not ctx.author.voice:
            raise CommandError("You're not **connected** to a voice channel")

        if (
            ctx.guild.me.voice
            and ctx.guild.me.voice.channel != ctx.author.voice.channel
        ):
            raise CommandError("I'm **already** connected to another voice channel")

        if (
            player := self.bot.node.get_player(ctx.guild.id)
        ) is None or not ctx.guild.me.voice:
            if not connect:
                raise CommandError("I'm not **connected** to a voice channel")
            await ctx.author.voice.channel.connect(cls=Player, self_deaf=True)
            player = self.bot.node.get_player(ctx.guild.id)
            player.bound_channel = ctx.channel
            await player.set_volume(65)

        return player

    @command(
        name="play",
        usage="(query)",
        example="Penthouse Shordy",
        parameters={
            "bump": {
                "require_value": False,
                "description": "Bump the track to the front of the queue",
                "aliases": ["b", "next"],
            }
        },
        aliases=["p"],
    )
    async def play(self: "Music", ctx: Context, *, query: str):
        """Queue a track."""
        if not query:
            raise CommandError("Please **provide** a query")

        player: Player = await self.get_player(ctx, connect=True)

        try:
            result: list[Track] | Playlist = await player.get_tracks(
                query=query, ctx=ctx
            )
        except Exception:
            return await ctx.error("No **results** were found")

        if not result:
            return await ctx.error("No **results** were found")

        if isinstance(result, Playlist):
            for track in result.tracks:
                await player.insert(
                    track, filter=False, bump=ctx.parameters.get("bump")
                )

            return await ctx.neutral(
                f"Added **{Plural(result.track_count):track}** from [**{result.name}**]({result.uri}) to the queue",
            )

        await player.insert(result[0], bump=ctx.parameters.get("bump"))
        if player.is_playing:
            return await ctx.neutral(
                f"Added [**{result[0].title}**]({result[0].uri}) to the queue"
            )

        if not player.is_playing:
            await player.next_track()

        if bound_channel := player.bound_channel:
            if bound_channel != ctx.channel:
                with suppress(HTTPException):
                    await ctx.react_check()

    @command(
        name="move",
        usage="(from) (to)",
        example="6 2",
        aliases=["mv"],
    )
    async def move(self, ctx: Context, track: int, to: int):
        """Move a track to a different position"""
        player: Player = await self.get_player(ctx, connect=False)
        queue = player.queue._queue

        if track == to:
            return await ctx.error(f"Track position `{track}` is invalid")
        try:
            queue[track - 1]
            queue[to - 1]
        except IndexError:
            return await ctx.error(
                f"Track position `{track}` is invalid (`1`/`{len(queue)}`)"
            )

        _track = queue[track - 1]
        del queue[track - 1]
        queue.insert(to - 1, _track)
        await ctx.approve(
            f"Moved [**{_track.title}**]({_track.uri}) to position `{to}`"
        )

    @command(
        name="remove",
        usage="(index)",
        example="3",
        aliases=["rmv"],
    )
    async def remove(self, ctx: Context, track: int):
        """Remove a track from the queue"""
        player: Player = await self.get_player(ctx, connect=False)
        queue = player.queue._queue

        if track < 1 or track > len(queue):
            return await ctx.error(
                f"Track position `{track}` is invalid (`1`/`{len(queue)}`)"
            )

        _track = queue[track - 1]
        del queue[track - 1]
        await ctx.approve(f"Removed [**{_track.title}**]({_track.uri}) from the queue")

    @command(
        name="shuffle",
        aliases=["mix"],
    )
    async def shuffle(self, ctx: Context):
        """Shuffle the queue"""
        player: Player = await self.get_player(ctx, connect=False)

        if queue := player.queue._queue:
            random.shuffle(queue)
            await ctx.message.add_reaction("🔀")
        else:
            await ctx.error("There aren't any **tracks** in the queue")

    @command(name="skip", aliases=["next", "sk"])
    async def skip(self, ctx: Context):
        """Skip the current track"""
        player: Player = await self.get_player(ctx, connect=False)

        if player.is_playing:
            await ctx.message.add_reaction("⏭️")
            await player.skip()
        else:
            await ctx.error("There isn't an active **track**")

    @command(
        name="loop",
        usage="(track, queue, or off)",
        example="queue",
        aliases=["repeat", "lp"],
    )
    async def loop(self, ctx: Context, option: Literal["track", "queue", "off"]):
        """Toggle looping for the current track or queue"""
        player: Player = await self.get_player(ctx, connect=False)

        if option == "off":
            if not player.loop:
                return await ctx.error("There isn't an active **loop**")
        elif option == "track":
            if not player.is_playing:
                return await ctx.error("There isn't an active **track**")
        elif option == "queue":
            if not player.queue._queue:
                return await ctx.error("There aren't any **tracks** in the queue")

        await ctx.message.add_reaction(
            "✅" if option == "off" else "🔂" if option == "track" else "🔁"
        )
        await player.set_loop(option if option != "off" else False)

    @command(name="pause")
    async def pause(self, ctx: Context):
        """Pause the current track"""
        player: Player = await self.get_player(ctx, connect=False)

        if player.is_playing and not player.is_paused:
            await ctx.message.add_reaction("⏸️")
            await player.set_pause(True)
        else:
            await ctx.error("There isn't an active **track**")

    @command(name="resume", aliases=["rsm"])
    async def resume(self, ctx: Context):
        """Resume the current track"""
        player: Player = await self.get_player(ctx, connect=False)

        if player.is_playing and player.is_paused:
            await ctx.message.add_reaction("✅")
            await player.set_pause(False)
        else:
            await ctx.error("There isn't an active **track**")

    @command(
        name="seek",
        usage="(position)",
        example="+30s",
        aliases=["ff", "rw"],
    )
    async def seek(self, ctx: Context, position: str):
        """Seek to a specified position"""
        player: Player = await self.get_player(ctx, connect=False)

        if not player.is_playing:
            return await ctx.error("There isn't an active **track**")

        if ctx.invoked_with == "ff" and not position.startswith("+"):
            position = f"+{position}"
        elif ctx.invoked_with == "rw" and not position.startswith("-"):
            position = f"-{position}"

        milliseconds = 0
        if match := TIME_HHMMSS.fullmatch(position):
            milliseconds += int(match.group("h")) * 3600000
            milliseconds += int(match.group("m")) * 60000
            milliseconds += int(match.group("s")) * 1000
            new_position = milliseconds
        elif match := TIME_SS.fullmatch(position):
            milliseconds += int(match.group("m")) * 60000
            milliseconds += int(match.group("s")) * 1000
            new_position = milliseconds
        elif match := TIME_OFFSET.fullmatch(position):
            milliseconds += int(match.group("s")) * 1000
            position = player.position
            new_position = position + milliseconds
        elif match := TIME_HUMAN.fullmatch(position):
            if m := match.group("m"):
                if match.group("s") and position.lower().endswith("m"):
                    return await ctx.error(f"Position `{position}` is invalid")
                milliseconds += int(m) * 60000
            if s := match.group("s"):
                if position.lower().endswith("m"):
                    milliseconds += int(s) * 60000
                else:
                    milliseconds += int(s) * 1000
            new_position = milliseconds
        else:
            return await ctx.error(f"Position `{position}` is invalid")

        new_position = max(0, min(new_position, player.current.length))
        await player.seek(new_position)
        await ctx.message.add_reaction("✅")

    @command(
        name="volume",
        usage="<percentage>",
        example="75",
        aliases=["vol", "v"],
    )
    async def volume(self, ctx: Context, percentage: int = None):
        """Set the player volume"""
        player: Player = await self.get_player(ctx, connect=False)

        if percentage is None:
            return await ctx.neutral(f"Current volume: `{player.volume}%`")

        if not 0 <= percentage <= 100:
            return await ctx.error("Please **provide** a **valid** percentage")

        await player.set_volume(percentage)
        await ctx.approve(f"Set **volume** to `{percentage}%`")

    @command(name="disconnect", aliases=["dc", "stop"])
    async def disconnect(self, ctx: Context):
        """Disconnect the music player"""
        player: Player = await self.get_player(ctx, connect=False)

        await player.teardown()
        await ctx.message.add_reaction("👋🏾")

    @command(
        name="queue",
        aliases=["q", "list"],
    )
    async def queue(self, ctx: Context):
        """View the current queue"""
        player: Player = await self.get_player(ctx, connect=False)
        queue = player.queue._queue
        tracks = []
        if not queue:
            return await ctx.error("There aren't any **tracks** in the queue")

        for track in queue:
            tracks.append(f"`{queue.index(track) + 1}.` [{track.title}]({track.uri})")

        embeds = []
        for i in range(0, len(tracks), 10):
            embed = Embed(
                title=f"Queue for {ctx.guild.name}",
                description="\n".join(tracks[i : i + 10]),
                color=config.Color.neutral,
            )
            embed.set_author(
                name=ctx.author.name, icon_url=ctx.author.display_avatar.url
            )
            embeds.append(embed)

        await ctx.paginate(embeds)

    @command(
        name="spotify",
        usage="(query)",
        example="Penthouse Shordy",
        aliases=["sp"],
    )
    async def spotify(self, ctx: Context, *, query: str):
        """Search for a song on Spotify"""
        try:
            song_url = await song(
                query
            )  # url='https://open.spotify.com/track/6vOedMRRZuckfMknIswvLv'
        except ValueError:
            return await ctx.error("No **results** were found")

        await ctx.reply(song_url.url)
