import discord
from discord import app_commands
import asyncio
import customtkinter as ctk
import threading
import os
from pathlib import Path
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import webbrowser
from PIL import Image, ImageTk, ImageDraw
import io
import logging
import requests
import re
import certifi
import sys
from datetime import datetime
import aiohttp
import colorsys

# Logger setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("DiscordBot")

# Set certificate paths
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

# Encoded sensitive data
PASTEBIN_URL = "aHR0cHM6Ly9wYXN0ZWJpbi5jb20vcmF3L1hBSFR1VUdL"
DISCORD_INVITE = "aHR0cHM6Ly9kaXNjb3JkLmdnL1ItRQ=="
LOGO_URL = "aHR0cHM6Ly9tZWRpYS5kaXNjb3JkYXBwLm5ldC9hdHRhY2htZW50cy8xMzY1MzY3NzIxNDU3NDgzODA2LzEzNjY3MTE1MzE2ODUwMjM3NzUvNDNfMjAyNTAyMjcwNzIyMjEucG5nP2V4PTY4MTFmMGNkJmlzPTY4MTA5ZjRkJmhtPWQ4YWQwOTY2OGM0ODBjMGJhYmRjOWIzYWEyY2ZhNGJkNzY4NjMwY2Q5YjAzODhhN2U1OWUzMjEzNDE0ZTgxZGImJndpZHRoPTk2MCZoZWlnaHQ9OTYw"
DISCORD_ICON = "aHR0cHM6Ly9pbWcuaWNvbnM4LmNvbS9pb3MtZmlsbGVkLzUwL2ZmZmZmZi9kaXNjb3JkLWxvZ28ucG5n"
TRASH_ICON = "aHR0cHM6Ly9pbWcuaWNvbnM4LmNvbS9pb3MtZmlsbGVkLzUwL2ZmZmZmZi90cmFzaC5wbmc="
THUMBNAIL_URL = "aHR0cHM6Ly9tZWRpYS5kaXNjb3JkYXBwLm5ldC9hdHRhY2htZW50cy8xMzY1MzY3NzIxNDU3NDgzODA2LzEzNjY3MTE1MzE2ODUwMjM3NzUvNDNfMjAyNTAyMjcwNzIyMjEucG5n"
IMAGE_URL = "aHR0cHM6Ly9tZWRpYS5kaXNjb3JkYXBwLm5ldC9hdHRhY2htZW50cy8xMzA0MTA3MjY2ODY5NDMyMzYyLzEzNjI3MTYyNDMwOTgwNzUyMjcvSU1HXzIyNTgucG5n"
CREDIT_TEXT = base64.b64encode("Developed by NitWit | discord.gg/nww".encode()).decode()

# File paths
LOG_FILE = Path.home() / "bot_log.json"
TOKEN_FILE = Path.home() / "bot_tokens.json"

# Bot storage
bots = {}

def decode_data(encoded):
    try:
        return base64.b64decode(encoded).decode('utf-8')
    except Exception as e:
        logger.error(f"Decode error: {str(e)}")
        return None

def generate_key():
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'secret_salt',
        iterations=200000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(b"secret_key"))
    return Fernet(key)

def encrypt_data(data, fernet):
    return fernet.encrypt(data.encode()).decode()

def decrypt_data(data, fernet):
    return fernet.decrypt(data.encode()).decode()

def save_tokens(tokens):
    if not tokens:
        return
    fernet = generate_key()
    data = {"tokens": [encrypt_data(token, fernet) for token in tokens]}
    with open(TOKEN_FILE, 'w') as f:
        json.dump(data, f)

def load_tokens():
    if not TOKEN_FILE.exists():
        return []
    with open(TOKEN_FILE, 'r') as f:
        data = json.load(f)
    fernet = generate_key()
    try:
        return [decrypt_data(token, fernet) for token in data.get("tokens", [])]
    except:
        return []

def log_message(user_id, message):
    try:
        logs = []
        if LOG_FILE.exists():
            with open(LOG_FILE, 'r') as f:
                logs = json.load(f)
        
        log_entry = {
            "user_id": user_id,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        logs.append(log_entry)
        
        with open(LOG_FILE, 'w') as f:
            json.dump(logs, f, indent=2)
        logger.info(f"Logged message from user {user_id}: {message}")
    except Exception as e:
        logger.error(f"Log error: {str(e)}")

async def send_multiple_messages(interaction, message, count, client):
    sent_count = 0
    for _ in range(count):
        try:
            await interaction.followup.send(message, ephemeral=False)
            sent_count += 1
            await asyncio.sleep(0.1)
        except discord.errors.HTTPException as e:
            if e.status == 429:
                retry_after = e.retry_after if hasattr(e, 'retry_after') else 5.0
                logger.warning(f"Rate limit hit, waiting {retry_after} seconds")
                await asyncio.sleep(retry_after)
                continue
            else:
                logger.error(f"Error sending message: {str(e)}")
                break
        except Exception as e:
            logger.error(f"Unexpected error sending message: {str(e)}")
            break

    await interaction.followup.send(f"✅ تم إرسال {sent_count} رسائل بنجاح!", ephemeral=True)
    return sent_count

def create_bot(token):
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    client = discord.Client(intents=intents)
    command_tree = app_commands.CommandTree(client)

    @client.event
    async def on_ready():
        logger.info(f'dis.gg/nww - Bot {client.user} is working')
        await command_tree.sync()
        if bot_manager:
            bot_manager.update_status(token, f"Connected as {client.user}", "#1E90FF")
            bot_manager.log_message(token, f"Bot connected: {client.user}")

    @command_tree.command(name="sendmessage", description="إرسال رسالة تفاعلية باستخدام أزرار مخصصة")
    @app_commands.describe(message="الرسالة التي سيتم إرسالها عند النقر على الأزرار")
    async def send_message(interaction: discord.Interaction, message: str):
        log_message(interaction.user.id, message)
        
        embed = discord.Embed(
            title="✨ لوحة التحكم بالرسائل",
            description="استخدم الأزرار أدناه لإرسال رسالتك!",
            color=discord.Color.from_rgb(30, 144, 255),
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_thumbnail(url=decode_data(THUMBNAIL_URL))
        embed.add_field(name="📜 الرسالة", value=f"```{message}```", inline=False)
        embed.add_field(name="🌐 انضم إلينا", value=f"[اضغط هنا]({decode_data(DISCORD_INVITE)})", inline=False)
        embed.set_footer(text=decode_data(CREDIT_TEXT), icon_url=client.user.avatar.url if client.user.avatar else None)
        embed.set_image(url=decode_data(IMAGE_URL))

        view = MessageView(interaction.user.id, message, client)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        logger.info(f"Sendmessage command used by {interaction.user} for bot {client.user}")

    return client, command_tree

class MessageView(discord.ui.View):
    def __init__(self, user_id, message, client):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.message = message
        self.client = client

    @discord.ui.button(label="إرسال رسالة واحدة", style=discord.ButtonStyle.blurple, emoji="📨")
    async def send_single(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("🚫 هذا الزر مخصص لمن أصدر الأمر فقط!", ephemeral=True)
            return
        await interaction.response.send_message(self.message)
        logger.info(f"Sent single message by {interaction.user} for bot {self.client.user}")

    @discord.ui.button(label="إرسال 5 رسائل", style=discord.ButtonStyle.green, emoji="📬")
    async def send_five(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("🚫 هذا الزر مخصص لمن أصدر الأمر فقط!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        sent_count = await send_multiple_messages(interaction, self.message, 5, self.client)
        logger.info(f"Sent {sent_count} messages by {interaction.user} for bot {self.client.user}")

    @discord.ui.button(label="إرسال 50 رسالة", style=discord.ButtonStyle.red, emoji="📢")
    async def send_fifty(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚫 هذا الزر مخصص للإدارة فقط!", ephemeral=True)

def adjust_color(hex_color, factor=0.8):
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(rgb[0]/255, rgb[1]/255, rgb[2]/255)
    l = max(0, l * factor)
    rgb_new = colorsys.hls_to_rgb(h, l, s)
    return '#{:02x}{:02x}{:02x}'.format(int(rgb_new[0]*255), int(rgb_new[1]*255), int(rgb_new[2]*255))

def create_rounded_image(image, size=(40, 40)):
    image = image.resize(size, Image.LANCZOS)
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    output = Image.new('RGBA', size, (0, 0, 0, 0))
    output.paste(image, (0, 0), mask)
    return output

def fetch_bot_avatar(token):
    try:
        intents = discord.Intents.default()
        client = discord.Client(intents=intents)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(client.login(token))
            avatar_url = client.user.avatar.url if client.user.avatar else None
            loop.run_until_complete(client.close())
            if avatar_url:
                response = requests.get(avatar_url, verify=certifi.where())
                if response.status_code == 200:
                    return Image.open(io.BytesIO(response.content))
            return None
        finally:
            if not loop.is_closed():
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
    except Exception as e:
        logger.warning(f"Failed to fetch bot avatar: {str(e)}")
        return None

class BotManager:
    def __init__(self, root):
        self.root = root
        self.root.title("NitWit Multi-Bot Control")
        self.root.geometry("900x650")
        self.root.resizable(False, False)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        logo_url = decode_data(LOGO_URL)
        try:
            response = requests.get(logo_url, verify=certifi.where()).content
            logo = Image.open(io.BytesIO(response)).resize((64, 64), Image.LANCZOS)
            logo_photo = ImageTk.PhotoImage(logo)
            self.root.iconphoto(False, logo_photo)
        except:
            logger.warning("Failed to load window icon")

        self.main_frame = ctk.CTkFrame(self.root, corner_radius=0, fg_color="#0B0E18")
        self.main_frame.pack(fill="both", expand=True)

        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="#141622", corner_radius=8)
        self.header_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        self.header_left = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.header_left.pack(side="left", padx=15)
        self.title_label = ctk.CTkLabel(
            self.header_left,
            text="NitWit Multi-Bot Control",
            font=ctk.CTkFont("Inter", 26, "bold"),
            text_color="#E5E7EB"
        )
        self.title_label.pack(anchor="w")
        self.subtitle_label = ctk.CTkLabel(
            self.header_left,
            text="Manage your Discord bots with a modern interface",
            font=ctk.CTkFont("Inter", 13),
            text_color="#9CA3AF"
        )
        self.subtitle_label.pack(anchor="w")

        self.header_right = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.header_right.pack(side="right", padx=15)
        
        discord_icon_url = decode_data(DISCORD_ICON)
        try:
            response = requests.get(discord_icon_url, verify=certifi.where()).content
            icon = Image.open(io.BytesIO(response)).resize((28, 28), Image.LANCZOS)
            discord_image = ctk.CTkImage(icon, size=(28, 28))
            self.discord_button = ctk.CTkButton(
                self.header_right,
                text="",
                image=discord_image,
                command=lambda: webbrowser.open(decode_data(DISCORD_INVITE)),
                corner_radius=8,
                width=45,
                height=45,
                fg_color="#4B5563",
                hover_color=adjust_color("#4B5563"),
                border_width=0
            )
            self.discord_button.pack(side="left", padx=5)
            self.add_button_effects(self.discord_button)
        except:
            logger.warning("Failed to load Discord icon")

        server_logo_url = decode_data(LOGO_URL)
        try:
            response = requests.get(server_logo_url, verify=certifi.where()).content
            logo = create_rounded_image(Image.open(io.BytesIO(response)), (50, 50))
            server_image = ctk.CTkImage(logo, size=(50, 50))
            self.server_logo = ctk.CTkLabel(
                self.header_right,
                text="",
                image=server_image
            )
            self.server_logo.pack(side="right", padx=5)
        except:
            logger.warning("Failed to load server logo")

        self.content_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=15, pady=10)

        self.left_panel = ctk.CTkFrame(self.content_frame, corner_radius=12, fg_color="#141622")
        self.left_panel.pack(side="left", fill="y", padx=(0, 10), expand=False, ipadx=10, ipady=10)

        self.token_frame = ctk.CTkFrame(self.left_panel, corner_radius=10, fg_color="#1E212F", border_width=1, border_color="#2A2D3E")
        self.token_frame.pack(pady=10, padx=15, fill="x")
        self.token_label = ctk.CTkLabel(
            self.token_frame,
            text="Add New Bot Token",
            font=ctk.CTkFont("Inter", 12, "bold"),
            text_color="#E5E7EB"
        )
        self.token_label.pack(anchor="w", padx=15, pady=(10, 5))
        self.token_entry = ctk.CTkEntry(
            self.token_frame,
            show="*",
            font=ctk.CTkFont("Inter", 12),
            width=260,
            height=35,
            corner_radius=8,
            fg_color="#2A2D3E",
            border_color="#1E90FF",
            placeholder_text="Enter bot token",
            text_color="#E5E7EB"
        )
        self.token_entry.pack(pady=(0, 5), padx=15, fill="x")
        self.add_token_button = ctk.CTkButton(
            self.token_frame,
            text="Add Token",
            font=ctk.CTkFont("Inter", 12, "bold"),
            command=self.add_token,
            corner_radius=8,
            height=35,
            fg_color="#1E90FF",
            hover_color=adjust_color("#1E90FF"),
            text_color="#E5E7EB"
        )
        self.add_token_button.pack(pady=(5, 5), padx=15, fill="x")
        self.start_all_button = ctk.CTkButton(
            self.token_frame,
            text="Start All Bots",
            font=ctk.CTkFont("Inter", 12, "bold"),
            command=self.start_all_bots,
            corner_radius=8,
            height=35,
            fg_color="#1E90FF",
            hover_color=adjust_color("#1E90FF"),
            text_color="#E5E7EB"
        )
        self.start_all_button.pack(pady=(5, 10), padx=15, fill="x")

        self.bots_frame = ctk.CTkFrame(self.left_panel, corner_radius=10, fg_color="#1E212F", border_width=1, border_color="#2A2D3E")
        self.bots_frame.pack(pady=10, padx=15, fill="both", expand=True)
        self.bots_label = ctk.CTkLabel(
            self.bots_frame,
            text="Active Bots",
            font=ctk.CTkFont("Inter", 12, "bold"),
            text_color="#E5E7EB"
        )
        self.bots_label.pack(anchor="w", padx=15, pady=(10, 5))
        self.bots_scroll = ctk.CTkScrollableFrame(self.bots_frame, fg_color="transparent")
        self.bots_scroll.pack(pady=5, padx=15, fill="both", expand=True)
        self.bot_widgets = {}

        self.right_panel = ctk.CTkFrame(self.content_frame, corner_radius=12, fg_color="#141622")
        self.right_panel.pack(side="right", fill="both", expand=True, ipadx=10, ipady=10)

        self.log_frame = ctk.CTkFrame(self.right_panel, corner_radius=10, fg_color="#1E212F", border_width=1, border_color="#2A2D3E")
        self.log_frame.pack(pady=10, padx=15, fill="both", expand=True)
        self.log_label = ctk.CTkLabel(
            self.log_frame,
            text="Activity Log",
            font=ctk.CTkFont("Inter", 12, "bold"),
            text_color="#E5E7EB"
        )
        self.log_label.pack(anchor="w", padx=15, pady=(10, 5))
        self.log_text = ctk.CTkTextbox(
            self.log_frame,
            font=ctk.CTkFont("Fira Code", 11),
            height=450,
            corner_radius=8,
            fg_color="#2A2D3E",
            text_color="#E5E7EB",
            wrap="word",
            state="disabled"
        )
        self.log_text.pack(pady=5, padx=15, fill="both", expand=True)
        self.clear_log_button = ctk.CTkButton(
            self.log_frame,
            text="Clear Log",
            font=ctk.CTkFont("Inter", 11, "bold"),
            command=self.clear_log,
            corner_radius=8,
            width=80,
            height=30,
            fg_color="#4B5563",
            hover_color=adjust_color("#4B5563"),
            text_color="#E5E7EB"
        )
        self.clear_log_button.pack(pady=(0, 10), padx=15, anchor="e")

        self.footer_frame = ctk.CTkFrame(self.main_frame, fg_color="#141622", corner_radius=8)
        self.footer_frame.pack(fill="x", padx=15, pady=10)
        self.footer_label = ctk.CTkLabel(
            self.footer_frame,
            text=f"✨ {decode_data(CREDIT_TEXT)} ✨",
            font=ctk.CTkFont("Inter", 12, "bold"),
            text_color="#1E90FF",
            cursor="hand2"
        )
        self.footer_label.pack(anchor="center", pady=10)
        self.footer_label.bind("<Button-1>", lambda e: webbrowser.open(decode_data(DISCORD_INVITE)))

        saved_tokens = load_tokens()
        for token in saved_tokens:
            self.add_token(token)

        self.add_button_effects(self.add_token_button)
        self.add_button_effects(self.start_all_button)
        self.add_button_effects(self.clear_log_button)

    def add_button_effects(self, button, scale_effect=False):
        original_color = button.cget("fg_color")
        hover_color = button.cget("hover_color") if button.cget("hover_color") else adjust_color(original_color)

        def on_enter(e):
            if button.cget("text") in ["Start", "Stop"]:
                return
            button.configure(fg_color=hover_color, text_color="#FFFFFF")
            button.scale = 1.05
            self.root.after(10, lambda: button.configure(cursor="hand2"))

        def on_leave(e):
            if button.cget("text") in ["Start", "Stop"]:
                return
            button.configure(fg_color=original_color, text_color="#E5E7EB")
            button.scale = 1.0
            self.root.after(10, lambda: button.configure(cursor=""))

        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)

    def add_token(self, token=None):
        if not token:
            token = self.token_entry.get().strip()
            self.token_entry.delete(0, "end")
        
        if not token or len(token) < 50 or not re.match(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", token):
            self.log_message("all", "❌ Invalid bot token format! Must be a valid Discord bot token.")
            return
        
        if token in bots:
            self.log_message("all", "⚠️ Token already added!")
            return

        client, command_tree = create_bot(token)
        bots[token] = {
            "client": client,
            "loop": None,
            "running": False,
            "command_tree": command_tree
        }

        bot_frame = ctk.CTkFrame(self.bots_scroll, fg_color="#2A2D3E", corner_radius=8)
        bot_frame.pack(pady=5, padx=5, fill="x")
        
        top_frame = ctk.CTkFrame(bot_frame, fg_color="transparent")
        top_frame.pack(fill="x", padx=10, pady=(5, 0))
        
        avatar = fetch_bot_avatar(token)
        if avatar:
            avatar = create_rounded_image(avatar, (30, 30))
            avatar_image = ctk.CTkImage(avatar, size=(30, 30))
        else:
            avatar_image = None
        avatar_label = ctk.CTkLabel(
            top_frame,
            text="",
            image=avatar_image,
            width=30,
            height=30
        )
        avatar_label.pack(side="left", padx=5)
        
        token_label = ctk.CTkLabel(
            top_frame,
            text=f"Token: {token[:10]}...",
            font=ctk.CTkFont("Inter", 10),
            text_color="#E5E7EB"
        )
        token_label.pack(side="left", padx=5)
        
        status_frame = ctk.CTkFrame(bot_frame, fg_color="transparent")
        status_frame.pack(fill="x", padx=10, pady=(0, 5))
        status_indicator = ctk.CTkLabel(
            status_frame,
            text="●",
            font=ctk.CTkFont("Inter", 11),
            text_color="#FF4040",
            width=12
        )
        status_indicator.pack(side="left", padx=5)
        status_label = ctk.CTkLabel(
            status_frame,
            text="Idle",
            font=ctk.CTkFont("Inter", 10),
            text_color="#9CA3AF"
        )
        status_label.pack(side="left")
        
        button_frame = ctk.CTkFrame(bot_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=10, pady=(0, 5))
        start_button = ctk.CTkButton(
            button_frame,
            text="Start",
            font=ctk.CTkFont("Inter", 10, "bold"),
            command=lambda: self.toggle_bot(token),
            corner_radius=6,
            width=150,
            height=22,
            fg_color="#1E90FF",
            text_color="#E5E7EB"
        )
        start_button.pack(side="left", padx=5)
        
        try:
            response = requests.get(decode_data(TRASH_ICON), verify=certifi.where()).content
            trash_icon = Image.open(io.BytesIO(response)).resize((16, 16), Image.LANCZOS)
            trash_image = ctk.CTkImage(trash_icon, size=(16, 16))
            delete_button = ctk.CTkButton(
                button_frame,
                text="",
                image=trash_image,
                command=lambda: self.remove_token(token),
                corner_radius=6,
                width=40,
                height=22,
                fg_color="#4B5563",
                hover_color=adjust_color("#4B5563")
            )
        except:
            logger.warning("Failed to load trash icon, using emoji instead")
            delete_button = ctk.CTkButton(
                button_frame,
                text="🗑️",
                font=ctk.CTkFont("Inter", 10, "bold"),
                command=lambda: self.remove_token(token),
                corner_radius=6,
                width=40,
                height=22,
                fg_color="#4B5563",
                hover_color=adjust_color("#4B5563")
            )
        delete_button.pack(side="left", padx=5)

        self.bot_widgets[token] = {
            "frame": bot_frame,
            "indicator": status_indicator,
            "status": status_label,
            "start_button": start_button,
            "delete_button": delete_button,
            "avatar": avatar_label
        }

        save_tokens(list(bots.keys()))
        self.log_message("all", f"✅ Added token: {token[:10]}...")
        
        self.add_button_effects(start_button)
        self.add_button_effects(delete_button)

    def remove_token(self, token):
        if token not in bots:
            return
        
        if bots[token]["running"]:
            self.stop_bot(token)
        
        self.bot_widgets[token]["frame"].destroy()
        del self.bot_widgets[token]
        
        del bots[token]
        
        save_tokens(list(bots.keys()))
        self.log_message("all", f"🗑️ Removed token: {token[:10]}...")

    def update_status(self, token, status, color):
        if token in self.bot_widgets:
            self.bot_widgets[token]["status"].configure(text=status)
            self.bot_widgets[token]["indicator"].configure(text_color=color)

    def log_message(self, token, message):
        self.log_text.configure(state="normal")
        target = "All Bots" if token == "all" else f"Bot {token[:10]}..."
        self.log_text.insert("end", f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {target}: {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_message("all", "🧹 Log cleared")
        self.log_text.configure(state="disabled")

    def toggle_bot(self, token):
        if token not in bots:
            return
        
        if not bots[token]["running"]:
            self.start_bot(token)
        else:
            self.stop_bot(token)

    def start_bot(self, token):
        if token not in bots or bots[token]["running"]:
            self.log_message(token, "⚠️ Bot is already running!")
            return
        
        if bots[token]["client"].is_closed():
            bots[token]["client"], bots[token]["command_tree"] = create_bot(token)
        
        bots[token]["loop"] = asyncio.new_event_loop()
        bots[token]["running"] = True
        self.bot_widgets[token]["start_button"].configure(
            text="Stop",
            fg_color="#FF4040",
            text_color="#E5E7EB"
        )
        self.update_status(token, "Starting...", "#FFD700")
        self.log_message(token, "🚀 Starting bot")
        threading.Thread(target=self.run_bot, args=(token,), daemon=True).start()

    def run_bot(self, token):
        asyncio.set_event_loop(bots[token]["loop"])
        try:
            logger.info(f"Attempting to start bot with token {token[:10]}...")
            bots[token]["loop"].run_until_complete(bots[token]["client"].start(token))
        except Exception as e:
            logger.error(f"Failed to start bot {token[:10]}...: {str(e)}")
            self.root.after(0, lambda: self.log_message(token, f"❌ Failed to start bot: {str(e)}"))
            self.root.after(0, lambda: self.reset_bot(token))
        finally:
            bots[token]["running"] = False
            if bots[token]["loop"] and not bots[token]["loop"].is_closed():
                logger.info(f"Closing event loop for bot {token[:10]}...")
                bots[token]["loop"].run_until_complete(bots[token]["loop"].shutdown_asyncgens())
                bots[token]["loop"].close()
            bots[token]["loop"] = None
            self.root.after(0, lambda: self.reset_bot(token))

    def stop_bot(self, token):
        if token not in bots or not bots[token]["running"]:
            self.log_message(token, "⚠️ Bot is not running!")
            return
        
        self.update_status(token, "Stopping...", "#FFD700")
        self.log_message(token, "🛑 Stopping bot")
        self.bot_widgets[token]["start_button"].configure(
            text="Start",
            fg_color="#1E90FF",
            text_color="#E5E7EB"
        )
        if bots[token]["loop"] and not bots[token]["loop"].is_closed():
            asyncio.run_coroutine_threadsafe(bots[token]["client"].close(), bots[token]["loop"])
        self.update_status(token, "Idle", "#FF4040")

    def start_all_bots(self):
        if not bots:
            self.log_message("all", "⚠️ No bots added!")
            return
        for token in bots:
            if not bots[token]["running"]:
                self.start_bot(token)
        self.log_message("all", "🚀 Starting all bots...")

    def reset_bot(self, token):
        if token in self.bot_widgets:
            self.bot_widgets[token]["start_button"].configure(
                text="Start",
                fg_color="#1E90FF",
                text_color="#E5E7EB"
            )
            self.update_status(token, "Idle", "#FF4040")

if __name__ == "__main__":
    root = ctk.CTk()
    bot_manager = BotManager(root)
    root.mainloop()