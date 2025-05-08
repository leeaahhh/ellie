from openai import OpenAI
from discord.ext.commands import Cog, command, Context, hybrid_command, has_permissions
from discord import Embed, TextChannel, Message
import config
import os
from tools.managers.cog import Cog
from tools.managers.context import Context

class AI(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.personalities = {}
        self.active_personality = None
        self.conversation_history = {}
        try:
            self.client = OpenAI(
                base_url=config.Authorization.AI.base_url,
                api_key=config.Authorization.AI.api_key
            )
            self.load_personalities()
        except Exception as e:
            print(f"Error initializing OpenAI client: {e}")
            self.client = None

    def load_personalities(self):
        instructions_dir = "instructions"
        if not os.path.exists(instructions_dir):
            os.makedirs(instructions_dir)
            return

        for file in os.listdir(instructions_dir):
            if file.endswith(".txt"):
                name = file[:-4]
                with open(os.path.join(instructions_dir, file), "r", encoding="utf-8") as f:
                    self.personalities[name] = f.read().strip()

    async def cog_load(self):
        try:
            await self.bot.db.execute("CREATE SCHEMA IF NOT EXISTS ai")
            await self.bot.db.execute("""
                CREATE TABLE IF NOT EXISTS ai.channels (
                    guild_id BIGINT PRIMARY KEY,
                    channel_id BIGINT NOT NULL
                )
            """)
        except Exception as e:
            print(f"Error setting up AI database: {e}")

    def get_user_history_key(self, message: Message) -> str:
        return f"{message.guild.id}:{message.channel.id}:{message.author.id}"

    async def get_conversation_history(self, message: Message, max_messages: int = 10) -> list:
        messages = []
        current = message
        history_key = self.get_user_history_key(message)
        
        if self.active_personality and self.active_personality in self.personalities:
            messages.append({"role": "system", "content": self.personalities[self.active_personality]})
        
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
        name="personality",
        usage="<name>",
        example="luna",
        aliases=["persona"]
    )
    @has_permissions(manage_guild=True)
    async def set_personality(self, ctx: Context, name: str):
        if name not in self.personalities:
            embed = Embed(
                color=0xFF0000,
                description=f"Personality '{name}' not found. Available personalities: {', '.join(self.personalities.keys())}"
            )
            return await ctx.send(embed=embed)
            
        self.active_personality = name
        embed = Embed(
            color=0x00FF00,
            description=f"AI personality set to {name}"
        )
        await ctx.send(embed=embed)

    @hybrid_command(
        name="personalities",
        usage="",
        example="",
        aliases=["personas"]
    )
    async def list_personalities(self, ctx: Context):
        if not self.personalities:
            embed = Embed(
                color=0xFF0000,
                description="No personalities found in the instructions directory"
            )
            return await ctx.send(embed=embed)
            
        embed = Embed(
            color=config.Color.neutral,
            title="Available AI Personalities",
            description="\n".join(f"• {name}" for name in self.personalities.keys())
        )
        await ctx.send(embed=embed)

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

        is_ai_channel = await self.bot.db.fetchval(
            "SELECT channel_id FROM ai.channels WHERE guild_id = $1",
            message.guild.id
        )
        
        is_reply_to_ai = False
        if message.reference and message.reference.message_id:
            try:
                referenced = await message.channel.fetch_message(message.reference.message_id)
                is_reply_to_ai = referenced.author == self.bot.user
            except:
                pass

        if not (is_ai_channel and message.channel.id == is_ai_channel) and not is_reply_to_ai:
            return

        async with message.channel.typing():
            try:
                messages = await self.get_conversation_history(message)
                
                response = self.client.chat.completions.create(
                    model='gpt-4o-mini',
                    messages=messages
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
                    model='gpt-4o-mini',
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

async def setup(bot):
    await bot.add_cog(AI(bot)) 