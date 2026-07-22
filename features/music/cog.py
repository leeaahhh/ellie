from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Optional

import discord
import wavelink
from discord.ext.commands import BucketType, cooldown, hybrid_command

import config
from tools.managers.cog import Cog
from tools.managers.context import Context

from .dispatcher import Dispatcher
from .embeds import EmbedBuilder
from .player import Player
from .queue_manager import QueueManager
from .spotify import SpotifyClient, SpotifyError
from .track import Track
from .youtube import (
    parse_query,
    resolve_spotify_to_youtube,
    search_youtube,
)

if TYPE_CHECKING:
    from tools.ellie import ellie

log = logging.getLogger(__name__)


class Music(Cog):
    """Slash-command music player backed by Lavalink."""

    def __init__(self, bot: "ellie"):
        self.bot = bot
        self.spotify = SpotifyClient(bot)
        self.queue_manager = QueueManager()
        self._node_ready = asyncio.Event()

    # -- lifecycle --------------------------------------------------------------

    async def cog_load(self) -> None:
        """Connect to the Lavalink node(s)."""
        nodes = [
            wavelink.Node(
                uri=f"{'https' if config.Authorization.Lavalink.secure else 'http'}://{config.Authorization.Lavalink.host}:{config.Authorization.Lavalink.port}",
                password=config.Authorization.Lavalink.password,
            )
        ]
        try:
            await wavelink.Pool.connect(nodes=nodes, client=self.bot)
            log.info("Connected to Lavalink node(s).")
        except Exception:
            log.exception("Failed to connect to Lavalink.")

    async def cog_unload(self) -> None:
        """Disconnect all players and close node connections."""
        for dispatcher in list(self.queue_manager._dispatchers.values()):
            try:
                await dispatcher.teardown()
            except Exception:
                pass
        self.queue_manager.clear()
        await wavelink.Pool.close()

    # -- helpers ----------------------------------------------------------------

    def _get_dispatcher(self, guild_id: int) -> Optional[Dispatcher]:
        """Get the Dispatcher for a guild, if one exists."""
        return self.queue_manager.get(guild_id)

    async def _get_available_node(self) -> Optional[wavelink.Node]:
        """Get an available Lavalink node, or None."""
        try:
            return wavelink.Pool.get_node()
        except Exception:
            return None

    async def _ensure_voice(self, ctx: Context) -> Optional[Dispatcher]:
        """Join the author's voice channel and return a Dispatcher.

        Retries the voice connection up to 3 times on timeout, with a 2 s gap
        between attempts.
        """
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.error("You're not connected to a **voice channel**")
            return None

        # Return existing dispatcher if we're already in this guild
        dispatcher = self._get_dispatcher(ctx.guild.id)
        if dispatcher is not None:
            if dispatcher.channel and dispatcher.channel.id != ctx.author.voice.channel.id:
                await ctx.error("I'm already in a different **voice channel**")
                return None
            # Update home channel if the command came from a different text channel
            if dispatcher.home_channel_id != ctx.channel.id:
                dispatcher.home_channel_id = ctx.channel.id
            return dispatcher

        # --- Node readiness check ---
        node = await self._get_available_node()
        if node is None:
            await ctx.error("No **music node** is available right now")
            return None

        if node.status != wavelink.NodeStatus.CONNECTED:
            await ctx.load("Waiting for the **music node** to be ready...")
            try:
                await asyncio.wait_for(self._node_ready.wait(), timeout=15)
            except asyncio.TimeoutError:
                await ctx.error(
                    "The **music node** isn't ready yet — please try again in a moment."
                )
                return None

        # --- Join voice (with retry) ---
        player: Optional[wavelink.Player] = None
        for attempt in range(3):
            try:
                player = await ctx.author.voice.channel.connect(
                    cls=Player,
                    self_deaf=True,
                    timeout=60,
                )
                break
            except asyncio.TimeoutError:
                if attempt < 2:
                    log.warning(
                        "Voice connect attempt %d failed for guild %d, retrying...",
                        attempt + 1,
                        ctx.guild.id,
                    )
                    await asyncio.sleep(2)
                    continue
                log.exception(
                    "All voice connect attempts failed for guild %d", ctx.guild.id
                )
                await ctx.error(
                    "Voice connection timed out after 3 attempts. "
                    "The **Lavalink node** may not be able to reach Discord's "
                    "voice servers — check that UDP egress is allowed from the "
                    "Lavalink container."
                )
                return None
            except discord.ClientException:
                await ctx.error("I was unable to join that **voice channel**")
                return None

        if player is None:
            await ctx.error("Failed to establish a voice connection")
            return None

        # --- Create dispatcher ---
        dispatcher = Dispatcher(
            guild_id=ctx.guild.id,
            bot=self.bot,
            player=player,
            home_channel_id=ctx.channel.id,
        )
        self.queue_manager.set(dispatcher)

        return dispatcher

    # -- event listeners --------------------------------------------------------

    @Cog.listener()
    async def on_wavelink_node_ready(
        self, payload: wavelink.NodeReadyEventPayload
    ) -> None:
        log.info(
            "Lavalink node %r ready (resumed: %s).",
            payload.node,
            payload.resumed,
        )
        self._node_ready.set()

    @Cog.listener()
    async def on_wavelink_node_closed(
        self, node: wavelink.Node, disconnected: list[wavelink.Player]
    ) -> None:
        log.warning("Lavalink node %r closed — clearing ready flag.", node)
        self._node_ready.clear()

    @Cog.listener()
    async def on_wavelink_track_start(
        self, payload: wavelink.TrackStartEventPayload
    ) -> None:
        player = payload.player
        if player is None or player.guild is None:
            return
        dispatcher = self._get_dispatcher(player.guild.id)
        if dispatcher is None:
            return
        await dispatcher.on_track_start()

    @Cog.listener()
    async def on_wavelink_track_end(
        self, payload: wavelink.TrackEndEventPayload
    ) -> None:
        player = payload.player
        if player is None or player.guild is None:
            return
        dispatcher = self._get_dispatcher(player.guild.id)
        if dispatcher is None:
            return
        await dispatcher.on_track_end(payload.reason)

    @Cog.listener()
    async def on_wavelink_track_exception(
        self, payload: wavelink.TrackExceptionEventPayload
    ) -> None:
        player = payload.player
        if player is None or player.guild is None:
            return
        dispatcher = self._get_dispatcher(player.guild.id)
        if dispatcher is None:
            return
        await dispatcher.on_track_exception(str(payload.exception))

    @Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if member.guild is None:
            return

        dispatcher = self._get_dispatcher(member.guild.id)
        if dispatcher is None:
            return

        # Bot was moved to a different channel
        if member.id == self.bot.user.id and after.channel is not None:
            if before.channel is not None and before.channel.id != after.channel.id:
                from .embeds import floor_bitrate
                floor_bitrate(after.channel.bitrate)

        # Someone left the bot's voice channel — check for empty VC
        if before.channel is not None and dispatcher.channel is not None:
            if before.channel.id == dispatcher.channel.id:
                humans = [m for m in dispatcher.channel.members if not m.bot]
                if not humans:
                    dispatcher._start_inactivity_timer(short=True)

    @Cog.listener()
    async def on_wavelink_inactive_player(self, player: wavelink.Player) -> None:
        if player.guild is None:
            return
        dispatcher = self._get_dispatcher(player.guild.id)
        if dispatcher:
            await dispatcher.teardown()
            self.queue_manager.delete(player.guild.id)

    # -- /play ------------------------------------------------------------------

    @hybrid_command(name="play", aliases=["p"])
    async def play(self, ctx: Context, *, query: str) -> None:
        """Play a song from YouTube or Spotify.

        Accepts YouTube search terms, YouTube video/playlist URLs,
        and Spotify track/album/playlist links.
        """
        dispatcher = await self._ensure_voice(ctx)
        if dispatcher is None:
            return

        url_type, url_id = parse_query(query)

        # --- Spotify handling ---
        if url_type and url_type.startswith("spotify_"):
            await self._handle_spotify(ctx, dispatcher, url_type, url_id)
            return

        # --- Direct YouTube URL ---
        if url_type in ("youtube_video", "youtube_playlist"):
            results = await search_youtube(query)
            if results is None:
                await ctx.error("No results found for that URL.")
                return

            if isinstance(results, wavelink.Playlist):
                tracks = [
                    Track.from_youtube(t, requester_id=ctx.author.id)
                    for t in list(results)
                ]
                count = dispatcher.enqueue_many(tracks)
                await ctx.approve(
                    f"Added **{count}** tracks from the playlist to the queue."
                )
            else:
                track = Track.from_youtube(results[0], requester_id=ctx.author.id)
                dispatcher.enqueue(track)
                embed = EmbedBuilder.track_added(
                    dispatcher, track, position=dispatcher.queue_size
                )
                await ctx.send(embed=embed)

            if dispatcher.current is None and dispatcher.queue:
                await dispatcher._play()
            return

        # --- Plain text search ---
        results = await search_youtube(f"ytsearch:{query}")
        if results is None or not results:
            await ctx.error(f"No results found for **{query}**")
            return

        if isinstance(results, wavelink.Playlist):
            first = list(results)[0] if results else None
        else:
            first = results[0] if results else None

        if first is None:
            await ctx.error(f"No results found for **{query}**")
            return

        track = Track.from_youtube(first, requester_id=ctx.author.id)
        dispatcher.enqueue(track)
        embed = EmbedBuilder.track_added(
            dispatcher, track, position=dispatcher.queue_size
        )
        await ctx.send(embed=embed)

        if dispatcher.current is None and dispatcher.queue:
            await dispatcher._play()

    async def _handle_spotify(
        self,
        ctx: Context,
        dispatcher: Dispatcher,
        url_type: str,
        spotify_id: str,
    ) -> None:
        """Resolve a Spotify URL and enqueue the resulting YouTube tracks."""
        try:
            if url_type == "spotify_track":
                meta = await self.spotify.get_track(spotify_id)
                playable = await resolve_spotify_to_youtube(meta)
                if playable is None:
                    await ctx.error(
                        "Could not find a matching YouTube video for that **Spotify track**."
                    )
                    return
                track = Track.from_spotify_meta(
                    playable, meta, requester_id=ctx.author.id
                )
                dispatcher.enqueue(track)
                embed = EmbedBuilder.track_added(
                    dispatcher, track, position=dispatcher.queue_size
                )
                await ctx.send(embed=embed)

            elif url_type == "spotify_album":
                metas = await self.spotify.get_album_tracks(spotify_id)
                if not metas:
                    await ctx.error("That **Spotify album** has no tracks.")
                    return

                await ctx.load(
                    f"Resolving **{len(metas)}** tracks from Spotify album..."
                )

                resolved = 0
                for meta in metas:
                    playable = await resolve_spotify_to_youtube(meta)
                    if playable is not None:
                        track = Track.from_spotify_meta(
                            playable, meta, requester_id=ctx.author.id
                        )
                        dispatcher.enqueue(track)
                        resolved += 1

                if resolved == 0:
                    await ctx.error(
                        "Could not resolve any tracks from that **Spotify album**."
                    )
                else:
                    await ctx.approve(
                        f"Added **{resolved}** / {len(metas)} tracks from the Spotify album to the queue."
                    )

            elif url_type == "spotify_playlist":
                metas = await self.spotify.get_playlist_tracks(spotify_id)
                if not metas:
                    await ctx.error("That **Spotify playlist** has no tracks.")
                    return

                await ctx.load(
                    f"Resolving **{len(metas)}** tracks from Spotify playlist..."
                )

                resolved = 0
                for meta in metas:
                    playable = await resolve_spotify_to_youtube(meta)
                    if playable is not None:
                        track = Track.from_spotify_meta(
                            playable, meta, requester_id=ctx.author.id
                        )
                        dispatcher.enqueue(track)
                        resolved += 1

                if resolved == 0:
                    await ctx.error(
                        "Could not resolve any tracks from that **Spotify playlist**."
                    )
                else:
                    await ctx.approve(
                        f"Added **{resolved}** / {len(metas)} tracks from the Spotify playlist to the queue."
                    )

        except SpotifyError as exc:
            await ctx.error(str(exc))
        except Exception:
            log.exception("Error resolving Spotify URL")
            await ctx.error("An error occurred while fetching Spotify metadata.")

        # Kick off playback
        if dispatcher.current is None and dispatcher.queue:
            await dispatcher._play()

    # -- /pause -----------------------------------------------------------------

    @hybrid_command(name="pause")
    async def pause(self, ctx: Context) -> None:
        """Pause the current track."""
        dispatcher = self._get_dispatcher(ctx.guild.id)
        if dispatcher is None or not dispatcher.playing:
            await ctx.error("Nothing is playing right now.")
            return
        await dispatcher.pause()
        state = "Paused" if dispatcher.paused else "Resumed"
        await ctx.approve(f"{state} playback.")

    # -- /resume ----------------------------------------------------------------

    @hybrid_command(name="resume")
    async def resume(self, ctx: Context) -> None:
        """Resume a paused track."""
        dispatcher = self._get_dispatcher(ctx.guild.id)
        if dispatcher is None:
            await ctx.error("I'm not connected to a voice channel.")
            return
        if dispatcher.paused:
            await dispatcher.pause()
        await ctx.approve("Resumed playback.")

    # -- /skip ------------------------------------------------------------------

    @hybrid_command(name="skip", aliases=["s", "next"])
    @cooldown(2, 5, BucketType.guild)
    async def skip(self, ctx: Context) -> None:
        """Skip the current track."""
        dispatcher = self._get_dispatcher(ctx.guild.id)
        if dispatcher is None or not dispatcher.playing:
            await ctx.error("Nothing is playing right now.")
            return
        await dispatcher.skip()
        await ctx.approve("Skipped the current track.")

    # -- /stop ------------------------------------------------------------------

    @hybrid_command(name="stop", aliases=["disconnect", "dc", "leave"])
    async def stop(self, ctx: Context) -> None:
        """Stop playback and disconnect from the voice channel."""
        dispatcher = self._get_dispatcher(ctx.guild.id)
        if dispatcher is None:
            await ctx.error("I'm not connected to a voice channel.")
            return
        await dispatcher.teardown()
        self.queue_manager.delete(ctx.guild.id)
        await ctx.approve("Disconnected from the voice channel.")

    # -- /queue -----------------------------------------------------------------

    @hybrid_command(name="queue", aliases=["q"])
    async def queue(self, ctx: Context) -> None:
        """Show the current playback queue."""
        dispatcher = self._get_dispatcher(ctx.guild.id)
        if dispatcher is None:
            await ctx.error("I'm not connected to a voice channel.")
            return

        if not dispatcher.queue and dispatcher.current is None:
            await ctx.error("The queue is empty.")
            return

        # Build pages — 10 tracks per page
        tracks_per_page = 10
        pages: list[discord.Embed] = []
        all_tracks = dispatcher.queue

        if not all_tracks and dispatcher.current:
            # Only show now-playing
            embed = EmbedBuilder.now_playing(dispatcher)
            await ctx.send(embed=embed)
            return

        for i in range(0, len(all_tracks), tracks_per_page):
            chunk = all_tracks[i : i + tracks_per_page]
            page_num = (i // tracks_per_page) + 1
            total = max((len(all_tracks) - 1) // tracks_per_page + 1, 1)
            pages.append(
                EmbedBuilder.queue_page(dispatcher, chunk, page_num, total)
            )

        if not pages:
            await ctx.error("The queue is empty.")
            return

        await ctx.paginate(pages)

    # -- /nowplaying ------------------------------------------------------------

    @hybrid_command(name="nowplaying", aliases=["np"])
    async def nowplaying(self, ctx: Context) -> None:
        """Show the currently playing track."""
        dispatcher = self._get_dispatcher(ctx.guild.id)
        if dispatcher is None or dispatcher.current is None:
            await ctx.error("Nothing is playing right now.")
            return
        embed = EmbedBuilder.now_playing(dispatcher)
        await ctx.send(embed=embed)

    # -- /loop ------------------------------------------------------------------

    @hybrid_command(name="loop", aliases=["repeat"])
    async def loop(self, ctx: Context, mode: str = "") -> None:
        """Set or toggle the loop mode. Modes: `off`, `track`, `queue`."""
        dispatcher = self._get_dispatcher(ctx.guild.id)
        if dispatcher is None:
            await ctx.error("I'm not connected to a voice channel.")
            return

        valid = {"off", "track", "queue"}
        if mode:
            if mode.lower() not in valid:
                await ctx.error("Loop mode must be `off`, `track`, or `queue`.")
                return
            dispatcher.repeat = mode.lower()  # type: ignore[assignment]
        else:
            # Cycle: off → track → queue → off
            cycle = {"off": "track", "track": "queue", "queue": "off"}
            dispatcher.repeat = cycle[dispatcher.repeat]  # type: ignore[assignment]

        await ctx.approve(f"Loop mode set to **{dispatcher.repeat}**.")

    # -- /shuffle ---------------------------------------------------------------

    @hybrid_command(name="shuffle")
    async def shuffle(self, ctx: Context) -> None:
        """Shuffle the tracks in the queue."""
        dispatcher = self._get_dispatcher(ctx.guild.id)
        if dispatcher is None:
            await ctx.error("I'm not connected to a voice channel.")
            return

        if not dispatcher.queue:
            await ctx.error("The queue is empty — nothing to shuffle.")
            return

        count = dispatcher.shuffle()
        await ctx.approve(f"Shuffled **{count}** tracks.")

    # -- /volume ----------------------------------------------------------------

    @hybrid_command(name="volume", aliases=["vol"])
    async def volume(self, ctx: Context, volume: int = -1) -> None:
        """Set or view the playback volume (0-200)."""
        dispatcher = self._get_dispatcher(ctx.guild.id)
        if dispatcher is None:
            await ctx.error("I'm not connected to a voice channel.")
            return

        if volume == -1:
            await ctx.neutral(f"Volume is currently **{dispatcher.volume}%**.")
            return

        await dispatcher.set_volume(volume)
        await ctx.approve(f"Volume set to **{dispatcher.volume}%**.")

    # -- /seek ------------------------------------------------------------------

    @hybrid_command(name="seek")
    async def seek(self, ctx: Context, position: int) -> None:
        """Seek to a position in the current track (in seconds)."""
        dispatcher = self._get_dispatcher(ctx.guild.id)
        if dispatcher is None or dispatcher.current is None:
            await ctx.error("Nothing is playing right now.")
            return

        track = dispatcher.current
        if not track.is_seekable:
            await ctx.error("The current track doesn't support seeking.")
            return

        position_ms = position * 1000
        if position_ms < 0 or position_ms > track.duration_ms:
            await ctx.error(
                f"Position must be between `0` and `{track.duration_ms // 1000}` seconds."
            )
            return

        if dispatcher.player:
            await dispatcher.player.seek(position_ms)
            await ctx.approve(f"Seeked to **{position}** seconds.")
