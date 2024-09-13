from discord.ext.commands import CommandError

from tools.managers.context import Context
from tools.rei import rei

bot = rei()


@bot.check
async def blacklisted(ctx: Context) -> bool:
    """Check if a user is blacklisted"""
    return not await ctx.bot.db.fetchrow(
        "SELECT * FROM blacklist WHERE user_id = $1", ctx.author.id
    )


@bot.check
async def disabled_check(ctx: Context) -> bool:
    """Checks if the command is disabled in the channel"""
    if not ctx.author.guild_permissions.administrator:
        if parent := ctx.command.parent:
            if await ctx.bot.db.fetchrow(
                "SELECT * FROM commands.ignored WHERE guild_id = $1 AND target_id = ANY($2::BIGINT[])",
                ctx.guild.id,
                [
                    ctx.author.id,
                    ctx.channel.id,
                ],
            ):
                return False
            if await ctx.bot.db.fetchrow(
                "SELECT * FROM commands.disabled WHERE guild_id = $1 AND channel_id = $2 AND command = $3",
                ctx.guild.id,
                ctx.channel.id,
                parent.qualified_name,
            ):
                raise CommandError(
                    f"Command `{ctx.command.qualified_name}` is disabled in {ctx.channel.mention}"
                )
            if await ctx.bot.db.fetchrow(
                "SELECT * FROM commands.restricted WHERE guild_id = $1 AND command = $2 AND NOT role_id = ANY($3::BIGINT[])",
                ctx.guild.id,
                parent.qualified_name,
                [role.id for role in ctx.author.roles],
            ):
                raise CommandError(
                    f"You don't have a **permitted role** to use `{parent.qualified_name}`"
                )

        if await ctx.bot.db.fetchrow(
            "SELECT * FROM commands.ignored WHERE guild_id = $1 AND target_id = ANY($2::BIGINT[])",
            ctx.guild.id,
            [
                ctx.author.id,
                ctx.channel.id,
            ],
        ):
            return False
        if await ctx.bot.db.fetchrow(
            "SELECT * FROM commands.disabled WHERE guild_id = $1 AND channel_id = $2 AND command = $3",
            ctx.guild.id,
            ctx.channel.id,
            ctx.command.qualified_name,
        ):
            raise CommandError(
                f"Command `{ctx.command.qualified_name}` is disabled in {ctx.channel.mention}"
            )
        if await ctx.bot.db.fetchrow(
            "SELECT * FROM commands.restricted WHERE guild_id = $1 AND command = $2 AND NOT role_id = ANY($3::BIGINT[])",
            ctx.guild.id,
            ctx.command.qualified_name,
            [role.id for role in ctx.author.roles],
        ):
            raise CommandError(
                f"You don't have a **permitted role** to use `{ctx.command.qualified_name}`"
            )

    return True


if __name__ == "__main__":
    bot.run()
