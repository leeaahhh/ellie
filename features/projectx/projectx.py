import aiohttp
from discord.ext import commands
from tools.managers import Context
import config
import json
from discord import Embed

class ProjectX(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="projectx", aliases=["pjx"], invoke_without_command=True)
    async def projectx(self, ctx: Context):
        """ProjectX commands."""
        await ctx.send("Use `projectx avatar <userid>` to get the avatar.")

    @projectx.command(name="avatar", aliases=["lp"])
    async def projectx_avatar(self, ctx: Context, userid: str):
        """Fetch the avatar for the given user ID."""
        cookie = config.RobloxSecurity

        async with aiohttp.ClientSession() as session:
            headers = {
                "Cookie": f".ROBLOSECURITY={cookie}"
            }
            
            user_info_url = f"https://www.projex.zip/apisite/users/v1/users/{userid}"
            async with session.get(user_info_url, headers=headers) as user_response:
                if not user_response.status == 200:
                    return await ctx.error("Failed to fetch user information. Please check the user ID.")
                
                user_info_body = await user_response.text()
                user_info = json.loads(user_info_body)  

            avatar_url_response = await session.get(f"https://www.projex.zip/Thumbs/avatar.ashx?userid={userid}", headers=headers)
            if avatar_url_response.status != 200:
                return await ctx.error("Failed to fetch the avatar URL. Please check the user ID.")
            
            final_avatar_url = str(avatar_url_response.url)  

            headshot_url = f"https://www.projex.zip/Thumbs/Headshot.ashx?userid={userid}"

            user_info['imageUrl'] = final_avatar_url  
            user_info['description'] = user_info.get('description', 'N/A')  
            user_info['isBanned'] = user_info.get('isBanned', 'Unknown')
            user_info['RAP'] = user_info.get('inventory_rap', 'N/A')  
            user_info['account_age'] = user_info.get('created', 'N/A')  
            if user_info['account_age'] != 'N/A':
                user_info['account_age'] = user_info['account_age'].split('T')[0]  
                user_info['account_age'] = user_info['account_age'].split('-')[2] + '/' + user_info['account_age'].split('-')[1] + '/' + user_info['account_age'].split('-')[0]  
            user_info['account_age'] = user_info['account_age'].replace('/', '-')  
            username = user_info.get('name', 'Unknown User')  

            embed = Embed(title=f"{username}'s Profile", url=f"https://www.projex.zip/users/{userid}/profile", color=0xff0000)
            embed.set_thumbnail(url=headshot_url)  
            embed.set_image(url=final_avatar_url)  
            embed.add_field(name="Description", value=user_info['description'], inline=False)
            embed.add_field(name="Account Age", value=user_info.get('account_age', 'N/A'), inline=True)
            embed.add_field(name="Banned", value=user_info.get('isBanned', 'No'), inline=True)
            embed.add_field(name="RAP", value=user_info.get('RAP', 'N/A'), inline=True)

            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ProjectX(bot))
