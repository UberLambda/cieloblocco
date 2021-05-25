import os
import asyncio
import logging
import zipfile
import tempfile
from pathlib import Path
from typing import Optional, Tuple
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
    save_folder = env.Var('CB_GAME_SAVE_FOLDER', type=Path,
                          help="The folder where the game saves its data / worlds in (absolute)",
                          optional=True,
                          default=Path("world"))
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

    async def run(self) -> Tuple[int, str]:
        startup_script = str(self.server_path / self.startup_script)
        cmd = f'{startup_script} {self.startup_args}'

        log.info("Launching %s", cmd)
        self.process = await asyncio.create_subprocess_shell(
            cmd,
            cwd=self.server_path,
            stdin=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

        exitcode = await self.process.wait()
        stderr = await self.process.stderr.read()
        return exitcode, stderr.decode()

    @property
    def stdin(self) -> Optional[asyncio.StreamWriter]:
        return self.process.stdin if self.process else None

    async def stop(self, kill_timeout: Optional[float] = 60):
        # TODO: User-configurable input?
        self.process.stdin.write(b'/stop\n')
        try:
            await asyncio.wait_for(self.process.wait(), timeout=kill_timeout)
        except asyncio.TimeoutError:
            log.error("Server failed to stop in time, killing it")
            self.process.kill()

    def backup_saves(self, format: str = 'zip') -> Path:
        base_name = self.save_folder.name
        in_dir = self.server_path / self.save_folder
        out_path = Path(tempfile.gettempdir()) / f'{base_name}.zip'

        with zipfile.ZipFile(out_path, mode='w') as zipf:
            for root, dirnames, filenames in os.walk(in_dir):
                rel_root = os.path.relpath(root, in_dir)
                for f in filenames:
                    zipf.write(Path(root) / f, f'{base_name}/{rel_root}/{f}')

        return out_path
