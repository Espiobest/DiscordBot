from discord.ext.commands import Context
from discord.ext import commands
import discord

from bot import Waifu

from inspect import Parameter
from datetime import datetime
import asyncio


class Tag(commands.Cog):

    def __init__(self, bot: Waifu):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def tag(self, ctx: Context, *, name: lambda inp: inp.lower()):
        """Get a tag"""
        query = "SELECT * FROM tags WHERE guild_id = $1 AND title = $2"
        tag = await self.bot.con.fetchrow(query, ctx.guild.id, name)

        if tag is None:
            await ctx.message.delete(delay=10.0)
            message = await ctx.send('Could not find a tag with that name.')
            return await message.delete(delay=10.0)

        await ctx.send(tag['text'])
        await self.bot.con.execute("UPDATE tags SET uses = uses + 1 WHERE guild_id = $1 AND title = $2",
                                   ctx.guild.id, name)

    @tag.command()
    async def create(self, ctx: Context, name: lambda inp: inp.lower(), *, text: str = None):
        """Create a tag by providing a name and the content."""

        name = await commands.clean_content().convert(ctx=ctx, argument=name)
        query = "SELECT * FROM tags WHERE guild_id = $1 AND title = $2"
        tag = await self.bot.con.fetchrow(query, ctx.guild.id, name)

        if tag is not None:
            return await ctx.send('A tag with that name already exists.')

        if not text and not ctx.message.attachments:
            raise commands.MissingRequiredArgument(Parameter("text", Parameter.POSITIONAL_OR_KEYWORD))
        if not text:
            text = "\n".join([i.url for i in ctx.message.attachments])
        else:
            text = await commands.clean_content().convert(ctx=ctx, argument=text)

        insert_query = """INSERT INTO tags(guild_id, author_id, title, text, uses, created_at)
                          VALUES($1, $2, $3, $4, $5, $6)"""
        await self.bot.con.execute(insert_query, ctx.guild.id, ctx.author.id, name, text, 0, datetime.utcnow())
        await ctx.send('You have successfully created your tag.')

    @tag.command()
    async def info(self, ctx: Context, *, name: lambda inp: inp.lower()):
        """Get information regarding the specified tag."""
        query = """SELECT * FROM tags WHERE guild_id = $1 AND title = $2"""
        tag = await self.bot.con.fetchrow(query, ctx.guild.id, name)

        if tag is None:
            await ctx.message.delete(delay=10.0)
            return await ctx.send('Could not find a tag with that name.', delete_after=10)

        author = self.bot.get_user(tag['author_id'])
        author = str(author) if isinstance(author, discord.User) else f"(ID: {tag['author_id']})"

        info = discord.Embed(title=f"🏷️ Tag: {tag['title']}", color=discord.Color.gold())
        info.add_field(name='Creator', value=author)
        info.add_field(name='Uses', value=tag['uses'])

        await ctx.send(embed=info)

    @tag.command()
    async def list(self, ctx: Context, *, member: discord.Member = None):
        """List your existing tags"""
        member = member or ctx.author
        query = """SELECT title FROM tags WHERE guild_id = $1 AND author_id = $2 ORDER BY title"""
        result = await self.bot.con.fetch(query, ctx.guild.id, member.id)

        if not result:
            return await ctx.send('No tags found.')

        await ctx.send(
            f"**{len(result)} tag{'s' * (len(result) > 1)} by {'you' if member == ctx.author else str(member)} found on this server.**"
        )

        pager = commands.Paginator()

        for record in result:
            pager.add_line(line=record["title"])

        for page in pager.pages:
            await ctx.send(page)

    @tag.command()
    async def delete(self, ctx: Context, *, name: lambda inp: inp.lower()):
        """Delete a tag."""
        query = """DELETE FROM tags WHERE guild_id = $1 AND title = $2"""
        await self.bot.con.execute(query, str(ctx.guild.id), name)
        await ctx.send("You have successfully deleted your tag.")

    @tag.command()
    async def all(self, ctx):
        """List all existing tags alphabetically ordered and sends them in DMs."""
        result = await self.bot.con.fetch(
            """SELECT title FROM tags WHERE guild_id = $1 ORDER BY title""",
            ctx.guild.id
        )
        if not result:
            return await ctx.send("This server doesn't have any tags.", delete_after=10)

        try:
            await ctx.author.send(f"***{len(result)} tag{'s' * (len(result) > 1)} found on this server.***")
        except discord.Forbidden:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("Could not dm you...", delete_after=10)

        pager = commands.Paginator()

        for record in result:
            pager.add_line(line=record["title"])

        for page in pager.pages:
            await asyncio.sleep(1)
            await ctx.author.send(page)

        await ctx.send("Tags sent in DMs.")

    @tag.command()
    async def edit(self, ctx: Context, name: lambda inp: inp.lower(), *, text: str):
        """Edit a tag"""
        text = await commands.clean_content().convert(ctx=ctx, argument=text)
        query = """SELECT * FROM tags WHERE guild_id = $1 AND title = $2"""
        tag = await self.bot.con.fetchrow(query, ctx.guild.id, name)

        if tag is None:
            await ctx.message.delete(delay=10.0)
            return await ctx.send('Could not find a tag with that name.', delete_after=10)

        if tag['author_id'] != ctx.author.id:
            owner = await self.bot.is_owner(ctx.author)
            if not owner:
                return await ctx.send("You don't have permission to do that.")

        update = "UPDATE tags SET text = $1 WHERE guild_id = $2 AND title = $3"
        await self.bot.con.execute(update, text, ctx.guild.id, name)
        await ctx.send('You have successfully edited your tag.')

    @tag.command()
    async def rename(self, ctx: Context, name: lambda inp: inp.lower(), *, new_name: lambda inp: inp.lower()):
        """Rename a tag."""

        new_name = await commands.clean_content().convert(ctx=ctx, argument=new_name)

        query = "SELECT * FROM tags WHERE guild_id = $1 AND title = $2"
        tag = await self.bot.con.fetchrow(query, ctx.guild.id, name)

        new_tag = await self.bot.con.fetchrow(query, ctx.guild.id, new_name)

        if new_tag is not None:
            return await ctx.send("A tag with that name already exists.")

        if tag is None:
            await ctx.message.delete(delay=10.0)
            return await ctx.send('Could not find a tag with that name.', delete_after=10)

        if tag['author_id'] != ctx.author.id:
            owner = await self.bot.is_owner(ctx.author)
            if not owner:
                return await ctx.send("You don't have permission to do that.")

        update = "UPDATE tags SET title = $1 WHERE guild_id = $2 AND title = $3"
        await self.bot.con.execute(update, new_name, ctx.guild.id, name)
        await ctx.send('You have successfully renamed your tag.')

    @tag.command()
    async def search(self, ctx: Context, *, term: str):
        """Search for a tag given a search term. PostgreSQL syntax must be used for the search."""
        query = """SELECT title FROM tags WHERE guild_id = $1 AND title LIKE $2 LIMIT 10"""
        result = await self.bot.con.fetch(query, ctx.guild.id, term)

        if not result:
            return await ctx.send("No tags found that has the term in it's name", delete_after=10)
        count = "Maximum of 10" if len(result) == 10 else len(result)
        tags = "\n".join(record["title"] for record in result)

        await ctx.send(
            f"**{count} tag{'s' * (len(result) > 1)} found with search term on this server.**```\n{tags}\n```"
        )


def setup(bot: Waifu):
    bot.add_cog(Tag(bot))
