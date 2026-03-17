# All-in-one Discord bot: Leveling, Ticketing, Polls, Giveaways
# Requires: python -m pip install discord.py
# Notes:
# - Configure the SETTINGS section.
# - This uses simple JSON persistence; replace with a real database for production.
# - Intents must be enabled in your Discord application (Server Members, Message Content).

import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import random
import json
import time
import os
import re
import io
from typing import Dict, List, Optional, Any
import datetime
import threading
import subprocess
import sys
from pathlib import Path

# Import for RCON functionality
from mcrcon import MCRcon
from dotenv import load_dotenv

# --- PATHS ---
# Define the absolute path to the script's directory to ensure it finds its files
SCRIPT_DIR = Path(__file__).parent

# Load environment variables from .env file in the script's directory
load_dotenv(dotenv_path=SCRIPT_DIR / ".env")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Define absolute paths for all data files
DATA_FILE = SCRIPT_DIR / "bot_data.json"
FORBIDDEN_WORDS_FILE = SCRIPT_DIR / "forbidden_words.json"
MODERATED_CHANNELS_FILE = SCRIPT_DIR / "moderated_channels.json"
SERVER_CONFIG_FILE = SCRIPT_DIR / "servers.json"

# --- GLOBALS ---
# Global variable to store server configurations
server_configs: Dict[str, Dict[str, Any]] = {}
bot_settings: Dict[str, Any] = {} # New global for general bot settings
state: Dict[str, Any] = {} # New global for bot state persistence

# -----------------------------
# SETTINGS (These will now be loaded from servers.json)
# -----------------------------
# COMMAND_PREFIX = "!" # Loaded from bot_settings



def load_forbidden_words():
    """Load forbidden words from separate JSON file"""
    if os.path.exists(FORBIDDEN_WORDS_FILE):
        try:
            with open(FORBIDDEN_WORDS_FILE, "r", encoding="utf-8") as f:
                words = json.load(f)
                return set(words) if isinstance(words, list) else set()
        except Exception as e:
            print(f"Error loading forbidden words: {e}")
            return set(["nigger", "nigga", "fuck", "bitch", "cunt", "asshole"])
    else:
        # Create default forbidden words file
        default_words = ["nigger", "nigga", "fuck", "bitch", "cunt", "asshole"]
        try:
            with open(FORBIDDEN_WORDS_FILE, "w", encoding="utf-8") as f:
                json.dump(default_words, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error creating forbidden words file: {e}")
        return set(default_words)

def save_forbidden_words():
    """Save forbidden words to separate JSON file"""
    try:
        with open(FORBIDDEN_WORDS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(state["forbidden_words"]), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving forbidden words: {e}")

def load_moderated_channels():
    """Load moderated channels from separate JSON file"""
    if os.path.exists(MODERATED_CHANNELS_FILE):
        try:
            with open(MODERATED_CHANNELS_FILE, "r", encoding="utf-8") as f:
                channels = json.load(f)
                return set(map(int, channels)) if isinstance(channels, list) else set()
        except Exception as e:
            print(f"Error loading moderated channels: {e}")
            return set()
    else:
        # Create empty moderated channels file
        try:
            with open(MODERATED_CHANNELS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error creating moderated channels file: {e}")
        return set()

def save_moderated_channels():
    """Save moderated channels to separate JSON file"""
    try:
        with open(MODERATED_CHANNELS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(state["moderated_channels"]), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving moderated channels: {e}")

def load_state():
    # Initialize default state structure
    default_state = {
        "forbidden_words": set(),
        "moderated_channels": set(),
        "cooldowns": {},
        "xp": {},
        "polls": {},
        "giveaways": {},
        "giveaway_settings": {
            "emoji": "🎉",
            "color": 0xFFD700  # Gold
        }
    }

    # Load forbidden words from separate file
    default_state["forbidden_words"] = load_forbidden_words()
    # Load moderated channels from separate file
    default_state["moderated_channels"] = load_moderated_channels()

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Don't load forbidden_words or moderated_channels from bot_data.json
                # They come from their own files now
                if "forbidden_words" in data:
                    del data["forbidden_words"]
                if "moderated_channels" in data:
                    del data["moderated_channels"]
                # Merge loaded data with defaults (loaded data takes precedence)
                for key, value in default_state.items():
                    if key not in data:
                        data[key] = value
                state.update(data)
        except Exception as e:
            print(f"Error loading state: {e}")
            print("Using default state values.")
            state.update(default_state)
    else:
        # Initialize with defaults if DATA_FILE doesn't exist
        print(f"No existing {DATA_FILE} found. Creating new state with defaults.")
        state.update(default_state)

def save_state():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            # Create copy and exclude forbidden_words and moderated_channels (they have their own files)
            serializable_state = state.copy()
            if "forbidden_words" in serializable_state:
                del serializable_state["forbidden_words"]
            if "moderated_channels" in serializable_state:
                del serializable_state["moderated_channels"]
            json.dump(serializable_state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving state: {e}")

# -----------------------------
# BOT SETUP
# -----------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.reactions = True

# Function to load global bot settings and server configurations
def load_bot_settings():
    global bot_settings, server_configs
    if os.path.exists(SERVER_CONFIG_FILE):
        try:
            with open(SERVER_CONFIG_FILE, "r", encoding="utf-8") as f:
                full_config = json.load(f)
                bot_settings = full_config.get("BotSettings", {})
                server_configs = full_config.get("servers", {})
                print(f"Loaded general bot settings and server configurations from {SERVER_CONFIG_FILE}.")
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {SERVER_CONFIG_FILE}. Please check file format.")
        except Exception as e:
            print(f"An unexpected error occurred while loading global bot settings from {SERVER_CONFIG_FILE}: {e}")
    else:
        print(f"Warning: {SERVER_CONFIG_FILE} not found. Using default global bot settings.")
    
    # Apply defaults if not found in config
    bot_settings.setdefault("COMMAND_PREFIX", "!")
    bot_settings.setdefault("ADMIN_LOG_CHANNEL_ID", 0) # Default to 0 (invalid)
    bot_settings.setdefault("GAME_CHAT_CHANNEL_ID", 0) # Default to 0 (invalid)
    bot_settings.setdefault("ENABLE_RCON_CHAT_MONITORING", True) # Default to True
    bot_settings.setdefault("STAFF_ROLE_NAME", "Staff")
    bot_settings.setdefault("TICKET_CATEGORY_NAME", "Tickets")
    bot_settings.setdefault("CHAT_LOOP_SERVER_NAME", "DefaultServer")
    bot_settings.setdefault("CROSS_CHAT_ROLES", ["Game Chat", "admin", "staff", "owner"])
    bot_settings.setdefault("XP_RANGE", [5, 10])
    bot_settings.setdefault("XP_COOLDOWN_SECONDS", 60)
    bot_settings.setdefault("LEVEL_XP_BASE", 100)
    bot_settings.setdefault("DEFAULT_POLL_EMOJIS", ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"])
    bot_settings.setdefault("WORD_FILTER_TIMEOUT_MINUTES", 5)
    bot_settings.setdefault("ROLE_REWARDS", {5: "Veteran", 10: "Elite", 20: "Legend"})

# Load settings before bot initialization
load_bot_settings()

STAFF_ROLE_NAME = bot_settings.get("STAFF_ROLE_NAME", "Staff")

load_state()

bot = commands.Bot(command_prefix=bot_settings["COMMAND_PREFIX"], intents=intents, case_insensitive=True)

# -----------------------------
# CONFIG UI LAUNCHER
# -----------------------------
config_ui_process = None

def launch_config_ui():
    """Launch the config UI in a separate process"""
    global config_ui_process
    try:
        config_ui_path = os.path.join(os.path.dirname(__file__), "config_ui.py")
        if os.path.exists(config_ui_path):
            print("Launching configuration UI...")
            config_ui_process = subprocess.Popen([sys.executable, config_ui_path])
        else:
            print("Warning: config_ui.py not found. Skipping UI launch.")
    except Exception as e:
        print(f"Error launching config UI: {e}")

# -----------------------------
# UTILITIES: persistence, levels, RCON
# -----------------------------

def level_for_xp(xp: int) -> int:
    # Simple linear level curve; customize as needed
    # Example: level increases every LEVEL_XP_BASE XP
    return xp // bot_settings.get("LEVEL_XP_BASE", 100)

async def give_role_reward(member: discord.Member, level: int):
    role_name = bot_settings.get("ROLE_REWARDS", {5: "Veteran", 10: "Elite", 20: "Legend"}).get(level)
    if not role_name:
        return
    role = discord.utils.get(member.guild.roles, name=role_name)
    if role and role not in member.roles:
        await member.add_roles(role, reason=f"Level reward reached: {level}")

def can_gain_xp(user_id: int) -> bool:
    now = time.time()
    key = str(user_id)
    last = state["cooldowns"].get(key, 0)
    if now - last >= bot_settings.get("XP_COOLDOWN_SECONDS", 60):
        state["cooldowns"][key] = now
        return True
    return False

def add_xp(user_id: int, amount: int) -> int:
    key = str(user_id)
    current = int(state["xp"].get(key, 0))
    new_xp = current + amount
    state["xp"][key] = new_xp
    save_state()
    return new_xp

# Helper functions to check for admin/owner/staff roles
def is_admin_or_owner(member):
    """Check if member has admin, owner, or staff role (for prefix commands)"""
    admin_roles = ["owner", "admin", "staff"]
    return any(role.name.lower() in admin_roles for role in member.roles)

def has_staff_permission(user) -> bool:
    """Check if user has admin, owner, or staff role (for slash commands)"""
    staff_roles = ["OWNER", "ADMIN", "Staff", "owner", "admin", "staff"]
    return any(role.name in staff_roles for role in user.roles)

async def send_rcon_command(ctx, command_str, server_name: Optional[str] = None) -> Optional[str]:
    if not is_admin_or_owner(ctx.author):
        await ctx.send("You do not have permission to use this command.")
        return None

    admin_log_channel = bot.get_channel(bot_settings.get("ADMIN_LOG_CHANNEL_ID", 0))

    # Get server configuration - use CHAT_LOOP_SERVER_NAME from settings if no server specified
    default_server = bot_settings.get("CHAT_LOOP_SERVER_NAME", "DefaultServer")
    target_server_name = server_name if server_name else default_server
    server_config = server_configs.get(target_server_name)

    if not server_config:
        error_msg = f"Server '{target_server_name}' not found in configuration."
        await ctx.send(error_msg)
        if admin_log_channel:
            await admin_log_channel.send(f"**Error:** {ctx.author.mention} attempted RCON command `{command_str}` but {error_msg}")
        return None

    RCON_HOST = server_config.get("RCON_HOST")
    RCON_PORT = server_config.get("RCON_PORT")
    RCON_PASSWORD = server_config.get("RCON_PASSWORD")

    if not RCON_HOST or not RCON_PASSWORD or not RCON_PORT:
        error_msg = f"Incomplete RCON configuration for server '{target_server_name}'. Please ensure Host, Port, and Password are set."
        await ctx.send(error_msg)
        if admin_log_channel:
            await admin_log_channel.send(f"**Error:** {ctx.author.mention} attempted RCON command `{command_str}` but {error_msg}")
        return None

    if admin_log_channel:
        await admin_log_channel.send(f"Admin command attempted by {ctx.author.mention} for server '{target_server_name}': `{command_str}`")

    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, RCON_PORT) as mcr:
            resp = mcr.command(command_str)
            if admin_log_channel:
                await admin_log_channel.send(f"Admin command `{command_str}` executed successfully by {ctx.author.mention} on server '{target_server_name}'.\n**Response:**\n```\n{resp}\n```")
            return resp
    except Exception as e:
        await ctx.send(f"Error connecting to RCON for server '{target_server_name}': {e}")
        if admin_log_channel:
            await admin_log_channel.send(f"**Error:** An error occurred while executing admin command `{command_str}` by {ctx.author.mention} on server '{target_server_name}': {e}")
        return None

# -----------------------------
# EVENTS: Leveling on messages, Welcome Message
# -----------------------------
@bot.event
async def on_ready():
    global server_configs
    load_state()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")

    print("Bot is ready.")

    if os.path.exists(SERVER_CONFIG_FILE):
        try:
            with open(SERVER_CONFIG_FILE, "r", encoding="utf-8") as f:
                server_configs = json.load(f).get("servers", {})
                print(f"Loaded {len(server_configs)} server configurations from {SERVER_CONFIG_FILE}.")
                if not server_configs:
                    print("Warning: servers.json loaded, but no server configurations found under 'servers' key.")
        except FileNotFoundError:
            print(f"Warning: {SERVER_CONFIG_FILE} not found. RCON commands for multiple servers will not function.")
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {SERVER_CONFIG_FILE}. Please check file format.")
        except Exception as e:
            print(f"An unexpected error occurred while loading {SERVER_CONFIG_FILE}: {e}")
    else:
        print(f"Warning: {SERVER_CONFIG_FILE} not found. RCON commands for multiple servers will not function.")

    # Re-apply command prefix from loaded settings, if bot allows changing prefix after init
    # For now, it's set on bot initialization
    # bot.command_prefix = bot_settings["COMMAND_PREFIX"] 

    if bot_settings.get("ENABLE_RCON_CHAT_MONITORING", True): # Default to True if not in settings
        rcon_chat_loop.start()
        print("RCON chat monitoring enabled.")
    else:
        print("RCON chat monitoring disabled. Set ENABLE_RCON_CHAT_MONITORING = True to enable.")

    # Launch configuration UI
    launch_config_ui()

def cleanup_config_ui():
    """Clean up the config UI process on bot shutdown"""
    global config_ui_process
    if config_ui_process:
        try:
            config_ui_process.terminate()
            config_ui_process.wait(timeout=5)
            print("Configuration UI closed.")
        except Exception as e:
            print(f"Error closing config UI: {e}")

@bot.event
async def on_member_join(member):
    """Sends a welcome message to a specific channel when a new member joins."""
    welcome_channel_name = "welcome" 
    welcome_channel = discord.utils.get(member.guild.channels, name=welcome_channel_name)
    
    if welcome_channel:
        await welcome_channel.send(f"Welcome to LitGaming, {member.mention}! Enjoy your stay!")
    else:
        print(f"Warning: Welcome channel '{welcome_channel_name}' not found.")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    # Word Filter
    if message.guild and not message.author.bot:
        # Check if author is immune (admin, staff, owner)
        if any(role.name.lower() in ["owner", "admin", "staff"] for role in message.author.roles):
            pass # Immune, skip word filter
        else:
            message_content_lower = message.content.lower()
            found_forbidden_word = None
            for word in state["forbidden_words"]:
                if word.lower() in message_content_lower:
                    # Simple check for whole words, avoids partial matches like "ass" in "glass"
                    # This regex ensures we match whole words and accounts for punctuation
                    if re.search(r'\b' + re.escape(word.lower()) + r'\b', message_content_lower):
                        found_forbidden_word = word
                        break
            
            if found_forbidden_word:
                admin_log_channel = bot.get_channel(bot_settings.get("ADMIN_LOG_CHANNEL_ID", 0))
                try:
                    # Timeout the user
                    timeout_duration = datetime.timedelta(minutes=bot_settings.get("WORD_FILTER_TIMEOUT_MINUTES", 5))
                    await message.author.timeout(timeout_duration, reason=f"Used forbidden word: '{found_forbidden_word}'")
                    
                    # Delete the message
                    await message.delete()
                    
                    # Notify in public channel and log to admin channel
                    await message.channel.send(f"{message.author.mention} has been timed out for {bot_settings.get("WORD_FILTER_TIMEOUT_MINUTES", 5)} minutes for using forbidden language.")
                    if admin_log_channel:
                        await admin_log_channel.send(
                            f"**Moderation Action:** {message.author.mention} timed out for {bot_settings.get("WORD_FILTER_TIMEOUT_MINUTES", 5)} minutes "
                            f"for using forbidden word: `{found_forbidden_word}` in channel {message.channel.mention}. "
                            f"Message deleted: `{message.content}`"
                        )
                    return # Stop further processing for this message
                except discord.Forbidden:
                    if admin_log_channel:
                        await admin_log_channel.send(f"**Error:** Bot lacks permissions to timeout {message.author.mention} or delete messages in {message.channel.mention}.")
                    print(f"Error: Bot lacks permissions to timeout {message.author.mention} or delete messages.")
                except Exception as e:
                    if admin_log_channel:
                        await admin_log_channel.send(f"**Error:** An unexpected error occurred during word filter for {message.author.mention}: {e}")
                    print(f"An unexpected error occurred during word filter: {e}")

    # Cross-chat: Discord to Game
    if message.channel.id == bot_settings.get("GAME_CHAT_CHANNEL_ID", 0) and not message.author.bot:
        # Check if user has any of the allowed roles (case-insensitive)
        user_role_names = [role.name.lower() for role in message.author.roles]
        allowed_roles_lower = [role.lower() for role in bot_settings.get("CROSS_CHAT_ROLES", ["Game Chat", "admin", "staff", "owner"])]
        has_permission = any(role in allowed_roles_lower for role in user_role_names)

        if not has_permission:
            # User doesn't have permission, silently skip cross-chat
            # (Still allow XP gain and other processing below)
            pass
        else:
            # User has permission, send to game
            full_message = f"[Discord] {message.author.display_name}: {message.content}"

            server_config = server_configs.get("DefaultServer")
            if not server_config:
                print("Warning: DefaultServer RCON configuration not found for cross-chat.")
            else:
                RCON_HOST_CHAT = server_config.get("RCON_HOST")
                RCON_PORT_CHAT = server_config.get("RCON_PORT")
                RCON_PASSWORD_CHAT = server_config.get("RCON_PASSWORD")

                if not RCON_HOST_CHAT or not RCON_PASSWORD_CHAT or not RCON_PORT_CHAT:
                    print("Warning: Incomplete RCON configuration for DefaultServer for cross-chat.")
                else:
                    try:
                        with MCRcon(RCON_HOST_CHAT, RCON_PASSWORD_CHAT, RCON_PORT_CHAT) as mcr:
                            mcr.command(f"ServerChat {full_message}")
                        # Optionally, delete the Discord message to prevent it from showing up twice
                        # Or add a reaction to confirm it was sent
                    except Exception as e:
                        print(f"Error sending Discord message to game via RCON for DefaultServer: {e}")
        # Even if RCON fails, still process other commands for the message if applicable
        # return # Only uncomment this if you want messages in the chat channel to ONLY go to RCON

    # XP gain with cooldown
    if can_gain_xp(message.author.id):
        xp_gain = random.randint(*tuple(bot_settings.get("XP_RANGE", [5, 10])))
        new_xp = add_xp(message.author.id, xp_gain)
        new_level = level_for_xp(new_xp)
        old_level = level_for_xp(new_xp - xp_gain)

        if new_level > old_level:
            try:
                await give_role_reward(message.author, new_level)
            except discord.Forbidden:
                pass  # Missing permissions; ignore
            await message.channel.send(
                f"{message.author.mention} leveled up to Level {new_level}! (+{xp_gain} XP)"
            )

    await bot.process_commands(message)

@tasks.loop(seconds=10) # Poll game chat every 10 seconds
async def rcon_chat_loop():
    """
    Monitors ASA game server chat and relays it to Discord.

    IMPORTANT: This feature is DISABLED by default (ENABLE_RCON_CHAT_MONITORING = False)

    To enable this feature:
    1. Set ENABLE_RCON_CHAT_MONITORING = True in settings
    2. Ensure your servers.json has correct RCON credentials
    3. The bot will use 'GetChat' command (works for ARK: Survival Ascended)

    Messages are filtered to exclude system notifications (tribe tames, kills, etc.)
    Only player chat messages are relayed to Discord.
    """
    await bot.wait_until_ready()

    server_config = server_configs.get(bot_settings.get("CHAT_LOOP_SERVER_NAME", "DefaultServer"))
    if not server_config:
        print(f"Warning: RCON chat loop server '{bot_settings.get("CHAT_LOOP_SERVER_NAME", "DefaultServer")}' not found in configuration.")
        rcon_chat_loop.cancel()  # Stop the loop if misconfigured
        return

    RCON_HOST_LOOP = server_config.get("RCON_HOST")
    RCON_PORT_LOOP = server_config.get("RCON_PORT")
    RCON_PASSWORD_LOOP = server_config.get("RCON_PASSWORD")
    GAME_CHAT_CHANNEL_ID_LOOP = server_config.get("GAME_CHAT_CHANNEL_ID", bot_settings.get("GAME_CHAT_CHANNEL_ID", 0))

    if not RCON_HOST_LOOP or not RCON_PASSWORD_LOOP or not RCON_PORT_LOOP:
        print(f"Warning: Incomplete RCON configuration for RCON chat loop server '{bot_settings.get("CHAT_LOOP_SERVER_NAME", "DefaultServer")}'.")
        rcon_chat_loop.cancel()  # Stop the loop if misconfigured
        return

    channel = bot.get_channel(GAME_CHAT_CHANNEL_ID_LOOP)
    if not channel:
        print(f"Warning: Game chat channel with ID {GAME_CHAT_CHANNEL_ID_LOOP} for server '{bot_settings.get("CHAT_LOOP_SERVER_NAME", "DefaultServer")}' not found.")
        rcon_chat_loop.cancel()  # Stop the loop if misconfigured
        return

    try:
        # Run RCON operation in thread pool to avoid blocking Discord heartbeat
        def get_rcon_chat():
            try:
                with MCRcon(RCON_HOST_LOOP, RCON_PASSWORD_LOOP, RCON_PORT_LOOP, timeout=5) as mcr:
                    return mcr.command("GetChat")
            except Exception as e:
                return None

        # Execute RCON command in separate thread with timeout
        try:
            resp = await asyncio.wait_for(
                asyncio.to_thread(get_rcon_chat),
                timeout=8.0  # Slightly longer than RCON timeout
            )
        except asyncio.TimeoutError:
            print(f"RCON chat loop timed out - skipping this iteration")
            return

        if not resp:
            return

        # ASA GetChat returns format: (PlayerName): Message
        # Filter out system messages and admin commands
        filters = [
            'Server received, But no response!!',
            'AdminCmd',
            'Tribe Tamed a',
            'Tribe ',
            'Tamed a',
            'was killed!',
            'added to the Tribe',
            'RichColor',
            'RCON: Not connected',
            'froze'
        ]

        # Only process if response is valid and not filtered
        if resp and "Server received, But no response!!" not in resp:
            # Check if any filter word is in the response
            if not any(filter_word in resp for filter_word in filters):
                # Parse the message using regex: (PlayerName): Message
                match = re.search(r"\((.+?)\): (.+)", resp)
                if match:
                    player_name = match.group(1)
                    message = match.group(2)

                    # Send to Discord channel
                    await channel.send(f"**[{player_name}]** {message}")

        # Check for "World Save Complete" messages and log to admin channel
        admin_log_channel = bot.get_channel(bot_settings.get("ADMIN_LOG_CHANNEL_ID", 0))
        if admin_log_channel and "World Save Complete" in resp:
            world_save_lines = [line for line in resp.splitlines() if "World Save Complete" in line]
            for line in world_save_lines:
                await admin_log_channel.send(f"**RCON Server Event:** World Save Detected: `{line}`")

    except Exception as e:
        print(f"Error in RCON chat loop: {e}")
        print("Tip: If this error persists, check that:")
        print("  1. RCON connection details are correct in servers.json")
        print("  2. Your server is online and RCON is enabled")
        print("  3. The 'GetChat' command is supported by your ASA server version")
        # Don't cancel the loop - it will retry on next iteration

# -----------------------------
# COMMANDS: Rank & Leaderboard (from giveaway bot)
# -----------------------------
@bot.command(name="rank")
async def rank(ctx: commands.Context, member: Optional[discord.Member] = None):
    target = member or ctx.author
    xp = int(state["xp"].get(str(target.id), 0))
    lvl = level_for_xp(xp)
    await ctx.send(f"{target.mention} | XP: {xp} | Level: {lvl}")

@bot.command(name="leaderboard", aliases=["lb"])
async def leaderboard(ctx: commands.Context, top: Optional[int] = 10):
    items = [(int(uid), int(xp)) for uid, xp in state["xp"].items()]
    items.sort(key=lambda x: x[1], reverse=True)
    top_n = items[:max(1, min(top, 25))]
    lines = []
    for i, (uid, xp) in enumerate(top_n, start=1):
        member = ctx.guild.get_member(uid)
        name = member.display_name if member else f"User {uid}"
        lvl = level_for_xp(xp)
        lines.append(f"{i}. {name} — XP: {xp}, Level: {lvl}")
    if not lines:
        await ctx.send("No leaderboard data yet.")
    else:
        await ctx.send("Leaderboard:\n" + "\n".join(lines))

# -----------------------------
# COMMANDS: RCON (integrated from old bot)
# -----------------------------
@bot.command(name="ping")
async def ping(ctx: commands.Context):
    await ctx.send("pong")

@bot.command(name="roast")
async def roast(ctx: commands.Context):
    roasts = [ # Moved roasts here for simplicity, or could put in a separate config
        "I'm not saying you're dumb, but you could hide your own Easter eggs and not find them.",
        "You're the reason the gene pool needs a lifeguard.",
        "If I had a face like yours, I'd sue my parents.",
        "I've seen more charisma in a potato.",
        "You're not the dumbest person in the world, but you better hope they don't die.",
        "I'd agree with you, but then we'd both be wrong.",
        "I'm jealous of people that don't know you.",
        "You have your entire life to be a jerk. Why not take today off?",
        "I'm not insulting you, I'm describing you.",
        "You're as useful as a screen door on a submarine.",
    ]
    await ctx.send(random.choice(roasts))

@bot.command(name="prayer")
async def prayer(ctx: commands.Context):
    blessing = f"We bless the greatest of all men, Lord {ctx.author.mention} the mightiest of all bobs"
    await ctx.send(blessing)

@bot.command(name="serverstatus")
async def serverstatus(ctx: commands.Context, server_name: Optional[str] = None):
    """Checks the status of a game server via RCON."""
    resp = await send_rcon_command(ctx, "ListPlayers", server_name=server_name)
    if resp:
        # Count players from response
        player_count = 0
        if "No Players Connected" not in resp:
            player_lines = resp.strip().split('\n')
            for line in player_lines:
                if "Players:" in line:
                    line = line.replace("Players:", "").strip()
                if line:
                    names = [name.strip() for name in line.split(',') if name.strip()]
                    player_count += len(names)

        # Send simple status message (detailed info logged to admin channel)
        await ctx.send(f"Server online - {player_count} players connected")

@bot.command(name="playerlist")
async def playerlist(ctx: commands.Context, server_name: Optional[str] = None):
    """Lists online players for a game server via RCON."""
    if not is_admin_or_owner(ctx.author):
        await ctx.send("You do not have permission to use this command.")
        return
    
    resp = await send_rcon_command(ctx, "ListPlayers", server_name=server_name)
    if resp:
        if "No Players Connected" in resp:
            await ctx.send(f"No players are currently online on server '{server_name or 'DefaultServer'}'.")
        else:
            player_lines = resp.strip().split('\n')
            players = []
            for line in player_lines:
                if "Players:" in line:
                    line = line.replace("Players:", "").strip()
                if line:
                    names = [name.strip() for name in line.split(',') if name.strip()]
                    players.extend(names)
            if players:
                await ctx.send(f"**Online Players on {server_name or 'DefaultServer'}:**\n```\n" + "\n".join(players) + "\n```")
            else:
                await ctx.send(f"Could not parse player list from server '{server_name or 'DefaultServer'}' response.")

@bot.command(name="playercount")
async def playercount(ctx: commands.Context, server_name: Optional[str] = None):
    """Gets the player count for a game server via RCON."""
    if not is_admin_or_owner(ctx.author):
        await ctx.send("You do not have permission to use this command.")
        return
    
    resp = await send_rcon_command(ctx, "ListPlayers", server_name=server_name)
    if resp:
        if "No Players Connected" in resp:
            await ctx.send(f"There are 0 players online on server '{server_name or 'DefaultServer'}'.")
        else:
            player_lines = resp.strip().split('\n')
            # Assuming "Players:" is the first line or not present, so count lines after filtering
            player_count = 0
            for line in player_lines:
                if "Players:" in line:
                    line = line.replace("Players:", "").strip()
                if line: # Count non-empty lines that are not just "Players:"
                    names = [name.strip() for name in line.split(',') if name.strip()]
                    player_count += len(names)
            
            await ctx.send(f"There are {player_count} players online on server '{server_name or 'DefaultServer'}'.")

@bot.command(name="kick")
async def kick(ctx: commands.Context, player_name: str, server_name: Optional[str] = None, *, reason: str = "No reason provided"):
    """Kicks a player from a game server via RCON."""
    await send_rcon_command(ctx, f"KickPlayer {player_name} {reason}", server_name=server_name)
    await ctx.send(f"Attempted to kick {player_name} from server '{server_name or 'DefaultServer'}'.")

@bot.command(name="ban")
async def ban(ctx: commands.Context, player_identifier: str, server_name: Optional[str] = None, *, reason: str = "No reason provided"):
    """Bans a player from a game server via RCON. Use player name or EOS ID."""
    await send_rcon_command(ctx, f"BanPlayer {player_identifier} {reason}", server_name=server_name)
    await ctx.send(f"Attempted to ban `{player_identifier}` from server '{server_name or 'DefaultServer'}'.")

@bot.command(name="unban")
async def unban(ctx: commands.Context, eos_id: str, server_name: Optional[str] = None):
    """Unbans a player from a game server via RCON. Requires EOS ID."""
    await send_rcon_command(ctx, f"UnbanPlayer {eos_id}", server_name=server_name)
    await ctx.send(f"Attempted to unban EOS ID `{eos_id}` from server '{server_name or 'DefaultServer'}'.")

@bot.command(name="whitelist")
async def whitelist(ctx: commands.Context, player_name: str, server_name: Optional[str] = None):
    """Whitelists a player on a game server via RCON."""
    await send_rcon_command(ctx, f"AllowPlayerToJoinNoCheck {player_name}", server_name=server_name)
    await ctx.send(f"Attempted to whitelist {player_name} on server '{server_name or 'DefaultServer'}'.")

@bot.command(name="blacklist")
async def blacklist(ctx: commands.Context, player_name: str, server_name: Optional[str] = None):
    """Blacklists a player on a game server via RCON."""
    await send_rcon_command(ctx, f"DisallowPlayerToJoinNoCheck {player_name}", server_name=server_name)
    await ctx.send(f"Attempted to blacklist {player_name} on server '{server_name or 'DefaultServer'}'.")

@bot.command(name="say")
async def say(ctx: commands.Context, *, message: str):
    """Sends a message to the default game server chat via RCON."""
    default_server = bot_settings.get("CHAT_LOOP_SERVER_NAME", "DefaultServer")
    await send_rcon_command(ctx, f"ServerChat {message}", server_name=None)
    await ctx.send(f"Message sent to server '{default_server}'.")

@bot.command(name="sayto")
async def sayto(ctx: commands.Context, server_name: str, *, message: str):
    """Sends a message to a specific game server chat via RCON."""
    await send_rcon_command(ctx, f"ServerChat {message}", server_name=server_name)
    await ctx.send(f"Message sent to server '{server_name}'.")

@bot.command(name="start")
@commands.has_role(STAFF_ROLE_NAME)
async def start_server(ctx: commands.Context, server_name: Optional[str] = None):
    """Starts the game server via RCON."""
    await send_rcon_command(ctx, "ServerStart", server_name=server_name)
    await ctx.send(f"Attempted to start server '{server_name or 'DefaultServer'}'.")

@bot.command(name="stop")
@commands.has_role(STAFF_ROLE_NAME)
async def stop_server(ctx: commands.Context, server_name: Optional[str] = None):
    """Stops the game server via RCON."""
    await send_rcon_command(ctx, "ServerStop", server_name=server_name)
    await ctx.send(f"Attempted to stop server '{server_name or 'DefaultServer'}'.")

@bot.command(name="restart")
@commands.has_role(STAFF_ROLE_NAME)
async def restart_server(ctx: commands.Context, server_name: Optional[str] = None):
    """Restarts the game server via RCON."""
    await send_rcon_command(ctx, "ServerRestart", server_name=server_name)
    await ctx.send(f"Attempted to restart server '{server_name or 'DefaultServer'}'.")

@bot.command(name="broadcast")
async def broadcast(ctx: commands.Context, *, message: str):
    """Broadcasts a message to all players on the default server (server-wide announcement)."""
    default_server = bot_settings.get("CHAT_LOOP_SERVER_NAME", "DefaultServer")
    await send_rcon_command(ctx, f"Broadcast {message}", server_name=None)
    await ctx.send(f"Broadcasted to server '{default_server}': `{message}`")

@bot.command(name="broadcastto")
async def broadcastto(ctx: commands.Context, server_name: str, *, message: str):
    """Broadcasts a message to all players on a specific server."""
    await send_rcon_command(ctx, f"Broadcast {message}", server_name=server_name)
    await ctx.send(f"Broadcasted to server '{server_name}': `{message}`")

@bot.command(name="addforbidden")
@commands.has_any_role("OWNER", "ADMIN", "Staff")
async def add_forbidden_word(ctx: commands.Context, *, word: str):
    """Adds a word to the forbidden words list."""
    admin_log_channel = bot.get_channel(bot_settings.get("ADMIN_LOG_CHANNEL_ID", 0))
    word_lower = word.lower()
    if word_lower in state["forbidden_words"]:
        await ctx.send(f"'{word}' is already in the forbidden words list.")
        if admin_log_channel:
            await admin_log_channel.send(f"**Moderation Action:** {ctx.author.mention} attempted to add existing forbidden word: `{word}`.")
        return

    state["forbidden_words"].add(word_lower)
    save_forbidden_words()
    # Removed public ctx.send confirmation
    if admin_log_channel:
        await admin_log_channel.send(f"**Moderation Action:** {ctx.author.mention} added forbidden word: `{word}`.")

@bot.command(name="removeforbidden")
@commands.has_any_role("OWNER", "ADMIN", "Staff")
async def remove_forbidden_word(ctx: commands.Context, *, word: str):
    """Removes a word from the forbidden words list."""
    admin_log_channel = bot.get_channel(bot_settings.get("ADMIN_LOG_CHANNEL_ID", 0))
    word_lower = word.lower()
    if word_lower not in state["forbidden_words"]:
        await ctx.send(f"'{word}' is not in the forbidden words list.")
        if admin_log_channel:
            await admin_log_channel.send(f"**Moderation Action:** {ctx.author.mention} attempted to remove non-existent forbidden word: `{word}`.")
        return

    state["forbidden_words"].remove(word_lower)
    save_forbidden_words()
    # Removed public ctx.send confirmation
    if admin_log_channel:
        await admin_log_channel.send(f"**Moderation Action:** {ctx.author.mention} removed forbidden word: `{word}`.")

@bot.command(name="listforbidden")
@commands.has_any_role("OWNER", "ADMIN", "Staff")
async def list_forbidden_words(ctx: commands.Context):
    """Lists all forbidden words."""
    if not state["forbidden_words"]:
        await ctx.send("The forbidden words list is currently empty.")
        return
    
    words_list = ", ".join(sorted(list(state["forbidden_words"])))
    await ctx.send(f"**Forbidden Words:**\n```{words_list}```")

@bot.command(name="destroydinos")
@commands.has_role(STAFF_ROLE_NAME)
async def destroydinos(ctx: commands.Context, server_name: Optional[str] = None):
    """Destroys all wild dinos on the server (forces fresh spawns)."""
    # Get actual server name being used
    target_server = server_name if server_name else bot_settings.get("CHAT_LOOP_SERVER_NAME", "DefaultServer")
    await send_rcon_command(ctx, "DestroyWildDinos", server_name=server_name)
    await ctx.send(f"Destroying all wild dinos on server '{target_server}'... This may cause lag!")

@bot.command(name="getgamelog")
@commands.has_role(STAFF_ROLE_NAME)
async def getgamelog(ctx: commands.Context, server_name: Optional[str] = None):
    """Gets the game log from the server and sends it as a file."""
    await ctx.send("Fetching game log... This may take a moment.")
    resp = await send_rcon_command(ctx, "GetGameLog", server_name=server_name)

    if resp:
        # Save log to file and send
        log_file = io.BytesIO(resp.encode('utf-8'))
        log_file.name = f"{server_name or 'DefaultServer'}_gamelog_{int(time.time())}.txt"
        await ctx.send(f"Game log from server '{server_name or 'DefaultServer'}':", file=discord.File(log_file))
    else:
        await ctx.send("Failed to retrieve game log.")

@bot.command(name="rcon")
@commands.has_role(STAFF_ROLE_NAME)
async def rcon_custom(ctx: commands.Context, command: str, server_name: Optional[str] = None):
    """Sends a custom RCON command to the server. Use with caution!"""
    resp = await send_rcon_command(ctx, command, server_name=server_name)
    if resp:
        # Truncate if too long
        if len(resp) > 1900:
            resp = resp[:1900] + "... (truncated)"
        await ctx.send(f"Response from server '{server_name or 'DefaultServer'}':\n```\n{resp}\n```")
    else:
        await ctx.send("No response or command failed.")

@bot.command(name="mute")
@commands.has_role(STAFF_ROLE_NAME)
@commands.bot_has_permissions(moderate_members=True)
async def mute(ctx: commands.Context, member: discord.Member, minutes: Optional[int] = 10, *, reason: str = "No reason provided"):
    """Mutes a member for a specified duration (default 10 minutes)."""
    if member.id == ctx.author.id:
        await ctx.send("You cannot mute yourself!")
        return
    if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        await ctx.send("You cannot mute someone with an equal or higher role than yourself.")
        return
    
    # Check if the bot can mute this member
    if member.top_role >= ctx.guild.me.top_role:
        await ctx.send("I cannot mute this member as their role is equal to or higher than mine.")
        return

    duration = datetime.timedelta(minutes=minutes)
    try:
        await member.timeout(duration, reason=reason)
        await ctx.send(f"{member.mention} has been muted for {minutes} minutes. Reason: {reason}")
        admin_log_channel = bot.get_channel(bot_settings.get("ADMIN_LOG_CHANNEL_ID", 0))
        if admin_log_channel:
            await admin_log_channel.send(f"**Discord Moderation:** {ctx.author.mention} muted {member.mention} for {minutes} minutes. Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("I do not have permissions to mute this member.")
        if admin_log_channel:
            await admin_log_channel.send(f"**Error:** Failed to mute {member.mention} by {ctx.author.mention} (missing permissions).")
    except Exception as e:
        await ctx.send(f"An error occurred while muting: {e}")
        if admin_log_channel:
            await admin_log_channel.send(f"**Error:** An error occurred while muting {member.mention} by {ctx.author.mention}: {e}")

@bot.command(name="unmute")
@commands.has_role(STAFF_ROLE_NAME)
@commands.bot_has_permissions(moderate_members=True)
async def unmute(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    """Unmutes a member."""
    if member.timed_out_until is None:
        await ctx.send(f"{member.mention} is not currently muted.")
        return

    try:
        await member.timeout(None, reason=reason) # Set timeout to None to unmute
        await ctx.send(f"{member.mention} has been unmuted. Reason: {reason}")
        admin_log_channel = bot.get_channel(bot_settings.get("ADMIN_LOG_CHANNEL_ID", 0))
        if admin_log_channel:
            await admin_log_channel.send(f"**Discord Moderation:** {ctx.author.mention} unmuted {member.mention}. Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("I do not have permissions to unmute this member.")
        if admin_log_channel:
            await admin_log_channel.send(f"**Error:** Failed to unmute {member.mention} by {ctx.author.mention} (missing permissions).")
    except Exception as e:
        await ctx.send(f"An error occurred while unmuting: {e}")
        if admin_log_channel:
            await admin_log_channel.send(f"**Error:** An error occurred while unmuting {member.mention} by {ctx.author.mention}: {e}")

@bot.command(name="deafen")
@commands.has_role(STAFF_ROLE_NAME)
@commands.bot_has_permissions(deafen_members=True)
async def deafen(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    """Deafens a member in a voice channel."""
    if member.id == ctx.author.id:
        await ctx.send("You cannot deafen yourself!")
        return
    if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        await ctx.send("You cannot deafen someone with an equal or higher role than yourself.")
        return

    if not member.voice or not member.voice.channel:
        await ctx.send(f"{member.mention} is not in a voice channel.")
        return

    if member.voice.self_deaf:
        await ctx.send(f"{member.mention} is already self-deafened.")
        return

    try:
        await member.edit(deafen=True, reason=reason)
        await ctx.send(f"{member.mention} has been deafened. Reason: {reason}")
        admin_log_channel = bot.get_channel(bot_settings.get("ADMIN_LOG_CHANNEL_ID", 0))
        if admin_log_channel:
            await admin_log_channel.send(f"**Discord Moderation:** {ctx.author.mention} deafened {member.mention}. Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("I do not have permissions to deafen this member.")
        if admin_log_channel:
            await admin_log_channel.send(f"**Error:** Failed to deafen {member.mention} by {ctx.author.mention} (missing permissions).")
    except Exception as e:
        await ctx.send(f"An error occurred while deafening: {e}")
        if admin_log_channel:
            await admin_log_channel.send(f"**Error:** An error occurred while deafening {member.mention} by {ctx.author.mention}: {e}")

@bot.command(name="undeafen")
@commands.has_role(STAFF_ROLE_NAME)
@commands.bot_has_permissions(deafen_members=True)
async def undeafen(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    """Undeafens a member in a voice channel."""
    if not member.voice or not member.voice.channel or not member.voice.deaf:
        await ctx.send(f"{member.mention} is not currently deafened or not in a voice channel.")
        return

    try:
        await member.edit(deafen=False, reason=reason)
        await ctx.send(f"{member.mention} has been undeafened. Reason: {reason}")
        admin_log_channel = bot.get_channel(bot_settings.get("ADMIN_LOG_CHANNEL_ID", 0))
        if admin_log_channel:
            await admin_log_channel.send(f"**Discord Moderation:** {ctx.author.mention} undeafened {member.mention}. Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("I do not have permissions to undeafen this member.")
        if admin_log_channel:
            await admin_log_channel.send(f"**Error:** Failed to undeafen {member.mention} by {ctx.author.mention} (missing permissions).")
    except Exception as e:
        await ctx.send(f"An error occurred while undeafening: {e}")
        if admin_log_channel:
            await admin_log_channel.send(f"**Error:** An error occurred while undeafening {member.mention} by {ctx.author.mention}: {e}")

# -----------------------------
# TICKETING: create/close tickets (from giveaway bot)
# -----------------------------
async def ensure_ticket_category(guild: discord.Guild) -> Optional[discord.CategoryChannel]:
    cat = discord.utils.get(guild.categories, name=bot_settings.get("TICKET_CATEGORY_NAME", "Tickets"))
    if cat:
        return cat
    try:
        return await guild.create_category(bot_settings.get("TICKET_CATEGORY_NAME", "Tickets"), reason="Ticket system setup")
    except discord.Forbidden:
        return None

def staff_role(guild: discord.Guild) -> Optional[discord.Role]:
    return discord.utils.get(guild.roles, name=bot_settings.get("STAFF_ROLE_NAME", "Staff"))

@bot.command(name="ticket")
async def ticket(ctx: commands.Context, *, subject: str = "Support"):
    cat = await ensure_ticket_category(ctx.guild)
    if not cat:
        await ctx.send("I need permission to create categories to open tickets.")
        return

    # Permission setup: only requester + staff can see
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        bot.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    staff = staff_role(ctx.guild)
    if staff:
        overwrites[staff] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    name = f"ticket-{ctx.author.name.lower()}-{random.randint(1000,9999)}"
    ch = await ctx.guild.create_text_channel(
        name=name,
        category=cat,
        overwrites=overwrites,
        topic=f"Ticket for {ctx.author} — {subject}"
    )
    await ch.send(f"{ctx.author.mention} Thanks for opening a ticket. A staff member will be with you shortly.\nSubject: {subject}")
    await ctx.send(f"Ticket created: {ch.mention}")

@bot.command(name="close", help="Close the current ticket channel")
@commands.has_role(STAFF_ROLE_NAME)
async def close(ctx: commands.Context):
    if ctx.channel.category and ctx.channel.category.name == bot_settings.get("TICKET_CATEGORY_NAME", "Tickets"):
        await ctx.send("Closing ticket in 5 seconds...")
        await asyncio.sleep(5)
        try:
            await ctx.channel.delete(reason=f"Ticket closed by {ctx.author}")
        except discord.Forbidden:
            await ctx.send("I don't have permission to delete this channel.")
    else:
        await ctx.send("This command can only be used in a ticket channel.")

# -----------------------------
# POLLS: create polls with reactions (from giveaway bot)
# -----------------------------
@bot.command(name="poll")
async def poll(ctx: commands.Context, question: str = None, *options: str):
    # Usage: !poll "Your question" option1 option2 option3 ...
    if not question:
        await ctx.send("**Poll Usage:**\n`!poll \"Your question here\" Option1 Option2 Option3`\n\n**Example:**\n`!poll \"Best fruit?\" Apple Banana Orange`\n\n**Note:** The question must be in quotes!")
        return
    if len(options) == 0:
        await ctx.send("Provide at least one option.\n**Example:** `!poll \"Best fruit?\" Apple Banana`")
        return
    if len(options) > len(bot_settings.get("DEFAULT_POLL_EMOJIS", ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"])):
        await ctx.send(f"Max {len(bot_settings.get("DEFAULT_POLL_EMOJIS", ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]))} options.")
        return

    emojis = bot_settings.get("DEFAULT_POLL_EMOJIS", ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"])[:len(options)]
    description_lines = [f"{emoji} {opt}" for emoji, opt in zip(emojis, options)]
    embed = discord.Embed(title="Poll", description="**" + question + "**", color=discord.Color.blurple()) # Added bold to question
    embed.add_field(name="Options", value="\n".join(description_lines), inline=False)
    msg = await ctx.send(embed=embed)

    # Add reactions and track poll
    for emoji in emojis:
        await msg.add_reaction(emoji)

    state["polls"][str(msg.id)] = {"options": list(options), "emoji_map": emojis}
    save_state()

@bot.command(name="pollresults")
async def pollresults(ctx: commands.Context, message_id: int):
    # Usage: !pollresults <message_id>
    msg = None
    try:
        msg = await ctx.channel.fetch_message(message_id)
    except discord.NotFound:
        await ctx.send("Poll message not found in this channel.")
        return

    poll = state["polls"].get(str(message_id))
    if not poll:
        await ctx.send("No tracked poll for that message.")
        return

    counts = []
    for emoji in poll["emoji_map"]:
        r = discord.utils.get(msg.reactions, emoji=emoji)
        counts.append(r.count - (1 if r and r.me else 0))

    lines = [f"{emoji} {opt}: {cnt}" for emoji, opt, cnt in zip(poll["emoji_map"], poll["options"], counts)]
    await ctx.send("Poll results:\n" + "\n".join(lines))

# -----------------------------
# GIVEAWAYS: GiveawayBot replacement with slash commands
# -----------------------------

async def conclude_giveaway(msg: discord.Message, winners_count: int = 1):
    """Conclude a giveaway and pick winner(s)"""
    data = state["giveaways"].get(str(msg.id))
    if not data:
        return

    emoji = state["giveaway_settings"]["emoji"]
    color = state["giveaway_settings"]["color"]

    await msg.edit(embed=discord.Embed(
        title="🎉 GIVEAWAY ENDED 🎉",
        description=f"**Prize:** {data['prize']}\n\nSelecting {winners_count} winner(s)...",
        color=color
    ))

    # Fetch users who reacted
    reaction = discord.utils.get(msg.reactions, emoji=emoji)
    if not reaction:
        await msg.channel.send("❌ No entries for this giveaway.")
        return

    users = []
    try:
        async for user in reaction.users():
            if not user.bot:
                users.append(user)
    except discord.Forbidden:
        await msg.channel.send("❌ I lack permission to read reactions.")
        return

    if not users:
        await msg.channel.send("❌ No valid entries for this giveaway.")
        return

    # Pick winners
    num_winners = min(winners_count, len(users))
    winners = random.sample(users, num_winners)

    # Store winners for potential reroll
    data["winners"] = [w.id for w in winners]
    state["giveaways"][str(msg.id)] = data
    save_state()

    # Announce winners
    if num_winners == 1:
        await msg.channel.send(f"🎉 Congratulations {winners[0].mention}! You won **{data['prize']}**!")
    else:
        winner_mentions = ", ".join([w.mention for w in winners])
        await msg.channel.send(f"🎉 Congratulations to our {num_winners} winners!\n{winner_mentions}\n\nYou won **{data['prize']}**!")

    # Update embed with winners
    winner_text = "\n".join([f"• {w.mention}" for w in winners])
    await msg.edit(embed=discord.Embed(
        title="🎉 GIVEAWAY ENDED 🎉",
        description=f"**Prize:** {data['prize']}\n\n**Winner(s):**\n{winner_text}",
        color=color
    ).set_footer(text=f"Ended • {num_winners} winner(s)"))

# Slash Commands for Giveaways
@bot.tree.command(name="gstart", description="Start a giveaway")
@app_commands.describe(
    duration="Duration in hours",
    winners="Number of winners",
    prize="Prize description"
)
async def gstart(interaction: discord.Interaction, duration: int, winners: int, prize: str):
    """Start a giveaway"""
    if not has_staff_permission(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to start giveaways.", ephemeral=True)
        return

    if duration <= 0:
        await interaction.response.send_message("❌ Duration must be greater than 0 hours.", ephemeral=True)
        return

    if winners <= 0:
        await interaction.response.send_message("❌ Number of winners must be at least 1.", ephemeral=True)
        return

    emoji = state["giveaway_settings"]["emoji"]
    color = state["giveaway_settings"]["color"]
    seconds = duration * 3600  # Convert hours to seconds

    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"**Prize:** {prize}\n\nReact with {emoji} to enter!\n⏰ Ends: <t:{int(time.time() + seconds)}:R>",
        color=color
    )
    embed.set_footer(text=f"Hosted by {interaction.user.display_name} • {winners} winner(s)")

    await interaction.response.send_message(embed=embed)
    msg = await interaction.original_response()
    await msg.add_reaction(emoji)

    # Store giveaway data
    state["giveaways"][str(msg.id)] = {
        "channel_id": interaction.channel_id,
        "end_ts": time.time() + seconds,
        "prize": prize,
        "winners": winners,
        "host_id": interaction.user.id,
        "ended": False
    }
    save_state()

    # Schedule end
    await asyncio.sleep(seconds)
    await conclude_giveaway(msg, winners)

@bot.tree.command(name="gend", description="End a giveaway early")
@app_commands.describe(message_id="ID of the giveaway message")
async def gend(interaction: discord.Interaction, message_id: str):
    """End a giveaway early"""
    if not has_staff_permission(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to end giveaways.", ephemeral=True)
        return

    if message_id not in state["giveaways"]:
        await interaction.response.send_message("❌ Giveaway not found.", ephemeral=True)
        return

    data = state["giveaways"][message_id]
    if data.get("ended"):
        await interaction.response.send_message("❌ This giveaway has already ended.", ephemeral=True)
        return

    try:
        channel = bot.get_channel(data["channel_id"])
        msg = await channel.fetch_message(int(message_id))
        await interaction.response.send_message("✅ Ending giveaway...", ephemeral=True)
        await conclude_giveaway(msg, data["winners"])
        data["ended"] = True
        save_state()
    except Exception as e:
        await interaction.response.send_message(f"❌ Error ending giveaway: {e}", ephemeral=True)

@bot.tree.command(name="greroll", description="Reroll a giveaway winner")
@app_commands.describe(message_id="ID of the giveaway message")
async def greroll(interaction: discord.Interaction, message_id: str):
    """Reroll giveaway winners"""
    if not has_staff_permission(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to reroll giveaways.", ephemeral=True)
        return

    if message_id not in state["giveaways"]:
        await interaction.response.send_message("❌ Giveaway not found.", ephemeral=True)
        return

    data = state["giveaways"][message_id]
    if not data.get("ended"):
        await interaction.response.send_message("❌ This giveaway hasn't ended yet.", ephemeral=True)
        return

    try:
        channel = bot.get_channel(data["channel_id"])
        msg = await channel.fetch_message(int(message_id))
        await interaction.response.send_message("🔄 Rerolling winners...", ephemeral=True)
        await conclude_giveaway(msg, data["winners"])
    except Exception as e:
        await interaction.response.send_message(f"❌ Error rerolling: {e}", ephemeral=True)

@bot.tree.command(name="gdelete", description="Delete a giveaway")
@app_commands.describe(message_id="ID of the giveaway message")
async def gdelete(interaction: discord.Interaction, message_id: str):
    """Delete a giveaway"""
    if not has_staff_permission(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to delete giveaways.", ephemeral=True)
        return

    if message_id not in state["giveaways"]:
        await interaction.response.send_message("❌ Giveaway not found.", ephemeral=True)
        return

    try:
        data = state["giveaways"][message_id]
        channel = bot.get_channel(data["channel_id"])
        msg = await channel.fetch_message(int(message_id))
        await msg.delete()
        del state["giveaways"][message_id]
        save_state()
        await interaction.response.send_message("✅ Giveaway deleted.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error deleting giveaway: {e}", ephemeral=True)

@bot.tree.command(name="glist", description="List active giveaways")
async def glist(interaction: discord.Interaction):
    """List all active giveaways"""
    active = [(msg_id, data) for msg_id, data in state["giveaways"].items() if not data.get("ended")]

    if not active:
        await interaction.response.send_message("📋 No active giveaways.", ephemeral=True)
        return

    embed = discord.Embed(
        title="📋 Active Giveaways",
        description=f"Total: {len(active)} giveaway(s)",
        color=state["giveaway_settings"]["color"]
    )

    for msg_id, data in active[:10]:  # Limit to 10
        time_left = int(data["end_ts"] - time.time())
        if time_left > 0:
            embed.add_field(
                name=f"🎁 {data['prize']}",
                value=f"Message ID: `{msg_id}`\nWinners: {data['winners']}\nEnds: <t:{int(data['end_ts'])}:R>",
                inline=False
            )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="gabout", description="About this bot")
async def gabout(interaction: discord.Interaction):
    """Show bot info"""
    embed = discord.Embed(
        title="🎉 Giveaway Bot",
        description="A full-featured giveaway bot for Discord!",
        color=state["giveaway_settings"]["color"]
    )
    embed.add_field(name="Commands", value="Use `/gstart` to create giveaways\nUse `/glist` to see active giveaways", inline=False)
    embed.set_footer(text=f"Powered by {bot.user.name}")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="gping", description="Check bot latency")
async def gping(interaction: discord.Interaction):
    """Ping command"""
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latency: {latency}ms", ephemeral=True)

@bot.tree.command(name="ginvite", description="Get bot invite link")
async def ginvite(interaction: discord.Interaction):
    """Generate invite link"""
    permissions = discord.Permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
        add_reactions=True,
        read_message_history=True
    )
    invite_url = discord.utils.oauth_url(bot.user.id, permissions=permissions)
    await interaction.response.send_message(f"🔗 Invite me: {invite_url}", ephemeral=True)

# Giveaway settings commands
@bot.tree.command(name="gsettings", description="Manage giveaway settings")
@app_commands.describe(
    action="Action to perform",
    setting="Setting to change",
    value="New value"
)
@app_commands.choices(action=[
    app_commands.Choice(name="show", value="show"),
    app_commands.Choice(name="set", value="set")
])
@app_commands.choices(setting=[
    app_commands.Choice(name="emoji", value="emoji"),
    app_commands.Choice(name="color", value="color")
])
async def gsettings(interaction: discord.Interaction, action: str, setting: str = None, value: str = None):
    """Manage giveaway settings"""
    if not has_staff_permission(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to change settings.", ephemeral=True)
        return

    if action == "show":
        emoji = state["giveaway_settings"]["emoji"]
        color = state["giveaway_settings"]["color"]
        embed = discord.Embed(
            title="⚙️ Giveaway Settings",
            color=color
        )
        embed.add_field(name="Emoji", value=emoji, inline=True)
        embed.add_field(name="Color", value=f"#{color:06x}", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    elif action == "set":
        if not setting or not value:
            await interaction.response.send_message("❌ Please specify both setting and value.", ephemeral=True)
            return

        if setting == "emoji":
            state["giveaway_settings"]["emoji"] = value
            save_state()
            await interaction.response.send_message(f"✅ Emoji set to {value}", ephemeral=True)

        elif setting == "color":
            try:
                # Accept hex color like #FFD700 or FFD700
                color_value = value.lstrip("#")
                color_int = int(color_value, 16)
                state["giveaway_settings"]["color"] = color_int
                save_state()
                await interaction.response.send_message(f"✅ Color set to #{color_int:06x}", ephemeral=True)
            except ValueError:
                await interaction.response.send_message("❌ Invalid color format. Use hex format like #FFD700", ephemeral=True)

# -----------------------------
# ERROR HANDLING
# -----------------------------
@close.error
async def close_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send(f"You need the '{bot_settings.get('STAFF_ROLE_NAME', 'Staff')}' role to close tickets.")

# -----------------------------
# RUN THE BOT
# -----------------------------
# Replace with your bot token (keep it secret!)
bot.remove_command("help") # Disable default help command

@bot.command(name="help")
@commands.has_any_role("OWNER", "ADMIN", "Staff")
async def help_command(ctx: commands.Context, command: Optional[str] = None):
    """Shows help for all commands or a specific command."""
    try:
        if command:
            # Help for a specific command
            cmd = bot.get_command(command)
            if not cmd:
                await ctx.send(f"Command `{command}` not found.")
                return

            embed = discord.Embed(
                title=f"Help for `{cmd.name}`",
                description=cmd.help or "No description provided.",
                color=discord.Color.blue()
            )
            if cmd.aliases:
                embed.add_field(name="Aliases", value=", ".join(cmd.aliases), inline=False)
            embed.add_field(name="Usage", value=f"`{ctx.prefix}{cmd.usage or cmd.name}`", inline=False)
            await ctx.send(embed=embed)
        else:
            # General help
            embed = discord.Embed(
                title="Bot Commands",
                description="Here's a list of all available commands:",
                color=discord.Color.green()
            )

            categories = {
                "General": [],
                "Server Status": [],
                "Player Management": [],
                "Server Communication": [],
                "Server Control": [],
                "Discord Moderation": [],
                "Ticketing": [],
                "Polls & Giveaways": [],
                "Leveling": []
            }

            for cmd in bot.commands:
                if not cmd.hidden: # Only show non-hidden commands
                    if cmd.name in ["ping", "roast", "prayer"]:
                        categories["General"].append(f"`{ctx.prefix}{cmd.name}`")
                    elif cmd.name in ["serverstatus", "playerlist", "playercount"]:
                        categories["Server Status"].append(f"`{ctx.prefix}{cmd.name}`")
                    elif cmd.name in ["kick", "ban", "unban", "whitelist", "blacklist"]:
                        categories["Player Management"].append(f"`{ctx.prefix}{cmd.name}`")
                    elif cmd.name in ["say", "sayto", "broadcast", "broadcastto"]:
                        categories["Server Communication"].append(f"`{ctx.prefix}{cmd.name}`")
                    elif cmd.name in ["start", "stop", "restart", "destroydinos", "getgamelog", "rcon"]:
                        categories["Server Control"].append(f"`{ctx.prefix}{cmd.name}`")
                    elif cmd.name in ["mute", "unmute", "deafen", "undeafen"]:
                        categories["Discord Moderation"].append(f"`{ctx.prefix}{cmd.name}`")
                    elif cmd.name in ["ticket", "close"]:
                        categories["Ticketing"].append(f"`{ctx.prefix}{cmd.name}`")
                    elif cmd.name in ["poll", "pollresults"]:
                        categories["Polls & Giveaways"].append(f"`{ctx.prefix}{cmd.name}`")
                    elif cmd.name in ["rank", "leaderboard"]:
                        categories["Leveling"].append(f"`{ctx.prefix}{cmd.name}`")

            for category, cmds in categories.items():
                if cmds:
                    embed.add_field(name=category, value="\n".join(cmds), inline=False)

            # Add slash commands info
            embed.add_field(
                name="🎉 Slash Commands (Giveaways)",
                value="`/gstart` `/gend` `/greroll` `/gdelete` `/glist`\n`/gabout` `/gping` `/ginvite` `/gsettings`",
                inline=False
            )

            embed.set_footer(text=f"Use {ctx.prefix}help <command> for more info on a command.")
            await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Error in help command: {e}")
        print(f"Help command error: {e}")

@bot.command(name="commands")
async def commands_command(ctx: commands.Context):
    """Shows all user-accessible commands (non-admin)."""
    embed = discord.Embed(
        title="Available Commands",
        description="Here are the commands you can use:",
        color=discord.Color.blue()
    )

    # Only show commands that regular users can access
    user_commands = {
        "General": [
            f"`{ctx.prefix}ping` - Check if bot is responsive",
            f"`{ctx.prefix}roast` - Get a random roast",
            f"`{ctx.prefix}prayer` - Receive a blessing"
        ],
        "Leveling/Stats": [
            f"`{ctx.prefix}rank [user]` - Check your rank and XP (or another user's)",
            f"`{ctx.prefix}leaderboard [top]` - View the XP leaderboard (default top 10)"
        ],
        "Ticketing": [
            f"`{ctx.prefix}ticket [subject]` - Open a support ticket"
        ],
        "Polls": [
            f"`{ctx.prefix}poll \"question\" option1 option2...` - Create a poll with up to 5 options",
            f"`{ctx.prefix}pollresults <message_id>` - View results of a poll"
        ]
    }

    for category, cmds in user_commands.items():
        embed.add_field(name=category, value="\n".join(cmds), inline=False)

    embed.set_footer(text=f"For admin commands, ask a staff member.")
    await ctx.send(embed=embed)

# -----------------------------
# STARTUP VALIDATION
# -----------------------------
if __name__ == "__main__":
    # Check for Discord token
    if not DISCORD_TOKEN:
        print("=" * 60)
        print("ERROR: DISCORD_TOKEN not found!")
        print("=" * 60)
        print("Please create a .env file with your Discord bot token:")
        print("DISCORD_TOKEN=your_token_here")
        print()
        print("To get a Discord bot token:")
        print("1. Go to https://discord.com/developers/applications")
        print("2. Create a new application or select an existing one")
        print("3. Go to the 'Bot' section")
        print("4. Copy the token and add it to your .env file")
        print("=" * 60)
        exit(1)

    # Check for servers.json
    if not os.path.exists(SERVER_CONFIG_FILE):
        print("=" * 60)
        print("WARNING: servers.json not found!")
        print("=" * 60)
        print("RCON commands will not work without server configuration.")
        print("Please create a servers.json file with this structure:")
        print("""
{
  "BotSettings": {
    "COMMAND_PREFIX": "!",
    "ADMIN_LOG_CHANNEL_ID": 0,
    "GAME_CHAT_CHANNEL_ID": 0,
    "STAFF_ROLE_NAME": "Staff"
  },
  "servers": {
    "DefaultServer": {
      "RCON_HOST": "your.server.ip",
      "RCON_PORT": 27020,
      "RCON_PASSWORD": "your_rcon_password"
    }
  }
}
""")
        print("=" * 60)
        print("Continuing without RCON functionality...")
        print()

    print("=" * 60)
    print(f"Starting Discord Bot...")
    print(f"Command Prefix: {bot_settings.get('COMMAND_PREFIX', '!')}")
    print(f"Loaded {len(server_configs)} server configuration(s)")
    print("=" * 60)

    try:
        bot.run(DISCORD_TOKEN)
    except discord.LoginFailure:
        print("=" * 60)
        print("ERROR: Invalid Discord token!")
        print("=" * 60)
        print("Please check your DISCORD_TOKEN in the .env file")
        print("=" * 60)
        cleanup_config_ui()
        exit(1)
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("Bot shutdown requested...")
        print("=" * 60)
        cleanup_config_ui()
        exit(0)
    except Exception as e:
        print("=" * 60)
        print(f"ERROR: Failed to start bot: {e}")
        print("=" * 60)
        cleanup_config_ui()
        exit(1)
    finally:
        cleanup_config_ui()