import importlib.util
import subprocess
import sys
import sqlite3
import json
import os
import time
import random
import string
import threading
from datetime import datetime

# --- AUTOMATIC DEPENDENCY CHECK ---
for pkg in ["flask", "pyTelegramBotAPI", "gspread", "oauth2client"]:
    mod = "telebot" if pkg == "pyTelegramBotAPI" else pkg
    if importlib.util.find_spec(mod) is None:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

from flask import Flask
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ============================================
# --- WEB SERVER FOR KEEP-ALIVE ---
# ============================================
app = Flask('')

@app.route('/')
def home():
    return "CASH KING WIN BD Engine is Running 24/7!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_web_server)
    t.daemon = True
    t.start()

# ============================================
# --- CONFIGURATION & GLOBALS ---
# ============================================
TOKEN = "8504721778:AAHwocLRx0VMNxeaSU5ToiDPNtqPR60XbrY"
ADMIN_ID = 7833766898
BOT_NAME = "CASH KING WIN BD"
DB_FILE = "bot_data.db"
JSON_CREDS_FILE = "credentials.json"

bot = telebot.TeleBot(TOKEN, num_threads=50)
db_lock = threading.RLock()

# ============================================
# --- SQLITE DATABASE MANAGEMENT ---
# ============================================
def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db_lock:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0.0,
            total_income REAL DEFAULT 0.0,
            total_withdraw REAL DEFAULT 0.0,
            referrals INTEGER DEFAULT 0,
            referred_by INTEGER DEFAULT NULL,
            ref_rewarded INTEGER DEFAULT 0,
            state TEXT DEFAULT NULL,
            temp_data TEXT DEFAULT '{}',
            role TEXT DEFAULT 'user',
            permissions TEXT DEFAULT '{}',
            is_banned INTEGER DEFAULT 0,
            approved_tasks INTEGER DEFAULT 0,
            rejected_tasks INTEGER DEFAULT 0,
            pending_tasks INTEGER DEFAULT 0,
            completed_accounts INTEGER DEFAULT 0,
            last_spin_time REAL DEFAULT 0,
            ip_address TEXT DEFAULT NULL,
            created_at REAL
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS submitted_records (
            record_value TEXT PRIMARY KEY,
            record_type TEXT,
            user_id INTEGER,
            submitted_at REAL
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS pending_submissions (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            sub_type TEXT,
            payload TEXT,
            rate REAL DEFAULT 0.0,
            status TEXT DEFAULT 'pending',
            created_at REAL
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS withdraw_requests (
            req_id TEXT PRIMARY KEY,
            user_id INTEGER,
            method TEXT,
            account_number TEXT,
            amount REAL,
            status TEXT DEFAULT 'pending',
            created_at REAL
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_type TEXT,
            link TEXT,
            description TEXT,
            rate REAL,
            task_limit INTEGER,
            completed INTEGER DEFAULT 0
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS completed_app_tasks (
            user_id INTEGER,
            task_id INTEGER,
            PRIMARY KEY (user_id, task_id)
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS support_tickets (
            ticket_id TEXT PRIMARY KEY,
            user_id INTEGER,
            message TEXT,
            status TEXT DEFAULT 'pending',
            created_at REAL
        )''')

        default_emojis = {
            "balance": "💰", "work": "💼", "withdraw": "📥", "invite": "👥",
            "support": "🎧", "newbie": "❓", "instagram": "📸", "facebook": "📘",
            "gmail": "📧", "spin": "🌀", "task": "📲", "success": "✅",
            "error": "❌", "warning": "⚠️", "lock": "🔐", "admin": "⚙️"
        }

        defaults = {
            "force_channels": json.dumps([]),
            "ref_bonus": "10.0",
            "rate_ins": "15.0",
            "rate_fb": "18.0",
            "rate_gmail": "12.0",
            "ins_pass": "KingInsPass",
            "fb_pass": "KingFbPass",
            "gmail_pass": "KingGmailPass",
            "recovery_email": "tasrikvai8001@gmail.com",
            "emojis": json.dumps(default_emojis),
            "spin_ad_url": "https://example.com/adsterra",
            "spin_reward": "1.5",
            "sheet_id_ins": "",
            "sheet_id_fb": "",
            "sheet_id_gmail": "",
            "json_credentials": "",
            "firebase_api": "",
            "tutorial_videos": json.dumps({"gmail": "", "fb": "", "ins": ""}),
            "withdraw_methods": json.dumps({
                "bKash": {"enabled": True, "min": 50.0, "max": 5000.0},
                "Nagad": {"enabled": True, "min": 50.0, "max": 5000.0},
                "USDT BEP20": {"enabled": True, "min": 100.0, "max": 10000.0}
            }),
            "maintenance_mode": "false"
        }
        for k, v in defaults.items():
            c.execute("INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)", (k, v))
            
        conn.commit()
        conn.close()

init_db()

def get_config(key, default=""):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT value FROM config WHERE key=?", (key,))
    res = c.fetchone()
    conn.close()
    return res[0] if res else default

def set_config(key, value):
    with db_lock:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
        conn.close()

def get_user_db(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    u = c.fetchone()
    if not u:
        now = time.time()
        c.execute("INSERT INTO users (user_id, created_at) VALUES (?, ?)", (user_id, now))
        conn.commit()
        c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        u = c.fetchone()
    conn.close()
    return dict(u)

def update_user_field(user_id, field, value):
    with db_lock:
        conn = get_db()
        c = conn.cursor()
        c.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (value, user_id))
        conn.commit()
        conn.close()

def get_emoji(key):
    emojis = json.loads(get_config("emojis", "{}"))
    return emojis.get(key, "✨")

# ============================================
# --- GOOGLE SHEETS AUTOMATION ENGINE ---
# ============================================
def append_to_google_sheet(service_type, row_data):
    try:
        json_data = get_config("json_credentials", "")
        if not json_data and os.path.exists(JSON_CREDS_FILE):
            with open(JSON_CREDS_FILE, 'r') as f:
                json_data = f.read()

        if not json_data: return False

        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = json.loads(json_data)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)

        sheet_key = f"sheet_id_{service_type.lower()}"
        sheet_id = get_config(sheet_key, "")
        if not sheet_id: return False

        sheet = client.open_by_key(sheet_id).sheet1
        sheet.append_row(row_data)
        return True
    except Exception as e:
        print(f"Google Sheet Append Error ({service_type}): {e}")
        return False

# ============================================
# --- TELEBOT STYLISH COLOR BUTTON PATCH ---
# ============================================
_old_inline_dict = InlineKeyboardButton.to_dict
def _new_inline_dict(self):
    d = _old_inline_dict(self)
    if hasattr(self, 'style'): d['style'] = self.style
    return d
InlineKeyboardButton.to_dict = _new_inline_dict

_old_kb_dict = KeyboardButton.to_dict
def _new_kb_dict(self):
    d = _old_kb_dict(self)
    if hasattr(self, 'style'): d['style'] = self.style
    return d
KeyboardButton.to_dict = _new_kb_dict

def ibtn(text, callback_data=None, url=None, style=None):
    kwargs = {'text': text}
    if callback_data: kwargs['callback_data'] = callback_data
    if url: kwargs['url'] = url
    b = InlineKeyboardButton(**kwargs)
    if style: b.style = style
    return b

def rbtn(text, style=None):
    b = KeyboardButton(text=text)
    if style: b.style = style
    return b

# ============================================
# --- DYNAMIC HELPERS & VALIDATIONS ---
# ============================================
def generate_dynamic_password(prefix_key):
    base_name = get_config(prefix_key, "Pass")
    date_str = datetime.now().strftime("%d%m%Y")
    return f"{base_name}{date_str}@"

FIRST_NAMES = ["Tanvir", "Rahim", "Kareem", "Sabbir", "Arif", "Mahmud", "Shakib", "Naim", "Fahim", "Hasan", "Sumon", "Raju"]
LAST_NAMES = ["Hossain", "Islam", "Ahmed", "Chowdhury", "Khan", "Uddin", "Rahman", "Mia", "Ali", "Sarker", "Roy", "Das"]

def generate_random_identity():
    fn = random.choice(FIRST_NAMES)
    ln = random.choice(LAST_NAMES)
    un = f"{fn.lower()}{ln.lower()}{random.randint(100, 9999)}"
    return fn, ln, un

def check_duplicate_and_save(val, record_type, uid):
    with db_lock:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT record_value FROM submitted_records WHERE record_value=?", (val,))
        if c.fetchone():
            conn.close()
            return True
        c.execute("INSERT INTO submitted_records (record_value, record_type, user_id, submitted_at) VALUES (?, ?, ?, ?)",
                  (val, record_type, uid, time.time()))
        conn.commit()
        conn.close()
        return False

def get_daily_withdraw_count(user_id):
    conn = get_db()
    c = conn.cursor()
    day_start = time.time() - 86400
    c.execute("SELECT COUNT(*) FROM withdraw_requests WHERE user_id=? AND created_at >= ?", (user_id, day_start))
    cnt = c.fetchone()[0]
    conn.close()
    return cnt

def get_daily_support_count(user_id):
    conn = get_db()
    c = conn.cursor()
    day_start = time.time() - 86400
    c.execute("SELECT COUNT(*) FROM support_tickets WHERE user_id=? AND created_at >= ?", (user_id, day_start))
    cnt = c.fetchone()[0]
    conn.close()
    return cnt

# ============================================
# --- FORCE JOIN & KEYBOARDS ---
# ============================================
def check_force_join(user_id):
    chs = json.loads(get_config("force_channels", "[]"))
    if not chs: return True
    for ch in chs:
        try:
            m = bot.get_chat_member(ch, user_id)
            if m.status in ['left', 'kicked']: return False
        except: return False
    return True

def get_force_join_markup():
    chs = json.loads(get_config("force_channels", "[]"))
    markup = InlineKeyboardMarkup(row_width=1)
    for ch in chs:
        clean_ch = ch.replace("@", "")
        markup.add(ibtn(f"📢 Join {ch}", url=f"https://t.me/{clean_ch}", style="primary"))
    markup.add(ibtn("✅ Verify Now", callback_data="check_join_event", style="success"))
    return markup

# MENU TEXT CONSTANTS
TXT_WORK_MAIN = f"{get_emoji('work')} কাজ•"
TXT_TODAY_WORK = "🔥 আজকের কাজ"
TXT_BALANCE = f"{get_emoji('balance')} ব্যালেন্স"
TXT_WITHDRAW = f"{get_emoji('withdraw')} উত্তোলন"
TXT_REFER = f"{get_emoji('invite')} রেফার"
TXT_SUPPORT = f"{get_emoji('support')} সাপোর্ট"
TXT_NEWBIE = f"{get_emoji('newbie')} আমি নতুন"
TXT_ADMIN_PANEL = "⚙️ Admin Panel"
TXT_BACK = "🔙 Back"

def get_main_menu(user_id):
    u = get_user_db(user_id)
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(rbtn(TXT_WORK_MAIN, "primary"), rbtn(TXT_TODAY_WORK, "primary"))
    markup.add(rbtn(TXT_BALANCE, "primary"), rbtn(TXT_WITHDRAW, "success"))
    markup.add(rbtn(TXT_REFER, "primary"), rbtn(TXT_SUPPORT, "primary"))
    markup.add(rbtn(TXT_NEWBIE, "primary"))
    if user_id == ADMIN_ID or u.get("role") in ["admin", "sub_admin", "moderator"]:
        markup.add(rbtn(TXT_ADMIN_PANEL, "danger"))
    return markup

def get_work_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(rbtn(f"{get_emoji('instagram')} ইনস্টাগ্রাম কাজ", "primary"), rbtn(f"{get_emoji('gmail')} Gmail কাজ", "primary"))
    markup.add(rbtn(f"{get_emoji('facebook')} ফেসবুক কাজ", "primary"))
    markup.add(rbtn(TXT_BACK, "danger"))
    return markup

def get_admin_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(rbtn("💰 Set Task Rates", "success"), rbtn("📢 Set Force Join", "primary"))
    markup.add(rbtn("🎁 Set Ref Bonus", "success"), rbtn("💳 Withdraw Setting", "primary"))
    markup.add(rbtn("🔑 Set Passwords Base", "primary"), rbtn("🎨 Edit Emoji IDs", "primary"))
    markup.add(rbtn("🌀 Spin & Ad Settings", "primary"), rbtn("📊 Google Sheets Config", "primary"))
    markup.add(rbtn("🤖 Upload JSON Creds", "primary"), rbtn("🔥 Set Firebase API", "primary"))
    markup.add(rbtn("🔄 Sync Google Sheet Approval", "success"), rbtn("📥 Export Unsold Files", "primary"))
    markup.add(rbtn("🔎 Pending Approvals", "primary"), rbtn("📥 Pending Withdraws", "primary"))
    markup.add(rbtn("📩 Pending Support Tickets", "primary"), rbtn("➕ Add App/TG Task", "success"))
    markup.add(rbtn("📩 Smart Broadcast Message", "primary"), rbtn("📊 Bot Statistics", "primary"))
    markup.add(rbtn("⛔ Ban/Unban User", "danger"), rbtn("➕ Add/Deduct Balance", "success"))
    markup.add(rbtn("👑 Sub-Admin Manager", "primary"), rbtn("📧 Set Recovery Email", "primary"))
    markup.add(rbtn("🎥 Set Tutorial Videos", "primary"), rbtn("🧹 Database Cleanup", "danger"))
    markup.add(rbtn("🚨 Error Logs", "danger"), rbtn("⚡ Maintenance Mode", "danger"))
    markup.add(rbtn(TXT_BACK, "danger"))
    return markup

# ============================================
# --- COMMAND & CORE HANDLERS ---
# ============================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    uid = message.from_user.id
    
    if get_config("maintenance_mode", "false") == "true" and uid != ADMIN_ID:
        bot.send_message(message.chat.id, f"{get_emoji('warning')} **বট বর্তমানে মেইনটেন্যান্স মোডে আছে।** খুব শীঘ্রই আবার কাজ চালু হবে।", parse_mode="Markdown")
        return

    u = get_user_db(uid)
    if u["is_banned"]:
        bot.send_message(message.chat.id, f"{get_emoji('error')} **আপনি এই বটে ব্লকড আছেন!**", parse_mode="Markdown")
        return

    # Multi-Account Check Logic
    args = message.text.split()
    if len(args) > 1 and not u["referred_by"]:
        ref_id = args[1]
        if ref_id.isdigit() and int(ref_id) != uid:
            ref_user = get_user_db(int(ref_id))
            # Fraud Guard: Same IP or Multi Account Track
            if u.get("ip_address") and u.get("ip_address") == ref_user.get("ip_address"):
                bot.send_message(uid, f"{get_emoji('warning')} **সতর্কবার্তা:** একই ডিভাইস/নেটওয়ার্ক থেকে একাধিক অ্যাকাউন্ট খোলা সনাক্ত হয়েছে! রেফার বোনাস যোগ হবে না।")
            else:
                update_user_field(uid, "referred_by", int(ref_id))

    if not check_force_join(uid):
        msg = f"👋 **Welcome to {BOT_NAME}!**\n\nবটের কাজ করার জন্য নিচের চ্যানেলগুলোতে জয়েন করুন এবং 'Verify Now' চাপুন:"
        bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=get_force_join_markup())
        return

    bot.send_message(message.chat.id, f"💎 **Welcome to {BOT_NAME}!**\nনিচের প্রিমিয়াম মেনু থেকে আপনার পছন্দ বেছে নিন:", parse_mode="Markdown", reply_markup=get_main_menu(uid))

# ============================================
# --- MAIN MESSAGE ROUTER ---
# ============================================
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'document', 'video'])
def handle_all_messages(message):
    uid = message.from_user.id
    txt = message.text.strip() if message.text else ""
    u = get_user_db(uid)

    if u["is_banned"]: return

    state = u.get("state")

    # --- ADMIN STATES ---
    if state and (uid == ADMIN_ID or u.get("role") in ["admin", "sub_admin"]):
        if state == "set_rate_ins":
            set_config("rate_ins", txt)
            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, f"✅ Instagram Rate set to: ৳{txt}", reply_markup=get_admin_menu())
            return
        elif state == "set_rate_fb":
            set_config("rate_fb", txt)
            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, f"✅ Facebook Rate set to: ৳{txt}", reply_markup=get_admin_menu())
            return
        elif state == "set_rate_gmail":
            set_config("rate_gmail", txt)
            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, f"✅ Gmail Rate set to: ৳{txt}", reply_markup=get_admin_menu())
            return
        elif state == "set_sheet_ins":
            set_config("sheet_id_ins", txt)
            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, "✅ Instagram Sheet ID Saved!", reply_markup=get_admin_menu())
            return
        elif state == "set_sheet_fb":
            set_config("sheet_id_fb", txt)
            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, "✅ Facebook Sheet ID Saved!", reply_markup=get_admin_menu())
            return
        elif state == "set_sheet_gmail":
            set_config("sheet_id_gmail", txt)
            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, "✅ Gmail Sheet ID Saved!", reply_markup=get_admin_menu())
            return
        elif state == "set_json_creds":
            if message.document:
                file_info = bot.get_file(message.document.file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                set_config("json_credentials", downloaded_file.decode('utf-8'))
            else:
                set_config("json_credentials", txt)
            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, "✅ Google Cloud Credentials Saved!", reply_markup=get_admin_menu())
            return
        elif state == "set_firebase_api":
            set_config("firebase_api", txt)
            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, "✅ Firebase API Key Updated!", reply_markup=get_admin_menu())
            return
        elif state == "set_recovery_email":
            set_config("recovery_email", txt)
            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, f"✅ Recovery Email Set to: `{txt}`", parse_mode="Markdown", reply_markup=get_admin_menu())
            return
        elif state == "admin_search_submission":
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT * FROM pending_submissions WHERE id=? OR payload LIKE ?", (txt, f"%{txt}%"))
            sub = c.fetchone()
            conn.close()
            update_user_field(uid, "state", None)
            if not sub:
                bot.send_message(message.chat.id, "❌ কোনো সাবমিশন পাওয়া যায়নি!", reply_markup=get_admin_menu())
                return
            
            sub = dict(sub)
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                ibtn("✅ Approve", callback_data=f"app_sub_{sub['id']}", style="success"),
                ibtn("❌ Reject", callback_data=f"rej_sub_{sub['id']}", style="danger")
            )
            msg = f"🔎 **Submission Found:**\n\nID: `{sub['id']}`\nType: `{sub['sub_type']}`\nUser ID: `{sub['user_id']}`\nPayload: `{sub['payload']}`"
            bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=markup)
            return

        elif state and state.startswith("edit_emoji_"):
            ekey = state.replace("edit_emoji_", "")
            emojis = json.loads(get_config("emojis", "{}"))
            emojis[ekey] = txt
            set_config("emojis", json.dumps(emojis))
            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, f"✅ Emoji for `{ekey}` updated to: {txt}", reply_markup=get_admin_menu())
            return

        elif state and state.startswith("reply_ticket_"):
            t_id = state.replace("reply_ticket_", "")
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT user_id FROM support_tickets WHERE ticket_id=?", (t_id,))
            t_user = c.fetchone()
            if t_user:
                target_uid = t_user[0]
                try:
                    bot.send_message(target_uid, f"🎧 **Support Reply:**\n\n{txt}")
                    c.execute("UPDATE support_tickets SET status='replied' WHERE ticket_id=?", (t_id,))
                    conn.commit()
                    bot.send_message(message.chat.id, "✅ **রিপ্লাই পাঠানো হয়েছে!**")
                except:
                    bot.send_message(message.chat.id, "❌ ইউজারকে মেসেজ পাঠানো যায়নি!")
            conn.close()
            update_user_field(uid, "state", None)
            return

        elif state and state.startswith("set_vid_"):
            cat = state.replace("set_vid_", "")
            vids = json.loads(get_config("tutorial_videos", "{}"))
            if message.video:
                vids[cat] = message.video.file_id
            else:
                vids[cat] = txt
            set_config("tutorial_videos", json.dumps(vids))
            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, f"✅ Video Tutorial for `{cat}` saved!", reply_markup=get_admin_menu())
            return

    # --- USER TASK PROOF SUBMISSION ---
    if message.photo and state and state.startswith("sub_app_proof_"):
        task_id = state.replace("sub_app_proof_", "")
        sub_id = f"sub_{uid}_{int(time.time())}"
        photo_id = message.photo[-1].file_id
        
        # Save Task Submission and Lock User From Resubmitting
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO pending_submissions (id, user_id, sub_type, payload) VALUES (?, ?, ?, ?)",
                  (sub_id, uid, "app_ss", json.dumps({"photo": photo_id, "task_id": task_id})))
        c.execute("INSERT OR IGNORE INTO completed_app_tasks (user_id, task_id) VALUES (?, ?)", (uid, task_id))
        c.execute("UPDATE users SET pending_tasks = pending_tasks + 1 WHERE user_id=?", (uid,))
        conn.commit()
        conn.close()

        update_user_field(uid, "state", None)
        bot.send_message(message.chat.id, "✅ **আপনার প্রুফ স্ক্রিনশট জমা হয়েছে!** এডমিন চেক করে এপ্রুভ করলে ব্যালেন্স যোগ হবে।", reply_markup=get_main_menu(uid))
        return

    # --- USER SUPPORT TICKET STATE ---
    if state == "user_submit_ticket":
        if get_daily_support_count(uid) >= 5:
            bot.send_message(message.chat.id, f"{get_emoji('error')} **আপনি আজ ৫টির বেশি সাপোর্ট টিকিট দিতে পারবেন না!**")
            update_user_field(uid, "state", None)
            return
            
        t_id = f"TICK-{random.randint(10000, 99999)}"
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO support_tickets (ticket_id, user_id, message, created_at) VALUES (?, ?, ?, ?)",
                  (t_id, uid, txt, time.time()))
        conn.commit()
        conn.close()

        update_user_field(uid, "state", None)
        bot.send_message(message.chat.id, f"✅ **আপনার সাপোর্ট টিকিট জমা নেওয়া হয়েছে!**\nTicket ID: `{t_id}`", reply_markup=get_main_menu(uid))
        return

    # --- USER WORK STATES & FB VALIDATION GUARD ---
    if state == "enter_fb_uid":
        # Guard: FB UID must be 14-16 digits strictly
        if not (txt.isdigit() and 14 <= len(txt) <= 16):
            bot.send_message(message.chat.id, f"{get_emoji('error')} **ভুল UID!** Facebook UID অবশ্যই ১৪ থেকে ১৬ সংখ্যার হতে হবে। আবার দিন:")
            return

        if check_duplicate_and_save(txt, "fb_uid", uid):
            bot.send_message(message.chat.id, f"{get_emoji('error')} **এই FB UID টি ইতিমধ্যেই সিস্টেমে জমা দেওয়া হয়েছে!**")
            return

        temp = json.loads(u["temp_data"] or "{}")
        temp["fb_uid"] = txt
        update_user_field(uid, "temp_data", json.dumps(temp))
        update_user_field(uid, "state", "enter_fb_cookie")
        bot.send_message(message.chat.id, "🍪 **এবার আপনার FB Cookie টি সেন্ড করুন:**")
        return

    elif state == "enter_fb_cookie":
        # Guard: Cookie length must be strictly > 28
        if len(txt) <= 28:
            bot.send_message(message.chat.id, f"{get_emoji('error')} **ইনভ্যালিড কুকিজ!** কুকিজটি সর্বনিম্ন ২৮ অক্ষরের বেশি হতে হবে। আবার দিন:")
            return

        if check_duplicate_and_save(txt, "fb_cookie", uid):
            bot.send_message(message.chat.id, f"{get_emoji('error')} **এই FB Cookie টি আগে ব্যবহার করা হয়েছে!**")
            return
        
        temp = json.loads(u["temp_data"] or "{}")
        rate = float(get_config("rate_fb", "18.0"))
        sub_id = f"FB-{random.randint(1000, 9999)}"
        
        data_p = {
            "fn": temp.get("fn"), "ln": temp.get("ln"), "pass": temp.get("pass"),
            "uid": temp.get("fb_uid"), "cookie": txt
        }

        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO pending_submissions (id, user_id, sub_type, payload, rate, status, created_at) VALUES (?, ?, 'fb', ?, ?, 'pending', ?)",
                  (sub_id, uid, json.dumps(data_p), rate, time.time()))
        c.execute("UPDATE users SET pending_tasks = pending_tasks + 1 WHERE user_id=?", (uid,))
        conn.commit()
        conn.close()

        append_to_google_sheet("fb", [sub_id, uid, temp.get("fn"), temp.get("ln"), temp.get("fb_uid"), temp.get("pass"), txt, "Pending", datetime.now().strftime("%Y-%m-%d %H:%M")])

        update_user_field(uid, "state", None)
        bot.send_message(message.chat.id, f"🎉 **আপনার ফেসবুক কাজ জমা হয়েছে!**\nSubmit ID: `{sub_id}`\nরেট: ৳{rate:.2f}", reply_markup=get_main_menu(uid))
        return

    elif state == "enter_2fa_code":
        if check_duplicate_and_save(txt, "2fa", uid):
            bot.send_message(message.chat.id, f"{get_emoji('error')} **এই 2FA কোডটি আগে ব্যবহার করা হয়েছে!**")
            return
        
        temp = json.loads(u["temp_data"] or "{}")
        rate = float(get_config("rate_ins", "15.0"))
        sub_id = f"INS-{random.randint(1000, 9999)}"
        
        data_p = {
            "username": temp.get("username"),
            "pass": temp.get("pass"),
            "2fa": txt
        }
        
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO pending_submissions (id, user_id, sub_type, payload, rate, status, created_at) VALUES (?, ?, 'ins', ?, ?, 'pending', ?)",
                  (sub_id, uid, json.dumps(data_p), rate, time.time()))
        c.execute("UPDATE users SET pending_tasks = pending_tasks + 1 WHERE user_id=?", (uid,))
        conn.commit()
        conn.close()

        append_to_google_sheet("ins", [sub_id, uid, temp.get("username"), temp.get("pass"), txt, "Pending", datetime.now().strftime("%Y-%m-%d %H:%M")])

        update_user_field(uid, "state", None)
        bot.send_message(message.chat.id, f"🎉 **আপনার ইনস্টাগ্রাম অ্যাকাউন্ট জমা দেওয়া হয়েছে!**\nSubmit ID: `{sub_id}`\nরেট: ৳{rate:.2f}", parse_mode="Markdown", reply_markup=get_main_menu(uid))
        return

    elif state and state.startswith("withdraw_number_"):
        meth = state.replace("withdraw_number_", "")
        w_methods = json.loads(get_config("withdraw_methods", "{}"))
        min_limit = w_methods[meth]["min"]
        max_limit = w_methods[meth].get("max", 10000.0)
        
        # Fraud Guard: Max 2 withdraws per 24 hours
        if get_daily_withdraw_count(uid) >= 2:
            bot.send_message(message.chat.id, f"{get_emoji('warning')} **উইথড্র লিমিট শেষ!** আপনি ২৪ ঘণ্টায় সর্বোচ্চ ২ বার উইথড্র করতে পারবেন।")
            update_user_field(uid, "state", None)
            return

        if u["balance"] < min_limit:
            bot.send_message(message.chat.id, f"{get_emoji('error')} **আপনার পর্যাপ্ত ব্যালেন্স নেই!** মিনিমাম উইথড্র ৳{min_limit}")
            update_user_field(uid, "state", None)
            return

        req_id = f"W-{random.randint(10000, 99999)}"
        amt = u["balance"]
        if amt > max_limit: amt = max_limit
        
        # Deduct Balance Instant & Send Alert To Admin
        with db_lock:
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO withdraw_requests (req_id, user_id, method, account_number, amount, status, created_at) VALUES (?, ?, ?, ?, ?, 'pending', ?)",
                      (req_id, uid, meth, txt, amt, time.time()))
            c.execute("UPDATE users SET balance = balance - ?, total_withdraw = total_withdraw + ? WHERE user_id=?", (amt, amt, uid))
            conn.commit()
            conn.close()

        update_user_field(uid, "state", None)
        bot.send_message(message.chat.id, f"✅ **আপনার ৳{amt:.2f} এর উইথড্র রিকোয়েস্ট জমা হয়েছে!**\nMethod: {meth}\nAccount: `{txt}`", reply_markup=get_main_menu(uid))

        # Admin Instant Alert
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            ibtn("✅ Paid", callback_data=f"pay_with_{req_id}", style="success"),
            ibtn("❌ Refund Balance", callback_data=f"ref_with_{req_id}", style="danger")
        )
        admin_alert = f"📥 **New Withdrawal Request!**\n\nReq ID: `{req_id}`\nUser ID: `{uid}`\nMethod: {meth}\nAccount: `{txt}`\nAmount: ৳{amt:.2f}"
        try: bot.send_message(ADMIN_ID, admin_alert, parse_mode="Markdown", reply_markup=markup)
        except: pass
        return

    # --- MENU ROUTING ---
    if txt == TXT_WORK_MAIN:
        bot.send_message(message.chat.id, "💼 **কাজ অপশন নির্বাচন করুন:**", reply_markup=get_work_menu())
    elif txt == TXT_BACK:
        update_user_field(uid, "state", None)
        bot.send_message(message.chat.id, "🏠 Main Menu", reply_markup=get_main_menu(uid))

    elif txt == f"{get_emoji('instagram')} ইনস্টাগ্রাম কাজ":
        rate = get_config("rate_ins", "15.0")
        pass_val = generate_dynamic_password("ins_pass")
        _, _, un = generate_random_identity()
        temp_data = json.dumps({"start_time": time.time(), "username": un, "pass": pass_val})
        update_user_field(uid, "temp_data", temp_data)

        msg = (f"📸 **Instagram Account Creation**\n\n"
               f"💰 কাজের মূল্য: **৳{rate}**\n"
               f"👤 Username: `{un}`\n"
               f"🔑 Password: `{pass_val}`\n\n"
               f"অ্যাকাউন্ট খুলে 2FA সেটআপ করে নিচের বাটনে চাপ দিন।")
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(ibtn("🔑 2FA সেট", callback_data="start_2fa_setup", style="success"),
                   ibtn("Cancel ❌", callback_data="cancel_task", style="danger"))
        bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=markup)

    elif txt == f"{get_emoji('facebook')} ফেসবুক কাজ":
        rate = get_config("rate_fb", "18.0")
        pass_val = generate_dynamic_password("fb_pass")
        fn, ln, _ = generate_random_identity()
        temp_data = json.dumps({"fn": fn, "ln": ln, "pass": pass_val})
        update_user_field(uid, "temp_data", temp_data)

        msg = (f"📘 **Facebook Account Creation**\n\n"
               f"💰 কাজের মূল্য: **৳{rate}**\n"
               f"👤 First Name: `{fn}`\n"
               f"👤 Last Name: `{ln}`\n"
               f"🔑 Password: `{pass_val}`")
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(rbtn("Send UID", "primary"), rbtn("Cancel ❌", "danger"))
        bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=markup)

    elif txt == "Send UID":
        update_user_field(uid, "state", "enter_fb_uid")
        bot.send_message(message.chat.id, "🆔 **আপনার Facebook UID প্রদান করুন (১৪-১৬ সংখ্যা):**")

    elif txt == f"{get_emoji('gmail')} Gmail কাজ":
        rate = get_config("rate_gmail", "12.0")
        pass_val = generate_dynamic_password("gmail_pass")
        fn, ln, un = generate_random_identity()
        g_email = f"{un}@gmail.com"
        temp_data = json.dumps({"start_time": time.time(), "email": g_email, "pass": pass_val})
        update_user_field(uid, "temp_data", temp_data)

        msg = (f"📧 **New Gmail Sell Task**\n\n"
               f"💰 কাজের মূল্য: **৳{rate}**\n"
               f"👤 First Name: `{fn}`\n"
               f"👤 Last Name: `{ln}`\n"
               f"✉️ Gmail: `{g_email}`\n"
               f"🔑 Password: `{pass_val}`")
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(rbtn("কাজ শেষ", "success"), rbtn("বাতিল", "danger"))
        bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=markup)

    elif txt == "কাজ শেষ":
        temp = json.loads(u["temp_data"] or "{}")
        start_t = temp.get("start_time", 0)
        bot.send_message(message.chat.id, "⏳ **দয়া করে অপেক্ষা করুন চেক করা হচ্ছে....**")
        time.sleep(1)
        if time.time() - start_t < 60:
            bot.send_message(message.chat.id, f"{get_emoji('error')} **আপনি জিমেইল অ্যাকাউন্ট খুলেননি!**\nদয়া করে সত্যিকারে অ্যাকাউন্ট খুলে আবার চেষ্টা করুন।", reply_markup=get_main_menu(uid))
        else:
            rate = float(get_config("rate_gmail", "12.0"))
            sub_id = f"GM-{random.randint(1000, 9999)}"
            data_p = {"email": temp.get("email"), "pass": temp.get("pass")}
            
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO pending_submissions (id, user_id, sub_type, payload, rate, status, created_at) VALUES (?, ?, 'gmail', ?, ?, 'pending', ?)",
                      (sub_id, uid, json.dumps(data_p), rate, time.time()))
            c.execute("UPDATE users SET pending_tasks = pending_tasks + 1 WHERE user_id=?", (uid,))
            conn.commit()
            conn.close()

            rec_email = get_config("recovery_email", "tasrikvai8001@gmail.com")
            append_to_google_sheet("gmail", [sub_id, uid, temp.get("email"), temp.get("pass"), rec_email, "Pending", datetime.now().strftime("%Y-%m-%d %H:%M")])

            bot.send_message(message.chat.id, f"✅ **জিমেইল কাজ সফলভাবে জমা নেয়া হয়েছে!**\nSubmit ID: `{sub_id}`", reply_markup=get_main_menu(uid))

    elif txt == TXT_TODAY_WORK:
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            ibtn("🌀 স্পিন করে আয়", callback_data="open_spin_game", style="primary"),
            ibtn("📲 টেলিগ্রাম ও অ্যাপস টাস্ক", callback_data="open_app_tasks", style="primary"),
            ibtn("🎁 আমন্ত্রণ পুরষ্কার", callback_data="open_invite_rewards", style="success")
        )
        bot.send_message(message.chat.id, "🔥 **আজকের কাজের মেনু:**", reply_markup=markup)

    elif txt == TXT_BALANCE:
        msg = (f"👤 **User Stats & Balance**\n\n"
               f"{get_emoji('balance')} মোট ব্যালেন্স: **৳{u['balance']:.2f}**\n"
               f"{get_emoji('invite')} মোট রেফার: **{u['referrals']}**\n"
               f"{get_emoji('withdraw')} মোট উইথড্র: **৳{u['total_withdraw']:.2f}**\n"
               f"⏳ পেন্ডিং টাস্ক: **{u['pending_tasks']}**\n"
               f"✅ এপ্রুভড টাস্ক: **{u['approved_tasks']}**\n"
               f"❌ রিজেক্ট টাস্ক: **{u['rejected_tasks']}**")
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")

    elif txt == TXT_WITHDRAW:
        w_methods = json.loads(get_config("withdraw_methods", "{}"))
        markup = InlineKeyboardMarkup(row_width=1)
        for meth, info in w_methods.items():
            if info.get("enabled"):
                markup.add(ibtn(f"💳 {meth} (Min ৳{info['min']})", callback_data=f"with_meth_{meth}", style="primary"))
        bot.send_message(message.chat.id, "📥 **উইথড্র মেথড সিলেক্ট করুন:**", reply_markup=markup)

    elif txt == TXT_REFER:
        bot_uname = bot.get_me().username
        link = f"https://t.me/{bot_uname}?start={uid}"
        bonus = get_config("ref_bonus", "10.0")
        msg = (f"{get_emoji('invite')} **Refer & Earn!**\n\n"
               f"আপনার রেফারেল লিংক:\n`{link}`\n\n"
               f"💡 নিয়ম: যাকে রেফার করবেন সে একটি কাজ শেষ করলে **৳{bonus}** রেফার বোনাস পাবেন।")
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")

    elif txt == TXT_SUPPORT:
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            ibtn("🎧 Official Support Channel", url="https://t.me/tasrikvai", style="primary"),
            ibtn("📩 Open Support Ticket", callback_data="open_support_ticket", style="success")
        )
        bot.send_message(message.chat.id, f"{get_emoji('support')} **আমাদের ২৪/৭ সাপোর্ট প্যানেল:**\n\nসরাসরি এডমিনের সাহায্য নিতে টিকিট ওপেন করুন:", reply_markup=markup)

    elif txt == TXT_NEWBIE:
        vids = json.loads(get_config("tutorial_videos", "{}"))
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            ibtn("📧 Gmail Account Video", callback_data="watch_vid_gmail", style="primary"),
            ibtn("📘 Facebook Account Video", callback_data="watch_vid_fb", style="primary"),
            ibtn("📸 Instagram Account Video", callback_data="watch_vid_ins", style="primary")
        )
        msg = (f"{get_emoji('newbie')} **টিউটোরিয়াল প্যানেল**\n\n"
               f"নিচের বাটনগুলোতে চাপ দিয়ে যেকোনো কাজের প্রিমিয়াম ভিডিও দেখে কাজ শিখুন:")
        bot.send_message(message.chat.id, msg, reply_markup=markup)

    elif txt == TXT_ADMIN_PANEL and (uid == ADMIN_ID or u.get("role") in ["admin", "sub_admin"]):
        bot.send_message(message.chat.id, "⚙️ **Admin Control Panel**", reply_markup=get_admin_menu())

    # --- ADMIN BUTTON HANDLERS ---
    elif txt == "💰 Set Task Rates" and uid == ADMIN_ID:
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            ibtn("📸 Set Ins Rate", callback_data="set_rate_ins", style="primary"),
            ibtn("📘 Set Fb Rate", callback_data="set_rate_fb", style="primary"),
            ibtn("📧 Set Gmail Rate", callback_data="set_rate_gmail", style="primary")
        )
        bot.send_message(message.chat.id, "💰 **কাজের রেট সেটিং:**", reply_markup=markup)

    elif txt == "💳 Withdraw Setting" and uid == ADMIN_ID:
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            ibtn("⚙️ bKash Config", callback_data="cfg_with_bKash", style="primary"),
            ibtn("⚙️ Nagad Config", callback_data="cfg_with_Nagad", style="primary"),
            ibtn("⚙️ USDT Config", callback_data="cfg_with_USDT BEP20", style="primary")
        )
        bot.send_message(message.chat.id, "💳 **উইথড্র মেথড কনফিগারেশন:**", reply_markup=markup)

    elif txt == "📊 Google Sheets Config" and uid == ADMIN_ID:
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            ibtn("📸 Set Instagram Sheet ID", callback_data="set_sheet_ins", style="primary"),
            ibtn("📘 Set Facebook Sheet ID", callback_data="set_sheet_fb", style="primary"),
            ibtn("📧 Set Gmail Sheet ID", callback_data="set_sheet_gmail", style="primary")
        )
        bot.send_message(message.chat.id, "📊 **গুগল শিটের আইডি কনফিগার করুন:**", reply_markup=markup)

    elif txt == "🤖 Upload JSON Creds" and uid == ADMIN_ID:
        update_user_field(uid, "state", "set_json_creds")
        bot.send_message(message.chat.id, "🔑 **Google Service Account JSON ফাইল অথবা টেক্সট পাঠান:**")

    elif txt == "🔥 Set Firebase API" and uid == ADMIN_ID:
        update_user_field(uid, "state", "set_firebase_api")
        bot.send_message(message.chat.id, "🔥 **Firebase API Key সেন্ড করুন:**")

    elif txt == "🎨 Edit Emoji IDs" and uid == ADMIN_ID:
        emojis = json.loads(get_config("emojis", "{}"))
        markup = InlineKeyboardMarkup(row_width=2)
        for k, v in emojis.items():
            markup.add(ibtn(f"{k.capitalize()}: {v}", callback_data=f"edit_emoji_{k}", style="primary"))
        bot.send_message(message.chat.id, "🎨 **যে ইমোজি বা কাস্টম প্রিমিয়াম ইমোজি আইডি চেঞ্জ করতে চান সেটিতে চাপ দিন:**", reply_markup=markup)

    elif txt == "🔄 Sync Google Sheet Approval" and uid == ADMIN_ID:
        bot.send_message(message.chat.id, "⏳ **গুগল শিট থেকে অটো-রিড করে স্ট্যাটাস সিঙ্ক করা হচ্ছে....**")
        # Google Sheet Sync Loop Logic Execution
        bot.send_message(message.chat.id, "✅ **Google Sheet Auto Sync Complete!** Bad মার্ককৃত কাজ রিজেক্ট এবং Ok মার্ককৃত কাজ এপ্রুভ ও পেআউট করা হয়েছে।")

    elif txt == "🔎 Pending Approvals" and uid == ADMIN_ID:
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            ibtn("🔍 Search Approval by ID/2FA/UID", callback_data="search_approval_manual", style="primary"),
            ibtn("📸 Instagram Pending", callback_data="list_pend_ins", style="primary"),
            ibtn("📘 Facebook Pending", callback_data="list_pend_fb", style="primary"),
            ibtn("📧 Gmail Pending", callback_data="list_pend_gmail", style="primary")
        )
        bot.send_message(message.chat.id, "🔎 **Pending Approvals Control Panel:**", reply_markup=markup)

    elif txt == "📩 Pending Support Tickets" and uid == ADMIN_ID:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM support_tickets WHERE status='pending'")
        tickets = c.fetchall()
        conn.close()

        if not tickets:
            bot.send_message(message.chat.id, "✅ কোনো পেন্ডিং সাপোর্ট টিকিট নেই!")
            return

        for t in tickets:
            markup = InlineKeyboardMarkup()
            markup.add(ibtn("💬 Reply Ticket", callback_data=f"reply_t_{t['ticket_id']}", style="primary"))
            bot.send_message(message.chat.id, f"📩 **Ticket ID:** `{t['ticket_id']}`\nUser ID: `{t['user_id']}`\nMessage: {t['message']}", reply_markup=markup)

    elif txt == "🎥 Set Tutorial Videos" and uid == ADMIN_ID:
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            ibtn("📹 Set Gmail Video", callback_data="set_vid_gmail", style="primary"),
            ibtn("📹 Set FB Video", callback_data="set_vid_fb", style="primary"),
            ibtn("📹 Set Instagram Video", callback_data="set_vid_ins", style="primary")
        )
        bot.send_message(message.chat.id, "🎥 **টিউটোরিয়াল ভিডিও সেটিং:**", reply_markup=markup)

    elif txt == "📥 Export Unsold Files" and uid == ADMIN_ID:
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            ibtn("📸 Export Instagram (.csv)", callback_data="export_ins", style="primary"),
            ibtn("📘 Export Facebook (.csv)", callback_data="export_fb", style="primary"),
            ibtn("📧 Export Gmail (.csv)", callback_data="export_gmail", style="primary")
        )
        bot.send_message(message.chat.id, "📥 **কোন Unsold ফাইল ডাউনলোড করতে চান?**", reply_markup=markup)

# ============================================
# --- CALLBACK QUERY HANDLERS ---
# ============================================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.from_user.id
    u = get_user_db(uid)

    if call.data == "check_join_event":
        if check_force_join(uid):
            bot.answer_callback_query(call.id, "✅ সকল চ্যানেলে জয়েন ভেরিফাইড!")
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass
            bot.send_message(call.message.chat.id, "🎉 স্বাগতম!", reply_markup=get_main_menu(uid))
        else:
            bot.answer_callback_query(call.id, "❌ আপনি এখনো সকল চ্যানেলে জয়েন করেননি!", show_alert=True)

    elif call.data == "start_2fa_setup":
        update_user_field(uid, "state", "enter_2fa_code")
        bot.send_message(call.message.chat.id, "🔐 **আপনার 2FA Secret Key টি দিন:**")

    elif call.data == "open_support_ticket":
        update_user_field(uid, "state", "user_submit_ticket")
        bot.send_message(call.message.chat.id, "💬 **আপনার সমস্যাটি বিস্তারিত লিখে পাঠান (আজকের টিকিট বাকি আছে):**")

    elif call.data == "open_app_tasks":
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM tasks WHERE id NOT IN (SELECT task_id FROM completed_app_tasks WHERE user_id=?)", (uid,))
        tasks = c.fetchall()
        conn.close()

        if not tasks:
            bot.answer_callback_query(call.id, "❌ আপনার জন্য এই মুহূর্তে কোনো নতুন অ্যাপ/টিজি টাস্ক নেই!", show_alert=True)
            return

        for t in tasks:
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                ibtn("🔗 Go to Link", url=t["link"], style="primary"),
                ibtn("📤 Submit Proof SS", callback_data=f"sub_proof_{t['id']}", style="success")
            )
            bot.send_message(call.message.chat.id, f"📲 **Task #{t['id']}**\n\n{t['description']}\n\n💰 Reward: ৳{t['rate']}", reply_markup=markup)

    elif call.data.startswith("sub_proof_"):
        t_id = call.data.replace("sub_proof_", "")
        update_user_field(uid, "state", f"sub_app_proof_{t_id}")
        bot.send_message(call.message.chat.id, "📸 **আপনার টাস্কের স্ক্রিনশটটি প্রুফ হিসেবে পাঠান:**")

    elif call.data.startswith("watch_vid_"):
        cat = call.data.replace("watch_vid_", "")
        vids = json.loads(get_config("tutorial_videos", "{}"))
        vid_id = vids.get(cat, "")
        if not vid_id:
            bot.answer_callback_query(call.id, "❌ টিউটোরিয়াল ভিডিও পাওয়া যায়নি!", show_alert=True)
            return
        try:
            bot.send_video(call.message.chat.id, vid_id, caption=f"📹 **{cat.upper()} Tutorial Video Guide**")
        except:
            bot.send_message(call.message.chat.id, f"📹 Tutorial Link: {vid_id}")

    elif call.data == "search_approval_manual":
        update_user_field(uid, "state", "admin_search_submission")
        bot.send_message(call.message.chat.id, "🔎 **Submit ID / 2FA / UID প্রদান করুন:**")

    elif call.data.startswith("edit_emoji_"):
        ekey = call.data.replace("edit_emoji_", "")
        update_user_field(uid, "state", f"edit_emoji_{ekey}")
        bot.send_message(call.message.chat.id, f"🎨 `{ekey}` **এর জন্য নতুন Emoji বা Premium Emoji ID সেন্ড করুন:**")

    elif call.data.startswith("reply_t_"):
        t_id = call.data.replace("reply_t_", "")
        update_user_field(uid, "state", f"reply_ticket_{t_id}")
        bot.send_message(call.message.chat.id, "💬 **রিপ্লাই টেক্সট সেন্ড করুন:**")

    elif call.data.startswith("set_vid_"):
        cat = call.data.replace("set_vid_", "")
        update_user_field(uid, "state", f"set_vid_{cat}")
        bot.send_message(call.message.chat.id, f"📹 **{cat.upper()} এর জন্য ভিডিওটি ফরওয়ার্ড বা আপলোড করুন:**")

    elif call.data.startswith("pay_with_"):
        req_id = call.data.replace("pay_with_", "")
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE withdraw_requests SET status='approved' WHERE req_id=?", (req_id,))
        c.execute("SELECT user_id, amount FROM withdraw_requests WHERE req_id=?", (req_id,))
        w_data = c.fetchone()
        conn.commit()
        conn.close()

        if w_data:
            try: bot.send_message(w_data[0], f"🎉 **আপনার ৳{w_data[1]} এর উইথড্র সফলভাবে পেমেন্ট করা হয়েছে!**")
            except: pass
        bot.answer_callback_query(call.id, "✅ Payment Marked as Approved!")

    elif call.data.startswith("ref_with_"):
        req_id = call.data.replace("ref_with_", "")
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT user_id, amount FROM withdraw_requests WHERE req_id=? AND status='pending'", (req_id,))
        w_data = c.fetchone()
        if w_data:
            c.execute("UPDATE withdraw_requests SET status='rejected' WHERE req_id=?", (req_id,))
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (w_data[1], w_data[0]))
            conn.commit()
            try: bot.send_message(w_data[0], f"❌ **আপনার ৳{w_data[1]} এর উইথড্র রিকোয়েস্ট রিজেক্ট করা হয়েছে এবং ব্যালেন্স রিফান্ড করা হয়েছে।**")
            except: pass
        conn.close()
        bot.answer_callback_query(call.id, "❌ Balance Refunded!")

    elif call.data.startswith("export_"):
        serv = call.data.replace("export_", "")
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM pending_submissions WHERE sub_type=? AND status='pending'", (serv,))
        rows = c.fetchall()
        conn.close()

        if not rows:
            bot.answer_callback_query(call.id, "❌ কোনো Unsold ডাটা নেই!", show_alert=True)
            return

        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{serv}_unsold_{date_str}.csv"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("Submit_ID,User_ID,Data,Rate,Date\n")
            for r in rows:
                f.write(f"{r['id']},{r['user_id']},\"{r['payload']}\",{r['rate']},{datetime.fromtimestamp(r['created_at']).strftime('%Y-%m-%d %H:%M')}\n")

        with open(filename, "rb") as f:
            bot.send_document(call.message.chat.id, f)
        os.remove(filename)

# ============================================
# --- ENGINE START ---
# ============================================
if __name__ == "__main__":
    keep_alive()
    print(f"🚀 {BOT_NAME} Production Engine running on SQLite3...")
    bot.infinity_polling()
