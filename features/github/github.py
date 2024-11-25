from typing import Optional
from discord.ext.commands import Cog, command, Context
from discord import Embed
import aiohttp
from datetime import datetime
import config

class GitHub(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_url = "https://api.github.com"
        
    @command(
        name="github",
        aliases=["git"],
        usage="(query)",
        example="NERVCorporation/rei"
    )
    async def github(self, ctx: Context, *, query: str):
        """Get information about GitHub repositories, users, or organizations"""
        async with aiohttp.ClientSession() as session:
            # check if query is a repo (contains /)
            if "/" in query:
                async with session.get(f"{self.api_url}/repos/{query}") as response:
                    if response.status == 200:
                        data = await response.json()
                        embed = Embed(
                            color=config.Color.neutral,
                            title=data["full_name"],
                            url=data["html_url"],
                            description=data["description"] or "No description provided"
                        )
                        
                        embed.add_field(
                            name="Statistics",
                            value=(
                                f"⭐ **Stars:** {data['stargazers_count']:,}\n"
                                f"🔨 **Forks:** {data['forks_count']:,}\n"
                                f"👀 **Watchers:** {data['watchers_count']:,}\n"
                                f"❗ **Issues:** {data['open_issues_count']:,}\n"
                            )
                        )
                        
                        embed.add_field(
                            name="Information",
                            value=(
                                f"📅 **Created:** <t:{int(datetime.strptime(data['created_at'], '%Y-%m-%dT%H:%M:%SZ').timestamp())}:R>\n"
                                f"📝 **Updated:** <t:{int(datetime.strptime(data['updated_at'], '%Y-%m-%dT%H:%M:%SZ').timestamp())}:R>\n"
                                f"🔤 **Language:** {data['language'] or 'None'}\n"
                                f"📑 **License:** {data['license']['name'] if data['license'] else 'None'}\n"
                            )
                        )
                        
                        if data["owner"]["avatar_url"]:
                            embed.set_thumbnail(url=data["owner"]["avatar_url"])
                        
                        return await ctx.send(embed=embed)

            # try user and if user not found, try organization
            async with session.get(f"{self.api_url}/users/{query}") as response:
                if response.status == 200:
                    data = await response.json()
                    is_org = data["type"] == "Organization"
                    
                    embed = Embed(
                        color=config.Color.neutral,
                        title=data["login"],
                        url=data["html_url"],
                        description=data["bio"] or "No bio provided"
                    )
                    
                    info_value = []
                    if data.get("followers"):
                        info_value.append(f"👥 **Followers:** {data['followers']:,}")
                    if data.get("following") and not is_org:
                        info_value.append(f"👤 **Following:** {data['following']:,}")
                    if data.get("public_repos"):
                        info_value.append(f"📚 **Public Repos:** {data['public_repos']:,}")
                    if data.get("location"):
                        info_value.append(f"📍 **Location:** {data['location']}")
                    if data.get("company"):
                        info_value.append(f"🏢 **Company:** {data['company']}")
                    
                    embed.add_field(
                        name="Information",
                        value="\n".join(info_value),
                        inline=False
                    )

                    # get repositories and sort by stars
                    async with session.get(f"{self.api_url}/users/{query}/repos?sort=stars&per_page=100") as repos_response:
                        if repos_response.status == 200:
                            repos = await repos_response.json()
                            if repos:
                                # sort repos by stars and get top 3
                                top_repos = sorted(repos, key=lambda r: r['stargazers_count'], reverse=True)[:3]
                                
                                embed.add_field(
                                    name=f"Top Repositories ({len(repos)})",
                                    value="\n".join(
                                        f"[`⭐ {repo['stargazers_count']:,}, "
                                        f"{datetime.strptime(repo['created_at'], '%Y-%m-%dT%H:%M:%SZ').strftime('%m/%d/%y')} "
                                        f"{repo['name']}`]({repo['html_url']})"
                                        for repo in top_repos
                                    ),
                                    inline=False
                                )
                    
                    if data["avatar_url"]:
                        embed.set_thumbnail(url=data["avatar_url"])
                    
                    embed.set_footer(text="Created")
                    embed.timestamp = datetime.strptime(data["created_at"], "%Y-%m-%dT%H:%M:%SZ")
                    
                    return await ctx.send(embed=embed)
                    
            return await ctx.error("Could not find that GitHub repository, user, or organization")
