import asyncio
from collections.abc import Buffer
from datetime import datetime
from io import BufferedIOBase, BytesIO
import logging
from asyncio import Event
from logging import Logger
from os import PathLike
from pathlib import Path
from typing import NoReturn, Optional
import subprocess

from discord import AudioSource, ClientException, FFmpegOpusAudio, Interaction, Member, StageChannel, VoiceChannel, VoiceClient, VoiceState
import discord

from .error import InvalidChannelException

from .request import Request
from .queue import Queue

log: Logger = logging.getLogger(__name__)


class Player():

    @property
    def current(self) -> Optional[Request]:
        """The currently playing request, if any."""

        return self._queue.current
    
    @property
    def is_connected(self) -> bool:
        return self._client.is_connected() if self._client else False
    
    @property
    def tone(self) -> Optional[AudioSource]:
        return self._load_tone(self._tone_path) if self._tone_path else None

    def __init__(self, *, timeout: Optional[float] = None, tone: Optional[PathLike[str]] = None) -> None:
        """
        """

        self._connection: Event = Event()
        """Signals voice channel connection events."""
        
        self._client: Optional[VoiceClient] = None
        """The client for accessing a voice connection."""

        self._queue: Queue[Request] = Queue()
        """The queue for storing requests."""

        self._timeout: Optional[float] = timeout
        """The timeout in seconds before automatically disconnecting."""

        self._inactive: Event = Event()
        """Signals the player is idle."""

        self._tone_path: Optional[PathLike[str]] = tone
        """A connection tone file path, if provided."""

    async def loop(self) -> NoReturn:
        """
        The audio playback loop.
        """

        # loop indefinitely
        while True:
            # try to execute the loop iteration
            try:                
                # wait for the connection event to be set
                await self._connection.wait()

                # if the voice client is unavailable and the connection is marked as active
                if self._client is None and self._connection.is_set():
                    log.warning('Voice client is unavailable. Resetting...')
                    # signal the voice client is not connected
                    self._connection.clear()
                    # restart the loop
                    continue

                log.debug('Waiting for next playback request')
                # wait for the queue to produce a request, or throw TimeoutError
                request: Request = await asyncio.wait_for(self._queue.get(), self._timeout)

                # play the request
                await self._play(request)
                
            # catch errors that occur during the loop iteration
            except (TimeoutError, ClientException, Exception) as exception:
                # handle the exception
                await self._on_exception(exception)

    async def _play(self, request: Request) -> None:
        """
        Play a request and await completion.
        """

        # signal the player is no longer inactive
        self._inactive.clear()
        # if the voice client is unavailable, return
        if self._client is None: return

        try:
            log.debug(f'Playing request {request.metadata.id}: {request.metadata.title}')
            # get the audio source from the request
            source: AudioSource = await request.process()
            # play the request
            self._client.play(source, after=self._on_finish)
        # if an error occurred during subprocess execution
        except subprocess.CalledProcessError as exception:
            await self._on_exception(exception)
        except Exception as exception:
            await self._on_exception(exception)

        play_ad: bool = False
        if play_ad:
            await asyncio.sleep(30)
            log.info('Playing advertisement')
            ad_complete: Event = Event()
            self._client.pause()
            ad_complete.clear()
            self._client.play(FFmpegOpusAudio('C:/Users/natel/Downloads/spotify-ad-meme.mp3'), after=lambda exception: ad_complete.set())
            await ad_complete.wait()            
            self._client.play(source, after=self._on_finish)

        # wait until signalled that the player is inactive
        await self._inactive.wait()
        log.debug(f'Finished request {request.metadata.id}: {request.metadata.title}')

        # clear the current request
        del self._queue.current

        if not self._client or not self._client.is_connected():
            log.info('Disconnecting...')
            await self.disconnect()

    def _on_finish(self, exception: Optional[Exception]) -> None:
        """
        Called when a request has been fulfilled.
        """

        try:
            # re-raise the exception
            if exception: raise exception
        except Exception as exception:
            # log the exception
            log.error(exception)
        finally:
            # signal the player is now inactive
            self._inactive.set()

    async def _on_exception(self, exception: Exception) -> None:
        """
        Called when an exception occurs while handling a request.
        """
        
        try:
            # get the channel instance if available
            channel: Optional[discord.abc.Connectable] = self._client.channel if self._client else None
            
            # if the channel can receive messages
            if isinstance(channel, discord.abc.Messageable):
                user: Optional[discord.ClientUser] = self._client.user if self._client else None
                embed: discord.Embed = PlaybackExceptionEmbed(exception, user=user)
                await channel.send(embed=embed)
            # re-raise the exception
            raise exception

        except Exception as exception:
            # log the exception
            log.error(exception)

    async def connect(self, interaction: Interaction) -> None:
        """
        Connect to the voice channel of the user that initiated the Interaction.
        """

        try:
            # if the user that initiated the interaction doesn't have a voice state
            if not isinstance(interaction.user, Member):
                # raise exception
                raise InvalidChannelException(None)
            
            # get the voice state of the user
            state: Optional[VoiceState] = interaction.user.voice
            # if the voice state was not provided
            if not isinstance(state, VoiceState):
                # raise exception
                raise InvalidChannelException(None)
            
            # get the channel of the user's voice state
            channel: Optional[VoiceChannel | StageChannel] = state.channel
            # if the channel is not a voice channel
            if not isinstance(channel, VoiceChannel):
                # raise exception
                raise InvalidChannelException(state.channel)
            
            # connect to the channel and store the voice client
            self._client = await channel.connect()

            # play connection tone
            await self._play_tone(self.tone)

        # catch client exceptions that may occur
        except ClientException as exception:
            # log the exception as a warning
            log.warning(exception)
            # ignore client exceptions
            pass

        finally:
            # signal the voice client is now connected
            self._connection.set()


    async def disconnect(self, *, force: bool = False) -> None:
        """
        Disconnect from the voice channel that is currently connected.
        """

        try:
            # if the voice client is unavailable
            if self._client is None:
                # raise exception
                raise ConnectionError('Voice connection unavailable')
            
            # disconnect the voice client from the channel
            await self._client.disconnect(force=force)
            
        except Exception as exception:
            # log the exception as a warning
            log.warning(exception)
            # ignore exceptions
            pass
        
        finally:
            # set the voice client to None
            self._client = None
            # signal the voice client is not connected
            self._connection.clear()

    async def queue(self, interaction: Interaction, request: Request) -> None:
        """
        Adds a request to the queue.
        """

        # put the request in the queue
        await self._queue.put(request)

    async def skip(self, interaction: Interaction) -> None:
        """
        Skips the remainder of the current request.
        """
        
        # if the voice client is unavailable, return
        if self._client is None: return
        # stop playback of the current request
        self._client.stop()

    async def pause(self, interaction: Interaction) -> None:
        """
        Pauses playback of the current request.
        """

        # if the voice client is unavailable, return
        if self._client is None: return
        # pause playback of the current request
        self._client.pause()

    async def stop(self, interaction: Interaction) -> None:
        """
        Stops playback of the current request and clears queued requests.
        """

        # if the voice client is unavailable, return
        if self._client is None: return
        # clear queued requests
        await self._queue.clear()
        # stop playback of the current request
        self._client.stop()

    def _load_tone(self, path: PathLike[str]) -> Optional[AudioSource]:
        # get a path object for the provided path
        reference: Path = Path(path)
        # if the reference does not exist at the provided path
        if not reference.exists(): return None

        with open(path, mode='rb') as file:
            # read the contents of the file
            file_data: Buffer = file.read()
            # store the buffer in a stream
            file_fp: BufferedIOBase = BytesIO(file_data)
        # get the audio source from the file object
        return FFmpegOpusAudio(file_fp, pipe=True)

    async def _play_tone(self, source: Optional[AudioSource]) -> None:
        # if no source was provided, return
        if source is None: return
        # if the voice client is unavailable, return
        if self._client is None: return

        # signal the player is no longer inactive
        self._inactive.clear()
        # play the source
        self._client.play(source, after=self._on_finish)
        # wait until signalled that the player is inactive
        await self._inactive.wait()

class PlaybackExceptionEmbed(discord.Embed):

    def __init__(self, exception: Exception, *, user: Optional[discord.ClientUser]):
        color: discord.Color = discord.Color.red()
        title: str = f'A Playback Exception occurred'
        description: Optional[str] = str(exception)
        url: Optional[str] = None
        timestamp: Optional[datetime] = datetime.now()
        super().__init__(color=color, title=title, description=description, url=url, timestamp=timestamp)

        if user: self.set_author(name=user.display_name, icon_url=user.avatar.url if user.avatar else None)
        self.add_field(name='Type', value=exception.__class__.__name__, inline=False)