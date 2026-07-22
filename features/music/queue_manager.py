from __future__ import annotations

from typing import Optional
from .dispatcher import Dispatcher


class QueueManager:
    """Registry mapping guild_id → Dispatcher.

    Thin wrapper around a dict.  Mirrors Green-bot's QueueManager class
    (which extends Map in JS).  The Music cog uses this as the single
    source of truth for per-guild music state.
    """

    __slots__ = ("_dispatchers",)

    def __init__(self):
        self._dispatchers: dict[int, Dispatcher] = {}

    def get(self, guild_id: int) -> Optional[Dispatcher]:
        return self._dispatchers.get(guild_id)

    def set(self, dispatcher: Dispatcher) -> None:
        self._dispatchers[dispatcher.guild_id] = dispatcher

    def delete(self, guild_id: int) -> Optional[Dispatcher]:
        return self._dispatchers.pop(guild_id, None)

    def has(self, guild_id: int) -> bool:
        return guild_id in self._dispatchers

    @property
    def size(self) -> int:
        return len(self._dispatchers)

    def clear(self) -> None:
        self._dispatchers.clear()
