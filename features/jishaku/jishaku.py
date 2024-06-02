from __future__ import annotations

import sys

import discord
import jishaku
from discord import Embed
from jishaku.cog import OPTIONAL_FEATURES, STANDARD_FEATURES
from jishaku.features.baseclass import Feature
from jishaku.math import natural_size

try:
    import psutil
except ImportError:
    psutil = None

from tools.managers import Context


class Jishaku(*OPTIONAL_FEATURES, *STANDARD_FEATURES):
    """Cog for Jishaku commands."""

    @Feature.Command(
        parent=None,
        name="jsk",
        aliases=["jishaku"],
        invoke_without_command=True,
    )
    async def jsk(self, ctx: Context):
        """
        The Jishaku debug and diagnostic commands.

        This command on its own gives a status brief.
        All other functionality is within its subcommands.
        """
        summary = [
            f"Jishaku `v{jishaku.__version__}` using discord.py `v{discord.__version__}` "
            f"on `{sys.platform}`.".replace("\n", ""),
            f"> Module was loaded *<t:{self.load_time.timestamp():.0f}:R>*, "
            f"cog was loaded *<t:{self.start_time.timestamp():.0f}:R>*.",
            "",
        ]

        # detect if [procinfo] feature is installed
        if psutil:
            try:
                proc = psutil.Process()

                with proc.oneshot():
                    try:
                        proc.name()
                        pid = proc.pid
                        thread_count = proc.num_threads()

                        summary.append(
                            f"Running on PID `{pid}` with `{thread_count}` threads."
                        )
                    except psutil.AccessDenied:
                        pass

                    try:
                        mem = proc.memory_full_info()
                        summary.append(
                            f"> Using `{natural_size(mem.rss)}` of physical memory"
                            f"\n> `{natural_size(mem.uss)}` of which is unique to this process."
                        )
                    except psutil.AccessDenied:
                        pass

                    summary.append("")  # blank line
            except psutil.AccessDenied:
                summary.append(
                    "psutil is installed, but this process does not have high enough access rights "
                    "to query process information."
                )
                summary.append("")  # blank line

        cache_summary = (
            f"`{len(self.bot.guilds)}` guilds and `{len(self.bot.users)}` users"
        )

        # Show shard settings to summary
        if isinstance(self.bot, discord.AutoShardedClient):
            if len(self.bot.shards) > 20:
                summary.append(
                    f"This bot is automatically sharded (`{len(self.bot.shards)}` shards of `{self.bot.shard_count}`)"
                    f" and can see {cache_summary}."
                )
            else:
                shard_ids = ", ".join(str(i) for i in self.bot.shards.keys())
                summary.append(
                    f"This bot is automatically sharded (Shards `{shard_ids}` of `{self.bot.shard_count}`)"
                    f" and can see {cache_summary}."
                )
        elif self.bot.shard_count:
            summary.append(
                f"This bot is manually sharded (Shard `{self.bot.shard_id}` of `{self.bot.shard_count}`)"
                f" and can see {cache_summary}."
            )
        else:
            summary.append(f"This bot is not sharded and can see {cache_summary}.")

        # Show websocket latency in milliseconds
        summary.append(
            f">>> Average websocket latency is `{round(self.bot.latency * 1000, 2)}ms` with `{len(set(self.bot.walk_commands()))}` loaded features."
        )

        # pylint: disable=protected-access
        if self.bot._connection.max_messages:
            message_cache = (
                f"Message cache capped at {self.bot._connection.max_messages}"
            )
        else:
            message_cache = "Message cache is disabled"

        if discord.version_info >= (1, 5, 0):
            presence_intent = f"The presence intent is {'enabled' if self.bot.intents.presences else 'disabled'}"
            members_intent = f"the members intent is {'enabled' if self.bot.intents.members else 'disabled'}"

            summary.append(f"{presence_intent} and {members_intent}.")
        else:
            guild_subscriptions = f"Guild Subscriptions are {'enabled' if self.bot._connection.guild_subscriptions else 'disabled'}"  # type: ignore

            summary.append(f"{message_cache} and {guild_subscriptions}.")

        # pylint: enable=protected-access

        summ = "\n".join(summary)
        if ctx.channel.permissions_for(ctx.me).embed_links:  # type: ignore
            embed = Embed(description=summ)
            await ctx.send(embed=embed)
        else:
            await ctx.send(summ)
