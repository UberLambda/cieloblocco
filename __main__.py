import sys
import logging
import asyncio
import threading
from datetime import datetime
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

    env.load_from_args()

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
            msg_intro = tr("Backing up saves: {save}", save=server.save_folder.name)
            msg = await bot.message(msg_intro)

            backup_done = asyncio.Event()
            last_edit_time = datetime.now()

            def on_progress(progress):
                nonlocal last_edit_time
                now = datetime.now()
                if (now - last_edit_time).seconds >= 2:
                    asyncio.ensure_future(msg.edit(content=f'{msg_intro}\n{progress}'), loop=bot.loop)
                    last_edit_time = now

            def backup_saves():
                zip_path = server.backup_saves(on_progress=on_progress)
                gdrive.upload_file(zip_path, zip_path.name, on_progress=on_progress)
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

except SystemExit:
    raise

except:
    log.exception("Exception caught, exiting")
    sys.exit(1)
