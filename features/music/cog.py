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

from .player import Player
from .spotify import SpotifyClient, SpotifyError
from .youtube import (
    parse_query,
    resolve_spotify_to_youtube,
    search_youtube,
)

if TYPE_CHECKING:
    from tools.ellie import ellie

log = logging.getLogger(__name__)

MUSIC_ERROR_EMOJI = config.Emoji.warn or ""


class Music(Cog):
    """Slash-command music player backed by Lavalink."""

    def __init__(self, bot: "ellie"):
        self.bot = bot
        self.spotify = SpotifyClient(bot)
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
        # Disconnect all active players
        for node in wavelink.Pool.nodes.values():
            for player in list(node.players.values()):
                try:
                    await player.teardown()
                except Exception:
                    pass
        await wavelink.Pool.close()

    # -- helpers ----------------------------------------------------------------

    def _get_player(self, guild_id: int) -> Optional[Player]:
        """Get the Player for a guild, if one exists."""
        try:
            node = wavelink.Pool.get_node()
            player = node.get_player(guild_id)
            if isinstance(player, Player):
                return player
        except Exception:
            pass
        return None

    async def _ensure_voice(self, ctx: Context) -> Optional[Player]:
        """Join the author's voice channel if not already connected.

        Returns the Player for the guild, or None (after notifying the user).
        """
        # Check that the user is in a voice channel
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.error("You're not connected to a **voice channel**")
            return None

        player = self._get_player(ctx.guild.id)

        if player is not None:
            # Already connected — make sure we're in the same channel
            if player.channel and player.channel.id != ctx.author.voice.channel.id:
                await ctx.error("I'm already in a different **voice channel**")
                return None
            # Bind this text channel as the player's home (for now-playing embeds)
            if getattr(player, "home", None) is None:
                player.home = ctx.channel
            return player

        # Wait for the Lavalink node to be fully ready (WebSocket handshake).
        # Pool.connect() returns after the HTTP handshake, but the WS "ready"
        # event can arrive a moment later.  If we try to join a voice channel
        # before the WS is up, the voice-server forwarding will stall and
        # discord.py will hit its 30 s connect timeout.
        try:
            node = wavelink.Pool.get_node()
        except Exception:
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

        # Join and create a Player
        try:
            player = await ctx.author.voice.channel.connect(
                cls=Player,
                self_deaf=True,
                timeout=60,
            )
        except asyncio.TimeoutError:
            log.exception("Voice channel connection timed out for guild %d", ctx.guild.id)
            await ctx.error(
                "Voice connection timed out — the **Lavalink node** may not be "
                "able to reach Discord's voice servers.  Check that UDP egress "
                "is allowed from the Lavalink container."
            )
            return None
        except discord.ClientException:
            await ctx.error("I was unable to join that **voice channel**")
            return None

        # Track the home channel
        player.home = ctx.channel

        # Read initial bitrate
        await player._apply_bitrate(ctx.author.voice.channel.bitrate)

        return player

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
        if not isinstance(player, Player):
            return

        channel = player.bound_channel
        if channel is None:
            return

        embed = player.build_now_playing_embed()
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            pass

    @Cog.listener()
    async def on_wavelink_track_end(
        self, payload: wavelink.TrackEndEventPayload
    ) -> None:
        player = payload.player
        if not isinstance(player, Player):
            return

        if payload.reason == "REPLACED":
            return

        # Let the player handle queue advancement + inactivity
        await player._play_next()

    @Cog.listener()
    async def on_wavelink_track_exception(
        self, payload: wavelink.TrackExceptionEventPayload
    ) -> None:
        player = payload.player
        if not isinstance(player, Player):
            return

        log.warning(
            "Track exception in guild %d: %s",
            player.guild.id if player.guild else 0,
            payload.exception,
        )

        channel = player.bound_channel
        if channel:
            try:
                await channel.send(
                    embed=discord.Embed(
                        description=f"{MUSIC_ERROR_EMOJI} The current track encountered an error — skipping."
                    )
                )
            except discord.HTTPException:
                pass

        await player._play_next()

    @Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        # Ignore non-guild or our own non-channel-move events
        if member.guild is None:
            return

        player = self._get_player(member.guild.id)
        if player is None:
            return

        # Case 1: the bot was moved to a different channel
        if member.id == self.bot.user.id and after.channel is not None:
            if before.channel is not None and before.channel.id != after.channel.id:
                await player._apply_bitrate(after.channel.bitrate)

        # Case 2: someone left the bot's voice channel — check for empty VC
        if before.channel is not None and player.channel is not None:
            if before.channel.id == player.channel.id:
                # Check current members of the player's channel (not before.channel,
                # since VoiceState.members reflects current state, not snapshot)
                humans = [
                    m for m in player.channel.members if not m.bot
                ]
                if not humans:
                    player._start_inactivity_timer(short=True)

    @Cog.listener()
    async def on_wavelink_inactive_player(self, player: Player) -> None:
        """Fired by wavelink when its own inactivity timeout expires."""
        if isinstance(player, Player) and player.channel:
            try:
                await player.teardown()
            except Exception:
                pass

    # -- /play ------------------------------------------------------------------

    @hybrid_command(name="play", aliases=["p"])
    async def play(self, ctx: Context, *, query: str) -> None:
        """Play a song from YouTube or Spotify.

        Accepts YouTube search terms, YouTube video/playlist URLs,
        and Spotify track/album/playlist links.
        """
        player = await self._ensure_voice(ctx)
        if player is None:
            return

        url_type, url_id = parse_query(query)

        # --- Spotify handling ---
        if url_type and url_type.startswith("spotify_"):
            await self._handle_spotify(ctx, player, url_type, url_id)
            return

        # --- Direct YouTube URL handling ---
        if url_type in ("youtube_video", "youtube_playlist"):
            results = await search_youtube(query)
            if results is None:
                await ctx.error("No results found for that URL.")
                return

            if isinstance(results, wavelink.Playlist):
                count = await player.add_tracks(
                    list(results), requester=ctx.author
                )
                await ctx.approve(
                    f"Added **{count}** tracks from the playlist to the queue."
                )
            else:
                track = results[0]
                await player.add_track(track, requester=ctx.author)
                position = player.queued_count
                embed = player.build_added_embed(track, position=position)
                await ctx.send(embed=embed)
            return

        # --- Plain text search ---
        results = await search_youtube(f"ytsearch:{query}")
        if results is None or not results:
            await ctx.error(f"No results found for **{query}**")
            return

        if isinstance(results, wavelink.Playlist):
            track = list(results)[0] if results else None
        else:
            track = results[0]

        if track is None:
            await ctx.error(f"No results found for **{query}**")
            return

        await player.add_track(track, requester=ctx.author)
        position = max(player.queued_count, 1)
        embed = player.build_added_embed(track, position=position)
        await ctx.send(embed=embed)

    async def _handle_spotify(
        self,
        ctx: Context,
        player: Player,
        url_type: str,
        spotify_id: str,
    ) -> None:
        """Resolve a Spotify URL and enqueue the resulting YouTube tracks."""
        try:
            if url_type == "spotify_track":
                meta = await self.spotify.get_track(spotify_id)
                track = await resolve_spotify_to_youtube(meta)
                if track is None:
                    await ctx.error(
                        "Could not find a matching YouTube video for that **Spotify track**."
                    )
                    return
                await player.add_track(track, requester=ctx.author)
                embed = player.build_added_embed(
                    track, position=max(player.queued_count, 1)
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
                    track = await resolve_spotify_to_youtube(meta)
                    if track is not None:
                        await player.add_track(track, requester=ctx.author)
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
                    track = await resolve_spotify_to_youtube(meta)
                    if track is not None:
                        await player.add_track(track, requester=ctx.author)
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

    # -- /pause -----------------------------------------------------------------

    @hybrid_command(name="pause")
    async def pause(self, ctx: Context) -> None:
        """Pause the current track."""
        player = self._get_player(ctx.guild.id)
        if player is None or not player.playing:
            await ctx.error("Nothing is playing right now.")
            return
        await player.pause(True)
        await ctx.approve("Paused playback.")

    # -- /resume ----------------------------------------------------------------

    @hybrid_command(name="resume")
    async def resume(self, ctx: Context) -> None:
        """Resume a paused track."""
        player = self._get_player(ctx.guild.id)
        if player is None:
            await ctx.error("I'm not connected to a voice channel.")
            return
        await player.pause(False)
        await ctx.approve("Resumed playback.")

    # -- /skip ------------------------------------------------------------------

    @hybrid_command(name="skip", aliases=["s", "next"])
    @cooldown(2, 5, BucketType.guild)
    async def skip(self, ctx: Context) -> None:
        """Skip the current track."""
        player = self._get_player(ctx.guild.id)
        if player is None or not player.playing:
            await ctx.error("Nothing is playing right now.")
            return

        await player.skip(force=True)
        await ctx.approve("Skipped the current track.")

    # -- /stop ------------------------------------------------------------------

    @hybrid_command(name="stop", aliases=["disconnect", "dc", "leave"])
    async def stop(self, ctx: Context) -> None:
        """Stop playback and disconnect from the voice channel."""
        player = self._get_player(ctx.guild.id)
        if player is None:
            await ctx.error("I'm not connected to a voice channel.")
            return

        await player.teardown()
        await ctx.approve("Disconnected from the voice channel.")

    # -- /queue -----------------------------------------------------------------

    @hybrid_command(name="queue", aliases=["q"])
    async def queue(self, ctx: Context) -> None:
        """Show the current playback queue."""
        player = self._get_player(ctx.guild.id)
        if player is None:
            await ctx.error("I'm not connected to a voice channel.")
            return

        if player.queue.is_empty and player.current is None:
            await ctx.error("The queue is empty.")
            return

        # Gather all queued tracks
        tracks: list[wavelink.Playable] = []
        current = player.current
        try:
            # The wavelink Queue doesn't expose iteration directly, so we
            # drain and re-fill.  This is safe because we're just reading.
            temp: list[wavelink.Playable] = []
            while not player.queue.is_empty:
                t = player.queue.get_nowait()
                temp.append(t)
                tracks.append(t)
            # Put them back
            for t in temp:
                await player.queue.put_wait(t)
        except Exception:
            pass

        if not tracks and current is None:
            await ctx.error("The queue is empty.")
            return

        from .player import _format_duration, _track_artist, _track_title

        # Build pages (10 tracks per page)
        entries: list[str] = []

        if current:
            entries.append(
                f"**Now Playing:** [{_track_title(current)}]({current.uri or ''}) "
                f"by *{_track_artist(current)}* `[{_format_duration(current.length)}]`"
            )
            entries.append("")  # spacer

        for i, track in enumerate(tracks, start=1):
            entries.append(
                f"`{i:02d}.` **{_track_title(track)}** "
                f"by *{_track_artist(track)}* `[{_format_duration(track.length)}]`"
            )

        # Use ctx.paginate() for multi-page output
        await ctx.paginate(
            entries,
            display_entries=len(entries),
            text="entries",
            of_text="Page",
        )

    # -- /nowplaying ------------------------------------------------------------

    @hybrid_command(name="nowplaying", aliases=["np"])
    async def nowplaying(self, ctx: Context) -> None:
        """Show the currently playing track."""
        player = self._get_player(ctx.guild.id)
        if player is None or player.current is None:
            await ctx.error("Nothing is playing right now.")
            return

        embed = player.build_now_playing_embed()
        await ctx.send(embed=embed)

    # -- /loop ------------------------------------------------------------------

    @hybrid_command(name="loop", aliases=["repeat"])
    async def loop(self, ctx: Context, mode: str = "") -> None:
        """Set or toggle the loop mode. Modes: `off`, `track`, `queue`."""
        player = self._get_player(ctx.guild.id)
        if player is None:
            await ctx.error("I'm not connected to a voice channel.")
            return

        mode_map = {
            "off": wavelink.QueueMode.normal,
            "track": wavelink.QueueMode.loop,
            "queue": wavelink.QueueMode.loop_all,
            "0": wavelink.QueueMode.normal,
            "1": wavelink.QueueMode.loop,
            "2": wavelink.QueueMode.loop_all,
        }

        if mode:
            if mode.lower() not in mode_map:
                await ctx.error(
                    "Loop mode must be `off`, `track`, or `queue`."
                )
                return
            player.queue.mode = mode_map[mode.lower()]
        else:
            # Cycle: normal → loop → loop_all → normal
            current = player.queue.mode
            if current == wavelink.QueueMode.normal:
                player.queue.mode = wavelink.QueueMode.loop
            elif current == wavelink.QueueMode.loop:
                player.queue.mode = wavelink.QueueMode.loop_all
            else:
                player.queue.mode = wavelink.QueueMode.normal

        names = {
            wavelink.QueueMode.normal: "off",
            wavelink.QueueMode.loop: "track",
            wavelink.QueueMode.loop_all: "queue",
        }
        await ctx.approve(
            f"Loop mode set to **{names[player.queue.mode]}**."
        )

    # -- /shuffle ---------------------------------------------------------------

    @hybrid_command(name="shuffle")
    async def shuffle(self, ctx: Context) -> None:
        """Shuffle the tracks in the queue."""
        player = self._get_player(ctx.guild.id)
        if player is None:
            await ctx.error("I'm not connected to a voice channel.")
            return

        if player.queue.is_empty:
            await ctx.error("The queue is empty — nothing to shuffle.")
            return

        count = await player.shuffle_queue()
        await ctx.approve(f"Shuffled **{count}** tracks.")

    # -- /volume ----------------------------------------------------------------

    @hybrid_command(name="volume", aliases=["vol"])
    async def volume(self, ctx: Context, volume: int = -1) -> None:
        """Set or view the playback volume (0-200)."""
        player = self._get_player(ctx.guild.id)
        if player is None:
            await ctx.error("I'm not connected to a voice channel.")
            return

        if volume == -1:
            await ctx.neutral(f"Volume is currently **{player.volume}%**.")
            return

        volume = max(0, min(200, volume))
        await player.set_volume(volume)
        await ctx.approve(f"Volume set to **{volume}%**.")

    # -- /seek ------------------------------------------------------------------

    @hybrid_command(name="seek")
    async def seek(self, ctx: Context, position: int) -> None:
        """Seek to a position in the current track (in seconds)."""
        player = self._get_player(ctx.guild.id)
        if player is None or player.current is None:
            await ctx.error("Nothing is playing right now.")
            return

        if not player.current.is_seekable:
            await ctx.error("The current track doesn't support seeking.")
            return

        position_ms = position * 1000
        if position_ms < 0 or position_ms > player.current.length:
            await ctx.error(
                f"Position must be between `0` and `{player.current.length // 1000}` seconds."
            )
            return

        await player.seek(position_ms)
        await ctx.approve(f"Seeked to **{position}** seconds.")
