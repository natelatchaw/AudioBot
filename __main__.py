import asyncio
import logging
import sys
from typing import List, Optional, Union

import discord

from core import Core
from metadata import Metadata
from request import Request


root: logging.Logger = logging.getLogger()

formatter: logging.Formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s')

stdoutHandler: logging.StreamHandler = logging.StreamHandler(sys.stdout)
stdoutHandler.setFormatter(formatter)
stdoutHandler.setLevel(logging.DEBUG)
root.addHandler(stdoutHandler)



log: logging.Logger = logging.getLogger(__name__)


def get_embed(interaction: discord.Interaction, metadata: Metadata) -> discord.Embed:
    user: Union[discord.User, discord.Member] = interaction.user

    embed: discord.Embed = discord.Embed()

    embed.set_author(name=user.display_name, icon_url=user.avatar.url)
    embed.set_image(url=metadata.thumbnail)

    embed.title =           metadata.title
    embed.description =     metadata.channel
    embed.url =             metadata.url
    embed.timestamp =       interaction.created_at
    embed.color =           discord.Colour.from_rgb(r=255, g=0, b=0)
    
    return embed


core: Core = Core(intents=discord.Intents.all())


@core.tree.command()
@discord.app_commands.describe(query='Audio content to search for', speed='Audio playback multiplier')
async def play(
    interaction: discord.Interaction, 
    query: str,
    speed: Optional[discord.app_commands.Range[float, 0.5, 2.0]]
) -> None:
    """
    Plays audio in a voice channel
    """
    followup: discord.Webhook = interaction.followup
    await interaction.response.defer(ephemeral=False, thinking=True)

    options: List[str] = list()

    try:
        await core._audio.__connect__(interaction)
    except discord.ClientException as exception:
        log.warn(exception)

    try:
        # download metadata for the provided query
        metadata: Optional[Metadata] = await core._audio.__query__(interaction, f'ytsearch:{query}')
        if not metadata: raise Exception(f"No result found for '{query}'.")        

        # get multiplier if speed was provided
        multiplier: Optional[float] = float(speed) if speed else None
        # assert the multiplier is within supported bounds
        multiplier = multiplier if multiplier and multiplier > 0.5 and multiplier < 2.0 else None
        # if a multiplier was specified, add it to the options list
        if multiplier: options.append(rf'-filter:a "atempo={multiplier}"')

        # queue the song and get the song's request data
        request: Optional[Request] = await core._audio.__queue__(metadata, options=options)

        # generate an embed from the song request data
        embed: discord.Embed = get_embed(interaction, request.metadata)

        # send the embed
        await followup.send(embed=embed)
    
    except Exception as exception:
        await followup.send(exception)
        

@core.tree.command()
async def skip(
    interaction: discord.Interaction
) -> None:
    """
    Skips the currently playing song
    """
    followup: discord.Webhook = interaction.followup
    await interaction.response.defer(ephemeral=False, thinking=True)

    # skip the song and get the skipped song's metadata.
    metadata: Metadata = await core._audio.__skip__()

    # generate an embed from the song request data
    embed: discord.Embed = get_embed(interaction, metadata)
    # send the embed
    await followup.send(f'Skipped {metadata.title}')


@core.tree.command()
@discord.app_commands.describe(enabled='Whether timeout should be enabled', duration='The duration of the timeout')
async def timeout(
    interaction: discord.Interaction,
    enabled: bool,
    duration: Optional[float]
) -> None:
    """
    Sets the bot's timeout duration in a voice channel
    """
    followup: discord.Webhook = interaction.followup
    await interaction.response.defer(ephemeral=False, thinking=True)

    core._audio.timeout = duration if enabled else None
    if enabled and core._audio.timeout:
        await followup.send(f'Timeout set to {core._audio.timeout} seconds.')
    elif enabled and not core._audio.timeout:
        await followup.send(f'Timeout disabled; no duration specified.')
    else:
        await followup.send(f'Timeout disabled.')


asyncio.run(core.start(core._settings.client.token.current))