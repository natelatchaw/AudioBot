import importlib.util
import logging
from collections.abc import Buffer, Mapping
from io import BufferedIOBase, BytesIO
from logging import Logger
from typing import (Any, Dict, Iterable, Iterator, List, Literal, Mapping, Optional,
                    Union)

import discord
from discord import AudioSource

from ..embed import RequestEmbed
from ..metadata import Metadata
from ..request import Request

log: Logger = logging.getLogger(__name__)


class FileRequest(Request):

    @property
    def metadata(self) -> Metadata:
        if self._metadata is not None: return self._metadata
        id: int = self._interaction.id
        user_id: int = self._interaction.user.id
        title: str = self._file.filename
        hyperlink: str = self._file.url
        self._metadata: Optional[Metadata] = Metadata(id, user_id=user_id, title=title, artist=None, hyperlink=hyperlink, thumbnail=None)
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
        self._metadata: Optional[Metadata] = None

    async def parse(self) -> None:
        """
        Parse the request for detailed metadata
        """
        buffer: Buffer = await self._file.read()
        data: BufferedIOBase = BytesIO(buffer)
        try:
            self._metadata = __parse_file__(self.metadata, data)
        except:
            pass
    
    async def as_embed(self, interaction: discord.Interaction, *, large_image: bool = True, thumbnail_format: Literal['png', 'bmp'] = 'png') -> RequestEmbed:
        return await super().as_embed(interaction, large_image=large_image, thumbnail_format=thumbnail_format)



def __parse_file__(metadata: Metadata, binary: BufferedIOBase) -> Metadata:
    if importlib.util.find_spec('mutagen'):
        log.debug('Found mutagen module. Beginning extraction process.')
        import mutagen
    else:
        log.warning('Unable to find mutagen module. Audio metadata extraction will be skipped.')
        return metadata

    file: Optional[mutagen.FileType] = mutagen.File(binary) # type: ignore
    if not file:
        raise Exception('Could not determine file container type.')

    elif isinstance(file, mutagen.id3.ID3FileType): # type: ignore
        metadata = __parse_tags__(metadata, binary, tagging_keys=TAGGING_FORMATS['ID3'])
        metadata = __parse_cover__(metadata, binary, tagging_keys=TAGGING_FORMATS['ID3'])
        return metadata

    elif isinstance(file, mutagen.ogg.OggFileType): # type: ignore
        metadata = __parse_tags__(metadata, binary, tagging_keys=TAGGING_FORMATS['Vorbis'])
        metadata = __parse_cover__(metadata, binary, tagging_keys=TAGGING_FORMATS['Vorbis'])
        return metadata

    elif isinstance(file, mutagen.flac.FLAC): # type: ignore
        metadata = __parse_tags__(metadata, binary, tagging_keys=TAGGING_FORMATS['Vorbis'])
        metadata = __parse_cover__(metadata, binary, tagging_keys=TAGGING_FORMATS['Vorbis'])
        return metadata

    else:
        raise Exception('Unsupported media type.')

TAGGING_FORMATS: Dict[str, Dict[Union[str, Literal['title', 'artist', 'album']], str]] = {
    'ID3': {
        'album':    'TALB',
        'artist':   'TPE1',
        'title':    'TIT2',
        'cover':    'APIC:'
    },
    'Vorbis': {
        'album':    'ALBUM',
        'artist':   'ARTIST',
        'title':    'TITLE',
        'cover':    'metadata_block_picture'
    },
    'APEv2': {
        'album':    'Album',
        'artist':   'Artist',
        'title':    'Title'
    }
}

def __parse_tags__(metadata: Metadata, binary: BufferedIOBase, tagging_keys: Dict[Union[Literal['artist', 'title'], str], str]) -> Metadata:
    if not importlib.util.find_spec('mutagen'):
        log.warning('Unable to find mutagen module. Audio metadata extraction will be skipped.')
        return metadata

    import mutagen
    from mutagen._util import DictMixin

    file: Optional[mutagen.FileType] = mutagen.File(binary) # type: ignore
    if not file:
        raise Exception('Could not determine file container type.')

    # retrieve the file's tags
    tags: mutagen.Tags = file.tags # type: ignore
    # if the tags instance is not a type of DictProxy, raise exception
    if not isinstance(tags, Mapping): raise Exception()

    # get the title key from the tagging keys dictionary
    title_key: Optional[str] = tagging_keys.get('title', None)
    # get the title tag data via the key
    title_data: Optional[Any] = tags.get(title_key, None) if title_key else None
    # assert the title data is iterable
    title_list: Optional[Iterator[Any]] = iter(title_data) if isinstance(title_data, Iterable) else None
    # get the first item in the title list, if available
    title: Optional[str] = ', '.join(title_list) if title_list else None
    # assign the metadata's title if the retrieved title data is a str
    metadata.title = title if isinstance(title, str) else None

    # get the artist key from the tagging keys dictionary
    artist_key: Optional[str] = tagging_keys.get('artist', None)
    # get the artist tag data via the key
    artist_data: Optional[Any] = tags.get(artist_key, None) if artist_key else None
    # assert the artist data is iterable
    artist_list: Optional[Iterator[Any]] = iter(artist_data) if isinstance(artist_data, Iterable) else None
    # get the first item in the artist list, if available
    artist: Optional[str] = ', '.join(artist_list) if artist_list else None
    # assign the metadata's artist if the retrieved artist data is a str
    metadata.artist = artist if isinstance(artist, str) else None

    # return the edited metadata
    return metadata

def __parse_cover__(metadata: Metadata, binary: BufferedIOBase, tagging_keys: Dict[Union[Literal['artist', 'title'], str], str]) -> Metadata:
    if not importlib.util.find_spec('mutagen'):
        log.warning('Unable to find mutagen module. Audio metadata extraction will be skipped.')
        return metadata
    import mutagen
    from mutagen._util import DictMixin

    file: Optional[mutagen.FileType] = mutagen.File(binary) # type: ignore
    if not file:
        raise Exception('Could not determine file container type.')

    if not importlib.util.find_spec('PIL'):
        log.warning('Unable to find Pillow module. Audio cover metadata extraction will be skipped.')
        return metadata
    from PIL import Image

    # retrieve the file's tags
    tags: mutagen.Tags = file.tags # type: ignore
    # if the tags instance is not a type of DictProxy, raise exception
    if not isinstance(tags, DictMixin):
        raise Exception()

    if isinstance(file, mutagen.flac.FLAC): # type: ignore
        # assert the cover data is iterable
        cover_list: Optional[Iterator[Any]] = iter(file.pictures) if isinstance(file.pictures, Iterable) else None
        # get the first item in the cover list, if available
        cover: Optional[Any] = next(cover_list, None) if cover_list else None
        # get the cover if the retrieved cover data is a picture
        thumbnail_data: Optional[BytesIO] = BytesIO(cover.data) if isinstance(cover, mutagen.flac.Picture) else None # type: ignore
        # open the thumbnail data as an Image
        image: Optional[Image.Image] = Image.open(fp=thumbnail_data) if thumbnail_data else None
        # initialize a buffer to save the thumbnail image data to
        buffer: BytesIO = BytesIO()
        # resize the image
        if image: image.thumbnail((256, 256))
        # save the image to the buffer
        if image: image.save(fp=buffer, format='png')
        # seek to the beginning of the buffer
        buffer.seek(0)
        # assign the metadata's thumbnail by reading the buffer out
        metadata.thumbnail = buffer.read() if image else None

    if isinstance(file, mutagen.id3.ID3FileType): # type: ignore
        # get the cover key from the tagging keys dictionary
        cover_key: Optional[str] = tagging_keys.get('cover', None)
        # get the cover tag data via the key
        cover: Optional[Any] = tags.get(cover_key, None) if cover_key else None
        # get the data from the APIC frame if it is available
        thumbnail_data: Optional[BytesIO] = BytesIO(cover.data) if isinstance(cover, mutagen.id3.APIC) else None # type: ignore
        # open the thumbnail data as an Image
        image: Optional[Image.Image] = Image.open(fp=thumbnail_data) if thumbnail_data else None
        # initialize a buffer to save the thumbnail image data to
        buffer: BytesIO = BytesIO()
        # resize the image
        if image: image.thumbnail((256, 256))
        # save the image to the buffer
        if image: image.save(fp=buffer, format='png')
        # seek to the beginning of the buffer
        buffer.seek(0)
        # assign the metadata's thumbnail by reading the buffer out
        metadata.thumbnail = buffer.read() if image else None

    # return the edited metadata
    return metadata