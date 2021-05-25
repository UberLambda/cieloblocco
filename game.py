import os
import asyncio
import logging
from pathlib import Path
from typing import Optional
from . import env

log = logging.getLogger()


class Server:
    server_path = env.Var('CB_GAME_SERVER_PATH', type=Path,
                          help="The directory containing the Minecraft server (or a symlink to it)",
                          optional=False)
    startup_script = env.Var('CB_GAME_STARTUP_SCRIPT', type=Path,
                             help="Path to the script or executable used to start the server, relative to CB_SERVER_PATH.\n"
                             "Make sure that the script will immediately terminate after the server stops running!\n"
                             "(e.g. remove any blocking `readline` or `pause` calls in it)",
                             optional=True,
                             default="ServerStart.sh" if os.name != 'nt' else "ServerStart.bat")
    startup_args = env.Var('CB_GAME_STARTUP_ARGS', type=str,
                           help="Any arguments to be passed to the server startup script",
                           optional=True,
                           default="")
    game = env.Var('CB_GAME_NAME', type=str,
                   help="The name of the game the server is for",
                   optional=True,
                   default="Minecraft")

    def __init__(self):
        self.process: Optional[asyncio.Process] = None

    @property
    def modpack(self) -> str:
        # TODO: Proper modpack name detection!
        return self.server_path.resolve().name

    async def run(self) -> int:
        startup_script = str(self.server_path / self.startup_script)
        cmd = f'{startup_script} {self.startup_args}'

        log.info("Launching %s", cmd)
        self.process = await asyncio.create_subprocess_shell(cmd, stdin=asyncio.subprocess.PIPE)
        return await self.process.wait()

    @property
    def stdin(self) -> Optional[asyncio.StreamWriter]:
        return self.process.stdin if self.process else None
