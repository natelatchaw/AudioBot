import logging
from logging import Logger
import re
from typing import Any, Dict, List, Literal, Mapping, Optional, TypedDict, Union

import discord
import yt_dlp as youtube_dl
from yt_dlp.utils import DownloadError
from discord import AudioSource

from ..embed import RequestEmbed
from ..error import AudioError
from ..metadata import Metadata
from ..request import Request

log: Logger = logging.getLogger(__name__)


class YouTubeRequest(Request):

    @property
    def metadata(self) -> Metadata:
        id:         int = self._interaction.id
        user_id:    Optional[int] = self._interaction.user.id
        title:      Optional[str] = self._tags.get('title', None)
        artist:     Optional[str] = self._tags.get('channel', None)
        webpage:    Optional[str] = self._tags.get('webpage_url', None)
        thumbnail:  Optional[str] = self._tags.get('thumbnail', None)
        return Metadata(id, user_id=user_id, title=title, artist=artist, hyperlink=webpage, thumbnail=thumbnail)
        
    def __init__(self, interaction: discord.Interaction, query: str, *, before_options: Optional[List[str]] = None, after_options: Optional[List[str]] = None):
        self._interaction: discord.Interaction = interaction
        self._query: str = query        
        self._before_options: List[str] = before_options if before_options else []
        self._after_options: List[str] = after_options if after_options else []

    async def process(self) -> AudioSource:
        await self.parse()

        source: Optional[str] = self._tags.get('url', None)
        if source is None: raise AudioError(f'Cannot find source media for {self._query}')

        bitrate: Optional[int | Any] = self._tags.get('abr', None)
        bitrate = bitrate if isinstance(bitrate, int) else None

        before_options: str = ' '.join(self._before_options)
        log.debug(f'Applying prepended streaming parameters: {before_options}')
        after_options: str = ' '.join(self._after_options)
        log.debug(f'Applying postpended streaming parameters: {after_options}')

        return await discord.FFmpegOpusAudio.from_probe(source, before_options=before_options, options=after_options)
        return discord.FFmpegOpusAudio(source, bitrate=bitrate, codec=None, before_options=before_options, options=after_options)

    async def parse(self) -> None:
        """
        Parse the request for detailed metadata
        """

        try:
            # use provided downloader or initialize one if not provided
            downloader: youtube_dl.YoutubeDL = youtube_dl.YoutubeDL(DEFAULTS) # type: ignore
            # extract info for the provided content
            data: Optional[Dict[str, Any]] = downloader.extract_info(self._query, download=False) # type: ignore

            # if unexpected data was extracted
            if not isinstance(data, Dict): raise AudioError(f'Invalid metadata received for {self._query}')

            # get the entries property, if it exists
            entries: Optional[List[Any]] = data.get('entries') if data else None
            # if the data contains a list of entries, use the list, otherwise create list from data (single entry)
            results: List[Dict[str, Any]] = entries if entries else [data]
            # return the first available result
            result: Optional[Dict[str, Any]] = results[0]
            # if no results are available
            if not result: raise AudioError(f'No results found for {self._query}')
            # assign result to tags property
            self._tags: Dict[str, Any] = result        

        except DownloadError as exception:
            ansi_escape: re.Pattern[str] = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            message: str = exception.msg if isinstance(exception.msg, str) else "Unknown error message format"
            inner: str = ansi_escape.sub('', message) 
            raise Exception(f'An error occurred during download.\nDetails: {inner}')
    
    async def as_embed(self, interaction: discord.Interaction, *, large_image: bool = True, thumbnail_format: Literal['png', 'bmp'] = 'png') -> RequestEmbed:
        return await super().as_embed(interaction, large_image=large_image, thumbnail_format=thumbnail_format)


class DownloadLogger(): # type: ignore
    def __init__(self, ydl: Any | youtube_dl.YoutubeDL | None = None) -> None:
        pass

    def debug(self, message: str):
        log.debug(message)

    def info(self, message: str) -> None:
        log.info(message)
        
    def warning(self, message: str, *, once: bool = ..., only_once: bool = ...) -> None: # type: ignore
        log.warning(message)

    def error(self, message: str):
        log.error(message)

    def stdout(self, message: str) -> None:
        pass
    
    def stderr(self, message: str) -> None:
        pass
        

AUDIO_LOGGER: DownloadLogger = DownloadLogger()

DEFAULTS: Mapping[str, Any] = {
    'default_search': 'auto',
    'format': 'bestaudio/best',
    'noplaylist': True,
    'postprocessors': [
        {
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'opus',
        },
    ],
    'logger': AUDIO_LOGGER,
    'progress_hooks': [ ],
}