from metadata import Metadata
from discord import AudioSource

class Request():
    """
    A request object for the bot to play.
    """

    def __init__(self, source: AudioSource, metadata: Metadata):
        self._metadata: Metadata = metadata
        self._source: AudioSource = source
    
    @property
    def metadata(self) -> Metadata:
        return self._metadata

    @property
    def source(self) -> AudioSource:
        return self._source

