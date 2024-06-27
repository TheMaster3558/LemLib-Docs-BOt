import os

import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()


class Bot(commands.Bot):
    session: aiohttp.ClientSession

    def __init__(self) -> None:
        super().__init__(command_prefix=None, intents=discord.Intents.default())

    async def setup_hook(self) -> None:
        self.session = aiohttp.ClientSession()

        await self.load_extension('docs')

        # test_guild = discord.Object(id=os.environ['TEST_GUILD_ID'])
        # self.tree.copy_global_to(guild=test_guild)
        # await self.tree.sync(guild=test_guild)

    async def close(self) -> None:
        await self.session.close()
        await super().close()


bot = Bot()
bot.run(os.environ['TOKEN'])
