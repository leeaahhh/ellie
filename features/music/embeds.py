from __future__ import annotations

from typing import Optional

import discord

from .dispatcher import Dispatcher
from .track import Track

# Valid Discord voice channel bitrates in bps
VALID_BITRATES = [
    8000, 16000, 32000, 64000, 96000, 128000,
    160000, 192000, 224000, 256000, 320000, 384000,
]


def format_duration(ms: int) -> str:
    """Return duration in ms as m:ss or h:mm:ss."""
    if not ms:
        return "??:??"
    minutes, seconds = divmod(ms // 1000, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def floor_bitrate(channel_bitrate: int) -> int:
    """Floor to the nearest valid bitrate not exceeding the channel bitrate."""
    return max(v for v in VALID_BITRATES if v <= channel_bitrate)


class EmbedBuilder:
    """Construct embeds from Dispatcher and Track state.

    Standalone class so embed logic doesn't live on either the Player
    or the Dispatcher.  Mirrors Green-bot's pattern where embeds are
    built at the call site rather than on the model objects.
    """

    @staticmethod
    def _get_requester_name(dispatcher: Dispatcher, track: Track) -> Optional[str]:
        """Resolve a requester ID to a display name, if the member is cached."""
        guild = dispatcher.bot.get_guild(dispatcher.guild_id)
        if guild is None:
            return None
        member = guild.get_member(track.requester_id)
        if member is None:
            return None
        return member.display_name

    @staticmethod
    def now_playing(dispatcher: Dispatcher) -> discord.Embed:
        """Build the *now playing* embed for the dispatcher's current track."""
        track = dispatcher.current
        if track is None:
            return discord.Embed(description="Nothing is currently playing.")

        embed = discord.Embed(
            title=track.title,
            url=track.url,
            description=(
                f"**{track.artist}**\n"
                f"`{format_duration(track.duration_ms)}`  •  {track.source_label()}"
            ),
        )
        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)

        requester_name = EmbedBuilder._get_requester_name(dispatcher, track)
        if requester_name:
            embed.set_footer(text=f"Requested by {requester_name}")

        # Append loop indicator to footer
        loop = dispatcher.repeat
        if loop == "track":
            extra = "  |  🔂 Track repeat"
        elif loop == "queue":
            extra = "  |  🔁 Queue repeat"
        else:
            extra = ""

        if extra and embed.footer:
            embed.set_footer(
                text=(embed.footer.text or "") + extra,
                icon_url=embed.footer.icon_url if embed.footer else None,
            )

        return embed

    @staticmethod
    def track_added(
        dispatcher: Dispatcher, track: Track, position: int
    ) -> discord.Embed:
        """Build an *added to queue* confirmation embed."""
        embed = discord.Embed(
            title="Added to Queue",
            description=(
                f"[**{track.title}**]({track.url})\n"
                f"**{track.artist}**  •  `{format_duration(track.duration_ms)}`"
                f"  •  {track.source_label()}\n"
                f"Position: **#{position}**"
            ),
        )
        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)

        requester_name = EmbedBuilder._get_requester_name(dispatcher, track)
        if requester_name:
            embed.set_footer(text=f"Requested by {requester_name}")

        return embed

    @staticmethod
    def playlist_added(count: int, *, name: str = "") -> discord.Embed:
        """Build a *playlist added* summary embed."""
        description = f"Added **{count}** tracks"
        if name:
            description += f" from **{name}**"
        description += " to the queue."
        return discord.Embed(title="Playlist Added", description=description)

    @staticmethod
    def queue_page(
        dispatcher: Dispatcher,
        tracks: list[Track],
        page: int,
        total_pages: int,
    ) -> discord.Embed:
        """Build one page of the queue listing."""
        embed = discord.Embed(title="Queue")
        lines: list[str] = []

        current = dispatcher.current
        if current and page == 1:
            lines.append(
                f"**Now Playing:** [{current.title}]({current.url}) "
                f"by *{current.artist}* `[{format_duration(current.duration_ms)}]`"
            )
            lines.append("")

        for i, track in enumerate(tracks, start=1):
            lines.append(
                f"`{i:02d}.` **{track.title}** "
                f"by *{track.artist}* `[{format_duration(track.duration_ms)}]`"
            )

        embed.description = "\n".join(lines) if lines else "No tracks queued."
        embed.set_footer(
            text=f"Page {page}/{max(total_pages, 1)}  •  {dispatcher.queue_size} tracks total"
        )
        return embed
