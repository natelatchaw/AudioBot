from typing import Optional

import discord


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

class InvalidChannelException(AudioError):
    """
    """

    def __init__(self, channel: Optional[discord.abc.GuildChannel], exception: Optional[Exception] = None):
        reference: str = channel.mention if channel else 'unknown'
        message: str = f'Cannot connect to {reference} channel'
        super().__init__(message, exception)