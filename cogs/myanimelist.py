from discord.ext.commands.errors import MissingRequiredArgument, CommandOnCooldown
from discord.ext.commands import Context
from discord.ext import commands
import discord

from bot import Waifu

import datetime
import asyncio


class MyAnimeList(commands.Cog):
    """Returns a list of results of the anime/character as a paginated message"""

    def __init__(self, bot: Waifu):
        self.bot = bot
        self.base_url = 'https://api.jikan.moe/v3/'

    @commands.cooldown(3, 15, commands.BucketType.guild)
    @commands.command()
    async def sauce(self, ctx: Context, *, query: str):
        query = query.replace(' ', '/')
        url = self.base_url + f'search/manga?q={query}&rated=rx&page=1'
        async with self.bot.session.get(url=url) as response:
            if response.status == 200:
                request = await response.json()
            elif response.status == 404:
                return await ctx.send("Enter a valid manga name.")
            else:
                return await ctx.send('The API is having some issues right now. Try again later.')
        await self.pagination(ctx, request, 'manga')

    @commands.cooldown(3, 15, commands.BucketType.guild)
    @commands.group(invoke_without_command=True, aliases=['mal', 'ani'])
    async def anime(self, ctx: Context, *, query: str):
        """Searching for an anime and getting the response"""
        print("anime")
        query = query.replace(' ', '/')
        url = self.base_url + f'search/anime?q={query}&page=1'

        async with self.bot.session.get(url=url) as response:
            if response.status == 200:
                request = await response.json()
            elif response.status == 404:
                return await ctx.send("Enter a valid anime name.")
            else:
                return await ctx.send('The API is having some issues right now. Try again later.')

        await self.pagination(ctx, request)

    @commands.cooldown(3, 15, commands.BucketType.guild)
    @anime.command(aliases=['char'])
    async def character(self, ctx, *, query):
        """Searching for a character and getting the response"""
        print("ch")
        query = query.replace(' ', '/')
        url = self.base_url + f'search/character?q={query}&page=1'

        async with self.bot.session.get(url=url) as response:
            if response.status == 200:
                request = await response.json()
            elif response.status == 404:
                return await ctx.send("Enter a valid character name.")
            else:
                return await ctx.send('The API is having some issues right now. Try again later.')

        await self.pagination(ctx, request, "char")

    async def pagination(self, ctx: Context, content: str, req: str = 'anime'):
        """Paginating the content from the requests"""
        embeds = []
        reactions = ['⏮', '◀', '🛑', '▶', '⏭']
        if req == "anime":
            for result in content['results'][:10]:
                embed = discord.Embed(title=f'{result["title"]}', colour=discord.colour.Color.red())
                embed.add_field(name='Description', value=f'{result["synopsis"]}' or "NA")
                embed.set_thumbnail(url=result["image_url"])
                status = 'Airing' if result['airing'] else 'Finished'
                embed.add_field(name='⏳ Status', value=status)
                embed.add_field(name='🗂️ Type', value=result["type"], inline=True)

                if result["start_date"]:
                    time = result["start_date"].split('-')

                    if int(time[0]) > datetime.datetime.today().year:
                        st = f"19{time[0][-2:]}-{time[1]}-{time[2]}"
                    else:
                        st = result["start_date"]

                    start_date = st.split('T')[0]
                    start = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()

                else:
                    start = "?"

                if not result["airing"]:
                    if result["end_date"]:
                        e_time = result["end_date"].split('-')

                        if int(e_time[0]) > datetime.datetime.today().year:
                            et = f"19{e_time[0][-2:]}-{e_time[1]}-{e_time[2]}"
                        else:
                            et = result["end_date"]

                        end_date = et.split('T')[0]
                        end = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
                    else:
                        end = "?"

                else:
                    end = "?"

                if result["score"] == 0:
                    score = "N/A"
                else:
                    score = result["score"]

                embed.add_field(name='🗓️ Aired', value=f'From **{start}** to **{end}**', inline=False)
                embed.add_field(name='💽 Episodes', value=result["episodes"] or '?')
                embed.add_field(name='⭐ Score', value=score, inline=True)
                embed.add_field(name='\u200b', value=f'[Link]({result["url"]})', inline=False)

                embeds.append(embed)

        elif req == "manga":
            for result in content['results'][:10]:
                embed = discord.Embed(title=f'{result["title"]}', colour=discord.colour.Color.red())
                embed.add_field(name='Description', value=f'{result["synopsis"]}' or "NA")
                embed.set_thumbnail(url=result["image_url"])
                status = 'Publishing' if result['publishing'] else 'Finished'
                embed.add_field(name='⏳ Status', value=status)
                embed.add_field(name='🗂️ Type', value=result["type"], inline=True)

                if result["start_date"]:
                    time = result["start_date"].split('-')

                    if int(time[0]) > datetime.datetime.today().year:
                        st = f"19{time[0][-2:]}-{time[1]}-{time[2]}"
                    else:
                        st = result["start_date"]

                    start_date = st.split('T')[0]
                    start = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()

                else:
                    start = "?"

                if not result["publishing"]:
                    if result["end_date"]:
                        e_time = result["end_date"].split('-')

                        if int(e_time[0]) > datetime.datetime.today().year:
                            et = f"19{e_time[0][-2:]}-{e_time[1]}-{e_time[2]}"
                        else:
                            et = result["end_date"]

                        end_date = et.split('T')[0]
                        end = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
                    else:
                        end = "?"

                else:
                    end = "?"

                if result["score"] == 0:
                    score = "N/A"
                else:
                    score = result["score"]

                embed.add_field(name='🗓️ Aired', value=f'From **{start}** to **{end}**', inline=False)
                embed.add_field(name='📕 Chapters', value=result["chapters"] or '?')
                embed.add_field(name="Volumes", value=result["volumes"] or "N/A")
                embed.add_field(name='⭐ Score', value=score, inline=True)
                embed.add_field(name='\u200b', value=f'[Link]({result["url"]})', inline=False)
                embeds.append(embed)

        elif req == "char":
            for result in content["results"][:20]:
                embed = discord.Embed(title=f'{result["name"].replace(",", "")}', colour=discord.colour.Color.red())
                embed.set_image(url=result["image_url"])
                alt_names = "\n".join(result["alternative_names"]) or "None"

                anime = result["anime"]

                if anime:
                    ani_res = f'[{anime[0]["name"]}]({anime[0]["url"]})'
                    if len(anime) > 1:
                        ani_res += f'\n[{anime[1]["name"]}]({anime[1]["url"]})'
                    embed.add_field(name='Anime', value=ani_res, inline=False)

                manga = result["manga"]

                if manga:
                    manga_res = f'[{manga[0]["name"]}]({manga[0]["url"]})'
                    if len(manga) > 1:
                        manga_res += f'\n[{manga[1]["name"]}]({manga[1]["url"]})'

                    embed.add_field(name='Manga', value=manga_res, inline=False)

                embed.add_field(name='Alternative Names', value=alt_names, inline=False)
                embed.add_field(name='\u200b', value=f'[{result["name"].replace(",", "")}]({result["url"]})')
                embeds.append(embed)

        embeds[0].set_footer(text=f"Page: 1/{len(embeds)}")
        msg = await ctx.send(embed=embeds[0])

        for reaction in reactions:
            await msg.add_reaction(reaction)

        total_pages = len(embeds) - 1
        current_page = 0

        def check(c_reaction: discord.Reaction, c_user: discord.Member):
            """Checking messages reactions"""
            message_check = False
            user_check = False
            channel_check = False
            react_check = False

            if c_reaction.message.id == msg.id:
                message_check = True
            if c_user.id == ctx.author.id:
                user_check = True
            if c_reaction.message.channel.id == msg.channel.id:
                channel_check = True
            if str(c_reaction.emoji) in reactions:
                react_check = True

            return all([message_check, user_check, channel_check, react_check])

        while True:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=300.0)
            except asyncio.TimeoutError:
                await msg.clear_reactions()
                return
            else:
                if str(reaction.emoji) == reactions[0]:  # first page
                    current_page = 0

                elif str(reaction.emoji) == reactions[1]:  # one page back
                    current_page -= 1
                    if current_page < 0:
                        current_page = total_pages

                elif str(reaction.emoji) == reactions[2]:  # stop
                    await msg.clear_reactions()
                    return

                elif str(reaction.emoji) == reactions[3]:  # one page forward
                    current_page += 1
                    if current_page > total_pages:
                        current_page = 0

                elif str(reaction.emoji) == reactions[4]:  # last page
                    current_page = total_pages

                await msg.remove_reaction(str(reaction.emoji), ctx.author)

                embeds[current_page].set_footer(text=f'Page: {current_page + 1}/{total_pages + 1}')
                await msg.edit(embed=embeds[current_page])

    @character.error
    @anime.error
    @sauce.error
    async def error_handler(self, ctx: Context, error: Exception):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("No name provided")

        elif isinstance(error, CommandOnCooldown):
            seconds = error.retry_after
            seconds = round(seconds, 2)
            hours, remainder = divmod(int(seconds), 3600)
            minutes, seconds = divmod(remainder, 60)
            await ctx.send(
                f'**You are on Cooldown:** '
                f'{seconds}s remaining.'
            )

        else:
            await self.bot.handle_error(error)


def setup(bot: Waifu):
    bot.add_cog(MyAnimeList(bot))
