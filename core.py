import asyncio
import logging
import sys
from typing import NoReturn
import discord
from audio import Audio
from demerit import DemeritManager
from settings import Settings

log: logging.Logger = logging.getLogger(__name__)

GUILD: discord.Object = discord.Object('702620957306519672')


class Core(discord.Client):

    @property
    def tree(self) -> discord.app_commands.CommandTree:
        return self._tree


    def __init__(self, *, intents: discord.Intents = discord.Intents.default()) -> None:
        self._settings: Settings = Settings()        
        self._audio: Audio = Audio(self._settings)
        self._dmanager: DemeritManager = DemeritManager(self._settings)

        super().__init__(intents=intents)
        self._tree = discord.app_commands.CommandTree(self)

    async def on_ready(self) -> None:
        await self._tree.sync()
        _: asyncio.Task[NoReturn] = self.loop.create_task(self._audio.__start__())
        log.info('Ready')