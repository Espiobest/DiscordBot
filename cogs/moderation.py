from discord.ext.commands import Context
from discord.ext import commands
from discord.ext import tasks
import discord

import cogs.utils.time as t
from bot import Waifu

from typing import Optional, Union
from datetime import datetime
import asyncio
import json


class Moderation(commands.Cog):

    def __init__(self, bot: Waifu):
        self.bot = bot
        self.logs_channel = self.bot.get_channel(784859378984681492)
        self.check_time.start()

    async def check(self, guild: discord.Guild) -> int:
        g_id = str(guild.id)
        logs = await self.bot.con.fetchrow("SELECT * FROM modlogs WHERE guild_id = $1 ORDER BY case_number DESC", g_id)
        if not logs:
            case_number = 1
        else:
            case_number = logs["case_number"]+1
        return case_number

    async def log(self, ctx: Context, member: discord.Member, reason: str, case: str, expires_at: datetime = None):

        if case == "Mute":
            muted = await self.bot.con.fetchrow("SELECT muted_members FROM guild_config WHERE guild_id = $1", ctx.guild.id)
            if muted[0]:
                muted_members = json.loads(muted[0])
            else:
                muted_members = {}
            if expires_at:
                expire_time = expires_at.isoformat()
            else:
                expire_time = None
            muted_members[str(member.id)] = expire_time
            muted_members = json.dumps(muted_members)
            await self.bot.con.execute("UPDATE guild_config SET muted_members = $1 WHERE guild_id = $2", muted_members, ctx.guild.id)

        g_id = str(ctx.guild.id)
        mod = str(ctx.author.id)
        reason = reason or "None"
        case_number = await self.check(ctx.guild)
        time = datetime.utcnow()
        m_id = str(member.id)
        query = """INSERT INTO modlogs (user_id, guild_id, case_type, reason, moderator, case_number, time_at, expires_at) 
                   VALUES($1, $2, $3, $4, $5, $6, $7, $8)
                   ON CONFLICT DO NOTHING"""
        await self.bot.con.execute(query, m_id, g_id, case, reason, mod, case_number, time, expires_at)

    @commands.command(aliases=["purge", "remove"])
    @commands.has_guild_permissions(manage_messages=True)
    async def clear(self, ctx: Context, member: Optional[discord.Member] = None, num: int = 0):
        """
        Delete a specific number of recent messages. Member is an optional argument.
        You are required to have the manage messages permission to use this
        """

        await ctx.message.delete()
        if member:
            num = 20 if num > 20 else num
            count = 0
            async for msg in ctx.channel.history(limit=None):
                if msg.author.id == member.id:
                    await msg.delete()
                    count += 1
                    if count == num:
                        return
        num = 100 if num > 100 else num
        await ctx.channel.purge(limit=num)

    def embedify(self, member: discord.Member, mod: discord.Member, case: str, case_number: int,
                 reason: str = None, sl_time: int = None) -> discord.Embed:
        """Returns an embed for modlogs"""
        e = discord.Embed(timestamp=datetime.utcnow(), color=discord.Color.random())

        if isinstance(member, discord.Member):
            name = member.display_name
        else:
            name = member

        if case == 'Unban':
            e.set_author(name=f'Case {case_number} | {case} | {name}')
            e.add_field(name="User", value=f"{member.name}#{member.discriminator}")
        else:
            e.set_author(name=f'Case {case_number} | {case} | {name}', icon_url=member.avatar_url)
            e.add_field(name="User", value=member.mention)

        e.add_field(name='Moderator', value=mod.mention)
        e.add_field(name='Reason', value=reason)

        if sl_time:
            e.add_field(name='Length', value=sl_time)

        e.set_footer(text=f'ID: {member.id}')

        return e

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def purgeall(self, ctx: Context, member: discord.Member = None):
        """Purge all messages sent by a user. You are required to be an admin to use this command."""
        member = member or ctx.author

        def check(m):
            return m.content.lower() in ['yes', 'no', 'y', 'n'] and m.author.id == ctx.author.id

        message = await ctx.send(f'Are you sure you want to delete all '
                                 f'messages sent by {str(member)} in {ctx.channel.mention}?')

        response = await self.bot.wait_for('message', check=check)
        await message.delete()

        if response.content.lower() in ('yes', 'y'):
            async for msg in ctx.channel.history(limit=None):
                if msg.author.id == member.id:
                    await msg.delete()

    @commands.command()
    @commands.has_guild_permissions(kick_members=True)
    async def mute(self,
                   ctx: Context,
                   member: discord.Member = None,
                   time: Optional[t.FutureTime] = None,
                   *, reason: str = None):
        """
        Mutes a member in the server.
        Time formats-
        `d`- Days
        `h`- Hours
        `m`- Minutes
        `w`- Weeks
        `s`- Seconds
        """
        if time is not None:
            difference = time.dt - datetime.utcnow()

            if "days" in str(difference):
                mute_time = str(difference).split(",")[0]
            else:
                seconds_in_day = 24 * 60 * 60
                times = divmod(difference.days * seconds_in_day + difference.seconds, 60)
                if times[0] == 0:
                    mute_time = f"{times[1]} second{'s'*(times[1]>1)}"
                else:
                    if (times[0] % 60) == 0:
                        hours = times[0] // 60
                        mute_time = f"{hours} hour{'s'*(hours>1)}"
                    else:
                        mute_time = f"{times[0]} minute{'s'*(times[0]>1)}"
            expires_at = time.dt

        else:
            expires_at = None
            mute_time = None

        if member is None and reason is None:
            return await ctx.send_help(self.bot.get_command('mute'))

        muted_role_id = (await self.bot.con.fetchrow("SELECT muted_role_id FROM guild_config WHERE guild_id = $1", ctx.guild.id))[0]

        muted_role = ctx.guild.get_role(int(muted_role_id))

        if muted_role is None:
            muted_role = await ctx.guild.create_role(
                name="Muted",
                color=discord.Color(value=1),
                reason=f"Muted Role by {ctx.author} (ID: {ctx.author.id})",
            )

            for channel in ctx.guild.text_channels:
                await channel.set_permissions(muted_role, send_messages=False)

            await self.bot.con.execute("UPDATE guild_config SET muted_role_id = $1 WHERE guild_id = $2", muted_role.id, ctx.guild.id)

        if member.id == ctx.author.id:
            return await ctx.send('You cannot mute yourself', delete_after=3)
        elif muted_role in member.roles:
            return await ctx.send(f'{member} is already muted', delete_after=5)

        reason = reason or None
        case = "Mute"

        await member.add_roles(muted_role)

        if member.voice:
            await member.edit(mute=True)
        msg = f"You were muted in {ctx.guild.name}"

        if time:
            msg += f" for {mute_time}"
        if reason:
            msg += f" for {reason}"

        embed = self.bot.embed(f"*{member} has been muted.*")
        await ctx.send(embed=embed)
        await ctx.message.delete()

        try:
            await member.send(embed=self.bot.em(description=msg))
        except:
            pass

        num = await self.check(ctx.guild)
        e = self.embedify(member, ctx.author, case, num, reason, mute_time)
        await self.logs_channel.send(embed=e)
        await self.log(ctx, member, reason, case, expires_at)

    @commands.command()
    @commands.has_guild_permissions(kick_members=True)
    async def unmute(self, ctx: Context, member: discord.Member = None, *, reason: str = None):
        """Unmutes a previously muted member"""

        if member is None:
            return await ctx.send_help(self.bot.get_command('unmute'))

        if member is not None:
            if member.id == ctx.author.id:
                await ctx.send('You cannot use this command on yourself')
            else:
                case = "Unmute"
                await self.log(ctx, member, reason, case)

                role = discord.utils.find(lambda r: r.name == 'Muted', ctx.guild.roles)

                if role in member.roles:

                    await member.remove_roles(role)

                    if member.voice:
                        await member.edit(mute=False)

                    try:
                        await member.send(embed=self.bot.em(description=f"You have been unmuted in {ctx.guild.name}"))

                    except:
                        pass

                    embed = self.bot.embed(f"*{member} has been unmuted.*", colour=0xff0000, emoji=False)
                    await ctx.send(embed=embed)
                    await ctx.message.delete()

                    num = await self.check(ctx.guild)
                    e = self.embedify(member, ctx.author, case, num, reason)
                    await self.logs_channel.send(embed=e)
                else:
                    await ctx.send(f'{member} is not muted')
        else:
            await ctx.send('Invalid argument')

    @commands.command()
    @commands.has_guild_permissions(ban_members=True)
    async def ban(self, ctx: Context, member: Union[discord.User, discord.Member] = None, delete: Optional[int] = 0, *,
                  reason: str = None):
        """
        Permanently bans a member from the server.
        You and the bot need the ban members permission for this command to work.
        """

        banned_users = [entry.user for entry in await ctx.guild.bans()]

        if member is None:
            return await ctx.send_help(self.bot.get_command('ban'))

        if isinstance(member, discord.Member) and member.top_role >= ctx.author.top_role:
            await ctx.send('You cannot ban someone with higher roles than you.', delete_after=4)

        elif member in banned_users:
            embed = self.bot.er_embed(content=f"{member} is already banned.")
            await ctx.send(embed=embed, delete_after=3)

        elif ctx.author != member:

            if delete < 0:
                return await ctx.send("Invalid number of days provided for deleting messages", delete_after=5)

            delete = delete <= 7 and delete or 7
            reason = reason or "None"
            case = "Ban"
            await self.log(ctx, member, reason, case)

            try:
                await member.send(embed=self.bot.em(
                    description=f"You were banned in {ctx.guild.name}" + ['.', f" for {reason}."][reason != "None"])
                )

            except:
                pass

            await ctx.guild.ban(user=member, reason=reason, delete_message_days=delete)

            embed = self.bot.embed(f"*{member} has been banned.*")
            await ctx.send(embed=embed)
            await ctx.message.delete()

            num = await self.check(ctx.guild)
            e = self.embedify(member, ctx.author, case, num, reason)
            await self.logs_channel.send(embed=e)

        else:
            await ctx.send("You can't ban yourself")

    @commands.command()
    @commands.has_guild_permissions(ban_members=True)
    async def unban(self, ctx: Context, user: discord.User = None, *, reason: str = "None"):
        """Unbans a member from the server. You and the bot need the ban members permission for this command to work"""

        if user is None:
            return await ctx.send_help(self.bot.get_command('unban'))

        banned_users = [entry.user for entry in await ctx.guild.bans()]

        if user in banned_users:
            case = "Unban"

            await self.log(ctx, user, reason, case)

            await ctx.message.delete()
            await ctx.guild.unban(user=user, reason=reason)

            embed = self.bot.embed(f"*{user} has been unbanned.*")
            await ctx.send(embed=embed)

            num = await self.check(ctx.guild)
            e = self.embedify(user, ctx.author, case, num, reason)
            await self.logs_channel.send(embed=e)
            return

        else:
            embed = self.bot.er_embed(f"{user} is not banned.")
            await ctx.send(embed=embed, delete_after=5)

    @commands.command()
    @commands.has_guild_permissions(kick_members=True)
    async def kick(self, ctx: Context, member: discord.Member = None, *, reason: str = None):
        """Kicks a member from the server. You and the bot need the kick members permission to use this command"""

        if member is None and reason is None:
            return await ctx.send_help(self.bot.get_command('kick'))

        if member.top_role >= ctx.author.top_role:
            await ctx.send("You can't kick someone with equal or higher roles", delete_after=6)

        elif ctx.author != member:

            reason = reason or "None"
            case = "Kick"
            await self.log(ctx, member, reason, case)

            try:
                await member.send(embed=self.bot.em(
                    description=f"You were kicked from {ctx.guild.name}" + ['.', f" for {reason}."][reason != "None"]
                ))

            except:
                pass

            await member.kick(reason=reason)

            embed = self.bot.embed(f"*{member} has been kicked.*")
            await ctx.send(embed=embed)

            await ctx.message.delete()
            num = await self.check(ctx.guild)
            e = self.embedify(member, ctx.author, case, num, reason)
            await self.logs_channel.send(embed=e)

        else:
            await ctx.send("You can't kick yourself")

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def modlogs(self, ctx: Context, member: Union[discord.Member, discord.User] = None):
        """Check the modlogs for a user. You need to be an administrator to use this."""

        member = member or ctx.author
        m_id = str(member.id)
        g_id = str(ctx.guild.id)

        logs = await self.bot.con.fetch("SELECT * FROM modlogs WHERE user_id = $1 AND guild_id = $2", m_id, g_id)

        if not logs:
            return await ctx.send(embed=discord.Embed(description=f'No modlogs found for `{str(member)}`'))

        paginator = commands.Paginator(prefix="", suffix="")
        for record in logs:
            time = self.bot.format_time(record["time_at"],fmt='%b %d %Y %H:%M:%S')
            moderator = self.bot.get_user(int(record["moderator"])) or record["moderator"]

            paginator.add_line(f'**Case {record["case_number"]}**')
            paginator.add_line(f'**Type:** {record["case_type"]}')
            paginator.add_line(f'**Moderator:** {moderator}')
            paginator.add_line(f'**Reason:** {record["reason"]}')
            paginator.add_line(f'**At:** {time}')
            paginator.add_line('')

        await ctx.send(f"{len(logs)} modlogs found for {str(member)}")
        for page in paginator.pages:
            embed = discord.Embed(title="Logs", description=page, color=discord.Color.blurple())
            await ctx.send(embed=embed)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def clearlogs(self, ctx: Context, member: Union[discord.Member, discord.User]):
        """Clear the logs of a user"""
        m_id = str(member.id)
        await self.bot.con.execute("DELETE FROM modlogs WHERE user_id = $1", m_id)
        await ctx.message.delete()

    @commands.command()
    @commands.has_guild_permissions(kick_members=True)
    async def warn(self, ctx: Context, member: discord.Member = None, *, reason: str = None):
        """Warns a member."""

        if member is None or reason is None:
            return await ctx.send_help(self.bot.get_command('warn'))

        if member != ctx.author:
            case = 'Warn'
            reason = reason or "None"

            await self.log(ctx, member, reason, case)

            embed = self.bot.embed(f"*{member} has been warned.*")
            await ctx.send(embed=embed)

            await ctx.message.delete()

            num = await self.check(ctx.guild)
            e = self.embedify(member, ctx.author, case, num, reason)
            await self.logs_channel.send(embed=e)
            try:
                await member.send(embed=self.bot.em(description=f"You were warned in {ctx.guild.name} for {reason}."))
            except:
                pass
        else:
            await ctx.send('You cannot warn yourself')

    @commands.command(name="multiban", aliases=["massban", ])
    @commands.guild_only()
    @commands.has_guild_permissions(ban_members=True)
    async def multi_ban(self,
                        ctx: Context,
                        members: commands.Greedy[Union[discord.Member, discord.User]],
                        *, reason: str = None):
        """
        Permanently bans multiple member from the server.
        This only works through banning via ID.
        """
        if reason is None:
            reason = f'Action done by {ctx.author} (ID: {ctx.author.id})'

        total_members = len(members)
        if total_members == 0:
            return await ctx.send('Missing members to ban.')

        if ctx.author in members:
            return await ctx.send("You can't ban yourself")

        failed = 0
        for member in members:
            if member.top_role >= ctx.author.top_role:
                raise commands.BadArgument('You cannot do this action on one of the users.')
            try:
                await ctx.guild.ban(member, reason=reason)
            except discord.HTTPException:
                failed += 1

        await ctx.send(f'Banned {total_members - failed}/{total_members} members.')
        reason = reason or "None"
        case = "Ban"
        for m in members:
            num = await self.check(ctx.guild)
            await self.log(ctx, m, reason, case)
            e = self.embedify(m, ctx.author, case, num, reason)
            await self.logs_channel.send(embed=e)

    @tasks.loop(minutes=1)
    async def check_time(self):
        for guild in self.bot.guilds:
            muted = None
            try:
                muted = await self.bot.con.fetchrow("SELECT muted_members FROM guild_config WHERE guild_id = $1", guild.id)
            except Exception as e:
                self.check_time.stop()
                await self.bot.handle_error(e)

            if muted is None:
                continue

            if muted[0]:

                remove = []
                muted_dict = json.loads(muted[0])

                for _id, time in muted_dict.items():
                    if time is None:
                        continue
                    expires_at = datetime.fromisoformat(time)

                    if expires_at < datetime.utcnow():
                        member = guild.get_member(int(_id))

                        muted_role_id = (await self.bot.con.fetchrow(
                            "SELECT muted_role_id FROM guild_config WHERE guild_id = $1", guild.id)
                                         )[0]

                        muted_role = guild.get_role(int(muted_role_id))

                        await member.remove_roles(muted_role)

                        if member.voice:
                            await member.edit(mute=False)

                        remove.append(str(member.id))

                        reason = "Auto Unmute"
                        case = "Unmute"

                        g_id = str(guild.id)
                        mod = str(self.bot.user.id)
                        reason = reason or "None"
                        case_number = await self.check(guild)
                        time = datetime.utcnow()
                        m_id = str(member.id)
                        expires_at = None
                        query = """INSERT INTO modlogs (user_id, guild_id, case_type, reason, moderator, case_number, time_at, expires_at)
                                   VALUES($1, $2, $3, $4, $5, $6, $7, $8)
                                   ON CONFLICT DO NOTHING"""

                        await self.bot.con.execute(query, m_id, g_id, case, reason, mod, case_number, time, expires_at)

                        num = await self.check(guild)
                        e = self.embedify(member, self.bot.user, case, num, reason)
                        await self.logs_channel.send(embed=e)
                        try:
                            await member.send(embed=self.bot.em(description=f'You have been unmuted in {guild.name}.'))
                        except:
                            pass

                for member in remove:
                    muted_dict.pop(member)
                muted_members = json.dumps(muted_dict)

                await self.bot.con.execute("UPDATE guild_config SET muted_members = $1 WHERE guild_id = $2",
                                            muted_members, guild.id)
            await asyncio.sleep(10)

    # @commands.Cog.listener()
    # async def on_disconnect(self):
    #     self.check_time.stop()


def setup(bot: Waifu):
    bot.add_cog(Moderation(bot))
