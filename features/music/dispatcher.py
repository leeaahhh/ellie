from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Optional, Literal

import discord
import wavelink

from .track import Track
from .embeds import EmbedBuilder

if TYPE_CHECKING:
    from tools.ellie import ellie

log = logging.getLogger(__name__)

INACTIVITY_TIMEOUT = 180   # seconds after queue drains
EMPTY_VC_TIMEOUT = 30      # seconds after the last human leaves
MAX_CONSECUTIVE_ERRORS = 6  # before forcing node migration
SILENT_TIMEOUT_BUFFER = 10  # extra seconds past track duration for silent detection

RepeatMode = Literal["off", "track", "queue"]


class Dispatcher:
    """Per-guild music state and orchestration.

    Holds ALL state separately from the wavelink Player. The Player is treated
    as a dumb audio handle — we only call .play(), .stop(), .pause(), and
    .set_volume() on it.

    Mirrors Green-bot's ExtendedDispatcher pattern.
    """

    __slots__ = (
        "guild_id",
        "bot",
        "_player",
        "queue",
        "current",
        "previous_tracks",
        "repeat",
        "playing",
        "paused",
        "_volume",
        "home_channel_id",
        "errors",
        "errored",
        "last_activity",
        "_inactivity_task",
        "_silent_timeout_task",
    )

    def __init__(
        self,
        guild_id: int,
        bot: "ellie",
        player: wavelink.Player,
        *,
        home_channel_id: int,
    ):
        self.guild_id = guild_id
        self.bot = bot
        self._player: Optional[wavelink.Player] = player
        self.queue: list[Track] = []
        self.current: Optional[Track] = None
        self.previous_tracks: list[Track] = []
        self.repeat: RepeatMode = "off"
        self.playing: bool = False
        self.paused: bool = False
        self._volume: int = 100
        self.home_channel_id = home_channel_id
        self.errors: int = 0
        self.errored: bool = False
        self.last_activity: float = 0.0
        self._inactivity_task: Optional[asyncio.Task] = None
        self._silent_timeout_task: Optional[asyncio.Task] = None

    # -- player access ----------------------------------------------------------

    @property
    def player(self) -> Optional[wavelink.Player]:
        """The wavelink Player (dumb pipe). May be None after disconnect."""
        return self._player

    @player.setter
    def player(self, value: Optional[wavelink.Player]) -> None:
        self._player = value

    @property
    def channel(self) -> Optional[discord.VoiceChannel]:
        """The voice channel the bot is connected to in this guild."""
        if self._player and self._player.channel:
            return self._player.channel  # type: ignore[return-value]
        return None

    @property
    def home_channel(self) -> Optional[discord.TextChannel]:
        """The text channel where now-playing embeds are sent."""
        return self.bot.get_channel(self.home_channel_id)  # type: ignore[return-value]

    @property
    def node(self) -> Optional[wavelink.Node]:
        """The Lavalink node this player is attached to."""
        if self._player:
            return self._player.node
        return None

    @property
    def volume(self) -> int:
        return self._volume

    async def set_volume(self, volume: int) -> None:
        """Set volume on both the dispatcher and the player."""
        self._volume = max(0, min(200, volume))
        if self._player:
            await self._player.set_volume(self._volume)

    # -- queue operations -------------------------------------------------------

    @property
    def queue_size(self) -> int:
        return len(self.queue)

    def enqueue(self, track: Track) -> None:
        """Add a single track to the end of the queue."""
        self.queue.append(track)
        self.last_activity = time.time()

    def enqueue_many(self, tracks: list[Track]) -> int:
        """Add multiple tracks. Returns the number added."""
        self.queue.extend(tracks)
        self.last_activity = time.time()
        return len(tracks)

    def clear_queue(self) -> None:
        """Empty the queue without affecting the current track."""
        self.queue.clear()

    def shuffle(self) -> int:
        """Shuffle the queue in place. Returns the number of tracks shuffled."""
        import random

        count = len(self.queue)
        random.shuffle(self.queue)
        return count

    # -- playback control -------------------------------------------------------

    async def _play(self) -> None:
        """Core play logic.

        Shifts the next track from the queue, sets it as current, and calls
        player.play().  Mirrors Green-bot's ExtendedDispatcher.play().
        """
        if self._player is None:
            return

        self._cancel_inactivity()
        self._cancel_silent_timeout()

        # Push previous track to history
        if self.current is not None:
            self.previous_tracks.append(self.current)

        # Shift next track
        if self.queue:
            self.current = self.queue.pop(0)
        else:
            self.current = None

        if self.current is None:
            self.playing = False
            self._start_inactivity_timer()
            return

        try:
            await self._player.play(
                self.current.playable,
                volume=self._volume,
            )
        except Exception as exc:
            log.warning(
                "Failed to play track in guild %d: %s",
                self.guild_id,
                exc,
            )
            self.errors += 1
            self.errored = True
            # Try the next track
            await self._play()
            return

        self.playing = True
        self.paused = False
        self.errors = 0
        self.errored = False

    async def on_track_start(self) -> None:
        """Called when wavelink emits *track_start*.

        Sends the now-playing embed and arms the silent-failure detector.
        Mirrors Green-bot's started().
        """
        if self.current is None:
            return

        self._cancel_inactivity()
        self.last_activity = time.time()

        channel = self.home_channel
        if channel:
            embed = EmbedBuilder.now_playing(self)
            try:
                await channel.send(embed=embed)
            except discord.HTTPException:
                pass

        self._setup_silent_timeout()

    async def on_track_end(self, reason: str) -> None:
        """Called when wavelink emits *track_end*.

        Handles ALL repeat modes manually — no reliance on wavelink's
        opaque QueueMode auto-advance.  Mirrors Green-bot's onEnd().
        """
        if reason == "REPLACED":
            return  # User skipped; on_track_start handles the next track

        if self.current is None:
            return

        previous = self.current

        # Handle repeat modes manually
        if self.repeat == "track":
            self.queue.insert(0, previous)
        elif self.repeat == "queue":
            self.queue.append(previous)

        self.current = None

        # Play next or go idle
        if self.queue:
            await self._play()
        else:
            self.playing = False
            self._start_inactivity_timer()

    async def on_track_exception(self, exception: str) -> None:
        """Called when wavelink emits *track_exception*.

        Tracks consecutive errors; after MAX_CONSECUTIVE_ERRORS failures
        attempts to migrate the player to a different Lavalink node.
        Mirrors Green-bot's error handling.
        """
        self.errors += 1
        self.errored = True
        log.warning(
            "Track exception in guild %d (error #%d): %s",
            self.guild_id,
            self.errors,
            exception,
        )

        channel = self.home_channel
        if channel:
            try:
                await channel.send(
                    embed=discord.Embed(
                        description="The current track encountered an error — skipping."
                    )
                )
            except discord.HTTPException:
                pass

        # Migrate node after too many consecutive errors
        if self.errors >= MAX_CONSECUTIVE_ERRORS:
            await self._migrate_node()

        # Skip to next
        await self.on_track_end("exception")

    async def skip(self) -> None:
        """Skip the current track."""
        if self._player:
            await self._player.stop()  # fires track_end with reason="REPLACED"
        await self._play()

    async def pause(self) -> None:
        """Toggle pause on the current track."""
        if self._player:
            await self._player.pause(not self.paused)
        self.paused = not self.paused

    # -- node migration ---------------------------------------------------------

    async def _migrate_node(self) -> None:
        """Move the player to a different Lavalink node, if available.

        Mirrors Green-bot's node migration after repeated errors.
        """
        if self._player is None:
            return

        try:
            node = wavelink.Pool.get_node()
        except Exception:
            log.warning("No available nodes for migration in guild %d", self.guild_id)
            self.errors = 0
            return

        current_identifier = self._player.node.identifier if self._player.node else ""
        if node.identifier == current_identifier:
            log.warning(
                "Only one node available, cannot migrate guild %d", self.guild_id
            )
            self.errors = 0
            return

        try:
            await self._player.move(node)
            log.info(
                "Migrated guild %d player to node %s", self.guild_id, node.identifier
            )
        except Exception:
            log.exception("Failed to migrate node for guild %d", self.guild_id)

        self.errors = 0
        self.errored = False

    # -- inactivity handling ----------------------------------------------------

    def _cancel_inactivity(self) -> None:
        if self._inactivity_task:
            self._inactivity_task.cancel()
            self._inactivity_task = None

    def _start_inactivity_timer(self, *, short: bool = False) -> None:
        """Schedule a disconnect after a period of inactivity."""
        timeout = EMPTY_VC_TIMEOUT if short else INACTIVITY_TIMEOUT
        self.last_activity = time.time()

        async def _disconnect_after():
            await asyncio.sleep(timeout)
            if self.playing or self.queue:
                return
            if short or (time.time() - self.last_activity >= timeout):
                await self.teardown()

        self._cancel_inactivity()
        self._inactivity_task = asyncio.ensure_future(_disconnect_after())

    # -- silent failure detection -----------------------------------------------

    def _setup_silent_timeout(self) -> None:
        """Arm a timer that fires slightly past the track's expected duration.

        If on_track_end hasn't fired by then, the track silently failed
        (e.g. Lavalink sent the start event but the stream never arrived).
        """
        self._cancel_silent_timeout()

        if self.current is None:
            return
        duration_ms = self.current.duration_ms
        if duration_ms <= 0:
            return  # live stream — can't detect silent failure

        timeout_seconds = (duration_ms / 1000) + SILENT_TIMEOUT_BUFFER

        async def _check():
            await asyncio.sleep(timeout_seconds)
            if self.playing and self.current is not None:
                log.warning(
                    "Silent failure detected in guild %d — track exceeded expected duration",
                    self.guild_id,
                )
                await self.on_track_exception(
                    "Silent failure (duration exceeded)"
                )

        self._silent_timeout_task = asyncio.ensure_future(_check())

    def _cancel_silent_timeout(self) -> None:
        if self._silent_timeout_task:
            self._silent_timeout_task.cancel()
            self._silent_timeout_task = None

    # -- teardown ---------------------------------------------------------------

    async def teardown(self) -> None:
        """Full cleanup: cancel timers, clear state, disconnect player."""
        self._cancel_inactivity()
        self._cancel_silent_timeout()

        self.queue.clear()
        self.current = None
        self.previous_tracks.clear()
        self.playing = False
        self.paused = False
        self.repeat = "off"

        if self._player:
            try:
                await self._player.disconnect()
            except Exception:
                pass
            self._player = None
