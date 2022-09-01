import asyncio
import logging
from asyncio import Event, Queue, Task, TimeoutError
from asyncio.events import AbstractEventLoop
from logging import Logger
from typing import Any, Dict, List, NoReturn, Optional, Union
from urllib.request import Request

import discord
import youtube_dl
from discord import (Activity, ClientException, StageChannel,
                     Streaming, VoiceChannel, VoiceClient,
                     VoiceState)
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
        self._settings: Settings = settings

        self._connection: Event = Event()
        self._playback_event: Event = Event()
        self._playback_queue: Queue = Queue()
        self._vclient: Optional[VoiceClient] = None
        self._current: Optional[Metadata] = None

        self.__setup__()


    def __setup__(self) -> None:
        # create a config section for Audio
        self._settings.client['Audio'] = Section('Audio', self._settings.client._parser, self._settings.client._reference)
        # create reference to Audio config section
        self._config: Section = self._settings.client['Audio']

    def __on_complete__(self, error: Optional[Exception]):
        """
        Called when a source completes in the audio loop.
        This is used internally and should not be called as a command.
        """
        # set the playback event
        self._playback_event.set()
        log.debug(f'Playback event is {"set" if self._playback_event.is_set() else "clear"}')
        # log error if available
        if error: log.error(error)

    async def __on_dequeue__(self, metadata: Metadata) -> None:
        """
        Called when a source is retrieved from the top of the queue.
        This is used internally and should not be called as a command.
        """
        # set the current metadata
        self._current = metadata
        # instantiate activity
        activity: Activity = Streaming(name=metadata.title, url=metadata.url)
        # change the client's presence
        #await self._client.change_presence(activity=activity)

    async def __start__(self):
        """
        The core audio playback loop.
        This is used internally and should not be called as a command.
        """

        while True:
            try:
                log.debug(f'Beginning core audio playback loop.')

                # wait for the connection event to be set
                _: True = await self._connection.wait()

                # if the VoiceClient is not available
                if self._vclient is None:
                    log.debug(f'No voice client available.')
                    log.debug('Resetting...')
                    # clear the connection event
                    self._connection.clear()
                    # restart the loop
                    continue

                log.debug(f'Waiting for next audio request')

                # get an audio request from the queue
                request: Request = await asyncio.wait_for(self._playback_queue.get(), self.timeout)

                # update presence
                await self.__on_dequeue__(request.metadata)

                log.debug(f'Beginning track \'{request.metadata.title}\'')

                # clear the playback event
                self._playback_event.clear()
                log.debug(f'Playback event is {"set" if self._playback_event.is_set() else "clear"}')

                # play the request
                print(request.source.__dict__)
                self._vclient.play(request.source, after=self.__on_complete__)

                # wait for the playback event to be set
                _: True = await self._playback_event.wait()

                log.debug(f'Finishing track \'{request.metadata.title}\'')

            except TimeoutError as error:
                log.error(error)
                if self._vclient:
                    await self._vclient.disconnect(force=True)
                    self._vclient: Optional[VoiceClient] = None
                self._connection.clear()

            except Exception as error:
                log.error(error)
                self._connection.clear()
    
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
        Add source media to the media queue.

        Parameters:
            - url: A URL link to a YouTube video to add to the queue.
            - search: Search terms to query YouTube for a source video.
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


    async def __connect__(self, interaction: discord.Interaction):
        """
        Joins the user's voice channel.
        """

        try:
            state: Optional[VoiceState] = interaction.user.voice
            if not state: raise InvalidChannelError(None)

            channel: Optional[Union[VoiceChannel, StageChannel]] = state.channel
            if not channel: raise InvalidChannelError(channel)

            self._vclient: VoiceClient = await channel.connect()

            self._connection.set()

        except ClientException:
            pass


    async def __disconnect__(self):
        """
        Disconnects the bot from the joined voice channel.
        """

        try:
            if not self._vclient:
                raise ConnectionError('Cannot disconnect: Not connected to begin with.')
            elif not self._vclient.is_connected():
                raise ConnectionError('Cannot disconnect: Not connected to begin with.')
            else:
                self._playback_event.set()
                await self._vclient.disconnect()
        except ConnectionError:
            raise
        except:
            await self._vclient.disconnect(force=True)
        finally:
            self._connection.clear()


    async def __pause__(self):
        """
        Pauses audio playback.
        """
        if self._vclient:
            self._vclient.pause()
            return


    async def __skip__(self) -> Metadata:
        """
        Skips the current track.
        """
        skipped: Metadata = self._current
        if self._vclient:
            self._vclient.source = AudioSource()
            return skipped

    
    async def __stop__(self):
        """
        Stops audio playback.
        """
        if self._vclient:
            self._vclient.stop()
            await self.__disconnect__()
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
