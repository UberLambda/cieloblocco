import sys
import logging
import asyncio
import threading
from pathlib import Path

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

try:
    import cieloblocco.env as env
    from cieloblocco.i18n import tr
    from cieloblocco.game import Server
    from cieloblocco.gdrive import GDrive
    from cieloblocco.bot import Bot

    gdrive = GDrive()
    server = Server()
    bot = Bot(server=server)

    async def main():
        await bot.is_ready.wait()

        exitcode, stderr = 9999, "<internal error>"
        try:
            server_future = asyncio.ensure_future(server.run())
            await bot.on_server_started(server)
            exitcode, stderr = await server_future
        finally:
            await bot.on_server_done(exitcode, stderr)

        if exitcode == 0:
            msg = await bot.message(tr("Backing up saves: {save}", save=server.save_folder.name))

            backup_done = asyncio.Event()

            def backup_saves():
                zip_path = server.backup_saves()
                gdrive.upload_file(zip_path, zip_path.name)
                backup_done.set()

            backup_thread = threading.Thread(target=backup_saves)
            backup_thread.start()
            await backup_done.wait()
            backup_thread.join()

            await msg.edit(content=tr("Done backing up: {save}", save=server.save_folder.name))
            await msg.add_reaction(bot.delete_reaction)

        await bot.close()

    bot.loop.create_task(main())
    bot.run()
except:
    log.exception("Exception caught, exiting")
    sys.exit(1)
