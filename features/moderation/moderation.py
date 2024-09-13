import os
from asyncio import Lock, create_subprocess_shell, gather, sleep, wait_for
from contextlib import suppress
from datetime import timedelta
from io import BytesIO
from re import finditer
from tempfile import TemporaryDirectory
from traceback import format_exception
from typing import Literal

from discord import Embed
from discord import Emoji as DiscordEmoji
from discord import (File, Forbidden, GuildSticker, HTTPException, Message,
                     NotFound, PartialEmoji, RateLimited, TextChannel, User,
                     VoiceChannel)
from discord.ext.commands import (BucketType, command, cooldown, group,
                                  has_permissions, max_concurrency)
from discord.utils import format_dt, utcnow
from PIL import Image

import config
from tools.converters.basic import (Emoji, EmojiFinder, ImageFinder,
                                    ImageFinderStrict, Member, Role, Roles,
                                    StickerFinder, TimeConverter)
from tools.converters.color import Color
from tools.converters.embed import EmbedScript
from tools.managers import regex
from tools.managers.cog import Cog
from tools.managers.context import Context
from tools.utilities.text import Plural, hash


class Moderation(Cog):
    """Cog for Moderation commands."""

    def __init__(self, bot):
        self.bot = bot
        self.case_lock: Lock = Lock()

    @Cog.listener("on_member_update")
    async def force_nickname(self, before: Member, after: Member):
        """Listen for nickname changes and force them back"""
        if before.nick == after.nick:
            return

        if nick := await self.bot.redis.get(
            f"nickname:{hash(f'{after.guild.id}-{after.id}')}"
        ):
            if nick != after.nick:
                with suppress(Forbidden):
                    await after.edit(nick=nick, reason="Nickname locked")

    @Cog.listener("on_member_join")
    async def force_nickname_rejoin(self, member: Member):
        """Listen for members joining and force their nickname"""
        if nick := await self.bot.redis.get(
            f"nickname:{hash(f'{member.guild.id}-{member.id}')}"
        ):
            with suppress(Forbidden):
                await member.edit(nick=nick, reason="Nickname locked")

    async def moderation_entry(
        self: "Moderation",
        ctx: Context,
        target: Member | User | Role | TextChannel | str,
        action: str,
        reason: str = "no reason provided",
    ):
        """Create a log entry for moderation actions."""
        mod_channel = await self.bot.db.fetchval(
            "SELECT mod_log FROM config WHERE guild_id = $1", ctx.guild.id
        )
        channel = ctx.guild.get_channel(mod_channel)
        if not channel:
            return

        async with self.case_lock:
            case = (
                await self.bot.db.fetchval(
                    "SELECT COUNT(*) FROM cases WHERE guild_id = $1",
                    ctx.guild.id,
                )
                + 1
            )

            if type(target) in (Member, User):
                _TARGET = "Member"
            elif type(target) is Role:
                _TARGET = "Role"
            elif type(target) is TextChannel:
                _TARGET = "Channel"
            else:
                _TARGET = "Target"

            embed = Embed(
                description=format_dt(utcnow(), "F")
                + " ("
                + format_dt(utcnow(), "R")
                + ")",
                color=config.Color.neutral,
            )
            embed.add_field(
                name=f"**Case #{case:,} | {action.title()}** ",
                value=f"""
                > **Moderator:** {ctx.author} (`{ctx.author.id}`)
                > **{_TARGET}:** {target} (`{target.id}`)
                > **Reason:** {reason}
                """,
            )
            embed.set_author(
                name=ctx.author.name, icon_url=ctx.author.display_avatar.url
            )

            try:
                message = await channel.send(embed=embed)
            except Forbidden:
                return await self.bot.db.execute(
                    "UPDATE config SET mod_log = $1 WHERE guild_id = $2",
                    None,
                    ctx.guild.id,
                )

            await self.bot.db.execute(
                "INSERT INTO cases (guild_id, case_id, case_type, message_id, moderator_id, target_id, moderator, target, reason, timestamp)"
                " VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)",
                ctx.guild.id,
                case,
                action.lower(),
                message.id,
                ctx.author.id,
                target.id,
                str(ctx.author),
                str(target),
                reason,
                message.created_at,
            )

    async def invoke_message(
        self,
        ctx: Context,
        default_function: str,
        default_message: str = None,
        **kwargs,
    ):
        """Send the moderation invoke message"""
        configuration = await self.bot.fetch_config(ctx.guild.id, "invoke") or {}
        if script := configuration.get(
            f"{ctx.command.qualified_name.replace(' ', '.')}"
        ):
            script = EmbedScript(script)
            try:
                await script.send(
                    ctx,
                    bot=self.bot,
                    guild=ctx.guild,
                    channel=kwargs.pop("channel", None) or ctx.channel,
                    moderator=ctx.author,
                    **kwargs,
                )
            except Exception as error:
                traceback_text = "".join(
                    format_exception(type(error), error, error.__traceback__, 4)
                )
                print(traceback_text)
        elif default_message:
            await default_function(default_message)
        else:
            await default_function()

    @group(
        name="set",
        usage="(subcommand) <args>",
        example="banner dscord.com/chnls/999/..png",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def _set(self, ctx: Context):
        """Set server settings through rei"""
        await ctx.send_help()

    @_set.command(
        name="name",
        usage="(text)",
        example="rei guild",
        aliases=["n"],
    )
    @has_permissions(manage_guild=True)
    async def set_name(self, ctx: Context, *, text: str):
        """Set the server name"""
        if len(text) > 100:
            return await ctx.error(
                "The **server name** can't be longer than **100** characters"
            )

        try:
            await ctx.guild.edit(
                name=text, reason=f"Name set by {ctx.author} ({ctx.author.id})"
            )
        except HTTPException:
            return await ctx.error(f"Couldn't set the **server name** to **{text}**")

        await self.invoke_message(
            ctx,
            ctx.approve,
            f"Set the **server name** to **{text}**",
            text=text,
        )

    @_set.command(
        name="icon",
        usage="(image)",
        example="https://dscord.com/chnls/999/..png",
        aliases=["i"],
    )
    @has_permissions(manage_guild=True)
    async def set_icon(self, ctx: Context, *, image: ImageFinder = None):
        """Set the server icon"""
        image = image or await ImageFinder.search(ctx)

        async with ctx.typing():
            response = await self.bot.session.request("GET", image)

            try:
                await ctx.guild.edit(
                    icon=response,
                    reason=f"Banner set by {ctx.author} ({ctx.author.id})",
                )
            except HTTPException:
                return await ctx.error(
                    f"Couldn't set the **server icon** to [**image**]({image})"
                )

        await self.invoke_message(
            ctx,
            ctx.approve,
            f"Set the **server icon** to [**image**]({image})",
            image=image,
        )

    @_set.command(
        name="banner",
        usage="(image)",
        example="https://dscord.com/chnls/999/..png",
        aliases=["background", "b"],
    )
    @has_permissions(manage_guild=True)
    async def set_banner(self, ctx: Context, *, image: ImageFinder = None):
        """Set the server banner"""
        image = image or await ImageFinder.search(ctx)

        async with ctx.typing():
            response = await self.bot.session.get(image)
            buffer = await response.read()

            try:
                await ctx.guild.edit(
                    banner=buffer,
                    reason=f"Banner set by {ctx.author} ({ctx.author.id})",
                )
            except HTTPException:
                return await ctx.error(
                    f"Couldn't set the **server banner** to [**image**]({image})"
                )

        await self.invoke_message(
            ctx,
            ctx.approve,
            f"Set the **server banner** to [**image**]({image})",
            image=image,
        )

    @_set.command(
        name="channel",
        usage="<name or topic> (text)",
        example="name bots",
    )
    @has_permissions(manage_channels=True)
    async def set_channel(
        self,
        ctx: Context,
        option: Literal["name", "topic"],
        *,
        text: str,
    ):
        """Set the channel name or topic"""
        if not isinstance(ctx.channel, TextChannel):
            return await ctx.error(
                "This command can only be used in a **text channel**"
            )

        try:
            if option == "name":
                await ctx.channel.edit(name=text)
            else:
                await ctx.channel.edit(topic=text)
        except HTTPException:
            return await ctx.error(
                f"Couldn't set the **channel {option}** to **{text}**"
            )
        except RateLimited as error:
            return await ctx.error(
                f"Couldn't set the **channel {option}** because of a **rate limit** (`{error.retry_after:.2f}s`)"
            )

        await self.invoke_message(
            ctx,
            ctx.approve,
            f"Set the **channel {option}** to `{text}`",
            option=option,
            text=text,
        )

    @group(
        name="nickname",
        usage="<member> (text)",
        example="igna ignatico",
        aliases=["nick", "n"],
        invoke_without_command=True,
    )
    @has_permissions(manage_nicknames=True)
    async def nickname(
        self,
        ctx: Context,
        member: Member | None = None,
        *,
        text: str,
    ):
        """Set the nickname of a user"""
        member = member or ctx.author
        await Member().hierarchy(ctx, member, author=True)

        if len(text) > 32:
            return await ctx.error(
                "The **nickname** can't be longer than **32** characters"
            )

        if await self.bot.redis.exists(
            f"nickname:{hash(f'{ctx.guild.id}-{member.id}')}"
        ):
            return await ctx.error(
                f"**{member}**'s nickname is currently **locked**\n> Use `{ctx.prefix}nickname force cancel` to unlock it"
            )

        try:
            await member.edit(
                nick=text,
                reason=f"Nickname set by {ctx.author} ({ctx.author.id})",
            )
        except HTTPException:
            return await ctx.error(f"Couldn't set the **nickname** to **{text}**")

        await self.invoke_message(
            ctx,
            ctx.approve,
            f"Set **{member}**'s nickname to `{text}`",
            user=member,
            text=text,
        )

    @nickname.command(
        name="remove",
        usage="<member>",
        example="igna",
        aliases=["reset", "rm"],
    )
    @has_permissions(manage_nicknames=True)
    async def nickname_remove(
        self,
        ctx: Context,
        member: Member | None = None,
    ):
        """Remove the nickname of a user"""
        member = member or ctx.author
        await Member().hierarchy(ctx, member, author=True)

        if not member.nick:
            return await ctx.error(f"**{member}** doesn't have a **nickname**")

        if await self.bot.redis.exists(
            f"nickname:{hash(f'{ctx.guild.id}-{member.id}')}"
        ):
            return await ctx.error(
                f"**{member}**'s nickname is currently **locked**\n> Use `{ctx.prefix}nickname force cancel` to unlock it"
            )

        try:
            await member.edit(
                nick=None,
                reason=f"Nickname removed by {ctx.author} ({ctx.author.id})",
            )
        except HTTPException:
            return await ctx.error(f"Couldn't remove **{member}**'s nickname")

        await self.invoke_message(
            ctx, ctx.approve, f"Removed **{member}**'s nickname", user=member
        )

    @nickname.group(
        name="force",
        usage="(member) <duration> (text)",
        example="rei 7d shito",
        aliases=["lock"],
        invoke_without_command=True,
    )
    @has_permissions(manage_nicknames=True)
    async def nickname_force(
        self,
        ctx: Context,
        member: Member,
        duration: TimeConverter | None,
        *,
        text: str,
    ):
        """Restrict the user from changing their nickname"""
        await Member().hierarchy(ctx, member)

        if len(text) > 32:
            return await ctx.error(
                "The **nickname** can't be longer than **32** characters"
            )

        if text:
            try:
                await member.edit(
                    nick=text,
                    reason=f"Nickname locked by {ctx.author} ({ctx.author.id})",
                )
            except HTTPException:
                return await ctx.error(f"Couldn't set the **nickname** to **{text}**")

            await self.bot.redis.set(
                f"nickname:{hash(f'{ctx.guild.id}-{member.id}')}",
                text,
                expire=(duration.seconds if duration else None),
            )
            await self.invoke_message(
                ctx,
                ctx.approve,
                f"Now **forcing nickname** for **{member}**",
                user=member,
                text=text,
            )

    @nickname_force.command(
        name="cancel",
        usage="(member)",
        example="rei",
        aliases=["stop", "end"],
    )
    @has_permissions(manage_nicknames=True)
    async def nickname_force_cancel(
        self,
        ctx: Context,
        *,
        member: Member,
    ):
        """Cancel the nickname lock"""
        await Member().hierarchy(ctx, member, author=True)

        if not await self.bot.redis.exists(
            f"nickname:{hash(f'{ctx.guild.id}-{member.id}')}"
        ):
            return await ctx.error(f"Not **forcing nickname** for **{member}**")

        await self.bot.redis.delete(f"nickname:{hash(f'{ctx.guild.id}-{member.id}')}")
        with suppress(HTTPException):
            await member.edit(
                nick=None,
                reason=f"Nickname lock cancelled by {ctx.author} ({ctx.author.id})",
            )
        await self.invoke_message(
            ctx,
            ctx.approve,
            f"No longer **forcing nickname** for **{member}**",
            user=member,
        )

    @command(
        name="reason",
        usage="<case ID> (reason)",
        example="User was spamming",
        aliases=["rsn"],
    )
    @has_permissions(manage_messages=True)
    async def reason(self, ctx: Context, case_id: int | None, *, reason: str):
        """Update a moderation case reason"""
        case = await self.bot.db.fetchrow(
            "SELECT * FROM cases WHERE guild_id = $1 AND (case_id = $2 OR case_id = (SELECT MAX(case_id) FROM cases WHERE guild_id = $1))",
            ctx.guild.id,
            case_id or 0,
        )
        if not case:
            return await ctx.error("There aren't any **cases** in this server")
        if case_id and case["case_id"] != case_id:
            return await ctx.error(f"Couldn't find a **case** with the ID `{case_id}`")

        with suppress(Exception):
            mod_log = await self.bot.db.fetchval(
                "SELECT mod_log FROM config WHERE guild_id = $1", ctx.guild.id
            )
            if channel := self.bot.get_channel(mod_log):
                message = await channel.fetch_message(case["message_id"])

                embed = message.embeds[0]
                field = embed.fields[0]
                embed.set_field_at(
                    0,
                    name=field.name,
                    value=(
                        field.value.replace(
                            f"**Reason:** {case['reason']}",
                            f"**Reason:** {reason}",
                        )
                    ),
                )
                await message.edit(embed=embed)
        await self.bot.db.execute(
            "UPDATE cases SET reason = $3 WHERE guild_id = $1 AND case_id = $2",
            ctx.guild.id,
            case["case_id"],
            reason,
        )
        return await self.invoke_message(
            ctx, ctx.react_check, case_id=case["case_id"], reason=reason
        )

    @group(
        name="history",
        usage="(user)",
        example="igna",
        invoke_without_command=True,
    )
    @has_permissions(manage_messages=True)
    async def history(self, ctx: Context, *, user: Member | User):
        """View punishment history for a user"""
        cases = await self.bot.db.fetch(
            "SELECT * FROM cases WHERE guild_id = $1 AND target_id = $2 ORDER BY case_id DESC",
            ctx.guild.id,
            user.id,
        )
        if not cases:
            return await ctx.error(
                f"**{user}** doesn't have any **cases** in this server"
            )

        embed = Embed(
            title=f"Punishment History for {user}",
        )
        embeds = []

        for case in cases:
            embed.add_field(
                name=f"Case #{case['case_id']} | {case['case_type'].title()}",
                value=(
                    f"{(format_dt(case['timestamp'], 'F') + ' (' + format_dt(case['timestamp'], 'R') + ')')}\n>>>"
                    f" **Moderator:** {self.bot.get_user(case['moderator_id'] or case['moderator'])}\n**Reason:** {case['reason']}"
                ),
                inline=False,
            )

            if len(embed.fields) == 3:
                embeds.append(embed.copy())
                embed.clear_fields()

        if embed.fields:
            embeds.append(embed.copy())

        await ctx.paginate(embeds)

    @history.command(
        name="remove",
        usage="(user) (case ID)",
        example="igna 9",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_messages=True)
    async def history_remove(
        self,
        ctx: Context,
        user: Member | User,
        case_id: int,
    ):
        """Remove a punishment from a user's history"""
        if not (
            await self.bot.db.fetchrow(
                "SELECT * FROM cases WHERE guild_id = $1 AND target_id = $2 AND case_id = $3",
                ctx.guild.id,
                user.id,
                case_id,
            )
        ):
            return await ctx.error(
                f"Couldn't find a **case** with the ID `{case_id}` for **{user}**"
            )

        await self.bot.db.execute(
            "DELETE FROM cases WHERE guild_id = $1 AND target_id = $2 AND case_id = $3",
            ctx.guild.id,
            user.id,
            case_id,
        )

        return await ctx.react_check()

    @history.command(
        name="reset",
        usage="(user)",
        example="igna",
        aliases=["clear"],
    )
    @has_permissions(manage_messages=True)
    async def history_reset(self, ctx: Context, user: Member | User):
        """Reset a user's punishment history"""
        await ctx.prompt(
            f"Are you sure you want to **reset** all punishment history for **{user}**?"
        )

        cases = await self.bot.db.fetch(
            "SELECT * FROM cases WHERE guild_id = $1 AND target_id = $2",
            ctx.guild.id,
            user.id,
        )

        if not cases:
            return await ctx.error(
                f"**{user}** doesn't have any **cases** in this server"
            )

        await self.bot.db.execute(
            "DELETE FROM cases WHERE guild_id = $1 AND target_id = $2",
            ctx.guild.id,
            user.id,
        )
        return await ctx.react_check()

    @command(
        name="timeout",
        usage="(member) (duration) <reason>",
        example="igna 7d trolling",
        aliases=["mute"],
    )
    @has_permissions(manage_messages=True)
    async def timeout(
        self,
        ctx: Context,
        member: Member,
        duration: TimeConverter,
        *,
        reason: str = "No reason provided",
    ):
        """Temporary timeout a member from the server"""
        await Member().hierarchy(ctx, member)

        if duration.seconds < 60:
            return await ctx.error(
                "The **duration** can't be shorter than **1 minute**"
            )
        if duration.seconds > 2419200:
            return await ctx.error("The **duration** can't be longer than **28 days**")

        try:
            await member.timeout(duration.delta, reason=f"{ctx.author}: {reason}")
        except HTTPException:
            return await ctx.error(f"Couldn't timeout **{member}**")

        await self.invoke_message(
            ctx,
            ctx.approve,
            f"Timed out **{member}** for **{duration}**",
            user=member,
            duration=duration,
            reason=reason,
        )
        await self.moderation_entry(ctx, member, "timeout", reason)

    @group(
        name="untimeout",
        usage="(member) <reason>",
        example="igna forgiven",
        aliases=["unmute"],
        invoke_without_command=True,
    )
    @has_permissions(manage_messages=True)
    async def untimeout(
        self,
        ctx: Context,
        member: Member,
        *,
        reason: str = "No reason provided",
    ):
        """Lift the timeout from a member"""
        await Member().hierarchy(ctx, member)

        if not member.timed_out_until:
            return await ctx.error(f"**{member}** isn't **timed out**")

        try:
            await member.timeout(None, reason=f"{ctx.author}: {reason}")
        except HTTPException:
            return await ctx.error(f"Couldn't remove the timeout from **{member}**")

        await self.invoke_message(
            ctx,
            ctx.approve,
            f"Lifted timeout for **{member}**",
            user=member,
            reason=reason,
        )
        await self.moderation_entry(ctx, member, "timeout lifted", reason)

    @command(
        name="ban",
        usage="(user) <delete history> <reason>",
        example="igna 7d trolling",
        parameters={
            "silent": {
                "require_value": False,
                "description": "Silently ban the user",
                "aliases": ["s"],
            }
        },
        aliases=["b"],
    )
    @has_permissions(ban_members=True)
    async def ban(
        self,
        ctx: Context,
        user: Member | User,
        days: Literal[0, 1, 7] | None = 0,
        *,
        reason: str = "No reason provided",
    ):
        """Ban a user from the server and optionally delete their messages"""
        await Member().hierarchy(ctx, user)

        if isinstance(user, Member) and user.premium_since:
            await ctx.prompt(
                f"Are you sure you want to ban {user.mention}?\n> They're currently **boosting** the server"
            )

        if (
            isinstance(user, Member)
            and not ctx.parameters.get("silent")
            and not user.bot
        ):
            embed = Embed(
                color=config.Color.neutral,
                title="Banned",
                description=f"> You've been banned from {ctx.guild.name}",
            )
            embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)

            embed.add_field(name="Moderator", value=ctx.author)
            embed.add_field(name="Reason", value=reason)
            embed.set_thumbnail(url=ctx.guild.icon)

            with suppress(HTTPException):
                await user.send(embed=embed)

        try:
            await ctx.guild.ban(
                user,
                reason=f"{ctx.author}: {reason}",
                delete_message_days=days,
            )
        except Forbidden:
            await ctx.error(f"I don't have **permissions** to ban {user.mention}")

        await self.invoke_message(
            ctx, ctx.check, user=user, duration="null", reason=reason
        )
        return await self.moderation_entry(ctx, user, "ban", reason)

    @command(
        name="kick",
        usage="(member) <reason>",
        example="igna trolling",
        parameters={
            "silent": {
                "require_value": False,
                "description": "Silently kick the member",
                "aliases": ["s"],
            }
        },
        aliases=["boot", "k"],
    )
    @has_permissions(kick_members=True)
    async def kick(
        self,
        ctx: Context,
        member: Member,
        *,
        reason: str = "No reason provided",
    ):
        """Kick a member from the server"""
        await Member().hierarchy(ctx, member)

        if member.premium_since:
            await ctx.prompt(
                f"Are you sure you want to kick {member.mention}?\n> They're currently **boosting** the server"
            )

        if not ctx.parameters.get("silent") and not member.bot:
            embed = Embed(
                color=config.Color.neutral,
                title="Kicked",
                description=f"> You've been kicked from {ctx.guild.name}",
            )
            embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)

            embed.add_field(name="Moderator", value=ctx.author)
            embed.add_field(name="Reason", value=reason)
            embed.set_thumbnail(url=ctx.guild.icon)

            with suppress(Exception):
                await member.send(embed=embed)
        try:
            await ctx.guild.kick(member, reason=f"{ctx.author}: {reason}")
        except Forbidden:
            return await ctx.error(
                f"I don't have **permissions** to kick {member.mention}"
            )

        await self.invoke_message(ctx, ctx.check, user=member, reason=reason)
        await self.moderation_entry(ctx, member, "kick", reason)

    @command(
        name="unban",
        usage="(user) <reason>",
        example="igna forgiven",
    )
    @has_permissions(ban_members=True)
    async def unban(
        self,
        ctx: Context,
        user: User,
        *,
        reason: str = "No reason provided",
    ):
        """Unban a user from the server"""
        try:
            await ctx.guild.unban(user, reason=f"{ctx.author}: {reason}")
        except NotFound:
            return await ctx.error(f"Unable to find a ban for **{user}**")
        except Forbidden:
            return await ctx.error(f"I don't have **permissions** to unban **{user}**")

        await self.invoke_message(ctx, ctx.check, user=user, reason=reason)
        await self.moderation_entry(ctx, user, "unban", reason)

    @group(
        name="emoji",
        usage="(subcommand) <args>",
        invoke_without_command=True,
    )
    async def emoji(self, ctx: Context, *, emoji: EmojiFinder):
        """Enlarge an emoji"""
        response = await self.bot.session.request("GET", emoji.url)
        image = BytesIO(response)

        if emoji.id:
            if emoji.animated:
                return await ctx.error("I can't enlarge **animated emojis**")

            _image = Image.open(image)
            _image = _image.resize((_image.width * 5, _image.height * 5), Image.LANCZOS)
            image = BytesIO()
            _image.save(image, format="PNG")
            image.seek(0)

        await ctx.send(file=File(image, filename="emoji.png"))

    @emoji.command(
        name="add",
        usage="(emoji or url) <name>",
        example="cdn.drapp/emojis/473.png lol",
        aliases=["create", "copy"],
    )
    @has_permissions(manage_emojis=True)
    async def emoji_add(
        self,
        ctx: Context,
        emoji: DiscordEmoji | PartialEmoji | ImageFinder | int | None,
        *,
        name: str = None,
    ):
        """Add an emoji to the server"""
        if not emoji:
            try:
                emoji = await ImageFinder.search(ctx, history=False)
            except Exception:
                return await ctx.send_help()

        if isinstance(emoji, Emoji) and emoji.guild_id == ctx.guild.id:
            return await ctx.error("That **emoji** is already in this server")
        if type(emoji) in (Emoji, PartialEmoji):
            name = name or emoji.name
        elif isinstance(emoji, int):
            emoji = f"https://cdn.discordapp.com/emojis/{emoji}.png"

        if not name:
            return await ctx.error("Please **provide** a name for the emoji")

        if len(name) < 2:
            return await ctx.error("The emoji name must be **2 characters** or longer")
        name = name[:32].replace(" ", "_")

        response = await self.bot.session.get(
            emoji if isinstance(emoji, str) else emoji.url
        )
        image = await response.read()

        try:
            emoji = await ctx.guild.create_custom_emoji(
                name=name, image=image, reason=f"{ctx.author}: Emoji added"
            )
        except RateLimited as error:
            return await ctx.error(
                f"Please try again in **{error.retry_after:.2f} seconds**"
            )
        except HTTPException:
            if len(ctx.guild.emojis) == ctx.guild.emoji_limit:
                return await ctx.error(
                    f"The maximum amount of **emojis** has been reached (`{ctx.guild.emoji_limit}`)"
                )
            return await ctx.error(
                f"Failed to add [**{name}**]({response.url}) to the server"
            )

        await self.invoke_message(
            ctx,
            ctx.approve,
            f"Added [**{emoji.name}**]({emoji.url}) to the server",
            emoji=emoji,
        )

    @emoji.command(
        name="addmany",
        usage="(emojis)",
        example=":uhh: :erm:",
        aliases=["am"],
    )
    @has_permissions(manage_emojis=True)
    @max_concurrency(1, BucketType.guild)
    async def emoji_add_many(self, ctx: Context, *, emojis: str):
        """Bulk add emojis to the server"""
        emojis = list(
            {
                Emoji(
                    name=match.group("name"),
                    url="https://cdn.discordapp.com/emojis/"
                    + match.group("id")
                    + (".gif" if match.group("animated") else ".png"),
                    id=int(match.group("id")),
                    animated=bool(match.group("animated")),
                )
                for match in finditer(regex.DISCORD_EMOJI, emojis)
                if int(match.group("id"))
                not in (emoji.id for emoji in ctx.guild.emojis)
            }
        )
        if not emojis:
            return await ctx.send_help()

        emojis_added = []
        async with ctx.typing():
            for emoji in emojis:
                image = await emoji.read()
                try:
                    emoji = await ctx.guild.create_custom_emoji(
                        name=emoji.name,
                        image=image,
                        reason=f"{ctx.author}: Emoji added (bulk)",
                    )
                except RateLimited as error:
                    await ctx.error(
                        f"Rate limited for **{error.retry_after:.2f} seconds**"
                        + (f", stopping at {emojis_added[0]}" if emojis_added else "")
                    )
                    break
                except HTTPException:
                    await ctx.error(
                        f"Failed to add [**{emoji.name}**]({emoji.url}) to the server"
                    )
                    break
                else:
                    emojis_added.append(emoji)

        await self.invoke_message(
            ctx,
            ctx.approve,
            f"Added **{Plural(len(emojis_added)):emoji}** to the server",
            emojis=", ".join(str(emoji) for emoji in emojis_added),
        )

    @emoji.group(
        name="remove",
        usage="(emoji)",
        example=":uhh:",
        aliases=["delete", "del", "rm"],
        invoke_without_command=True,
    )
    @has_permissions(manage_emojis=True)
    async def emoji_remove(self, ctx: Context, *, emoji: DiscordEmoji):
        """Remove an emoji from the server"""
        if emoji.guild_id != ctx.guild.id:
            return await ctx.error("That **emoji** isn't in this server")

        await emoji.delete(reason=f"{ctx.author}: Emoji deleted")
        await self.invoke_message(
            ctx,
            ctx.approve,
            f"Removed [**{emoji.name}**]({emoji.url}) from the server",
            emoji=emoji,
        )

    @group(
        name="purge",
        usage="<user> (amount)",
        example="igna 15",
        aliases=["clear", "prune", "c"],
        invoke_without_command=True,
    )
    @has_permissions(manage_messages=True)
    async def purge(
        self,
        ctx: Context,
        user: Member | User | None = None,
        amount: int = None,
    ):
        """Purge a specified amount of messages"""
        if user and not amount:
            if user.name.isdigit():
                amount = int(user.name)
                user = None
            else:
                return await ctx.send_help()

        if not amount:
            return await ctx.send_help()
        amount = min(amount, 2000)

        def check(message: Message):
            if message.created_at < (utcnow() - timedelta(days=14)):
                return False

            return message.author.id == user.id if user else True

        with suppress(HTTPException):
            await ctx.message.delete()

        await ctx.channel.purge(
            limit=amount,
            check=check,
            before=ctx.message,
            bulk=True,
            reason=f"{ctx.author}: Purge",
        )

    @purge.command(
        name="after",
        usage="(message)",
        example="dscord.com/chnls/999/..",
        aliases=["upto", "to"],
    )
    @has_permissions(manage_messages=True)
    async def purge_after(
        self,
        ctx: Context,
        message: Message,
    ):
        """Purge messages after a specified message"""
        if message.channel != ctx.channel:
            return await ctx.error("That **message** isn't in this channel")

        def check(message: Message):
            return message.created_at >= utcnow() - timedelta(days=14)

        with suppress(HTTPException):
            await ctx.message.delete()

        await ctx.channel.purge(
            limit=300,
            check=check,
            after=message,
            before=ctx.message,
            bulk=True,
            reason=f"{ctx.author}: Purge after",
        )

    @purge.command(
        name="between",
        usage="(start message) (end message)",
        example="dscord.com/chnls/999/.. ../..",
        aliases=["inside", "btw", "bt"],
    )
    @has_permissions(manage_messages=True)
    async def purge_between(
        self,
        ctx: Context,
        start_message: Message,
        end_message: Message,
    ):
        """Purge messages between two specified messages"""
        if start_message.channel != ctx.channel:
            return await ctx.error("That **start message** isn't in this channel")
        if end_message.channel != ctx.channel:
            return await ctx.error("That **end message** isn't in this channel")

        def check(message: Message):
            return message.created_at >= utcnow() - timedelta(days=14)

        with suppress(HTTPException):
            await ctx.message.delete()

        await ctx.channel.purge(
            limit=300,
            check=check,
            after=start_message,
            before=end_message,
            bulk=True,
            reason=f"{ctx.author}: Purge between",
        )

    @purge.command(
        name="startswith",
        usage="(substring) <amount>",
        example="poop 15",
        aliases=["sw", "sws"],
    )
    @has_permissions(manage_messages=True)
    async def purge_startswith(
        self,
        ctx: Context,
        substring: str,
        amount: int = 15,
    ):
        """Purge a specified amount of messages that start with a substring"""
        amount = min(amount, 2000)

        def check(message: Message):
            if message.created_at < (utcnow() - timedelta(days=14)):
                return False

            return bool(
                message.content
                and message.content.lower().startswith(substring.lower())
            )

        with suppress(HTTPException):
            await ctx.message.delete()

        await ctx.channel.purge(
            limit=amount,
            check=check,
            before=ctx.message,
            bulk=True,
            reason=f"{ctx.author}: Purge startswith",
        )

    @purge.command(
        name="endswith",
        usage="(substring) <amount>",
        example="poop 15",
        aliases=["ew", "ews"],
    )
    @has_permissions(manage_messages=True)
    async def purge_endswith(
        self,
        ctx: Context,
        substring: str,
        amount: int = 15,
    ):
        """Purge a specified amount of messages that end with a substring"""
        amount = min(amount, 2000)

        def check(message: Message):
            if message.created_at < (utcnow() - timedelta(days=14)):
                return False

            return bool(
                message.content and message.content.lower().endswith(substring.lower())
            )

        with suppress(HTTPException):
            await ctx.message.delete()

        await ctx.channel.purge(
            limit=amount,
            check=check,
            before=ctx.message,
            bulk=True,
            reason=f"{ctx.author}: Purge endswith",
        )

    @purge.command(
        name="contains",
        usage="(substring) <amount>",
        example="poop 15",
        aliases=["contain", "c", "cs"],
    )
    @has_permissions(manage_messages=True)
    async def purge_contains(
        self,
        ctx: Context,
        substring: str,
        amount: int = 15,
    ):
        """Purge a specified amount of messages that contain a substring"""
        amount = min(amount, 2000)

        def check(message: Message):
            if message.created_at < (utcnow() - timedelta(days=14)):
                return False

            return bool(
                message.content and substring.lower() in message.content.lower()
            )

        with suppress(HTTPException):
            await ctx.message.delete()

        await ctx.channel.purge(
            limit=amount,
            check=check,
            before=ctx.message,
            bulk=True,
            reason=f"{ctx.author}: Purge contains",
        )

    @purge.command(
        name="emojis",
        usage="<amount>",
        example="15",
        aliases=["emoji", "emotes", "emote"],
    )
    @has_permissions(manage_messages=True)
    async def purge_emojis(self, ctx: Context, amount: int = 15):
        """Purge a specified amount of emoji messages"""
        amount = min(amount, 2000)

        def check(message: Message):
            if message.created_at < (utcnow() - timedelta(days=14)):
                return False

            return bool(message.emojis)

        with suppress(HTTPException):
            await ctx.message.delete()

        await ctx.channel.purge(
            limit=amount,
            check=check,
            before=ctx.message,
            bulk=True,
            reason=f"{ctx.author}: Purge",
        )

    @purge.command(
        name="stickers",
        usage="<amount>",
        example="15",
        aliases=["sticker"],
    )
    @has_permissions(manage_messages=True)
    async def purge_stickers(self, ctx: Context, amount: int = 15):
        """Purge a specified amount of sticker messages"""
        amount = min(amount, 2000)

        def check(message: Message):
            if message.created_at < (utcnow() - timedelta(days=14)):
                return False

            return message.stickers

        with suppress(HTTPException):
            await ctx.message.delete()

        await ctx.channel.purge(
            limit=amount,
            check=check,
            before=ctx.message,
            bulk=True,
            reason=f"{ctx.author}: Purge",
        )

    @purge.command(
        name="humans",
        usage="<amount>",
        example="15",
        aliases=["human"],
    )
    @has_permissions(manage_messages=True)
    async def purge_humans(self, ctx: Context, amount: int = 15):
        """Purge a specified amount of human messages"""
        amount = min(amount, 2000)

        def check(message: Message):
            if message.created_at < (utcnow() - timedelta(days=14)):
                return False

            return not message.author.bot

        with suppress(HTTPException):
            await ctx.message.delete()

        await ctx.channel.purge(
            limit=amount,
            check=check,
            before=ctx.message,
            bulk=True,
            reason=f"{ctx.author}: Purge humans",
        )

    @purge.command(
        name="bots",
        usage="<amount>",
        example="15",
        aliases=["bot"],
    )
    @has_permissions(manage_messages=True)
    async def purge_bots(self, ctx: Context, amount: int = 15):
        """Purge a specified amount of bot messages"""
        amount = min(amount, 2000)

        def check(message: Message):
            if message.created_at < (utcnow() - timedelta(days=14)):
                return False

            if message.content and message.content.startswith(
                (
                    ctx.prefix,
                    ",",
                    ".",
                    "!",
                    "?",
                    ";",
                    "?",
                    "$",
                    "-",
                )
            ):
                return True

            return message.author.bot

        with suppress(HTTPException):
            await ctx.message.delete()

        await ctx.channel.purge(
            limit=amount,
            check=check,
            before=ctx.message,
            bulk=True,
            reason=f"{ctx.author}: Purge bots",
        )

    @purge.command(
        name="embeds",
        usage="<amount>",
        example="15",
        aliases=["embed"],
    )
    @has_permissions(manage_messages=True)
    async def purge_embeds(self, ctx: Context, amount: int = 15):
        """Purge a specified amount of embeds"""
        amount = min(amount, 2000)

        def check(message: Message):
            if message.created_at < (utcnow() - timedelta(days=14)):
                return False

            return message.embeds

        with suppress(HTTPException):
            await ctx.message.delete()

        await ctx.channel.purge(
            limit=amount,
            check=check,
            before=ctx.message,
            bulk=True,
            reason=f"{ctx.author}: Purge embeds",
        )

    @purge.command(
        name="files",
        usage="<amount>",
        example="15",
        aliases=["file", "attachments", "attachment"],
    )
    @has_permissions(manage_messages=True)
    async def purge_files(self, ctx: Context, amount: int = 15):
        """Purge a specified amount of files"""
        amount = min(amount, 2000)

        def check(message: Message):
            if message.created_at < (utcnow() - timedelta(days=14)):
                return False

            return message.attachments

        with suppress(HTTPException):
            await ctx.message.delete()

        await ctx.channel.purge(
            limit=amount,
            check=check,
            before=ctx.message,
            bulk=True,
            reason=f"{ctx.author}: Purge files",
        )

    @purge.command(
        name="images",
        usage="<amount>",
        example="15",
        aliases=["image", "imgs", "img", "pics", "pic"],
    )
    @has_permissions(manage_messages=True)
    async def purge_images(self, ctx: Context, amount: int = 15):
        """Purge a specified amount of images"""
        amount = min(amount, 2000)

        def check(message: Message):
            if message.created_at < (utcnow() - timedelta(days=14)):
                return False

            if message.attachments:
                for attachment in message.attachments:
                    if str(attachment.content_type) in {
                        "image/png",
                        "image/jpeg",
                        "image/gif",
                        "image/webp",
                    }:
                        return True

            return False

        with suppress(HTTPException):
            await ctx.message.delete()

        await ctx.channel.purge(
            limit=amount,
            check=check,
            before=ctx.message,
            bulk=True,
            reason=f"{ctx.author}: Purge images",
        )

    @purge.command(
        name="links",
        usage="<amount>",
        example="15",
        aliases=["link"],
    )
    @has_permissions(manage_messages=True)
    async def purge_links(self, ctx: Context, amount: int = 15):
        """Purge a specified amount of links"""
        amount = min(amount, 2000)

        def check(message: Message):
            if message.created_at < (utcnow() - timedelta(days=14)):
                return False

            return bool(
                message.content
                and "http" in message.content
                or regex.DISCORD_INVITE.match(message.content)
            )

        with suppress(HTTPException):
            await ctx.message.delete()

        await ctx.channel.purge(
            limit=amount,
            check=check,
            before=ctx.message,
            bulk=True,
            reason=f"{ctx.author}: Purge links",
        )

    @purge.command(
        name="invites",
        usage="<amount>",
        example="15",
        aliases=["invite"],
    )
    @has_permissions(manage_messages=True)
    async def purge_invites(self, ctx: Context, amount: int = 15):
        """Purge a specified amount of invites"""
        amount = min(amount, 2000)

        def check(message: Message):
            if message.created_at < (utcnow() - timedelta(days=14)):
                return False

            return bool(message.content and regex.DISCORD_INVITE.match(message.content))

        with suppress(HTTPException):
            await ctx.message.delete()

        await ctx.channel.purge(
            limit=amount,
            check=check,
            before=ctx.message,
            bulk=True,
            reason=f"{ctx.author}: Purge invites",
        )

    @purge.command(
        name="mentions",
        usage="<amount>",
        example="15",
        aliases=["mention", "pings", "ping"],
    )
    @has_permissions(manage_messages=True)
    async def purge_mentions(self, ctx: Context, amount: int = 15):
        """Purge a specified amount of mentions"""
        amount = min(amount, 2000)

        def check(message: Message):
            if message.created_at < (utcnow() - timedelta(days=14)):
                return False

            return message.mentions

        with suppress(HTTPException):
            await ctx.message.delete()

        await ctx.channel.purge(
            limit=amount,
            check=check,
            before=ctx.message,
            bulk=True,
            reason=f"{ctx.author}: Purge mentions",
        )

    @group(
        name="role",
        usage="(member) (role)",
        example="igna @Administrator",
        invoke_without_command=True,
    )
    @has_permissions(manage_roles=True)
    async def role(
        self,
        ctx: Context,
        member: Member,
        *,
        roles: Roles,
    ):
        """Add or remove a role from a member"""
        await Member().hierarchy(ctx, member, author=True)
        await Roles().manageable(ctx, roles)
        await Roles().dangerous(ctx, roles)

        _roles_add, _roles_remove, _result = [], [], []
        for role in roles:
            if role not in member.roles:
                _roles_add.append(role)
            else:
                _roles_remove.append(role)

        if _roles_add:
            try:
                await member.add_roles(
                    *_roles_add,
                    reason=f"{ctx.author}: Role added",
                    atomic=False,
                )
            except Forbidden:
                return await ctx.error(
                    f"I don't have **permissions** to add {', '.join([role.mention for role in _roles_add])} to {member.mention}"
                )
            else:
                _result.extend(f"**+{role}**" for role in _roles_add)
        if _roles_remove:
            try:
                await member.remove_roles(
                    *_roles_remove,
                    reason=f"{ctx.author}: Role removed",
                    atomic=False,
                )
            except Forbidden:
                await ctx.error(
                    f"I don't have **permissions** to remove {', '.join([role.mention for role in _roles_remove])} from {member.mention}"
                )
            else:
                _result.extend(f"**-{role}**" for role in _roles_remove)

        if _result:
            if len(_result) > 1:
                return await self.invoke_message(
                    ctx,
                    ctx.approve,
                    f"Updated roles for {member.mention}: {' '.join(_result)}",
                    command="role multiple",
                    user=member,
                    roles=_result,
                )
            if _roles_add:
                return await self.invoke_message(
                    ctx,
                    ctx.approve,
                    f"Added {_roles_add[0].mention} to {member.mention}",
                    command="role add",
                    user=member,
                    role=_roles_add[0],
                )
            return await self.invoke_message(
                ctx,
                ctx.approve,
                f"Removed {_roles_remove[0].mention} from {member.mention}",
                command="role remove",
                user=member,
                role=_roles_remove[0],
            )

        return await ctx.error(f"{member.mention} already has all of those roles")

    @role.command(
        name="add",
        usage="(member) (role)",
        example="igna @Administrator",
        aliases=["grant"],
    )
    @has_permissions(manage_roles=True)
    async def role_add(
        self,
        ctx: Context,
        member: Member,
        *,
        role: Role,
    ):
        """Add a role to a member"""
        await Member().hierarchy(ctx, member, author=True)
        await Role().manageable(ctx, role)
        await Role().dangerous(ctx, role)

        if role not in member.roles:
            try:
                await member.add_roles(role, reason=f"{ctx.author}: Role added")
            except Forbidden:
                await ctx.error(
                    f"I don't have **permissions** to add {role.mention} to {member.mention}"
                )
            else:
                return await self.invoke_message(
                    ctx,
                    ctx.approve,
                    f"Added {role.mention} to {member.mention}",
                    user=member,
                    role=role,
                )

        return await ctx.error(f"{member.mention} already has {role.mention}")

    @role.command(
        name="remove",
        usage="(member) (role)",
        example="igna @Administrator",
        aliases=["revoke"],
    )
    @has_permissions(manage_roles=True)
    async def role_remove(
        self,
        ctx: Context,
        member: Member,
        *,
        role: Role,
    ):
        """Remove a role from a member"""
        await Member().hierarchy(ctx, member, author=True)
        await Role().manageable(ctx, role)
        await Role().dangerous(ctx, role)

        if role in member.roles:
            try:
                await member.remove_roles(role, reason=f"{ctx.author}: Role removed")
            except Forbidden:
                await ctx.error(
                    f"I don't have **permissions** to remove {role.mention} from {member.mention}"
                )

            return await self.invoke_message(
                ctx,
                ctx.approve,
                f"Removed {role.mention} from {member.mention}",
                user=member,
                role=role,
            )

        return await ctx.error(f"{member.mention} doesn't have {role.mention}")

    @role.command(
        name="multiple",
        usage="(member) (roles)",
        example="igna @Administrator @Moderator",
        aliases=["multi"],
    )
    @has_permissions(manage_roles=True)
    async def role_multiple(
        self,
        ctx: Context,
        member: Member,
        *,
        roles: Roles,
    ):
        """Add or remove multiple roles from a member"""
        await ctx.command.parent.command(ctx, member=member, roles=roles)

    @role.command(
        name="create",
        usage="(name)",
        example="Member",
        aliases=["new"],
    )
    @has_permissions(manage_roles=True)
    async def role_create(self, ctx: Context, *, name: str):
        """Create a role"""
        role = await ctx.guild.create_role(
            name=name, reason=f"{ctx.author}: Role created"
        )
        await self.invoke_message(
            ctx, ctx.approve, f"Created {role.mention}", role=role
        )

    @role.command(
        name="delete",
        usage="(role)",
        example="@Member",
        aliases=["del"],
    )
    @has_permissions(manage_roles=True)
    async def role_delete(self, ctx: Context, *, role: Role):
        """Delete a role"""
        await Role().manageable(ctx, role)

        await role.delete(reason=f"{ctx.author}: Role deleted")
        await self.invoke_message(
            ctx, ctx.approve, f"Deleted **{role.name}**", role=role
        )

    @role.command(
        name="color",
        usage="(role) (color)",
        example="@Member #ff0000",
        aliases=["colour"],
    )
    @has_permissions(manage_roles=True)
    async def role_color(self, ctx: Context, role: Role, *, color: Color):
        """Change the color of a role"""
        await Role().manageable(ctx, role, booster=True)

        await role.edit(color=color, reason=f"{ctx.author}: Role color changed")
        await self.invoke_message(
            ctx,
            ctx.approve,
            f"Changed the color of {role.mention} to `{color}`",
            role=role,
            color=color,
        )

    @role.command(
        name="name",
        usage="(role) (name)",
        example="@Member Guest",
        aliases=["rename"],
    )
    @has_permissions(manage_roles=True)
    async def role_name(self, ctx: Context, role: Role, *, name: str):
        """Change the name of a role"""
        await Role().manageable(ctx, role, booster=True)

        await role.edit(name=name, reason=f"{ctx.author}: Role name changed")
        await self.invoke_message(
            ctx,
            ctx.approve,
            f"Changed the name of {role.mention} to `{name}`",
            role=role,
            name=name,
        )

    @role.command(
        name="icon",
        usage="(role) (icon)",
        example="@Member 🦅",
        aliases=["emoji"],
    )
    @has_permissions(manage_roles=True)
    async def role_icon(
        self,
        ctx: Context,
        role: Role,
        *,
        icon: Literal["remove", "reset", "off"] | EmojiFinder | ImageFinder = None,
    ):
        """Change the icon of a role"""
        await Role().manageable(ctx, role, booster=True)

        if "ROLE_ICONS" not in ctx.guild.features:
            return await ctx.error(
                "This server doesn't have enough **boosts** to use **role icons**"
            )
        if not icon:
            icon = await ImageFinder.search(ctx)
        elif isinstance(icon, str) and icon in ("remove", "reset", "off"):
            icon = None

        _icon = None
        if type(icon) in (Emoji, str):
            _icon = await self.bot.session.request(
                "GET", icon.url if isinstance(icon, Emoji) else icon
            )
        elif not role.display_icon:
            return await ctx.error(f"**{role.name}** doesn't have an icon")

        await role.edit(display_icon=_icon, reason=f"{ctx.author}: Role icon changed")
        if icon:
            return await ctx.approve(
                f"Changed the icon of {role.mention} to {f'{icon}' if isinstance(icon, Emoji) else f'[**image**]({icon})'}"
            )

        return await ctx.approve(f"Removed the icon of {role.mention}")

    @role.command(
        name="hoist",
        usage="(role)",
        example="@Member",
        aliases=["display"],
    )
    @has_permissions(manage_roles=True)
    async def role_hoist(self, ctx: Context, *, role: Role):
        """Toggle if a role is hoisted"""
        await Role().manageable(ctx, role, booster=True)

        await role.edit(
            hoist=not role.hoist, reason=f"{ctx.author}: Role hoist toggled"
        )
        await self.invoke_message(
            ctx,
            ctx.approve,
            f"{'Now hoisting' if role.hoist else 'No longer hoisting'} {role.mention}",
            role=role,
            hoist=role.hoist,
        )

    @role.command(
        name="mentionable",
        usage="(role)",
        example="@Member",
        aliases=["mention"],
    )
    @has_permissions(manage_roles=True, mention_everyone=True)
    async def role_mentionable(self, ctx: Context, *, role: Role):
        """Toggle if a role is mentionable"""
        await Role().manageable(ctx, role, booster=True)

        await role.edit(
            mentionable=not role.mentionable,
            reason=f"{ctx.author}: Role mentionable toggled",
        )
        await self.invoke_message(
            ctx,
            ctx.approve,
            f"{'Now allowing' if role.mentionable else 'No longer allowing'} {role.mention} to be mentioned",
            role=role,
            mentionable=role.mentionable,
        )

    @command(
        name="moveall",
        usage="(voice channel)",
        example="#voice",
        aliases=["mvall"],
    )
    @has_permissions(manage_channels=True)
    @max_concurrency(1, BucketType.member)
    @cooldown(1, 10, BucketType.member)
    async def move(
        self,
        ctx: Context,
        *,
        channel: VoiceChannel,
    ):
        """Move all members to another voice channel"""
        if not ctx.author.voice:
            return await ctx.error("You're not **connected** to a voice channel")
        if not channel.permissions_for(ctx.author).connect:
            return await ctx.error(
                "You don't have **permission** to connect to that channel"
            )
        if ctx.author.voice.channel == channel:
            return await ctx.error("You're already **connected** to that channel")

        tasks = [member.move_to(channel) for member in ctx.author.voice.channel.members]
        async with ctx.typing():
            moved = await gather(*tasks)
            await ctx.approve(f"Moved **{Plural(moved):member}** to {channel.mention}")

    @command(
        name="hide",
        usage="<channel> <reason>",
        example="#chat",
        aliases=["private", "priv"],
    )
    @has_permissions(manage_channels=True)
    async def hide(
        self,
        ctx: Context,
        channel: TextChannel | None = None,
        *,
        reason: str = "No reason provided",
    ):
        """Hide a channel from regular members"""
        channel = channel or ctx.channel

        if channel.overwrites_for(ctx.guild.default_role).read_messages is False:
            return await ctx.error(f"The channel {channel.mention} is already hidden")

        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.read_messages = False
        await channel.set_permissions(
            ctx.guild.default_role,
            overwrite=overwrite,
            reason=f"{ctx.author}: {reason}",
        )

        await self.invoke_message(
            ctx,
            ctx.approve,
            f"Set channel {channel.mention} as hidden",
            channel=channel,
            reason=reason,
        )
        await self.moderation_entry(ctx, channel, "hide", reason)

    @command(
        name="reveal",
        usage="<channel> <reason>",
        example="#chat",
        aliases=["unhide", "public"],
    )
    @has_permissions(manage_channels=True)
    async def unhide(
        self,
        ctx: Context,
        channel: TextChannel | None = None,
        *,
        reason: str = "No reason provided",
    ):
        """Reveal a channel to regular members"""
        channel = channel or ctx.channel

        if channel.overwrites_for(ctx.guild.default_role).read_messages is True:
            return await ctx.error(f"The channel {channel.mention} isn't hidden")

        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.read_messages = True
        await channel.set_permissions(
            ctx.guild.default_role,
            overwrite=overwrite,
            reason=f"{ctx.author}: {reason}",
        )

        await self.invoke_message(
            ctx,
            ctx.approve,
            f"Revealed channel {channel.mention}",
            channel=channel,
            reason=reason,
        )
        await self.moderation_entry(ctx, channel, "reveal", reason)

    @group(
        name="lockdown",
        usage="<channel> <reason>",
        example="#chat spamming",
        aliases=["lock"],
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def lockdown(
        self,
        ctx: Context,
        channel: TextChannel | None = None,
        *,
        reason: str = "No reason provided",
    ):
        """Prevent regular members from typing"""
        channel = channel or ctx.channel

        if channel.overwrites_for(ctx.guild.default_role).send_messages is False:
            return await ctx.error(f"The channel {channel.mention} is already locked")

        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await channel.set_permissions(
            ctx.guild.default_role,
            overwrite=overwrite,
            reason=f"{ctx.author}: {reason}",
        )

        await self.invoke_message(
            ctx,
            ctx.approve,
            f"Locked channel {channel.mention}",
            channel=channel,
            reason=reason,
        )
        await self.moderation_entry(ctx, channel, "lockdown", reason)

    @lockdown.command(
        name="all",
        usage="<reason>",
    )
    @has_permissions(manage_channels=True)
    @max_concurrency(1, per=BucketType.guild)
    @cooldown(1, 60, BucketType.guild)
    async def lockdown_all(self, ctx: Context, *, reason: str = "No reason provided"):
        """Prevent regular members from typing in all channels"""
        ignored_channels = (
            await self.bot.fetch_config(ctx.guild.id, "lock_ignore") or []
        )
        if not ignored_channels:
            await ctx.prompt(
                f"Are you sure you want to lock all channels?\n> You haven't set any ignored channels with `{ctx.prefix}lock ignore` yet"
            )

        async with ctx.typing():
            for channel in ctx.guild.text_channels:
                if (
                    channel.overwrites_for(ctx.guild.default_role).send_messages
                    is False
                    or channel.id in ignored_channels
                ):
                    continue

                overwrite = channel.overwrites_for(ctx.guild.default_role)
                overwrite.send_messages = False
                await channel.set_permissions(
                    ctx.guild.default_role,
                    overwrite=overwrite,
                    reason=f"{ctx.author}: {reason} (lockdown all)",
                )

            await self.invoke_message(
                ctx, ctx.approve, "Locked all channels", reason=reason
            )
            await self.moderation_entry(ctx, ctx.guild, "lockdown all", reason)

    @lockdown.group(
        name="ignore",
        usage="(subcommand) <args>",
        example="add #psa",
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def lockdown_ignore(self, ctx: Context):
        """Prevent channels from being altered"""
        await ctx.send_help()

    @lockdown_ignore.command(
        name="add",
        usage="(channel)",
        example="#psa",
        aliases=["create"],
    )
    @has_permissions(manage_channels=True)
    async def lockdown_ignore_add(self, ctx: Context, *, channel: TextChannel):
        """Add a channel to the ignore list"""
        ignored_channels = (
            await self.bot.fetch_config(ctx.guild.id, "lock_ignore") or []
        )
        if channel.id in ignored_channels:
            return await ctx.error(f"{channel.mention} is already ignored")

        ignored_channels.append(channel.id)
        await self.bot.update_config(ctx.guild.id, "lock_ignore", ignored_channels)

        await ctx.approve(f"Now ignoring {channel.mention}")

    @lockdown_ignore.command(
        name="remove",
        usage="(channel)",
        example="#psa",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_channels=True)
    async def lockdown_ignore_remove(self, ctx: Context, *, channel: TextChannel):
        """Remove a channel from the ignore list"""
        ignored_channels = (
            await self.bot.fetch_config(ctx.guild.id, "lock_ignore") or []
        )
        if channel.id not in ignored_channels:
            return await ctx.error(f"{channel.mention} isn't ignored")

        ignored_channels.remove(channel.id)
        await self.bot.update_config(ctx.guild.id, "lock_ignore", ignored_channels)

        await ctx.approve(f"No longer ignoring {channel.mention}")

    @lockdown_ignore.command(
        name="list",
        aliases=["show", "all"],
    )
    @has_permissions(manage_channels=True)
    async def lockdown_ignore_list(self, ctx: Context):
        """List all ignored channels"""
        channels = [
            ctx.guild.get_channel(channel_id).mention
            for channel_id in await self.bot.fetch_config(ctx.guild.id, "lock_ignore")
            or []
            if ctx.guild.get_channel(channel_id)
        ]
        if not channels:
            return await ctx.error("No **ignored channels** have been set up")

        await ctx.paginate(
            Embed(
                title="Ignored Channels",
                description="\n".join(channels),
            )
        )

    @group(
        name="unlockdown",
        usage="<channel> <reason>",
        example="#chat behave",
        aliases=["unlock"],
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def unlockdown(
        self,
        ctx: Context,
        channel: TextChannel | None = None,
        *,
        reason: str = "No reason provided",
    ):
        """Allow regular members to type"""
        channel = channel or ctx.channel

        if channel.overwrites_for(ctx.guild.default_role).send_messages is True:
            return await ctx.error(f"The channel {channel.mention} isn't locked")

        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = True
        await channel.set_permissions(
            ctx.guild.default_role,
            overwrite=overwrite,
            reason=f"{ctx.author}: {reason}",
        )

        await self.invoke_message(
            ctx,
            ctx.approve,
            f"Unlocked channel {channel.mention}",
            channel=channel,
            reason=reason,
        )
        await self.moderation_entry(ctx, channel, "unlockdown", reason)

    @unlockdown.command(
        name="all",
        usage="<reason>",
        example="raid over",
    )
    @has_permissions(manage_channels=True)
    @max_concurrency(1, per=BucketType.guild)
    @cooldown(1, 60, BucketType.guild)
    async def unlockdown_all(self, ctx: Context, *, reason: str = "No reason provided"):
        """Allow regular members to type in all channels"""
        ignored_channels = (
            await self.bot.fetch_config(ctx.guild.id, "lock_ignore") or []
        )
        if not ignored_channels:
            await ctx.prompt(
                f"Are you sure you want to unlock all channels?\n> You haven't set any ignored channels with `{ctx.prefix}lock ignore` yet"
            )

        async with ctx.typing():
            for channel in ctx.guild.text_channels:
                if (
                    channel.overwrites_for(ctx.guild.default_role).send_messages is True
                    or channel.id in ignored_channels
                ):
                    continue

                overwrite = channel.overwrites_for(ctx.guild.default_role)
                overwrite.send_messages = True
                await channel.set_permissions(
                    ctx.guild.default_role,
                    overwrite=overwrite,
                    reason=f"{ctx.author}: {reason} (unlockdown all)",
                )

            await self.invoke_message(
                ctx, ctx.approve, "Unlocked all channels", reason=reason
            )
            await self.moderation_entry(ctx, ctx.guild, "unlockdown all", reason)

    @group(
        name="slowmode",
        usage="<channel> (delay time)",
        example="#chat 10s",
        aliases=["slowmo", "slow"],
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def slowmode(
        self,
        ctx: Context,
        channel: TextChannel | None,
        *,
        delay: TimeConverter,
    ):
        """Set the slowmode delay for a channel"""
        channel = channel or ctx.channel

        if channel.slowmode_delay == delay.seconds:
            return await ctx.error(
                f"The slowmode for {channel.mention} is already set to **{delay}**"
            )

        try:
            await channel.edit(slowmode_delay=delay.seconds)
        except HTTPException:
            return await ctx.error(
                f"Coudn't set the slowmode for {channel.mention} to **{delay}**"
            )

        if delay.seconds:
            return await ctx.approve(
                f"Set the slowmode for {channel.mention} to **{delay}**"
            )

        return await ctx.approve(f"Disabled slowmode for {channel.mention}")

    @slowmode.command(
        name="disable",
        usage="<channel>",
        example="#chat",
        aliases=["off"],
    )
    @has_permissions(manage_channels=True)
    async def slowmode_disable(self, ctx: Context, channel: TextChannel | None):
        """Disable slowmode for a channel"""
        channel = channel or ctx.channel

        if not channel.slowmode_delay:
            return await ctx.error(
                f"The slowmode for {channel.mention} is already **disabled**"
            )

        await channel.edit(slowmode_delay=0)
        await ctx.approve(f"Disabled slowmode for {channel.mention}")

    @command(
        name="nsfw",
        usage="<channel>",
        example="#chat",
        aliases=["naughty"],
    )
    @has_permissions(manage_channels=True)
    async def nsfw(self, ctx: Context, channel: TextChannel = None):
        """Temporarily mark a channel as NSFW"""
        channel = channel or ctx.channel

        if channel.is_nsfw():
            return await ctx.error(
                f"The channel {channel.mention} is already marked as **NSFW**"
            )

        await channel.edit(nsfw=True)
        await ctx.approve(
            f"Temporarily marked {channel.mention} as **NSFW** for **60 seconds**"
        )

        await sleep(60)
        await channel.edit(nsfw=False)

    @group(
        name="sticker",
        usage="(subcommand) <args>",
        example="add dscord.com/chnls/999/.. mommy",
        invoke_without_command=True,
    )
    @has_permissions(manage_emojis=True)
    async def sticker(self, ctx: Context):
        """Manage stickers in the server"""
        await ctx.send_help()

    @sticker.command(
        name="add",
        usage="(image or url) <name>",
        example="dscord.com/chnls/999/.. mommy",
        aliases=["create", "copy"],
    )
    @has_permissions(manage_emojis=True)
    async def sticker_add(
        self,
        ctx: Context,
        image: StickerFinder | ImageFinderStrict | None,
        *,
        name: str = None,
    ):
        """Add a sticker to the server"""
        if not image:
            try:
                image = await StickerFinder.search(ctx)
            except Exception:
                try:
                    image = await ImageFinder.search(ctx, history=False)
                except Exception:
                    return await ctx.send_help()

        if isinstance(image, GuildSticker):
            if image.guild_id == ctx.guild.id:
                return await ctx.error("That **sticker** is already in this server")
            name = name or image.name
            image = image.url

        if not name:
            return await ctx.error("Please provide a **name** for the sticker")
        name = name[:30]

        if match := regex.DISCORD_ATTACHMENT.match(image):
            if match.group("mime") not in ("png", "jpg", "jpeg", "webp"):
                return await ctx.error("Invalid **image** type")
            with TemporaryDirectory() as temp_dir:
                try:
                    terminal = await wait_for(
                        create_subprocess_shell(
                            f"cd {temp_dir} && ffmpeg -i {image} -vf scale=320:320 image.png -nostats -loglevel 0"
                        ),
                        timeout=25,
                    )
                    stdout, stderr = await terminal.communicate()
                except TimeoutError:
                    return await ctx.error(
                        f"Couldn't converter [**image**]({image}) to a **png** - Timeout"
                    )

                if not os.path.exists(f"{temp_dir}/image.png"):
                    return await ctx.error(
                        f"Couldn't converter [**image**]({image}) to a **png**"
                    )

                image = File(
                    f"{temp_dir}/image.png",
                )
        else:
            response = await self.bot.session.get(image)
            if response.status != 200:
                return await ctx.error("Invalid **image** url")

            image = File(
                BytesIO(await response.read()),
            )

        try:
            sticker = await ctx.guild.create_sticker(
                name=name,
                description=name,
                emoji="🤔",
                file=image,
                reason=f"{ctx.author}: Sticker added",
            )
        except HTTPException:
            if len(ctx.guild.stickers) == ctx.guild.sticker_limit:
                return await ctx.error(
                    f"The maximum amount of **stickers** has been reached (`{ctx.guild.sticker_limit}`)"
                )
            return await ctx.error("Failed to add **sticker** to the server")

        await self.invoke_message(
            ctx,
            ctx.approve,
            f"Added [**{sticker.name}**]({sticker.url}) to the server",
            sticker=sticker,
        )

    @sticker.command(
        name="remove",
        usage="(sticker)",
        example="mommy",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_emojis=True)
    async def sticker_remove(
        self,
        ctx: Context,
        *,
        sticker: StickerFinder = None,
    ):
        """Remove a sticker from the server"""
        if not sticker:
            try:
                sticker = await StickerFinder.search(ctx)
            except Exception:
                return await ctx.send_help()

        if sticker.guild_id != ctx.guild.id:
            return await ctx.error("That **sticker** isn't in this server")

        await sticker.delete(reason=f"{ctx.author}: Sticker deleted")
        await self.invoke_message(
            ctx,
            ctx.approve,
            f"Removed [**{sticker.name}**]({sticker.url}) from the server",
            sticker=sticker,
        )

    @sticker.command(
        name="rename",
        usage="(sticker) (name)",
        example="yeat indian",
        aliases=["name"],
    )
    @has_permissions(manage_emojis=True)
    async def sticker_rename(
        self,
        ctx: Context,
        sticker: StickerFinder | None,
        *,
        name: str,
    ):
        """Rename a sticker in the server"""
        if not sticker:
            try:
                sticker = await StickerFinder.search(ctx)
            except Exception:
                return await ctx.send_help()

        if sticker.guild_id != ctx.guild.id:
            return await ctx.error("That **sticker** isn't in this server")

        name = name[:30]
        _sticker = sticker
        await _sticker.edit(name=name, reason=f"{ctx.author}: Sticker renamed")
        await self.invoke_message(
            ctx,
            ctx.approve,
            f"Renamed [**{sticker.name}**]({sticker.url}) to **{name}**",
            sticker=sticker,
            name=name,
        )

    @sticker.command(
        name="list",
        aliases=["all"],
    )
    async def sticker_list(self, ctx: Context):
        """View all stickers in the server"""
        await self.bot.get_command("stickers")(ctx)

    @command(
        name="cleanup",
        usage="<amount>",
        example="15",
        aliases=["botcleanup", "bcleanup", "bclean", "botclean"],
    )
    @has_permissions(manage_messages=True)
    async def cleanup(
        self,
        ctx: Context,
        amount: int = 50,
    ):
        """Clean up messages from rei"""
        amount = min(amount, 2000)

        def check(message: Message):
            if message.created_at < (utcnow() - timedelta(days=14)):
                return False

            if message.content and message.content.startswith(ctx.prefix):
                return True

            return message.author == self.bot.user or message.webhook_id is not None

        with suppress(HTTPException):
            await ctx.message.delete()

        await ctx.channel.purge(
            limit=amount,
            check=check,
            before=ctx.message,
            bulk=True,
            reason=f"{ctx.author}: Cleanup",
        )
