from pydantic import BaseModel


class Song(BaseModel):
    """A song from Spotify"""

    url: str
