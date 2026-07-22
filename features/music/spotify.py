from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

import asyncspotify
from cashews import cache

import config

if TYPE_CHECKING:
    from tools.ellie import ellie

# Cache TTL for Spotify metadata (60 minutes)
SPOTIFY_CACHE_TTL = 3600

# Regex to extract Spotify IDs from various URL formats
TRACK_ID_RE = re.compile(r"spotify\.com/track/([a-zA-Z0-9]+)")
ALBUM_ID_RE = re.compile(r"spotify\.com/album/([a-zA-Z0-9]+)")
PLAYLIST_ID_RE = re.compile(r"spotify\.com/playlist/([a-zA-Z0-9]+)")


class SpotifyClient:
    """Async Spotify Web API client using Client Credentials flow.

    Resolves track / album / playlist metadata so the bot can build
    YouTube search queries.  No audio is ever downloaded from Spotify.
    """

    def __init__(self, bot: "ellie"):
        self.bot = bot
        self._client: Optional[asyncspotify.Client] = None

    async def _ensure_auth(self) -> asyncspotify.Client:
        """Lazy-init the Spotify client with Client Credentials."""
        if self._client is not None:
            return self._client

        client_id = config.Authorization.Spotify.client_id
        client_secret = config.Authorization.Spotify.client_secret

        if not client_id or not client_secret:
            raise SpotifyError(
                "Spotify **client ID** and **client secret** are not configured."
            )

        auth = asyncspotify.ClientCredentialsFlow(
            client_id=client_id,
            client_secret=client_secret,
        )
        self._client = asyncspotify.Client(auth)
        return self._client

    # -- URL parsing -----------------------------------------------------------

    @staticmethod
    def parse_url(url: str) -> tuple[Optional[str], Optional[str]]:
        """Extract (kind, id) from a Spotify URL.  Returns (None, None) if no match.

        kind is one of: "track", "album", "playlist"
        """
        for pattern, kind in [
            (TRACK_ID_RE, "track"),
            (ALBUM_ID_RE, "album"),
            (PLAYLIST_ID_RE, "playlist"),
        ]:
            match = pattern.search(url)
            if match:
                return kind, match.group(1)
        return None, None

    # -- metadata fetching -----------------------------------------------------

    async def get_track(self, track_id: str) -> dict:
        """Fetch metadata for a single Spotify track.

        Returns a dict with: title, artist, duration_ms, url, thumbnail
        """
        client = await self._ensure_auth()
        track = await client.get_track(track_id)

        artist_name = (
            track.artists[0].name if track.artists else "Unknown Artist"
        )
        thumbnail = (
            track.album.images[0].url
            if track.album and track.album.images
            else None
        )

        return {
            "title": track.name,
            "artist": artist_name,
            "duration_ms": track.duration_ms,
            "url": f"https://open.spotify.com/track/{track_id}",
            "thumbnail": thumbnail,
        }

    async def get_album_tracks(self, album_id: str) -> list[dict]:
        """Fetch metadata for all tracks in a Spotify album.

        Handles pagination (Spotify returns max 50 tracks per page).
        """
        client = await self._ensure_auth()
        album = await client.get_album(album_id)

        tracks: list[dict] = []
        # Collect main album tracks
        album_art = album.images[0].url if album.images else None

        for item in album.tracks.items:
            artist_name = (
                item.artists[0].name if item.artists else "Unknown Artist"
            )
            tracks.append(
                {
                    "title": item.name,
                    "artist": artist_name,
                    "duration_ms": item.duration_ms,
                    "url": f"https://open.spotify.com/track/{item.id}",
                    "thumbnail": album_art,
                }
            )

        return tracks

    async def get_playlist_tracks(self, playlist_id: str) -> list[dict]:
        """Fetch metadata for all tracks in a Spotify playlist.

        Handles pagination (Spotify returns max 100 tracks per page).
        """
        client = await self._ensure_auth()
        playlist = await client.get_playlist(playlist_id)

        tracks: list[dict] = []

        async for item in playlist.tracks:
            if item.track is None:
                continue
            track = item.track
            artist_name = (
                track.artists[0].name if track.artists else "Unknown Artist"
            )
            thumbnail = (
                track.album.images[0].url
                if track.album and track.album.images
                else None
            )
            tracks.append(
                {
                    "title": track.name,
                    "artist": artist_name,
                    "duration_ms": track.duration_ms,
                    "url": f"https://open.spotify.com/track/{track.id}",
                    "thumbnail": thumbnail,
                }
            )

        return tracks

    @staticmethod
    def build_search_query(track: dict) -> str:
        """Build a 'artist - title' search query from track metadata."""
        return f"{track['artist']} - {track['title']}"


class SpotifyError(Exception):
    """Raised when Spotify API interaction fails."""
