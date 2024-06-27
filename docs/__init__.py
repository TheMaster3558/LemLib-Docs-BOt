from __future__ import annotations

from typing import TYPE_CHECKING

from .commands import Documentation

if TYPE_CHECKING:
    from bot import Bot


async def setup(bot: Bot) -> None:
    await bot.add_cog(Documentation(bot))
