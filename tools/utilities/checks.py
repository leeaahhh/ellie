import discord
from discord.ext import commands
from discord.ext.commands import CommandError


def has_permissions(**permissions):
    """Check if the user has permissions to execute the command (fake permissions included)"""

    async def predicate(ctx: commands.Context):
        if isinstance(ctx, int):
            return [
                permission for permission, value in permissions.items() if value is True
            ]

        if "guild_owner" in permissions:
            if ctx.author.id != ctx.guild.owner_id:
                raise CommandError(
                    f"You must be the **server owner** to use `{ctx.command.qualified_name}`"
                )
            return True

        if ctx.author.guild_permissions.administrator:
            return True

        for permission in permissions:
            missing_permissions = []
            if getattr(ctx.author.guild_permissions, permission) is not True:
                missing_permissions.append(permission)

            if missing_permissions:
                fake_permissions = await ctx.bot.db.fetch(
                    "SELECT * FROM fake_permissions WHERE guild_id = $1 AND permission = ANY($2::text[])",
                    ctx.guild.id,
                    missing_permissions,
                )
                for fake_permission in fake_permissions:
                    if fake_permission["role_id"] in [
                        role.id for role in ctx.author.roles
                    ]:
                        try:
                            missing_permissions.remove(fake_permission["permission"])
                        except ValueError:
                            continue

            if missing_permissions:
                raise commands.MissingPermissions(missing_permissions)

        return True

    return commands.check(predicate)


def require_dm():
    """Check if the bot can DM the user."""

    async def predicate(ctx: commands.Context):
        try:
            await ctx.author.send()
        except discord.HTTPException as error:
            if error.code == 50007:
                raise commands.CommandError(
                    "You need to enable **DMs** to use this command"
                )

        return True

    return commands.check(predicate)


def donator(booster: bool = False):
    """Check if the user is a donator"""

    async def predicate(ctx: commands.Context):
        guild = ctx.bot.get_guild(1181448215699140658)
        role = guild.get_role(1186989657678950440)
        user = guild.get_member(ctx.author.id)

        if booster:
            if role in user.roles:
                return True

            if not user or not user.premium_since:
                raise commands.CommandError(
                    f"You must **boost** the shiro [**Discord Server**](https://discord.gg/ignacio) to use `{ctx.command.qualified_name}`"
                )

            return True

        donator_check = await ctx.bot.db.fetchrow(
            "SELECT * FROM donators WHERE user_id = $1", ctx.author.id
        )

        if not donator_check:
            raise commands.CommandError(
                f"You must be a **donator** to use `{ctx.command.qualified_name}` - [**Discord Server**](https://discord.gg/ignacio)"
            )

        return True

    return commands.check(predicate)


def require_boost():
    """Check if the user has boosted the server"""

    async def predicate(ctx: commands.Context):
        if not ctx.author.premium_since:
            raise commands.CommandError(
                f"You must **boost** the server to use `{ctx.command.qualified_name}`"
            )

        return True

    return commands.check(predicate)


commands.has_permissions = has_permissions
