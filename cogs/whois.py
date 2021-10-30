from discord.ext.commands import Context
from discord.ext import commands
from bot import Waifu
import discord

from cogs.utils.time import human_timedelta

from typing import Union
import datetime


class WhoIs(commands.Cog):
    """Returns an embed containing information about a user"""

    def __init__(self, bot: Waifu):
        self.bot = bot

    @commands.command(aliases=['info'])
    async def whois(self, ctx: Context, *, member: Union[discord.Member, discord.User] = None):
        """Get information about a user"""
        member = member or ctx.author

        if isinstance(member, discord.Member):
            join_date = self.bot.format_time(member.joined_at)
            create_date = self.bot.format_time(member.created_at)
            role_list = [role.mention for role in member.roles[1:]]
            roles = ' '.join(reversed(role_list))

            perm_list = [perm[0] for perm in member.guild_permissions if perm[1]]
            perms_list = [perm.replace('_', ' ').title() for perm in perm_list]
            perms = ', '.join(perms_list)

            embed = discord.Embed(title=member.display_name, colour=member.top_role.color,
                                  timestamp=datetime.datetime.utcnow())
            embed.set_thumbnail(url=member.avatar_url)

            embed.set_author(name=str(member), icon_url=member.avatar_url)
            embed.add_field(name='Status', value=f'{str(member.status).upper()}')
            embed.add_field(name='Top Role', value=member.top_role.mention or "None", inline=True)
            embed.add_field(name='Nickname', value=member.nick, inline=True)
            embed.add_field(name='Joined', value=f"{human_timedelta(member.joined_at, accuracy=2)}\n({join_date})", inline=True)
            embed.add_field(name='Registered', value=f"{human_timedelta(member.created_at, accuracy=2)}\n({create_date})", inline=False)
            embed.add_field(name=f'Roles [{len(role_list)}]', value=f'{roles}' or "None", inline=False)
            embed.add_field(name=f'Permissions', value=f'{perms}', inline=False)

            embed.set_footer(icon_url=ctx.author.avatar_url, text=f'ID:{member.id} ')

            await ctx.send(embed=embed)

        elif isinstance(member, discord.User):
            create_date = self.bot.format_time(member.created_at)

            embed = discord.Embed(title=member.display_name, colour=member.color)
            embed.set_author(name=str(member), icon_url=member.avatar_url)
            embed.set_thumbnail(url=member.avatar_url)

            embed.add_field(name="User information", value="\u200b")
            embed.add_field(name="Name", value=str(member), inline=False)
            embed.add_field(name="ID", value=member.id, inline=False)
            embed.add_field(name="Bot", value=member.bot, inline=False)
            embed.add_field(name='Registered', value=f"{human_timedelta(member.created_at, accuracy=2)}\n({create_date})", inline=False)
            embed.add_field(name='Mention', value=member.mention, inline=False)

            await ctx.send(embed=embed)


def setup(bot: Waifu):
    bot.add_cog(WhoIs(bot))
