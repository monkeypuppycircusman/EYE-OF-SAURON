================================================================================
  EYE OF SAURON - DISCORD BOT FOR ARK: SURVIVAL ASCENDED
  Version 2.0 - December 2025
================================================================================

OVERVIEW
--------
All-in-one Discord bot for managing ARK: Survival Ascended servers with:
- RCON server control and management
- Leveling system with XP and role rewards
- Giveaway system with slash commands
- Ticket system for support requests
- Poll creation with reactions
- Word filter with automatic moderation
- Cross-chat between Discord and game server
- Automatic Configuration UI launcher

QUICK START
-----------
1. Install dependencies:
   pip install discord.py python-dotenv mcrcon ttkbootstrap

2. Configure your Discord token in .env file:
   DISCORD_TOKEN=your_token_here

3. Run the bot:
   python EOSDiscordbot.py

   The Configuration UI will open automatically!

CONFIGURATION FILES
-------------------
Essential Files:
- EOSDiscordbot.py          Main bot script
- config_ui.py              Graphical configuration interface
- .env                      Discord bot token (KEEP SECRET!)
- servers.json              Server RCON configs and bot settings
- forbidden_words.json      Word filter list
- moderated_channels.json   Channels with active moderation
- bot_data.json             Runtime data (XP, giveaways, polls)

Templates:
- .env.example              Template for .env file
- servers.json.example      Template for servers.json

FEATURES
--------
RCON Server Management:
  !serverstatus              Check if server is online
  !playerlist                List online players
  !kick <player>             Kick a player
  !ban <player>              Ban a player
  !say <message>             Send message to game chat
  !broadcast <message>       Broadcast to all players
  !destroydinos              Respawn all wild dinos

Leveling System:
  !rank [user]               Check rank and XP
  !leaderboard [top]         View top ranked users
  - Users gain XP from chatting
  - Auto role rewards at levels 5, 10, 20

Giveaways (Slash Commands):
  /gstart                    Start a giveaway
  /gend <id>                 End a giveaway early
  /greroll <id>              Reroll winner
  /glist                     List active giveaways

Moderation:
  !mute <user> <minutes>     Timeout a user
  !unmute <user>             Remove timeout
  !addforbidden <word>       Add forbidden word
  !removeforbidden <word>    Remove forbidden word
  !listforbidden             List all forbidden words

Support:
  !ticket [subject]          Open a support ticket
  !close                     Close ticket (staff only)

Polls:
  !poll "question" opt1 opt2 Create a poll with reactions
  !pollresults <id>          View poll results

CONFIGURATION UI
----------------
The bot automatically launches a graphical interface where you can:
- Add/edit/remove server configurations
- Manage forbidden words
- Configure moderated channels
- Set bot preferences and XP settings
- Configure role rewards

All changes save automatically to the JSON files.

DISCORD SETUP
-------------
1. Go to https://discord.com/developers/applications
2. Create a new application
3. Add a Bot and copy the token
4. Enable these intents:
   - Server Members Intent
   - Message Content Intent
5. Invite bot to your server with proper permissions

RCON SETUP
----------
1. In servers.json, configure your ARK server:
   - RCON_HOST: Your server IP
   - RCON_PORT: RCON port (usually 27020)
   - RCON_PASSWORD: Your RCON password

2. Ensure RCON is enabled on your ARK server

TROUBLESHOOTING
---------------
Bot won't start:
- Check .env file has valid DISCORD_TOKEN
- Ensure all dependencies installed: pip install -r requirements.txt

RCON commands fail:
- Verify RCON credentials in servers.json
- Check firewall isn't blocking RCON port
- Ensure ARK server has RCON enabled

Configuration UI won't open:
- Install ttkbootstrap: pip install ttkbootstrap
- Check Python version is 3.8 or higher

Bot can't see messages:
- Enable Message Content Intent in Discord Developer Portal
- Check bot has proper permissions in your Discord server

IMPORTANT NOTES
---------------
- Keep your .env file SECRET - never share your bot token
- The bot requires admin permissions to moderate users
- Cross-chat only works if RCON is properly configured
- Backup your configuration files before making major changes

FILE STRUCTURE
--------------
DISCORDBOT/
├── EOSDiscordbot.py           Main bot script
├── config_ui.py               Configuration UI
├── .env                       Bot token (secret!)
├── .env.example               Token template
├── servers.json               Configuration
├── servers.json.example       Config template
├── forbidden_words.json       Word filter
├── moderated_channels.json    Moderation settings
├── bot_data.json              Runtime data
├── requirements.txt           Dependencies
├── SETUP_INSTRUCTIONS.md      Detailed setup guide
├── README.txt                 This file
└── venv/                      Virtual environment

SUPPORT & DOCUMENTATION
-----------------------
For detailed setup instructions, see SETUP_INSTRUCTIONS.md

Discord.py Documentation: https://discordpy.readthedocs.io/
Discord Developer Portal: https://discord.com/developers/applications

================================================================================
  BOT READY! Run: python EOSDiscordbot.py
================================================================================
