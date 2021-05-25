import sys
import logging
import asyncio
from pathlib import Path

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

try:
    import cieloblocco.env as env
    from cieloblocco.game import Server
    from cieloblocco.gdrive import GDrive
    from cieloblocco.bot import Bot

    gdrive = GDrive()
    server = Server()
    bot = Bot(server=server)

    async def main():
        await bot.is_ready.wait()

        exitcode, stderr = None, "<internal error>"
        try:
            server_future = asyncio.ensure_future(server.run())
            await bot.on_server_started(server)
            exitcode, stderr = await server_future
        finally:
            await bot.on_server_done(exitcode, stderr)
            await bot.close()

    bot.loop.create_task(main())
    bot.run()
except:
    log.exception("Exception caught, exiting")
    sys.exit(1)
