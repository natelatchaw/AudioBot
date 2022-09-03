import asyncio
from configparser import ConfigParser
import logging
from asyncio import Event, Queue, Task
from logging import Logger
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Optional, Union
from urllib.request import Request

import discord
import youtube_dl
from discord import Activity, Streaming, VoiceClient, VoiceState
from discord.player import AudioSource
from router.configuration import Section

from logger import AudioLogger
from metadata import Metadata
from request import Request
from settings.settings import Settings

log: Logger = logging.getLogger(__name__)

defaults: Dict[str, Any] = {
    'format': 'bestaudio/best',
    'noplaylist': False,
    'postprocessors': [
        {
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'opus',
        },
    ],
    'logger': AudioLogger(),
    'progress_hooks': [ ],
}


class Audio():
    """
    Component responsible for audio playback.
    """

    @property
    def timeout(self) -> Optional[float]:
        key: str = "timeout"
        value: Optional[str] = None
        try:
            value = self._config[key]
            return float(value) if value and isinstance(value, str) else None                
        except KeyError:
            self._config[key] = ""
            return None
        except ValueError:
            self._config[key] = ""
            return None

    @timeout.setter
    def timeout(self, value: float) -> None:
        key: str = "timeout"
        if value: self._config[key] = str(value)        


    def __init__(self, settings: Settings):
        """
        """

        self._settings: Settings = settings
        self._connection: Event = Event()
        self._playback_event: Event = Event()
        self._playback_queue: Queue = Queue()
        self._client: Optional[VoiceClient] = None
        self._current: Optional[Metadata] = None
        self.__setup__()


    def __setup__(self) -> None:
        """
        Called after instance properties are initialized.
        """

        # create a config section for Audio
        self._settings.client[Audio.__name__] = Section(Audio.__name__, self._settings.client._parser, self._settings.client._reference)
        # create reference to Audio config section
        self._config: Section = self._settings.client[Audio.__name__]


    def __on_complete__(self, error: Optional[Exception]):
        """
        Called when a request completes in the audio loop.
        """

        # set the playback event
        self._playback_event.set()
        # log error if it was provided
        if error: log.error(error)


    async def __on_dequeue__(self, request: Request) -> None:
        """
        Called when a request is retrieved from the queue.
        """

        # set the current metadata
        self._current = request.metadata


    async def __start__(self):
        """
        The core audio playback loop.
        This is used internally and should not be called as a command.
        """

        while True:
            try:
                # wait for the connection event to be set
                _: True = await self._connection.wait()
                log.debug(f"Beginning core audio playback loop")

                # if the voice client is not available
                if self._client is None:
                    # clear the connection event
                    self._connection.clear()
                    log.debug(f"Resetting; no voice client available")
                    # restart the loop
                    continue

                log.debug(f"Waiting for next audio request")
                # wait for the playback queue to return a request, or throw TimeoutError
                request: Request = await asyncio.wait_for(self._playback_queue.get(), self.timeout)

                # call on dequeue logic
                await self.__on_dequeue__(request)

                # clear the playback event
                self._playback_event.clear()
                log.debug(f"Beginning track '{request.metadata.title}'")

                # play the request
                self._client.play(request.source, after=self.__on_complete__)

                # wait for the playback event to be set
                _: True = await self._playback_event.wait()
                log.debug(f"Finishing track '{request.metadata.title}'")

            except asyncio.TimeoutError as error:
                log.error(error)
                try:
                    await self.__disconnect__()
                finally:
                    # clear the connection event
                    self._connection.clear()

            except Exception as error:
                log.error(error)
                try:
                    await self.__disconnect__()
                finally:
                    # clear the connection event
                    self._connection.clear()

    
    async def __connect__(self, interaction: discord.Interaction):
        """
        Connects the bot to the user's voice channel.
        
        ### Raises
        - discord.ClientException:
            You are already connected to a voice channel.
        """

        try:
            # get the user's voice state
            state: Optional[VoiceState] = interaction.user.voice
            # if the user doesn't have a voice state, raise error
            if not state:
                raise InvalidChannelError(None)

            # if the voice state does not reference a channel, raise error
            if not state.channel:
                raise InvalidChannelError(state.channel)

            # connect to the channel and get a voice client
            self._client: VoiceClient = await state.channel.connect()
            # set the connection event
            self._connection.set()

        except discord.ClientException as exception:
            log.warn(exception)
            # ignore client exception errors
            pass

        finally:
            pass


    async def __disconnect__(self, *, force: bool = False):
        """
        Disconnects the bot from the joined voice channel.
        """

        try:
            # if the voice client is unavailable
            if not self._client:
                raise ConnectionError("Voice connection unavailable")
            # if the voice client is not connected
            if not self._client.is_connected():
                raise ConnectionError("Voice connection disconnected")

            # disconnect the voice client and clear the voice client
            self._client = await self._client.disconnect(force=force)
            # clear the connection event
            self._connection.clear()
            
        except Exception as exception:
            log.warn(exception)
            pass
        
        finally:
            pass

    
    async def __query__(self, interaction: discord.Interaction, query: str, *, downloader: Optional[youtube_dl.YoutubeDL] = None) -> Optional[Metadata]:
        """
        Searches for a query on YouTube and downloads the metadata.

        Parameters:
            - query: A string or URL to download metadata from YouTube
            - downloader: YoutubeDL downloader instance
        """
        
        # use provided downloader or initialize one if not provided
        downloader = downloader if downloader else youtube_dl.YoutubeDL(defaults)
        # extract info for the provided query
        data: Dict[str, Any] = downloader.extract_info(query, download=False)

        # get the entries property, if it exists
        entries: Optional[List[Any]] = data.get('entries')
        # if the data contains a list of entries, use the list;
        # otherwise create list from data (single entry)
        results: List[Dict[str, Any]] = entries if entries else [data]
        # return the first available result
        result: Optional[Dict[str, Any]] = results[0]

        # return a Metadata object if result exists
        return Metadata.__from_dict__(interaction, result) if result else None


    async def __queue__(self, metadata: Metadata, options: List[str] = list()) -> Request:
        """
        Adds metadata to the queue.
        """

        # add the audio filter parameter to the options list
        options.append(r'-vn')

        # create source from metadata url and options
        source: AudioSource = discord.FFmpegOpusAudio(metadata.source, options=' '.join(options))
        # create request from source and metadata
        request: Request = Request(source, metadata)

        # add the request to the queue
        await self._playback_queue.put(request)
        # return the request
        return request


    async def __pause__(self) -> None:
        """
        Pauses the current track.
        """
        # pause the voice client if available
        if self._client: self._client.pause()
        #
        return


    async def __skip__(self) -> Optional[Metadata]:
        """
        Skips the current track.
        """

        # store reference to the current metadata
        skipped: Optional[Metadata] = self._current
        # stop the voice client if available
        if self._client: self._client.stop()
        # return the skipped metadata
        return skipped

    
    async def __stop__(self) -> None:
        """
        Stops audio playback.
        """

        # stop the voice client if available
        if self._client: self._client.stop()
        # disconnect the voice client
        await self.__disconnect__()
        #
        return



class AudioError(Exception):
    """
    """

    def __init__(self, message: str, exception: Optional[Exception] = None):
        self._message = message
        self._inner_exception = exception

    def __str__(self) -> str:
        return self._message


class NotConnectedError(AudioError):
    """
    """

    def __init__(self, exception: Optional[Exception] = None):
        message: str = f'The client is not connected to a compatible voice channel.'
        super().__init__(message, exception)


class InvalidChannelError(AudioError):
    """
    """

    def __init__(self, channel: Optional[discord.abc.GuildChannel], exception: Optional[Exception] = None):
        reference: str = channel.mention if channel else 'unknown'
        message: str = f'Cannot connect to {reference} channel'
        super().__init__(message, exception)
