import logging
from logging import Logger
from typing import Literal, Protocol

import discord
from discord import AudioSource

from ..embed import RequestEmbed
from ..metadata import Metadata

log: Logger = logging.getLogger(__name__)


class Request(Protocol):
    """
    A request object for the module to play
    """

    @property
    def metadata(self) -> Metadata:
        """
        Retrieve metadata for the request
        """
        return NotImplemented
    
    async def process(self) -> AudioSource:
        """
        Process the request data into an AudioSource
        """
        return NotImplemented
    
    async def as_embed(self, interaction: discord.Interaction, *, large_image: bool = True, thumbnail_format: Literal['png', 'bmp'] = 'png') -> RequestEmbed:
        """
        Generate an embed for the request
        """
        return RequestEmbed(self.metadata, interaction.user, interaction.created_at, large_image=large_image, thumbnail_format=thumbnail_format)
    

from .file import FileRequest
from .midi import MidiRequest
from .youtube import YouTubeRequest