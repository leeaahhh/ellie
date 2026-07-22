from __future__ import annotations

import asyncio
import random
import time
from typing import TYPE_CHECKING, Optional

import discord
import wavelink

if TYPE_CHECKING:
    from tools.ellie import ellie

# Valid Discord voice channel bitrates in bps
VALID_BITRATES = [
    8000,
    16000,
    32000,
    64000,
    96000,
    128000,
    160000,
    192000,
    224000,
    256000,
    320000,
    384000,
]

INACTIVITY_TIMEOUT = 180  # seconds after queue drains
EMPTY_VC_TIMEOUT = 30  # seconds after the last human leaves


def _format_duration(ms: int) -> str:
    """Return duration in ms as mm:ss or hh:mm:ss."""
    if not ms:
        return "??:??"
    minutes, seconds = divmod(ms // 1000, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def _source_label(track: wavelink.Playable) -> str:
    """Return a human-readable source label for a track."""
    src = getattr(track.extras, "source", None) or getattr(track, "source", "youtube")
    if src == "spotify":
        return "Spotify"
    if src == "soundcloud":
        return "SoundCloud"
    return "YouTube"


def _track_title(track: wavelink.Playable) -> str:
    """Return the display title, preferring Spotify metadata when present."""
    return getattr(track.extras, "spotify_title", None) or track.title


def _track_artist(track: wavelink.Playable) -> str:
    """Return the display artist, preferring Spotify metadata when present."""
    return getattr(track.extras, "spotify_artist", None) or track.author


def _track_url(track: wavelink.Playable) -> str:
    """Return the display URL, preferring Spotify metadata when present."""
    return getattr(track.extras, "spotify_url", None) or track.uri or ""


def _track_thumbnail(track: wavelink.Playable) -> Optional[str]:
    """Return the display thumbnail, preferring Spotify artwork."""
    spotify_thumb = getattr(track.extras, "spotify_thumbnail", None)
    if spotify_thumb:
        return spotify_thumb
    return track.artwork


class Player(wavelink.Player):
    """Per-guild wavelink player with inactivity handling and bitrate awareness."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._bitrate: int = 64000
        self.last_activity: float = 0.0
        self.inactivity_task: Optional[asyncio.Task] = None

    # -- bitrate ----------------------------------------------------------------

    async def _apply_bitrate(self, bitrate: int) -> None:
        """Floor bitrate to the nearest valid value not exceeding channel bitrate.

        Discord's Opus encoder caps at the channel bitrate; we track the
        effective ceiling so we can log / inform quality selection.  Lavalink
        itself picks the best available source format.
        """
        target = max(v for v in VALID_BITRATES if v <= bitrate)
        self._bitrate = target

    @property
    def bitrate(self) -> int:
        return self._bitrate

    # -- queue helpers ----------------------------------------------------------

    @property
    def queued_count(self) -> int:
        """Number of tracks waiting in the queue (excluding current)."""
        # wavelink Queue supports len()
        return len(self.queue)

    @property
    def bound_channel(self) -> Optional[discord.TextChannel]:
        """The text channel where now-playing embeds are sent."""
        home = getattr(self, "home", None)
        if home is None:
            return None
        return self.client.get_channel(home.id) if hasattr(home, "id") else home

    async def add_track(
        self, track: wavelink.Playable, *, requester: Optional[discord.Member] = None
    ) -> None:
        """Enqueue a single track and start playback if idle."""
        if requester:
            track.extras.requester_id = requester.id
        await self.queue.put_wait(track)
        if not self.playing and not self.queue.is_empty:
            await self._play_first()

    async def add_tracks(
        self,
        tracks: list[wavelink.Playable],
        *,
        requester: Optional[discord.Member] = None,
    ) -> int:
        """Enqueue multiple tracks. Returns the number added."""
        for track in tracks:
            if requester:
                track.extras.requester_id = requester.id
            await self.queue.put_wait(track)
        if not self.playing and not self.queue.is_empty:
            await self._play_first()
        return len(tracks)

    async def _play_first(self) -> None:
        """Start playback from the queue (called when player was idle)."""
        self._cancel_inactivity()
        if self.queue.is_empty:
            return
        next_track = await self.queue.get()
        if self.channel:
            await self._apply_bitrate(self.channel.bitrate)
        await self.play(next_track)

    async def _play_next(self) -> None:
        """Advance queue after a track ends naturally.

        Wavelink auto-plays the next track from the queue when one finishes.
        This method only handles the inactivity timer when the queue is truly
        empty or restarts playback if auto-advance didn't fire.
        """
        self._cancel_inactivity()

        # If already playing, wavelink handled the queue advance for us
        if self.playing:
            return

        # Queue is empty and nothing is playing — start inactivity countdown
        if self.queue.is_empty:
            self._start_inactivity_timer()
            return

        # Fallback: queue has tracks but nothing is playing — start the next one
        next_track = await self.queue.get()
        if self.channel:
            await self._apply_bitrate(self.channel.bitrate)
        await self.play(next_track)

    def _cancel_inactivity(self) -> None:
        """Cancel any pending inactivity disconnect."""
        if self.inactivity_task:
            self.inactivity_task.cancel()
            self.inactivity_task = None

    def _start_inactivity_timer(self, *, short: bool = False) -> None:
        """Schedule a disconnect after a period of inactivity."""
        timeout = EMPTY_VC_TIMEOUT if short else INACTIVITY_TIMEOUT
        self.last_activity = time.time()

        async def _disconnect_after_timeout():
            await asyncio.sleep(timeout)
            if self.playing or not self.queue.is_empty:
                return
            if short or (time.time() - self.last_activity >= timeout):
                await self.disconnect()

        self.inactivity_task = asyncio.ensure_future(_disconnect_after_timeout())

    # -- shuffle ----------------------------------------------------------------

    async def shuffle_queue(self) -> int:
        """Shuffle the current queue. Returns the number of tracks shuffled."""
        items: list[wavelink.Playable] = []
        while not self.queue.is_empty:
            items.append(self.queue.get_nowait())
        random.shuffle(items)
        for item in items:
            await self.queue.put_wait(item)
        return len(items)

    # -- teardown ---------------------------------------------------------------

    async def teardown(self) -> None:
        """Clean up: clear queue, cancel timers, disconnect."""
        self._cancel_inactivity()
        # Drain the queue
        while not self.queue.is_empty:
            try:
                self.queue.get_nowait()
            except Exception:
                break
        self.queue.reset()
        await self.disconnect()

    # -- embeds -----------------------------------------------------------------

    def _get_requester(self, track: wavelink.Playable) -> Optional[discord.Member]:
        """Resolve the requester member from extras if possible."""
        requester_id = getattr(track.extras, "requester_id", None)
        if requester_id is None:
            return None
        guild = self.guild
        if guild:
            return guild.get_member(requester_id)
        return None

    def build_now_playing_embed(self) -> discord.Embed:
        """Build a rich embed for the currently playing track."""
        track = self.current
        if track is None:
            return discord.Embed(description="Nothing is currently playing.")

        title = _track_title(track)
        artist = _track_artist(track)
        url = _track_url(track)
        duration = _format_duration(track.length)
        source = _source_label(track)
        thumbnail = _track_thumbnail(track)

        embed = discord.Embed(
            title=title,
            url=url,
            description=f"**{artist}**\n`{duration}`  •  {source}",
        )
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        requester = self._get_requester(track)
        if requester:
            embed.set_footer(
                text=f"Requested by {requester.display_name}",
                icon_url=requester.display_avatar,
            )

        # Append loop indicator to footer
        mode = self.queue.mode
        if mode == wavelink.QueueMode.loop:
            extra = "  |  🔂 Track"
        elif mode == wavelink.QueueMode.loop_all:
            extra = "  |  🔁 Queue"
        else:
            extra = ""

        if extra and embed.footer:
            embed.set_footer(
                text=(embed.footer.text or "") + extra,
                icon_url=embed.footer.icon_url if embed.footer else None,
            )

        return embed

    def build_track_embed(self, track: wavelink.Playable) -> discord.Embed:
        """Build an embed for a single queued track (used in /queue)."""
        title = _track_title(track)
        artist = _track_artist(track)
        url = _track_url(track)
        duration = _format_duration(track.length)
        source = _source_label(track)
        thumbnail = _track_thumbnail(track)

        embed = discord.Embed(
            title=title,
            url=url,
            description=f"**{artist}**\n`{duration}`  •  {source}",
        )
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        requester = self._get_requester(track)
        if requester:
            embed.set_footer(
                text=f"Queued by {requester.display_name}",
                icon_url=requester.display_avatar,
            )
        return embed

    def build_added_embed(
        self, track: wavelink.Playable, *, position: int = 0
    ) -> discord.Embed:
        """Build an embed confirming a track was added to the queue."""
        title = _track_title(track)
        artist = _track_artist(track)
        url = _track_url(track)
        duration = _format_duration(track.length)
        source = _source_label(track)
        thumbnail = _track_thumbnail(track)

        embed = discord.Embed(
            title="Added to Queue",
            description=(
                f"[**{title}**]({url})\n"
                f"**{artist}**  •  `{duration}`  •  {source}\n"
                f"Position: **#{position}**"
            ),
        )
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        requester = self._get_requester(track)
        if requester:
            embed.set_footer(
                text=f"Requested by {requester.display_name}",
                icon_url=requester.display_avatar,
            )
        return embed

    def build_playlist_embed(
        self, count: int, *, playlist_name: str = ""
    ) -> discord.Embed:
        """Build an embed confirming a playlist was added."""
        description = f"Added **{count}** tracks"
        if playlist_name:
            description += f" from **{playlist_name}**"
        description += " to the queue."
        return discord.Embed(title="Playlist Added", description=description)

    def build_queue_embed(
        self, tracks: list[wavelink.Playable], page: int, total_pages: int
    ) -> discord.Embed:
        """Build an embed summarising a page of the queue."""
        embed = discord.Embed(title="Queue")
        description_lines: list[str] = []

        for i, track in enumerate(tracks, start=1):
            title = _track_title(track)
            artist = _track_artist(track)
            duration = _format_duration(track.length)
            description_lines.append(
                f"`{i}.` **{title}** by *{artist}* `[{duration}]`"
            )

        embed.description = "\n".join(description_lines) or "No tracks queued."

        total = getattr(self.queue, "_max_size", 0) or len(tracks)
        embed.set_footer(text=f"Page {page}/{max(total_pages, 1)}  •  {total} tracks total")

        return embed
