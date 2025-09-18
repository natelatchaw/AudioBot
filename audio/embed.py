from datetime import datetime
import hashlib
from io import BytesIO
from typing import List, Literal, Optional, Tuple, Union
import discord

from .metadata import Metadata


class RequestEmbed(discord.Embed):

    def __init__(self, metadata: Metadata, user: Union[discord.User, discord.Member], timestamp: Optional[datetime] = None, *, large_image: bool = True, thumbnail_format: Literal['png', 'bmp'] = 'png'):
        # store the provided metadata
        self._metadata: Metadata = metadata

        color: discord.Color = discord.Color.blurple()
        title: str = self._metadata.title if self._metadata.title else "Unknown Title"
        description: Optional[str] = self._metadata.artist if self._metadata.artist else "Unknown Artist"
        url: Optional[str] = self._metadata.hyperlink
        super().__init__(color=color, title=title, description=description, url=url, timestamp=timestamp)

        self.set_author(name=user.display_name, icon_url=user.avatar.url if user.avatar else None)

        thumbnail: Optional[bytes] = self._metadata.thumbnail
        image_data: BytesIO = BytesIO(thumbnail) if thumbnail else BytesIO()

        identifier: Optional[str] = hashlib.md5(thumbnail).hexdigest() if thumbnail else None
        filename: Optional[str] = '.'.join([identifier, thumbnail_format]) if identifier else None
        self._file: Optional[discord.File] = discord.File(fp=image_data, filename=filename)

        thumbnail_url: Optional[str] = f'attachment://{self._file.filename}' if self._file else None
        self.set_image(url=thumbnail_url if large_image else None)
        self.set_thumbnail(url=thumbnail_url if not large_image else None)

    @property
    def file(self) -> Optional[discord.File]:
        return self._file
        

class RequestQueueEmbed(discord.Embed):

    def __init__(self, interaction: discord.Interaction, metadata: Metadata, queue: List[Metadata], large_image: bool = False, thumbnail_format: Literal['png', 'bmp'] = 'png'):
        # store the provided metadata
        self._metadata: Metadata = metadata

        color: discord.Color = discord.Color.blurple()
        title: str = self._metadata.title if self._metadata.title else "Unknown Title"
        description: Optional[str] = self._metadata.artist if self._metadata.artist else "Unknown Artist"
        url: Optional[str] = self._metadata.hyperlink
        timestamp: Optional[datetime] = interaction.created_at
        super().__init__(color=color, title=title, description=description, url=url, timestamp=timestamp)

        user: Union[discord.User, discord.Member] = interaction.user
        self.set_author(name=user.display_name, icon_url=user.avatar.url if user.avatar else None)

        thumbnail: Optional[bytes] = self._metadata.thumbnail
        image_data: BytesIO = BytesIO(thumbnail) if thumbnail else BytesIO()

        identifier: Optional[str] = hashlib.md5(thumbnail).hexdigest() if thumbnail else None
        filename: Optional[str] = '.'.join([identifier, thumbnail_format]) if identifier else None
        self._file: Optional[discord.File] = discord.File(fp=image_data, filename=filename)

        thumbnail_url: Optional[str] = f'attachment://{self._file.filename}' if self._file else None
        self.set_image(url=thumbnail_url if large_image else None)
        self.set_thumbnail(url=thumbnail_url if not large_image else None)

        for item in queue: self.add_field(name=item.title, value=item.artist, inline=False)

    @property
    def file(self) -> Optional[discord.File]:
        return self._file
        

class RequestFrequencyEmbed(discord.Embed):

    def __init__(self, interaction: discord.Interaction, metadata: List[Tuple[Metadata, int]]):
        color: discord.Color = discord.Color.blurple()
        user: Union[discord.User, discord.Member] = interaction.user
        title: str = 'Top Requests'
        description: Optional[str] = None
        url: Optional[str] = None
        timestamp: Optional[datetime] = interaction.created_at
        super().__init__(color=color, title=title, description=description, url=url, timestamp=timestamp)
        self.set_author(name=user.display_name, icon_url=user.avatar.url if user.avatar else None)

        for item, count in metadata: self.add_field(name=item.title, value=f'{count} requests', inline=False)

class RequestRecentEmbed(discord.Embed):

    def __init__(self, interaction: discord.Interaction, metadata: List[Tuple[Metadata, datetime]]):
        color: discord.Color = discord.Color.blurple()
        user: Union[discord.User, discord.Member] = interaction.user
        title: str = 'Recent Requests'
        description: Optional[str] = None
        url: Optional[str] = None
        timestamp: Optional[datetime] = interaction.created_at
        super().__init__(color=color, title=title, description=description, url=url, timestamp=timestamp)
        self.set_author(name=user.display_name, icon_url=user.avatar.url if user.avatar else None)

        for item, timestamp in metadata: self.add_field(name=item.title, value=f'{timestamp.strftime("%Y-%m-%d")}', inline=False)
