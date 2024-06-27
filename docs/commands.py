from __future__ import annotations

from typing import TYPE_CHECKING, List, Literal

import discord
from discord import app_commands
from discord.ext import commands
from rapidfuzz import fuzz

from .doc_reader import DocumentationReader

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

    from bot import Bot


def code_block(text: str, lang: str = 'cpp') -> str:
    return f'```{lang}\n{text}\n```'


def truncate(text: str, limit: int) -> str:
    if len(text) > limit:
        return text[: limit - 3] + '...'
    return text


def sort_by_similarity(options: List[str], comparator: str) -> List[str]:
    options = sorted(
        options, key=lambda x: fuzz.partial_ratio(x, comparator), reverse=True
    )
    return list(options)


Versions: TypeAlias = Literal['master', 'stable', 'v0.5.1', 'v0.5.0']


class Documentation(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.doc_reader = DocumentationReader(
            'https://lemlib.readthedocs.io/en/', self.bot.session
        )

    @app_commands.command(name='docs', description='Get specific LemLib documentation')
    @app_commands.describe(
        name='The name of the symbol to look up', version='The version of LemLib to use'
    )
    async def docs(
        self,
        interaction: discord.Interaction[Bot],
        name: str,
        version: Versions = 'stable',
    ):
        await interaction.response.defer()

        if not self.doc_reader.has_inventory_for_version(version):
            await self.doc_reader.update_inventory(version)

        res = await self.doc_reader.get_symbol_markdown(name, version)

        # look at DocumentationReader.get_symbol_markdown for info on the return types
        if isinstance(res, tuple):
            url, signature, description = res
            embed = discord.Embed(
                title=name,
                url=url,
                description=truncate(f'{code_block(signature)}\n{description}', 4096),
            )
        elif isinstance(res, str):
            embed = discord.Embed(
                title='No documentation could be displayed',
                description=f'However, you can still view the symbol by clicking above.',
                url=res,
            )
        else:
            embed = discord.Embed(
                title=f'That wasn\'t found',
                description=f'No symbol named `{name}` was found.',
            )

        await interaction.followup.send(embed=embed)

    @docs.autocomplete('name')
    async def name_autocomplete(
        self, interaction: discord.Interaction[Bot], current: str
    ) -> List[app_commands.Choice]:
        current_version = interaction.namespace.version or 'stable'

        if not self.doc_reader.has_inventory_for_version(current_version):
            await self.doc_reader.update_inventory(current_version)

        # get first 25 most similar options
        options = sort_by_similarity(
            self.doc_reader.inventories[current_version].keys(), current
        )[:25]
        return [app_commands.Choice(name=option, value=option) for option in options]
