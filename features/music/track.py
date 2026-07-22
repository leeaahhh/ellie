from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import wavelink

if TYPE_CHECKING:
    pass


class Track:
    """Wraps a wavelink.Playable with requester info and Spotify metadata.

    Mirrors Green-bot's Song class. All metadata is stored as explicit instance
    attributes rather than buried in wavelink's extras namespace, so the
    Dispatcher always has direct access regardless of what happens to the
    underlying Playable.
    """

    __slots__ = (
        "_playable",
        "requester_id",
        "source",
        "spotify_title",
        "spotify_artist",
        "spotify_url",
        "spotify_thumbnail",
    )

    def __init__(
        self,
        playable: wavelink.Playable,
        *,
        requester_id: int,
        source: str = "youtube",
        spotify_title: Optional[str] = None,
        spotify_artist: Optional[str] = None,
        spotify_url: Optional[str] = None,
        spotify_thumbnail: Optional[str] = None,
    ):
        self._playable = playable
        self.requester_id = requester_id
        self.source = source
        self.spotify_title = spotify_title
        self.spotify_artist = spotify_artist
        self.spotify_url = spotify_url
        self.spotify_thumbnail = spotify_thumbnail

    # -- pass-through / override properties for embed building -------------------

    @property
    def playable(self) -> wavelink.Playable:
        """The underlying wavelink.Playable (needed to call player.play())."""
        return self._playable

    @property
    def title(self) -> str:
        """Display title — prefers Spotify metadata, falls back to Playable."""
        return self.spotify_title or self._playable.title

    @property
    def artist(self) -> str:
        """Display artist — prefers Spotify metadata, falls back to Playable."""
        return self.spotify_artist or self._playable.author

    @property
    def url(self) -> str:
        """Display URL — prefers Spotify metadata, falls back to Playable."""
        return self.spotify_url or self._playable.uri or ""

    @property
    def thumbnail(self) -> Optional[str]:
        """Display thumbnail — prefers Spotify artwork, falls back to Playable."""
        if self.spotify_thumbnail:
            return self.spotify_thumbnail
        return self._playable.artwork

    @property
    def duration_ms(self) -> int:
        """Track duration in milliseconds."""
        return self._playable.length

    @property
    def is_seekable(self) -> bool:
        """Whether Lavalink supports seeking on this track."""
        return self._playable.is_seekable

    @property
    def uri(self) -> str:
        """Track URI (YouTube / Spotify)."""
        return self._playable.uri or ""

    @property
    def identifier(self) -> str:
        """Lavalink track identifier."""
        return self._playable.identifier or ""

    def source_label(self) -> str:
        """Human-readable source label for embeds."""
        return {"spotify": "Spotify", "soundcloud": "SoundCloud"}.get(
            self.source, "YouTube"
        )

    @classmethod
    def from_spotify_meta(
        cls,
        playable: wavelink.Playable,
        meta: dict,
        *,
        requester_id: int,
    ) -> "Track":
        """Construct a Track from Spotify metadata + resolved YouTube Playable.

        Parameters
        ----------
        playable : wavelink.Playable
            The YouTube match returned by yt-dlp / Lavalink.
        meta : dict
            Spotify metadata dict with keys: title, artist, url, thumbnail
        requester_id : int
            The Discord user ID who queued the track.
        """
        return cls(
            playable,
            requester_id=requester_id,
            source="spotify",
            spotify_title=meta.get("title"),
            spotify_artist=meta.get("artist"),
            spotify_url=meta.get("url"),
            spotify_thumbnail=meta.get("thumbnail"),
        )

    @classmethod
    def from_youtube(
        cls,
        playable: wavelink.Playable,
        *,
        requester_id: int,
    ) -> "Track":
        """Construct a Track from a plain YouTube Playable."""
        return cls(
            playable,
            requester_id=requester_id,
            source="youtube",
        )
