from discord.ext.commands import Context
from discord.ext import commands
from bot import Waifu
import discord

import random
import time


class Level(commands.Cog):

    def __init__(self, bot: Waifu):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return
        m_id = str(message.author.id)
        g_id = str(message.guild.id)
        channel_id = str(message.channel.id)
        message_id = str(message.id)

        get_user = """SELECT * FROM users 
                      WHERE user_id = $1 AND
                      guild_id = $2"""

        user = await self.bot.con.fetchrow(get_user, m_id, g_id)

        query = """INSERT INTO messages(author_id, guild_id, content, created_at, channel_id, message_id)
                   VALUES ($1, $2, $3, $4, $5, $6)
                   ON CONFLICT DO NOTHING"""

        await self.bot.con.execute(query, m_id, g_id, message.content, message.created_at, channel_id, message_id)

        if not user:
            insert = """INSERT INTO users(user_id, guild_id, level, xp, last_msg, muted, message_count) 
                        VALUES($1, $2, $3, $4, $5, $6, $7)"""
            await self.bot.con.execute(insert, m_id, g_id, 1, 0, time.time() - 60, False, 1)
            user = await self.bot.con.fetchrow(get_user, m_id, g_id)

        get_levels = """SELECT * FROM level_settings
                        WHERE guild_id = $1"""

        result = await self.bot.con.fetchrow(get_levels, g_id)
        if not result:
            level = """INSERT INTO level_settings(guild_id, multiplier) 
                       VALUES($1, $2)"""
            await self.bot.con.execute(level, g_id, 1)
            result = await self.bot.con.fetchrow(get_levels, g_id)

        msgs = user["message_count"]
        update_messages = """UPDATE users 
                             SET message_count = $1 
                             WHERE user_id = $2 AND 
                             guild_id = $3"""
        if not msgs:
            await self.bot.con.execute(update_messages, 1, m_id, g_id)
        else:
            msg_count = int(msgs) + 1
            await self.bot.con.execute(update_messages, msg_count, m_id, g_id)

        if user['muted']:
            return

        if time.time() - int(user["last_msg"]) > 60:
            xp = user["xp"] + random.randint(20, 25) * result["multiplier"]
            set_xp = """UPDATE users 
                        SET xp = $1, 
                        last_msg = $2 
                        WHERE user_id = $3 AND 
                        guild_id = $4"""
            await self.bot.con.execute(set_xp, xp, time.time(), m_id, g_id)

            cur_level = int(user["level"])
            exp_end = int(5 * (cur_level**2) + 50 * cur_level + 100)

            if xp > exp_end:
                level_up = """UPDATE users 
                              SET xp = $1, level = $2 
                              WHERE guild_id = $3 AND 
                              user_id = $4"""
                await self.bot.con.execute(level_up, abs(exp_end-xp), cur_level+1, g_id, m_id)
                if message.guild.id == 743222429437919283:
                    await message.channel.send(f"{message.author} has advanced to level {cur_level+1}")

    @commands.command(aliases=['level'])
    async def rank(self, ctx: Context, member: discord.Member = None):
        """Check your rank in the server"""
        member = member or ctx.author
        m_id = str(member.id)
        g_id = str(ctx.guild.id)
        rank = """SELECT * FROM users 
                  WHERE guild_id = $1 AND 
                  user_id = $2"""
        result = await self.bot.con.fetchrow(rank, g_id, m_id)

        if not result:
            return await ctx.send(f'{member} has not talked and is therefore unranked')

        cur_level = int(result["level"])
        exp_end = int(5 * (cur_level ** 2) + 50 * cur_level + 100)
        embed = discord.Embed(color=member.top_role.color)
        embed.set_author(name=member, icon_url=member.avatar_url)
        embed.add_field(name="Level", value=f"{cur_level}", inline=False)
        embed.add_field(name="XP", value=f"{result['xp']}/{exp_end}")
        embed.set_footer(text=f"Called by {ctx.author}")
        await ctx.send(embed=embed)

    @commands.command(aliases=["xpmul", "expmul"])
    @commands.has_permissions(administrator=True)
    async def xp_multiplier(self, ctx: Context, num: float):
        """Set the exp multiplier for the server"""
        if num > 5:
            return await ctx.send("Sorry, the maximum exp multiplier is 5")
        g_id = str(ctx.guild.id)
        settings = """SELECT * FROM level_settings
                      WHERE guild_id = $1"""
        result = await self.bot.con.fetchrow(settings, g_id)
        if not result:
            await self.bot.con.execute("INSERT INTO level_settings(guild_id, multiplier) VALUES($1,$2)", g_id, num)
        else:
            await self.bot.con.execute("UPDATE level_settings SET multiplier = $1 WHERE guild_id = $2", num, g_id)

        await ctx.send(f"The exp multiplier has been updated to {num}")

    @commands.command(aliases=["expmute", "xpmute", "mutexp"])
    @commands.has_permissions(administrator=True)
    async def exp_mute(self, ctx: Context, member: discord.Member):
        """Exp mute a member so that they cannot gain xp for talking anymore"""

        m_id = str(member.id)
        g_id = str(ctx.guild.id)
        query = """SELECT muted FROM users 
                   WHERE user_id = $1 AND 
                   guild_id = $2"""
        check = await self.bot.con.fetchval(query, m_id, g_id)

        if check:
            return await ctx.send(f"{str(member)} is already exp muted.")
        await self.bot.con.execute("UPDATE users SET muted = True WHERE user_id = $1 AND guild_id = $2", m_id, g_id)
        await ctx.send(f"{str(member)} has been exp muted.")

    @commands.command(aliases=['xpunmute', 'expunmute'])
    @commands.has_permissions(administrator=True)
    async def exp_unmute(self, ctx: Context, member: discord.Member):
        """Let a previously exp muted member gain xp by talking"""
        m_id = str(member.id)
        g_id = str(ctx.guild.id)
        query = """SELECT muted FROM users 
                   WHERE user_id = $1 AND 
                   guild_id = $2"""
        check = await self.bot.con.fetchval(query, m_id, g_id)

        if not check:
            return await ctx.send(f"{str(member)} is not exp muted.")
        await self.bot.con.execute("UPDATE users SET muted = False WHERE user_id = $1 AND guild_id = $2", m_id, g_id)
        await ctx.send(f"{str(member)} can now gain exp by talking.")


def setup(bot: Waifu):
    bot.add_cog(Level(bot))
