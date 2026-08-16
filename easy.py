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
import traceback
import smtplib
import pyotp
import csv
import io
from datetime import datetime

# --- AUTOMATIC DEPENDENCY CHECK ---
for pkg in ["flask", "pyTelegramBotAPI", "gspread", "oauth2client", "pyotp"]:
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
    return "EASY EARN BD Engine is Running 24/7!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_web_server)
    t.daemon = True
    t.start()

# ============================================
# --- CONFIGURATION & ENVIRONMENT SECURITY ---
# ============================================
TOKEN = os.environ.get("BOT_TOKEN", "8593556780:AAFPvacoLaCxJoF8xiyM27AIBVX1c-XwEHA")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 7833766898))
BOT_NAME = "EASY EARN BD"
DB_FILE = "bot_data.db"
LOG_FILE = "error_logs.txt"
JSON_CREDS_FILE = "credentials.json"

bot = telebot.TeleBot(TOKEN, num_threads=50)
db_lock = threading.RLock()

# --- ERROR & AUDIT LOGGERS ---
def log_error(err_msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {err_msg}\n{'-'*40}\n")

def log_admin_action(admin_id, action_desc):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"🛡️ **Admin Audit Log**\n👤 Admin: `{admin_id}`\n📝 Action: {action_desc}\n⏰ Time: `{timestamp}`"
    try:
        bot.send_message(ADMIN_ID, msg, parse_mode="Markdown")
    except:
        pass

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
            daily_spins INTEGER DEFAULT 0,
            last_spin_date TEXT DEFAULT '',
            last_active REAL DEFAULT 0,
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
            "ins_pass": "Nabil",
            "fb_pass": "Nabil",
            "gmail_pass": "Nabil",
            "recovery_email": "tasrikvai8001@gmail.com",
            "emojis": json.dumps(default_emojis),
            "spin_ad_url": "https://example.com/adsterra",
            "spin_reward": "1.5",
            "spin_limit": "5",
            "sheet_id_ins": "",
            "sheet_id_fb": "",
            "sheet_id_gmail": "",
            "json_credentials": "",
            "firebase_api": "AIzaSyB_Your_Firebase_API_Key_Here",
            "tutorial_videos": json.dumps({"gmail": "", "fb": "", "ins": ""}),
            "withdraw_methods": json.dumps({
                "bKash": {"enabled": True, "min": 50.0, "max": 5000.0},
                "Nagad": {"enabled": True, "min": 50.0, "max": 5000.0},
                "Rocket": {"enabled": True, "min": 50.0, "max": 5000.0},
                "USDT BEP20": {"enabled": True, "min": 100.0, "max": 10000.0}
            }),
            "maintenance_mode": "false",
            "pause_gmail": "false",
            "pause_fb": "false",
            "pause_ins": "false",
            "daily_bot_withdraw_limit": "50000.0",
            "today_total_withdrawn": "0.0",
            "last_withdraw_reset_date": ""
        }
        for k, v in defaults.items():
            c.execute("INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)", (k, str(v)))
            
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
        c.execute("INSERT INTO users (user_id, created_at, last_active) VALUES (?, ?, ?)", (user_id, now, now))
        conn.commit()
        c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        u = c.fetchone()
    else:
        c.execute("UPDATE users SET last_active=? WHERE user_id=?", (time.time(), user_id))
        conn.commit()
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

def check_permission(user_id, perm):
    if user_id == ADMIN_ID: return True
    u = get_user_db(user_id)
    if u.get("role") == "admin": return True
    if u.get("role") == "sub_admin":
        perms = json.loads(u.get("permissions") or "{}")
        return perms.get(perm, False)
    return False

# ============================================
# --- GOOGLE SHEETS AUTOMATION ENGINE ---
# ============================================
def get_gspread_client():
    try:
        json_data = get_config("json_credentials", "")
        if not json_data and os.path.exists(JSON_CREDS_FILE):
            with open(JSON_CREDS_FILE, 'r') as f:
                json_data = f.read()

        if not json_data: return None

        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = json.loads(json_data)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        log_error(f"GSpread Client Auth Error: {e}\n{traceback.format_exc()}")
        return None

def append_to_google_sheet(service_type, row_data):
    try:
        client = get_gspread_client()
        if not client: return False

        sheet_key = f"sheet_id_{service_type.lower()}"
        sheet_id = get_config(sheet_key, "")
        if not sheet_id: return False

        sh = client.open_by_key(sheet_id)
        
        target_sheet = None
        for ws in sh.worksheets():
            w_title = ws.title.strip().lower()
            if service_type.lower() in w_title or w_title == "sheet1":
                target_sheet = ws
                break
        if not target_sheet:
            target_sheet = sh.sheet1

        target_sheet.append_row(row_data)
        return True
    except Exception as e:
        log_error(f"Google Sheet Append Error ({service_type}): {e}\n{traceback.format_exc()}")
        return False

def sync_sheet_approvals():
    processed_count = 0
    client = get_gspread_client()
    if not client: return 0

    services = ['ins', 'fb', 'gmail']
    for s_type in services:
        sheet_id = get_config(f"sheet_id_{s_type}", "")
        if not sheet_id: continue
        try:
            sh = client.open_by_key(sheet_id)
            target_sheet = sh.sheet1
            records = target_sheet.get_all_records()
            for idx, row in enumerate(records, start=2):
                sub_id = str(row.get("Submit_ID") or row.get("ID") or "")
                status_val = str(row.get("Status") or "").strip().lower()

                if not sub_id or status_val not in ["ok", "bad", "approved", "rejected"]:
                    continue

                conn = get_db()
                c = conn.cursor()
                c.execute("SELECT * FROM pending_submissions WHERE id=? AND status='pending'", (sub_id,))
                sub = c.fetchone()
                
                if sub:
                    sub = dict(sub)
                    uid = sub['user_id']
                    rate = sub['rate']

                    if status_val in ["ok", "approved"]:
                        c.execute("UPDATE pending_submissions SET status='approved' WHERE id=?", (sub_id,))
                        c.execute("UPDATE users SET balance = balance + ?, total_income = total_income + ?, approved_tasks = approved_tasks + 1, pending_tasks = MAX(0, pending_tasks - 1) WHERE user_id=?", (rate, rate, uid))
                        
                        c.execute("SELECT referred_by FROM users WHERE user_id=?", (uid,))
                        u_ref = c.fetchone()
                        if u_ref and u_ref[0]:
                            ref_id = u_ref[0]
                            ref_comm = rate * 0.10
                            c.execute("UPDATE users SET balance = balance + ?, total_income = total_income + ? WHERE user_id=?", (ref_comm, ref_comm, ref_id))
                            try: bot.send_message(ref_id, f"🎉 **রেফারেল ১০% কমিশন!** আপনার রেফারেল একটি কাজ সম্পন্ন করায় আপনি **৳{ref_comm:.2f}** কমিশন পেয়েছেন!")
                            except: pass

                        try: bot.send_message(uid, f"✅ **আপনার কাজ এপ্রুভ হয়েছে!**\nSubmit ID: `{sub_id}`\nব্যালেন্সে যোগ করা হয়েছে: ৳{rate:.2f}")
                        except: pass

                    elif status_val in ["bad", "rejected"]:
                        c.execute("UPDATE pending_submissions SET status='rejected' WHERE id=?", (sub_id,))
                        c.execute("UPDATE users SET rejected_tasks = rejected_tasks + 1, pending_tasks = MAX(0, pending_tasks - 1) WHERE user_id=?", (uid,))
                        try: bot.send_message(uid, f"❌ **আপনার কাজ রিজেক্ট করা হয়েছে!**\nSubmit ID: `{sub_id}`")
                        except: pass

                    conn.commit()
                    processed_count += 1
                conn.close()
        except Exception as e:
            log_error(f"Sheet Sync Error for {s_type}: {e}\n{traceback.format_exc()}")
            continue
    return processed_count

# ============================================
# --- AUTOMATIC GMAIL SMTP EXISTENCE CHECKER ---
# ============================================
def verify_gmail_smtp(email):
    try:
        domain = email.split('@')[-1]
        if domain.lower() != "gmail.com": return True
        server = smtplib.SMTP(timeout=5)
        server.connect('gmail-smtp-in.l.google.com', 25)
        server.helo('localhost')
        server.mail('check@example.com')
        code, message = server.rcpt(str(email))
        server.quit()
        return code == 250
    except Exception as e:
        log_error(f"SMTP Verification Warning for {email}: {e}")
        return True

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
# --- DYNAMIC HELPERS & GENERATORS ---
# ============================================
def generate_dynamic_password(prefix_key):
    base_name = get_config(prefix_key, "Nabil")
    date_str = datetime.now().strftime("%d%m")
    special_char = "@"
    return f"{base_name}{date_str}{special_char}"

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

def export_unsold_csv(service_type):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, user_id, payload, created_at FROM pending_submissions WHERE sub_type=? AND status='pending'", (service_type,))
    records = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)

    if service_type == "ins":
        writer.writerow(["Submit_ID", "User_ID", "Username", "Password", "2FA_Secret", "Code", "Created_At"])
        for r in records:
            p = json.loads(r['payload'] or '{}')
            t_str = datetime.fromtimestamp(r['created_at']).strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow([r['id'], r['user_id'], p.get('username'), p.get('pass'), p.get('2fa'), p.get('code'), t_str])
    elif service_type == "fb":
        writer.writerow(["Submit_ID", "User_ID", "First_Name", "Last_Name", "FB_UID", "Password", "Cookie", "Created_At"])
        for r in records:
            p = json.loads(r['payload'] or '{}')
            t_str = datetime.fromtimestamp(r['created_at']).strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow([r['id'], r['user_id'], p.get('fn'), p.get('ln'), p.get('uid'), p.get('pass'), p.get('cookie'), t_str])
    elif service_type == "gmail":
        writer.writerow(["Submit_ID", "User_ID", "Email", "Password", "Recovery_Email", "Created_At"])
        rec_email = get_config("recovery_email", "tasrikvai8001@gmail.com")
        for r in records:
            p = json.loads(r['payload'] or '{}')
            t_str = datetime.fromtimestamp(r['created_at']).strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow([r['id'], r['user_id'], p.get('email'), p.get('pass'), rec_email, t_str])

    return output.getvalue()

# ============================================
# --- CAPTCHA GENERATOR & FORCE JOIN ---
# ============================================
def generate_captcha():
    num1 = random.randint(1, 9)
    num2 = random.randint(1, 9)
    ans = num1 + num2
    return f"{num1} + {num2} = ?", str(ans)

def check_force_join(user_id):
    chs = json.loads(get_config("force_channels", "[]"))
    if not chs: return True
    for ch in chs:
        try:
            m = bot.get_chat_member(ch, user_id)
            if m.status in ['left', 'kicked']: return False
        except Exception as e: 
            log_error(f"Force join check error for {ch}: {e}")
            return False
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
    markup.add(rbtn("🎥 Set Tutorial Videos", "primary"), rbtn("🔍 User Deep Search", "primary"))
    markup.add(rbtn("📢 Channel Multi-Post Broadcast", "primary"), rbtn("🗑️ Bulk Reject Submissions", "danger"))
    markup.add(rbtn("⏸️ Task Pause Manager", "primary"), rbtn("🧹 Database Cleanup", "danger"))
    markup.add(rbtn("🚨 Error Logs", "danger"), rbtn("⚡ Maintenance Mode", "danger"))
    markup.add(rbtn(TXT_BACK, "danger"))
    return markup

# ============================================
# --- CRON / RE-ENGAGEMENT BACKGROUND THREAD ---
# ============================================
def automated_reengagement_cron():
    while True:
        try:
            time.sleep(86400)
            conn = get_db()
            c = conn.cursor()
            three_days_ago = time.time() - (3 * 86400)
            c.execute("SELECT user_id FROM users WHERE last_active <= ? AND is_banned=0", (three_days_ago,))
            inactive_users = c.fetchall()
            conn.close()

            for u_row in inactive_users:
                try:
                    msg = "👋 **আমরা আপনাকে মিস করছি!**\n\nআপনার জন্য নতুন ফেসবুক ও জিমেইল টাস্ক অপেক্ষা করছে। এখনই বটে লগইন করে কাজ করে আয় করুন! 💰"
                    bot.send_message(u_row['user_id'], msg, parse_mode="Markdown")
                    time.sleep(0.05)
                except:
                    pass
        except Exception as e:
            log_error(f"Re-engagement Cron Error: {e}")

threading.Thread(target=automated_reengagement_cron, daemon=True).start()

# ============================================
# --- COMMAND & START CAPTCHA HANDLERS ---
# ============================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        uid = message.from_user.id
        
        if get_config("maintenance_mode", "false") == "true" and uid != ADMIN_ID:
            bot.send_message(message.chat.id, f"{get_emoji('warning')} **বট বর্তমানে মেইনটেন্যান্স মোডে আছে।** খুব শীঘ্রই আবার কাজ চালু হবে।", parse_mode="Markdown")
            return

        u = get_user_db(uid)
        if u["is_banned"]:
            bot.send_message(message.chat.id, f"{get_emoji('error')} **আপনি এই বটে ব্লকড আছেন!**", parse_mode="Markdown")
            return

        args = message.text.split()
        if len(args) > 1 and not u["referred_by"]:
            ref_id = args[1]
            if ref_id.isdigit() and int(ref_id) != uid:
                ref_user = get_user_db(int(ref_id))
                if u.get("ip_address") and u.get("ip_address") == ref_user.get("ip_address"):
                    bot.send_message(uid, f"{get_emoji('warning')} **সতর্কবার্তা:** একই ডিভাইস/নেটওয়ার্ক থেকে একাধিক অ্যাকাউন্ট খোলা সনাক্ত হয়েছে! রেফার বোনাস যোগ হবে না।")
                    bot.send_message(ADMIN_ID, f"🚨 **Multi-Account Alert!**\nUser `{uid}` joined via Ref `{ref_id}` from the same Network/IP!")
                else:
                    update_user_field(uid, "referred_by", int(ref_id))

        question, ans = generate_captcha()
        temp = json.loads(u["temp_data"] or "{}")
        temp["captcha_ans"] = ans
        update_user_field(uid, "temp_data", json.dumps(temp))
        update_user_field(uid, "state", "verify_captcha")

        bot.send_message(message.chat.id, f"🤖 **বট সিকিউরিটি ভেরিফিকেশন:**\n\nদয়া করে গাণিতিক উত্তরটি দিন:\n👉 **{question}**")
    except Exception as e:
        log_error(f"Error in /start: {e}\n{traceback.format_exc()}")

# ============================================
# --- MAIN MESSAGE ROUTER ---
# ============================================
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'document', 'video'])
def handle_all_messages(message):
    try:
        uid = message.from_user.id
        txt = message.text.strip() if message.text else ""
        u = get_user_db(uid)

        state = u.get("state")
        if state == "verify_captcha":
            temp = json.loads(u["temp_data"] or "{}")
            c_ans = temp.get("captcha_ans")
            if txt == c_ans:
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, "✅ **ক্যাপচা ভেরিফিকেশন সফল হয়েছে!**")
                
                if u.get("referred_by") and u.get("ref_rewarded") == 0:
                    ref_id = u.get("referred_by")
                    fname = message.from_user.first_name
                    ref_msg = (f"🎉 **নতুন রেফারেল নোটিফিকেশন!**\n\n"
                               f"আপনার রেফার লিংক ব্যবহার করে **{fname}** বটে জয়েন করেছে।\n\n"
                               f"👉 **দয়া করে তাকে একটি জিমেইল এর কাজ করতে বলেন তাহলে ১০ টাকা বোনাস পাবেন এবং সে যত কাজ করবে আপনি ১০% বোনাস পাবেন সারাজীবন।**")
                    try: bot.send_message(ref_id, ref_msg, parse_mode="Markdown")
                    except: pass
                
                if not check_force_join(uid):
                    msg = f"👋 **Welcome to {BOT_NAME}!**\n\nবটের কাজ করার জন্য নিচের চ্যানেলগুলোতে জয়েন করুন এবং 'Verify Now' চাপুন:"
                    bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=get_force_join_markup())
                    return
                else:
                    bot.send_message(message.chat.id, f"💎 **Welcome to {BOT_NAME}!**\nনিচের প্রিমিয়াম মেনু থেকে আপনার পছন্দ বেছে নিন:", parse_mode="Markdown", reply_markup=get_main_menu(uid))
                    return
            else:
                question, ans = generate_captcha()
                temp["captcha_ans"] = ans
                update_user_field(uid, "temp_data", json.dumps(temp))
                bot.send_message(message.chat.id, f"❌ **ভুল উত্তর!** আবার চেষ্টা করুন:\n👉 **{question}**")
                return

        if uid != ADMIN_ID and not check_force_join(uid):
            bot.send_message(message.chat.id, f"{get_emoji('warning')} **কাজ শুরু করার আগে অবশ্যই আপনাকে আমাদের অফিসিয়াল চ্যানেলগুলোতে জয়েন করতে হবে!**", reply_markup=get_force_join_markup())
            return

        if u["is_banned"]: return

        if state and check_permission(uid, "admin"):
            if state == "set_rate_ins":
                set_config("rate_ins", txt)
                update_user_field(uid, "state", None)
                log_admin_action(uid, f"Set Ins Rate to ৳{txt}")
                bot.send_message(message.chat.id, f"✅ Instagram Rate set to: ৳{txt}", reply_markup=get_admin_menu())
                return
            elif state == "set_rate_fb":
                set_config("rate_fb", txt)
                update_user_field(uid, "state", None)
                log_admin_action(uid, f"Set FB Rate to ৳{txt}")
                bot.send_message(message.chat.id, f"✅ Facebook Rate set to: ৳{txt}", reply_markup=get_admin_menu())
                return
            elif state == "set_rate_gmail":
                set_config("rate_gmail", txt)
                update_user_field(uid, "state", None)
                log_admin_action(uid, f"Set Gmail Rate to ৳{txt}")
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
                bot.send_message(message.chat.id, "✅ Google Cloud Service Account JSON Saved!", reply_markup=get_admin_menu())
                return
            elif state == "set_firebase_api":
                if message.document:
                    file_info = bot.get_file(message.document.file_id)
                    downloaded_file = bot.download_file(file_info.file_path)
                    set_config("firebase_api", downloaded_file.decode('utf-8'))
                else:
                    set_config("firebase_api", txt)
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, "✅ Firebase API Key / Config JSON Updated Successfully!", reply_markup=get_admin_menu())
                return
            elif state == "set_recovery_email":
                set_config("recovery_email", txt)
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, f"✅ Recovery Email Set to: `{txt}`", parse_mode="Markdown", reply_markup=get_admin_menu())
                return
            elif state == "set_ref_bonus":
                set_config("ref_bonus", txt)
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, f"✅ Refer Bonus Set to: ৳{txt}", reply_markup=get_admin_menu())
                return
            elif state == "set_pass_ins":
                set_config("ins_pass", txt)
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, f"✅ Instagram Password Base Set to: `{txt}`", parse_mode="Markdown", reply_markup=get_admin_menu())
                return
            elif state == "set_pass_fb":
                set_config("fb_pass", txt)
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, f"✅ Facebook Password Base Set to: `{txt}`", parse_mode="Markdown", reply_markup=get_admin_menu())
                return
            elif state == "set_pass_gmail":
                set_config("gmail_pass", txt)
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, f"✅ Gmail Password Base Set to: `{txt}`", parse_mode="Markdown", reply_markup=get_admin_menu())
                return
            elif state == "set_force_join":
                chs = [c.strip() for c in txt.split(",") if c.strip()]
                set_config("force_channels", json.dumps(chs))
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, f"✅ Force Join Channels Updated to: {chs}", reply_markup=get_admin_menu())
                return
            elif state == "set_spin_reward":
                set_config("spin_reward", txt)
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, f"✅ Spin Reward Set to: ৳{txt}", reply_markup=get_admin_menu())
                return
            elif state == "set_spin_limit":
                set_config("spin_limit", txt)
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, f"✅ Spin Daily Limit Set to: {txt} Times", reply_markup=get_admin_menu())
                return
            elif state == "set_spin_url":
                set_config("spin_ad_url", txt)
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, f"✅ Adsterra Direct Link Set to: `{txt}`", parse_mode="Markdown", reply_markup=get_admin_menu())
                return
            elif state == "admin_ban_user":
                if txt.isdigit():
                    update_user_field(int(txt), "is_banned", 1)
                    log_admin_action(uid, f"Banned User {txt}")
                    bot.send_message(message.chat.id, f"⛔ User `{txt}` has been BANNED!", reply_markup=get_admin_menu())
                else: bot.send_message(message.chat.id, "❌ ইনভ্যালিড ইউজার আইডি!")
                update_user_field(uid, "state", None)
                return
            elif state == "admin_unban_user":
                if txt.isdigit():
                    update_user_field(int(txt), "is_banned", 0)
                    log_admin_action(uid, f"Unbanned User {txt}")
                    bot.send_message(message.chat.id, f"✅ User `{txt}` has been UNBANNED!", reply_markup=get_admin_menu())
                else: bot.send_message(message.chat.id, "❌ ইনভ্যালিড ইউজার আইডি!")
                update_user_field(uid, "state", None)
                return
            elif state == "admin_mod_user":
                if txt.isdigit():
                    perms = {"withdraw": True, "tasks": True, "support": True}
                    update_user_field(int(txt), "role", "sub_admin")
                    update_user_field(int(txt), "permissions", json.dumps(perms))
                    log_admin_action(uid, f"Made Sub-Admin User {txt}")
                    bot.send_message(message.chat.id, f"👑 User `{txt}` updated to Sub-Admin!", reply_markup=get_admin_menu())
                else: bot.send_message(message.chat.id, "❌ ইনভ্যালিড ইউজার আইডি!")
                update_user_field(uid, "state", None)
                return
            elif state == "admin_unmod_user":
                if txt.isdigit():
                    update_user_field(int(txt), "role", "user")
                    log_admin_action(uid, f"Demoted Sub-Admin User {txt}")
                    bot.send_message(message.chat.id, f"👤 User `{txt}` demoted to General User!", reply_markup=get_admin_menu())
                else: bot.send_message(message.chat.id, "❌ ইনভ্যালিড ইউজার আইডি!")
                update_user_field(uid, "state", None)
                return
            elif state == "admin_add_bal_id":
                temp = json.loads(u["temp_data"] or "{}")
                temp["target_user"] = txt
                update_user_field(uid, "temp_data", json.dumps(temp))
                update_user_field(uid, "state", "admin_add_bal_amt")
                bot.send_message(message.chat.id, "💰 **কত টাকা ব্যালেন্স যোগ করতে চান? (যেমন: 50):**")
                return
            elif state == "admin_add_bal_amt":
                try:
                    amt = float(txt)
                    temp = json.loads(u["temp_data"] or "{}")
                    target = int(temp.get("target_user"))
                    conn = get_db()
                    c = conn.cursor()
                    c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, target))
                    conn.commit()
                    conn.close()
                    log_admin_action(uid, f"Added ৳{amt} balance to User {target}")
                    bot.send_message(message.chat.id, f"✅ User `{target}` এর সাথে ৳{amt} যোগ করা হয়েছে!", reply_markup=get_admin_menu())
                    try: bot.send_message(target, f"🎉 **এডমিন আপনার অ্যাকাউন্টে ৳{amt} যোগ করেছেন!**")
                    except: pass
                except: bot.send_message(message.chat.id, "❌ ইনভ্যালিড অ্যামাউন্ট!", reply_markup=get_admin_menu())
                update_user_field(uid, "state", None)
                return
            elif state == "admin_ded_bal_id":
                temp = json.loads(u["temp_data"] or "{}")
                temp["target_user"] = txt
                update_user_field(uid, "temp_data", json.dumps(temp))
                update_user_field(uid, "state", "admin_ded_bal_amt")
                bot.send_message(message.chat.id, "💰 **কত টাকা ব্যালেন্স কাটতে চান? (যেমন: 20):**")
                return
            elif state == "admin_ded_bal_amt":
                try:
                    amt = float(txt)
                    temp = json.loads(u["temp_data"] or "{}")
                    target = int(temp.get("target_user"))
                    conn = get_db()
                    c = conn.cursor()
                    c.execute("UPDATE users SET balance = MAX(0, balance - ?) WHERE user_id=?", (amt, target))
                    conn.commit()
                    conn.close()
                    log_admin_action(uid, f"Deducted ৳{amt} balance from User {target}")
                    bot.send_message(message.chat.id, f"✅ User `{target}` এর অ্যাকাউন্ট থেকে ৳{amt} কাটা হয়েছে!", reply_markup=get_admin_menu())
                except: bot.send_message(message.chat.id, "❌ ইনভ্যালিড অ্যামাউন্ট!", reply_markup=get_admin_menu())
                update_user_field(uid, "state", None)
                return
            elif state and state.startswith("cfg_w_min_"):
                meth = state.replace("cfg_w_min_", "")
                try:
                    val = float(txt)
                    w_methods = json.loads(get_config("withdraw_methods", "{}"))
                    w_methods[meth]["min"] = val
                    set_config("withdraw_methods", json.dumps(w_methods))
                    bot.send_message(message.chat.id, f"✅ {meth} Min Limit Set to ৳{val}", reply_markup=get_admin_menu())
                except: bot.send_message(message.chat.id, "❌ ইনভ্যালিড ইনপুট!")
                update_user_field(uid, "state", None)
                return
            elif state and state.startswith("cfg_w_max_"):
                meth = state.replace("cfg_w_max_", "")
                try:
                    val = float(txt)
                    w_methods = json.loads(get_config("withdraw_methods", "{}"))
                    w_methods[meth]["max"] = val
                    set_config("withdraw_methods", json.dumps(w_methods))
                    bot.send_message(message.chat.id, f"✅ {meth} Max Limit Set to ৳{val}", reply_markup=get_admin_menu())
                except: bot.send_message(message.chat.id, "❌ ইনভ্যালিড ইনপুট!")
                update_user_field(uid, "state", None)
                return
            elif state == "set_daily_bot_withdraw_limit":
                try:
                    val = float(txt)
                    set_config("daily_bot_withdraw_limit", str(val))
                    bot.send_message(message.chat.id, f"✅ Daily Total Bot Withdrawal Limit Set to ৳{val:.2f}", reply_markup=get_admin_menu())
                except:
                    bot.send_message(message.chat.id, "❌ ইনভ্যালিড অ্যামাউন্ট!")
                update_user_field(uid, "state", None)
                return
            elif state == "admin_broadcast_msg":
                conn = get_db()
                c = conn.cursor()
                c.execute("SELECT user_id FROM users WHERE is_banned=0")
                users = c.fetchall()
                conn.close()
                bot.send_message(message.chat.id, f"🚀 **{len(users)} জন ইউজারের নিকট ব্রডকাস্ট পাঠানো শুরু হয়েছে...**")
                
                success = 0
                for u_row in users:
                    try:
                        if message.photo:
                            bot.send_photo(u_row['user_id'], message.photo[-1].file_id, caption=message.caption or "")
                        else:
                            bot.send_message(u_row['user_id'], txt, parse_mode="Markdown")
                        success += 1
                        time.sleep(0.05)
                    except: pass
                bot.send_message(message.chat.id, f"✅ **ব্রডকাস্ট সম্পন্ন!** সফলভাবে পাঠানো হয়েছে: {success} জনের কাছে।", reply_markup=get_admin_menu())
                update_user_field(uid, "state", None)
                return

            elif state == "admin_channel_multipost":
                conn = get_db()
                c = conn.cursor()
                c.execute("SELECT user_id FROM users WHERE is_banned=0")
                users = c.fetchall()
                conn.close()

                temp = json.loads(u["temp_data"] or "{}")
                btn_txt = temp.get("btn_txt", "🔗 Join Now")
                btn_url = temp.get("btn_url", "https://t.me")

                markup = InlineKeyboardMarkup()
                markup.add(ibtn(btn_txt, url=btn_url, style="primary"))

                success = 0
                for u_row in users:
                    try:
                        if message.photo:
                            bot.send_photo(u_row['user_id'], message.photo[-1].file_id, caption=message.caption or "", reply_markup=markup)
                        elif message.video:
                            bot.send_video(u_row['user_id'], message.video.file_id, caption=message.caption or "", reply_markup=markup)
                        else:
                            bot.send_message(u_row['user_id'], txt, parse_mode="Markdown", reply_markup=markup)
                        success += 1
                        time.sleep(0.05)
                    except: pass
                bot.send_message(message.chat.id, f"✅ **Channel Multi-Post Broadcast Complete!** Sent to {success} users.", reply_markup=get_admin_menu())
                update_user_field(uid, "state", None)
                return

            elif state == "admin_deep_search_id":
                if txt.isdigit():
                    t_uid = int(txt)
                    t_user = get_user_db(t_uid)
                    msg = (f"🔍 **User Deep Search & History**\n\n"
                           f"🆔 User ID: `{t_user['user_id']}`\n"
                           f"💰 Balance: ৳{t_user['balance']:.2f}\n"
                           f"📥 Total Withdraw: ৳{t_user['total_withdraw']:.2f}\n"
                           f"👥 Referrals: {t_user['referrals']}\n"
                           f"⏳ Pending Tasks: {t_user['pending_tasks']}\n"
                           f"✅ Approved Tasks: {t_user['approved_tasks']}\n"
                           f"❌ Rejected Tasks: {t_user['rejected_tasks']}\n"
                           f"🌐 IP/Network: `{t_user.get('ip_address', 'N/A')}`\n"
                           f"🚫 Banned Status: {t_user['is_banned']}")
                    
                    markup = InlineKeyboardMarkup(row_width=2)
                    markup.add(
                        ibtn("⛔ Ban User" if not t_user['is_banned'] else "✅ Unban User", callback_data=f"deep_ban_{t_uid}", style="danger"),
                        ibtn("💰 Modify Balance", callback_data=f"deep_bal_{t_uid}", style="success")
                    )
                    bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=markup)
                else: bot.send_message(message.chat.id, "❌ ইনভ্যালিড ইউজার আইডি!")
                update_user_field(uid, "state", None)
                return

            elif state == "admin_add_task_step1":
                temp = {"link": txt}
                update_user_field(uid, "temp_data", json.dumps(temp))
                update_user_field(uid, "state", "admin_add_task_step2")
                bot.send_message(message.chat.id, "📝 **টাস্কের বিবরণ/ডিসক্রিপশন দিন:**")
                return
            elif state == "admin_add_task_step2":
                temp = json.loads(u["temp_data"] or "{}")
                temp["desc"] = txt
                update_user_field(uid, "temp_data", json.dumps(temp))
                update_user_field(uid, "state", "admin_add_task_step3")
                bot.send_message(message.chat.id, "💰 **টাস্কের রিওয়ার্ড অ্যামাউন্ট দিন (যেমন: 5.0):**")
                return
            elif state == "admin_add_task_step3":
                try:
                    rate = float(txt)
                    temp = json.loads(u["temp_data"] or "{}")
                    conn = get_db()
                    c = conn.cursor()
                    c.execute("INSERT INTO tasks (task_type, link, description, rate, task_limit) VALUES ('app_tg', ?, ?, ?, 9999)",
                              (temp.get("link"), temp.get("desc"), rate))
                    conn.commit()
                    conn.close()
                    bot.send_message(message.chat.id, "✅ **নতুন App/TG Task যুক্ত করা হয়েছে!**", reply_markup=get_admin_menu())
                except: bot.send_message(message.chat.id, "❌ ইনভ্যালিড রেট!", reply_markup=get_admin_menu())
                update_user_field(uid, "state", None)
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
                bot.send_message(message.chat.id, f"✅ Video Tutorial for `{cat}` saved successfully!", reply_markup=get_admin_menu())
                return

        if message.photo and state and state.startswith("sub_app_proof_"):
            task_id = state.replace("sub_app_proof_", "")
            sub_id = f"sub_{uid}_{int(time.time())}"
            photo_id = message.photo[-1].file_id
            
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

        if state == "enter_fb_uid":
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
            
            try:
                totp = pyotp.TOTP(txt.replace(" ", "").upper())
                six_digit_code = totp.now()
            except Exception as e:
                log_error(f"2FA Code Generator Error: {e}")
                six_digit_code = "123456"

            temp = json.loads(u["temp_data"] or "{}")
            temp["2fa_secret"] = txt
            temp["six_digit_code"] = six_digit_code
            update_user_field(uid, "temp_data", json.dumps(temp))

            markup = InlineKeyboardMarkup()
            markup.add(ibtn(f"📋 6-Digit Code: {six_digit_code}", callback_data=f"copy_code_{six_digit_code}", style="success"))

            bot.send_message(message.chat.id, f"🔐 **আপনার ইনস্ট্যান্ট ২FA কোড তৈরি হয়েছে:**\n\n`{six_digit_code}`\n\nনিচের বাটন চেপে কোড কপি করুন এবং একাউন্ট খোলা সম্পন্ন করুন:", parse_mode="Markdown", reply_markup=markup)

            reply_kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            reply_kb.add(rbtn("অ্যাকাউন্ট খোলা শেষ", "success"), rbtn("Cancel ❌", "danger"))
            bot.send_message(message.chat.id, "অ্যাকাউন্ট খোলা শেষ হলে নিচের 'অ্যাকাউন্ট খোলা শেষ' বাটনে ক্লিক করুন:", reply_markup=reply_kb)
            update_user_field(uid, "state", None)
            return

        elif state and state.startswith("withdraw_number_"):
            meth = state.replace("withdraw_number_", "")
            w_methods = json.loads(get_config("withdraw_methods", "{}"))
            min_limit = w_methods[meth]["min"]
            max_limit = w_methods[meth].get("max", 10000.0)
            
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
            
            today_str = datetime.now().strftime("%Y-%m-%d")
            last_reset = get_config("last_withdraw_reset_date", "")
            if last_reset != today_str:
                set_config("today_total_withdrawn", "0.0")
                set_config("last_withdraw_reset_date", today_str)

            daily_bot_limit = float(get_config("daily_bot_withdraw_limit", "50000.0"))
            today_total = float(get_config("today_total_withdrawn", "0.0"))

            if today_total + amt > daily_bot_limit:
                bot.send_message(message.chat.id, f"{get_emoji('warning')} **বটের আজকের গ্লোবাল ক্যাশআউট লিমিট পূর্ণ হয়েছে!** অনুগ্রহ করে আগামীকাল আবার চেষ্টা করুন।")
                update_user_field(uid, "state", None)
                return

            with db_lock:
                conn = get_db()
                c = conn.cursor()
                c.execute("INSERT INTO withdraw_requests (req_id, user_id, method, account_number, amount, status, created_at) VALUES (?, ?, ?, ?, ?, 'pending', ?)",
                          (req_id, uid, meth, txt, amt, time.time()))
                c.execute("UPDATE users SET balance = balance - ?, total_withdraw = total_withdraw + ? WHERE user_id=?", (amt, amt, uid))
                conn.commit()
                conn.close()

            set_config("today_total_withdrawn", str(today_total + amt))

            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, f"✅ **আপনার ৳{amt:.2f} এর উইথড্র রিকোয়েস্ট জমা হয়েছে!**\nMethod: {meth}\nAccount: `{txt}`", reply_markup=get_main_menu(uid))

            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                ibtn("✅ Paid", callback_data=f"pay_with_{req_id}", style="success"),
                ibtn("❌ Refund Balance", callback_data=f"ref_with_{req_id}", style="danger")
            )
            admin_alert = f"📥 **New Withdrawal Request!**\n\nReq ID: `{req_id}`\nUser ID: `{uid}`\nMethod: {meth}\nAccount: `{txt}`\nAmount: ৳{amt:.2f}"
            try: bot.send_message(ADMIN_ID, admin_alert, parse_mode="Markdown", reply_markup=markup)
            except: pass
            return

        if txt == TXT_WORK_MAIN:
            bot.send_message(message.chat.id, "💼 **কাজ অপশন নির্বাচন করুন:**", reply_markup=get_work_menu())
        elif txt == TXT_BACK:
            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, "🏠 Main Menu", reply_markup=get_main_menu(uid))

        elif txt == f"{get_emoji('instagram')} ইনস্টাগ্রাম কাজ":
            if get_config("pause_ins", "false") == "true":
                bot.send_message(message.chat.id, f"{get_emoji('warning')} **ইনস্টাগ্রাম কাজ সাময়িক বন্ধ আছে।**")
                return
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
            
            markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(rbtn("🔑 2FA সেট", "primary"), rbtn("Cancel ❌", "danger"))
            bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=markup)

        elif txt == "🔑 2FA সেট":
            update_user_field(uid, "state", "enter_2fa_code")
            bot.send_message(message.chat.id, "🔐 **আপনার 2FA Secret Key টি দিন:**")

        elif txt == "Cancel ❌":
            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, "❌ কাজ বাতিল করা হয়েছে।", reply_markup=get_main_menu(uid))

        elif txt == "অ্যাকাউন্ট খোলা শেষ":
            temp = json.loads(u["temp_data"] or "{}")
            rate = float(get_config("rate_ins", "15.0"))
            sub_id = f"INS-{random.randint(1000, 9999)}"
            
            data_p = {
                "username": temp.get("username"),
                "pass": temp.get("pass"),
                "2fa": temp.get("2fa_secret"),
                "code": temp.get("six_digit_code")
            }
            
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO pending_submissions (id, user_id, sub_type, payload, rate, status, created_at) VALUES (?, ?, 'ins', ?, ?, 'pending', ?)",
                      (sub_id, uid, json.dumps(data_p), rate, time.time()))
            c.execute("UPDATE users SET pending_tasks = pending_tasks + 1 WHERE user_id=?", (uid,))
            conn.commit()
            conn.close()

            append_to_google_sheet("ins", [sub_id, uid, temp.get("username"), temp.get("pass"), temp.get("2fa_secret"), "Pending", datetime.now().strftime("%Y-%m-%d %H:%M")])

            bot.send_message(message.chat.id, f"🎉 **আপনার ইনস্টাগ্রাম অ্যাকাউন্ট সফলভাবে পেন্ডিংয়ে জমা দেওয়া হয়েছে!**\nSubmit ID: `{sub_id}`\nরেট: ৳{rate:.2f}", parse_mode="Markdown", reply_markup=get_main_menu(uid))

        elif txt == f"{get_emoji('facebook')} ফেসবুক কাজ":
            if get_config("pause_fb", "false") == "true":
                bot.send_message(message.chat.id, f"{get_emoji('warning')} **ফেসবুক কাজ সাময়িক বন্ধ আছে।**")
                return
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
            if get_config("pause_gmail", "false") == "true":
                bot.send_message(message.chat.id, f"{get_emoji('warning')} **জিমেইল কাজ সাময়িক বন্ধ আছে।**")
                return
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

        elif txt in ["কাজ শেষ", "বাতিল"]:
            if txt == "বাতিল":
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, "❌ কাজ বাতিল করা হয়েছে।", reply_markup=get_main_menu(uid))
                return

            temp = json.loads(u["temp_data"] or "{}")
            g_email = temp.get("email")
            bot.send_message(message.chat.id, "⏳ **দয়া করে অপেক্ষা করুন, গুগল মেইল সার্ভারে অ্যাকাউন্টের স্থায়িত্ব সাইলেন্টলি ভেরিফাই করা হচ্ছে....**")
            
            if not verify_gmail_smtp(g_email):
                bot.send_message(message.chat.id, f"{get_emoji('error')} **আপনি জিমেইল অ্যাকাউন্টটি তৈরি না করেই 'কাজ শেষ' বাটনে চাপ দিয়েছেন!**\n\nদয়া করে সঠিক নিয়মে অ্যাকাউন্ট তৈরি করে আবার চেষ্টা করুন।", reply_markup=get_main_menu(uid))
                return

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

            bot.send_message(message.chat.id, f"✅ **জিমেইল কাজ সফলভাবে যাচাইপূর্বক জমা নেওয়া হয়েছে!**\nSubmit ID: `{sub_id}`", reply_markup=get_main_menu(uid))

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
                   f"💡 নিয়ম: আপনার লিংক থেকে কোনো ইউজার জয়েন করে ১ম কাজ শেষ করলে পাবেন **৳{bonus}** এবং তার সারাজীবনের কাজের ওপর পাবেন **১০% লাইফটাইম কমিশন**!")
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

        elif txt == TXT_ADMIN_PANEL and check_permission(uid, "admin"):
            bot.send_message(message.chat.id, "⚙️ **Admin Control Panel**", reply_markup=get_admin_menu())

        elif txt == "💰 Set Task Rates" and check_permission(uid, "admin"):
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                ibtn(f"📸 Set Ins Rate (Current: ৳{get_config('rate_ins')})", callback_data="set_rate_ins", style="primary"),
                ibtn(f"📘 Set Fb Rate (Current: ৳{get_config('rate_fb')})", callback_data="set_rate_fb", style="primary"),
                ibtn(f"📧 Set Gmail Rate (Current: ৳{get_config('rate_gmail')})", callback_data="set_rate_gmail", style="primary")
            )
            bot.send_message(message.chat.id, "💰 **কাজের রেট সেটিং:**", reply_markup=markup)

        elif txt == "📢 Set Force Join" and check_permission(uid, "admin"):
            update_user_field(uid, "state", "set_force_join")
            bot.send_message(message.chat.id, "📢 **নতুন চ্যানেল ইউজারনেম ইনপুট দিন (যেমন: @channel1, @channel2):**")

        elif txt == "🎁 Set Ref Bonus" and check_permission(uid, "admin"):
            update_user_field(uid, "state", "set_ref_bonus")
            bot.send_message(message.chat.id, f"🎁 **নতুন রেফার বোনাসের পরিমাণ দিন (বর্তমান: ৳{get_config('ref_bonus')}):**")

        elif txt == "🔑 Set Passwords Base" and check_permission(uid, "admin"):
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                ibtn(f"📸 Ins Base Pass ({get_config('ins_pass')})", callback_data="set_pass_ins", style="primary"),
                ibtn(f"📘 FB Base Pass ({get_config('fb_pass')})", callback_data="set_pass_fb", style="primary"),
                ibtn(f"📧 Gmail Base Pass ({get_config('gmail_pass')})", callback_data="set_pass_gmail", style="primary")
            )
            bot.send_message(message.chat.id, "🔑 **ডায়নামিক পাসওয়ার্ড প্রিফিক্স সেটিং:**", reply_markup=markup)

        elif txt == "💳 Withdraw Setting" and check_permission(uid, "admin"):
            w_methods = json.loads(get_config("withdraw_methods", "{}"))
            markup = InlineKeyboardMarkup(row_width=1)
            for m_name, m_data in w_methods.items():
                st = "ON ✅" if m_data.get("enabled") else "OFF ❌"
                markup.add(ibtn(f"⚙️ {m_name} [{st}]", callback_data=f"cfg_w_menu_{m_name}", style="primary"))
            markup.add(ibtn(f"📊 Daily Total Withdraw Limit (৳{get_config('daily_bot_withdraw_limit')})", callback_data="set_daily_bot_withdraw_limit", style="success"))
            bot.send_message(message.chat.id, "💳 **উইথড্র মেথড ও ক্যাশআউট কনফিগারেশন:**", reply_markup=markup)

        elif txt == "🌀 Spin & Ad Settings" and check_permission(uid, "admin"):
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                ibtn(f"💰 Spin Reward (৳{get_config('spin_reward')})", callback_data="set_spin_reward", style="primary"),
                ibtn(f"🔢 Daily Spin Limit ({get_config('spin_limit')} Times)", callback_data="set_spin_limit", style="primary"),
                ibtn(f"🔗 Adsterra Direct Link", callback_data="set_spin_url", style="primary")
            )
            bot.send_message(message.chat.id, "🌀 **স্পিন ও অ্যাড সেটিং:**", reply_markup=markup)

        elif txt == "📊 Google Sheets Config" and check_permission(uid, "admin"):
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                ibtn("📸 Set Instagram Sheet ID", callback_data="set_sheet_ins", style="primary"),
                ibtn("📘 Set Facebook Sheet ID", callback_data="set_sheet_fb", style="primary"),
                ibtn("📧 Set Gmail Sheet ID", callback_data="set_sheet_gmail", style="primary")
            )
            bot.send_message(message.chat.id, "📊 **গুগল শিটের আইডি কনফিগার করুন:**", reply_markup=markup)

        elif txt == "🤖 Upload JSON Creds" and check_permission(uid, "admin"):
            update_user_field(uid, "state", "set_json_creds")
            bot.send_message(message.chat.id, "🔑 **Google Service Account JSON ফাইল অথবা টেক্সট পেস্ট করে পাঠ পাঠান:**")

        elif txt == "🔥 Set Firebase API" and check_permission(uid, "admin"):
            update_user_field(uid, "state", "set_firebase_api")
            bot.send_message(message.chat.id, "🔥 **Firebase API Key অথবা Config JSON ফাইলটি সরাসরি আপলোড বা টেক্সট আকারে পাঠিয়া দিন:**")

        elif txt == "📧 Set Recovery Email" and check_permission(uid, "admin"):
            update_user_field(uid, "state", "set_recovery_email")
            bot.send_message(message.chat.id, f"📧 **নতুন Recovery Email লিখুন (বর্তমান: `{get_config('recovery_email')}`):**", parse_mode="Markdown")

        elif txt == "🎨 Edit Emoji IDs" and check_permission(uid, "admin"):
            emojis = json.loads(get_config("emojis", "{}"))
            markup = InlineKeyboardMarkup(row_width=2)
            for k, v in emojis.items():
                markup.add(ibtn(f"{k.capitalize()}: {v}", callback_data=f"edit_emoji_{k}", style="primary"))
            bot.send_message(message.chat.id, "🎨 **যে ইমোজি বা কাস্টম প্রিমিয়াম ইমোজি আইডি চেঞ্জ করতে চান সেটিতে চাপ দিন:**", reply_markup=markup)

        elif txt == "🔄 Sync Google Sheet Approval" and check_permission(uid, "admin"):
            bot.send_message(message.chat.id, "⏳ **গুগল শিট থেকে অটো-রিড করে স্ট্যাটাস সিঙ্ক করা হচ্ছে....**")
            count = sync_sheet_approvals()
            bot.send_message(message.chat.id, f"✅ **Google Sheet Auto Sync Complete!** মোট {count} টি কাজ প্রসেসড করা হয়েছে।", reply_markup=get_admin_menu())

        elif txt == "🔎 Pending Approvals" and check_permission(uid, "admin"):
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                ibtn("🔍 Search Approval by ID/2FA/UID", callback_data="search_approval_manual", style="primary"),
                ibtn("📸 Instagram Pending", callback_data="list_pend_ins", style="primary"),
                ibtn("📘 Facebook Pending", callback_data="list_pend_fb", style="primary"),
                ibtn("📧 Gmail Pending", callback_data="list_pend_gmail", style="primary")
            )
            bot.send_message(message.chat.id, "🔎 **Pending Approvals Control Panel:**", reply_markup=markup)

        elif txt == "📥 Pending Withdraws" and check_permission(uid, "admin"):
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT * FROM withdraw_requests WHERE status='pending'")
            reqs = c.fetchall()
            conn.close()

            if not reqs:
                bot.send_message(message.chat.id, "✅ কোনো পেন্ডিং উইথড্র রিকোয়েস্ট নেই!")
                return

            for r in reqs:
                markup = InlineKeyboardMarkup(row_width=2)
                markup.add(
                    ibtn("✅ Paid", callback_data=f"pay_with_{r['req_id']}", style="success"),
                    ibtn("❌ Refund", callback_data=f"ref_with_{r['req_id']}", style="danger")
                )
                bot.send_message(message.chat.id, f"📥 **Req ID:** `{r['req_id']}`\nUser: `{r['user_id']}`\nMethod: {r['method']}\nAccount: `{r['account_number']}`\nAmount: ৳{r['amount']}", parse_mode="Markdown", reply_markup=markup)

        elif txt == "📩 Pending Support Tickets" and check_permission(uid, "admin"):
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

        elif txt == "🔍 User Deep Search" and check_permission(uid, "admin"):
            update_user_field(uid, "state", "admin_deep_search_id")
            bot.send_message(message.chat.id, "🔍 **যার তথ্য বের করতে চান তার Telegram User ID দিন:**")

        elif txt == "📢 Channel Multi-Post Broadcast" and check_permission(uid, "admin"):
            bot.send_message(message.chat.id, "📢 **Multi-Post Configuration:**\n\nপ্রথমে আপনার ইনলাইন বাটন URL লিংক লিখুন (যেমন: https://t.me/example):")
            update_user_field(uid, "state", "set_multipost_url")

        elif txt == "🗑️ Bulk Reject Submissions" and check_permission(uid, "admin"):
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE pending_submissions SET status='rejected' WHERE status='pending'")
            affected = c.rowcount
            conn.commit()
            conn.close()
            log_admin_action(uid, f"Bulk Rejected {affected} Submissions")
            bot.send_message(message.chat.id, f"🗑️ **সফলভাবে মোট {affected} টি পেন্ডিং ফেক কাজ এক ক্লিকে রিজেক্ট করা হয়েছে!**")

        elif txt == "⏸️ Task Pause Manager" and check_permission(uid, "admin"):
            p_gm = "PAUSED 🔴" if get_config("pause_gmail", "false") == "true" else "ACTIVE 🟢"
            p_fb = "PAUSED 🔴" if get_config("pause_fb", "false") == "true" else "ACTIVE 🟢"
            p_ins = "PAUSED 🔴" if get_config("pause_ins", "false") == "true" else "ACTIVE 🟢"
            
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                ibtn(f"Gmail Task: {p_gm}", callback_data="toggle_pause_gmail", style="primary"),
                ibtn(f"Facebook Task: {p_fb}", callback_data="toggle_pause_fb", style="primary"),
                ibtn(f"Instagram Task: {p_ins}", callback_data="toggle_pause_ins", style="primary")
            )
            bot.send_message(message.chat.id, "⏸️ **Task Pause & Status Manager:**", reply_markup=markup)

        elif txt == "🎥 Set Tutorial Videos" and check_permission(uid, "admin"):
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                ibtn("📹 Set Gmail Video", callback_data="set_vid_gmail", style="primary"),
                ibtn("📹 Set FB Video", callback_data="set_vid_fb", style="primary"),
                ibtn("📹 Set Instagram Video", callback_data="set_vid_ins", style="primary")
            )
            bot.send_message(message.chat.id, "🎥 **টিউটোরিয়াল ভিডিও সেটিং:**", reply_markup=markup)

        elif txt == "➕ Add App/TG Task" and check_permission(uid, "admin"):
            update_user_field(uid, "state", "admin_add_task_step1")
            bot.send_message(message.chat.id, "📲 **অ্যাপ বা টেলিগ্রাম চ্যানেলের লিংক দিন:**")

        elif txt == "📩 Smart Broadcast Message" and check_permission(uid, "admin"):
            update_user_field(uid, "state", "admin_broadcast_msg")
            bot.send_message(message.chat.id, "📢 **যে বার্তা বা ছবি সবার কাছে পাঠাতে চান তা লিখুন বা পাঠান:**")

        elif txt == "📊 Bot Statistics" and check_permission(uid, "admin"):
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users")
            total_users = c.fetchone()[0]
            
            day_ago = time.time() - 86400
            c.execute("SELECT COUNT(*) FROM users WHERE last_active >= ?", (day_ago,))
            active_users = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM pending_submissions")
            total_tasks = c.fetchone()[0]
            
            c.execute("SELECT SUM(amount) FROM withdraw_requests WHERE status='approved'")
            tot_withdraw = c.fetchone()[0] or 0.0
            
            c.execute("SELECT SUM(rate) FROM pending_submissions WHERE status='approved'")
            tot_income = c.fetchone()[0] or 0.0
            conn.close()

            msg = (f"📊 **Bot Statistics & Overview**\n\n"
                   f"👥 মোট ইউজার: **{total_users}**\n"
                   f"⚡ ২৪ ঘণ্টায় একটিভ ইউজার: **{active_users}**\n"
                   f"📥 মোট সাবমিটেড টাস্ক: **{total_tasks}**\n"
                   f"💸 মোট পেইড উইথড্র: **৳{tot_withdraw:.2f}**\n"
                   f"💰 বটের মোট বিতরণ করা ইনকাম: **৳{tot_income:.2f}**")
            bot.send_message(message.chat.id, msg, parse_mode="Markdown")

        elif txt == "⛔ Ban/Unban User" and check_permission(uid, "admin"):
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                ibtn("⛔ Ban User", callback_data="btn_ban_u", style="danger"),
                ibtn("✅ Unban User", callback_data="btn_unban_u", style="success")
            )
            bot.send_message(message.chat.id, "⛔ **ব্যান / আনব্যান প্যানেল:**", reply_markup=markup)

        elif txt == "➕ Add/Deduct Balance" and check_permission(uid, "admin"):
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                ibtn("➕ Add Balance", callback_data="btn_add_bal", style="success"),
                ibtn("➖ Deduct Balance", callback_data="btn_ded_bal", style="danger")
            )
            bot.send_message(message.chat.id, "💰 **ইউজার ব্যালেন্স কন্ট্রোল:**", reply_markup=markup)

        elif txt == "👑 Sub-Admin Manager" and uid == ADMIN_ID:
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                ibtn("👑 Make Sub-Admin", callback_data="btn_mod_u", style="primary"),
                ibtn("👤 Remove Sub-Admin", callback_data="btn_unmod_u", style="danger")
            )
            bot.send_message(message.chat.id, "👑 **সাব-এডমিন ম্যানেজমেন্ট:**", reply_markup=markup)

        elif txt == "🧹 Database Cleanup" and check_permission(uid, "admin"):
            old_time = time.time() - (30 * 86400)
            conn = get_db()
            c = conn.cursor()
            c.execute("DELETE FROM pending_submissions WHERE created_at < ? AND status!='pending'", (old_time,))
            c.execute("DELETE FROM withdraw_requests WHERE created_at < ? AND status!='pending'", (old_time,))
            conn.commit()
            conn.close()
            bot.send_message(message.chat.id, "🧹 **৩০ দিনের পুরাতন সকল রিজেক্টেড/কমপ্লিট ডাটা ডিলিট করা হয়েছে!**")

        elif txt == "🚨 Error Logs" and check_permission(uid, "admin"):
            if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 0:
                with open(LOG_FILE, "rb") as f:
                    bot.send_document(message.chat.id, f, caption="🚨 **Error Log File**")
            else:
                bot.send_message(message.chat.id, "✅ **কোনো এরর লগ পাওয়া যায়নি! সিস্টেমে কোনো সমস্যা নেই।**")

        elif txt == "⚡ Maintenance Mode" and check_permission(uid, "admin"):
            curr = get_config("maintenance_mode", "false")
            new_st = "true" if curr == "false" else "false"
            set_config("maintenance_mode", new_st)
            st_txt = "ON 🟢" if new_st == "true" else "OFF 🔴"
            bot.send_message(message.chat.id, f"⚡ **Maintenance Mode set to: {st_txt}**", reply_markup=get_admin_menu())

        elif txt == "📥 Export Unsold Files" and check_permission(uid, "admin"):
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                ibtn("📸 Export Instagram (.csv)", callback_data="export_ins", style="primary"),
                ibtn("📘 Export Facebook (.csv)", callback_data="export_fb", style="primary"),
                ibtn("📧 Export Gmail (.csv)", callback_data="export_gmail", style="primary")
            )
            bot.send_message(message.chat.id, "📥 **কোন Unsold ফাইল ডাউনলোড করতে চান?**", reply_markup=markup)

        elif state == "set_multipost_url":
            temp = json.loads(u["temp_data"] or "{}")
            temp["btn_url"] = txt
            update_user_field(uid, "temp_data", json.dumps(temp))
            update_user_field(uid, "state", "set_multipost_txt")
            bot.send_message(message.chat.id, "📝 **বাটনের টেক্সট লিখুন (যেমন: 🚀 Join Now):**")
            return
        elif state == "set_multipost_txt":
            temp = json.loads(u["temp_data"] or "{}")
            temp["btn_txt"] = txt
            update_user_field(uid, "temp_data", json.dumps(temp))
            update_user_field(uid, "state", "admin_channel_multipost")
            bot.send_message(message.chat.id, "📸 **এখন ব্রডকাস্ট করার পোস্ট (ছবি/ভিডিও/লেখা) সেন্ড করুন:**")
            return
    except Exception as e:
        log_error(f"Error in handle_all_messages: {e}\n{traceback.format_exc()}")

# ============================================
# --- CALLBACK QUERY HANDLERS ---
# ============================================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    try:
        uid = call.from_user.id
        u = get_user_db(uid)

        if uid != ADMIN_ID and call.data != "check_join_event" and not check_force_join(uid):
            bot.answer_callback_query(call.id, "❌ আপনি এখনও চ্যানেলগুলিতে জয়েন করেননি!", show_alert=True)
            return

        if call.data == "check_join_event":
            if check_force_join(uid):
                bot.answer_callback_query(call.id, "✅ সকল চ্যানেলে জয়েন ভেরিফাইড!")
                try: bot.delete_message(call.message.chat.id, call.message.message_id)
                except: pass
                bot.send_message(call.message.chat.id, "🎉 স্বাগতম!", reply_markup=get_main_menu(uid))
            else:
                bot.answer_callback_query(call.id, "❌ আপনি এখনো সকল চ্যানেলে জয়েন করেননি!", show_alert=True)

        elif call.data.startswith("copy_code_"):
            code = call.data.replace("copy_code_", "")
            bot.answer_callback_query(call.id, f"✅ Code copied: {code}", show_alert=True)

        elif call.data == "open_spin_game":
            today_str = datetime.now().strftime("%Y-%m-%d")
            limit = int(get_config("spin_limit", "5"))
            
            if u.get("last_spin_date") != today_str:
                update_user_field(uid, "last_spin_date", today_str)
                update_user_field(uid, "daily_spins", 0)
                u["daily_spins"] = 0

            if u.get("daily_spins", 0) >= limit:
                bot.answer_callback_query(call.id, f"❌ আজকের স্পিন লিমিট ({limit}/{limit}) শেষ!", show_alert=True)
                return

            ad_url = get_config("spin_ad_url", "https://example.com")
            
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                ibtn("🌐 অ্যাড দেখুন (Ad Click Required)", url=ad_url, style="primary"),
                ibtn("🎁 রিওয়ার্ড ভেরিফাই করুন", callback_data="claim_spin_reward_secure", style="success")
            )
            bot.send_message(call.message.chat.id, "⚠️ **স্পিন রিওয়ার্ড সিকিউরিটি চেক:**\n\nনিচের অ্যাড লিংকে ক্লিক করে অ্যাড দেখার পর 'রিওয়ার্ড ভেরিফাই করুন' বাটনে চাপ দিন:", reply_markup=markup)

        elif call.data == "claim_spin_reward_secure":
            limit = int(get_config("spin_limit", "5"))
            reward = float(get_config("spin_reward", "1.5"))
            
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE users SET balance = balance + ?, total_income = total_income + ?, daily_spins = daily_spins + 1 WHERE user_id=?", (reward, reward, uid))
            conn.commit()
            conn.close()

            bot.answer_callback_query(call.id, f"🎉 ভেরিফাইড! আপনি ৳{reward} পেয়েছেন!", show_alert=True)
            bot.send_message(call.message.chat.id, f"🎉 **অভিনন্দন! আপনি সফলভাবে ৳{reward} আয় করেছেন!**\nআজকে আর স্পিন বাকি: {limit - (u.get('daily_spins', 0) + 1)} টি", reply_markup=get_main_menu(uid))

        elif call.data == "open_invite_rewards":
            bonus = get_config("ref_bonus", "10.0")
            msg = f"🎁 **আমন্ত্রণ পুরষ্কার:**\n\nপ্রতিটি সফল রেফারের জন্য আপনি **৳{bonus}** পাবেন এবং আপনার রেফারেল যত কাজ করবে তার ওপর **১০% লাইফটাইম কমিশন** পাবেন!"
            bot.send_message(call.message.chat.id, msg)

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
            except Exception as e:
                log_error(f"Error sending video {cat}: {e}")
                bot.send_message(call.message.chat.id, f"📹 Tutorial Video ID/Link: `{vid_id}`", parse_mode="Markdown")

        elif call.data.startswith("with_meth_"):
            meth = call.data.replace("with_meth_", "")
            update_user_field(uid, "state", f"withdraw_number_{meth}")
            bot.send_message(call.message.chat.id, f"💳 **আপনার {meth} একাউন্ট নাম্বার প্রদান করুন:**")

        elif call.data == "set_rate_ins":
            update_user_field(uid, "state", "set_rate_ins")
            bot.send_message(call.message.chat.id, "📸 **Instagram এর নতুন রেট লিখুন (যেমন: 15.0):**")

        elif call.data == "set_rate_fb":
            update_user_field(uid, "state", "set_rate_fb")
            bot.send_message(call.message.chat.id, "📘 **Facebook এর নতুন রেট লিখুন (যেমন: 18.0):**")

        elif call.data == "set_rate_gmail":
            update_user_field(uid, "state", "set_rate_gmail")
            bot.send_message(call.message.chat.id, "📧 **Gmail এর নতুন রেট লিখুন (যেমন: 12.0):**")

        elif call.data == "set_pass_ins":
            update_user_field(uid, "state", "set_pass_ins")
            bot.send_message(call.message.chat.id, "📸 **Instagram এর ডায়নামিক পাসওয়ার্ড প্রিফিক্স লিখুন:**")

        elif call.data == "set_pass_fb":
            update_user_field(uid, "state", "set_pass_fb")
            bot.send_message(call.message.chat.id, "📘 **Facebook এর ডায়নামিক পাসওয়ার্ড প্রিফিক্স লিখুন:**")

        elif call.data == "set_pass_gmail":
            update_user_field(uid, "state", "set_pass_gmail")
            bot.send_message(call.message.chat.id, "📧 **Gmail এর ডায়নামিক পাসওয়ার্ড প্রিফিক্স লিখুন:**")

        elif call.data == "set_sheet_ins":
            update_user_field(uid, "state", "set_sheet_ins")
            bot.send_message(call.message.chat.id, "📊 **Instagram Sheet ID দিন:**")

        elif call.data == "set_sheet_fb":
            update_user_field(uid, "state", "set_sheet_fb")
            bot.send_message(call.message.chat.id, "📊 **Facebook Sheet ID দিন:**")

        elif call.data == "set_sheet_gmail":
            update_user_field(uid, "state", "set_sheet_gmail")
            bot.send_message(call.message.chat.id, "📊 **Gmail Sheet ID দিন:**")

        elif call.data == "set_spin_reward":
            update_user_field(uid, "state", "set_spin_reward")
            bot.send_message(call.message.chat.id, "💰 **স্পিন এর রিওয়ার্ড কত দিতে চান? (যেমন: 1.5):**")

        elif call.data == "set_spin_limit":
            update_user_field(uid, "state", "set_spin_limit")
            bot.send_message(call.message.chat.id, "🔢 **দৈনিক স্পিনের লিমিট দিন (যেমন: 5):**")

        elif call.data == "set_spin_url":
            update_user_field(uid, "state", "set_spin_url")
            bot.send_message(call.message.chat.id, "🔗 **Adsterra Direct Link টি প্রদান করুন:**")

        elif call.data == "set_daily_bot_withdraw_limit":
            update_user_field(uid, "state", "set_daily_bot_withdraw_limit")
            bot.send_message(call.message.chat.id, "💰 **বটের দৈনিক মোট উইথড্র লিমিট (৳) নির্ধারণ করুন (যেমন: 50000):**")

        elif call.data.startswith("toggle_pause_"):
            target = call.data.replace("toggle_pause_", "")
            curr = get_config(f"pause_{target}", "false")
            new_val = "true" if curr == "false" else "false"
            set_config(f"pause_{target}", new_val)
            bot.answer_callback_query(call.id, f"✅ {target.upper()} Task Status Toggled!")
            bot.send_message(call.message.chat.id, f"⏸️ **{target.upper()} Task is now {'PAUSED' if new_val == 'true' else 'ACTIVE'}**", reply_markup=get_admin_menu())

        elif call.data.startswith("cfg_w_menu_"):
            meth = call.data.replace("cfg_w_menu_", "")
            w_methods = json.loads(get_config("withdraw_methods", "{}"))
            m_data = w_methods[meth]
            st = "OFF ❌" if m_data.get("enabled") else "ON ✅"
            
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                ibtn(f"Toggle Method ({st})", callback_data=f"toggle_w_{meth}", style="danger"),
                ibtn(f"Set Min Limit (Current: ৳{m_data['min']})", callback_data=f"min_w_{meth}", style="primary"),
                ibtn(f"Set Max Limit (Current: ৳{m_data.get('max', 10000)})", callback_data=f"max_w_{meth}", style="primary")
            )
            bot.send_message(call.message.chat.id, f"⚙️ **{meth} Configuration:**", reply_markup=markup)

        elif call.data.startswith("toggle_w_"):
            meth = call.data.replace("toggle_w_", "")
            w_methods = json.loads(get_config("withdraw_methods", "{}"))
            w_methods[meth]["enabled"] = not w_methods[meth]["enabled"]
            set_config("withdraw_methods", json.dumps(w_methods))
            bot.send_message(call.message.chat.id, f"✅ {meth} Toggled!", reply_markup=get_admin_menu())

        elif call.data.startswith("min_w_"):
            meth = call.data.replace("min_w_", "")
            update_user_field(uid, "state", f"cfg_w_min_{meth}")
            bot.send_message(call.message.chat.id, f"💰 **{meth} এর জন্য নতুন Minimum Limit দিন:**")

        elif call.data.startswith("max_w_"):
            meth = call.data.replace("max_w_", "")
            update_user_field(uid, "state", f"cfg_w_max_{meth}")
            bot.send_message(call.message.chat.id, f"💰 **{meth} এর জন্য নতুন Maximum Limit দিন:**")

        elif call.data == "btn_ban_u":
            update_user_field(uid, "state", "admin_ban_user")
            bot.send_message(call.message.chat.id, "⛔ **ব্যান করার জন্য ইউজার ID দিন:**")

        elif call.data == "btn_unban_u":
            update_user_field(uid, "state", "admin_unban_user")
            bot.send_message(call.message.chat.id, "✅ **আনব্যান করার জন্য ইউজার ID দিন:**")

        elif call.data == "btn_mod_u":
            update_user_field(uid, "state", "admin_mod_user")
            bot.send_message(call.message.chat.id, "👑 **সাব-এডমিন বানানোর জন্য ইউজার ID দিন:**")

        elif call.data == "btn_unmod_u":
            update_user_field(uid, "state", "admin_unmod_user")
            bot.send_message(call.message.chat.id, "👤 **সাব-এডমিন সরানোর জন্য ইউজার ID দিন:**")

        elif call.data == "btn_add_bal":
            update_user_field(uid, "state", "admin_add_bal_id")
            bot.send_message(call.message.chat.id, "💰 **যার সাথে ব্যালেন্স যোগ করবেন তার ইউজার ID দিন:**")

        elif call.data == "btn_ded_bal":
            update_user_field(uid, "state", "admin_ded_bal_id")
            bot.send_message(call.message.chat.id, "💰 **যার থেকে ব্যালেন্স কাটবেন তার ইউজার ID দিন:**")

        elif call.data.startswith("deep_ban_"):
            t_uid = int(call.data.replace("deep_ban_", ""))
            t_u = get_user_db(t_uid)
            new_st = 0 if t_u['is_banned'] else 1
            update_user_field(t_uid, "is_banned", new_st)
            log_admin_action(uid, f"Toggled Ban status for {t_uid}")
            bot.answer_callback_query(call.id, f"✅ User Status Updated!")

        elif call.data.startswith("deep_bal_"):
            t_uid = call.data.replace("deep_bal_", "")
            temp = json.loads(u["temp_data"] or "{}")
            temp["target_user"] = t_uid
            update_user_field(uid, "temp_data", json.dumps(temp))
            update_user_field(uid, "state", "admin_add_bal_amt")
            bot.send_message(call.message.chat.id, "💰 **নতুন ব্যালেন্স পরিমাণ লিখুন:**")

        elif call.data.startswith("list_pend_"):
            stype = call.data.replace("list_pend_", "")
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT * FROM pending_submissions WHERE sub_type=? AND status='pending' LIMIT 10", (stype,))
            subs = c.fetchall()
            conn.close()

            if not subs:
                bot.answer_callback_query(call.id, f"✅ {stype.upper()} এর কোনো পেন্ডিং সাবমিশন নেই!", show_alert=True)
                return

            for s in subs:
                markup = InlineKeyboardMarkup(row_width=2)
                markup.add(
                    ibtn("✅ Approve", callback_data=f"app_sub_{s['id']}", style="success"),
                    ibtn("❌ Reject", callback_data=f"rej_sub_{s['id']}", style="danger")
                )
                bot.send_message(call.message.chat.id, f"🔎 **ID:** `{s['id']}`\nUser: `{s['user_id']}`\nPayload: `{s['payload']}`", parse_mode="Markdown", reply_markup=markup)

        elif call.data.startswith("app_sub_"):
            sub_id = call.data.replace("app_sub_", "")
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT * FROM pending_submissions WHERE id=? AND status='pending'", (sub_id,))
            sub = c.fetchone()
            
            if sub:
                sub = dict(sub)
                uid_t = sub['user_id']
                rate = sub['rate']
                
                c.execute("UPDATE pending_submissions SET status='approved' WHERE id=?", (sub_id,))
                c.execute("UPDATE users SET balance = balance + ?, total_income = total_income + ?, approved_tasks = approved_tasks + 1, pending_tasks = MAX(0, pending_tasks - 1) WHERE user_id=?", (rate, rate, uid_t))
                
                c.execute("SELECT referred_by FROM users WHERE user_id=?", (uid_t,))
                u_ref = c.fetchone()
                if u_ref and u_ref[0]:
                    ref_id = u_ref[0]
                    ref_comm = rate * 0.10
                    c.execute("UPDATE users SET balance = balance + ?, total_income = total_income + ? WHERE user_id=?", (ref_comm, ref_comm, ref_id))
                    try: bot.send_message(ref_id, f"🎉 **রেফারেল ১০% কমিশন!** আপনার রেফারেল একটি কাজ সম্পন্ন করায় আপনি **৳{ref_comm:.2f}** কমিশন পেয়েছেন!")
                    except: pass

                conn.commit()
                log_admin_action(uid, f"Approved Task {sub_id}")
                bot.answer_callback_query(call.id, "✅ Task Approved!")
                try: bot.send_message(uid_t, f"✅ **আপনার কাজ এপ্রুভ করা হয়েছে!**\nSubmit ID: `{sub_id}`\nযোগ করা হয়েছে: ৳{rate}")
                except: pass
            else:
                bot.answer_callback_query(call.id, "❌ Task Already Processed!", show_alert=True)
            conn.close()

        elif call.data.startswith("rej_sub_"):
            sub_id = call.data.replace("rej_sub_", "")
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT * FROM pending_submissions WHERE id=? AND status='pending'", (sub_id,))
            sub = c.fetchone()
            
            if sub:
                sub = dict(sub)
                uid_t = sub['user_id']
                
                c.execute("UPDATE pending_submissions SET status='rejected' WHERE id=?", (sub_id,))
                c.execute("UPDATE users SET rejected_tasks = rejected_tasks + 1, pending_tasks = MAX(0, pending_tasks - 1) WHERE user_id=?", (uid_t,))
                conn.commit()
                log_admin_action(uid, f"Rejected Task {sub_id}")
                bot.answer_callback_query(call.id, "❌ Task Rejected!")
                try: bot.send_message(uid_t, f"❌ **আপনার কাজ রিজেক্ট করা হয়েছে!**\nSubmit ID: `{sub_id}`")
                except: pass
            else:
                bot.answer_callback_query(call.id, "❌ Task Already Processed!", show_alert=True)
            conn.close()

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
            bot.send_message(call.message.chat.id, f"💬 **Ticket `{t_id}` এর জন্য আপনার উত্তরটি লিখুন:**", parse_mode="Markdown")

        elif call.data.startswith("pay_with_"):
            req_id = call.data.replace("pay_with_", "")
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT * FROM withdraw_requests WHERE req_id=? AND status='pending'", (req_id,))
            w = c.fetchone()
            if w:
                w = dict(w)
                c.execute("UPDATE withdraw_requests SET status='approved' WHERE req_id=?", (req_id,))
                conn.commit()
                log_admin_action(uid, f"Approved Withdrawal Request {req_id}")
                bot.answer_callback_query(call.id, "✅ Withdrawal Approved!")
                try: bot.send_message(w['user_id'], f"🎉 **আপনার উইথড্র রিকোয়েস্ট এপ্রুভ ও পেমেন্ট সম্পন্ন করা হয়েছে!**\nReq ID: `{req_id}`\nAmount: ৳{w['amount']}")
                except: pass
            else:
                bot.answer_callback_query(call.id, "❌ Request Already Processed!", show_alert=True)
            conn.close()

        elif call.data.startswith("ref_with_"):
            req_id = call.data.replace("ref_with_", "")
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT * FROM withdraw_requests WHERE req_id=? AND status='pending'", (req_id,))
            w = c.fetchone()
            if w:
                w = dict(w)
                uid_t = w['user_id']
                amt = w['amount']
                c.execute("UPDATE withdraw_requests SET status='rejected' WHERE req_id=?", (req_id,))
                c.execute("UPDATE users SET balance = balance + ?, total_withdraw = MAX(0, total_withdraw - ?) WHERE user_id=?", (amt, amt, uid_t))
                conn.commit()
                log_admin_action(uid, f"Refunded Withdrawal Request {req_id}")
                bot.answer_callback_query(call.id, "❌ Withdrawal Refunded!")
                try: bot.send_message(uid_t, f"⚠️ **আপনার ৳{amt} উইথড্র রিজেক্ট করা হয়েছে এবং ব্যালেন্স ফেরত দেওয়া হয়েছে!**\nReq ID: `{req_id}`")
                except: pass
            else:
                bot.answer_callback_query(call.id, "❌ Request Already Processed!", show_alert=True)
            conn.close()

        elif call.data.startswith("set_vid_"):
            cat = call.data.replace("set_vid_", "")
            update_user_field(uid, "state", f"set_vid_{cat}")
            bot.send_message(call.message.chat.id, f"📹 **{cat.upper()} এর জন্য নতুন Tutorial Video (ফাইল/আইডি/লিংক) সেন্ড করুন:**")

        elif call.data.startswith("export_"):
            stype = call.data.replace("export_", "")
            csv_data = export_unsold_csv(stype)
            
            if csv_data:
                bio = io.BytesIO(csv_data.encode('utf-8'))
                bio.name = f"unsold_{stype}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                bot.send_document(call.message.chat.id, bio, caption=f"📥 **Unsold {stype.upper()} Accounts Export File**")
            else:
                bot.answer_callback_query(call.id, "❌ কোনো Unsold ডাটা পাওয়া যায়নি!", show_alert=True)

    except Exception as e:
        log_error(f"Error in handle_callbacks: {e}\n{traceback.format_exc()}")

# ============================================
# --- BOT EXECUTION LOOP ---
# ============================================
if __name__ == '__main__':
    keep_alive()
    print("🤖 EASY EARN BD Engine Starting Polling...")
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception as e:
            log_error(f"Polling Crashed: {e}\n{traceback.format_exc()}")
            time.sleep(3)
