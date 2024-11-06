# definitely broken

from datetime import timedelta

from asyncspotify import Client as SpotifyClient
from asyncspotify import ClientCredentialsFlow

import config
from tools.managers import cache
from tools.models.spotify import Song


@cache(ttl=timedelta(minutes=60), key="{query}")
async def song(query: str):
    """Search for a song on Spotify"""
    auth = ClientCredentialsFlow(
        client_id=config.Authorization.Spotify.client_id,
        client_secret=config.Authorization.Spotify.client_secret,
    )

    async with SpotifyClient(auth) as Spotify:
        results = await Spotify.search_tracks(
            q=query,
            limit=1,
        )

        if not results:
            raise ValueError("No results found.")

        return Song(url=results[0].link)
