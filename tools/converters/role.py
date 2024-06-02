from discord import Role
from discord.ext.commands import CommandError, RoleConverter, RoleNotFound
from discord.utils import find

from tools.managers.context import Context
from tools.managers.regex import DISCORD_ID, DISCORD_ROLE_MENTION

DANGEROUS_PERMISSIONS = [
    "administrator",
    "kick_members",
    "ban_members",
    "manage_guild",
    "manage_roles",
    "manage_channels",
    "manage_emojis",
    "manage_webhooks",
    "manage_nicknames",
    "mention_everyone",
]


class Role(RoleConverter):
    @staticmethod
    async def convert(ctx: Context, argument: str):
        role = None
        if match := DISCORD_ID.match(argument):
            role = ctx.guild.get_role(int(match.group(1)))
        elif match := DISCORD_ROLE_MENTION.match(argument):
            role = ctx.guild.get_role(int(match.group(1)))
        else:
            role = (
                find(
                    lambda r: r.name.lower() == argument.lower(),
                    ctx.guild.roles,
                )
                or find(
                    lambda r: argument.lower() in r.name.lower(),
                    ctx.guild.roles,
                )
                or find(
                    lambda r: r.name.lower().startswith(argument.lower()),
                    ctx.guild.roles,
                )
            )
        if not role or role.is_default():
            raise RoleNotFound(argument)
        return role

    @staticmethod
    async def manageable(ctx: Context, role: Role, booster: bool = False):
        if role.managed and not booster:
            raise CommandError(f"You're unable to manage {role.mention}")
        if not role.is_assignable() and not booster:
            raise CommandError(f"I'm unable to manage {role.mention}")
        if role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner.id:
            raise CommandError(f"You're unable to manage {role.mention}")

        return True

    @staticmethod
    async def dangerous(ctx: Context, role: Role, _: str = "manage"):
        if (
            permissions := list(
                filter(
                    lambda permission: getattr(role.permissions, permission),
                    DANGEROUS_PERMISSIONS,
                )
            )
        ) and ctx.author.id != ctx.guild.owner_id:
            raise CommandError(
                f"You're unable to {_} {role.mention} because it has the `{permissions[0]}` permission"
            )

        return False
