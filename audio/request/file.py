import logging
from collections.abc import Buffer
from io import BufferedIOBase, BytesIO
from logging import Logger
from typing import (List, Literal, Optional)

import discord
from discord import AudioSource

from ..embed import RequestEmbed
from ..metadata import Metadata
from ..request import Request
from ..parser import Parser

log: Logger = logging.getLogger(__name__)


class FileRequest(Request):

    @property
    def metadata(self) -> Metadata:
        return self._metadata
    
    async def process(self) -> AudioSource:
        file_data: Buffer = await self._file.read()
        file_fp: BufferedIOBase = BytesIO(file_data)

        before_options: str = ' '.join(self._before_options)
        log.debug(f'Applying prepended streaming parameters: {before_options}')
        after_options: str = ' '.join(self._after_options)
        log.debug(f'Applying postpended streaming parameters: {after_options}')

        return discord.FFmpegPCMAudio(file_fp, pipe=True, before_options=before_options, options=after_options)
    
    def __init__(self, interaction: discord.Interaction, file: discord.Attachment, *, before_options: Optional[List[str]] = None, after_options: Optional[List[str]] = None):
        self._interaction: discord.Interaction = interaction
        self._file: discord.Attachment = file
        self._before_options: List[str] = before_options if before_options else []
        self._after_options: List[str] = after_options if after_options else []
        self._metadata: Metadata = Metadata(interaction.id, user_id=interaction.user.id, title=file.filename, hyperlink=file.url)

    async def parse(self) -> None:
        """
        Parse the request for detailed metadata
        """
        buffer: Buffer = await self._file.read()
        data: BufferedIOBase = BytesIO(buffer)
        try:
            parser: Parser = Parser(data)
            if parser.artists:  self._metadata.artist = ', '.join(parser.artists)
            if parser.title:    self._metadata.title = ', '.join(parser.title)
            if parser.cover:    self._metadata.thumbnail = bytes(parser.cover)
        except:
            pass
    
    async def as_embed(self, interaction: discord.Interaction, *, large_image: bool = True, thumbnail_format: Literal['png', 'bmp'] = 'png') -> RequestEmbed:
        return await super().as_embed(interaction, large_image=large_image, thumbnail_format=thumbnail_format)