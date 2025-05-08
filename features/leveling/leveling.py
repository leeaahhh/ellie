from discord.ext.commands import Cog, command, group, has_permissions
from discord import TextChannel, Member, Embed
from tools.managers.context import Context
from tools.managers.cache import cache
from datetime import datetime, timedelta
import random
from zoneinfo import ZoneInfo

class Leveling(Cog):
    """Cog for Leveling commands."""

    def __init__(self, bot):
        self.bot = bot

    def calculate_level(self, xp: int) -> int:
        """Calculate level based on XP."""
        return int((xp / 100) ** 0.5)

    def calculate_xp_for_level(self, level: int) -> int:
        """Calculate XP required for a level."""
        return int((level ** 2) * 100)

    @Cog.listener()
    async def on_message(self, message):
        """Handle XP gain from messages."""
        if message.author.bot or not message.guild:
            return

        # Get guild settings
        settings = await self.bot.db.fetchrow(
            "SELECT * FROM leveling.settings WHERE guild_id = $1",
            message.guild.id
        )
        if not settings or not settings["enabled"]:
            return

        # Check cooldown
        last_message = await self.bot.db.fetchval(
            "SELECT last_message FROM leveling.users WHERE guild_id = $1 AND user_id = $2",
            message.guild.id,
            message.author.id
        )
        if last_message:
            cooldown = timedelta(seconds=settings["xp_cooldown"])
            current_time = datetime.now(ZoneInfo("UTC"))
            if current_time - last_message < cooldown:
                return

        # Update last message timestamp
        current_time = datetime.now(ZoneInfo("UTC"))
        await self.bot.db.execute(
            """
            INSERT INTO leveling.users (guild_id, user_id, last_message)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id, user_id)
            DO UPDATE SET last_message = $3
            """,
            message.guild.id,
            message.author.id,
            current_time
        )

        # Add XP
        xp_gain = random.randint(settings["xp_rate"] - 5, settings["xp_rate"] + 5)
        result = await self.bot.db.fetchrow(
            """
            UPDATE leveling.users
            SET xp = xp + $3
            WHERE guild_id = $1 AND user_id = $2
            RETURNING xp, level
            """,
            message.guild.id,
            message.author.id,
            xp_gain
        )

        if not result:
            await self.bot.db.execute(
                "INSERT INTO leveling.users (guild_id, user_id, xp) VALUES ($1, $2, $3)",
                message.guild.id,
                message.author.id,
                xp_gain
            )
            return

        old_level = result["level"]
        new_level = self.calculate_level(result["xp"])

        if new_level > old_level:
            # Level up!
            await self.bot.db.execute(
                "UPDATE leveling.users SET level = $3 WHERE guild_id = $1 AND user_id = $2",
                message.guild.id,
                message.author.id,
                new_level
            )

            # Send level up message
            if settings["level_up_channel"]:
                channel = message.guild.get_channel(settings["level_up_channel"])
                if channel:
                    message_text = settings["level_up_message"].format(
                        user=message.author,
                        level=new_level
                    )
                    await channel.send(message_text)

    @group(
        name="leveling",
        usage="(subcommand) <args>",
        example="settings",
        invoke_without_command=True
    )
    async def leveling(self, ctx: Context):
        """Manage the leveling system."""
        await ctx.send_help()

    @leveling.command(
        name="rank",
        usage="<member>",
        example="leah",
        aliases=["level", "profile"]
    )
    async def rank(self, ctx: Context, member: Member = None):
        """View your or another member's rank."""
        member = member or ctx.author
        data = await self.bot.db.fetchrow(
            "SELECT * FROM leveling.users WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id,
            member.id
        )

        if not data:
            return await ctx.error(f"**{member}** hasn't earned any XP yet!")

        embed = Embed(
            color=ctx.bot.color.neutral,
            title=f"{member}'s Level Profile"
        )
        embed.set_thumbnail(url=member.display_avatar)
        
        current_level = data["level"]
        current_xp = data["xp"]
        next_level_xp = self.calculate_xp_for_level(current_level + 1)
        progress = (current_xp - self.calculate_xp_for_level(current_level)) / (next_level_xp - self.calculate_xp_for_level(current_level)) * 100

        embed.add_field(
            name="Level",
            value=f"**{current_level}**",
            inline=True
        )
        embed.add_field(
            name="XP",
            value=f"**{current_xp:,}** / {next_level_xp:,}",
            inline=True
        )
        embed.add_field(
            name="Progress",
            value=f"**{progress:.1f}%**",
            inline=True
        )

        await ctx.send(embed=embed)

    @leveling.command(
        name="leaderboard",
        usage="",
        example="",
        aliases=["top", "lb"]
    )
    async def leaderboard(self, ctx: Context):
        """View the server's level leaderboard."""
        data = await self.bot.db.fetch(
            """
            SELECT * FROM leveling.users
            WHERE guild_id = $1
            ORDER BY xp DESC
            LIMIT 10
            """,
            ctx.guild.id
        )

        if not data:
            return await ctx.error("No one has earned any XP yet!")

        embed = Embed(
            color=ctx.bot.color.neutral,
            title=f"{ctx.guild.name}'s Level Leaderboard"
        )

        description = []
        for i, row in enumerate(data, 1):
            member = ctx.guild.get_member(row["user_id"])
            if not member:
                continue

            description.append(
                f"**{i}.** {member.mention} • Level **{row['level']}** • **{row['xp']:,}** XP"
            )

        embed.description = "\n".join(description)
        await ctx.send(embed=embed)

    @leveling.group(
        name="settings",
        usage="(subcommand) <args>",
        example="channel #level-up",
        invoke_without_command=True
    )
    @has_permissions(manage_guild=True)
    async def settings(self, ctx: Context):
        """Manage leveling settings."""
        await ctx.send_help()

    @settings.command(
        name="channel",
        usage="<channel>",
        example="#level-up"
    )
    @has_permissions(manage_guild=True)
    async def channel(self, ctx: Context, channel: TextChannel):
        """Set the channel for level up messages."""
        await self.bot.db.execute(
            """
            INSERT INTO leveling.settings (guild_id, level_up_channel)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET level_up_channel = $2
            """,
            ctx.guild.id,
            channel.id
        )
        await ctx.approve(f"Set the level up channel to {channel.mention}")

    @settings.command(
        name="message",
        usage="<message>",
        example="GG {user.mention}! You're now level {level}!"
    )
    @has_permissions(manage_guild=True)
    async def message(self, ctx: Context, *, message: str):
        """Set the level up message."""
        await self.bot.db.execute(
            """
            INSERT INTO leveling.settings (guild_id, level_up_message)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET level_up_message = $2
            """,
            ctx.guild.id,
            message
        )
        await ctx.approve("Updated the level up message")

    @settings.command(
        name="rate",
        usage="<amount>",
        example="20"
    )
    @has_permissions(manage_guild=True)
    async def rate(self, ctx: Context, amount: int):
        """Set the XP gain rate."""
        if amount < 1 or amount > 50:
            return await ctx.error("XP rate must be between 1 and 50")

        await self.bot.db.execute(
            """
            INSERT INTO leveling.settings (guild_id, xp_rate)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET xp_rate = $2
            """,
            ctx.guild.id,
            amount
        )
        await ctx.approve(f"Set the XP rate to **{amount}**")

    @settings.command(
        name="cooldown",
        usage="<seconds>",
        example="30"
    )
    @has_permissions(manage_guild=True)
    async def cooldown(self, ctx: Context, seconds: int):
        """Set the XP cooldown."""
        if seconds < 1 or seconds > 300:
            return await ctx.error("Cooldown must be between 1 and 300 seconds")

        await self.bot.db.execute(
            """
            INSERT INTO leveling.settings (guild_id, xp_cooldown)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET xp_cooldown = $2
            """,
            ctx.guild.id,
            seconds
        )
        await ctx.approve(f"Set the XP cooldown to **{seconds}** seconds")

    @settings.command(
        name="toggle",
        usage="",
        example=""
    )
    @has_permissions(manage_guild=True)
    async def toggle(self, ctx: Context):
        """Toggle the leveling system."""
        settings = await self.bot.db.fetchrow(
            "SELECT enabled FROM leveling.settings WHERE guild_id = $1",
            ctx.guild.id
        )
        enabled = not (settings["enabled"] if settings else True)

        await self.bot.db.execute(
            """
            INSERT INTO leveling.settings (guild_id, enabled)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET enabled = $2
            """,
            ctx.guild.id,
            enabled
        )
        await ctx.approve(f"{'Enabled' if enabled else 'Disabled'} the leveling system") 