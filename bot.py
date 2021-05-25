import os
import asyncio
import logging
import itertools
from typing import Optional
from discord import Client, Game, Status, RawReactionActionEvent, Message, NotFound, Emoji
from discord.abc import GuildChannel
from . import env
from .game import Server
from .i18n import tr

log = logging.getLogger()


class Bot(Client):
    token = env.Var('CB_DISCORD_TOKEN', type=str,
                    help="Discord bot token",
                    optional=False)
    channel_id = env.Var('CB_DISCORD_CHANNEL_ID', type=int,
                         help="Id of the Discord text channel the bot is to send messages in",
                         optional=False)
    delete_reaction = env.Var('CB_DISCORD_DELETE_REACTION', type=str,
                              help="The reaction emoji for deleting the Discord bot's messages\n"
                                   "This should either be a unicode character or a :name: code for custom emojis.\n"
                                   "(see https://discordpy.readthedocs.io/en/stable/faq.html#how-can-i-add-a-reaction-to-a-message)",
                              optional=True, default="❌")

    def __init__(self, server: Server, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.server: Server = server

    def find_emoji(self, name: str) -> Optional[Emoji]:
        if name.startswith(':') and name.endswith(':'):
            name = name[1:-1]
        all_emojis = itertools.chain(iter(self.emojis), iter(self.channel.guild.emojis))
        return next((e for e in all_emojis if e.name == name), None)

    async def on_ready(self):
        log.info('Bot ready: %s', self.user.name)
        self.channel: GuildChannel = self.get_channel(self.channel_id)
        self.delete_reaction: Emoji = self.find_emoji(self.delete_reaction)

        game_name = tr("{game} ({modpack})", game=self.server.game, modpack=self.server.modpack)
        await self.change_presence(activity=Game(name=game_name))

    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        if payload.user_id == self.user.id:
            return
        try:
            message: Message = await self.channel.fetch_message(payload.message_id)
            if message.author == self.user and payload.emoji == self.delete_reaction:
                await message.delete()
        except NotFound:
            pass

    def run(self, **kwargs):
        super().run(self.token, **kwargs)

    async def message(self, content: str, **kwargs) -> Message:
        log.info(content)
        msg = await self.channel.send(content=content, **kwargs)
        for reaction in [self.delete_reaction]:
            await msg.add_reaction(reaction)
        return msg

    async def on_server_done(self, exitcode: int, stderr: str):
        await self.change_presence(activity=None)
        if exitcode == 0:
            log.info("Server done")
        else:
            log.error("Server crashed")
            await self.message(tr("Server crashed! (exit code: {exitcode})", exitcode=exitcode))
            log.error("Server stderr: %s", stderr)
            await self.message(stderr)
