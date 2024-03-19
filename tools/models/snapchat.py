from typing import Literal

from pydantic import BaseModel


class SnapchatHighlight(BaseModel):
    type: Literal["image", "video"]
    url: str


class SnapchatProfile(BaseModel):
    url: str
    username: str
    display_name: str
    description: str | None
    snapcode: str
    bitmoji: str | None
    subscribers: int | None = 0
    stories: list[SnapchatHighlight] = []
    highlights: list[SnapchatHighlight] = []
