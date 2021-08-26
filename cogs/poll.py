# noinspection PyPackageRequirements
from discord.ext.commands import Context
from discord.ext import commands
import discord

from bot import Waifu
import datetime


class Poll(commands.Cog):

    def __init__(self, bot: Waifu):
        self.bot = bot

    @property
    def reactions(self):
        return {
            1: '1️⃣',
            2: '2️⃣',
            3: '3️⃣',
            4: '4️⃣',
            5: '5️⃣',
            6: '6️⃣',
            7: '7️⃣',
            8: '8️⃣',
            9: '9️⃣',
            10: '🔟'
        }

    @commands.command(pass_context=True)
    async def suggest(self, ctx: Context, *, text: str):
        """Create a poll to suggest things so that people can react"""

        embed = discord.Embed(colour=0x6DD300)
        embed.set_author(name=f'Poll by {ctx.author}', icon_url=ctx.author.avatar_url)
        embed.description = text
        msg = await ctx.send(embed=embed)
        await msg.add_reaction('👍')
        await msg.add_reaction('👎')
        await ctx.message.delete()

    @commands.command()
    async def poll(self, ctx: Context, desc: str, *choices):
        """ Create a new poll """

        if len(choices) < 2:
            if len(choices) == 1:
                return await ctx.send("Can't make a poll with only one choice")
            return await ctx.send("You have to enter two or more choices to make a poll")

        if len(choices) > 10:
            return await ctx.send("You can't make a poll with more than 10 choices")

        await ctx.message.delete()

        embed = discord.Embed(description=f"**{desc}**\n\n" + "\n\n".join(
            f"{str(self.reactions[i])}  {choice}" for i, choice in enumerate(choices, 1)),
                              timestamp=datetime.datetime.utcnow(), color=discord.colour.Color.dark_blue())
        embed.set_footer(text=f"Poll by {str(ctx.author)}")

        msg = await ctx.send(embed=embed)
        for i in range(1, len(choices) + 1):
            await msg.add_reaction(self.reactions[i])


def setup(bot: Waifu):
    bot.add_cog(Poll(bot))
