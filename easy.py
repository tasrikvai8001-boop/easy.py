import importlib.util
import subprocess
import sys
import json
import os
import time
import random
import string
import threading
import traceback
import smtplib
import csv
import io
import pyotp
from datetime import datetime, timedelta

# --- AUTOMATIC DEPENDENCY CHECK ---
required_pkgs = ["flask", "pyTelegramBotAPI", "gspread", "oauth2client", "pyotp", "requests"]
for pkg in required_pkgs:
    mod = "telebot" if pkg == "pyTelegramBotAPI" else pkg
    if importlib.util.find_spec(mod) is None:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

from flask import Flask
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests

# ============================================
# --- WEB SERVER FOR KEEP-ALIVE ---
# ============================================
app = Flask('')

@app.route('/')
def home():
    return "EASY EARN BD Engine is Running 24/7 with Firebase Realtime DB!"

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
LOG_FILE = "error_logs.txt"
JSON_CREDS_FILE = "credentials.json"

bot = telebot.TeleBot(TOKEN, num_threads=50)
db_lock = threading.RLock()

# ============================================
# --- FIREBASE REALTIME DATABASE REST ENGINE ---
# ============================================
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyBGABXnrP66oCndR0a6Hza3m2pehk2JgcE",
    "authDomain": "fast-cash-out.firebaseapp.com",
    "databaseURL": "https://fast-cash-out-default-rtdb.firebaseio.com",
    "projectId": "fast-cash-out",
    "storageBucket": "fast-cash-out.firebasestorage.app",
    "messagingSenderId": "860839345974",
    "appId": "1:860839345974:web:25c10d619e5c71d0297d97",
    "measurementId": "G-1JSWJVREF2"
}

FB_DB_URL = FIREBASE_CONFIG["databaseURL"]

def fb_get(path):
    try:
        r = requests.get(f"{FB_DB_URL}/{path}.json", timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        log_error(f"Firebase GET Error [{path}]: {e}")
        return None

def fb_put(path, data):
    try:
        r = requests.put(f"{FB_DB_URL}/{path}.json", json=data, timeout=10)
        return r.status_code == 200
    except Exception as e:
        log_error(f"Firebase PUT Error [{path}]: {e}")
        return False

def fb_patch(path, data):
    try:
        r = requests.patch(f"{FB_DB_URL}/{path}.json", json=data, timeout=10)
        return r.status_code == 200
    except Exception as e:
        log_error(f"Firebase PATCH Error [{path}]: {e}")
        return False

def fb_delete(path):
    try:
        r = requests.delete(f"{FB_DB_URL}/{path}.json", timeout=10)
        return r.status_code == 200
    except Exception as e:
        log_error(f"Firebase DELETE Error [{path}]: {e}")
        return False

# --- ERROR & AUDIT LOGGERS ---
def log_error(err_msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {err_msg}\n{'-'*40}\n")

def log_admin_action(admin_id, action_desc):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = (f"<b>🛡️ Admin Audit Log</b>\n\n"
           f"<b>👤 Admin:</b> <code>{admin_id}</code>\n"
           f"<b>📝 Action:</b> {action_desc}\n"
           f"<b>⏰ Time:</b> <code>{timestamp}</code>")
    try:
        bot.send_message(ADMIN_ID, msg, parse_mode="HTML")
    except:
        pass

# ============================================
# --- DATABASE INITIALIZATION & CONFIG ---
# ============================================
def init_db():
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
        "firebase_api": FIREBASE_CONFIG["apiKey"],
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
    
    current_cfg = fb_get("config") or {}
    for k, v in defaults.items():
        if k not in current_cfg:
            fb_put(f"config/{k}", str(v))

init_db()

def get_config(key, default=""):
    val = fb_get(f"config/{key}")
    return str(val) if val is not None else str(default)

def set_config(key, value):
    with db_lock:
        fb_put(f"config/{key}", str(value))

def get_user_db(user_id):
    user_id_str = str(user_id)
    u = fb_get(f"users/{user_id_str}")
    now = time.time()
    
    if not u:
        u = {
            "user_id": int(user_id),
            "balance": 0.0,
            "total_income": 0.0,
            "total_withdraw": 0.0,
            "referrals": 0,
            "referred_by": None,
            "ref_rewarded": 0,
            "state": None,
            "temp_data": "{}",
            "role": "user",
            "permissions": "{}",
            "is_banned": 0,
            "approved_tasks": 0,
            "rejected_tasks": 0,
            "pending_tasks": 0,
            "completed_accounts": 0,
            "last_spin_time": 0,
            "daily_spins": 0,
            "last_spin_date": "",
            "last_active": now,
            "ip_address": None,
            "created_at": now
        }
        fb_put(f"users/{user_id_str}", u)
    else:
        fb_patch(f"users/{user_id_str}", {"last_active": now})
        u["last_active"] = now
    return u

def update_user_field(user_id, field, value):
    with db_lock:
        user_id_str = str(user_id)
        fb_patch(f"users/{user_id_str}", {field: value})

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
    all_pending = fb_get("pending_submissions") or {}

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

                sub = all_pending.get(sub_id)
                if sub and sub.get("status") == "pending":
                    uid = sub['user_id']
                    rate = float(sub['rate'])

                    if status_val in ["ok", "approved"]:
                        fb_patch(f"pending_submissions/{sub_id}", {"status": "approved"})
                        
                        u = get_user_db(uid)
                        new_bal = u['balance'] + rate
                        new_inc = u['total_income'] + rate
                        app_t = u['approved_tasks'] + 1
                        pend_t = max(0, u['pending_tasks'] - 1)
                        
                        fb_patch(f"users/{uid}", {
                            "balance": new_bal, "total_income": new_inc,
                            "approved_tasks": app_t, "pending_tasks": pend_t
                        })
                        
                        ref_id = u.get("referred_by")
                        if ref_id:
                            ref_u = get_user_db(ref_id)
                            ref_comm = rate * 0.10
                            fb_patch(f"users/{ref_id}", {
                                "balance": ref_u['balance'] + ref_comm,
                                "total_income": ref_u['total_income'] + ref_comm
                            })
                            try: bot.send_message(ref_id, f"<b>🎉 রেফারেল ১০% কমিশন!</b>\nআপনার রেফারেল একটি কাজ সম্পন্ন করায় আপনি <b>৳{ref_comm:.2f}</b> কমিশন পেয়েছেন!", parse_mode="HTML")
                            except: pass

                        try: bot.send_message(uid, f"<b>✅ আপনার কাজ এপ্রুভ হয়েছে!</b>\nSubmit ID: <code>{sub_id}</code>\nব্যালেন্সে যোগ করা হয়েছে: <b>৳{rate:.2f}</b>", parse_mode="HTML")
                        except: pass

                    elif status_val in ["bad", "rejected"]:
                        fb_patch(f"pending_submissions/{sub_id}", {"status": "rejected"})
                        u = get_user_db(uid)
                        rej_t = u['rejected_tasks'] + 1
                        pend_t = max(0, u['pending_tasks'] - 1)
                        fb_patch(f"users/{uid}", {"rejected_tasks": rej_t, "pending_tasks": pend_t})
                        try: bot.send_message(uid, f"<b>❌ আপনার কাজ রিজেক্ট করা হয়েছে!</b>\nSubmit ID: <code>{sub_id}</code>", parse_mode="HTML")
                        except: pass

                    processed_count += 1
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
        val_clean = val.replace("/", "_").replace(".", "_").replace("#", "_").replace("$", "_")
        existing = fb_get(f"submitted_records/{val_clean}")
        if existing:
            return True
        rec = {
            "record_value": val,
            "record_type": record_type,
            "user_id": uid,
            "submitted_at": time.time()
        }
        fb_put(f"submitted_records/{val_clean}", rec)
        return False

def get_daily_withdraw_count(user_id):
    reqs = fb_get("withdraw_requests") or {}
    day_start = time.time() - 86400
    cnt = 0
    for r in reqs.values():
        if r.get("user_id") == user_id and r.get("created_at", 0) >= day_start:
            cnt += 1
    return cnt

def get_daily_support_count(user_id):
    tickets = fb_get("support_tickets") or {}
    day_start = time.time() - 86400
    cnt = 0
    for t in tickets.values():
        if t.get("user_id") == user_id and t.get("created_at", 0) >= day_start:
            cnt += 1
    return cnt

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
    markup.add(rbtn("🗑️ Sold & Batch Delete", "danger"), rbtn("🔎 Pending Approvals", "primary"))
    markup.add(rbtn("📥 Pending Withdraws", "primary"), rbtn("📩 Pending Support Tickets", "primary"))
    markup.add(rbtn("➕ Add App/TG Task", "success"), rbtn("📩 Smart Broadcast Message", "primary"))
    markup.add(rbtn("📊 Bot Statistics", "primary"), rbtn("⛔ Ban/Unban User", "danger"))
    markup.add(rbtn("➕ Add/Deduct Balance", "success"), rbtn("👑 Sub-Admin Manager", "primary"))
    markup.add(rbtn("📧 Set Recovery Email", "primary"), rbtn("🎥 Set Tutorial Videos", "primary"))
    markup.add(rbtn("🔍 User Deep Search", "primary"), rbtn("📢 Channel Multi-Post Broadcast", "primary"))
    markup.add(rbtn("🗑️ Bulk Reject Submissions", "danger"), rbtn("⏸️ Task Pause Manager", "primary"))
    markup.add(rbtn("🧹 Database Cleanup", "danger"), rbtn("🚨 Error Logs", "danger"))
    markup.add(rbtn("⚡ Maintenance Mode", "danger"), rbtn(TXT_BACK, "danger"))
    return markup

# ============================================
# --- CRON / RE-ENGAGEMENT BACKGROUND THREAD ---
# ============================================
def automated_reengagement_cron():
    while True:
        try:
            time.sleep(86400)
            users = fb_get("users") or {}
            three_days_ago = time.time() - (3 * 86400)

            for uid, u_row in users.items():
                if u_row.get("last_active", 0) <= three_days_ago and not u_row.get("is_banned"):
                    try:
                        msg = "<b>👋 আমরা আপনাকে মিস করছি!</b>\n\nআপনার জন্য নতুন ফেসবুক ও জিমেইল টাস্ক অপেক্ষা করছে। এখনই বটে লগইন করে কাজ করে আয় করুন! 💰"
                        bot.send_message(int(uid), msg, parse_mode="HTML")
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
            bot.send_message(message.chat.id, f"{get_emoji('warning')} <b>বট বর্তমানে মেইনটেন্যান্স মোডে আছে।</b> খুব শীঘ্রই আবার কাজ চালু হবে।", parse_mode="HTML")
            return

        u = get_user_db(uid)
        if u["is_banned"]:
            bot.send_message(message.chat.id, f"{get_emoji('error')} <b>আপনি এই বটে ব্লকড আছেন!</b>", parse_mode="HTML")
            return

        args = message.text.split()
        if len(args) > 1 and not u["referred_by"]:
            ref_id = args[1]
            if ref_id.isdigit() and int(ref_id) != uid:
                ref_user = get_user_db(int(ref_id))
                if u.get("ip_address") and u.get("ip_address") == ref_user.get("ip_address"):
                    bot.send_message(uid, f"{get_emoji('warning')} <b>সতর্কবার্তা:</b> একই ডিভাইস/নেটওয়ার্ক থেকে একাধিক অ্যাকাউন্ট খোলা সনাক্ত হয়েছে! রেফার বোনাস যোগ হবে না।", parse_mode="HTML")
                    bot.send_message(ADMIN_ID, f"🚨 <b>Multi-Account Alert!</b>\nUser <code>{uid}</code> joined via Ref <code>{ref_id}</code> from the same Network/IP!", parse_mode="HTML")
                else:
                    update_user_field(uid, "referred_by", int(ref_id))

        question, ans = generate_captcha()
        temp = json.loads(u["temp_data"] or "{}")
        temp["captcha_ans"] = ans
        update_user_field(uid, "temp_data", json.dumps(temp))
        update_user_field(uid, "state", "verify_captcha")

        bot.send_message(message.chat.id, f"🤖 <b>বট সিকিউরিটি ভেরিফিকেশন:</b>\n\nদয়া করে গাণিতিক উত্তরটি দিন:\n👉 <b>{question}</b>", parse_mode="HTML")
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

        # STATE OVERRIDE IF NAVIGATION BUTTON CLICKED (Prevents Stuck State)
        all_menu_buttons = [
            TXT_WORK_MAIN, TXT_TODAY_WORK, TXT_BALANCE, TXT_WITHDRAW, 
            TXT_REFER, TXT_SUPPORT, TXT_NEWBIE, TXT_ADMIN_PANEL, TXT_BACK,
            f"{get_emoji('instagram')} ইনস্টাগ্রাম কাজ", f"{get_emoji('facebook')} ফেসবুক কাজ", 
            f"{get_emoji('gmail')} Gmail কাজ"
        ]
        
        if txt in all_menu_buttons and u.get("state") not in ["verify_captcha"]:
            update_user_field(uid, "state", None)
            u["state"] = None

        state = u.get("state")

        # Captcha Check First
        if state == "verify_captcha":
            temp = json.loads(u["temp_data"] or "{}")
            c_ans = temp.get("captcha_ans")
            if txt == c_ans:
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, "<b>✅ ক্যাপচা ভেরিফিকেশন সফল হয়েছে!</b>", parse_mode="HTML")
                
                if u.get("referred_by") and u.get("ref_rewarded") == 0:
                    ref_id = u.get("referred_by")
                    fname = message.from_user.first_name
                    ref_msg = (f"<b>🎉 নতুন রেফারেল নোটিফিকেশন!</b>\n\n"
                               f"আপনার রেফার লিংক ব্যবহার করে <b>{fname}</b> বটে জয়েন করেছে।\n\n"
                               f"👉 <b>দয়া করে তাকে একটি জিমেইল এর কাজ করতে বলেন তাহলে ১০ টাকা বোনাস পাবেন এবং সে যত কাজ করবে আপনি ১০% বোনাস পাবেন সারাজীবন।</b>")
                    try: bot.send_message(ref_id, ref_msg, parse_mode="HTML")
                    except: pass
                
                if not check_force_join(uid):
                    msg = f"<b>👋 Welcome to {BOT_NAME}!</b>\n\nবটের কাজ করার জন্য নিচের চ্যানেলগুলোতে জয়েন করুন এবং 'Verify Now' চাপুন:"
                    bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=get_force_join_markup())
                    return
                else:
                    bot.send_message(message.chat.id, f"<b>💎 Welcome to {BOT_NAME}!</b>\nনিচের প্রিমিয়াম মেনু থেকে আপনার পছন্দ বেছে নিন:", parse_mode="HTML", reply_markup=get_main_menu(uid))
                    return
            else:
                question, ans = generate_captcha()
                temp["captcha_ans"] = ans
                update_user_field(uid, "temp_data", json.dumps(temp))
                bot.send_message(message.chat.id, f"<b>❌ ভুল উত্তর!</b> আবার চেষ্টা করুন:\n👉 <b>{question}</b>", parse_mode="HTML")
                return

        # Force Join Real-time Enforcement Guard
        if uid != ADMIN_ID and not check_force_join(uid):
            bot.send_message(message.chat.id, f"{get_emoji('warning')} <b>কাজ শুরু করার আগে অবশ্যই আপনাকে আমাদের অফিসিয়াল চ্যানেলগুলোতে জয়েন করতে হবে!</b>", parse_mode="HTML", reply_markup=get_force_join_markup())
            return

        if u["is_banned"]: return

        # --- ADMIN STATES ---
        if state and check_permission(uid, "admin"):
            if state == "set_rate_ins":
                set_config("rate_ins", txt)
                update_user_field(uid, "state", None)
                log_admin_action(uid, f"Set Ins Rate to ৳{txt}")
                bot.send_message(message.chat.id, f"<b>✅ Instagram Rate set to: ৳{txt}</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                return
            elif state == "set_rate_fb":
                set_config("rate_fb", txt)
                update_user_field(uid, "state", None)
                log_admin_action(uid, f"Set FB Rate to ৳{txt}")
                bot.send_message(message.chat.id, f"<b>✅ Facebook Rate set to: ৳{txt}</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                return
            elif state == "set_rate_gmail":
                set_config("rate_gmail", txt)
                update_user_field(uid, "state", None)
                log_admin_action(uid, f"Set Gmail Rate to ৳{txt}")
                bot.send_message(message.chat.id, f"<b>✅ Gmail Rate set to: ৳{txt}</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                return
            elif state == "set_sheet_ins":
                set_config("sheet_id_ins", txt)
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, "<b>✅ Instagram Sheet ID Saved!</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                return
            elif state == "set_sheet_fb":
                set_config("sheet_id_fb", txt)
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, "<b>✅ Facebook Sheet ID Saved!</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                return
            elif state == "set_sheet_gmail":
                set_config("sheet_id_gmail", txt)
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, "<b>✅ Gmail Sheet ID Saved!</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                return
            elif state == "set_json_creds":
                if message.document:
                    file_info = bot.get_file(message.document.file_id)
                    downloaded_file = bot.download_file(file_info.file_path)
                    set_config("json_credentials", downloaded_file.decode('utf-8'))
                else:
                    set_config("json_credentials", txt)
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, "<b>✅ Google Cloud Service Account JSON Saved!</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                return
            elif state == "set_firebase_api":
                if message.document:
                    file_info = bot.get_file(message.document.file_id)
                    downloaded_file = bot.download_file(file_info.file_path)
                    set_config("firebase_api", downloaded_file.decode('utf-8'))
                else:
                    set_config("firebase_api", txt)
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, "<b>✅ Firebase API Key / Config JSON Updated Successfully!</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                return
            elif state == "set_recovery_email":
                set_config("recovery_email", txt)
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, f"<b>✅ Recovery Email Set to:</b> <code>{txt}</code>", parse_mode="HTML", reply_markup=get_admin_menu())
                return
            elif state == "set_ref_bonus":
                set_config("ref_bonus", txt)
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, f"<b>✅ Refer Bonus Set to: ৳{txt}</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                return
            elif state == "set_pass_ins":
                set_config("ins_pass", txt)
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, f"<b>✅ Instagram Password Base Set to:</b> <code>{txt}</code>", parse_mode="HTML", reply_markup=get_admin_menu())
                return
            elif state == "set_pass_fb":
                set_config("fb_pass", txt)
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, f"<b>✅ Facebook Password Base Set to:</b> <code>{txt}</code>", parse_mode="HTML", reply_markup=get_admin_menu())
                return
            elif state == "set_pass_gmail":
                set_config("gmail_pass", txt)
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, f"<b>✅ Gmail Password Base Set to:</b> <code>{txt}</code>", parse_mode="HTML", reply_markup=get_admin_menu())
                return
            elif state == "set_force_join":
                chs = [c.strip() for c in txt.split(",") if c.strip()]
                set_config("force_channels", json.dumps(chs))
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, f"<b>✅ Force Join Channels Updated to: {chs}</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                return
            elif state == "remove_force_join_ch":
                chs = json.loads(get_config("force_channels", "[]"))
                if txt in chs:
                    chs.remove(txt)
                    set_config("force_channels", json.dumps(chs))
                    bot.send_message(message.chat.id, f"<b>✅ {txt} চ্যানেলটি সফলভাবে রিমুভ করা হয়েছে!</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                else:
                    bot.send_message(message.chat.id, "<b>❌ চ্যানেলটি লিস্টে পাওয়া যায়নি!</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                update_user_field(uid, "state", None)
                return
            elif state == "set_spin_reward":
                set_config("spin_reward", txt)
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, f"<b>✅ Spin Reward Set to: ৳{txt}</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                return
            elif state == "set_spin_limit":
                set_config("spin_limit", txt)
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, f"<b>✅ Spin Daily Limit Set to: {txt} Times</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                return
            elif state == "set_spin_url":
                set_config("spin_ad_url", txt)
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, f"<b>✅ Adsterra Direct Link Set to:</b> <code>{txt}</code>", parse_mode="HTML", reply_markup=get_admin_menu())
                return
            elif state == "admin_ban_user":
                if txt.isdigit():
                    update_user_field(int(txt), "is_banned", 1)
                    log_admin_action(uid, f"Banned User {txt}")
                    bot.send_message(message.chat.id, f"<b>⛔ User <code>{txt}</code> has been BANNED!</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                else: bot.send_message(message.chat.id, "<b>❌ ইনভ্যালিড ইউজার আইডি!</b>", parse_mode="HTML")
                update_user_field(uid, "state", None)
                return
            elif state == "admin_unban_user":
                if txt.isdigit():
                    update_user_field(int(txt), "is_banned", 0)
                    log_admin_action(uid, f"Unbanned User {txt}")
                    bot.send_message(message.chat.id, f"<b>✅ User <code>{txt}</code> has been UNBANNED!</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                else: bot.send_message(message.chat.id, "<b>❌ ইনভ্যালিড ইউজার আইডি!</b>", parse_mode="HTML")
                update_user_field(uid, "state", None)
                return
            elif state == "admin_mod_user":
                if txt.isdigit():
                    perms = {"withdraw": True, "tasks": True, "support": True}
                    update_user_field(int(txt), "role", "sub_admin")
                    update_user_field(int(txt), "permissions", json.dumps(perms))
                    log_admin_action(uid, f"Made Sub-Admin User {txt}")
                    bot.send_message(message.chat.id, f"<b>👑 User <code>{txt}</code> updated to Sub-Admin!</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                else: bot.send_message(message.chat.id, "<b>❌ ইনভ্যালিড ইউজার আইডি!</b>", parse_mode="HTML")
                update_user_field(uid, "state", None)
                return
            elif state == "admin_unmod_user":
                if txt.isdigit():
                    update_user_field(int(txt), "role", "user")
                    log_admin_action(uid, f"Demoted Sub-Admin User {txt}")
                    bot.send_message(message.chat.id, f"<b>👤 User <code>{txt}</code> demoted to General User!</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                else: bot.send_message(message.chat.id, "<b>❌ ইনভ্যালিড ইউজার আইডি!</b>", parse_mode="HTML")
                update_user_field(uid, "state", None)
                return
            elif state == "admin_add_bal_id":
                temp = json.loads(u["temp_data"] or "{}")
                temp["target_user"] = txt
                update_user_field(uid, "temp_data", json.dumps(temp))
                update_user_field(uid, "state", "admin_add_bal_amt")
                bot.send_message(message.chat.id, "<b>💰 কত টাকা ব্যালেন্স যোগ করতে চান? (যেমন: 50):</b>", parse_mode="HTML")
                return
            elif state == "admin_add_bal_amt":
                try:
                    amt = float(txt)
                    temp = json.loads(u["temp_data"] or "{}")
                    target = int(temp.get("target_user"))
                    t_user = get_user_db(target)
                    new_b = t_user["balance"] + amt
                    update_user_field(target, "balance", new_b)
                    
                    log_admin_action(uid, f"Added ৳{amt} balance to User {target}")
                    bot.send_message(message.chat.id, f"<b>✅ User <code>{target}</code> এর সাথে ৳{amt} যোগ করা হয়েছে!</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                    try: bot.send_message(target, f"<b>🎉 এডমিন আপনার অ্যাকাউন্টে ৳{amt} যোগ করেছেন!</b>", parse_mode="HTML")
                    except: pass
                except: bot.send_message(message.chat.id, "<b>❌ ইনভ্যালিড অ্যামাউন্ট!</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                update_user_field(uid, "state", None)
                return
            elif state == "admin_ded_bal_id":
                temp = json.loads(u["temp_data"] or "{}")
                temp["target_user"] = txt
                update_user_field(uid, "temp_data", json.dumps(temp))
                update_user_field(uid, "state", "admin_ded_bal_amt")
                bot.send_message(message.chat.id, "<b>💰 কত টাকা ব্যালেন্স কাটতে চান? (যেমন: 20):</b>", parse_mode="HTML")
                return
            elif state == "admin_ded_bal_amt":
                try:
                    amt = float(txt)
                    temp = json.loads(u["temp_data"] or "{}")
                    target = int(temp.get("target_user"))
                    t_user = get_user_db(target)
                    new_b = max(0.0, t_user["balance"] - amt)
                    update_user_field(target, "balance", new_b)
                    
                    log_admin_action(uid, f"Deducted ৳{amt} balance from User {target}")
                    bot.send_message(message.chat.id, f"<b>✅ User <code>{target}</code> এর অ্যাকাউন্ট থেকে ৳{amt} কাটা হয়েছে!</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                except: bot.send_message(message.chat.id, "<b>❌ ইনভ্যালিড অ্যামাউন্ট!</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                update_user_field(uid, "state", None)
                return
            elif state and state.startswith("cfg_w_min_"):
                meth = state.replace("cfg_w_min_", "")
                try:
                    val = float(txt)
                    w_methods = json.loads(get_config("withdraw_methods", "{}"))
                    w_methods[meth]["min"] = val
                    set_config("withdraw_methods", json.dumps(w_methods))
                    bot.send_message(message.chat.id, f"<b>✅ {meth} Min Limit Set to ৳{val}</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                except: bot.send_message(message.chat.id, "<b>❌ ইনভ্যালিড ইনপুট!</b>", parse_mode="HTML")
                update_user_field(uid, "state", None)
                return
            elif state and state.startswith("cfg_w_max_"):
                meth = state.replace("cfg_w_max_", "")
                try:
                    val = float(txt)
                    w_methods = json.loads(get_config("withdraw_methods", "{}"))
                    w_methods[meth]["max"] = val
                    set_config("withdraw_methods", json.dumps(w_methods))
                    bot.send_message(message.chat.id, f"<b>✅ {meth} Max Limit Set to ৳{val}</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                except: bot.send_message(message.chat.id, "<b>❌ ইনভ্যালিড ইনপুট!</b>", parse_mode="HTML")
                update_user_field(uid, "state", None)
                return
            elif state == "set_daily_bot_withdraw_limit":
                try:
                    val = float(txt)
                    set_config("daily_bot_withdraw_limit", str(val))
                    bot.send_message(message.chat.id, f"<b>✅ Daily Total Bot Withdrawal Limit Set to ৳{val:.2f}</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                except:
                    bot.send_message(message.chat.id, "<b>❌ ইনভ্যালিড অ্যামাউন্ট!</b>", parse_mode="HTML")
                update_user_field(uid, "state", None)
                return
            elif state == "admin_broadcast_msg":
                users = fb_get("users") or {}
                bot.send_message(message.chat.id, f"<b>🚀 {len(users)} জন ইউজারের নিকট ব্রডকাস্ট পাঠানো শুরু হয়েছে...</b>", parse_mode="HTML")
                
                success = 0
                for u_id, u_row in users.items():
                    if u_row.get("is_banned"): continue
                    try:
                        if message.photo:
                            bot.send_photo(int(u_id), message.photo[-1].file_id, caption=message.caption or "")
                        else:
                            bot.send_message(int(u_id), txt, parse_mode="HTML")
                        success += 1
                        time.sleep(0.05)
                    except: pass
                bot.send_message(message.chat.id, f"<b>✅ ব্রডকাস্ট সম্পন্ন! সফলভাবে পাঠানো হয়েছে: {success} জনের কাছে।</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                update_user_field(uid, "state", None)
                return

            elif state == "admin_channel_multipost":
                users = fb_get("users") or {}
                temp = json.loads(u["temp_data"] or "{}")
                btn_txt = temp.get("btn_txt", "🔗 Join Now")
                btn_url = temp.get("btn_url", "https://t.me")

                markup = InlineKeyboardMarkup()
                markup.add(ibtn(btn_txt, url=btn_url, style="primary"))

                success = 0
                for u_id, u_row in users.items():
                    if u_row.get("is_banned"): continue
                    try:
                        if message.photo:
                            bot.send_photo(int(u_id), message.photo[-1].file_id, caption=message.caption or "", reply_markup=markup)
                        elif message.video:
                            bot.send_video(int(u_id), message.video.file_id, caption=message.caption or "", reply_markup=markup)
                        else:
                            bot.send_message(int(u_id), txt, parse_mode="HTML", reply_markup=markup)
                        success += 1
                        time.sleep(0.05)
                    except: pass
                bot.send_message(message.chat.id, f"<b>✅ Channel Multi-Post Broadcast Complete! Sent to {success} users.</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                update_user_field(uid, "state", None)
                return

            elif state == "admin_deep_search_id":
                if txt.isdigit():
                    t_uid = int(txt)
                    t_user = get_user_db(t_uid)
                    msg = (f"<b>🔍 User Deep Search & History</b>\n\n"
                           f"<b>🆔 User ID:</b> <code>{t_user['user_id']}</code>\n"
                           f"<b>💰 Balance:</b> ৳{t_user['balance']:.2f}\n"
                           f"<b>📥 Total Withdraw:</b> ৳{t_user['total_withdraw']:.2f}\n"
                           f"<b>👥 Referrals:</b> {t_user['referrals']}\n"
                           f"<b>⏳ Pending Tasks:</b> {t_user['pending_tasks']}\n"
                           f"<b>✅ Approved Tasks:</b> {t_user['approved_tasks']}\n"
                           f"<b>❌ Rejected Tasks:</b> {t_user['rejected_tasks']}\n"
                           f"<b>🌐 IP/Network:</b> <code>{t_user.get('ip_address', 'N/A')}</code>\n"
                           f"<b>🚫 Banned Status:</b> {t_user['is_banned']}")
                    
                    markup = InlineKeyboardMarkup(row_width=2)
                    markup.add(
                        ibtn("⛔ Ban User" if not t_user['is_banned'] else "✅ Unban User", callback_data=f"deep_ban_{t_uid}", style="danger"),
                        ibtn("💰 Modify Balance", callback_data=f"deep_bal_{t_uid}", style="success")
                    )
                    bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=markup)
                else: bot.send_message(message.chat.id, "<b>❌ ইনভ্যালিড ইউজার আইডি!</b>", parse_mode="HTML")
                update_user_field(uid, "state", None)
                return

            elif state == "admin_add_task_step1":
                temp = {"link": txt}
                update_user_field(uid, "temp_data", json.dumps(temp))
                update_user_field(uid, "state", "admin_add_task_step2")
                bot.send_message(message.chat.id, "<b>📝 টাস্কের বিবরণ/ডিসক্রিপশন দিন:</b>", parse_mode="HTML")
                return
            elif state == "admin_add_task_step2":
                temp = json.loads(u["temp_data"] or "{}")
                temp["desc"] = txt
                update_user_field(uid, "temp_data", json.dumps(temp))
                update_user_field(uid, "state", "admin_add_task_step3")
                bot.send_message(message.chat.id, "<b>💰 টাস্কের রিওয়ার্ড অ্যামাউন্ট দিন (যেমন: 5.0):</b>", parse_mode="HTML")
                return
            elif state == "admin_add_task_step3":
                try:
                    rate = float(txt)
                    temp = json.loads(u["temp_data"] or "{}")
                    t_id = f"task_{int(time.time())}"
                    task_data = {
                        "id": t_id, "task_type": "app_tg",
                        "link": temp.get("link"), "description": temp.get("desc"),
                        "rate": rate, "task_limit": 9999, "completed": 0
                    }
                    fb_put(f"tasks/{t_id}", task_data)
                    bot.send_message(message.chat.id, "<b>✅ নতুন App/TG Task যুক্ত করা হয়েছে!</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                except: bot.send_message(message.chat.id, "<b>❌ ইনভ্যালিড রেট!</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                update_user_field(uid, "state", None)
                return
            elif state == "admin_search_submission":
                all_sub = fb_get("pending_submissions") or {}
                sub = None
                for k, v in all_sub.items():
                    if k == txt or txt in str(v.get("payload")):
                        sub = v
                        break

                update_user_field(uid, "state", None)
                if not sub:
                    bot.send_message(message.chat.id, "<b>❌ কোনো সাবমিশন পাওয়া যায়নি!</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                    return
                
                markup = InlineKeyboardMarkup(row_width=2)
                markup.add(
                    ibtn("✅ Approve", callback_data=f"app_sub_{sub['id']}", style="success"),
                    ibtn("❌ Reject", callback_data=f"rej_sub_{sub['id']}", style="danger")
                )
                msg = f"<b>🔎 Submission Found:</b>\n\n<b>ID:</b> <code>{sub['id']}</code>\n<b>Type:</b> <code>{sub['sub_type']}</code>\n<b>User ID:</b> <code>{sub['user_id']}</code>\n<b>Payload:</b> <code>{sub['payload']}</code>"
                bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=markup)
                return

            elif state and state.startswith("edit_emoji_"):
                ekey = state.replace("edit_emoji_", "")
                emojis = json.loads(get_config("emojis", "{}"))
                emojis[ekey] = txt
                set_config("emojis", json.dumps(emojis))
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, f"<b>✅ Emoji for <code>{ekey}</code> updated to: {txt}</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                return

            elif state and state.startswith("reply_ticket_"):
                t_id = state.replace("reply_ticket_", "")
                ticket = fb_get(f"support_tickets/{t_id}")
                if ticket:
                    target_uid = ticket["user_id"]
                    try:
                        bot.send_message(target_uid, f"<b>🎧 Support Reply:</b>\n\n{txt}", parse_mode="HTML")
                        fb_patch(f"support_tickets/{t_id}", {"status": "replied"})
                        bot.send_message(message.chat.id, "<b>✅ রিপ্লাই পাঠানো হয়েছে!</b>", parse_mode="HTML")
                    except:
                        bot.send_message(message.chat.id, "<b>❌ ইউজারকে মেসেজ পাঠানো যায়নি!</b>", parse_mode="HTML")
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
                bot.send_message(message.chat.id, f"<b>✅ Video Tutorial for <code>{cat}</code> saved successfully!</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                return

            elif state == "admin_sold_batch_date":
                # Batch Sold Delete Action
                all_subs = fb_get("pending_submissions") or {}
                deleted_count = 0
                for s_id, s_data in list(all_subs.items()):
                    created_date = datetime.fromtimestamp(s_data.get("created_at", 0)).strftime("%Y-%m-%d")
                    if created_date == txt:
                        fb_delete(f"pending_submissions/{s_id}")
                        deleted_count += 1
                
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, f"<b>🗑️ {txt} তারিখের মোট {deleted_count} টি সাবমিশন ডাটাবেস থেকে Sold/Deleted মার্ক করা হয়েছে!</b>", parse_mode="HTML", reply_markup=get_admin_menu())
                return

        # --- USER TASK PROOF SUBMISSION ---
        if message.photo and state and state.startswith("sub_app_proof_"):
            task_id = state.replace("sub_app_proof_", "")
            sub_id = f"sub_{uid}_{int(time.time())}"
            photo_id = message.photo[-1].file_id
            
            p_data = {
                "id": sub_id, "user_id": uid, "sub_type": "app_ss",
                "payload": json.dumps({"photo": photo_id, "task_id": task_id}),
                "rate": 0.0, "status": "pending", "created_at": time.time()
            }
            fb_put(f"pending_submissions/{sub_id}", p_data)
            fb_put(f"completed_app_tasks/{uid}_{task_id}", True)
            
            u_pend = u.get("pending_tasks", 0) + 1
            update_user_field(uid, "pending_tasks", u_pend)

            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, "<b>✅ আপনার প্রুফ স্ক্রিনশট জমা হয়েছে!</b> এডমিন চেক করে এপ্রুভ করলে ব্যালেন্স যোগ হবে।", parse_mode="HTML", reply_markup=get_main_menu(uid))
            return

        # --- USER SUPPORT TICKET STATE ---
        if state == "user_submit_ticket":
            if get_daily_support_count(uid) >= 5:
                bot.send_message(message.chat.id, f"{get_emoji('error')} <b>আপনি আজ ৫টির বেশি সাপোর্ট টিকিট দিতে পারবেন না!</b>", parse_mode="HTML")
                update_user_field(uid, "state", None)
                return
                
            t_id = f"TICK-{random.randint(10000, 99999)}"
            t_data = {
                "ticket_id": t_id, "user_id": uid,
                "message": txt, "status": "pending", "created_at": time.time()
            }
            fb_put(f"support_tickets/{t_id}", t_data)

            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, f"<b>✅ আপনার সাপোর্ট টিকিট জমা নেওয়া হয়েছে!</b>\nTicket ID: <code>{t_id}</code>", parse_mode="HTML", reply_markup=get_main_menu(uid))
            return

        # --- USER WORK STATES & FB VALIDATION GUARD ---
        if state == "enter_fb_uid":
            if not (txt.isdigit() and 14 <= len(txt) <= 16):
                bot.send_message(message.chat.id, f"{get_emoji('error')} <b>ভুল UID!</b> Facebook UID অবশ্যই ১৪ থেকে ১৬ সংখ্যার হতে হবে। আবার দিন:", parse_mode="HTML")
                return

            if check_duplicate_and_save(txt, "fb_uid", uid):
                bot.send_message(message.chat.id, f"{get_emoji('error')} <b>এই FB UID টি ইতিমধ্যেই সিস্টেমে জমা দেওয়া হয়েছে!</b>", parse_mode="HTML")
                return

            temp = json.loads(u["temp_data"] or "{}")
            temp["fb_uid"] = txt
            update_user_field(uid, "temp_data", json.dumps(temp))
            update_user_field(uid, "state", "enter_fb_cookie")
            bot.send_message(message.chat.id, "<b>🍪 এবার আপনার FB Cookie টি সেন্ড করুন:</b>", parse_mode="HTML")
            return

        elif state == "enter_fb_cookie":
            if len(txt) <= 28:
                bot.send_message(message.chat.id, f"{get_emoji('error')} <b>ইনভ্যালিড কুকিজ!</b> কুকিজটি সর্বনিম্ন ২৮ অক্ষরের বেশি হতে হবে। আবার দিন:", parse_mode="HTML")
                return

            if check_duplicate_and_save(txt, "fb_cookie", uid):
                bot.send_message(message.chat.id, f"{get_emoji('error')} <b>এই FB Cookie টি আগে ব্যবহার করা হয়েছে!</b>", parse_mode="HTML")
                return
            
            temp = json.loads(u["temp_data"] or "{}")
            rate = float(get_config("rate_fb", "18.0"))
            sub_id = f"FB-{random.randint(1000, 9999)}"
            
            data_p = {
                "fn": temp.get("fn"), "ln": temp.get("ln"), "pass": temp.get("pass"),
                "uid": temp.get("fb_uid"), "cookie": txt
            }

            p_data = {
                "id": sub_id, "user_id": uid, "sub_type": "fb",
                "payload": json.dumps(data_p), "rate": rate,
                "status": "pending", "created_at": time.time()
            }
            fb_put(f"pending_submissions/{sub_id}", p_data)
            update_user_field(uid, "pending_tasks", u.get("pending_tasks", 0) + 1)

            append_to_google_sheet("fb", [sub_id, uid, temp.get("fn"), temp.get("ln"), temp.get("fb_uid"), temp.get("pass"), txt, "Pending", datetime.now().strftime("%Y-%m-%d %H:%M")])

            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, f"<b>🎉 আপনার ফেসবুক কাজ জমা হয়েছে!</b>\nSubmit ID: <code>{sub_id}</code>\nরেট: <b>৳{rate:.2f}</b>", parse_mode="HTML", reply_markup=get_main_menu(uid))
            return

        elif state == "enter_2fa_code":
            if check_duplicate_and_save(txt, "2fa", uid):
                bot.send_message(message.chat.id, f"{get_emoji('error')} <b>এই 2FA কোডটি আগে ব্যবহার করা হয়েছে!</b>", parse_mode="HTML")
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

            bot.send_message(message.chat.id, f"<b>🔐 আপনার ইনস্ট্যান্ট ২FA কোড তৈরি হয়েছে:</b>\n\n<code>{six_digit_code}</code>\n\nনিচের বাটন চেপে কোড কপি করুন এবং একাউন্ট খোলা সম্পন্ন করুন:", parse_mode="HTML", reply_markup=markup)

            # VERTICAL KEYBOARD BUTTONS FOR INSTAGRAM
            reply_kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            reply_kb.add(rbtn("অ্যাকাউন্ট খোলা শেষ", "success"))
            reply_kb.add(rbtn("Cancel ❌", "danger"))
            bot.send_message(message.chat.id, "<b>অ্যাকাউন্ট খোলা শেষ হলে নিচের 'অ্যাকাউন্ট খোলা শেষ' বাটনে ক্লিক করুন:</b>", parse_mode="HTML", reply_markup=reply_kb)
            update_user_field(uid, "state", None)
            return

        elif state and state.startswith("withdraw_number_"):
            meth = state.replace("withdraw_number_", "")
            w_methods = json.loads(get_config("withdraw_methods", "{}"))
            min_limit = w_methods[meth]["min"]
            max_limit = w_methods[meth].get("max", 10000.0)
            
            if get_daily_withdraw_count(uid) >= 2:
                bot.send_message(message.chat.id, f"{get_emoji('warning')} <b>উইথড্র লিমিট শেষ!</b> আপনি ২৪ ঘণ্টায় সর্বোচ্চ ২ বার উইথড্র করতে পারবেন।", parse_mode="HTML")
                update_user_field(uid, "state", None)
                return

            if u["balance"] < min_limit:
                bot.send_message(message.chat.id, f"{get_emoji('error')} <b>আপনার পর্যাপ্ত ব্যালেন্স নেই!</b> মিনিমাম উইথড্র ৳{min_limit}", parse_mode="HTML")
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
                bot.send_message(message.chat.id, f"{get_emoji('warning')} <b>বটের আজকের গ্লোবাল ক্যাশআউট লিমিট পূর্ণ হয়েছে!</b> অনুগ্রহ করে আগামীকাল আবার চেষ্টা করুন।", parse_mode="HTML")
                update_user_field(uid, "state", None)
                return

            with db_lock:
                w_req = {
                    "req_id": req_id, "user_id": uid, "method": meth,
                    "account_number": txt, "amount": amt,
                    "status": "pending", "created_at": time.time()
                }
                fb_put(f"withdraw_requests/{req_id}", w_req)
                
                new_bal = u["balance"] - amt
                new_tot_w = u["total_withdraw"] + amt
                update_user_field(uid, "balance", new_bal)
                update_user_field(uid, "total_withdraw", new_tot_w)

            set_config("today_total_withdrawn", str(today_total + amt))

            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, f"<b>✅ আপনার ৳{amt:.2f} এর উইথড্র রিকোয়েস্ট জমা হয়েছে!</b>\nMethod: <b>{meth}</b>\nAccount: <code>{txt}</code>", parse_mode="HTML", reply_markup=get_main_menu(uid))

            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                ibtn("✅ Paid", callback_data=f"pay_with_{req_id}", style="success"),
                ibtn("❌ Refund Balance", callback_data=f"ref_with_{req_id}", style="danger")
            )
            admin_alert = f"<b>📥 New Withdrawal Request!</b>\n\n<b>Req ID:</b> <code>{req_id}</code>\n<b>User ID:</b> <code>{uid}</code>\n<b>Method:</b> {meth}\n<b>Account:</b> <code>{txt}</code>\n<b>Amount:</b> ৳{amt:.2f}"
            try: bot.send_message(ADMIN_ID, admin_alert, parse_mode="HTML", reply_markup=markup)
            except: pass
            return

        # --- MENU ROUTING & TASK PAUSE CHECKS ---
        if txt == TXT_WORK_MAIN:
            bot.send_message(message.chat.id, "<b>💼 কাজ অপশন নির্বাচন করুন:</b>", parse_mode="HTML", reply_markup=get_work_menu())
        elif txt == TXT_BACK:
            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, "<b>🏠 Main Menu</b>", parse_mode="HTML", reply_markup=get_main_menu(uid))

        elif txt == f"{get_emoji('instagram')} ইনস্টাগ্রাম কাজ":
            if get_config("pause_ins", "false") == "true":
                bot.send_message(message.chat.id, f"{get_emoji('warning')} <b>ইনস্টাগ্রাম কাজ সাময়িক বন্ধ আছে।</b>", parse_mode="HTML")
                return
            rate = get_config("rate_ins", "15.0")
            pass_val = generate_dynamic_password("ins_pass")
            _, _, un = generate_random_identity()
            temp_data = json.dumps({"start_time": time.time(), "username": un, "pass": pass_val})
            update_user_field(uid, "temp_data", temp_data)

            msg = (f"<b>📸 Instagram Account Creation</b>\n\n"
                   f"<b>💰 কাজের মূল্য:</b> <b>৳{rate}</b>\n"
                   f"<b>👤 Username:</b> <code>{un}</code>\n"
                   f"<b>🔑 Password:</b> <code>{pass_val}</code>\n\n"
                   f"অ্যাকাউন্ট খুলে 2FA সেটআপ করে নিচের বাটনে চাপ দিন।")
            
            # VERTICAL LAYOUT FOR INSTAGRAM BUTTONS
            markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            markup.add(rbtn("🔑 2FA সেট", "primary"))
            markup.add(rbtn("Cancel ❌", "danger"))
            bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=markup)

        elif txt == "🔑 2FA সেট":
            update_user_field(uid, "state", "enter_2fa_code")
            bot.send_message(message.chat.id, "<b>🔐 আপনার 2FA Secret Key টি দিন:</b>", parse_mode="HTML")

        elif txt == "Cancel ❌":
            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, "<b>❌ কাজ বাতিল করা হয়েছে।</b>", parse_mode="HTML", reply_markup=get_main_menu(uid))

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
            
            p_data = {
                "id": sub_id, "user_id": uid, "sub_type": "ins",
                "payload": json.dumps(data_p), "rate": rate,
                "status": "pending", "created_at": time.time()
            }
            fb_put(f"pending_submissions/{sub_id}", p_data)
            update_user_field(uid, "pending_tasks", u.get("pending_tasks", 0) + 1)

            append_to_google_sheet("ins", [sub_id, uid, temp.get("username"), temp.get("pass"), temp.get("2fa_secret"), "Pending", datetime.now().strftime("%Y-%m-%d %H:%M")])

            bot.send_message(message.chat.id, f"<b>🎉 আপনার ইনস্টাগ্রাম অ্যাকাউন্ট সফলভাবে পেন্ডিংয়ে জমা দেওয়া হয়েছে!</b>\nSubmit ID: <code>{sub_id}</code>\nরেট: <b>৳{rate:.2f}</b>", parse_mode="HTML", reply_markup=get_main_menu(uid))

        elif txt == f"{get_emoji('facebook')} ফেসবুক কাজ":
            if get_config("pause_fb", "false") == "true":
                bot.send_message(message.chat.id, f"{get_emoji('warning')} <b>ফেসবুক কাজ সাময়িক বন্ধ আছে।</b>", parse_mode="HTML")
                return
            rate = get_config("rate_fb", "18.0")
            pass_val = generate_dynamic_password("fb_pass")
            fn, ln, _ = generate_random_identity()
            temp_data = json.dumps({"fn": fn, "ln": ln, "pass": pass_val})
            update_user_field(uid, "temp_data", temp_data)

            msg = (f"<b>📘 Facebook Account Creation</b>\n\n"
                   f"<b>💰 কাজের মূল্য:</b> <b>৳{rate}</b>\n"
                   f"<b>👤 First Name:</b> <code>{fn}</code>\n"
                   f"<b>👤 Last Name:</b> <code>{ln}</code>\n"
                   f"<b>🔑 Password:</b> <code>{pass_val}</code>")
            
            # VERTICAL LAYOUT FOR FACEBOOK BUTTONS
            markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            markup.add(rbtn("Send UID", "primary"))
            markup.add(rbtn("Cancel ❌", "danger"))
            bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=markup)

        elif txt == "Send UID":
            update_user_field(uid, "state", "enter_fb_uid")
            bot.send_message(message.chat.id, "<b>🆔 আপনার Facebook UID প্রদান করুন (১৪-১৬ সংখ্যা):</b>", parse_mode="HTML")

        elif txt == f"{get_emoji('gmail')} Gmail কাজ":
            if get_config("pause_gmail", "false") == "true":
                bot.send_message(message.chat.id, f"{get_emoji('warning')} <b>জিমেইল কাজ সাময়িক বন্ধ আছে।</b>", parse_mode="HTML")
                return
            rate = get_config("rate_gmail", "12.0")
            pass_val = generate_dynamic_password("gmail_pass")
            fn, ln, un = generate_random_identity()
            g_email = f"{un}@gmail.com"
            
            # TIMER STAMP SAVE FOR 2-3 MINUTE CHECK
            temp_data = json.dumps({"start_time": time.time(), "email": g_email, "pass": pass_val})
            update_user_field(uid, "temp_data", temp_data)

            msg = (f"<b>📧 New Gmail Sell Task</b>\n\n"
                   f"<b>💰 কাজের মূল্য:</b> <b>৳{rate}</b>\n"
                   f"<b>👤 First Name:</b> <code>{fn}</code>\n"
                   f"<b>👤 Last Name:</b> <code>{ln}</code>\n"
                   f"<b>✉️ Gmail:</b> <code>{g_email}</code>\n"
                   f"<b>🔑 Password:</b> <code>{pass_val}</code>")
            
            # VERTICAL LAYOUT FOR GMAIL BUTTONS
            markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            markup.add(rbtn("কাজ শেষ", "success"))
            markup.add(rbtn("বাতিল", "danger"))
            bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=markup)

        elif txt in ["কাজ শেষ", "বাতিল"]:
            if txt == "বাতিল":
                update_user_field(uid, "state", None)
                bot.send_message(message.chat.id, "<b>❌ কাজ বাতিল করা হয়েছে।</b>", parse_mode="HTML", reply_markup=get_main_menu(uid))
                return

            temp = json.loads(u["temp_data"] or "{}")
            start_time = temp.get("start_time", 0)
            elapsed_time = time.time() - start_time

            # 2-3 MINUTES WAIT GUARD CHECK (120 SECONDS MINIMUM)
            if elapsed_time < 120:
                bot.send_message(message.chat.id, f"{get_emoji('warning')} <b>আপনি মাত্র কয়েক সেকেন্ডের মধ্যে 'কাজ শেষ' বাটনে চাপ দিয়েছেন!</b>\n\nজিমেইল অ্যাকাউন্টটি খুলতে ২-৩ মিনিট সময় লাগে। সঠিকভাবে সম্পূর্ণ অ্যাকাউন্ট খুলে ২ মিনিট পর চেষ্টা করুন।", parse_mode="HTML")
                return

            g_email = temp.get("email")
            bot.send_message(message.chat.id, "<b>⏳ দয়া করে অপেক্ষা করুন, গুগল মেইল সার্ভারে অ্যাকাউন্টের স্থায়িত্ব সাইলেন্টলি ভেরিফাই করা হচ্ছে....</b>", parse_mode="HTML")
            
            if not verify_gmail_smtp(g_email):
                bot.send_message(message.chat.id, f"{get_emoji('error')} <b>আপনি জিমেইল অ্যাকাউন্টটি তৈরি না করেই 'কাজ শেষ' বাটনে চাপ দিয়েছেন!</b>\n\nদয়া করে সঠিক নিয়মে অ্যাকাউন্ট তৈরি করে আবার চেষ্টা করুন।", parse_mode="HTML", reply_markup=get_main_menu(uid))
                return

            rate = float(get_config("rate_gmail", "12.0"))
            sub_id = f"GM-{random.randint(1000, 9999)}"
            data_p = {"email": temp.get("email"), "pass": temp.get("pass")}
            
            p_data = {
                "id": sub_id, "user_id": uid, "sub_type": "gmail",
                "payload": json.dumps(data_p), "rate": rate,
                "status": "pending", "created_at": time.time()
            }
            fb_put(f"pending_submissions/{sub_id}", p_data)
            update_user_field(uid, "pending_tasks", u.get("pending_tasks", 0) + 1)

            rec_email = get_config("recovery_email", "tasrikvai8001@gmail.com")
            append_to_google_sheet("gmail", [sub_id, uid, temp.get("email"), temp.get("pass"), rec_email, "Pending", datetime.now().strftime("%Y-%m-%d %H:%M")])

            bot.send_message(message.chat.id, f"<b>✅ জিমেইল কাজ সফলভাবে যাচাইপূর্বক জমা নেওয়া হয়েছে!</b>\nSubmit ID: <code>{sub_id}</code>", parse_mode="HTML", reply_markup=get_main_menu(uid))

        elif txt == TXT_TODAY_WORK:
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                ibtn("🌀 স্পিন করে আয়", callback_data="open_spin_game", style="primary"),
                ibtn("📲 টেলিগ্রাম ও অ্যাপস টাস্ক", callback_data="open_app_tasks", style="primary"),
                ibtn("🎁 আমন্ত্রণ পুরষ্কার", callback_data="open_invite_rewards", style="success")
            )
            bot.send_message(message.chat.id, "<b>🔥 আজকের কাজের মেনু:</b>", parse_mode="HTML", reply_markup=markup)

        elif txt == TXT_BALANCE:
            msg = (f"<b>👤 USER STATS & BALANCE</b>\n\n"
                   f"<b>{get_emoji('balance')} মোট ব্যালেন্স:</b> <b>৳{u['balance']:.2f}</b>\n"
                   f"<b>{get_emoji('invite')} মোট রেফার:</b> <b>{u['referrals']}</b>\n"
                   f"<b>{get_emoji('withdraw')} মোট উইথড্র:</b> <b>৳{u['total_withdraw']:.2f}</b>\n"
                   f"<b>⏳ পেন্ডিং টাস্ক:</b> <b>{u['pending_tasks']}</b>\n"
                   f"<b>✅ এপ্রুভড টাস্ক:</b> <b>{u['approved_tasks']}</b>\n"
                   f"<b>❌ রিজেক্ট টাস্ক:</b> <b>{u['rejected_tasks']}</b>")
            bot.send_message(message.chat.id, msg, parse_mode="HTML")

        elif txt == TXT_WITHDRAW:
            w_methods = json.loads(get_config("withdraw_methods", "{}"))
            markup = InlineKeyboardMarkup(row_width=1)
            for meth, info in w_methods.items():
                if info.get("enabled"):
                    markup.add(ibtn(f"💳 {meth} (Min ৳{info['min']})", callback_data=f"with_meth_{meth}", style="primary"))
            bot.send_message(message.chat.id, "<b>📥 উইথড্র মেথড সিলেক্ট করুন:</b>", parse_mode="HTML", reply_markup=markup)

        elif txt == TXT_REFER:
            bot_uname = bot.get_me().username
            link = f"https://t.me/{bot_uname}?start={uid}"
            bonus = get_config("ref_bonus", "10.0")
            msg = (f"<b>{get_emoji('invite')} Refer & Earn!</b>\n\n"
                   f"<b>আপনার রেফার লিংক:</b>\n<code>{link}</code>\n\n"
                   f"💡 <b>নিয়ম:</b> আপনার লিংক থেকে কোনো ইউজার জয়েন করে ১ম কাজ শেষ করলে পাবেন <b>৳{bonus}</b> এবং তার সারাজীবনের কাজের ওপর পাবেন <b>১০% লাইফটাইম কমিশন</b>!")
            bot.send_message(message.chat.id, msg, parse_mode="HTML")

        elif txt == TXT_SUPPORT:
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                ibtn("🎧 Official Support Channel", url="https://t.me/tasrikvai", style="primary"),
                ibtn("📩 Open Support Ticket", callback_data="open_support_ticket", style="success")
            )
            bot.send_message(message.chat.id, f"<b>{get_emoji('support')} আমাদের ২৪/৭ সাপোর্ট প্যানেল:</b>\n\nসরাসরি এডমিনের সাহায্য নিতে টিকিট ওপেন করুন:", parse_mode="HTML", reply_markup=markup)

        elif txt == TXT_NEWBIE:
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                ibtn("📧 Gmail Account Video", callback_data="watch_vid_gmail", style="primary"),
                ibtn("📘 Facebook Account Video", callback_data="watch_vid_fb", style="primary"),
                ibtn("📸 Instagram Account Video", callback_data="watch_vid_ins", style="primary")
            )
            msg = (f"<b>{get_emoji('newbie')} টিউটোরিয়াল প্যানেল</b>\n\n"
                   f"নিচের বাটনগুলোতে চাপ দিয়ে যেকোনো কাজের প্রিমিয়াম ভিডিও দেখে কাজ শিখুন:")
            bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=markup)

        elif txt == TXT_ADMIN_PANEL and check_permission(uid, "admin"):
            bot.send_message(message.chat.id, "<b>⚙️ Admin Control Panel</b>", parse_mode="HTML", reply_markup=get_admin_menu())

        # --- ADMIN BUTTON HANDLERS ---
        elif txt == "💰 Set Task Rates" and check_permission(uid, "admin"):
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                ibtn(f"📸 Set Ins Rate (Current: ৳{get_config('rate_ins')})", callback_data="set_rate_ins", style="primary"),
                ibtn(f"📘 Set Fb Rate (Current: ৳{get_config('rate_fb')})", callback_data="set_rate_fb", style="primary"),
                ibtn(f"📧 Set Gmail Rate (Current: ৳{get_config('rate_gmail')})", callback_data="set_rate_gmail", style="primary")
            )
            bot.send_message(message.chat.id, "<b>💰 কাজের রেট সেটিং:</b>", parse_mode="HTML", reply_markup=markup)

        elif txt == "📢 Set Force Join" and check_permission(uid, "admin"):
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                ibtn("➕ Add Channel", callback_data="add_force_join_ch", style="success"),
                ibtn("➖ Remove Channel", callback_data="remove_force_join_ch", style="danger")
            )
            chs = json.loads(get_config("force_channels", "[]"))
            bot.send_message(message.chat.id, f"<b>📢 Force Join Channel Settings:</b>\nবর্তমান চ্যানেল: <code>{chs}</code>", parse_mode="HTML", reply_markup=markup)

        elif txt == "🎁 Set Ref Bonus" and check_permission(uid, "admin"):
            update_user_field(uid, "state", "set_ref_bonus")
            bot.send_message(message.chat.id, f"<b>🎁 নতুন রেফার বোনাসের পরিমাণ দিন (বর্তমান: ৳{get_config('ref_bonus')}):</b>", parse_mode="HTML")

        elif txt == "🔑 Set Passwords Base" and check_permission(uid, "admin"):
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                ibtn(f"📸 Ins Base Pass ({get_config('ins_pass')})", callback_data="set_pass_ins", style="primary"),
                ibtn(f"📘 FB Base Pass ({get_config('fb_pass')})", callback_data="set_pass_fb", style="primary"),
                ibtn(f"📧 Gmail Base Pass ({get_config('gmail_pass')})", callback_data="set_pass_gmail", style="primary")
            )
            bot.send_message(message.chat.id, "<b>🔑 ডায়নামিক পাসওয়ার্ড প্রিফিক্স সেটিং:</b>", parse_mode="HTML", reply_markup=markup)

        elif txt == "💳 Withdraw Setting" and check_permission(uid, "admin"):
            w_methods = json.loads(get_config("withdraw_methods", "{}"))
            markup = InlineKeyboardMarkup(row_width=1)
            for m_name, m_data in w_methods.items():
                st = "ON ✅" if m_data.get("enabled") else "OFF ❌"
                markup.add(ibtn(f"⚙️ {m_name} [{st}]", callback_data=f"cfg_w_menu_{m_name}", style="primary"))
            markup.add(ibtn(f"📊 Daily Total Withdraw Limit (৳{get_config('daily_bot_withdraw_limit')})", callback_data="set_daily_bot_withdraw_limit", style="success"))
            bot.send_message(message.chat.id, "<b>💳 উইথড্র মেথড ও ক্যাশআউট কনফিগারেশন:</b>", parse_mode="HTML", reply_markup=markup)

        elif txt == "🌀 Spin & Ad Settings" and check_permission(uid, "admin"):
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                ibtn(f"💰 Spin Reward (৳{get_config('spin_reward')})", callback_data="set_spin_reward", style="primary"),
                ibtn(f"🔢 Daily Spin Limit ({get_config('spin_limit')} Times)", callback_data="set_spin_limit", style="primary"),
                ibtn(f"🔗 Adsterra Direct Link", callback_data="set_spin_url", style="primary")
            )
            bot.send_message(message.chat.id, "<b>🌀 স্পিন ও অ্যাড সেটিং:</b>", parse_mode="HTML", reply_markup=markup)

        elif txt == "📊 Google Sheets Config" and check_permission(uid, "admin"):
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                ibtn("📸 Set Instagram Sheet ID", callback_data="set_sheet_ins", style="primary"),
                ibtn("📘 Set Facebook Sheet ID", callback_data="set_sheet_fb", style="primary"),
                ibtn("📧 Set Gmail Sheet ID", callback_data="set_sheet_gmail", style="primary")
            )
            bot.send_message(message.chat.id, "<b>📊 গুগল শিটের আইডি কনফিগার করুন:</b>", parse_mode="HTML", reply_markup=markup)

        elif txt == "🤖 Upload JSON Creds" and check_permission(uid, "admin"):
            update_user_field(uid, "state", "set_json_creds")
            bot.send_message(message.chat.id, "<b>🔑 Google Service Account JSON ফাইল অথবা টেক্সট পেস্ট করে পাঠ পাঠান:</b>", parse_mode="HTML")

        elif txt == "🔥 Set Firebase API" and check_permission(uid, "admin"):
            update_user_field(uid, "state", "set_firebase_api")
            bot.send_message(message.chat.id, "<b>🔥 Firebase API Key অথবা Config JSON ফাইলটি সরাসরি আপলোড বা টেক্সট আকারে পাঠিয়া দিন:</b>", parse_mode="HTML")

        elif txt == "📧 Set Recovery Email" and check_permission(uid, "admin"):
            update_user_field(uid, "state", "set_recovery_email")
            bot.send_message(message.chat.id, f"<b>📧 নতুন Recovery Email লিখুন (বর্তমান: <code>{get_config('recovery_email')}</code>):</b>", parse_mode="HTML")

        elif txt == "🎨 Edit Emoji IDs" and check_permission(uid, "admin"):
            emojis = json.loads(get_config("emojis", "{}"))
            markup = InlineKeyboardMarkup(row_width=2)
            for k, v in emojis.items():
                markup.add(ibtn(f"{k.capitalize()}: {v}", callback_data=f"edit_emoji_{k}", style="primary"))
            bot.send_message(message.chat.id, "<b>🎨 যে ইমোজি বা কাস্টম প্রিমিয়াম ইমোজি আইডি চেঞ্জ করতে চান সেটিতে চাপ দিন:</b>", parse_mode="HTML", reply_markup=markup)

        elif txt == "🔄 Sync Google Sheet Approval" and check_permission(uid, "admin"):
            bot.send_message(message.chat.id, "<b>⏳ গুগল শিট থেকে অটো-রিড করে স্ট্যাটাস সিঙ্ক করা হচ্ছে....</b>", parse_mode="HTML")
            count = sync_sheet_approvals()
            bot.send_message(message.chat.id, f"<b>✅ Google Sheet Auto Sync Complete! মোট {count} টি কাজ প্রসেসড করা হয়েছে।</b>", parse_mode="HTML", reply_markup=get_admin_menu())

        elif txt == "🔎 Pending Approvals" and check_permission(uid, "admin"):
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                ibtn("🔍 Search Approval by ID/2FA/UID", callback_data="search_approval_manual", style="primary"),
                ibtn("📸 Instagram Pending", callback_data="list_pend_ins", style="primary"),
                ibtn("📘 Facebook Pending", callback_data="list_pend_fb", style="primary"),
                ibtn("📧 Gmail Pending", callback_data="list_pend_gmail", style="primary")
            )
            bot.send_message(message.chat.id, "<b>🔎 Pending Approvals Control Panel:</b>", parse_mode="HTML", reply_markup=markup)

        elif txt == "📥 Pending Withdraws" and check_permission(uid, "admin"):
            all_w = fb_get("withdraw_requests") or {}
            pending_reqs = [v for v in all_w.values() if v.get("status") == "pending"]

            if not pending_reqs:
                bot.send_message(message.chat.id, "<b>✅ কোনো পেন্ডিং উইথড্র রিকোয়েস্ট নেই!</b>", parse_mode="HTML")
                return

            for r in pending_reqs:
                markup = InlineKeyboardMarkup(row_width=2)
                markup.add(
                    ibtn("✅ Paid", callback_data=f"pay_with_{r['req_id']}", style="success"),
                    ibtn("❌ Refund", callback_data=f"ref_with_{r['req_id']}", style="danger")
                )
                bot.send_message(message.chat.id, f"<b>📥 Req ID:</b> <code>{r['req_id']}</code>\n<b>User:</b> <code>{r['user_id']}</code>\n<b>Method:</b> {r['method']}\n<b>Account:</b> <code>{r['account_number']}</code>\n<b>Amount:</b> ৳{r['amount']}", parse_mode="HTML", reply_markup=markup)

        elif txt == "📩 Pending Support Tickets" and check_permission(uid, "admin"):
            all_t = fb_get("support_tickets") or {}
            pending_tickets = [v for v in all_t.values() if v.get("status") == "pending"]

            if not pending_tickets:
                bot.send_message(message.chat.id, "<b>✅ কোনো পেন্ডিং সাপোর্ট টিকিট নেই!</b>", parse_mode="HTML")
                return

            for t in pending_tickets:
                markup = InlineKeyboardMarkup()
                markup.add(ibtn("💬 Reply Ticket", callback_data=f"reply_t_{t['ticket_id']}", style="primary"))
                bot.send_message(message.chat.id, f"<b>📩 Ticket ID:</b> <code>{t['ticket_id']}</code>\n<b>User ID:</b> <code>{t['user_id']}</code>\n<b>Message:</b> {t['message']}", parse_mode="HTML", reply_markup=markup)

        elif txt == "🔍 User Deep Search" and check_permission(uid, "admin"):
            update_user_field(uid, "state", "admin_deep_search_id")
            bot.send_message(message.chat.id, "<b>🔍 যার তথ্য বের করতে চান তার Telegram User ID দিন:</b>", parse_mode="HTML")

        elif txt == "📢 Channel Multi-Post Broadcast" and check_permission(uid, "admin"):
            bot.send_message(message.chat.id, "<b>📢 Multi-Post Configuration:</b>\n\nপ্রথমে আপনার ইনলাইন বাটন URL লিংক লিখুন (যেমন: https://t.me/example):", parse_mode="HTML")
            update_user_field(uid, "state", "set_multipost_url")

        elif txt == "🗑️ Bulk Reject Submissions" and check_permission(uid, "admin"):
            all_subs = fb_get("pending_submissions") or {}
            affected = 0
            for s_id, s_data in all_subs.items():
                if s_data.get("status") == "pending":
                    fb_patch(f"pending_submissions/{s_id}", {"status": "rejected"})
                    affected += 1
            
            log_admin_action(uid, f"Bulk Rejected {affected} Submissions")
            bot.send_message(message.chat.id, f"<b>🗑️ সফলভাবে মোট {affected} টি পেন্ডিং ফেক কাজ এক ক্লিকে রিজেক্ট করা হয়েছে!</b>", parse_mode="HTML")

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
            bot.send_message(message.chat.id, "<b>⏸️ Task Pause & Status Manager:</b>", parse_mode="HTML", reply_markup=markup)

        elif txt == "🎥 Set Tutorial Videos" and check_permission(uid, "admin"):
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                ibtn("📹 Set Gmail Video", callback_data="set_vid_gmail", style="primary"),
                ibtn("📹 Set FB Video", callback_data="set_vid_fb", style="primary"),
                ibtn("📹 Set Instagram Video", callback_data="set_vid_ins", style="primary")
            )
            bot.send_message(message.chat.id, "<b>🎥 টিউটোরিয়াল ভিডিও সেটিং:</b>", parse_mode="HTML", reply_markup=markup)

        elif txt == "➕ Add App/TG Task" and check_permission(uid, "admin"):
            update_user_field(uid, "state", "admin_add_task_step1")
            bot.send_message(message.chat.id, "<b>📲 অ্যাপ বা টেলিগ্রাম চ্যানেলের লিংক দিন:</b>", parse_mode="HTML")

        elif txt == "📩 Smart Broadcast Message" and check_permission(uid, "admin"):
            update_user_field(uid, "state", "admin_broadcast_msg")
            bot.send_message(message.chat.id, "<b>📢 যে বার্তা বা ছবি সবার কাছে পাঠাতে চান তা লিখুন বা পাঠান:</b>", parse_mode="HTML")

        elif txt == "📊 Bot Statistics" and check_permission(uid, "admin"):
            users = fb_get("users") or {}
            total_users = len(users)
            
            day_ago = time.time() - 86400
            active_users = sum(1 for u in users.values() if u.get("last_active", 0) >= day_ago)
            
            subs = fb_get("pending_submissions") or {}
            total_tasks = len(subs)
            tot_income = sum(float(s.get("rate", 0)) for s in subs.values() if s.get("status") == "approved")
            
            reqs = fb_get("withdraw_requests") or {}
            tot_withdraw = sum(float(r.get("amount", 0)) for r in reqs.values() if r.get("status") == "approved")

            msg = (f"<b>📊 BOT STATISTICS & OVERVIEW</b>\n\n"
                   f"<b>👥 মোট ইউজার:</b> <b>{total_users}</b>\n"
                   f"<b>⚡ ২৪ ঘণ্টায় একটিভ ইউজার:</b> <b>{active_users}</b>\n"
                   f"<b>📥 মোট সাবমিটেড টাস্ক:</b> <b>{total_tasks}</b>\n"
                   f"<b>💸 মোট পেইড উইথড্র:</b> <b>৳{tot_withdraw:.2f}</b>\n"
                   f"<b>💰 বটের মোট বিতরণ করা ইনকাম:</b> <b>৳{tot_income:.2f}</b>")
            bot.send_message(message.chat.id, msg, parse_mode="HTML")

        elif txt == "⛔ Ban/Unban User" and check_permission(uid, "admin"):
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                ibtn("⛔ Ban User", callback_data="btn_ban_u", style="danger"),
                ibtn("✅ Unban User", callback_data="btn_unban_u", style="success")
            )
            bot.send_message(message.chat.id, "<b>⛔ ব্যান / আনব্যান প্যানেল:</b>", parse_mode="HTML", reply_markup=markup)

        elif txt == "➕ Add/Deduct Balance" and check_permission(uid, "admin"):
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                ibtn("➕ Add Balance", callback_data="btn_add_bal", style="success"),
                ibtn("➖ Deduct Balance", callback_data="btn_ded_bal", style="danger")
            )
            bot.send_message(message.chat.id, "<b>💰 ইউজার ব্যালেন্স কন্ট্রোল:</b>", parse_mode="HTML", reply_markup=markup)

        elif txt == "👑 Sub-Admin Manager" and uid == ADMIN_ID:
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                ibtn("👑 Make Sub-Admin", callback_data="btn_mod_u", style="primary"),
                ibtn("👤 Remove Sub-Admin", callback_data="btn_unmod_u", style="danger")
            )
            bot.send_message(message.chat.id, "<b>👑 সাব-এডমিন ম্যানেজমেন্ট:</b>", parse_mode="HTML", reply_markup=markup)

        elif txt == "🧹 Database Cleanup" and check_permission(uid, "admin"):
            old_time = time.time() - (30 * 86400)
            all_subs = fb_get("pending_submissions") or {}
            for s_id, s_data in list(all_subs.items()):
                if s_data.get("created_at", 0) < old_time and s_data.get("status") != "pending":
                    fb_delete(f"pending_submissions/{s_id}")
            bot.send_message(message.chat.id, "<b>🧹 ৩০ দিনের পুরাতন সকল রিজেক্টেড/কমপ্লিট ডাটা ডিলিট করা হয়েছে!</b>", parse_mode="HTML")

        elif txt == "🚨 Error Logs" and check_permission(uid, "admin"):
            if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 0:
                with open(LOG_FILE, "rb") as f:
                    bot.send_document(message.chat.id, f, caption="<b>🚨 Error Log File</b>", parse_mode="HTML")
            else:
                bot.send_message(message.chat.id, "<b>✅ কোনো এরর লগ পাওয়া যায়নি! সিস্টেমে কোনো সমস্যা নেই।</b>", parse_mode="HTML")

        elif txt == "⚡ Maintenance Mode" and check_permission(uid, "admin"):
            curr = get_config("maintenance_mode", "false")
            new_st = "true" if curr == "false" else "false"
            set_config("maintenance_mode", new_st)
            st_txt = "ON 🟢" if new_st == "true" else "OFF 🔴"
            bot.send_message(message.chat.id, f"<b>⚡ Maintenance Mode set to: {st_txt}</b>", parse_mode="HTML", reply_markup=get_admin_menu())

        elif txt == "📥 Export Unsold Files" and check_permission(uid, "admin"):
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                ibtn("📸 Export Instagram", callback_data="export_serv_ins", style="primary"),
                ibtn("📘 Export Facebook", callback_data="export_serv_fb", style="primary"),
                ibtn("📧 Export Gmail", callback_data="export_serv_gmail", style="primary")
            )
            bot.send_message(message.chat.id, "<b>📥 কোন কাজের Unsold ফাইল ডাউনলোড করতে চান?</b>", parse_mode="HTML", reply_markup=markup)

        elif txt == "🗑️ Sold & Batch Delete" and check_permission(uid, "admin"):
            update_user_field(uid, "state", "admin_sold_batch_date")
            bot.send_message(message.chat.id, "<b>🗑️ যে তারিখের ফাইল ডিলিট বা Sold মার্ক করতে চান তা ওয়াইওয়াইওয়াইওয়াই-এমএম-ডিডি ফরম্যাটে লিখুন (যেমন: 2026-08-19):</b>", parse_mode="HTML")

        # Multi-post intermediate state string collection
        elif state == "set_multipost_url":
            temp = json.loads(u["temp_data"] or "{}")
            temp["btn_url"] = txt
            update_user_field(uid, "temp_data", json.dumps(temp))
            update_user_field(uid, "state", "set_multipost_txt")
            bot.send_message(message.chat.id, "<b>📝 বাটনের টেক্সট লিখুন (যেমন: 🚀 Join Now):</b>", parse_mode="HTML")
            return
        elif state == "set_multipost_txt":
            temp = json.loads(u["temp_data"] or "{}")
            temp["btn_txt"] = txt
            update_user_field(uid, "temp_data", json.dumps(temp))
            update_user_field(uid, "state", "admin_channel_multipost")
            bot.send_message(message.chat.id, "<b>📸 এখন ব্রডকাস্ট করার পোস্ট (ছবি/ভিডিও/লেখা) সেন্ড করুন:</b>", parse_mode="HTML")
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

        # Force Join Guard on Inline Clicks
        if uid != ADMIN_ID and call.data != "check_join_event" and not check_force_join(uid):
            bot.answer_callback_query(call.id, "❌ আপনি এখনও সকল চ্যানেলগুলিতে জয়েন করেননি!", show_alert=True)
            return

        if call.data == "check_join_event":
            if check_force_join(uid):
                bot.answer_callback_query(call.id, "✅ সকল চ্যানেলে জয়েন ভেরিফাইড!")
                try: bot.delete_message(call.message.chat.id, call.message.message_id)
                except: pass
                bot.send_message(call.message.chat.id, "<b>🎉 স্বাগতম!</b>", parse_mode="HTML", reply_markup=get_main_menu(uid))
            else:
                bot.answer_callback_query(call.id, "❌ আপনি এখনো সকল চ্যানেলে জয়েন করেননি!", show_alert=True)

        elif call.data.startswith("copy_code_"):
            code = call.data.replace("copy_code_", "")
            bot.answer_callback_query(call.id, f"✅ Code copied: {code}", show_alert=True)

        elif call.data == "open_spin_game":
            today_str = datetime.now().strftime("%Y-%m-%d")
            limit = int(get_config("spin_limit", "5"))
            
            # FIX: Ensure Spin Limit Strict Database Check
            if u.get("last_spin_date") != today_str:
                update_user_field(uid, "last_spin_date", today_str)
                update_user_field(uid, "daily_spins", 0)
                u["daily_spins"] = 0

            if u.get("daily_spins", 0) >= limit:
                bot.answer_callback_query(call.id, f"❌ আপনার আজকের স্পিন লিমিট ({limit}/{limit}) শেষ!", show_alert=True)
                return

            ad_url = get_config("spin_ad_url", "https://example.com")
            
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                ibtn("🌐 অ্যাড দেখুন (Ad Click Required)", url=ad_url, style="primary"),
                ibtn("🎁 রিওয়ার্ড ভেরিফাই করুন", callback_data="claim_spin_reward_secure", style="success")
            )
            bot.send_message(call.message.chat.id, "<b>⚠️ স্পিন রিওয়ার্ড সিকিউরিটি চেক:</b>\n\nনিচের অ্যাড লিংকে ক্লিক করে অ্যাড দেখার পর 'রিওয়ার্ড ভেরিফাই করুন' বাটনে চাপ দিন:", parse_mode="HTML", reply_markup=markup)

        elif call.data == "claim_spin_reward_secure":
            today_str = datetime.now().strftime("%Y-%m-%d")
            limit = int(get_config("spin_limit", "5"))
            reward = float(get_config("spin_reward", "1.5"))
            
            curr_spins = u.get("daily_spins", 0)
            if u.get("last_spin_date") == today_str and curr_spins >= limit:
                bot.answer_callback_query(call.id, f"❌ দৈনিক লিমিট পূর্ণ হয়েছে! আর স্পিন করা সম্ভব নয়।", show_alert=True)
                return

            new_spins = curr_spins + 1
            new_bal = u["balance"] + reward
            new_inc = u["total_income"] + reward

            update_user_field(uid, "daily_spins", new_spins)
            update_user_field(uid, "balance", new_bal)
            update_user_field(uid, "total_income", new_inc)
            update_user_field(uid, "last_spin_date", today_str)

            bot.answer_callback_query(call.id, f"🎉 ভেরিফাইড! আপনি ৳{reward} পেয়েছেন!", show_alert=True)
            bot.send_message(call.message.chat.id, f"<b>🎉 অভিনন্দন! আপনি সফলভাবে ৳{reward} আয় করেছেন!</b>\nআজকে আর স্পিন বাকি: <b>{limit - new_spins}</b> টি", parse_mode="HTML", reply_markup=get_main_menu(uid))

        elif call.data == "open_invite_rewards":
            bonus = get_config("ref_bonus", "10.0")
            msg = f"<b>🎁 আমন্ত্রণ পুরষ্কার:</b>\n\nপ্রতিটি সফল রেফারের জন্য আপনি <b>৳{bonus}</b> পাবেন এবং আপনার রেফারেল যত কাজ করবে তার ওপর <b>১০% লাইফটাইম কমিশন</b> পাবেন!"
            bot.send_message(call.message.chat.id, msg, parse_mode="HTML")

        elif call.data == "open_support_ticket":
            update_user_field(uid, "state", "user_submit_ticket")
            bot.send_message(call.message.chat.id, "<b>💬 আপনার সমস্যাটি বিস্তারিত লিখে পাঠান (আজকের টিকিট বাকি আছে):</b>", parse_mode="HTML")

        elif call.data == "open_app_tasks":
            all_tasks = fb_get("tasks") or {}
            completed = fb_get("completed_app_tasks") or {}

            available = []
            for t_id, t_data in all_tasks.items():
                if not completed.get(f"{uid}_{t_id}"):
                    available.append(t_data)

            if not available:
                bot.answer_callback_query(call.id, "❌ আপনার জন্য এই মুহূর্তে কোনো নতুন অ্যাপ/টিজি টাস্ক নেই!", show_alert=True)
                return

            for t in available:
                markup = InlineKeyboardMarkup(row_width=2)
                markup.add(
                    ibtn("🔗 Go to Link", url=t["link"], style="primary"),
                    ibtn("📤 Submit Proof SS", callback_data=f"sub_proof_{t['id']}", style="success")
                )
                bot.send_message(call.message.chat.id, f"<b>📲 Task #{t['id']}</b>\n\n{t['description']}\n\n<b>💰 Reward:</b> ৳{t['rate']}", parse_mode="HTML", reply_markup=markup)

        elif call.data.startswith("sub_proof_"):
            t_id = call.data.replace("sub_proof_", "")
            update_user_field(uid, "state", f"sub_app_proof_{t_id}")
            bot.send_message(call.message.chat.id, "<b>📸 আপনার টাস্কের স্ক্রিনশটটি প্রুফ হিসেবে পাঠান:</b>", parse_mode="HTML")

        elif call.data.startswith("watch_vid_"):
            cat = call.data.replace("watch_vid_", "")
            vids = json.loads(get_config("tutorial_videos", "{}"))
            vid_id = vids.get(cat, "")
            if not vid_id:
                bot.answer_callback_query(call.id, "❌ টিউটোরিয়াল ভিডিও পাওয়া যায়নি!", show_alert=True)
                return
            try:
                bot.send_video(call.message.chat.id, vid_id, caption=f"<b>📹 {cat.upper()} Tutorial Video Guide</b>", parse_mode="HTML")
            except Exception as e:
                log_error(f"Error sending video {cat}: {e}")
                bot.send_message(call.message.chat.id, f"<b>📹 Tutorial Video ID/Link:</b> <code>{vid_id}</code>", parse_mode="HTML")

        elif call.data.startswith("with_meth_"):
            meth = call.data.replace("with_meth_", "")
            update_user_field(uid, "state", f"withdraw_number_{meth}")
            bot.send_message(call.message.chat.id, f"<b>💳 আপনার {meth} একাউন্ট নাম্বার প্রদান করুন:</b>", parse_mode="HTML")

        # --- ADMIN CALLBACKS ---
        elif call.data == "add_force_join_ch":
            update_user_field(uid, "state", "set_force_join")
            bot.send_message(call.message.chat.id, "<b>📢 নতুন চ্যানেল ইউজারনেম ইনপুট দিন (যেমন: @channel1, @channel2):</b>", parse_mode="HTML")

        elif call.data == "remove_force_join_ch":
            update_user_field(uid, "state", "remove_force_join_ch")
            bot.send_message(call.message.chat.id, "<b>📢 যে চ্যানেলটি রিমুভ করতে চান সেটি লিখুন (যেমন: @channel1):</b>", parse_mode="HTML")

        elif call.data == "set_rate_ins":
            update_user_field(uid, "state", "set_rate_ins")
            bot.send_message(call.message.chat.id, "<b>📸 Instagram এর নতুন রেট লিখুন (যেমন: 15.0):</b>", parse_mode="HTML")

        elif call.data == "set_rate_fb":
            update_user_field(uid, "state", "set_rate_fb")
            bot.send_message(call.message.chat.id, "<b>📘 Facebook এর নতুন রেট লিখুন (যেমন: 18.0):</b>", parse_mode="HTML")

        elif call.data == "set_rate_gmail":
            update_user_field(uid, "state", "set_rate_gmail")
            bot.send_message(call.message.chat.id, "<b>📧 Gmail এর নতুন রেট লিখুন (যেমন: 12.0):</b>", parse_mode="HTML")

        elif call.data == "set_pass_ins":
            update_user_field(uid, "state", "set_pass_ins")
            bot.send_message(call.message.chat.id, "<b>📸 Instagram এর ডায়নামিক পাসওয়ার্ড প্রিফিক্স লিখুন:</b>", parse_mode="HTML")

        elif call.data == "set_pass_fb":
            update_user_field(uid, "state", "set_pass_fb")
            bot.send_message(call.message.chat.id, "<b>📘 Facebook এর ডায়নামিক পাসওয়ার্ড প্রিফিক্স লিখুন:</b>", parse_mode="HTML")

        elif call.data == "set_pass_gmail":
            update_user_field(uid, "state", "set_pass_gmail")
            bot.send_message(call.message.chat.id, "<b>📧 Gmail এর ডায়নামিক পাসওয়ার্ড প্রিফিক্স লিখুন:</b>", parse_mode="HTML")

        elif call.data == "set_sheet_ins":
            update_user_field(uid, "state", "set_sheet_ins")
            bot.send_message(call.message.chat.id, "<b>📊 Instagram Sheet ID দিন:</b>", parse_mode="HTML")

        elif call.data == "set_sheet_fb":
            update_user_field(uid, "state", "set_sheet_fb")
            bot.send_message(call.message.chat.id, "<b>📊 Facebook Sheet ID দিন:</b>", parse_mode="HTML")

        elif call.data == "set_sheet_gmail":
            update_user_field(uid, "state", "set_sheet_gmail")
            bot.send_message(call.message.chat.id, "<b>📊 Gmail Sheet ID দিন:</b>", parse_mode="HTML")

        elif call.data == "set_spin_reward":
            update_user_field(uid, "state", "set_spin_reward")
            bot.send_message(call.message.chat.id, "<b>💰 স্পিন এর রিওয়ার্ড কত দিতে চান? (যেমন: 1.5):</b>", parse_mode="HTML")

        elif call.data == "set_spin_limit":
            update_user_field(uid, "state", "set_spin_limit")
            bot.send_message(call.message.chat.id, "<b>🔢 দৈনিক স্পিনের লিমিট দিন (যেমন: 5):</b>", parse_mode="HTML")

        elif call.data == "set_spin_url":
            update_user_field(uid, "state", "set_spin_url")
            bot.send_message(call.message.chat.id, "<b>🔗 Adsterra Direct Link টি প্রদান করুন:</b>", parse_mode="HTML")

        elif call.data == "set_daily_bot_withdraw_limit":
            update_user_field(uid, "state", "set_daily_bot_withdraw_limit")
            bot.send_message(call.message.chat.id, "<b>💰 বটের দৈনিক মোট উইথড্র লিমিট (৳) নির্ধারণ করুন (যেমন: 50000):</b>", parse_mode="HTML")

        elif call.data.startswith("toggle_pause_"):
            target = call.data.replace("toggle_pause_", "")
            curr = get_config(f"pause_{target}", "false")
            new_val = "true" if curr == "false" else "false"
            set_config(f"pause_{target}", new_val)
            bot.answer_callback_query(call.id, f"✅ {target.upper()} Task Status Toggled!")
            bot.send_message(call.message.chat.id, f"<b>⏸️ {target.upper()} Task is now {'PAUSED' if new_val == 'true' else 'ACTIVE'}</b>", parse_mode="HTML", reply_markup=get_admin_menu())

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
            bot.send_message(call.message.chat.id, f"<b>⚙️ {meth} Configuration:</b>", parse_mode="HTML", reply_markup=markup)

        elif call.data.startswith("toggle_w_"):
            meth = call.data.replace("toggle_w_", "")
            w_methods = json.loads(get_config("withdraw_methods", "{}"))
            w_methods[meth]["enabled"] = not w_methods[meth]["enabled"]
            set_config("withdraw_methods", json.dumps(w_methods))
            bot.send_message(call.message.chat.id, f"<b>✅ {meth} Toggled!</b>", parse_mode="HTML", reply_markup=get_admin_menu())

        elif call.data.startswith("min_w_"):
            meth = call.data.replace("min_w_", "")
            update_user_field(uid, "state", f"cfg_w_min_{meth}")
            bot.send_message(call.message.chat.id, f"<b>💰 {meth} এর জন্য নতুন Minimum Limit দিন:</b>", parse_mode="HTML")

        elif call.data.startswith("max_w_"):
            meth = call.data.replace("max_w_", "")
            update_user_field(uid, "state", f"cfg_w_max_{meth}")
            bot.send_message(call.message.chat.id, f"<b>💰 {meth} এর জন্য নতুন Maximum Limit দিন:</b>", parse_mode="HTML")

        elif call.data == "btn_ban_u":
            update_user_field(uid, "state", "admin_ban_user")
            bot.send_message(call.message.chat.id, "<b>⛔ ব্যান করার জন্য ইউজার ID দিন:</b>", parse_mode="HTML")

        elif call.data == "btn_unban_u":
            update_user_field(uid, "state", "admin_unban_user")
            bot.send_message(call.message.chat.id, "<b>✅ আনব্যান করার জন্য ইউজার ID দিন:</b>", parse_mode="HTML")

        elif call.data == "btn_mod_u":
            update_user_field(uid, "state", "admin_mod_user")
            bot.send_message(call.message.chat.id, "<b>👑 সাব-এডমিন বানানোর জন্য ইউজার ID দিন:</b>", parse_mode="HTML")

        elif call.data == "btn_unmod_u":
            update_user_field(uid, "state", "admin_unmod_user")
            bot.send_message(call.message.chat.id, "<b>👤 সাব-এডমিন সরানোর জন্য ইউজার ID দিন:</b>", parse_mode="HTML")

        elif call.data == "btn_add_bal":
            update_user_field(uid, "state", "admin_add_bal_id")
            bot.send_message(call.message.chat.id, "<b>💰 যার সাথে ব্যালেন্স যোগ করবেন তার ইউজার ID দিন:</b>", parse_mode="HTML")

        elif call.data == "btn_ded_bal":
            update_user_field(uid, "state", "admin_ded_bal_id")
            bot.send_message(call.message.chat.id, "<b>💰 যার থেকে ব্যালেন্স কাটবেন তার ইউজার ID দিন:</b>", parse_mode="HTML")

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
            bot.send_message(call.message.chat.id, "<b>💰 নতুন ব্যালেন্স পরিমাণ লিখুন:</b>", parse_mode="HTML")

        elif call.data.startswith("list_pend_"):
            stype = call.data.replace("list_pend_", "")
            all_subs = fb_get("pending_submissions") or {}
            subs = [v for v in all_subs.values() if v.get("sub_type") == stype and v.get("status") == "pending"][:10]

            if not subs:
                bot.answer_callback_query(call.id, f"✅ {stype.upper()} এর কোনো পেন্ডিং সাবমিশন নেই!", show_alert=True)
                return

            for s in subs:
                markup = InlineKeyboardMarkup(row_width=2)
                markup.add(
                    ibtn("✅ Approve", callback_data=f"app_sub_{s['id']}", style="success"),
                    ibtn("❌ Reject", callback_data=f"rej_sub_{s['id']}", style="danger")
                )
                bot.send_message(call.message.chat.id, f"<b>🔎 ID:</b> <code>{s['id']}</code>\n<b>User:</b> <code>{s['user_id']}</code>\n<b>Payload:</b> <code>{s['payload']}</code>", parse_mode="HTML", reply_markup=markup)

        elif call.data.startswith("app_sub_"):
            sub_id = call.data.replace("app_sub_", "")
            sub = fb_get(f"pending_submissions/{sub_id}")
            
            if sub and sub.get("status") == "pending":
                uid_t = sub['user_id']
                rate = float(sub['rate'])
                
                fb_patch(f"pending_submissions/{sub_id}", {"status": "approved"})
                
                t_user = get_user_db(uid_t)
                new_bal = t_user['balance'] + rate
                new_inc = t_user['total_income'] + rate
                app_t = t_user['approved_tasks'] + 1
                pend_t = max(0, t_user['pending_tasks'] - 1)
                
                fb_patch(f"users/{uid_t}", {
                    "balance": new_bal, "total_income": new_inc,
                    "approved_tasks": app_t, "pending_tasks": pend_t
                })
                
                ref_id = t_user.get("referred_by")
                if ref_id:
                    ref_u = get_user_db(ref_id)
                    ref_comm = rate * 0.10
                    fb_patch(f"users/{ref_id}", {
                        "balance": ref_u['balance'] + ref_comm,
                        "total_income": ref_u['total_income'] + ref_comm
                    })
                    try: bot.send_message(ref_id, f"<b>🎉 রেফারেল ১০% কমিশন!</b>\nআপনার রেফারেল একটি কাজ সম্পন্ন করায় আপনি <b>৳{ref_comm:.2f}</b> কমিশন পেয়েছেন!", parse_mode="HTML")
                    except: pass

                log_admin_action(uid, f"Approved Task {sub_id}")
                bot.answer_callback_query(call.id, "✅ Task Approved!")
                try: bot.send_message(uid_t, f"<b>✅ আপনার কাজ এপ্রুভ করা হয়েছে!</b>\nSubmit ID: <code>{sub_id}</code>\nযোগ করা হয়েছে: <b>৳{rate}</b>", parse_mode="HTML")
                except: pass
            else:
                bot.answer_callback_query(call.id, "❌ Task Already Processed!", show_alert=True)

        elif call.data.startswith("rej_sub_"):
            sub_id = call.data.replace("rej_sub_", "")
            sub = fb_get(f"pending_submissions/{sub_id}")
            
            if sub and sub.get("status") == "pending":
                uid_t = sub['user_id']
                
                fb_patch(f"pending_submissions/{sub_id}", {"status": "rejected"})
                t_user = get_user_db(uid_t)
                rej_t = t_user['rejected_tasks'] + 1
                pend_t = max(0, t_user['pending_tasks'] - 1)
                fb_patch(f"users/{uid_t}", {"rejected_tasks": rej_t, "pending_tasks": pend_t})
                
                log_admin_action(uid, f"Rejected Task {sub_id}")
                bot.answer_callback_query(call.id, "❌ Task Rejected!")
                try: bot.send_message(uid_t, f"<b>❌ আপনার কাজ রিজেক্ট করা হয়েছে!</b>\nSubmit ID: <code>{sub_id}</code>", parse_mode="HTML")
                except: pass
            else:
                bot.answer_callback_query(call.id, "❌ Task Already Processed!", show_alert=True)

        elif call.data == "search_approval_manual":
            update_user_field(uid, "state", "admin_search_submission")
            bot.send_message(call.message.chat.id, "<b>🔎 Submit ID / 2FA / UID প্রদান করুন:</b>", parse_mode="HTML")

        elif call.data.startswith("edit_emoji_"):
            ekey = call.data.replace("edit_emoji_", "")
            update_user_field(uid, "state", f"edit_emoji_{ekey}")
            bot.send_message(call.message.chat.id, f"<b>🎨 <code>{ekey}</code> এর জন্য নতুন Emoji বা Premium Emoji ID সেন্ড করুন:</b>", parse_mode="HTML")

        elif call.data.startswith("reply_t_"):
            t_id = call.data.replace("reply_t_", "")
            update_user_field(uid, "state", f"reply_ticket_{t_id}")
            bot.send_message(call.message.chat.id, "<b>💬 রিপ্লাই টেক্সট সেন্ড করুন:</b>", parse_mode="HTML")

        elif call.data.startswith("set_vid_"):
            cat = call.data.replace("set_vid_", "")
            update_user_field(uid, "state", f"set_vid_{cat}")
            bot.send_message(call.message.chat.id, f"<b>📹 {cat.upper()} এর জন্য ভিডিওটি ফরওয়ার্ড বা আপলোড করুন:</b>", parse_mode="HTML")

        elif call.data.startswith("pay_with_"):
            req_id = call.data.replace("pay_with_", "")
            fb_patch(f"withdraw_requests/{req_id}", {"status": "approved"})
            w_data = fb_get(f"withdraw_requests/{req_id}")

            if w_data:
                log_admin_action(uid, f"Approved Withdrawal {req_id} of ৳{w_data['amount']}")
                try: bot.send_message(w_data['user_id'], f"<b>🎉 আপনার ৳{w_data['amount']} এর উইথড্র সফলভাবে পেমেন্ট করা হয়েছে!</b>", parse_mode="HTML")
                except: pass
            bot.answer_callback_query(call.id, "✅ Payment Marked as Approved!")

        elif call.data.startswith("ref_with_"):
            req_id = call.data.replace("ref_with_", "")
            w_data = fb_get(f"withdraw_requests/{req_id}")
            if w_data and w_data.get("status") == "pending":
                fb_patch(f"withdraw_requests/{req_id}", {"status": "rejected"})
                t_u = get_user_db(w_data['user_id'])
                fb_patch(f"users/{w_data['user_id']}", {"balance": t_u['balance'] + w_data['amount']})
                
                log_admin_action(uid, f"Refunded Withdrawal {req_id} of ৳{w_data['amount']}")
                try: bot.send_message(w_data['user_id'], f"<b>❌ আপনার ৳{w_data['amount']} এর উইথড্র রিকোয়েস্ট রিজেক্ট করা হয়েছে এবং ব্যালেন্স রিফান্ড করা হয়েছে।</b>", parse_mode="HTML")
                except: pass
            bot.answer_callback_query(call.id, "❌ Balance Refunded!")

        # --- DATE-WISE DYNAMIC EXPORT SUB-MENU ---
        elif call.data.startswith("export_serv_"):
            serv = call.data.replace("export_serv_", "")
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                ibtn("📅 আজকের ফাইল (Today)", callback_data=f"exp_dt_today_{serv}", style="primary"),
                ibtn("📅 গতকালকের ফাইল (Yesterday)", callback_data=f"exp_dt_yest_{serv}", style="primary"),
                ibtn("🗓️ সব অল-টাইম ফাইল (All Time)", callback_data=f"exp_dt_all_{serv}", style="success")
            )
            bot.send_message(call.message.chat.id, f"<b>📥 {serv.upper()} - এর কোন সময়ের ডাটা ফাইল ডাউনলোড করতে চান?</b>", parse_mode="HTML", reply_markup=markup)

        elif call.data.startswith("exp_dt_"):
            parts = call.data.split("_")
            filter_type = parts[2]
            serv = parts[3]

            all_subs = fb_get("pending_submissions") or {}
            target_subs = [v for v in all_subs.values() if v.get("sub_type") == serv and v.get("status") == "pending"]

            today_dt = datetime.now().date()
            yest_dt = today_dt - timedelta(days=1)

            filtered = []
            for s in target_subs:
                s_dt = datetime.fromtimestamp(s.get("created_at", 0)).date()
                if filter_type == "today" and s_dt == today_dt:
                    filtered.append(s)
                elif filter_type == "yest" and s_dt == yest_dt:
                    filtered.append(s)
                elif filter_type == "all":
                    filtered.append(s)

            if not filtered:
                bot.answer_callback_query(call.id, "❌ কোনো Unsold ডাটা ফাইল পাওয়া যায়নি!", show_alert=True)
                return

            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = f"{serv}_unsold_{filter_type}_{date_str}.csv"
            
            # STYLISH CENTER-ALIGNED FORMATTED EXPORT CSV
            with open(filename, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                # Colored Styled Header Token
                writer.writerow(["=== Submit_ID ===", "=== User_ID ===", "=== Payload_Data ===", "=== Rate ===", "=== Date_Time ==="])
                for idx, r in enumerate(filtered):
                    dt_formatted = datetime.fromtimestamp(r.get('created_at', 0)).strftime('%Y-%m-%d %H:%M')
                    writer.writerow([r.get('id'), r.get('user_id'), r.get('payload'), f"Tk {r.get('rate')}", dt_formatted])

            with open(filename, "rb") as f:
                bot.send_document(call.message.chat.id, f, caption=f"<b>📥 {serv.upper()} ({filter_type.upper()}) Unsold Data Export</b>", parse_mode="HTML")
            os.remove(filename)

    except Exception as e:
        log_error(f"Error in handle_callbacks: {e}\n{traceback.format_exc()}")

# ============================================
# --- ENGINE START ---
# ============================================
if __name__ == "__main__":
    keep_alive()
    print(f"🚀 {BOT_NAME} Production Engine running safely with Firebase Realtime Database...")
    bot.infinity_polling(skip_pending=True)
