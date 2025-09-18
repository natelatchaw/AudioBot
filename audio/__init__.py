from .embed import (RequestEmbed, RequestFrequencyEmbed, RequestQueueEmbed,
                    RequestRecentEmbed)
from .error import AudioError, InvalidChannelException, NotConnectedError
from .metadata import Metadata
from .request import FileRequest, MidiRequest, Request, YouTubeRequest
from .player import Player
from .queue import Queue


from logging import Logger
import logging

log: Logger = logging.getLogger(__name__)

log.info('Loaded companion module.')