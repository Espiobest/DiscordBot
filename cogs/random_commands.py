from cogs.utils.time import human_timedelta

from discord.ext.commands import Context
from discord.ext import commands
import discord

from gtts import gTTS

from bot import Waifu

from typing import Optional, Union
import asyncio
import random
import os
import io

channels = ['bot-commands', 'vc-bot-commands']
img_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'pics'))
img_list = [img_path + '\\' + c for c in os.listdir(img_path)]


class Random(commands.Cog):
    """Just a bunch of random, fun commands :p"""

    def __init__(self, bot: Waifu):
        self.bot = bot

    @commands.command(aliases=['av'])
    async def avatar(self, ctx: Context, *, member: Union[discord.Member, discord.User] = None):
        """Sends a user's avatar"""
        member = member or ctx.author
        embed = discord.Embed(title='Avatar', timestamp=ctx.message.created_at)
        embed.set_author(name=str(member), icon_url=member.avatar_url)
        embed.set_image(url=member.avatar_url)
        await ctx.send(embed=embed)

    @commands.command()
    async def banner(self, ctx: Context, *, user: discord.User = None):
        """Sends a user's banner if available"""
        user = user or ctx.author
        URL = "https://cdn.discordapp.com/banners/"
        banner_id = (await self.bot.http.request(discord.http.Route("GET", "/users/{uid}", uid=user.id)))['banner']
        if banner_id is None:
            return await ctx.send(f"{user} does not have a banner.", delete_after=10)

        animated = banner_id.startswith("a_")
        extension = ".gif" if animated else ".png"

        embed = discord.Embed(timestamp=ctx.message.created_at)
        embed.set_author(name=str(user), icon_url=user.avatar_url)

        if extension == ".png":
            png_link = URL + f"{user.id}/{banner_id}.png?size=4096"
            jpg_link = URL + f"{user.id}/{banner_id}.jpg?size=4096"
            webp_link = URL + f"{user.id}/{banner_id}.webp?size=4096"
            embed.add_field(name=f"Banner", value=f"[PNG]({png_link}) | [JPG]({jpg_link}) | [WEBP]({webp_link})")
        else:
            gif_link = URL + f"{user.id}/{banner_id}.gif?size=4096"
            embed.add_field(name=f"Banner", value=f"[GIF]({gif_link})")

        embed.set_image(url=URL + f"{user.id}/{banner_id}{extension}?size=4096""")
        await ctx.send(embed=embed)

    @commands.command()
    async def count(self, ctx: Context):
        """Sends the number of users in the server"""
        await ctx.send(f'{ctx.guild.name} has {ctx.guild.member_count} members.')

    @commands.command()
    async def ping(self, ctx: Context):
        """Gets the bot's latency"""
        embed = discord.Embed(title="Pong 🏓", description=f'{round(self.bot.latency * 1000)} ms',
                              colour=discord.Color.blurple())
        await ctx.send(embed=embed)

    @commands.command(aliases=['serv', 'server', 'serverinfo'])
    async def server_info(self, ctx: Context):
        """Gets information about the server"""

        member_info = f"""
                      Total: **{ctx.guild.member_count}**
                      Max: **{ctx.guild.max_members}**
                      Online: **{len([m for m in ctx.guild.members if str(m.status) == "online"])}**
                      Offline: **{len([m for m in ctx.guild.members if str(m.status) == "offline"])}**
                      """

        channel_info = f"""
                       Total: **{len(ctx.guild.channels)}**
                       Categories: **{len(ctx.guild.categories)}**
                       Text: **{len(ctx.guild.text_channels)}**
                       Voice: **{len(ctx.guild.voice_channels)}**
                       """

        other_info = f"""
                     Bots: {len([m for m in ctx.guild.members if m.bot])}
                     Roles: **{len(ctx.guild.roles)}**/ 250
                     Emojis: **{len(ctx.guild.emojis)}**/ {ctx.guild.emoji_limit * 2}
                     Boosts: **{ctx.guild.premium_subscription_count}** (Level {ctx.guild.premium_tier})
                     """

        create_date = self.bot.format_time(ctx.guild.created_at)

        embed = discord.Embed(title=f"Server: {ctx.guild.name}")
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
        embed.set_thumbnail(url=ctx.guild.icon_url)
        embed.add_field(name="Owner", value=ctx.guild.owner.mention, inline=True)
        embed.add_field(name="ID", value=ctx.guild.id, inline=True)
        embed.add_field(name="Created At", value=f"{human_timedelta(ctx.guild.created_at, accuracy=2)}\n{create_date}",
                        inline=True)
        embed.add_field(name="Members", value=member_info)
        embed.add_field(name="Channels", value=channel_info)
        embed.add_field(name="Others", value=other_info)
        embed.add_field(name="Voice Region", value=str(ctx.guild.region).title(), inline=True)

        await ctx.send(embed=embed)

    @commands.command(aliases=['msgs'])
    async def messages(self, ctx: Context, member: discord.Member = None):
        """Gets the number of messages sent by a user"""
        member = member or ctx.author
        if member.bot:
            return await ctx.send(f"{member.mention} is a bot! Messages sent by bots are not counted!")
        member = member or ctx.author
        m_id = str(member.id)
        g_id = str(ctx.guild.id)
        query = """SELECT message_count FROM users 
                    WHERE guild_id = $1 AND 
                    user_id = $2"""
        messages = await self.bot.con.fetchval(query, g_id, m_id)
        messages = messages or 0
        embed = discord.Embed(color=discord.Color.orange())
        embed.set_author(name=member.display_name, icon_url=member.avatar_url)
        embed.add_field(name='Count', value=messages)
        embed.add_field(name="Since", value=human_timedelta(member.joined_at, accuracy=2))
        embed.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @commands.command()
    async def blush(self, ctx: Context):
        """Sends a picture of Waifu"""
        await ctx.send(file=discord.File(random.choice(img_list)))

    @commands.command(aliases=["tts"])
    async def text_to_speech(self, ctx: Context, slow: Optional[bool] = False, *, message: str):
        """Sends an audio file generated from the text"""
        loop = asyncio.get_running_loop()
        file = await loop.run_in_executor(None, Random.get_speech, message, slow)
        await ctx.send(file=file)

    @staticmethod
    def get_speech(message: str, slow: bool) -> discord.File:
        text = gTTS(text=message, lang="en", slow=slow)
        obj = io.BytesIO()
        text.write_to_fp(obj)
        obj.seek(0)
        file = discord.File(obj, 'tts.mp3')
        return file

    @commands.command(aliases=['hello', 'sup'])
    async def hi(self, ctx: Context):
        """Greets you!"""
        await ctx.send(f'Hello {ctx.author.mention}!')

    @commands.command(aliases=['repeat'])
    async def say(self, ctx: Context, channel: Optional[discord.TextChannel], *, message: str):
        """Repeats what the user says"""
        channel = channel or ctx.channel
        text = await commands.clean_content().convert(ctx=ctx, argument=message)
        await ctx.message.delete()
        await channel.send(text)


def setup(bot: Waifu):
    bot.add_cog(Random(bot))
