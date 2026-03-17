import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox, filedialog
import json
import os
from dotenv import load_dotenv, set_key
import webbrowser

# ============================================================================
# FILE PATHS - Define paths relative to the script's location
# ============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVERS_FILE = os.path.join(SCRIPT_DIR, "servers.json")
ENV_FILE = os.path.join(SCRIPT_DIR, ".env")
FORBIDDEN_WORDS_FILE = os.path.join(SCRIPT_DIR, "forbidden_words.json")
MODERATED_CHANNELS_FILE = os.path.join(SCRIPT_DIR, "moderated_channels.json")
ROLES_FILE = os.path.join(SCRIPT_DIR, "roles.json")
STAFF_ROLES_FILE = os.path.join(SCRIPT_DIR, "staff_roles.json")

class ConfigUI(ttk.Window):
    def __init__(self):
        super().__init__(themename="darkly")
        self.title("Eye of Sauron - Bot Configuration")
        self.geometry("500x900")

        # ====================================================================
        # SERVER CONFIGURATION VARIABLES
        # ====================================================================
        self.selected_server_name = tk.StringVar()
        self.server_name = tk.StringVar()
        self.rcon_host = tk.StringVar()
        self.rcon_port = tk.StringVar()
        self.rcon_password = tk.StringVar()
        self.install_dir = tk.StringVar()
        self.servers_dict = {}  # {server_name: {RCON_HOST, RCON_PORT, RCON_PASSWORD, install_dir}}

        # ====================================================================
        # DISCORD CONFIGURATION VARIABLES
        # ====================================================================
        self.discord_token = tk.StringVar()
        self.discord_server_id = tk.StringVar()
        self.admin_log_channel_id = tk.StringVar()
        self.game_chat_channel_id = tk.StringVar()

        # ====================================================================
        # MODERATION VARIABLES
        # ====================================================================
        self.new_forbidden_word = tk.StringVar()
        self.forbidden_words_list = []
        self.new_moderated_channel_id = tk.StringVar()
        self.moderated_channel_ids_list = []
        self.word_filter_timeout = tk.StringVar(value="5")

        # ====================================================================
        # ROLES VARIABLES
        # ====================================================================
        self.new_role = tk.StringVar()
        self.roles_list = []
        self.new_staff_role = tk.StringVar()
        self.staff_roles_list = []

        # ====================================================================
        # BOT SETTINGS VARIABLES
        # ====================================================================
        self.command_prefix = tk.StringVar(value="!")
        self.staff_role_name = tk.StringVar(value="Staff")
        self.ticket_category_name = tk.StringVar(value="Tickets")
        self.enable_rcon_monitoring = tk.BooleanVar(value=True)
        self.cross_chat_roles_list = []
        self.new_cross_chat_role = tk.StringVar()

        # ====================================================================
        # LEVELING & XP VARIABLES
        # ====================================================================
        self.xp_min = tk.StringVar(value="5")
        self.xp_max = tk.StringVar(value="10")
        self.xp_cooldown = tk.StringVar(value="60")
        self.level_xp_base = tk.StringVar(value="100")
        self.role_rewards_dict = {}  # {level: role_name}
        self.new_reward_level = tk.StringVar()
        self.new_reward_role = tk.StringVar()

        # ====================================================================
        # INITIALIZE UI
        # ====================================================================
        self.create_widgets()
        self.load_configs()

    def create_widgets(self):
        notebook = ttk.Notebook(self)
        notebook.pack(pady=10, padx=10, expand=True, fill=BOTH)

        tab1 = ttk.Frame(notebook)
        tab2 = ttk.Frame(notebook)
        tab3 = ttk.Frame(notebook)
        tab4 = ttk.Frame(notebook)
        tab5 = ttk.Frame(notebook)

        notebook.add(tab1, text='Initial Setup')
        notebook.add(tab2, text='Discord')
        notebook.add(tab3, text='Channels & Roles')
        notebook.add(tab4, text='Bot Settings')
        notebook.add(tab5, text='Leveling & XP')

        # --- Tab 1: Initial Setup ---
        # Bot Actions
        bot_actions_frame = ttk.Labelframe(tab1, text="Bot Actions", padding=(10, 5))
        bot_actions_frame.pack(padx=10, pady=5, fill="x")

        invite_button = ttk.Button(bot_actions_frame, text="Invite Bot to Server", command=self.invite_bot, bootstyle=INFO)
        invite_button.pack(pady=10)

        # Server Configuration
        server_config_frame = ttk.Labelframe(tab1, text="Server Configuration", padding=(10, 5))
        server_config_frame.pack(padx=10, pady=5, fill="x")

        ttk.Label(server_config_frame, text="Server Name:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(server_config_frame, textvariable=self.server_name).grid(row=0, column=1, padx=5, pady=2, sticky="ew", columnspan=2)

        ttk.Label(server_config_frame, text="Install Directory:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(server_config_frame, textvariable=self.install_dir).grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        ttk.Button(server_config_frame, text="Browse...", command=self.browse_install_dir).grid(row=1, column=2, padx=5, pady=2)

        ttk.Label(server_config_frame, text="RCON Host:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(server_config_frame, textvariable=self.rcon_host).grid(row=2, column=1, padx=5, pady=2, sticky="ew", columnspan=2)

        ttk.Label(server_config_frame, text="RCON Port:").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(server_config_frame, textvariable=self.rcon_port).grid(row=3, column=1, padx=5, pady=2, sticky="ew", columnspan=2)

        ttk.Label(server_config_frame, text="RCON Password:").grid(row=4, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(server_config_frame, textvariable=self.rcon_password, show="*").grid(row=4, column=1, padx=5, pady=2, sticky="ew", columnspan=2)

        server_config_frame.columnconfigure(1, weight=1)

        # Server Selection & Management
        servers_list_frame = ttk.Labelframe(tab1, text="Server Management", padding=(10, 5))
        servers_list_frame.pack(padx=10, pady=5, fill="x")

        # Server selection dropdown
        servers_select_frame = ttk.Frame(servers_list_frame)
        servers_select_frame.pack(pady=5, fill=X)

        ttk.Label(servers_select_frame, text="Select Server:").pack(side=LEFT, padx=(0, 5))
        self.servers_combobox = ttk.Combobox(servers_select_frame, state="readonly", width=30)
        self.servers_combobox.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        self.servers_combobox.bind('<<ComboboxSelected>>', self.on_server_select)

        # Server management buttons
        servers_buttons_frame = ttk.Frame(servers_list_frame)
        servers_buttons_frame.pack(pady=5, fill=X)

        ttk.Button(servers_buttons_frame, text="Add New", command=self.add_server, bootstyle=SUCCESS).pack(side=LEFT, padx=5)
        ttk.Button(servers_buttons_frame, text="Edit Selected", command=self.update_server, bootstyle=INFO).pack(side=LEFT, padx=5)
        ttk.Button(servers_buttons_frame, text="Remove", command=self.remove_server, bootstyle=DANGER).pack(side=LEFT, padx=5)
        ttk.Button(servers_buttons_frame, text="Clear Fields", command=self.clear_server_fields, bootstyle=SECONDARY).pack(side=LEFT, padx=5)

        # --- Tab 2: Discord ---
        discord_tab_frame = ttk.Frame(tab2)
        discord_tab_frame.pack(fill=BOTH, expand=True)

        # Discord Settings
        discord_settings_frame = ttk.Labelframe(discord_tab_frame, text="Discord Settings", padding=(10, 5))
        discord_settings_frame.pack(padx=10, pady=5, fill="x")

        ttk.Label(discord_settings_frame, text="Bot Token:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(discord_settings_frame, textvariable=self.discord_token, show="*").grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(discord_settings_frame, text="Discord Server ID:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(discord_settings_frame, textvariable=self.discord_server_id).grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        discord_settings_frame.columnconfigure(1, weight=1)

        # Moderation Settings
        mod_settings_frame = ttk.Labelframe(discord_tab_frame, text="Moderation Settings", padding=(10, 5))
        mod_settings_frame.pack(padx=10, pady=5, fill="x")

        ttk.Label(mod_settings_frame, text="Word Filter Timeout (minutes):").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(mod_settings_frame, textvariable=self.word_filter_timeout).grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(mod_settings_frame, text="Staff Role Name:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(mod_settings_frame, textvariable=self.staff_role_name).grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(mod_settings_frame, text="Ticket Category Name:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(mod_settings_frame, textvariable=self.ticket_category_name).grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        mod_settings_frame.columnconfigure(1, weight=1)

        # Forbidden Words
        forbidden_words_frame = ttk.Labelframe(discord_tab_frame, text="Forbidden Words", padding=(10, 5))
        forbidden_words_frame.pack(padx=10, pady=5, fill=BOTH, expand=True)

        fw_list_frame = ttk.Frame(forbidden_words_frame)
        fw_list_frame.pack(pady=5, fill=BOTH, expand=True)

        self.forbidden_words_listbox = tk.Listbox(fw_list_frame, selectmode=tk.SINGLE, height=4)
        self.forbidden_words_listbox.pack(side=LEFT, fill=BOTH, expand=True)

        fw_scrollbar = ttk.Scrollbar(fw_list_frame, orient=VERTICAL, command=self.forbidden_words_listbox.yview)
        fw_scrollbar.pack(side=RIGHT, fill=Y)
        self.forbidden_words_listbox.config(yscrollcommand=fw_scrollbar.set)

        fw_controls_frame = ttk.Frame(forbidden_words_frame)
        fw_controls_frame.pack(pady=5, fill=X)

        ttk.Entry(fw_controls_frame, textvariable=self.new_forbidden_word).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        ttk.Button(fw_controls_frame, text="Add", command=self.add_forbidden_word, bootstyle=SUCCESS).pack(side=LEFT, padx=(0, 5))
        ttk.Button(fw_controls_frame, text="Remove", command=self.remove_forbidden_word, bootstyle=DANGER).pack(side=LEFT)

        # Moderated Channel IDs
        mod_channels_frame = ttk.Labelframe(discord_tab_frame, text="Moderated Channel IDs", padding=(10, 5))
        mod_channels_frame.pack(padx=10, pady=5, fill=BOTH, expand=True)

        mc_list_frame = ttk.Frame(mod_channels_frame)
        mc_list_frame.pack(pady=5, fill=BOTH, expand=True)

        self.moderated_channels_listbox = tk.Listbox(mc_list_frame, selectmode=tk.SINGLE, height=4)
        self.moderated_channels_listbox.pack(side=LEFT, fill=BOTH, expand=True)

        mc_scrollbar = ttk.Scrollbar(mc_list_frame, orient=VERTICAL, command=self.moderated_channels_listbox.yview)
        mc_scrollbar.pack(side=RIGHT, fill=Y)
        self.moderated_channels_listbox.config(yscrollcommand=mc_scrollbar.set)

        mc_controls_frame = ttk.Frame(mod_channels_frame)
        mc_controls_frame.pack(pady=5, fill=X)

        ttk.Entry(mc_controls_frame, textvariable=self.new_moderated_channel_id).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        ttk.Button(mc_controls_frame, text="Add", command=self.add_moderated_channel, bootstyle=SUCCESS).pack(side=LEFT, padx=(0, 5))
        ttk.Button(mc_controls_frame, text="Remove", command=self.remove_moderated_channel, bootstyle=DANGER).pack(side=LEFT)

        # --- Tab 3: Channels & Roles ---
        channels_roles_frame = ttk.Frame(tab3)
        channels_roles_frame.pack(fill=BOTH, expand=True)

        # Channel IDs
        channel_frame = ttk.Labelframe(channels_roles_frame, text="Channel IDs", padding=(10, 5))
        channel_frame.pack(padx=10, pady=5, fill="x")
        ttk.Label(channel_frame, text="Admin Log Channel:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(channel_frame, textvariable=self.admin_log_channel_id).grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        ttk.Label(channel_frame, text="Game Chat Channel:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(channel_frame, textvariable=self.game_chat_channel_id).grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        channel_frame.columnconfigure(1, weight=1)

        # Admin Roles
        roles_frame = ttk.Labelframe(channels_roles_frame, text="Admin Roles", padding=(10, 5))
        roles_frame.pack(padx=10, pady=5, fill=BOTH, expand=True)

        roles_list_frame = ttk.Frame(roles_frame)
        roles_list_frame.pack(pady=5, fill=BOTH, expand=True)

        self.roles_listbox = tk.Listbox(roles_list_frame, selectmode=tk.SINGLE, height=2)
        self.roles_listbox.pack(side=LEFT, fill=BOTH, expand=True)

        roles_scrollbar = ttk.Scrollbar(roles_list_frame, orient=VERTICAL, command=self.roles_listbox.yview)
        roles_scrollbar.pack(side=RIGHT, fill=Y)
        self.roles_listbox.config(yscrollcommand=roles_scrollbar.set)

        roles_controls_frame = ttk.Frame(roles_frame)
        roles_controls_frame.pack(pady=5, fill=X)

        ttk.Entry(roles_controls_frame, textvariable=self.new_role).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        ttk.Button(roles_controls_frame, text="Add", command=self.add_role, bootstyle=SUCCESS).pack(side=LEFT, padx=(0, 5))
        ttk.Button(roles_controls_frame, text="Remove", command=self.remove_role, bootstyle=DANGER).pack(side=LEFT)

        # Staff Roles
        staff_roles_frame = ttk.Labelframe(channels_roles_frame, text="Staff Roles", padding=(10, 5))
        staff_roles_frame.pack(padx=10, pady=5, fill=BOTH, expand=True)

        staff_roles_list_frame = ttk.Frame(staff_roles_frame)
        staff_roles_list_frame.pack(pady=5, fill=BOTH, expand=True)

        self.staff_roles_listbox = tk.Listbox(staff_roles_list_frame, selectmode=tk.SINGLE, height=2)
        self.staff_roles_listbox.pack(side=LEFT, fill=BOTH, expand=True)

        staff_roles_scrollbar = ttk.Scrollbar(staff_roles_list_frame, orient=VERTICAL, command=self.staff_roles_listbox.yview)
        staff_roles_scrollbar.pack(side=RIGHT, fill=Y)
        self.staff_roles_listbox.config(yscrollcommand=staff_roles_scrollbar.set)

        staff_roles_controls_frame = ttk.Frame(staff_roles_frame)
        staff_roles_controls_frame.pack(pady=5, fill=X)

        ttk.Entry(staff_roles_controls_frame, textvariable=self.new_staff_role).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        ttk.Button(staff_roles_controls_frame, text="Add", command=self.add_staff_role, bootstyle=SUCCESS).pack(side=LEFT, padx=(0, 5))
        ttk.Button(staff_roles_controls_frame, text="Remove", command=self.remove_staff_role, bootstyle=DANGER).pack(side=LEFT)

        # --- Tab 4: Bot Settings ---
        bot_settings_tab_frame = ttk.Frame(tab4)
        bot_settings_tab_frame.pack(fill=BOTH, expand=True)

        # General Bot Configuration
        general_config_frame = ttk.Labelframe(bot_settings_tab_frame, text="General Configuration", padding=(10, 5))
        general_config_frame.pack(padx=10, pady=5, fill="x")

        ttk.Label(general_config_frame, text="Command Prefix:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(general_config_frame, textvariable=self.command_prefix).grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ttk.Checkbutton(general_config_frame, text="Enable RCON Chat Monitoring", variable=self.enable_rcon_monitoring).grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        general_config_frame.columnconfigure(1, weight=1)

        # Cross-Chat Roles
        cross_chat_frame = ttk.Labelframe(bot_settings_tab_frame, text="Cross-Chat Allowed Roles", padding=(10, 5))
        cross_chat_frame.pack(padx=10, pady=5, fill="x")

        cc_list_frame = ttk.Frame(cross_chat_frame)
        cc_list_frame.pack(pady=5, fill=X)

        self.cross_chat_roles_listbox = tk.Listbox(cc_list_frame, selectmode=tk.SINGLE, height=6)
        self.cross_chat_roles_listbox.pack(side=LEFT, fill=BOTH, expand=True)

        cc_scrollbar = ttk.Scrollbar(cc_list_frame, orient=VERTICAL, command=self.cross_chat_roles_listbox.yview)
        cc_scrollbar.pack(side=RIGHT, fill=Y)
        self.cross_chat_roles_listbox.config(yscrollcommand=cc_scrollbar.set)

        cc_controls_frame = ttk.Frame(cross_chat_frame)
        cc_controls_frame.pack(pady=5, fill=X)

        ttk.Entry(cc_controls_frame, textvariable=self.new_cross_chat_role).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        ttk.Button(cc_controls_frame, text="Add", command=self.add_cross_chat_role, bootstyle=SUCCESS).pack(side=LEFT, padx=(0, 5))
        ttk.Button(cc_controls_frame, text="Remove", command=self.remove_cross_chat_role, bootstyle=DANGER).pack(side=LEFT)

        # Theme Settings
        theme_settings_frame = ttk.Labelframe(bot_settings_tab_frame, text="Theme Settings", padding=(10, 5))
        theme_settings_frame.pack(padx=10, pady=5, fill="x")

        ttk.Label(theme_settings_frame, text="Choose Theme:").pack(pady=5)
        self.theme_options = self.style.theme_names() # Get available themes
        self.selected_theme = tk.StringVar(value=self.style.theme_use()) # Default to current theme
        theme_combobox = ttk.Combobox(theme_settings_frame, textvariable=self.selected_theme, values=self.theme_options, state="readonly")
        theme_combobox.pack(pady=5)
        theme_combobox.bind("<<ComboboxSelected>>", self.change_theme)

        # --- Tab 5: Leveling & XP ---
        leveling_tab_frame = ttk.Frame(tab5)
        leveling_tab_frame.pack(fill=BOTH, expand=True)

        # XP Settings
        xp_settings_frame = ttk.Labelframe(leveling_tab_frame, text="XP Settings", padding=(10, 5))
        xp_settings_frame.pack(padx=10, pady=5, fill="x")

        ttk.Label(xp_settings_frame, text="XP Range Min:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(xp_settings_frame, textvariable=self.xp_min).grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(xp_settings_frame, text="XP Range Max:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(xp_settings_frame, textvariable=self.xp_max).grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(xp_settings_frame, text="XP Cooldown (seconds):").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(xp_settings_frame, textvariable=self.xp_cooldown).grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(xp_settings_frame, text="Level XP Base:").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(xp_settings_frame, textvariable=self.level_xp_base).grid(row=3, column=1, padx=5, pady=2, sticky="ew")

        xp_settings_frame.columnconfigure(1, weight=1)

        # Role Rewards
        role_rewards_frame = ttk.Labelframe(leveling_tab_frame, text="Role Rewards (Level → Role)", padding=(10, 5))
        role_rewards_frame.pack(padx=10, pady=5, fill=BOTH, expand=True)

        rr_list_frame = ttk.Frame(role_rewards_frame)
        rr_list_frame.pack(pady=5, fill=BOTH, expand=True)

        self.role_rewards_listbox = tk.Listbox(rr_list_frame, selectmode=tk.SINGLE, height=3)
        self.role_rewards_listbox.pack(side=LEFT, fill=BOTH, expand=True)

        rr_scrollbar = ttk.Scrollbar(rr_list_frame, orient=VERTICAL, command=self.role_rewards_listbox.yview)
        rr_scrollbar.pack(side=RIGHT, fill=Y)
        self.role_rewards_listbox.config(yscrollcommand=rr_scrollbar.set)

        rr_controls_frame = ttk.Frame(role_rewards_frame)
        rr_controls_frame.pack(pady=5, fill=X)

        ttk.Label(rr_controls_frame, text="Level:").pack(side=LEFT, padx=(0, 5))
        ttk.Entry(rr_controls_frame, textvariable=self.new_reward_level, width=8).pack(side=LEFT, padx=(0, 5))
        ttk.Label(rr_controls_frame, text="Role:").pack(side=LEFT, padx=(0, 5))
        ttk.Entry(rr_controls_frame, textvariable=self.new_reward_role).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        ttk.Button(rr_controls_frame, text="Add", command=self.add_role_reward, bootstyle=SUCCESS).pack(side=LEFT, padx=(0, 5))
        ttk.Button(rr_controls_frame, text="Remove", command=self.remove_role_reward, bootstyle=DANGER).pack(side=LEFT)

        # --- Bottom Buttons ---
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)

        save_button = ttk.Button(button_frame, text="Save Configuration", command=self.save_configs, bootstyle=SUCCESS)
        save_button.pack(side=LEFT, padx=5)

        load_button = ttk.Button(button_frame, text="Load Configuration", command=self.load_configs_and_show_info, bootstyle=INFO)
        load_button.pack(side=LEFT, padx=5)

    # ========================================================================
    # UI HELPER METHODS
    # ========================================================================
    def browse_install_dir(self):
        """Open directory browser for install directory selection"""
        directory = filedialog.askdirectory()
        if directory:
            self.install_dir.set(directory)

    # ========================================================================
    # SERVER MANAGEMENT METHODS
    # ========================================================================
    def load_servers_list(self):
        """Populate the servers dropdown"""
        server_names = sorted(self.servers_dict.keys())
        self.servers_combobox['values'] = server_names
        if server_names and not self.servers_combobox.get():
            self.servers_combobox.current(0)

    def on_server_select(self, event=None):
        """Load selected server configuration into fields"""
        server_name = self.servers_combobox.get()
        if not server_name:
            return

        self.selected_server_name.set(server_name)

        if server_name in self.servers_dict:
            server_config = self.servers_dict[server_name]
            self.server_name.set(server_name)
            self.rcon_host.set(server_config.get("RCON_HOST", ""))
            self.rcon_port.set(str(server_config.get("RCON_PORT", "")))
            self.rcon_password.set(server_config.get("RCON_PASSWORD", ""))
            self.install_dir.set(server_config.get("install_dir", ""))

    def add_server(self):
        """Add a new server with current field values"""
        server_name = self.server_name.get().strip()
        if not server_name:
            messagebox.showerror("Error", "Please enter a server name.")
            return

        if server_name in self.servers_dict:
            messagebox.showerror("Error", f"Server '{server_name}' already exists. Use 'Update Server' to modify it.")
            return

        # Validate required fields
        if not self.rcon_host.get() or not self.rcon_port.get() or not self.rcon_password.get():
            messagebox.showerror("Error", "Please fill in all RCON fields (Host, Port, Password).")
            return

        self.servers_dict[server_name] = {
            "RCON_HOST": self.rcon_host.get(),
            "RCON_PORT": int(self.rcon_port.get()) if self.rcon_port.get().isdigit() else 0,
            "RCON_PASSWORD": self.rcon_password.get(),
            "install_dir": self.install_dir.get()
        }

        self.load_servers_list()
        # Select the newly added server in dropdown
        self.servers_combobox.set(server_name)
        messagebox.showinfo("Success", f"Server '{server_name}' added successfully!")

        # Clear fields
        self.clear_server_fields()

    def update_server(self):
        """Update the selected server with current field values"""
        # Get the originally selected server name (before any edits)
        original_server_name = self.selected_server_name.get().strip()
        # Get the new server name from the input field
        new_server_name = self.server_name.get().strip()

        if not new_server_name:
            messagebox.showerror("Error", "Please enter a server name.")
            return

        if not original_server_name:
            messagebox.showerror("Error", "Please select a server from the list first.")
            return

        if original_server_name not in self.servers_dict:
            messagebox.showerror("Error", f"Original server '{original_server_name}' not found. Please select a server from the list.")
            return

        # Check if renaming to a name that already exists (but not the same server)
        if new_server_name != original_server_name and new_server_name in self.servers_dict:
            messagebox.showerror("Error", f"Server '{new_server_name}' already exists. Choose a different name.")
            return

        # Validate required fields
        if not self.rcon_host.get() or not self.rcon_port.get() or not self.rcon_password.get():
            messagebox.showerror("Error", "Please fill in all RCON fields (Host, Port, Password).")
            return

        # Create/update the server config
        server_config = {
            "RCON_HOST": self.rcon_host.get(),
            "RCON_PORT": int(self.rcon_port.get()) if self.rcon_port.get().isdigit() else 0,
            "RCON_PASSWORD": self.rcon_password.get(),
            "install_dir": self.install_dir.get()
        }

        # If the name changed, remove the old entry
        if new_server_name != original_server_name:
            del self.servers_dict[original_server_name]
            message = f"Server renamed from '{original_server_name}' to '{new_server_name}' and updated!"
        else:
            message = f"Server '{new_server_name}' updated successfully!"

        # Add the new/updated entry
        self.servers_dict[new_server_name] = server_config
        self.selected_server_name.set(new_server_name)  # Update selected name

        self.load_servers_list()
        # Select the updated server in dropdown
        self.servers_combobox.set(new_server_name)
        messagebox.showinfo("Success", message)

    def remove_server(self):
        """Remove the selected server"""
        server_name = self.servers_combobox.get()
        if not server_name:
            messagebox.showerror("Error", "Please select a server to remove.")
            return

        confirm = messagebox.askyesno("Confirm", f"Are you sure you want to remove server '{server_name}'?")
        if confirm:
            del self.servers_dict[server_name]
            self.load_servers_list()
            self.clear_server_fields()
            messagebox.showinfo("Success", f"Server '{server_name}' removed successfully!")

    def clear_server_fields(self):
        """Clear all server configuration fields"""
        self.server_name.set("")
        self.rcon_host.set("")
        self.rcon_port.set("")
        self.rcon_password.set("")
        self.install_dir.set("")
        self.selected_server_name.set("")
        self.servers_combobox.set("")  # Clear dropdown selection

    # ========================================================================
    # CONFIGURATION LOAD/SAVE METHODS
    # ========================================================================
    def load_configs_and_show_info(self):
        """Reload configuration and show success message"""
        self.load_configs()
        messagebox.showinfo("Success", "Configuration reloaded successfully!")

    def load_configs(self):
        """Load all configuration from files"""
        try:
            with open(SERVERS_FILE, 'r', encoding='utf-8') as f:
                servers_data = json.load(f)

                # Load all servers
                self.servers_dict = servers_data.get("servers", {})
                self.load_servers_list()

                # Load Discord Server ID and theme from DefaultServer if exists
                default_server = self.servers_dict.get("DefaultServer", {})
                self.discord_server_id.set(default_server.get("DISCORD_SERVER_ID", ""))

                # Load theme
                saved_theme = default_server.get("THEME", self.style.theme_use())
                self.selected_theme.set(saved_theme)
                self.style.theme_use(saved_theme)

                # Load BotSettings
                bot_settings = servers_data.get("BotSettings", {})
                self.command_prefix.set(bot_settings.get("COMMAND_PREFIX", "!"))
                self.admin_log_channel_id.set(str(bot_settings.get("ADMIN_LOG_CHANNEL_ID", 0)))
                self.game_chat_channel_id.set(str(bot_settings.get("GAME_CHAT_CHANNEL_ID", 0)))
                self.staff_role_name.set(bot_settings.get("STAFF_ROLE_NAME", "Staff"))
                self.ticket_category_name.set(bot_settings.get("TICKET_CATEGORY_NAME", "Tickets"))
                self.enable_rcon_monitoring.set(bot_settings.get("ENABLE_RCON_CHAT_MONITORING", True))
                self.word_filter_timeout.set(str(bot_settings.get("WORD_FILTER_TIMEOUT_MINUTES", 5)))

                # Load XP settings
                xp_range = bot_settings.get("XP_RANGE", [5, 10])
                self.xp_min.set(str(xp_range[0]))
                self.xp_max.set(str(xp_range[1]))
                self.xp_cooldown.set(str(bot_settings.get("XP_COOLDOWN_SECONDS", 60)))
                self.level_xp_base.set(str(bot_settings.get("LEVEL_XP_BASE", 100)))

                # Load Cross-Chat Roles
                self.cross_chat_roles_list = bot_settings.get("CROSS_CHAT_ROLES", ["Game Chat", "admin", "staff", "owner"])
                self.load_cross_chat_roles()

                # Load Role Rewards
                role_rewards = bot_settings.get("ROLE_REWARDS", {5: "Veteran", 10: "Elite", 20: "Legend"})
                self.role_rewards_dict = {int(k): v for k, v in role_rewards.items()}
                self.load_role_rewards()

        except (FileNotFoundError, json.JSONDecodeError):
            pass

        load_dotenv(dotenv_path=ENV_FILE)
        self.discord_token.set(os.getenv("DISCORD_TOKEN", ""))

        self.load_forbidden_words()
        self.load_moderated_channels()
        self.load_roles()
        self.load_staff_roles()

    def save_configs(self):
        try:
            servers_data = {}
            if os.path.exists(SERVERS_FILE):
                with open(SERVERS_FILE, 'r', encoding='utf-8') as f:
                    servers_data = json.load(f)

            # Save all servers from servers_dict
            servers_data["servers"] = self.servers_dict

            # Save Discord Server ID and Theme to DefaultServer (or first server if DefaultServer doesn't exist)
            if "DefaultServer" in self.servers_dict:
                servers_data["servers"]["DefaultServer"]["DISCORD_SERVER_ID"] = self.discord_server_id.get()
                servers_data["servers"]["DefaultServer"]["THEME"] = self.selected_theme.get()
            elif self.servers_dict:
                # If no DefaultServer, save to first available server
                first_server = list(self.servers_dict.keys())[0]
                servers_data["servers"][first_server]["DISCORD_SERVER_ID"] = self.discord_server_id.get()
                servers_data["servers"][first_server]["THEME"] = self.selected_theme.get()

            # Save BotSettings
            servers_data.setdefault("BotSettings", {})
            servers_data["BotSettings"]["COMMAND_PREFIX"] = self.command_prefix.get()
            servers_data["BotSettings"]["ADMIN_LOG_CHANNEL_ID"] = int(self.admin_log_channel_id.get()) if self.admin_log_channel_id.get().isdigit() else 0
            servers_data["BotSettings"]["GAME_CHAT_CHANNEL_ID"] = int(self.game_chat_channel_id.get()) if self.game_chat_channel_id.get().isdigit() else 0
            servers_data["BotSettings"]["ENABLE_RCON_CHAT_MONITORING"] = self.enable_rcon_monitoring.get()
            servers_data["BotSettings"]["STAFF_ROLE_NAME"] = self.staff_role_name.get()
            servers_data["BotSettings"]["TICKET_CATEGORY_NAME"] = self.ticket_category_name.get()
            servers_data["BotSettings"]["CHAT_LOOP_SERVER_NAME"] = "DefaultServer"
            servers_data["BotSettings"]["CROSS_CHAT_ROLES"] = self.cross_chat_roles_list
            servers_data["BotSettings"]["XP_RANGE"] = [int(self.xp_min.get()), int(self.xp_max.get())]
            servers_data["BotSettings"]["XP_COOLDOWN_SECONDS"] = int(self.xp_cooldown.get())
            servers_data["BotSettings"]["LEVEL_XP_BASE"] = int(self.level_xp_base.get())
            servers_data["BotSettings"]["WORD_FILTER_TIMEOUT_MINUTES"] = int(self.word_filter_timeout.get())
            servers_data["BotSettings"]["ROLE_REWARDS"] = {int(k): v for k, v in self.role_rewards_dict.items()}
            servers_data["BotSettings"]["DEFAULT_POLL_EMOJIS"] = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

            with open(SERVERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(servers_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")
            return

        try:
            set_key(ENV_FILE, "DISCORD_TOKEN", self.discord_token.get())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save Discord token: {e}")
            return

        self.save_forbidden_words()
        self.save_moderated_channels()
        self.save_roles()
        self.save_staff_roles()

        messagebox.showinfo("Success", "Configuration saved successfully!")

    # ========================================================================
    # FORBIDDEN WORDS METHODS
    # ========================================================================
    def load_forbidden_words(self):
        try:
            with open(FORBIDDEN_WORDS_FILE, 'r', encoding='utf-8') as f:
                self.forbidden_words_list = json.load(f)
            self.forbidden_words_listbox.delete(0, tk.END)
            for word in self.forbidden_words_list:
                self.forbidden_words_listbox.insert(tk.END, word)
        except (FileNotFoundError, json.JSONDecodeError):
            self.forbidden_words_list = []

    def save_forbidden_words(self):
        with open(FORBIDDEN_WORDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.forbidden_words_list, f, indent=2)

    def add_forbidden_word(self):
        word = self.new_forbidden_word.get().strip()
        if word and word not in self.forbidden_words_list:
            self.forbidden_words_list.append(word)
            self.forbidden_words_listbox.insert(tk.END, word)
            self.new_forbidden_word.set("")

    def remove_forbidden_word(self):
        selected_indices = self.forbidden_words_listbox.curselection()
        if selected_indices:
            index = selected_indices[0]
            word = self.forbidden_words_listbox.get(index)
            self.forbidden_words_list.remove(word)
            self.forbidden_words_listbox.delete(index)

    # ========================================================================
    # MODERATED CHANNELS METHODS
    # ========================================================================
    def load_moderated_channels(self):
        try:
            with open(MODERATED_CHANNELS_FILE, 'r', encoding='utf-8') as f:
                self.moderated_channel_ids_list = json.load(f)
            self.moderated_channels_listbox.delete(0, tk.END)
            for channel_id in self.moderated_channel_ids_list:
                self.moderated_channels_listbox.insert(tk.END, channel_id)
        except (FileNotFoundError, json.JSONDecodeError):
            self.moderated_channel_ids_list = []

    def save_moderated_channels(self):
        with open(MODERATED_CHANNELS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.moderated_channel_ids_list, f, indent=2)

    def add_moderated_channel(self):
        channel_id = self.new_moderated_channel_id.get().strip()
        if channel_id.isdigit() and channel_id not in self.moderated_channel_ids_list:
            self.moderated_channel_ids_list.append(channel_id)
            self.moderated_channels_listbox.insert(tk.END, channel_id)
            self.new_moderated_channel_id.set("")

    def remove_moderated_channel(self):
        selected_indices = self.moderated_channels_listbox.curselection()
        if selected_indices:
            index = selected_indices[0]
            channel_id = self.moderated_channels_listbox.get(index)
            self.moderated_channel_ids_list.remove(channel_id)
            self.moderated_channels_listbox.delete(index)

    # ========================================================================
    # ADMIN ROLES METHODS
    # ========================================================================
    def load_roles(self):
        try:
            with open(ROLES_FILE, 'r', encoding='utf-8') as f:
                self.roles_list = json.load(f)
            self.roles_listbox.delete(0, tk.END)
            for role in self.roles_list:
                self.roles_listbox.insert(tk.END, role)
        except (FileNotFoundError, json.JSONDecodeError):
            self.roles_list = []
    
    def save_roles(self):
        with open(ROLES_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.roles_list, f, indent=2)

    def add_role(self):
        role = self.new_role.get().strip()
        if role and role not in self.roles_list:
            self.roles_list.append(role)
            self.roles_listbox.insert(tk.END, role)
            self.new_role.set("")

    def remove_role(self):
        selected_indices = self.roles_listbox.curselection()
        if selected_indices:
            index = selected_indices[0]
            role = self.roles_listbox.get(index)
            self.roles_list.remove(role)
            self.roles_listbox.delete(index)

    # ========================================================================
    # STAFF ROLES METHODS
    # ========================================================================
    def load_staff_roles(self):
        try:
            with open(STAFF_ROLES_FILE, 'r', encoding='utf-8') as f:
                self.staff_roles_list = json.load(f)
            self.staff_roles_listbox.delete(0, tk.END)
            for role in self.staff_roles_list:
                self.staff_roles_listbox.insert(tk.END, role)
        except (FileNotFoundError, json.JSONDecodeError):
            self.staff_roles_list = []
    
    def save_staff_roles(self):
        with open(STAFF_ROLES_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.staff_roles_list, f, indent=2)

    def add_staff_role(self):
        role = self.new_staff_role.get().strip()
        if role and role not in self.staff_roles_list:
            self.staff_roles_list.append(role)
            self.staff_roles_listbox.insert(tk.END, role)
            self.new_staff_role.set("")

    def remove_staff_role(self):
        selected_indices = self.staff_roles_listbox.curselection()
        if selected_indices:
            index = selected_indices[0]
            role = self.staff_roles_listbox.get(index)
            self.staff_roles_list.remove(role)
            self.staff_roles_listbox.delete(index)

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    def invite_bot(self):
        """Generate and open Discord bot invite URL"""
        # Replace 'YOUR_CLIENT_ID' with your bot's actual client ID
        CLIENT_ID = "YOUR_CLIENT_ID"  
        # Common permissions: Read Messages, Send Messages, Embed Links, Attach Files, Manage Channels, Manage Roles
        PERMISSIONS = "8" # Example: Read Messages (1024), Send Messages (2048) -> 1024+2048 = 3072. Check Discord API documentation for full list.
        # A more comprehensive set of permissions might be needed depending on the bot's functionality
        # Example permissions integer for a general-purpose bot: 277025779776 (Administrator) or a more granular set.
        # The '8' is just a placeholder for 'VIEW_CHANNEL'
        
        # A good starting point for common permissions (read, send messages, embed links):
        # 2048 (Send Messages) + 10240 (Embed Links) + 32768 (Attach Files) + 67108864 (Read Message History)
        # = 80448 (approx)
        # For typical admin/mod actions, you might want roles, kick, ban, manage channels etc.
        # A simpler way is to generate the URL in Discord dev portal and paste here.

        if CLIENT_ID == "YOUR_CLIENT_ID":
            messagebox.showerror("Error", "Please replace 'YOUR_CLIENT_ID' in the invite_bot method with your bot's actual client ID from the Discord Developer Portal.")
            return

        invite_url = f"https://discord.com/oauth2/authorize?client_id={CLIENT_ID}&permissions={PERMISSIONS}&scope=bot"
        webbrowser.open(invite_url)
        messagebox.showinfo("Invite Bot", f"Opening Discord invite URL in your browser:\n{invite_url}")

    def change_theme(self, event=None):
        """Change UI theme"""
        selected_theme = self.selected_theme.get()
        self.style.theme_use(selected_theme)

    # ========================================================================
    # CROSS-CHAT ROLES METHODS
    # ========================================================================
    def load_cross_chat_roles(self):
        self.cross_chat_roles_listbox.delete(0, tk.END)
        for role in self.cross_chat_roles_list:
            self.cross_chat_roles_listbox.insert(tk.END, role)

    def add_cross_chat_role(self):
        role = self.new_cross_chat_role.get().strip()
        if role and role not in self.cross_chat_roles_list:
            self.cross_chat_roles_list.append(role)
            self.cross_chat_roles_listbox.insert(tk.END, role)
            self.new_cross_chat_role.set("")

    def remove_cross_chat_role(self):
        selected_indices = self.cross_chat_roles_listbox.curselection()
        if selected_indices:
            index = selected_indices[0]
            role = self.cross_chat_roles_listbox.get(index)
            self.cross_chat_roles_list.remove(role)
            self.cross_chat_roles_listbox.delete(index)

    # ========================================================================
    # ROLE REWARDS METHODS
    # ========================================================================
    def load_role_rewards(self):
        self.role_rewards_listbox.delete(0, tk.END)
        for level, role in sorted(self.role_rewards_dict.items(), key=lambda x: int(x[0])):
            self.role_rewards_listbox.insert(tk.END, f"Level {level} → {role}")

    def add_role_reward(self):
        level = self.new_reward_level.get().strip()
        role = self.new_reward_role.get().strip()
        if level.isdigit() and role:
            self.role_rewards_dict[int(level)] = role
            self.load_role_rewards()
            self.new_reward_level.set("")
            self.new_reward_role.set("")

    def remove_role_reward(self):
        selected_indices = self.role_rewards_listbox.curselection()
        if selected_indices:
            index = selected_indices[0]
            text = self.role_rewards_listbox.get(index)
            # Extract level from "Level X → RoleName" format
            level = int(text.split()[1])
            if level in self.role_rewards_dict:
                del self.role_rewards_dict[level]
                self.load_role_rewards()

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    app = ConfigUI()
    app.mainloop()

