from __future__ import annotations

import importlib.util
from io import BytesIO
from sqlite3 import Row
from typing import Any, Optional, Tuple, Type
from bot.database import ColumnBuilder, Table, TableBuilder, TStorable

import requests


class Metadata():
    def __init__(self, id: int, *, user_id: Optional[int] = None, title: Optional[str] = None, artist: Optional[str] = None, hyperlink: Optional[str] = None, media_url: Optional[str] = None, thumbnail: Optional[str] = None) -> None:
        self.id:        int = id
        self.user_id:   Optional[int] = user_id
        self.title:     Optional[str] = title
        self.artist:    Optional[str] = artist
        self.hyperlink: Optional[str] = hyperlink
        self.thumbnail: Optional[bytes] = None

        if importlib.util.find_spec('PIL') and thumbnail is not None:                
            from PIL import Image                
            # create a request to the thumbnail reference
            response: Optional[requests.Response] = requests.get(thumbnail, stream=True)
            # initialize a BytesIO instance from the data received from the request
            thumbnail_data: Optional[BytesIO] = BytesIO(response.content) if response else None
            # open the thumbnail data as an Image
            image: Optional[Image.Image] = Image.open(thumbnail_data) if thumbnail_data else None
            # initialize a buffer to save the thumbnail image data to
            buffer: BytesIO = BytesIO()
            # resize the image
            if image: image.thumbnail((256, 256))
            # save the image to the buffer
            if image: image.save(fp=buffer, format='png')
            # seek to the beginning of the buffer
            buffer.seek(0)
            # assign the metadata's thumbnail by reading the buffer out
            self.thumbnail: Optional[bytes] = buffer.read() if image else None

    def __str__(self) -> str:
        return f'{self.artist} - {self.title} <{self.hyperlink}>'

    _table: Table

    @classmethod
    def __table__(cls) -> Table:
        table: TableBuilder = TableBuilder().setName('Metadata')
        column: ColumnBuilder = ColumnBuilder()
        table.addColumn(column.setName('ID').setType('INTEGER').isPrimary().isUnique().build())
        table.addColumn(column.setName('UserID').setType('INTEGER').build())
        table.addColumn(column.setName('Title').setType('TEXT').build())
        table.addColumn(column.setName('Artist').setType('TEXT').build())
        table.addColumn(column.setName('Hyperlink').setType('TEXT').build())
        table.addColumn(column.setName('Thumbnail').setType('BLOB').build())
        return table.build()

    def __values__(self) -> Tuple[Any, ...]:
        # create a tuple with the corresponding values
        value: Tuple[Any, ...] = (self.id, self.user_id, self.title, self.artist, self.hyperlink, self.thumbnail)
        # return the tuple
        return value

    @classmethod
    def __from_row__(cls: Type[TStorable], row: Row) -> Metadata:
        id: Optional[int] = row['ID'] if isinstance(row['ID'], int) else None
        if not id: raise KeyError('id')
        metadata: Metadata = Metadata(id)

        user_id: Optional[int] = row['UserID'] if isinstance(row['UserID'], int) else None
        metadata.user_id = user_id

        title: Optional[str] = row['Title'] if isinstance(row['Title'], str) else None
        metadata.title = title

        artist: Optional[str] = row['Artist'] if isinstance(row['Artist'], str) else None
        metadata.artist = artist

        hyperlink: Optional[str] = row['Hyperlink'] if isinstance(row['Hyperlink'], str) else None
        metadata.hyperlink = hyperlink

        thumbnail: Optional[bytes] = row['Thumbnail'] if isinstance(row['Thumbnail'], bytes) else None
        metadata.thumbnail = thumbnail

        return metadata