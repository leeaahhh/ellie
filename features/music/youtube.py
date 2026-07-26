from __future__ import annotations

import asyncio
import re
from typing import Optional

import wavelink
from yt_dlp import YoutubeDL

# Compile regexes once
SPOTIFY_TRACK_RE = re.compile(
    r"(?:https?://)?(?:open\.)?spotify\.com/track/([a-zA-Z0-9]+)"
)
SPOTIFY_ALBUM_RE = re.compile(
    r"(?:https?://)?(?:open\.)?spotify\.com/album/([a-zA-Z0-9]+)"
)
SPOTIFY_PLAYLIST_RE = re.compile(
    r"(?:https?://)?(?:open\.)?spotify\.com/playlist/([a-zA-Z0-9]+)"
)

YOUTUBE_VIDEO_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})"
)
YOUTUBE_PLAYLIST_RE = re.compile(
    r"(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)"
)

def parse_query(query: str) -> tuple[Optional[str], Optional[str]]:
    """Inspect a query and return (type, id) if it matches a known URL pattern.

    Returns (None, None) for plain-text search queries.
    """
    for pattern, kind in [
        (SPOTIFY_TRACK_RE, "spotify_track"),
        (SPOTIFY_ALBUM_RE, "spotify_album"),
        (SPOTIFY_PLAYLIST_RE, "spotify_playlist"),
        (YOUTUBE_VIDEO_RE, "youtube_video"),
        (YOUTUBE_PLAYLIST_RE, "youtube_playlist"),
    ]:
        match = pattern.search(query)
        if match:
            return kind, match.group(1)
    return None, None


async def search_youtube(query: str) -> Optional[wavelink.Search]:
    """Search YouTube via wavelink's built-in source manager."""
    try:
        results: wavelink.Search = await wavelink.Playable.search(
            query, source=wavelink.TrackSource.YouTube
        )
        return results
    except Exception:
        return None


async def search_youtube_ytdlp(query: str) -> Optional[dict]:
    """Fallback: use yt-dlp directly when wavelink search fails."""
    try:
        loop = asyncio.get_running_loop()
        with YoutubeDL({"quiet": True, "format": "bestaudio/best"}) as ydl:
            info = await loop.run_in_executor(
                None, lambda: ydl.extract_info(f"ytsearch:{query}", download=False)
            )
            if info and "entries" in info and info["entries"]:
                return info["entries"][0]
    except Exception:
        pass
    return None


async def resolve_spotify_to_youtube(
    spotify_meta: dict,
) -> Optional[wavelink.Playable]:
    """Build a YouTube search from Spotify metadata and return the best match.

    Parameters
    ----------
    spotify_meta : dict
        Dict with keys: title, artist, duration_ms, url, thumbnail

    Returns
    -------
    wavelink.Playable or None
    """
    query = f"{spotify_meta['artist']} - {spotify_meta['title']}"
    results = await search_youtube(query)
    if not results:
        return None

    if isinstance(results, wavelink.Playlist):
        tracks = list(results)
    else:
        tracks = results

    if not tracks:
        return None

    # Prefer a track whose duration is within 10 % of the Spotify track
    spotify_duration = spotify_meta.get("duration_ms", 0)
    best = tracks[0]
    if spotify_duration:
        best_diff = abs(best.length - spotify_duration)
        for track in tracks[1:]:
            diff = abs(track.length - spotify_duration)
            if diff < best_diff:
                best_diff = diff
                best = track

    # Stamp Spotify metadata onto the playable
    best.extras.source = "spotify"
    best.extras.spotify_title = spotify_meta["title"]
    best.extras.spotify_artist = spotify_meta["artist"]
    best.extras.spotify_url = spotify_meta["url"]
    best.extras.spotify_thumbnail = spotify_meta.get("thumbnail")

    return best


async def resolve_youtube_url(query: str) -> Optional[wavelink.Search]:
    """Resolve a direct YouTube video or playlist URL."""
    return await wavelink.Playable.search(query)
