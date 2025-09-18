from __future__ import annotations

import importlib.util
import logging
from collections import Counter
from datetime import datetime
from importlib.machinery import ModuleSpec
from logging import Logger
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, MutableMapping, Optional, Sequence, Tuple

import discord
from bot.database import Database
from discord import Interaction, PartialEmoji
from discord.app_commands import describe

log: Logger = logging.getLogger(__name__)

location: Path = Path('./audio/__init__.py')
spec: Optional[ModuleSpec] = importlib.util.spec_from_file_location('audio', location)
if not spec: raise Exception('Could not get ModuleSpec')
log.debug(f'Found companion ModuleSpec {spec.name}')

module: Optional[ModuleType] = importlib.util.module_from_spec(spec) if spec else None
if not module: raise Exception('Could not find ModuleType')
log.debug(f'Found companion ModuleType {module.__name__}')

if spec.loader: spec.loader.exec_module(module)
log.debug(f'Imported companion ModuleType {module.__name__} from {module.__path__}')

from audio import (AudioError, FileRequest, Metadata, MidiRequest, Player,
                   Request, RequestEmbed, RequestFrequencyEmbed,
                   RequestRecentEmbed, YouTubeRequest)


class Audio():
    """
    Component responsible for audio playback.
    """

    #region Properties

    @property
    def timeout(self) -> Optional[float]:
        key: str = "timeout"
        value: Optional[str] = None
        try:
            value = self._config[key]
            return float(value) if value else None
        except:
            self._config[key] = ""
            return None

    @timeout.setter
    def timeout(self, value: float) -> None:
        key: str = "timeout"
        if value: self._config[key] = str(value)

    @property
    def update_activity(self) -> Optional[bool]:
        key: str = 'update_activity'
        value: Optional[str] = None
        try:
            value = self._config[key]
            if value.lower() in ['true', 'yes', 'y', '1']:
                return True
            if value.lower() in ['false', 'no', 'n', '0']:
                return False
            return None
        except:
            self._config[key] = ""
            return None

    @property
    def before_options(self) -> Optional[List[str]]:
        key: str = 'before_options'
        value: Optional[str] = None
        try:
            value = self._config[key]
            return value.split(' ')
        except:
            self._config[key] = ''
            return None

    @property
    def after_options(self) -> Optional[List[str]]:
        key: str = 'after_options'
        value: Optional[str] = None
        try:
            value = self._config[key]
            return value.split(' ')
        except:
            self._config[key] = ''
            return None

    #endregion


    #region Lifecycle Events

    def __init__(self, *args: Any, config: MutableMapping[str, str], **kwargs: Any):
        """
        Initializes state management objects for the audio loop
        """

        self._config: MutableMapping[str, str] = config        
        self.player: Player = Player(timeout=self.timeout)

    async def __setup__(self) -> None:
        """
        Called after instance properties are initialized.
        """

        # create database instance
        self._database: Database = Database(Path(f'./data/{__name__}.db'))
        self._database.create(Metadata)

        # begin player loop
        await self.player.loop()

    #endregion


    #region Application Commands

    @describe(file='The audio file to play')
    async def file(self, interaction: Interaction, file: discord.Attachment) -> None:
        """
        Plays an audio file in a voice channel
        """

        followup: discord.Webhook = interaction.followup
        await interaction.response.defer(ephemeral=False, thinking=True)

        try:
            # connect the player to the channel
            await self.player.connect(interaction)

            request: Request = FileRequest(interaction, file, before_options=None, after_options=['-b:a', '192k'])
            if isinstance(request, FileRequest): await request.parse()

            # queue the request
            await self.player.queue(interaction, request)

            # generate an embed from the song request data
            embed: RequestEmbed = await request.as_embed(interaction)
            # send the embed
            await followup.send(embed=embed, file=embed.file)

        except Exception as exception:
            await followup.send(f'{exception}')
            raise

    @describe(query='A URL or video title to search for')
    async def play(self, interaction: Interaction, query: str) -> None:
        """
        Plays audio in a voice channel
        """

        followup: discord.Webhook = interaction.followup
        await interaction.response.defer(ephemeral=False, thinking=True)

        try:
            # connect the player to the channel
            await self.player.connect(interaction)

            # create a request from the provided query
            request: Request = YouTubeRequest(interaction, query, before_options=self.before_options, after_options=self.after_options)
            if isinstance(request, YouTubeRequest): await request.parse()

            # queue the request
            await self.player.queue(interaction, request)

            # generate an embed from the song request data
            embed: RequestEmbed = await request.as_embed(interaction)
            # send the embed
            await followup.send(embed=embed, file=embed.file)

        except Exception as exception:
            await followup.send(f'{exception}')
            raise

    @describe(midi='The MIDI file to play')
    @describe(sf2='A soundfont file to render the MIDI with')
    async def midi(self, interaction: Interaction, midi: discord.Attachment, sf2: Optional[discord.Attachment]) -> None:
        """
        Plays audio in a voice channel
        """

        followup: discord.Webhook = interaction.followup
        await interaction.response.defer(ephemeral=False, thinking=True)

        try:
            # connect the player to the channel
            await self.player.connect(interaction)

            request: Request = MidiRequest(interaction, midi, sf2=sf2)

            # queue the request
            await self.player.queue(interaction, request)

            # generate an embed from the song request data
            embed: RequestEmbed = await request.as_embed(interaction)
            # send the embed
            await followup.send(embed=embed, file=embed.file)

        except Exception as exception:
            await followup.send(f'{exception}')
            raise

    async def queue(self, interaction: discord.Interaction) -> None:
        """
        Displays the request queue
        """

        followup: discord.Webhook = interaction.followup
        await interaction.response.defer(ephemeral=False, thinking=True)

        try:
            # if there is no current request in the player
            if self.player.current is None: raise AudioError("Nothing is playing right now.")
            
            # get reference to the current request's metadata
            metadata: Metadata = self.player.current.metadata
            # get the first 5 upcoming requests' metadata
            queue: List[Metadata] = [request.metadata for request in list(self.player._queue)][:5]

            # generate an embed from the song request data
            embed: RequestEmbed = RequestEmbed(metadata, interaction.user, interaction.created_at, large_image=False)
            # add fields for upcoming requests
            for item in queue: embed.add_field(name=item.title, value=item.artist, inline=False)

            # send the embed
            await followup.send(embed=embed, file=embed.file)

        except AudioError as exception:
            await followup.send(f'{exception}')
            raise

    async def skip(self, interaction: discord.Interaction) -> None:
        """
        Skips the currently playing song
        """

        followup: discord.Webhook = interaction.followup
        await interaction.response.defer(ephemeral=False, thinking=True)

        try:
            # get the request to be skipped
            current: Optional[Request] = self.player.current
            # get the metadata of the request
            metadata: Optional[Metadata] = current.metadata if current else None

            # skip the song
            await self.player.skip(interaction)
            # determine whether the message should be ephemeral
            ephemeral: bool = metadata is None

            # send the embed
            await followup.send(f'Skipped {metadata.title}' if metadata else 'Nothing is playing', ephemeral=ephemeral)
        
        except Exception as exception:
            await followup.send(f'{exception}')
            raise

    @describe(user='The user to calculate most frequent song requests for.')
    async def top(self, interaction: discord.Interaction, user: Optional[discord.User] = None) -> None:
        """
        Displays your most frequent song requests
        """

        followup: discord.Webhook = interaction.followup
        await interaction.response.defer(ephemeral=False, thinking=True)

        # get the user's ID
        user_id: int = user.id if user else interaction.user.id
        # get the user's stored metadata
        results: List[Metadata] = [metadata for metadata in self._database.select(Metadata) if metadata.user_id == user_id]

        videos: Dict[str, Metadata] = { metadata.title : metadata for metadata in results if metadata.title }
        counted = Counter(metadata.title for metadata in results if metadata.title)
        top: Sequence[Tuple[str, int]]= counted.most_common(5)
        output: List[Tuple[Metadata, int]] = [(videos[entry], count) for entry, count in top]

        # generate an embed from the song request data
        embed: discord.Embed = RequestFrequencyEmbed(interaction, output)
        # send the embed
        await followup.send(embed=embed)

    @describe(user='The user to calculate most recent song requests for.')
    async def recent(self, interaction: discord.Interaction, user: Optional[discord.User] = None) -> None:
        """
        Displays your most recent song requests
        """

        followup: discord.Webhook = interaction.followup
        await interaction.response.defer(ephemeral=False, thinking=True)

        # get the user's ID
        user_id: int = user.id if user else interaction.user.id
        # get the user's stored metadata
        results: List[Metadata] = [metadata for metadata in self._database.select(Metadata) if metadata.user_id == user_id]

        # if no results are found
        if len(results) == 0:
            await followup.send('No recent requests found.')
            return

        # sort the results by id, descending (id is a snowflake timestamp)
        results = sorted(results, key=lambda result: result.id, reverse=True)[:5]
        # map each result to a tuple containing the timestamp
        output: List[Tuple[Metadata, datetime]] = [(result, discord.utils.snowflake_time(result.id)) for result in results]

        # generate an embed from the song request data
        embed: discord.Embed = RequestRecentEmbed(interaction, output)
        # send the embed
        await followup.send(embed=embed)

    #endregion


    #region Client Activity State Management

    async def __update_activity__(self, client: discord.VoiceClient, metadata: Optional[Metadata]):
        """
        Updates the bot's activity state to the provided request.
        """

        # return if updating the activity is disabled
        if not self.update_activity: return

        try:
            # get the guild's shard id
            shard_id: int = client.guild.shard_id
            # create an activity from request metadata
            activity: Optional[discord.Activity] = Audio.RequestActivity(metadata) if metadata else None
            # if the client is a sharded client
            if isinstance(client.client, discord.AutoShardedClient):
                log.debug('Sharding detected. Supplying shard id...')
                # update the client's activity presence with the request and specify the shard
                return await client.client.change_presence(activity=activity, shard_id=shard_id)
            else:
                log.debug('No sharding detected. Ignoring shard id...')
                # update the client's activity presence with the request
                return await client.client.change_presence(activity=activity)

        except (Exception) as exception:
            log.error(exception)

    #endregion


    #region Associated Classes
  
    class RequestActivity(discord.Activity):

        def __init__(self, current: Metadata) -> None:
            self.state: Optional[str] = None
            self.type: discord.ActivityType = discord.ActivityType.listening
            self.name: Optional[str] = current.title if current.title else "Unknown Title"
            self.details: Optional[str] = current.artist if current.artist else "Unknown Artist"
            self.url: Optional[str] = current.hyperlink
            self.emoji: Optional[PartialEmoji] = None

    #endregion