from typing import List, Optional, Union
import discord

from demerit import Demerit, DemeritManager

def as_embed(demerit: Demerit, user: discord.Member, author: discord.Member) -> discord.Embed:
    embed: discord.Embed = discord.Embed()

    embed.set_author(name=author.display_name, icon_url=author.avatar.url)
    if user.avatar: embed.set_thumbnail(url=user.avatar.url)

    embed.title = f"Demerit Submitted for {user.display_name}"
    embed.add_field(name='Reason', value=demerit.reason, inline=False)
    embed.add_field(name='Details', value=demerit.details, inline=False)

    embed.timestamp = demerit.timestamp

    return embed

class DemeritModal(discord.ui.Modal):

    def __init__(self, user: discord.Member, author: discord.Member, manager: DemeritManager, *, timeout: Optional[float] = None) -> None:
        self._user: discord.Member = user
        self._author: discord.Member = author
        self._manager: DemeritManager = manager
        super().__init__(timeout=timeout)

    title = f"Add Demerit"
    reason: discord.ui.TextInput = discord.ui.TextInput(label="Reason", style=discord.TextStyle.short)
    details: discord.ui.TextInput = discord.ui.TextInput(label="Details", style=discord.TextStyle.paragraph)


    async def on_submit(self, interaction: discord.Interaction, /) -> None:
        demerit: Demerit = Demerit(interaction.id, self._user.id, self._author.id, interaction.created_at, self.reason.value, self.details.value)
        await self._manager.post(demerit)
        embed: discord.Embed = as_embed(demerit, self._user, self._author)
        await interaction.response.send_message(embed=embed)