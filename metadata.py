from __future__ import annotations

from typing import Any, Dict

import discord


class Metadata():

    def __init__(self, id: int, user_id: int, video_id: str, title: str, channel: str, thumbnail: str, url: str, video_url: str) -> None:
        self._id: int = id
        self._user_id: int = user_id
        self._video_id: str = video_id
        self._title: str = title
        self._channel: str = channel
        self._thumbnail: str = thumbnail
        self._source: str = url
        self._url: str = video_url

    @property
    def id(self) -> int:
        return self._id

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def video_id(self) -> str:
        return self._video_id

    @property
    def title(self) -> str:
        return self._title
    
    @property
    def channel(self) -> str:
        return self._channel
    
    @property
    def thumbnail(self) -> str:
        return self._thumbnail

    @property
    def source(self) -> str:
        return self._source

    @property
    def url(self) -> str:
        return self._url

        

    @classmethod
    def __from_dict__(cls, interaction: discord.Interaction, dict: Dict[str, Any]) -> Metadata:

        id: int = interaction.id
        user_id: int = interaction.user.id

        video_id: str = dict['id']
        if not isinstance(video_id, str): raise KeyError('id')

        title: str = dict['title']
        if not isinstance(title, str): raise KeyError('title')

        channel: str = dict['channel']
        if not isinstance(channel, str): raise KeyError('channel')

        thumbnail: str = dict['thumbnail']
        if not isinstance(channel, str): raise KeyError('thumbnail')

        url: str = dict['url']
        if not isinstance(url, str): raise KeyError('url')

        video_url: str = dict['webpage_url']
        if not isinstance(video_url, str): raise KeyError('video_url')

        return Metadata(id, user_id, video_id, title, channel, thumbnail, url, video_url)
