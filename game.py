import os
import re
import asyncio
import struct
import logging
import zipfile
import tempfile
from collections import namedtuple
from pathlib import Path
from typing import Optional, Tuple
from . import env

log = logging.getLogger()


class Control:
    def __init__(self, server: 'Server'):
        self.server = server

    async def init(self):
        pass

    async def stop(self):
        raise NotImplementedError()


class StdinControl(Control):
    async def stop(self):
        log.debug("Typing stop command")
        self.server.stdin.write(self.server.stop_command.encode())
        self.server.stdin.write(b'\n')


class RconPacket(namedtuple('RconPacket', 'id type body')):
    # See: https://developer.valvesoftware.com/wiki/Source_RCON_Protocol
    SERVERDATA_AUTH = 3
    SERVERDATA_AUTH_RESPONSE = 2
    SERVERDATA_EXECCOMMAND = 2
    SERVERDATA_RESPONSE_VALUE = 0

    MIN_SIZE = 4 * 3 + 1 + 1

    def encode(self) -> bytes:
        data = struct.pack('<ll', self.id, self.type)
        data += self.body.encode('ascii')
        data += b'\0\0'
        size = struct.pack('<l', len(data))
        return size + data

    @staticmethod
    def decode(data: bytes) -> 'RconPacket':
        assert len(data) >= RconPacket.MIN_SIZE, "Packet is too short"
        size = struct.unpack('<l', data[:4])[0]
        assert len(data[4:]) == size, "Mismatched packet size"

        assert data.endswith(b'\0\0'), "Malformed packet"

        id, type = struct.unpack('<ll', data[4:12])
        body = data[12:-2].decode('ascii')
        return RconPacket(id=id, type=type, body=body)

    @staticmethod
    async def async_read(stream: asyncio.StreamReader) -> 'RconPacket':
        # End of body string + empty string = end of packet
        raw_resp = b''
        while len(raw_resp) < RconPacket.MIN_SIZE or not raw_resp.endswith(b'\0\0'):
            if read := await stream.read(1):
                raw_resp += read
            else:
                # Let other coroutines run while we wait for auth
                await asyncio.sleep(1)

        return RconPacket.decode(raw_resp)


class RconControl(Control):
    async def _request(self, **kwargs) -> RconPacket:
        req = RconPacket(**kwargs)
        self.tx.write(req.encode())
        return await RconPacket.async_read(self.rx)

    async def init(self, host: str = 'localhost', port: int = 25575, password: str = ''):
        log.debug("Connecting to rcon on %s:%d", host, port)
        while True:
            try:
                self.rx, self.tx = await asyncio.open_connection(host=host, port=int(port))
            except (OSError, ConnectionError, ConnectionRefusedError):
                # Let other coroutines run while we wait for RCON
                await asyncio.sleep(1)
                continue
            else:
                break

        log.debug("Authenticating to rcon server")
        req_id = 0x42
        auth_resp = await self._request(id=req_id, type=RconPacket.SERVERDATA_AUTH, body=password)
        if auth_resp.type != RconPacket.SERVERDATA_AUTH_RESPONSE or auth_resp.id != req_id:
            raise RuntimeError("Rcon authentication failed")

        log.debug("Authenticated")

    async def stop(self):
        log.debug("Stopping server via rcon")
        resp = await self._request(id=1, type=RconPacket.SERVERDATA_EXECCOMMAND, body=self.server.stop_command)
        log.debug("[rcon] %s", resp.body)


control_types = {
    'stdin': StdinControl,
    'rcon': RconControl,
}


async def make_control(config: str, server: 'Server') -> Control:
    name, *args = config.split(maxsplit=1)
    args = args[0] if args else ''

    try:
        control_type = control_types[name]
    except KeyError as err:
        raise RuntimeError("Unknown control type") from err

    control = control_type(server)
    kwargs = {key: value1 or value2
              for key, value1, value2 in re.findall(r"(\w+)=(?:'([^']*)'|([^\s]*))", args)}
    await control.init(**kwargs)

    return control


class Server:
    game = env.Var('CB_GAME_NAME', type=str,
                   help="The name of the game the server is for",
                   optional=True,
                   default="Minecraft")
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
    stop_command = env.Var('CB_GAME_STOP_COMMAND', type=str,
                           help="The console command to stop the server",
                           optional=True,
                           default='/stop')
    control_config = env.Var('CB_GAME_CONTROL', type=str,
                             help="The type of server control\n"
                             "`stdin`: pass commands directly to standard input\n"
                             "`rcon <host=host> <port=port> <password='password'>`: Source/Minecraft rcon protocol\n",
                             optional=True,
                             default='stdin')

    def __init__(self):
        self.process: Optional[asyncio.Process] = None
        self.control: Optional[Control] = None

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

        self.control = await make_control(server=self, config=self.control_config)

        exitcode = await self.process.wait()
        stderr = await self.process.stderr.read()
        return exitcode, stderr.decode()

    @property
    def stdin(self) -> Optional[asyncio.StreamWriter]:
        return self.process.stdin if self.process else None

    async def stop(self, kill_timeout: Optional[float] = 60):
        await self.control.stop()
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
