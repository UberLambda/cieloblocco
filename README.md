# CieloBlocco
A Python daemon for managing Minecraft servers.

## Prerequisites
### Discord
Discord is used for controlling the server, and seeing its current status.  
See [the official docs](https://discord.com/developers/docs/intro).

1. Create a Discord account (or use an existing one)
2. Create a Discord application with the given account
3. Make the application into a bot (= create a bot account for the application)
4. Invite the bot to the server it will be controlled from. Bot permissions:
    - View channels
    - Read message history
    - Send messages
    - Add reactions

### Google Drive
Google Drive is used to keep copies of savefiles (usually the Minecraft world folder).

1. Create a Google account (or use an existing one)
2. From the [developer dashboard](https://console.cloud.google.com/home/dashboard):
    1. Create a new application and select it
    2. Enable the Google Drive API for the application
    3. Register a service account
    4. Generate a key for the service account and download it. **Keep the downloaded JSON safe!**
3. From Google Drive:
    1. Create a folder
        - This is called the "root folder" in the code; save files will go here
    2. Share the folder with the service account
        - Like you would with a ~~meatbag~~ person; just share it with the service account's email
        - Service account must be "Editor" (read + write permissions)
4. Wait a few minutes until Drive API is enabled - API calls will fail in the meantime!

## Example deployment (Arch/Manjaro Linux)
1. Install prerequisites:
```bash
# pacman -S sudo python python-pip python-virtualenv
```
2. Create a user exclusively for running Minecraft:
```bash
# useradd --home=/mc -m --shell=/usr/bin/nologin mc
# cd /mc
```
(optionally mount `/mc` to a dedicated BTRFS subvolume or partition)
3. Launch a shell as the new user:
```bash
# sudo -u mc $SHELL
$
```
4. Clone this repo:
```bash
$ git clone https://github.com/UberLambda/cieloblocco
$ cd cieloblocco
```
5. Create a virtualenv and install Python dependencies:
```bash
$ virtualenv venv
$ source venv/bin/activate
(venv) $ pip install -r requirements.txt
```
6. Setup a server
    1. Download a server pack (.zip) and/or installer script
    2. Unzip/install the pack somewhere in `/mc` (e.g. `/mc/mypack`)
    3. Configure `/mc/mypack/server.properties` appropriately
    4. Tweak any supplied `ServerStart.sh` script
        - Remove all infinite loops / readline calls / user interaction
        - Disable GUI (`nogui`)
        - Change Java memory flags appropriately (`-Xms`, `-Xmx`, ...)
    5. `chmod +x ServerStart.sh`
    6. (Optional) Start the server; check if everything is working
    7. (Optional) `/op <Player>` via the server's console as needed
7. Symlink the current server folder (for whatever modpack) to `/mc/current`
8. Create a /etc/cieloblocco/envfile (in Systemd `EnvironmentFile=` format)
    - Configure `key=value` environment variable pairs, as needed by CieloBlocco
    - Or: `systemctl edit cieloblocco.service` (see `(9)`), and add environment variables in manually
    - Crucial environment variables:
        - `CB_GAME_SERVER_PATH`: Path to the server (e.g. `/mc/current`)
        - `CB_GAME_STARTUP_SCRIPT`: Relative path to the startup script (e.g. `ServerStart.sh`)
        - `CB_GAME_SAVE_FOLDER`: Relative path to world / save files (e.g. `world`)
        - `CB_DISCORD_TOKEN`: Token (**secret!**) for the Discord bot
        - `CB_DISCORD_CHANNEL_ID`: Discord ID of the text channel the bot is to send messages to
        - `CB_GDRIVE_CRED`: Path to the GDrive service account key .json
        - `CB_GDRIVE_ROOT_ID`: File ID of the folder shared with the service account
        - `CB_GAME_CONTROL`: To setup rcon if needed (see the help of the `env.Var`)
9. Copy the GDrive service account key .json to /etc/cieloblocco
    - And change its owner to `mc`, since the Python script (which is run by the `mc` user) needs to access it!
10. Create a systemd unit for the service, e.g.:
```properties
[Unit]
Description=CieloBlocco server
After=network.target network-online.target nss-lookup.target

[Service]
EnvironmentFile=/etc/cieloblocco/envfile
RuntimeDirectory=/mc
Exec=/mc/cieloblocco/venv/bin/python -m cieloblocco
User=mc
Group=mc

ProtectSystem=on
ProtectHome=on

[Install]
WantedBy=multi-user.target
```
11. Start the server:
```bash
# systemctl enable cieloblocco
```
- Or `systemctl enable --now cieloblocco` to make the server start with the (virtual) machine
- The bot should now connect to the Discord channel; click on the "Server running" message's reaction to stop the server. The world is zipped and copied to GDrive immediately after the server is stopped.
