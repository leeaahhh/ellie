from discord import Embed, Member, User
from discord.ext.commands import command, group, is_owner
from discord.utils import format_dt

from tools.managers.cog import Cog
from tools.managers.context import Context


class Developer(Cog):
    """Cog for Developer commands."""

    @command(
        name="traceback",
        usage="(error id)",
        example="NrnMZEYuV5g",
        aliases=["trace"],
    )
    @is_owner()
    async def traceback(self: "Developer", ctx: Context, _id: str):
        """Get the traceback of an error"""
        error = await self.bot.db.fetchrow(
            "SELECT * FROM traceback WHERE error_id = $1", _id
        )

        if not error:
            return await ctx.error(f"Couldn't find an error for `{_id}`")

        embed = Embed(
            title=f"Command: {error['command']}",
            description=(
                f"**Guild:** {self.bot.get_guild(error['guild_id']) or 'N/A'} (`{error['guild_id']}`)\n**User:**"
                f" {self.bot.get_user(error['user_id']) or 'N/A'} (`{error['user_id']}`)\n**Timestamp**:"
                f" {format_dt(error['timestamp'])}\n```py\n{error['traceback']}```"
            ),
        )

        await ctx.send(embed=embed)

    @group(
        name="blacklist",
        aliases=["block", "bl"],
        invoke_without_command=True,
    )
    @is_owner()
    async def blacklist(self: "Developer", ctx: Context):
        """Manage the blacklist"""
        await ctx.send_help()

    @blacklist.command(
        name="add",
        usage="(user)",
        example="igna",
        aliases=["a", "append"],
    )
    @is_owner()
    async def blacklist_add(
        self: "Developer",
        ctx: Context,
        user: User | Member,
        *,
        reason: str = "No reason provided",
    ):
        """Blacklist a user"""
        try:
            await self.bot.db.execute(
                "INSERT INTO blacklist (user_id, reason) VALUES ($1, $2)",
                user.id,
                reason,
            )
        except Exception:
            return await ctx.error(f"**{user}** has already been blacklisted")

        await ctx.approve(f"Added **{user}** to the blacklist")

    @blacklist.command(
        name="remove",
        usage="(user)",
        example="rei",
        aliases=["delete", "del", "rm"],
    )
    @is_owner()
    async def blacklist_remove(self, ctx: Context, *, user: Member | User):
        """Remove a user from the blacklist"""
        try:
            await self.bot.db.execute(
                "DELETE FROM blacklist WHERE user_id = $1", user.id
            )
        except Exception:
            return await ctx.error(f"**{user}** isn't blacklisted")

        return await ctx.approve(f"Removed **{user}** from the blacklist")

    @blacklist.command(
        name="check",
        usage="(user)",
        example="rei",
        aliases=["note"],
    )
    @is_owner()
    async def blacklist_check(self, ctx: Context, *, user: Member | User):
        """Check why a user is blacklisted"""
        note = await self.bot.db.fetchval(
            "SELECT reason FROM blacklist WHERE user_id = $1", user.id
        )
        if not note:
            return await ctx.error(f"**{user}** isn't blacklisted")

        await ctx.neutral(f"**{user}** is blacklisted for **{note}**")

    @group(
        name="donator",
        aliases=["d"],
        example="add igna",
        invoke_without_command=True,
    )
    @is_owner()
    async def donator(self: "Developer", ctx: Context):
        """Manage the donators"""
        await ctx.send_help()

    @donator.command(
        name="add",
        usage="(user)",
        example="igna",
        aliases=["a", "append"],
    )
    @is_owner()
    async def donator_add(
        self: "Developer",
        ctx: Context,
        user: User | Member,
    ):
        """Add a donator"""
        try:
            await self.bot.db.execute(
                "INSERT INTO donators (user_id) VALUES ($1)", user.id
            )
        except Exception:
            return await ctx.error(f"**{user}** is already a **donator**")

        await ctx.approve(f"Added **{user}** to the **donators**")

    @donator.command(
        name="remove",
        usage="(user)",
        example="igna",
        aliases=["delete", "del", "rm"],
    )
    @is_owner()
    async def donator_remove(self, ctx: Context, *, user: Member | User):
        """Remove a donator"""
        if not await self.bot.db.fetchval(
            "SELECT user_id FROM donators WHERE user_id = $1", user.id
        ):
            return await ctx.error(f"**{user}** isn't a **donator**")

        await self.bot.db.execute("DELETE FROM donators WHERE user_id = $1", user.id)

        return await ctx.approve(f"Removed **{user}** from the **donators**")

    @donator.command(
        name="list",
        aliases=["l"],
    )
    @is_owner()
    async def donator_list(self, ctx: Context):
        """List all the donators"""
        donators = [
            f"**{await self.bot.fetch_user(row['user_id']) or 'Unknown User'}** (`{row['user_id']}`)"
            for row in await self.bot.db.fetch(
                "SELECT user_id FROM donators",
            )
        ]
        if not donators:
            return await ctx.error("There are no **donators**")

        await ctx.paginate(
            Embed(
                title="Donators",
                description="\n".join(donators),
            )
        )

    @command(
        name="echo",
        usage="(message)",
        example="Hello, world!",
    )
    @is_owner()
    async def echo(self: "Developer", ctx: Context, *, message: str):
        """Make the bot echo a message"""
        await ctx.send(message)

    @command(
        name="changepfp",
        usage="(image url or attachment)",
        example="https://example.com/image.png",
        aliases=["setpfp"],
    )
    @is_owner()
    async def change_avatar(self: "Developer", ctx: Context, url: str = None):
        """Change the bot's avatar using a URL or attachment"""
        if not url and not ctx.message.attachments:
            return await ctx.error("Missing image url or attachment")

        try:

            image_url = url or ctx.message.attachments[0].url
            async with self.bot.session.get(image_url) as response:
                avatar_bytes = await response.read()

            await self.bot.user.edit(avatar=avatar_bytes)
            await ctx.approve("Successfully changed my avatar!")

        except Exception as e:
            await ctx.error(f"Failed to change avatar: {str(e)}")