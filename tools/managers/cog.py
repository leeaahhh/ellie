from __future__ import annotations

from typing import TYPE_CHECKING, Any

from discord.ext.commands import Cog as _Cog

if TYPE_CHECKING:
    from tools.ellie import ellie


__all__: tuple[str, ...] = ("Cog",)


class Cog(_Cog):
    __slots__: tuple[str, ...] = ("bot",)

    def __init_subclass__(cls: type[Cog], **kwargs: Any):
        if not hasattr(cls, "__cog_name__"):
            cls.__cog_name__ = cls.__name__
        return super().__init_subclass__(**kwargs)

    def __init__(self, bot: ellie, *args: Any, **kwargs: Any):
        self.bot: ellie = bot
        super().__init__(*args, **kwargs)
