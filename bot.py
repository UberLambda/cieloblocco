import os
import asyncio
import logging
from discord import Client, Game, Status
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

    def __init__(self, server: Server, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.server: Server = server

    def run(self, **kwargs):
        super().run(self.token, **kwargs)

    async def on_ready(self):
        log.info('Bot ready: %s', self.user.name)
        self.channel: GuildChannel = self.get_channel(self.channel_id)

        game_name = tr("{game} ({modpack})", game=self.server.game, modpack=self.server.modpack)
        await self.change_presence(activity=Game(name=game_name))

    async def tick(self):
        while not self.is_closed():
            await asyncio.sleep(1.0)
            print('tick')
