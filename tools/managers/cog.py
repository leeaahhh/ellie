from __future__ import annotations

from typing import TYPE_CHECKING, Any

from discord.ext import commands

if TYPE_CHECKING:
    from tools.shiro import shiro


__all__: tuple[str, ...] = ("Cog",)


class Cog(commands.Cog):
    if TYPE_CHECKING:
        emoji: str | None
        brief: str | None
        hidden: bool

    __slots__: tuple[str, ...] = ("bot",)

    def __init_subclass__(cls: type[Cog], **kwargs: Any):
        cls.emoji = kwargs.pop("emoji", None)
        cls.brief = kwargs.pop("brief", None)
        cls.hidden = kwargs.pop("hidden", False)
        return super().__init_subclass__(**kwargs)

    def __init__(self, bot: shiro, *args: Any, **kwargs: Any):
        self.bot: shiro = bot
        super().__init__(*args, **kwargs)
