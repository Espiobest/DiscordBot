from discord.ext import commands
import discord

from bot import Waifu

from datetime import datetime


class Joke(commands.Cog):
    """Generate a random joke"""

    def __init__(self, bot: Waifu):
        self.bot = bot
        self.base_url = "https://official-joke-api.appspot.com/jokes/random"

    @commands.command()
    @commands.cooldown(5, 15, commands.BucketType.guild)
    async def joke(self, ctx: commands.Context):
        """Get a random joke"""
        async with self.bot.session.get(url=self.base_url) as response:
            if response.status != 200:
                return await ctx.send('The API is having some issues right now. Try again later.')

            data = await response.json()
            embed = discord.Embed(
                color=discord.Color.random(),
                timestamp=datetime.utcnow(),
                description=data["setup"],
                title=f"Type: {data['type']}"
            )
            embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
            embed.add_field(name="Punchline", value=data["punchline"])

            await ctx.send(embed=embed)

    @joke.error
    async def error_handler(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("No name provided")

        elif isinstance(error, commands.CommandOnCooldown):
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
    bot.add_cog(Joke(bot))
