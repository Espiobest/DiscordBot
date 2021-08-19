from discord.ext import commands
from bot import Waifu
import discord

from datetime import datetime as dt
import itertools


class Help(commands.HelpCommand):
    def __init__(self, **options: dict):
        super().__init__(verify_checks=True, **options)

    def embedify(self, title: str, description: str) -> discord.Embed:
        """Returns an embed with the title and description"""
        embed = discord.Embed(title=title, description=description, color=discord.Color.blurple(), timestamp=dt.utcnow())
        embed.set_author(name=self.context.bot.user, icon_url=self.context.bot.user.avatar_url)
        embed.set_footer(icon_url=self.context.author.avatar_url, text=f'Called by: {self.context.author}')
        return embed

    def command_not_found(self, string: str) -> str:
        return f'Command or category `{self.clean_prefix}{string}` not found. Try again...'

    def subcommand_not_found(self, command, string) -> str:
        ret = f"Command `{self.context.prefix}{command.qualified_name}` has no subcommands."
        if isinstance(command, commands.Group) and len(command.all_commands) > 0:
            return ret[:-2] + f' named {string}'
        return ret

    @staticmethod
    def no_category() -> str:
        return 'No Category'

    def get_opening_note(self) -> str:
        return f"""A discord bot.
                   Use prefix **{self.clean_prefix}**
                   Use **`{self.clean_prefix}help "command name"`** for more info on a command
                   You can also use **`{self.clean_prefix}help "category name"`** for more info on a category
                """

    @staticmethod
    def command_or_group(*obj) -> list:
        names = []
        for command in obj:
            if isinstance(command, commands.Group):
                names.append('Group: ' + f'{command.name}')
            else:
                names.append(f'{command.name}')
        return names

    def full_command_path(self, command: commands.Command, include_prefix: bool = False) -> str:
        string = f'{command.qualified_name} {command.signature}'

        if include_prefix:
            string = self.clean_prefix + string

        return string

    def get_alias(self, command: commands.Command) -> str:
        string = ''
        if any(command.aliases):
            string += ' Aliases: '
            string += ', '.join(f'{alias}' for alias in command.aliases)
        return string

    async def send_bot_help(self, mapping):
        embed = self.embedify(title='**General Help**', description=self.get_opening_note())

        no_category = f'\u200b{self.no_category()}'

        def get_category(command: commands.Command, *, no_cat=no_category):
            cog = command.cog
            return cog.qualified_name if cog is not None else no_cat

        filtered = await self.filter_commands(self.context.bot.commands, sort=True, key=get_category)
        for category, cmds in itertools.groupby(filtered, key=get_category):
            if cmds:
                embed.add_field(name=f'**{category}**', value=f"""```markdown
# {' - '.join(self.command_or_group(*cmds))} #
```""", inline=False)

        await self.context.send(embed=embed)

    async def send_group_help(self, group: commands.Group):
        embed = self.embedify(title=group.name,
                              description=group.short_doc or "*No special description*")
        if group.invoke_without_command:
            embed.add_field(name="Usage", value=f"```css\n{self.full_command_path(group)}\n```")
        filtered = await self.filter_commands(group.commands, sort=True, key=lambda c: c.name)
        if filtered:
            for command in filtered:
                name = self.full_command_path(command)
                if isinstance(command, commands.Group):
                    name = 'Group: ' + name
                name = f"""```css\n{name}\n```"""
                embed.add_field(name=command.name, value=command.help or "*No specified command description.*", inline=False)
                embed.add_field(name=f'**Usage**', value=name)

        if len(embed.fields) == 0:
            embed.add_field(name='No commands', value='This group has no commands?')

        await self.context.send(embed=embed)

    async def send_cog_help(self, cog: commands.Cog):
        embed = self.embedify(title=cog.qualified_name, description=cog.description or "*No special description*")
        filtered = await self.filter_commands(cog.get_commands())
        if filtered:
            for command in filtered:
                name = self.full_command_path(command)
                if isinstance(command, commands.Group):
                    name = 'Group: ' + name
                name = f"""```css
{name}
```"""
                embed.add_field(name=f'{self.clean_prefix}{command.qualified_name}\n{self.get_alias(command)}', value=name, inline=False)

        await self.context.send(embed=embed)

    async def send_command_help(self, command: commands.Command):

        desc = f"""```css
{self.full_command_path(command, include_prefix=False)}
```"""
        if command.full_parent_name:
            title = f"{self.clean_prefix}{command.full_parent_name} {command.name}"
        else:
            title = f"{self.clean_prefix}{command.name}"
        embed = self.embedify(title=title, description=self.get_alias(command))
        embed.add_field(name='Info', value=command.help or "*No specified command description.*")
        embed.add_field(name="**Usage**", value=desc, inline=False)
        await self.context.send(embed=embed)

    @staticmethod
    def list_to_string(lst: list) -> str:
        return ', '.join([obj.name if isinstance(obj, discord.Role) else str(obj).replace('_', ' ') for obj in lst])


class NewHelp(commands.Cog, name="Help Command"):
    def __init__(self, bot: Waifu):
        self._original_help_command = bot.help_command
        bot.help_command = Help()
        bot.help_command.cog = self
        bot.get_command('help').hidden = True
        self.bot = bot

    def cog_unload(self):
        self.bot.help_command = self._original_help_command


def setup(bot: Waifu):
    bot.add_cog(NewHelp(bot))

