import sys
import logging
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
        await bot.wait_until_ready()
        exitcode, stderr = await server.run()
        await bot.on_server_done(exitcode, stderr)

    bot.loop.create_task(main())
    bot.run()
except:
    log.exception("Exception caught, exiting")
    sys.exit(1)
