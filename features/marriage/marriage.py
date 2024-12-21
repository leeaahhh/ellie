from discord import Member, Permissions, File
from discord.ext.commands import BucketType, command, cooldown, max_concurrency, has_permissions
from typing import Optional, List, Union
import asyncio
from PIL import Image, ImageDraw, ImageFont
import io
from typing import Dict, Set, Tuple
import math

from tools.managers.cog import Cog
from tools.managers.context import Context
from discord import app_commands
from discord.ext.commands import hybrid_command

class Marriage(Cog):
    @hybrid_command(
        name="marry",
        usage="(member)",
        example="igna",
        aliases=["propose", "proposal"],
    )
    @max_concurrency(1, BucketType.member)
    @cooldown(1, 60, BucketType.member)
    async def marry(self: "Marriage", ctx: Context, member: Member):
        """Propose to another member"""
        marriage = await self.bot.db.fetchrow(
            "SELECT * FROM marriages WHERE user_id = $1 OR partner_id = $1",
            member.id,
        )
        if marriage:
            partner_id = marriage['partner_id'] if marriage['user_id'] == member.id else marriage['user_id']
            return await ctx.error(
                f"**{member.name}** is already married to **{self.bot.get_user(partner_id).name}**"
            )

        marriage = await self.bot.db.fetchrow(
            "SELECT * FROM marriages WHERE user_id = $1 OR partner_id = $1",
            ctx.author.id,
        )
        if marriage:
            partner_id = marriage['partner_id'] if marriage['user_id'] == ctx.author.id else marriage['user_id']
            return await ctx.error(
                f"You're already married to **{self.bot.get_user(partner_id).name}**"
            )

        if member == ctx.author:
            return await ctx.error("yeah get that ego out of there :unamused:")

        if member.bot:
            return await ctx.error("You can't marry **bots**")

        if not await ctx.prompt(
            f"**{member.name}**, do you accept **{ctx.author.name}**'s proposal?",
            member=member,
        ):
            return await ctx.error(f"**{member.name}** denied your proposal")

        await self.bot.db.execute(
            "INSERT INTO marriages (user_id, partner_id) VALUES ($1, $2)",
            ctx.author.id,
            member.id,
        )

        return await ctx.neutral(
            f"**{ctx.author.name}** and **{member.name}** are now married!"
        )

    @hybrid_command(
        name="divorce",
        aliases=["breakup"],
    )
    @max_concurrency(1, BucketType.member)
    @cooldown(1, 60, BucketType.member)
    async def divorce(self: "Marriage", ctx: Context):
        """Divorce your partner"""
        marriage = await self.bot.db.fetchrow(
            "SELECT * FROM marriages WHERE user_id = $1 OR partner_id = $1",
            ctx.author.id,
        )
        if not marriage:
            return await ctx.error("You're not **married** to anyone")

        await ctx.prompt(
            f"Are you sure you want to divorce **{self.bot.get_user(marriage.get('partner_id')).name}**?",
        )

        await self.bot.db.execute(
            "DELETE FROM marriages WHERE user_id = $1 OR partner_id = $1",
            ctx.author.id,
        )
        return await ctx.neutral("You are now **divorced**")

    @hybrid_command(
        name="partner",
        aliases=["spouse"],
    )
    @max_concurrency(1, BucketType.member)
    async def partner(self: "Marriage", ctx: Context):
        """Check who you're married to"""
        marriage = await self.bot.db.fetchrow(
            "SELECT * FROM marriages WHERE user_id = $1 OR partner_id = $1",
            ctx.author.id,
        )
        if not marriage:
            return await ctx.error("You're not **married** to anyone")

        partner = self.bot.get_user(marriage.get("partner_id"))
        return await ctx.neutral(f"You're married to **{partner}**")

    @hybrid_command(name="adopt", usage="(member)", example="igna")
    @max_concurrency(1, BucketType.member)
    @cooldown(1, 60, BucketType.member)
    async def adopt(self, ctx: Context, member: Member):
        """Adopt another member as your child"""
        existing = await self.bot.db.fetchrow(
            "SELECT parent_id FROM family_relationships WHERE child_id = $1",
            member.id
        )
        if existing:
            return await ctx.error(f"**{member.name}** already has a parent")

        if member == ctx.author:
            return await ctx.error("my ranked teammates :")

        if member.bot:
            return await ctx.error("You can't adopt bots")

        allow_incest = await self.bot.db.fetchval(
            "SELECT allow_incest FROM guild_settings WHERE guild_id = $1",
            ctx.guild.id
        )
        
        if not allow_incest:
            marriage = await self.bot.db.fetchrow(
                "SELECT * FROM marriages WHERE user_id = $1 OR partner_id = $1",
                member.id
            )
            if marriage and (marriage['user_id'] == ctx.author.id or marriage['partner_id'] == ctx.author.id):
                return await ctx.error("You can't adopt someone you're married to")

        if not await ctx.prompt(
            f"**{member.name}**, do you want **{ctx.author.name}** to adopt you?",
            member=member,
        ):
            return await ctx.error(f"**{member.name}** denied your adoption request")

        await self.bot.db.execute(
            "INSERT INTO family_relationships (child_id, parent_id) VALUES ($1, $2)",
            member.id,
            ctx.author.id
        )

        return await ctx.neutral(
            f"**{ctx.author.name}** has adopted **{member.name}**!"
        )

    @hybrid_command(name="children")
    async def children(self, ctx: Context, member: Optional[Member] = None):
        """List all your children or another member's children"""
        target = member or ctx.author
        
        children = await self.bot.db.fetch(
            "SELECT child_id FROM family_relationships WHERE parent_id = $1",
            target.id
        )
        
        if not children:
            return await ctx.error(f"**{target.name}** has no children")
            
        children_names = [f"**{self.bot.get_user(child['child_id']).name}**" for child in children]
        return await ctx.neutral(f"{target.name}'s children: {', '.join(children_names)}")

    @hybrid_command(name="parent")
    async def parent(self, ctx: Context, member: Optional[Member] = None):
        """Check who is your/someone's parent"""
        target = member or ctx.author
        
        parent = await self.bot.db.fetchrow(
            "SELECT parent_id FROM family_relationships WHERE child_id = $1",
            target.id
        )
        
        if not parent:
            return await ctx.error(f"**{target.name}** has no parent")
            
        parent_user = self.bot.get_user(parent['parent_id'])
        return await ctx.neutral(f"**{target.name}**'s parent is **{parent_user.name}**")

    @hybrid_command(name="runaway")
    @cooldown(1, 60, BucketType.member)
    async def runaway(self, ctx: Context):
        """Run away from your parent"""
        parent = await self.bot.db.fetchrow(
            "SELECT parent_id FROM family_relationships WHERE child_id = $1",
            ctx.author.id
        )
        
        if not parent:
            return await ctx.error("You don't have a parent to run away from")

        if not await ctx.prompt("Are you sure you want to run away from your parent?"):
            return await ctx.error("Cancelled running away")

        await self.bot.db.execute(
            "DELETE FROM family_relationships WHERE child_id = $1",
            ctx.author.id
        )
        return await ctx.neutral("You have successfully run away from your parent")

    @hybrid_command(name="disown")
    @cooldown(1, 60, BucketType.member)
    async def disown(self, ctx: Context, member: Member):
        """Disown one of your children"""
        child = await self.bot.db.fetchrow(
            "SELECT child_id FROM family_relationships WHERE parent_id = $1 AND child_id = $2",
            ctx.author.id,
            member.id
        )
        
        if not child:
            return await ctx.error(f"**{member.name}** is not your child")

        if not await ctx.prompt(f"Are you sure you want to disown **{member.name}**?"):
            return await ctx.error("Cancelled disowning")

        await self.bot.db.execute(
            "DELETE FROM family_relationships WHERE parent_id = $1 AND child_id = $2",
            ctx.author.id,
            member.id
        )
        return await ctx.neutral(f"You have disowned **{member.name}**")

    @hybrid_command(name="relationship")
    async def relationship(self, ctx: Context, member1: Member, member2: Optional[Member] = None):
        """Check the relationship between two members"""
        if member2 is None:
            member2 = ctx.author
            member1, member2 = member2, member1

        # Check if directly married
        marriage = await self.bot.db.fetchrow(
            "SELECT * FROM marriages WHERE (user_id = $1 AND partner_id = $2) OR (user_id = $2 AND partner_id = $1)",
            member1.id,
            member2.id
        )
        if marriage:
            return await ctx.neutral(f"**{member1.name}** and **{member2.name}** are married")

        # Check direct parent/child relationship
        parent_child = await self.bot.db.fetchrow(
            "SELECT * FROM family_relationships WHERE (parent_id = $1 AND child_id = $2) OR (parent_id = $2 AND child_id = $1)",
            member1.id,
            member2.id
        )
        if parent_child:
            if parent_child['parent_id'] == member1.id:
                return await ctx.neutral(f"**{member1.name}** is **{member2.name}**'s parent")
            else:
                return await ctx.neutral(f"**{member2.name}** is **{member1.name}**'s parent")

        # Check multi-generation relationships (great-grandparents etc)
        ancestor = await self.bot.db.fetchrow("""
            WITH RECURSIVE family_tree AS (
                SELECT parent_id, child_id, 1 as depth
                FROM family_relationships
                UNION ALL
                SELECT f.parent_id, ft.child_id, ft.depth + 1
                FROM family_relationships f
                JOIN family_tree ft ON f.child_id = ft.parent_id
                WHERE ft.depth < 10
            )
            SELECT * FROM family_tree 
            WHERE (parent_id = $1 AND child_id = $2) OR (parent_id = $2 AND child_id = $1)
            ORDER BY depth ASC
            LIMIT 1
        """, member1.id, member2.id)
        
        if ancestor:
            depth = ancestor['depth']
            great_prefix = "great-" * (depth - 2) if depth > 2 else ""
            
            if ancestor['parent_id'] == member1.id:
                if depth == 2:
                    relationship = "grandparent"
                else:
                    relationship = f"{great_prefix}grandparent"
                return await ctx.neutral(f"**{member1.name}** is **{member2.name}**'s {relationship}")
            else:
                if depth == 2:
                    relationship = "grandchild"
                else:
                    relationship = f"{great_prefix}grandchild"
                return await ctx.neutral(f"**{member2.name}** is **{member1.name}**'s {relationship}")

        # Check if siblings (same parent)
        siblings = await self.bot.db.fetchrow("""
            SELECT * FROM family_relationships f1
            JOIN family_relationships f2 ON f1.parent_id = f2.parent_id
            WHERE f1.child_id = $1 AND f2.child_id = $2
        """, member1.id, member2.id)
        
        if siblings:
            return await ctx.neutral(f"**{member1.name}** and **{member2.name}** are siblings")

        # Check if uncle/aunt/nephew/niece with multiple generations
        extended_family = await self.bot.db.fetchrow("""
            WITH RECURSIVE ancestor_tree AS (
                SELECT parent_id, child_id, 1 as depth
                FROM family_relationships
                UNION ALL
                SELECT f.parent_id, at.child_id, at.depth + 1
                FROM family_relationships f
                JOIN ancestor_tree at ON f.child_id = at.parent_id
                WHERE at.depth < 5
            )
            SELECT a1.depth as p1_depth, a2.depth as p2_depth
            FROM ancestor_tree a1
            JOIN ancestor_tree a2 ON a1.parent_id = a2.parent_id
            WHERE a1.child_id = $1 AND a2.child_id = $2
            ORDER BY a1.depth + a2.depth ASC
            LIMIT 1
        """, member1.id, member2.id)

        if extended_family:
            p1_depth = extended_family['p1_depth']
            p2_depth = extended_family['p2_depth']
            
            if abs(p1_depth - p2_depth) == 1:
                if p1_depth < p2_depth:
                    return await ctx.neutral(f"**{member1.name}** is **{member2.name}**'s uncle/aunt")
                else:
                    return await ctx.neutral(f"**{member2.name}** is **{member1.name}**'s uncle/aunt")
            elif p1_depth == p2_depth:
                return await ctx.neutral(f"**{member1.name}** and **{member2.name}** are cousins")

        # Check if in-laws through any family connection
        inlaw = await self.bot.db.fetchrow("""
            WITH RECURSIVE family_tree AS (
                SELECT parent_id, child_id, 1 as depth
                FROM family_relationships
                UNION ALL
                SELECT f.parent_id, ft.child_id, ft.depth + 1
                FROM family_relationships f
                JOIN family_tree ft ON f.child_id = ft.parent_id
                WHERE ft.depth < 5
            )
            SELECT * FROM marriages m
            JOIN family_tree ft ON m.user_id = ft.child_id
            WHERE (ft.parent_id = $1 AND m.partner_id = $2) 
               OR (ft.parent_id = $2 AND m.partner_id = $1)
        """, member1.id, member2.id)

        if inlaw:
            return await ctx.neutral(f"**{member1.name}** and **{member2.name}** are in-laws")

        return await ctx.error(f"**{member1.name}** and **{member2.name}** are not related")

    @hybrid_command(name="forcedivorce")
    @has_permissions(manage_roles=True)
    async def forcedivorce(self, ctx: Context, member: Member):
        """Force divorce a member (Manage Roles required)"""
        marriage = await self.bot.db.fetchrow(
            "SELECT * FROM marriages WHERE user_id = $1 OR partner_id = $1",
            member.id
        )
        if not marriage:
            return await ctx.error(f"**{member.name}** is not married")

        await self.bot.db.execute(
            "DELETE FROM marriages WHERE user_id = $1 OR partner_id = $1",
            member.id
        )
        return await ctx.neutral(f"**{member.name}** has been forcefully divorced")

    @hybrid_command(name="forceemancipate")
    @has_permissions(manage_roles=True)
    async def forceemancipate(self, ctx: Context, member: Member):
        """Force emancipate a member from their parent (Manage Roles required)"""
        relationship = await self.bot.db.fetchrow(
            "SELECT * FROM family_relationships WHERE child_id = $1",
            member.id
        )
        if not relationship:
            return await ctx.error(f"**{member.name}** has no parent")

        await self.bot.db.execute(
            "DELETE FROM family_relationships WHERE child_id = $1",
            member.id
        )
        return await ctx.neutral(f"**{member.name}** has been forcefully emancipated")

    @hybrid_command(name="forcemarry")
    @has_permissions(manage_roles=True)
    async def forcemarry(self, ctx: Context, member1: Member, member2: Member):
        """Force marry two members (Manage Roles required)"""
        for member in (member1, member2):
            marriage = await self.bot.db.fetchrow(
                "SELECT * FROM marriages WHERE user_id = $1 OR partner_id = $1",
                member.id
            )
            if marriage:
                return await ctx.error(f"**{member.name}** is already married")

        await self.bot.db.execute(
            "INSERT INTO marriages (user_id, partner_id) VALUES ($1, $2)",
            member1.id,
            member2.id
        )
        return await ctx.neutral(f"**{member1.name}** and **{member2.name}** have been forcefully married")

    @hybrid_command(name="makeparent")
    @has_permissions(manage_roles=True)
    async def makeparent(self, ctx: Context, parent: Member, child: Member):
        """Force make someone a parent of another member (Manage Roles required)"""
        existing = await self.bot.db.fetchrow(
            "SELECT * FROM family_relationships WHERE child_id = $1",
            child.id
        )
        if existing:
            return await ctx.error(f"**{child.name}** already has a parent")

        await self.bot.db.execute(
            "INSERT INTO family_relationships (child_id, parent_id) VALUES ($1, $2)",
            child.id,
            parent.id
        )
        return await ctx.neutral(f"**{parent.name}** has forcefully made **{child.name}** their child")

    @hybrid_command(name="toggleincest", aliases=["incest"])
    @has_permissions(manage_guild=True)
    async def toggle_incest(self, ctx: Context):
        """Toggle whether family members can marry each other (Manage Guild required)"""
        current_setting = await self.bot.db.fetchval(
            "SELECT allow_incest FROM guild_settings WHERE guild_id = $1",
            ctx.guild.id
        )
        
        new_setting = not current_setting if current_setting is not None else True
        
        await self.bot.db.execute(
            """
            INSERT INTO guild_settings (guild_id, allow_incest)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) 
            DO UPDATE SET allow_incest = $2
            """,
            ctx.guild.id,
            new_setting
        )
        
        status = "enabled" if new_setting else "disabled"
        return await ctx.neutral(f"Family marriage has been **{status}** for this server")

    async def _get_all_relationships(self, user_id: int, processed: Set[int] = None) -> Dict:
        """Recursively fetch all family relationships"""
        if processed is None:
            processed = set()
        
        if user_id in processed:
            return None
        
        processed.add(user_id)
        
        data = {
            "id": user_id,
            "name": self.bot.get_user(user_id).name,
            "partner": None,
            "partner_data": None,
            "parents": [],
            "children": []
        }
        
        marriage = await self.bot.db.fetchrow(
            "SELECT * FROM marriages WHERE user_id = $1 OR partner_id = $1",
            user_id
        )
        if marriage:
            partner_id = marriage['partner_id'] if marriage['user_id'] == user_id else marriage['user_id']
            data["partner"] = partner_id
            if partner_id not in processed:
                data["partner_data"] = await self._get_all_relationships(partner_id, processed)
        
        parents = await self.bot.db.fetch(
            "SELECT parent_id FROM family_relationships WHERE child_id = $1",
            user_id
        )
        for parent in parents:
            if parent['parent_id'] not in processed:
                parent_data = await self._get_all_relationships(parent['parent_id'], processed)
                if parent_data:
                    data["parents"].append(parent_data)
        
        children = await self.bot.db.fetch(
            "SELECT child_id FROM family_relationships WHERE parent_id = $1",
            user_id
        )
        for child in children:
            if child['child_id'] not in processed:
                child_data = await self._get_all_relationships(child['child_id'], processed)
                if child_data:
                    data["children"].append(child_data)
        
        return data

    def _calculate_tree_dimensions(self, tree_data: Dict) -> Tuple[int, int, int]:
        """Calculate dimensions needed for the tree"""
        def count_max_width(node, level=0, widths=None):
            if widths is None:
                widths = {}
            
            widths[level] = widths.get(level, 0) + 1
            
            for child in node.get("children", []):
                count_max_width(child, level + 1, widths)
            for parent in node.get("parents", []):
                count_max_width(parent, level - 1, widths)
            
            return widths
        
        level_widths = count_max_width(tree_data)
        
        max_nodes_in_row = max(level_widths.values())
        num_levels = len(level_widths)
        
        width = max(1200, max_nodes_in_row * 300)
        height = max(800, num_levels * 200)
        padding = 100
        
        return width, height, padding

    def _draw_node(self, draw: ImageDraw, x: int, y: int, name: str, 
                   highlight: bool = False, font: ImageFont = None) -> Tuple[int, int]:
        """Draw a single node of the family tree"""
        text_bbox = draw.textbbox((0, 0), name, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        box_width = text_width + 40
        box_height = text_height + 20
        
        box_left = x - box_width // 2
        box_top = y - box_height // 2
        box_right = box_left + box_width
        box_bottom = box_top + box_height
        
        box_color = (255, 215, 0, 230) if highlight else (255, 255, 255, 230)
        outline_color = (0, 0, 0, 255)
        draw.rectangle([box_left, box_top, box_right, box_bottom], 
                      fill=box_color, outline=outline_color, width=2)
        
        text_x = x - text_width // 2
        text_y = y - text_height // 2
        draw.text((text_x, text_y), name, fill=(0, 0, 0, 255), font=font)
        
        return box_width, box_height

    def _draw_tree(self, img: Image, draw: ImageDraw, data: Dict, x: int, y: int, 
                   target_id: int, font: ImageFont, level: int = 0):
        """Recursively draw the family tree"""
        is_target = data["id"] == target_id
        node_width, node_height = self._draw_node(draw, x, y, data["name"], 
                                                highlight=is_target, font=font)
        
        if data["partner"] and data["partner_data"]:
            partner_x = x + node_width + 50
            
            is_partner_target = data["partner"] == target_id
            partner_width, _ = self._draw_node(draw, partner_x, y, 
                                             data["partner_data"]["name"],
                                             highlight=is_partner_target, font=font)
            
            line_y = y
            draw.line([(x + node_width/2, line_y), (partner_x - partner_width/2, line_y)],
                     fill=(255, 255, 255, 200), width=2)
            
            if data["partner_data"].get("parents"):
                self._draw_parent_tree(img, draw, data["partner_data"], partner_x, y,
                                     target_id, font, level)
        
        vertical_spacing = 150
        
        if data["parents"]:
            parent_y = y - vertical_spacing
            total_parents = len(data["parents"])
            parent_spacing = max(200, node_width * 1.5)
            
            start_x = x - (total_parents - 1) * parent_spacing / 2
            for i, parent in enumerate(data["parents"]):
                parent_x = start_x + i * parent_spacing
                self._draw_tree(img, draw, parent, parent_x, parent_y, 
                              target_id, font, level - 1)
                draw.line([(parent_x, parent_y + node_height/2),
                          (x, y - node_height/2)],
                         fill=(255, 255, 255, 200), width=2)
        
        if data["children"]:
            child_y = y + vertical_spacing
            total_children = len(data["children"])
            child_spacing = max(200, node_width * 1.5)
            
            center_x = x
            
            start_x = center_x - (total_children - 1) * child_spacing / 2
            for i, child in enumerate(data["children"]):
                child_x = start_x + i * child_spacing
                self._draw_tree(img, draw, child, child_x, child_y, 
                              target_id, font, level + 1)
                
                draw.line([(x, y + node_height/2),
                          (child_x, child_y - node_height/2)],
                         fill=(255, 255, 255, 200), width=2)

    def _draw_parent_tree(self, img: Image, draw: ImageDraw, data: Dict, x: int, y: int,
                         target_id: int, font: ImageFont, level: int):
        """Draw only the parent portion of a tree (for partner's family)"""
        if data["parents"]:
            vertical_spacing = 150
            parent_y = y - vertical_spacing
            total_parents = len(data["parents"])
            parent_spacing = max(200, 150)
            
            start_x = x - (total_parents - 1) * parent_spacing / 2
            for i, parent in enumerate(data["parents"]):
                parent_x = start_x + i * parent_spacing
                self._draw_tree(img, draw, parent, parent_x, parent_y,
                              target_id, font, level - 1)
                draw.line([(parent_x, parent_y + 20),
                          (x, y - 20)],
                         fill=(255, 255, 255, 200), width=2)

    @hybrid_command(name="tree")
    # TODO: Fix rendering issues when there are too many members
    async def tree(self, ctx: Context, member: Optional[Member] = None):
        """Display a family tree"""
        target = member or ctx.author
        
        tree_data = await self._get_all_relationships(target.id)
        if not tree_data:
            return await ctx.error(f"**{target.name}** has no family relationships")
        
        width, height, padding = self._calculate_tree_dimensions(tree_data)
        
        img = Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans.ttf", 20)
        except OSError:
            try:
                font = ImageFont.truetype("assets/font.ttf", 20)
            except OSError:
                font = ImageFont.load_default()
        
        self._draw_tree(img, draw, tree_data, width//2, height//2, target.id, font)
        
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
            padding = 20
            new_img = Image.new('RGBA', (img.width + padding*2, img.height + padding*2), (0, 0, 0, 0))
            new_img.paste(img, (padding, padding))
            img = new_img
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        await ctx.send(file=File(buffer, filename='family_tree.png'))
