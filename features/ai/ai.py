from openai import OpenAI
from discord.ext.commands import Cog, command, Context, hybrid_command, has_permissions
from discord import Embed, TextChannel, Message
import config
import os
from tools.managers.cog import Cog
from tools.managers.context import Context
import asyncio
import datetime

class AI(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conversation_history = {}
        self.ping_reply_enabled = True
        self.active_channels = set()  # Set of channel IDs
        self.last_message_times = {}  # channel_id: datetime
        self.dead_channel_check_interval = 60  # seconds
        self.dead_channel_threshold = 600  # seconds (10 minutes)
        self.recent_users = {}  # channel_id: set of user_ids
        self.active_join_threshold = 3  # users
        self.active_join_window = 120  # seconds
        try:
            self.client = OpenAI(
                base_url=config.Authorization.AI.base_url,
                api_key=config.Authorization.AI.api_key
            )
        except Exception as e:
            print(f"Error initializing OpenAI client: {e}")
            self.client = None
        self.bot.loop.create_task(self.dead_channel_monitor())

    async def cog_load(self):
        try:
            await self.bot.db.execute("CREATE SCHEMA IF NOT EXISTS ai")
            await self.bot.db.execute("""
                CREATE TABLE IF NOT EXISTS ai.channels (
                    guild_id BIGINT NOT NULL,
                    channel_id BIGINT NOT NULL,
                    PRIMARY KEY (guild_id, channel_id)
                )
            """)
            await self.bot.db.execute("""
                CREATE TABLE IF NOT EXISTS ai.settings (
                    guild_id BIGINT PRIMARY KEY,
                    ping_reply_enabled BOOLEAN DEFAULT TRUE
                )
            """)
        except Exception as e:
            print(f"Error setting up AI database: {e}")
        # Load settings and channels for all guilds on cog load
        for guild in self.bot.guilds:
            await self.load_settings(guild.id)
            await self.load_active_channels(guild.id)

    def get_user_history_key(self, message: Message) -> str:
        return f"{message.guild.id}:{message.channel.id}:{message.author.id}"

    async def get_conversation_history(self, message: Message, max_messages: int = 10) -> list:
        messages = []
        current = message
        history_key = self.get_user_history_key(message)
        
        messages.append({"role": "user", "content": current.content})
        
        if history_key in self.conversation_history:
            messages = self.conversation_history[history_key] + messages
        
        for _ in range(max_messages):
            if not current.reference or not current.reference.message_id:
                break
                
            try:
                referenced = await current.channel.fetch_message(current.reference.message_id)
                
                if referenced.author == self.bot.user:
                    messages.insert(0, {"role": "assistant", "content": referenced.content})
                else:
                    messages.insert(0, {"role": "user", "content": referenced.content})
                
                current = referenced
            except:
                break
        
        self.conversation_history[history_key] = messages[-max_messages:]
        return messages

    @hybrid_command(
        name="wipechat",
        usage="",
        example="",
        aliases=["clearhistory", "clear"]
    )
    async def wipe_chat(self, ctx: Context):
        history_key = self.get_user_history_key(ctx.message)
        if history_key in self.conversation_history:
            del self.conversation_history[history_key]
        embed = Embed(
            color=0x00FF00,
            description="Conversation history has been wiped"
        )
        await ctx.send(embed=embed)

    @hybrid_command(
        name="setchannel",
        usage="<channel>",
        example="#ai-chat",
        aliases=["setaichannel"]
    )
    @has_permissions(manage_guild=True)
    async def set_channel(self, ctx: Context, channel: TextChannel):
        if not self.client:
            embed = Embed(
                color=0xFF0000,
                description="AI client is not properly configured"
            )
            return await ctx.send(embed=embed)
            
        await self.bot.db.execute(
            """
            INSERT INTO ai.channels (guild_id, channel_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO UPDATE
            SET channel_id = $2
            """,
            ctx.guild.id,
            channel.id
        )
        embed = Embed(
            color=0x00FF00,
            description=f"AI channel set to {channel.mention}"
        )
        await ctx.send(embed=embed)

    @hybrid_command(
        name="removechannel",
        usage="",
        example="",
        aliases=["removeaichannel"]
    )
    @has_permissions(manage_guild=True)
    async def remove_channel(self, ctx: Context):
        await self.bot.db.execute(
            "DELETE FROM ai.channels WHERE guild_id = $1",
            ctx.guild.id
        )
        embed = Embed(
            color=0x00FF00,
            description="AI channel configuration removed"
        )
        await ctx.send(embed=embed)

    @Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot or not message.guild or not self.client:
            return

        guild_id = message.guild.id
        await self.load_settings(guild_id)
        await self.load_active_channels(guild_id)

        # Check if message is in an active channel or is a ping to the bot
        is_active_channel = message.channel.id in self.active_channels
        is_ping = self.ping_reply_enabled and self.bot.user in message.mentions

        # Only respond if in active channel or pinged
        if not (is_active_channel or is_ping):
            return

        # Don't reply to itself
        if message.author == self.bot.user:
            return

        # Track last message time for dead channel detection
        if is_active_channel:
            self.last_message_times[message.channel.id] = datetime.datetime.utcnow()
            # Track recent users for active join
            now = datetime.datetime.utcnow()
            if message.channel.id not in self.recent_users:
                self.recent_users[message.channel.id] = []
            self.recent_users[message.channel.id].append((message.author.id, now))
            # Remove old entries
            self.recent_users[message.channel.id] = [
                (uid, t) for uid, t in self.recent_users[message.channel.id]
                if (now - t).total_seconds() < self.active_join_window
            ]
            unique_users = set(uid for uid, _ in self.recent_users[message.channel.id])
            if len(unique_users) >= self.active_join_threshold:
                # Bot joins the conversation
                N = 10
                history = []
                async for msg in message.channel.history(limit=N, oldest_first=False):
                    if msg.author == self.bot.user:
                        history.insert(0, {"role": "assistant", "content": msg.content})
                    else:
                        history.insert(0, {"role": "user", "content": msg.content})
                async with message.channel.typing():
                    try:
                        response = self.client.chat.completions.create(
                            model='shapesinc/reiayanami-y8ux',
                            messages=history
                        )
                        content = response.choices[0].message.content
                        await message.channel.send(content)
                    except Exception as e:
                        embed = Embed(
                            color=0xFF0000,
                            description=f"Error: {str(e)}"
                        )
                        await message.channel.send(embed=embed)
                # Reset recent users to avoid spamming
                self.recent_users[message.channel.id] = []

        # Fetch last N messages for context
        N = 10
        history = []
        async for msg in message.channel.history(limit=N, oldest_first=False):
            if msg.author == self.bot.user:
                history.insert(0, {"role": "assistant", "content": msg.content})
            else:
                history.insert(0, {"role": "user", "content": msg.content})

        async with message.channel.typing():
            try:
                response = self.client.chat.completions.create(
                    model='shapesinc/reiayanami-y8ux',
                    messages=history
                )
                content = response.choices[0].message.content
                await message.reply(content)
            except Exception as e:
                embed = Embed(
                    color=0xFF0000,
                    description=f"Error: {str(e)}"
                )
                await message.reply(embed=embed)

    @hybrid_command(
        name="chat",
        usage="<message>",
        example="What's the capital of France?",
        aliases=["ask", "gpt"]
    )
    async def chat(self, ctx: Context, *, message: str):
        if not self.client:
            embed = Embed(
                color=0xFF0000,
                description="AI client is not properly configured"
            )
            return await ctx.send(embed=embed)
            
        async with ctx.typing():
            try:
                messages = await self.get_conversation_history(ctx.message)
                
                response = self.client.chat.completions.create(
                    model='shapesinc/reiayanami-y8ux',
                    messages=messages
                )
                content = response.choices[0].message.content
                await ctx.send(content)
            except Exception as e:
                embed = Embed(
                    color=0xFF0000,
                    description=f"Error generating response: {str(e)}"
                )
                await ctx.send(embed=embed)

    @hybrid_command(
        name="image",
        usage="<prompt>",
        example="A white siamese cat",
        aliases=["generate", "img"]
    )
    async def image(self, ctx: Context, *, prompt: str):
        if not self.client:
            embed = Embed(
                color=0xFF0000,
                description="AI client is not properly configured"
            )
            return await ctx.send(embed=embed)
            
        async with ctx.typing():
            try:
                response = self.client.images.generate(
                    model='sdxl',
                    prompt=prompt
                )
                
                image_data = response.data[0]
                
                embed = Embed(
                    color=config.Color.neutral,
                    title="Generated Image",
                    description=f"Prompt: {prompt}"
                )
                embed.set_author(
                    name=ctx.author.display_name,
                    icon_url=ctx.author.display_avatar
                )
                embed.set_image(url=image_data.url)
                await ctx.send(embed=embed)

            except Exception as e:
                embed = Embed(
                    color=0xFF0000,
                    description=f"Error generating image: {str(e)}"
                )
                await ctx.send(embed=embed)

    async def load_settings(self, guild_id):
        row = await self.bot.db.fetchrow("SELECT ping_reply_enabled FROM ai.settings WHERE guild_id = $1", guild_id)
        if row:
            self.ping_reply_enabled = row["ping_reply_enabled"] if row["ping_reply_enabled"] is not None else True
        else:
            await self.save_settings(guild_id)

    async def save_settings(self, guild_id):
        await self.bot.db.execute(
            """
            INSERT INTO ai.settings (guild_id, ping_reply_enabled)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO UPDATE SET ping_reply_enabled = $2
            """,
            guild_id, self.ping_reply_enabled
        )

    async def load_active_channels(self, guild_id):
        rows = await self.bot.db.fetch("SELECT channel_id FROM ai.channels WHERE guild_id = $1", guild_id)
        self.active_channels = set(row["channel_id"] for row in rows)

    async def add_active_channel(self, guild_id, channel_id):
        await self.bot.db.execute(
            "INSERT INTO ai.channels (guild_id, channel_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            guild_id, channel_id
        )
        self.active_channels.add(channel_id)

    async def remove_active_channel(self, guild_id, channel_id):
        await self.bot.db.execute(
            "DELETE FROM ai.channels WHERE guild_id = $1 AND channel_id = $2",
            guild_id, channel_id
        )
        self.active_channels.discard(channel_id)

    @hybrid_command(
        name="panel",
        usage="",
        example="",
        aliases=["config", "settings"]
    )
    @has_permissions(manage_guild=True)
    async def panel(self, ctx: Context):
        guild_id = ctx.guild.id
        await self.load_settings(guild_id)
        await self.load_active_channels(guild_id)
        embed = Embed(
            color=0x00BFFF,
            title="AI Configuration Panel",
            description=f"**Ping Reply:** {'Enabled' if self.ping_reply_enabled else 'Disabled'}\n\n"
                        f"**Active Channels:**\n" + ("\n".join(f"<#{cid}>" for cid in self.active_channels) if self.active_channels else "None")
        )
        embed.set_footer(text="Use /ai toggleping, /ai addchannel, /ai removechannel to configure.")
        await ctx.send(embed=embed)

    @hybrid_command(
        name="toggleping",
        usage="",
        example="",
        aliases=["pingtoggle"]
    )
    @has_permissions(manage_guild=True)
    async def toggle_ping(self, ctx: Context):
        self.ping_reply_enabled = not self.ping_reply_enabled
        await self.save_settings(ctx.guild.id)
        await ctx.send(embed=Embed(color=0x00FF00, description=f"Ping reply {'enabled' if self.ping_reply_enabled else 'disabled'}."))

    @hybrid_command(
        name="addchannel",
        usage="<channel>",
        example="#general",
        aliases=["enablechannel"]
    )
    @has_permissions(manage_guild=True)
    async def add_channel(self, ctx: Context, channel: TextChannel):
        await self.add_active_channel(ctx.guild.id, channel.id)
        await ctx.send(embed=Embed(color=0x00FF00, description=f"Channel {channel.mention} added to AI active channels."))

    @hybrid_command(
        name="removeactivechannel",
        usage="<channel>",
        example="#general",
        aliases=["disableactivechannel"]
    )
    @has_permissions(manage_guild=True)
    async def remove_active_channel(self, ctx: Context, channel: TextChannel):
        await self.remove_active_channel(ctx.guild.id, channel.id)
        await ctx.send(embed=Embed(color=0x00FF00, description=f"Channel {channel.mention} removed from AI active channels."))

    async def dead_channel_monitor(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            now = datetime.datetime.utcnow()
            for channel_id in list(self.active_channels):
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    continue
                last_time = self.last_message_times.get(channel_id)
                if not last_time:
                    # Fetch last message time if not cached
                    try:
                        last_msg = await channel.history(limit=1).flatten()
                        if last_msg:
                            self.last_message_times[channel_id] = last_msg[0].created_at.replace(tzinfo=None)
                            last_time = self.last_message_times[channel_id]
                    except Exception:
                        continue
                if not last_time:
                    continue
                if (now - last_time).total_seconds() > self.dead_channel_threshold:
                    # Channel is dead, send a starter message
                    try:
                        await channel.send("It's been quiet here! Anyone want to chat?")
                        self.last_message_times[channel_id] = now
                    except Exception:
                        pass
            await asyncio.sleep(self.dead_channel_check_interval)

async def setup(bot):
    await bot.add_cog(AI(bot)) 