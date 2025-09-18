import logging
from collections.abc import Buffer
from io import BufferedIOBase, BytesIO
from pathlib import Path
from typing import Literal, Optional

import discord
import numpy as np
from discord import AudioSource
from numpy.typing import NDArray
from pretty_midi import PrettyMIDI
from scipy.io.wavfile import write as write_wav

from ..embed import RequestEmbed
from ..metadata import Metadata
from ..request import Request

log: logging.Logger = logging.getLogger(__name__)


class MidiRequest(Request):

    @property
    def metadata(self) -> Metadata:
        id: int = self._interaction.id
        user_id: int = self._interaction.user.id
        title: str = self._midi.filename
        hyperlink: str = self._midi.url
        return Metadata(id, user_id=user_id, title=title, artist=None, hyperlink=hyperlink, thumbnail=None)

    def __init__(self, interation: discord.Interaction, midi: discord.Attachment, *, sf2: Optional[discord.Attachment] = None):
        self._interaction: discord.Interaction = interation
        self._midi: discord.Attachment = midi
        self._sf2: Optional[discord.Attachment] = sf2

    async def process(self) -> AudioSource:
        midi_data: Buffer = await self._midi.read()
        midi_fp: BytesIO = BytesIO(midi_data)

        sf2_path: Optional[Path] = self.soundfonts.joinpath(self._sf2.filename) if self._sf2 else None
        if self._sf2 and sf2_path: await self._sf2.save(sf2_path)

        # specify the sampling rate
        sampling_rate: int = 44100

        # initialize midi with data and synthesize to waveform
        waveform: NDArray = PrettyMIDI(midi_file=midi_fp).fluidsynth(fs=sampling_rate, sf2_path=str(sf2_path))
        # calculate max amplitude
        amplitude: int = np.iinfo(np.int16).max
        # calculate the maximum of the waveform
        maximum: NDArray = np.max(np.abs(waveform))
        # normalize the waveform given the waveform's maximum and the amplitude
        waveform = (waveform / maximum) * amplitude
        # cast the waveform to a 16-bit array
        waveform = waveform.astype(np.int16)
        
        # create a byte buffer
        buffer: Buffer = bytes()
        # initialize BytesIO with created buffer
        fp: BufferedIOBase = BytesIO(buffer)
        # write the waveform to the file object
        write_wav(fp, 44100, waveform)

        # create and return the audio source
        return discord.FFmpegPCMAudio(fp, pipe=True)

    @property
    def soundfonts(self) -> Path:
        directory: Path = Path('./sf2').absolute()
        if not directory.exists(): directory.mkdir(parents=True, exist_ok=True)
        return directory        

    async def as_embed(self, interaction: discord.Interaction, *, large_image: bool = True, thumbnail_format: Literal['png', 'bmp'] = 'png') -> RequestEmbed:
        return await super().as_embed(interaction, large_image=large_image, thumbnail_format=thumbnail_format)