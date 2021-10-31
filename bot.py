from discord_components import DiscordComponents
from discord.embeds import EmptyEmbed
from discord.ext.commands import *
from discord.ext import commands
import discord

from aiohttp import ClientSession

from PIL import Image, ImageDraw, ImageFont, ImageOps
from datetime import datetime
import requests
import asyncio


from cogs.utils.db import DataBase

from typing import Union
import traceback
import logging
import dotenv
import json
import sys
import io
import os

dotenv.load_dotenv(".env")
TOKEN = os.environ.get("TOKEN")

os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
os.environ["JISHAKU_RETAIN"] = "True"
os.environ["JISHAKU_HIDE"] = "True"

cogs = [
    'cogs.moderation',
    'cogs.myanimelist',
    'cogs.poll',
    'cogs._help',
    'cogs.random_commands',
    'cogs.whois',
    'cogs.levelling',
    'cogs.tags',
    'cogs.logs',
    'cogs.joke',
    'jishaku'
]


class Waifu(commands.Bot):
    def __init__(self, **kwargs):
        intents = discord.Intents.all()
        super().__init__(command_prefix=kwargs.pop('command_prefix', ['x.', 'X.']),
                         case_insensitive=False,
                         intents=intents,
                         **kwargs)
        self.session = None
        self.con = None

    async def process_commands(self, message: discord.Message):
        if message.author.bot:
            return
        ctx = await self.get_context(message=message)
        await self.invoke(ctx)

    async def on_connect(self):
        if self.session is None:
            self.session = ClientSession()

        self.con = await DataBase.create_pool(bot=self,
                                              uri=os.environ.get('URI'),
                                              loop=self.loop
                                              )

    async def on_guild_join(self, guild: discord.Guild):
        print(f'Joined {guild.name}')
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:  # checking for channel with perms to send messages
                await channel.send(f'{self.user.name} just joined {guild.name}!')
                break

    async def on_ready(self):
        DiscordComponents(self)
        await self.change_presence(status=discord.Status.online,
                                   activity=discord.Activity(type=discord.ActivityType.playing,
                                                             name=f"""use prefix \"{self.command_prefix[0] 
                                                             if isinstance(self.command_prefix, (list, tuple))
                                                             else self.command_prefix}\""""))
        print(f'Logged on as {self.user}!')
        for ext in cogs:
            try:
                self.load_extension(ext)
            except ExtensionAlreadyLoaded:
                pass

    async def on_member_join(self, member: discord.Member):
        if member.guild.id == 837759567986688132:
            channel = self.get_channel(837759567986688132)
        elif member.guild.id == 743222429437919283:
            channel = self.get_channel(743222429437919286)
        else:
            return

        muted = None
        try:
            muted = await self.con.fetchrow("SELECT muted_members FROM guild_config WHERE guild_id = $1", member.guild.id)
        except Exception as e:
            await self.handle_error(e)

        if muted[0]:
            muted_dict = json.loads(muted[0])
            if member.id in muted_dict:
                muted_role_id = (await self.con.fetchrow("SELECT muted_role_id FROM guild_config WHERE guild_id = $1", member.guild.id))[0]

                muted_role = member.guild.get_role(int(muted_role_id))

                await member.add_roles(muted_role)

        num = member.guild.member_count
        loop = asyncio.get_running_loop()
        file = await loop.run_in_executor(None, Waifu.make_banner, member, num)

        await channel.send(f'{member.mention} has joined the server!', file=file)

        if member.bot and member.guild.id == 743222429437919283:
            role = member.guild.get_role(749030905099714680)
            await member.add_roles(role)

        if member.guild.id == 743222429437919283:
            await channel.send('Members += 1')
            await channel.send(f'Current number of members: {num}')

    async def on_message(self, message: discord.Message):
        await self.wait_until_ready()
        if not message.guild:
            return
        sent_at = self.format_time(datetime.now(), fmt="%Y-%m-%d %H:%M:%S")
        log_message = f"{message.guild.name}: #{message.channel}: @{message.author}: {message.clean_content}"
        logger.log(20, log_message)
        if not message.author.bot:
            print(f"[{sent_at}] {log_message}")
        await self.process_commands(message)

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):

        if payload.guild_id != 743222429437919283:
            return

        msg_id = payload.message_id
        roles = self.get_channel(743247134433869854)
        role_msg_id = 0
        async for msg in roles.history(limit=None):
            if msg.author.id == self.user.id:
                role_msg_id = msg.id
                break

        if msg_id == role_msg_id:
            guild_id = payload.guild_id
            guild = self.get_guild(guild_id)
            if payload.emoji.id == 743450299645296741:
                role = guild.get_role(743404080008921088)
                if role is not None:
                    member = guild.get_member(payload.user_id)
                    if member is not None:
                        await member.add_roles(role)

    async def on_command_error(self, ctx: Context, exception: Exception) -> None:
        await self.wait_until_ready()
        error = getattr(exception, 'original', exception)

        if hasattr(ctx.command, 'on_error'):
            return
        if isinstance(error, (NotOwner, CommandNotFound)):
            return
        elif isinstance(error, (MissingRequiredArgument,)):
            await ctx.send(*error.args)
        elif isinstance(error, (BadArgument, discord.Forbidden,)):
            await ctx.send(f"Bad Argument: {' '.join(error.args)}", delete_after=5)
        elif isinstance(error, (MissingPermissions,)):
            await ctx.send(f"Missing Permissions: {' '.join(error.args)}", delete_after=5)
        else:
            await self.handle_error(error)

    async def handle_error(self, error) -> None:
        error_channel = self.get_channel(804118604923928637)
        trace = traceback.format_exception(
            type(error),
            error,
            error.__traceback__
        )
        paginator = commands.Paginator(prefix="", suffix="")

        for line in trace:
            paginator.add_line(line)

        def embed_exception(text: str, *, index: int = 0) -> discord.Embed:
            embed = discord.Embed(
                color=discord.Color(value=15532032),
                description="```py\n%s\n```" % text,
                timestamp=datetime.utcnow(),
            )

            if not index:
                embed.title = "Error"

            return embed

        for page in paginator.pages:
            await error_channel.send(embed=embed_exception(page))

    @staticmethod
    def format_time(dt: datetime, fmt='%b %d, %Y at %I:%M %p'):
        """Shortcut to format `datetime` objects"""
        return dt.strftime(fmt)

    @staticmethod
    def em(**attrs) -> discord.Embed:
        """Shortcut to create `Embed` objects."""

        embed = discord.Embed(
            title=attrs.get("title", EmptyEmbed),
            description=attrs.get("description", "\u200b"),
            color=attrs.get("color", attrs.get("colour", 0x337fd5)),
            url=attrs.get("url", EmptyEmbed),
        )

        timestamp = attrs.get("timestamp")
        thumbnail = attrs.get("thumbnail")
        image = attrs.get("image")
        footer = attrs.get("footer")
        author = attrs.get("author")

        if timestamp:
            if timestamp == "now":
                embed.timestamp = datetime.utcnow()
            else:
                embed.timestamp = timestamp

        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        if image:
            embed.set_image(url=image)

        if footer is not None:
            embed.set_footer(
                text=footer, icon_url=attrs.get("footer_icon_url", EmptyEmbed)
            )

        if author:
            embed.set_author(
                name=author,
                url=attrs.get("author_url", EmptyEmbed),
                icon_url=attrs.get("author_icon_url", EmptyEmbed),
            )

        for field in attrs.get("fields", []):
            embed.add_field(**field)

        return embed

    @staticmethod
    def embed(content: str, colour: Union[int, discord.Color] = discord.Colour.green(), emoji=True) -> discord.Embed:
        """Shortcut to create "correct" `Embed` Objects"""

        if emoji:
            emoji = "<a:tick1:779481579004493855> "
        else:
            emoji = ""
        embed = discord.Embed(colour=colour)
        embed.description = f"{emoji}_**{content.strip()}**_"
        return embed

    @staticmethod
    def er_embed(content: str) -> discord.Embed:
        """Shortcut to create "wrong" `Embed` Objects"""

        emoji = "<a:cross1:779695230760910898>"
        embed = discord.Embed(colour=discord.Colour.red())
        embed.description = f"{emoji} _**{content.strip()}**_"
        return embed

    @staticmethod
    def make_banner(member: discord.Member, num: int) -> discord.File:
        """Using PIL to make a banner and sending it as a BytesIO object"""

        url = member.avatar_url
        response = requests.get(url)

        im = Image.open(io.BytesIO(response.content)).convert("RGBA")
        im = im.resize((300, 300))
        big_size = (im.size[0] * 10, im.size[1] * 10)
        mask = Image.new('L', big_size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + big_size, fill=255)
        mask = mask.resize(im.size, Image.ANTIALIAS)
        im.putalpha(mask)

        output = ImageOps.fit(im, mask.size, centering=(0.5, 0.5))
        output.putalpha(mask)
        welcome_img = "./pics/banner1.png"
        background = Image.open(welcome_img)
        draws = ImageDraw.Draw(background)
        background.paste(im, (470, 80), im)

        font = ImageFont.truetype(r'fonts/Rapier Zero.otf', 55)
        name_font = ImageFont.truetype(r'fonts/Rapier Zero.otf', 45)
        # font = ImageFont.load_default()
        # name_font = ImageFont.load_default()
        draws.text((350, 20), "Welcome to the Server", (255, 255, 255), font=font)
        draws.text((370, 410), f'Member count: {num}', (255, 255, 255), font=font)
        draws.text((30, 230), f"{member.display_name}#{member.discriminator}", (255, 255, 255), font=name_font)

        obj = io.BytesIO()
        background.save(obj, format='PNG')
        obj.seek(0)
        file = discord.File(obj, 'image.png')
        return file

    @classmethod
    async def setup(cls, **kwargs):
        BOT = cls()
        try:
            await BOT.start(TOKEN, **kwargs)
        except KeyboardInterrupt:
            if BOT.session is not None:
                await BOT.session.close()
            await BOT.close()


if __name__ == "__main__":
    logging.getLogger('discord').setLevel(logging.INFO)
    logging.getLogger('discord.http').setLevel(logging.WARNING)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(filename='log/bot.log', encoding='utf-8', mode='w')
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    frmt = logging.Formatter('[{asctime}] [{levelname:<7}] {name}: {message}', dt_fmt, style='{')
    handler.setFormatter(frmt)
    logger.addHandler(handler)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.get_event_loop().run_until_complete(Waifu.setup())
