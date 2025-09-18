import asyncio
import logging
from asyncio import Event
from logging import Logger
from typing import NoReturn, Optional

from discord import AudioSource, ClientException, Interaction, Member, StageChannel, VoiceChannel, VoiceClient, VoiceState

from .error import InvalidChannelException

from .request import Request
from .queue import Queue

log: Logger = logging.getLogger(__name__)


class Player():

    @property
    def current(self) -> Optional[Request]:
        """The currently playing request, if any."""

        return self._queue.current

    def __init__(self, *, timeout: Optional[float] = None) -> None:
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
            except (TimeoutError, Exception) as exception:
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

        log.debug(f'Playing request {request.metadata.id}: {request.metadata.title}')
        # get the audio source from the request
        source: AudioSource = await request.process()
        # play the request
        self._client.play(source, after=self._on_finish)

        # wait until signalled that the player is inactive
        await self._inactive.wait()
        log.debug(f'Finished request {request.metadata.id}: {request.metadata.title}')

    def _on_finish(self, exception: Optional[Exception]) -> None:
        """
        Called when a request has been fulfilled.
        """

        # if an exception was provided, log it
        if exception is not None: log.error(exception)
        # signal the player is now inactive
        self._inactive.set()

    async def _on_exception(self, exception: Exception) -> None:
        """
        Called when an exception occurs while handling a request.
        """

        # log the exception
        log.error(exception)
        # try to disconnect the voice connection
        try: await self.disconnect()
        # signal the voice client is not connected
        finally: self._connection.clear()

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
            # signal the voice client is now connected
            self._connection.set()

        # catch client exceptions that may occur
        except ClientException as exception:
            # log the exception as a warning
            log.warning(exception)
            # ignore client exceptions
            pass

    async def disconnect(self, *, force: bool = False) -> None:
        """
        Disconnect from the voice channel that is currently connected.
        """

        try:
            # if the voice client is unavailable
            if self._client is None:
                # raise exception
                raise ConnectionError('Voice connection unavailable')
            
            # if the voice client is not connected
            if not self._client.is_connected():
                # raise exception
                raise ConnectionError('Voice connection disconnected')
            
            # disconnect the voice client from the channel
            self._client = await self._client.disconnect(force=force)
            # signal the voice client is not connected
            self._connection.clear()
            
        except Exception as exception:
            # log the exception as a warning
            log.warning(exception)
            # ignore exceptions
            pass

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
