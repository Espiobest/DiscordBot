from discord.errors import HTTPException
from discord.ext import commands

from bot import Waifu

import discord

from datetime import datetime
from typing import Union


class Logs(commands.Cog):

    def __init__(self, bot: Waifu):
        self.bot = bot
        self.log_channel = self.bot.get_channel(784859378984681492)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        """Called when multiple messages are deleted/ purged"""
        log_channel_id = await self.bot.con.fetchval("SELECT log_channel FROM guild_config WHERE guild_id = $1",
                                                     payload.guild_id)

        if log_channel_id is None:
            return

        log_channel = self.bot.get_guild(payload.guild_id).get_channel(log_channel_id)

        if log_channel is None:
            return

        channel = self.bot.get_channel(payload.channel_id)

        try:
            author = payload.cached_messages[0].author
        except IndexError:
            author = self.bot.user

        embed = discord.Embed(color=discord.Color.blue())
        embed.set_author(name=author, icon_url=author.avatar_url)
        embed.add_field(name='Bulk Message Delete',
                        value=f"{len(payload.message_ids)} messages deleted in {channel.mention}")
        try:
            await log_channel.send(embed=embed)

        except Exception as e:
            return await self.bot.handle_error(e)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        """Called when a message is deleted."""
        log_channel_id = await self.bot.con.fetchval("SELECT log_channel FROM guild_config WHERE guild_id = $1",
                                                     payload.guild_id)

        if log_channel_id is None:
            return

        log_channel = self.bot.get_guild(payload.guild_id).get_channel(log_channel_id)
        # print(log_channel, log_channel_id[0], type(log_channel_id[0]), payload.guild_id, self.bot.get_guild(payload.guild_id))

        if log_channel is None:
            return

        channel = self.bot.get_channel(payload.channel_id)

        if not payload.cached_message:
            return

        if channel == log_channel:
            return

        author = payload.cached_message.author
        message = payload.cached_message
        content = message.content

        if content == '':
            content = "Blank Message"

        embed = discord.Embed(color=discord.Color.red(),
                              description=f'**Message sent by {author} deleted in **{channel.mention}',
                              timestamp=datetime.utcnow())
        embed.set_author(name=author, icon_url=author.avatar_url)

        if message.embeds:
            deleted_embed = message.embeds[0]
            description = deleted_embed.description

            if deleted_embed.image:
                embed.set_image(url=deleted_embed.image.url)

            if not description:
                description = "No description"
            else:
                description = "This is the description: " + description
            embed.add_field(name=f"{author} sent an embed:", value=description, inline=False)
            embed.add_field(name="Content", value=content, inline=False)
            for field in deleted_embed.fields:
                embed.add_field(name=field.name, value=field.value, inline=field.inline)

        else:
            embed.add_field(name='Message:', value=content)

        embed.set_footer(text=f'Author: {author.id} | Message ID: {message.id}')

        try:
            await log_channel.send(embed=embed)
        except HTTPException:
            await log_channel.send(embed=self.bot.em(description="Long embed", colour=discord.Colour.red()))

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Called when a message is edited"""

        # if before.guild.id != 743222429437919283:
        #    return
        log_channel_id = await self.bot.con.fetchval("SELECT log_channel FROM guild_config WHERE guild_id = $1", before.guild.id)

        if log_channel_id is None:
            return

        channel = before.channel
        log_channel = before.guild.get_channel(log_channel_id)

        if log_channel is None:
            return

        if channel == log_channel:
            return

        author = before.author
        if author.bot:
            return

        old_content = before.content
        new_content = after.content
        if old_content == new_content:
            return

        embed = discord.Embed(colour=discord.Colour.blurple(), timestamp=datetime.utcnow())
        embed.set_author(name=author, icon_url=author.avatar_url)
        embed.add_field(name=f"Message Edited by {author}",
                        value=f"In {channel.mention} [Jump to Message]({before.jump_url})", inline=False)
        embed.add_field(name='Before', value=old_content, inline=False)
        embed.add_field(name='After', value=new_content, inline=False)
        embed.set_footer(text=f"ID: {author.id}")

        try:
            await log_channel.send(embed=embed)

        except Exception as e:
            return await self.bot.handle_error(e)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: Union[discord.TextChannel, discord.VoiceChannel]):
        """Called when a new channel is created in the server"""

        log_channel_id = await self.bot.con.fetchval("SELECT log_channel FROM guild_config WHERE guild_id = $1",
                                                     channel.guild.id)

        if log_channel_id is None:
            return

        log_channel = channel.guild.get_channel(log_channel_id)

        if log_channel is None:
            return

        embed = discord.Embed(title=f'Created Channel {channel.name}', timestamp=channel.created_at,
                              color=discord.Color.green())

        embed.set_thumbnail(url=channel.guild.icon_url)
        embed.set_footer(text=f"ID: {channel.id}")
        embed.add_field(name=channel.guild.name, value=channel.mention)
        embed.add_field(name='Category', value=channel.category)

        try:
            await log_channel.send(embed=embed)

        except Exception as e:
            return await self.bot.handle_error(e)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: Union[discord.TextChannel, discord.VoiceChannel]):
        """Called when a channel is deleted from the server"""

        log_channel_id = await self.bot.con.fetchval("SELECT log_channel FROM guild_config WHERE guild_id = $1",
                                                     channel.guild.id)

        if log_channel_id is None:
            return

        log_channel = channel.guild.get_channel(log_channel_id)

        if log_channel is None:
            return

        embed = discord.Embed(title=f"Deleted channel {channel.name}", timestamp=datetime.utcnow(),
                              color=discord.Color.dark_red())
        embed.set_thumbnail(url=channel.guild.icon_url)
        embed.add_field(name='Category', value=channel.category)

        try:
            await log_channel.send(embed=embed)

        except Exception as e:
            return await self.bot.handle_error(e)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Called when a member is removed from the server"""

        log_channel_id = await self.bot.con.fetchval("SELECT log_channel FROM guild_config WHERE guild_id = $1",
                                                     member.guild.id)

        if log_channel_id is None:
            return

        log_channel = member.guild.get_channel(log_channel_id)

        if log_channel is None:
            return

        bans = await member.guild.bans()
        if any(entry.user.id == member.id for entry in bans):
            return

        embed = discord.Embed(title="Member left", description=f"{member.mention} left the server {member}",
                              color=discord.Color.orange())
        try:
            await log_channel.send(embed=embed)

        except Exception as e:
            return await self.bot.handle_error(e)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Called when a member updates their profile"""

        log_channel_id = await self.bot.con.fetchval("SELECT log_channel FROM guild_config WHERE guild_id = $1",
                                                     before.guild.id)

        if log_channel_id is None:
            return

        log_channel = before.guild.get_channel(log_channel_id)

        if log_channel is None:
            return

        embed = discord.Embed(color=discord.Color.dark_gold(), timestamp=datetime.utcnow())
        embed.set_footer(text=f"ID: {before.id}")
        embed.set_author(name=before, icon_url=before.avatar_url)

        if before.nick != after.nick:
            embed.title = f"{before} Nickname Change"

            embed.add_field(name='Before', value=before.nick)
            embed.add_field(name='After', value=after.nick)

        elif before.roles != after.roles:
            if len(before.roles) < len(after.roles):
                role = next(role for role in after.roles if role not in before.roles)
                embed.description = f"**{after.mention} was given the `{role.name}` role**"
            else:
                role = next(role for role in before.roles if role not in after.roles)
                embed.description = f"**{after.mention} was removed from the `{role.name}` role**"

        # elif before.status != after.status:
        #     embed.title = f"{before} Status Changed"
        #     embed.set_author(name=before, icon_url=before.avatar_url)
        #     embed.add_field(name='Before', value=before.status)
        #     embed.add_field(name='After', value=after.status)

        else:
            return

        try:
            await log_channel.send(embed=embed)

        except Exception as e:
            return await self.bot.handle_error(e)

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        """Called when a user updates their profile"""

        embed = discord.Embed(color=discord.Color.blurple(), timestamp=datetime.utcnow())
        embed.set_author(name=before, icon_url=before.avatar_url)
        embed.set_footer(text=f"ID: {before.id}")

        if before.avatar_url != after.avatar_url:
            embed.description = f"{before.mention} Avatar Change"
            embed.set_image(url=after.avatar_url)
            embed.set_thumbnail(url=before.avatar_url)

        elif before.name != after.name:
            embed.description = f"{before.mention} Username Change"
            embed.add_field(name='Before', value=before.name)
            embed.add_field(name='After', value=after.name)
            embed.set_thumbnail(url=after.avatar_url)

        elif before.discriminator != after.discriminator:
            embed.description = f"{before.mention} Discriminator Change"
            embed.add_field(name='Before', value=before)
            embed.add_field(name='After', value=after)
            embed.set_thumbnail(url=after.avatar_url)

        else:
            return

        await self.log_channel.send(embed=embed)


def setup(bot: Waifu):
    bot.add_cog(Logs(bot))
