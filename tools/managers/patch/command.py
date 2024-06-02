from discord.ext.commands.core import Command, hooked_wrapped_callback

from tools.managers import Context


class CommandCore(Command):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def permissions(self):
        if self.checks:
            for check in self.checks:
                if "has_permissions" in str(check):
                    return await check(0)

        return []

    async def invoke(self, ctx: Context, /):
        await self.prepare(ctx)

        if hasattr(ctx, "parameters") and (parameters := ctx.parameters):
            for parameter, value in parameters.items():
                if kwargs := list(ctx.kwargs.keys()):
                    kwarg = kwargs[-1]
                    for parameter in (
                        parameter,
                        *ctx.command.parameters.get(parameter).get("aliases", []),
                    ):
                        if isinstance(ctx.kwargs.get(kwarg), str):
                            ctx.kwargs.update(
                                {
                                    kwarg: (
                                        ctx.kwargs.get(kwarg)
                                        .replace("—", "--")
                                        .replace(f"--{parameter} {value}", "")
                                        .replace(f"--{parameter}", "")
                                        .replace(f"-{parameter}", "")
                                        .strip()
                                    )
                                    or (
                                        ctx.command.params.get(kwarg).default
                                        if isinstance(
                                            ctx.command.params.get(kwarg).default,
                                            str,
                                        )
                                        else None
                                    )
                                }
                            )

        ctx.invoked_subcommand = None
        ctx.subcommand_passed = None
        injected = hooked_wrapped_callback(self, ctx, self.callback)  # type: ignore
        await injected(*ctx.args, **ctx.kwargs)  # type: ignore


Command.invoke = CommandCore.invoke
Command.permissions = CommandCore.permissions
