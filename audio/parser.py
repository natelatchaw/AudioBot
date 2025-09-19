import logging
from pathlib import Path
import sys
from collections.abc import Buffer
from io import BufferedIOBase, BytesIO
from logging import Logger
from typing import (Any, Dict, Iterable, Iterator, List, Optional, Tuple,
                    TypedDict)

import mutagen
from mutagen._file import FileType
from mutagen._tags import Tags
from mutagen.flac import FLAC, VCFLACDict
from mutagen.id3 import ID3, ID3FileType
from mutagen.id3._frames import APIC
from mutagen.mp4 import MP4, MP4Cover, MP4Tags

log: Logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class TagKeys(TypedDict):
    album: str
    artist: str
    title: str


keys: Dict[type, TagKeys] = {
    ID3: {
        'album':    'TALB',
        'artist':   'TPE1',
        'title':    'TIT2',
    },
    MP4Tags: {
        'album':    '©alb',
        'artist':   '©ART',
        'title':    '©nam',
    },
    VCFLACDict: {
        'album':    'ALBUM',
        'artist':   'ARTIST',
        'title':    'TITLE',
    }
}


class Parser():

    @property
    def _tags(self) -> Optional[Tags]:
        tags: Optional[Tags] = self._file.tags if isinstance(self._file.tags, Tags) else None # type: ignore
        if not tags: raise Exception('No tags found.')
        #log.debug(f'Determined file tags to be {type(tags)}')
        value: Tags = tags   # shut the typechecker up
        return value
    
    @property
    def _keys(self) -> Optional[TagKeys]:
        tag_type: type = type(self._tags)
        value: Optional[TagKeys] = keys.get(tag_type, None)
        return value


    def __init__(self, fp: BufferedIOBase) -> None:
        self._fp: BufferedIOBase = fp

        file: Optional[FileType] = mutagen.File(fp) # type: ignore
        if not isinstance(file, FileType): raise Exception('Incompatible file provided.')
        #log.debug(f'Determined file to be {type(file)}')
        self._file: FileType = file


    @property
    def title(self) -> Optional[List[str]]:
        """Retrieve the title metadata for the file-like object."""  

        key: Optional[str] = self._keys.get('title', None) if self._keys else None    
        data: Optional[Any] = self._tags.get(key, None)                                                     # type: ignore
        content: Optional[Iterator[Any]] = iter(data) if isinstance(data, Iterable) else None               # type: ignore
        if not isinstance(content, Iterator): return None
        
        values: List[str] = [value for value in content if isinstance(value, str)]
        return values


    @property
    def artists(self) -> Optional[List[str]]:
        """Retrieve the artist metadata for the file-like object."""  

        key: Optional[str] = self._keys.get('artist', None) if self._keys else None    
        data: Optional[Any] = self._tags.get(key, None)                                                     # type: ignore
        content: Optional[Iterator[Any]] = iter(data) if isinstance(data, Iterable) else None               # type: ignore
        if not isinstance(content, Iterator): return None
        
        values: List[str] = [value for value in content if isinstance(value, str)]
        return values
    
    @property
    def album(self) -> Optional[List[str]]:
        """Retrieve the album metadata for the file-like object."""

        key: Optional[str] = self._keys.get('album', None) if self._keys else None
        data: Optional[Any] = self._tags.get(key, None)                                                     # type: ignore
        content: Optional[Iterator[Any]] = iter(data) if isinstance(data, Iterable) else None               # type: ignore
        if not isinstance(content, Iterator): return None
        
        values: List[str] = [value for value in content if isinstance(value, str)]
        return values
    
    @property
    def cover(self) -> Optional[Buffer]:
        """Retrieve the album cover binary image data."""

        size: Tuple[int, int] = (256, 256)

        if isinstance(self._file, FLAC):
            return self._extract_flac(size=size)
        
        if isinstance(self._file, ID3FileType):
            return self._extract_id3(size=size)
        
        
        if isinstance(self._file, MP4):
            return self._extract_mp4(size=size)
            

    def _extract_flac(self, *, size: Tuple[int, int]) -> Optional[Buffer]:
        if not isinstance(self._file, FLAC): return None
        pictures: List[Any] = file.pictures # type: ignore
        buffers: List[Buffer] = [picture.data for picture in pictures if isinstance(picture.data, Buffer)]      # type: ignore
        try:
            buffer: Optional[Buffer] = buffers.pop(0)
            return _to_thumbnail(buffer, size=size)
        except IndexError:
            pass

        key: str = 'metadata_block_picture'#'METADATA_BLOCK_PICTURE'
        cover: Optional[Any] = self._tags.get(key, None) if key else None                   # type: ignore
        #if not isinstance(cover, object): return None
        buffer: Optional[Buffer] = cover if isinstance(cover, Buffer) else None
        return _to_thumbnail(buffer, size=size) if buffer else _default_thumbnail(size=size)
    
    def _extract_id3(self, *, size: Tuple[int, int]) -> Optional[Buffer]:
        if not isinstance(self._file, ID3FileType): return None
        key: str = 'APIC:'
        cover: Optional[Any] = self._tags.get(key, None) if key else None                   # type: ignore
        buffer: Optional[Buffer] = cover.data if isinstance(cover, APIC) and isinstance(cover.data, Buffer) else None   # type: ignore
        return _to_thumbnail(buffer, size=size) if buffer else _default_thumbnail(size=size)
    
    def _extract_mp4(self, *, size: Tuple[int, int]) -> Optional[Buffer]:
        if not isinstance(self._file, MP4): return None
        key: str = 'covr'
        value: Optional[List[Any]] = self._tags.get(key, None) if key else None             # type: ignore
        covers: Optional[List[MP4Cover]] = [cover for cover in value if isinstance(cover, MP4Cover)] if value else None  # type: ignore
        try:
            cover: Optional[MP4Cover] = covers.pop(0) if covers else None
        except IndexError:
            cover: Optional[MP4Cover] = None
        
        #if not isinstance(cover, MP4Cover): return None
        buffer: Optional[Buffer] = cover if isinstance(cover, Buffer) else None
        return _to_thumbnail(buffer, size=size) if buffer else _default_thumbnail(size=size)


try:
    from PIL import Image
    
    def _to_thumbnail(buffer: Buffer, *, size: Tuple[int, int]) -> Optional[Buffer]:
        # load the provided buffer into a stream
        input: BytesIO = BytesIO(buffer)

        # open the stream as an image
        image: Image.Image = Image.open(fp=input, mode='r')
        # create a thumbnail from the image of size
        image.thumbnail(size)

        # create a stream so write data to
        output: BufferedIOBase = BytesIO()
        # save the image to the stream
        image.save(fp=output, format='png')
        # seek to the beginning of the stream
        output.seek(0)
        # read out a buffer from the stream
        return output.read()
    
    def _default_thumbnail(*, size: Tuple[int, int]) -> Optional[Buffer]:
        # get the path of the default png
        path: Path = Path(__file__).parent.joinpath('default.png')
        # if the file does not exist, return None
        if not path.exists():
            log.warning(f'Cannot find {path.name} in directory {path.parent}')
            return None

        # open the file and read the contents
        with open(path, 'rb') as file: buffer: Buffer = file.read()
        # load read buffer into stream
        input: BytesIO = BytesIO(buffer)

        # open the stream as an image
        image: Image.Image = Image.open(fp=input, mode='r')
        # create a thumbnail from the image of size
        image.thumbnail(size)

        # create a stream so write data to
        output: BufferedIOBase = BytesIO()
        # save the image to the stream
        image.save(fp=output, format='png')
        # seek to the beginning of the stream
        output.seek(0)
        # read out a buffer from the stream
        return output.read()
    
except ModuleNotFoundError:

    def _to_thumbnail(buffer: Buffer, size: Tuple[int, int]) -> Optional[Buffer]:
        return None
    
    def _default_thumbnail(*, size: Tuple[int, int]) -> Optional[Buffer]:
        return None