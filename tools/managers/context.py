from contextlib import suppress
from copy import copy
from io import BytesIO, StringIO
from typing import TYPE_CHECKING, Any

from discord import (Embed, File, Guild, HTTPException, Member, Message,
                     NotFound)
from discord.ext.commands import Command, CommandError
from discord.ext.commands import Context as BaseContext
from discord.ext.commands import FlagConverter as DefaultFlagConverter
from discord.ext.commands import Group, UserInputError
from discord.utils import cached_property

import config
from tools.managers.cache import cache
from tools.utilities.checks import donator

from ..utilities.text import shorten
from ..utilities.typing import Typing
from . import views
from .paginator import Paginator

if TYPE_CHECKING:
    from tools.rei import rei


class Context(BaseContext):
    bot: "rei"
    guild: Guild

    @cached_property
    def parameters(self):
        data = {}
        if command := self.command:
            if parameters := command.parameters:
                for name, parameter in parameters.items():
                    data[name] = ParameterParser(self).get(name, **parameter)

        return data

    def typing(self) -> Typing:
        return Typing(self)

    @cache(ttl="1m", key="{self.message.id}", prefix="reskin")
    async def reskin(self):
        try:
            await donator().predicate(self)
        except Exception:
            pass
        else:
            configuration = await self.bot.fetch_config(self.guild.id, "reskin") or {}
            if configuration.get("status"):
                if webhook_id := configuration["webhooks"].get(str(self.channel.id)):
                    reskin = await self.bot.db.fetchrow(
                        "SELECT username, avatar_url, colors, emojis FROM reskin WHERE user_id = $1",
                        self.author.id,
                    )
                    if reskin and (reskin.get("username") or reskin.get("avatar_url")):
                        webhook = await self.channel.reskin_webhook(webhook_id)
                        if webhook:
                            return {
                                "username": reskin.get("username")
                                or self.bot.user.name,
                                "avatar_url": reskin.get("avatar_url")
                                or self.bot.user.display_avatar.url,
                                "colors": reskin.get("colors", {}),
                                "emojis": reskin.get("emojis", {}),
                                "webhook": webhook,
                            }

                        del configuration["webhooks"][str(self.channel.id)]
                        await self.bot.update_config(
                            self.guild.id, "reskin", configuration
                        )
        return {}

    @cached_property
    def replied_message(self) -> Message:
        if (reference := self.message.reference) and isinstance(
            reference.resolved, Message
        ):
            return reference.resolved

    async def send(self, *args, **kwargs):
        reskin = await self.reskin()
        kwargs["files"] = kwargs.get("files") or []
        if file := kwargs.pop("file", None):
            kwargs["files"].append(file)

        if embed := kwargs.get("embed"):
            if not embed.color:
                embed.color = (
                    reskin.get("colors", {}).get("main") or config.Color.neutral
                )
            if (
                embed.title
                and not embed.author
                and self.command.qualified_name not in ("nowplaying", "createembed")
            ):
                embed.set_author(
                    name=self.author.display_name,
                    icon_url=self.author.display_avatar,
                )
            if embed.title:
                embed.title = shorten(embed.title, 256)
            if embed.description:
                embed.description = shorten(embed.description, 4096)
            for field in embed.fields:
                embed.set_field_at(
                    index=embed.fields.index(field),
                    name=field.name,
                    value=field.value[:1024],
                    inline=field.inline,
                )
            if hasattr(embed, "_attachments") and embed._attachments:
                for attachment in embed._attachments:
                    if isinstance(attachment, File):
                        kwargs["files"].append(
                            File(
                                copy(attachment.fp),
                                filename=attachment.filename,
                            )
                        )
                    elif isinstance(attachment, tuple):
                        response = await self.bot.session.get(attachment[0])
                        if response.status == 200:
                            kwargs["files"].append(
                                File(
                                    BytesIO(await response.read()),
                                    filename=attachment[1],
                                )
                            )

        if embeds := kwargs.get("embeds"):
            for embed in embeds:
                if not embed.color:
                    embed.color = (
                        reskin.get("colors", {}).get("main") or config.Color.neutral
                    )
                if (
                    embed.title
                    and not embed.author
                    and self.command.qualified_name not in ("nowplaying", "createembed")
                ):
                    embed.set_author(
                        name=self.author.display_name,
                        icon_url=self.author.display_avatar,
                    )
                if embed.title:
                    embed.title = shorten(embed.title, 256)
                if embed.description:
                    embed.description = shorten(embed.description, 4096)
                for field in embed.fields:
                    embed.set_field_at(
                        index=embed.fields.index(field),
                        name=field.name,
                        value=field.value[:1024],
                        inline=field.inline,
                    )
                if hasattr(embed, "_attachments") and embed._attachments:
                    for attachment in embed._attachments:
                        if isinstance(attachment, File):
                            kwargs["files"].append(
                                File(
                                    copy(attachment.fp),
                                    filename=attachment.filename,
                                )
                            )
                        elif isinstance(attachment, tuple):
                            response = await self._state._get_client().session.get(
                                attachment[0]
                            )
                            if response.status == 200:
                                kwargs["files"].append(
                                    File(
                                        BytesIO(await response.read()),
                                        filename=attachment[1],
                                    )
                                )

        if content := (args[0] if args else kwargs.get("content")):
            content = str(content)
            if len(content) > 4000:
                kwargs[
                    "content"
                ] = f"Response too large to send (`{len(content)}/4000`)"
                kwargs["files"].append(
                    File(
                        StringIO(content),
                        filename="reiResult.txt",
                    )
                )
                if args:
                    args = args[1:]

        # Override the send function with a webhook for reskin..
        if reskin:
            webhook = reskin["webhook"]
            kwargs["username"] = reskin["username"]
            kwargs["avatar_url"] = reskin["avatar_url"]
            kwargs["wait"] = True

            delete_after = kwargs.pop("delete_after", None)
            kwargs.pop("stickers", None)
            kwargs.pop("reference", None)
            kwargs.pop("followup", None)

            try:
                message = await webhook.send(*args, **kwargs)
            except NotFound:
                reskin = await self.bot.fetch_config(self.guild.id, "reskin") or {}
                del reskin["webhooks"][str(self.channel.id)]
                await self.bot.update_config(self.guild.id, "reskin", reskin)
                await cache.delete_many(
                    f"reskin:channel:{self.channel.id}",
                    f"reskin:webhook:{self.channel.id}",
                )
            except HTTPException as error:
                raise error
            else:
                if delete_after:
                    await message.delete(delay=delete_after)

                return message

        return await super().send(*args, **kwargs)

    async def send_help(self, command: Command | Group = None):
        command_obj: Command | Group = command or self.command

        embeds = []
        for command in [command_obj] + (
            list(command_obj.walk_commands()) if isinstance(command_obj, Group) else []
        ):
            embed = Embed(
                color=config.Color.neutral,
                title=(
                    ("Group Command: " if isinstance(command, Group) else "Command: ")
                    + command.qualified_name
                ),
                description=command.help,
            )

            embed.add_field(
                name="Aliases",
                value=(", ".join(command.aliases) if command.aliases else "N/A"),
                inline=True,
            )
            embed.add_field(
                name="Parameters",
                value=(
                    ", ".join(command.clean_params) if command.clean_params else "N/A"
                ),
                inline=True,
            )

            embed.add_field(
                name="Usage",
                value=(
                    f"```\nSyntax: {self.prefix}{command.qualified_name} {command.usage or ''}"
                    + (
                        f"\nExample: {self.prefix}{command.qualified_name} {command.example}"
                        if command.example
                        else ""
                    )
                    + "```"
                ),
                inline=False,
            )
            embed.set_footer(
                text=(
                    f"Module: {command.cog_name}" if command.cog_name else "Module: N/A"
                ),
            )

            embeds.append(embed)

        await self.paginate(embeds)

    async def neutral(
        self: "Context",
        description: str,
        emoji: str = "",
        color=config.Color.neutral,
        **kwargs: Any,
    ) -> Message:
        """Send a neutral embed."""
        reskin = await self.reskin()
        color = reskin.get("colors", {}).get("main") or kwargs.pop(
            "color", config.Color.neutral
        )

        sign = "> " if "\n>" not in description else ""
        embed = Embed(
            description=f"{sign} {emoji} {self.author.mention}: {description}",
            color=color,
            **kwargs,
        )

        if previous_load := getattr(self, "previous_load", None):
            cancel_load = kwargs.pop("cancel_load", False)
            result = await previous_load.edit(embed=embed, **kwargs)
            if cancel_load:
                delattr(self, "previous_load")
            return result

        return await self.send(embed=embed, **kwargs)

    async def approve(
        self: "Context",
        description: str,
        emoji: str = "",
        **kwargs: Any,
    ) -> Message:
        """Send an approve embed."""
        reskin = await self.reskin()
        color = reskin.get("colors", {}).get("main") or kwargs.pop(
            "color", config.Color.approval
        )

        sign = "> " if "\n>" not in description else ""
        embed = Embed(
            description=f"{sign} {self.author.mention}: {description}",
            color=color,
            **kwargs,
        )
        if previous_load := getattr(self, "previous_load", None):
            cancel_load = kwargs.pop("cancel_load", False)
            result = await previous_load.edit(embed=embed, **kwargs)
            if cancel_load:
                delattr(self, "previous_load")
            return result

        return await self.send(embed=embed, **kwargs)

    async def error(
        self: "Context",
        description: str,
        **kwargs: Any,
    ) -> Message:
        """Send an error embed."""
        reskin = await self.reskin()
        color = reskin.get("colors", {}).get("main") or kwargs.pop(
            "color", config.Color.error
        )
        sign = "> " if "\n>" not in description else ""
        embed = Embed(
            description=f"{sign} {self.author.mention}: {description}",
            color=color,
            **kwargs,
        )
        if previous_load := getattr(self, "previous_load", None):
            cancel_load = kwargs.pop("cancel_load", False)
            result = await previous_load.edit(embed=embed, **kwargs)
            if cancel_load:
                delattr(self, "previous_load")
            return result

        return await self.send(embed=embed, **kwargs)

    async def load(self, message: str, emoji: str = "", **kwargs: Any):
        """Send a loading embed."""
        reskin = await self.reskin()
        color = reskin.get("colors", {}).get("load") or kwargs.pop(
            "color", config.Color.neutral
        )
        sign = "> " if "\n>" not in message else ""
        embed = Embed(
            color=color,
            description=f"{sign} {message}",
        )
        if not getattr(self, "previous_load", None):
            message = await self.send(embed=embed, **kwargs)
            setattr(self, "previous_load", message)
            return self.previous_load

        await self.previous_load.edit(embed=embed, **kwargs)
        return self.previous_load

    async def paginate(
        self,
        data: Embed | list[Embed | str],
        display_entries: bool = True,
        text: str = "entry|entries",
        of_text: str = None,
    ) -> Message:
        if isinstance(data, Embed):
            embed: Embed = data.copy()
            if description := data.description:
                embed.description = "\n".join(
                    [
                        (f"`{index + 1}` " if display_entries else "") + line.strip()
                        for index, line in enumerate(description.split("\n"))
                    ]
                )
            data = [embed]
        else:
            len(data)

        if isinstance(data[0], Embed):
            paginator = Paginator(self, data)
            for page, embed in enumerate(data):
                await self.style_embed(embed)
                if footer := embed.footer:
                    embed.set_footer(
                        text=(
                            (f"{footer.text} ∙ " if footer.text else "")
                            + f"Page {page + 1} of {len(data)} "
                        ),
                        icon_url=footer.icon_url,
                    )
                else:
                    embed.set_footer(
                        text=(
                            (f"{footer.text} ∙ " if footer.text else "")
                            + f"Page {page + 1} of {len(data)} "
                        ),
                    )

        return await paginator.start()

    async def style_embed(self, embed: Embed) -> Embed:
        reskin = await self.reskin()

        if (
            self.command
            and self.command.name == "createembed"
            and len(self.message.content.split()) > 1
        ):
            return embed

        if not embed.color:
            embed.color = reskin.get("colors", {}).get("main") or config.Color.neutral

        if not embed.author and embed.title:
            embed.set_author(
                name=self.author.display_name,
                icon_url=self.author.display_avatar,
            )

        if embed.title:
            embed.title = shorten(embed.title, 256)

        if embed.description:
            embed.description = shorten(embed.description, 4096)

        for field in embed.fields:
            embed.set_field_at(
                index=embed.fields.index(field),
                name=field.name,
                value=shorten(field.value, 1024),
                inline=field.inline,
            )

        return embed

    async def react_check(self: "Context"):
        """React to the message"""
        await self.message.add_reaction("✅")

    async def check(self):
        return await self.send(content="😈")

    async def prompt(self, message: str, member: Member = None, **kwargs):
        if member:
            view = views.ConfirmViewForUser(self, member)
            message = await self.send(
                embed=Embed(description=message), view=view, **kwargs
            )
            await view.wait()
            with suppress(HTTPException):
                await message.delete()
            if view.value is False:
                raise UserInputError("Prompt was denied.")

            return view.value
        view = views.ConfirmView(self)
        message = await self.send(embed=Embed(description=message), view=view, **kwargs)

        await view.wait()
        with suppress(HTTPException):
            await message.delete()

        if view.value is False:
            raise UserInputError("Prompt was denied.")
        return view.value


class ParameterParser:
    def __init__(self, ctx: "Context"):
        self.context = ctx

    def get(self, parameter: str, **kwargs) -> Any:
        for param in (parameter, *kwargs.get("aliases", ())):
            sliced = self.context.message.content.split()

            if kwargs.get("require_value", True) is False:
                return kwargs.get("default") if f"-{param}" not in sliced else True

            try:
                index = sliced.index(f"--{param}")

            except ValueError:
                return kwargs.get("default")

            result = []
            for word in sliced[index + 1 :]:
                if word.startswith("-"):
                    break

                result.append(word)

            if not (result := " ".join(result).replace("\\n", "\n").strip()):
                return kwargs.get("default")

            if choices := kwargs.get("choices"):
                if choice := tuple(
                    choice for choice in choices if choice.lower() == result.lower()
                ):
                    result = choice[0]

                else:
                    raise CommandError(f"Invalid choice for parameter `{param}`.")

            if converter := kwargs.get("converter"):
                if hasattr(converter, "convert"):
                    result = self.context.bot.loop.create_task(
                        converter().convert(self.ctx, result)
                    )

                else:
                    try:
                        result = converter(result)

                    except Exception as e:
                        raise CommandError(
                            f"Invalid value for parameter `{param}`."
                        ) from e

            if isinstance(result, int):
                if result < kwargs.get("minimum", 1):
                    raise CommandError(
                        f"The **minimum input** for parameter `{param}` is `{kwargs.get('minimum', 1)}`"
                    )

                if result > kwargs.get("maximum", 100):
                    raise CommandError(
                        f"The **maximum input** for parameter `{param}` is `{kwargs.get('maximum', 100)}`"
                    )

            return result

        return kwargs.get("default")


class FlagConverter(
    DefaultFlagConverter, case_insensitive=True, prefix="--", delimiter=" "
):
    ...
