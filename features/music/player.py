from __future__ import annotations

import wavelink


class Player(wavelink.Player):
    """Thin wavelink.Player subclass.

    Acts as a VoiceProtocol shim for discord.py and a streaming handle for
    Lavalink.  ALL business logic — queue management, loop modes, embed
    construction, inactivity timers, error recovery — lives in the
    Dispatcher class.
    """
