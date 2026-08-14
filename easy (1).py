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
for pkg in ["flask", "pyTelegramBotAPI"]:
    mod = "telebot" if pkg == "pyTelegramBotAPI" else pkg
    if importlib.util.find_spec(mod) is None:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

from flask import Flask
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

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
        
        # Key-Value Config Store
        c.execute('''CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        
        # Users Table
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
            is_banned INTEGER DEFAULT 0,
            approved_tasks INTEGER DEFAULT 0,
            rejected_tasks INTEGER DEFAULT 0,
            pending_tasks INTEGER DEFAULT 0,
            completed_accounts INTEGER DEFAULT 0,
            last_spin_time REAL DEFAULT 0,
            created_at REAL
        )''')

        # Submitted Data Tracking (Anti-Duplicate Guard)
        c.execute('''CREATE TABLE IF NOT EXISTS submitted_records (
            record_value TEXT PRIMARY KEY,
            record_type TEXT,
            user_id INTEGER,
            submitted_at REAL
        )''')

        # Submissions Pending / Completed
        c.execute('''CREATE TABLE IF NOT EXISTS pending_submissions (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            sub_type TEXT,
            payload TEXT,
            status TEXT DEFAULT 'pending',
            created_at REAL
        )''')

        # Tasks Table
        c.execute('''CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_type TEXT,
            link TEXT,
            description TEXT,
            rate REAL,
            task_limit INTEGER,
            completed INTEGER DEFAULT 0
        )''')

        # Defaults Inserts
        defaults = {
            "force_channels": json.dumps([]),
            "ref_bonus": "10.0",
            "ins_pass": "KingInsPass",
            "fb_pass": "KingFbPass",
            "gmail_pass": "KingGmailPass",
            "recovery_email": "tasrikvai8001@gmail.com",
            "emojis": json.dumps({"balance": "💰", "work": "💼", "withdraw": "📥", "invite": "👥"}),
            "spin_ad_url": "https://example.com/adsterra",
            "spin_reward": "1.5",
            "sheets_config": json.dumps({"ins": "", "fb": "", "gmail": ""}),
            "withdraw_methods": json.dumps({
                "bKash": {"enabled": True, "min": 50.0},
                "Nagad": {"enabled": True, "min": 50.0},
                "USDT BEP20": {"enabled": True, "min": 100.0}
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
# --- DYNAMIC PASSWORD & DATA HELPERS ---
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
TXT_WORK_MAIN = "💼 কাজ•"
TXT_TODAY_WORK = "🔥 আজকের কাজ"
TXT_BALANCE = "💰 ব্যালেন্স"
TXT_WITHDRAW = "📥 উত্তোলন"
TXT_REFER = "👥 রেফার"
TXT_SUPPORT = "🎧 সাপোর্ট"
TXT_NEWBIE = "❓ আমি নতুন"
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
    markup.add(rbtn("📸 ইনস্টাগ্রাম কাজ", "primary"), rbtn("📧 Gmail কাজ", "primary"))
    markup.add(rbtn("📘 ফেসবুক কাজ", "primary"))
    markup.add(rbtn(TXT_BACK, "danger"))
    return markup

def get_admin_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(rbtn("📢 Set Force Join", "primary"), rbtn("🎁 Set Ref Bonus", "success"))
    markup.add(rbtn("💳 Set Min Withdraw", "primary"), rbtn("🔑 Set FB Pass", "primary"))
    markup.add(rbtn("🔑 Set Ins Pass", "primary"), rbtn("🔑 Set Gmail Pass", "primary"))
    markup.add(rbtn("📧 Set Recovery Email", "primary"), rbtn("🎨 Edit Emoji IDs", "primary"))
    markup.add(rbtn("🌀 Spin & Ad Settings", "primary"), rbtn("📊 Google Sheets Config", "primary"))
    markup.add(rbtn("➕ Add App/TG Task", "success"), rbtn("📥 Export Unsold Files", "primary"))
    markup.add(rbtn("🔎 Pending Approvals", "primary"), rbtn("📥 Pending Withdraws", "primary"))
    markup.add(rbtn("📢 Broadcast Message", "primary"), rbtn("📊 Bot Statistics", "primary"))
    markup.add(rbtn("⛔ Ban/Unban User", "danger"), rbtn("➕ Add/Deduct Balance", "success"))
    markup.add(rbtn("👑 Promote/Demote", "primary"), rbtn("🧹 Database Cleanup", "danger"))
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
        bot.send_message(message.chat.id, "🛠️ **বট বর্তমানে মেইনটেন্যান্স মোডে আছে।** খুব শীঘ্রই আবার কাজ চালু হবে।", parse_mode="Markdown")
        return

    u = get_user_db(uid)
    if u["is_banned"]:
        bot.send_message(message.chat.id, "⛔ **আপনি এই বটে ব্লকড আছেন!**", parse_mode="Markdown")
        return

    # Referral Check
    args = message.text.split()
    if len(args) > 1 and not u["referred_by"]:
        ref_id = args[1]
        if ref_id.isdigit() and int(ref_id) != uid:
            update_user_field(uid, "referred_by", int(ref_id))

    if not check_force_join(uid):
        msg = f"👋 **Welcome to {BOT_NAME}!**\n\nবটের কাজ করার জন্য নিচের চ্যানেলগুলোতে জয়েন করুন এবং 'Verify Now' চাপুন:"
        bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=get_force_join_markup())
        return

    bot.send_message(message.chat.id, f"💎 **Welcome to {BOT_NAME}!**\nনিচের প্রিমিয়াম মেনু থেকে আপনার পছন্দ বেছে নিন:", parse_mode="Markdown", reply_markup=get_main_menu(uid))

# ============================================
# --- MAIN MESSAGE ROUTER ---
# ============================================
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'document'])
def handle_all_messages(message):
    uid = message.from_user.id
    txt = message.text.strip() if message.text else ""
    u = get_user_db(uid)

    if u["is_banned"]: return

    # Admin State Processing
    state = u.get("state")
    if state and uid == ADMIN_ID:
        if state == "set_fb_pass":
            set_config("fb_pass", txt)
            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, f"✅ FB Pass Base set to: `{txt}`", parse_mode="Markdown")
            return
        elif state == "set_ins_pass":
            set_config("ins_pass", txt)
            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, f"✅ Ins Pass Base set to: `{txt}`", parse_mode="Markdown")
            return
        elif state == "set_gmail_pass":
            set_config("gmail_pass", txt)
            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, f"✅ Gmail Pass Base set to: `{txt}`", parse_mode="Markdown")
            return
        elif state == "set_ref_bonus":
            set_config("ref_bonus", txt)
            update_user_field(uid, "state", None)
            bot.send_message(message.chat.id, f"✅ Referral Bonus set to: ৳{txt}")
            return
        elif state == "enter_2fa_code":
            if check_duplicate_and_save(txt, "2fa", uid):
                bot.send_message(message.chat.id, "❌ **এই 2FA কোডটি আগে ব্যবহার করা হয়েছে!**")
                return
            # 6 Digit OTP Mock Gen
            otp = str(random.randint(100000, 999999))
            markup = ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(rbtn("অ্যাকাউন্ট খোলা শেষ", "success"))
            bot.send_message(message.chat.id, f"🔑 **Your 2FA OTP Code:** `{otp}`\n\n(কপি করতে কোডে চাপুন)", parse_mode="Markdown", reply_markup=markup)
            update_user_field(uid, "state", None)
            return

    # Task Photo Proof Submission Handler
    if message.photo and state and state.startswith("sub_app_proof_"):
        task_id = state.replace("sub_app_proof_", "")
        sub_id = f"sub_{uid}_{int(time.time())}"
        photo_id = message.photo[-1].file_id
        
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO pending_submissions (id, user_id, sub_type, payload) VALUES (?, ?, ?, ?)",
                  (sub_id, uid, "app_ss", json.dumps({"photo": photo_id, "task_id": task_id})))
        conn.commit()
        conn.close()

        update_user_field(uid, "state", None)
        bot.send_message(message.chat.id, "✅ **আপনার স্ক্রিনশট জমা হয়েছে!** এডমিন অনুমোদন দিলে ব্যালেন্স যোগ হবে।", reply_markup=get_main_menu(uid))
        return

    # User States
    if state == "enter_fb_uid":
        if check_duplicate_and_save(txt, "fb_uid", uid):
            bot.send_message(message.chat.id, "❌ **এই FB UID টি ইতিমধ্যেই সিস্টেমে জমা দেওয়া হয়েছে!**")
            return
        update_user_field(uid, "temp_data", json.dumps({"fb_uid": txt}))
        update_user_field(uid, "state", "enter_fb_cookie")
        bot.send_message(message.chat.id, "🍪 **এবার আপনার FB Cookie টি সেন্ড করুন:**")
        return
    elif state == "enter_fb_cookie":
        temp = json.loads(u["temp_data"] or "{}")
        temp["cookie"] = txt
        update_user_field(uid, "temp_data", json.dumps(temp))
        update_user_field(uid, "state", None)
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(rbtn("অ্যাকাউন্ট খোলা শেষ", "success"))
        bot.send_message(message.chat.id, "✅ **তথ্য সংগৃহীত হয়েছে!** কাজ শেষ করতে নিচের বাটনে চাপ দিন:", reply_markup=markup)
        return

    # Dynamic Menu Actions
    if txt == TXT_WORK_MAIN:
        bot.send_message(message.chat.id, "💼 **কাজ অপশন নির্বাচন করুন:**", reply_markup=get_work_menu())
    elif txt == TXT_BACK:
        update_user_field(uid, "state", None)
        bot.send_message(message.chat.id, "🏠 Main Menu", reply_markup=get_main_menu(uid))

    elif txt == "📸 ইনস্টাগ্রাম কাজ":
        pass_val = generate_dynamic_password("ins_pass")
        _, _, un = generate_random_identity()
        temp_data = json.dumps({"start_time": time.time(), "username": un, "pass": pass_val})
        update_user_field(uid, "temp_data", temp_data)

        msg = (f"📸 **Instagram Account Creation**\n\n"
               f"👤 Username: `{un}`\n"
               f"🔑 Password: `{pass_val}`\n\n"
               f"অ্যাকাউন্ট খুলে 2FA সেটআপ বাটনে চাপ দিন।")
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(ibtn("🔑 2FA সেট", callback_data="start_2fa_setup", style="success"),
                   ibtn("Cancel ❌", callback_data="cancel_task", style="danger"))
        bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=markup)

    elif txt == "📘 ফেসবুক কাজ":
        pass_val = generate_dynamic_password("fb_pass")
        fn, ln, _ = generate_random_identity()
        msg = (f"📘 **Facebook Account Creation**\n\n"
               f"👤 First Name: `{fn}`\n"
               f"👤 Last Name: `{ln}`\n"
               f"🔑 Password: `{pass_val}`")
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(rbtn("Send UID", "primary"), rbtn("Cancel ❌", "danger"))
        bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=markup)

    elif txt == "Send UID":
        update_user_field(uid, "state", "enter_fb_uid")
        bot.send_message(message.chat.id, "🆔 **আপনার Facebook UID প্রদান করুন:**")

    elif txt == "অ্যাকাউন্ট খোলা শেষ":
        update_user_field(uid, "state", None)
        update_user_field(uid, "completed_accounts", u.get("completed_accounts", 0) + 1)
        bot.send_message(message.chat.id, "🎉 **আপনার কাজ সফলভাবে ডাটাবেজ ও সিটে জমা হয়েছে!**", reply_markup=get_main_menu(uid))

    elif txt == "📧 Gmail কাজ":
        pass_val = generate_dynamic_password("gmail_pass")
        fn, ln, un = generate_random_identity()
        g_email = f"{un}@gmail.com"
        temp_data = json.dumps({"start_time": time.time(), "email": g_email, "pass": pass_val})
        update_user_field(uid, "temp_data", temp_data)

        msg = (f"📧 **New Gmail Sell Task**\n\n"
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
        if time.time() - start_t < 120:
            bot.send_message(message.chat.id, "❌ **আপনি জিমেইল অ্যাকাউন্ট খুলেননি!**\nদয়া করে সত্যিকারে অ্যাকাউন্ট খুলে আবার চেষ্টা করুন।", reply_markup=get_main_menu(uid))
        else:
            bot.send_message(message.chat.id, "✅ **জিমেইল কাজ সফলভাবে জমা নেয়া হয়েছে!**", reply_markup=get_main_menu(uid))

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
               f"💰 মোট ব্যালেন্স: **৳{u['balance']:.2f}**\n"
               f"👥 মোট রেফার: **{u['referrals']}**\n"
               f"📤 মোট উইথড্র: **৳{u['total_withdraw']:.2f}**\n"
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
        msg = (f"👥 **Refer & Earn!**\n\n"
               f"আপনার রেফারেল লিংক:\n`{link}`\n\n"
               f"💡 নিয়ম: যাকে রেফার করবেন সে একটি জিমেইল কাজ শেষ করলে **৳{bonus}** রেফার বোনাস পাবেন। সাথে ১০% লাইফটাইম কমিশন!")
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")

    elif txt == TXT_ADMIN_PANEL and (uid == ADMIN_ID or u.get("role") in ["admin", "sub_admin"]):
        bot.send_message(message.chat.id, "⚙️ **Admin Control Panel**", reply_markup=get_admin_menu())

    elif txt == "🔑 Set FB Pass" and uid == ADMIN_ID:
        update_user_field(uid, "state", "set_fb_pass")
        bot.send_message(message.chat.id, "FB পাসওয়ার্ডের বেস নাম দিন:")
    elif txt == "🔑 Set Ins Pass" and uid == ADMIN_ID:
        update_user_field(uid, "state", "set_ins_pass")
        bot.send_message(message.chat.id, "Instagram পাসওয়ার্ডের বেস নাম দিন:")
    elif txt == "🔑 Set Gmail Pass" and uid == ADMIN_ID:
        update_user_field(uid, "state", "set_gmail_pass")
        bot.send_message(message.chat.id, "Gmail পাসওয়ার্ডের বেস নাম দিন:")
    elif txt == "🎁 Set Ref Bonus" and uid == ADMIN_ID:
        update_user_field(uid, "state", "set_ref_bonus")
        bot.send_message(message.chat.id, "নতুন রেফার বোনাসের পরিমাণ দিন:")

    elif txt == "⚡ Maintenance Mode" and uid == ADMIN_ID:
        curr = get_config("maintenance_mode", "false")
        new_val = "true" if curr == "false" else "false"
        set_config("maintenance_mode", new_val)
        bot.send_message(message.chat.id, f"⚡ Maintenance Mode Changed to: `{new_val}`", parse_mode="Markdown")

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

    elif call.data == "cancel_task":
        update_user_field(uid, "state", None)
        bot.answer_callback_query(call.id, "Task Cancelled")
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass

    elif call.data == "open_spin_game":
        last_spin = u.get("last_spin_time", 0)
        ad_url = get_config("spin_ad_url", "https://google.com")
        if time.time() - last_spin < 30:
            rem = int(30 - (time.time() - last_spin))
            bot.answer_callback_query(call.id, f"⏳ আপনাকে আরও {rem} সেকেন্ড এড দেখতে হবে!", show_alert=True)
            return
        
        rew = float(get_config("spin_reward", "1.5"))
        update_user_field(uid, "balance", u["balance"] + rew)
        update_user_field(uid, "last_spin_time", time.time())
        
        markup = InlineKeyboardMarkup()
        markup.add(ibtn("📺 Watch Ad to Unlock Spin", url=ad_url, style="success"))
        bot.send_message(call.message.chat.id, f"🎉 **স্পিন সফল! আপনি ৳{rew} পেয়েছেন।**\nপরবর্তী স্পিন পাবেন ৩০ সেকেন্ড পর অ্যাড দেখার পরে:", reply_markup=markup)

    elif call.data == "open_invite_rewards":
        acc_cnt = u.get("completed_accounts", 0)
        msg = (f"🎁 **আমন্ত্রণ ও টাস্ক কমপ্লিট পুরষ্কার**\n\n"
               f"আপনার বর্তমান সাবমিট করা অ্যাকাউন্ট: **{acc_cnt} টি**\n\n"
               f"• ৩০ অ্যাকাউন্ট = ৳৫\n"
               f"• ৫০ অ্যাকাউন্ট = ৳১০\n"
               f"• ১০০ অ্যাকাউন্ট = ৳২৫\n\n"
               f"• ১০ রেফার = ৳২০\n"
               f"• ১০০ রেফার = ৳৩০০")
        bot.send_message(call.message.chat.id, msg, parse_mode="Markdown")

    elif call.data.startswith("with_meth_"):
        meth = call.data.replace("with_meth_", "")
        w_methods = json.loads(get_config("withdraw_methods", "{}"))
        min_limit = w_methods[meth]["min"]
        
        if u["balance"] < min_limit:
            bot.answer_callback_query(call.id, f"❌ আপনার পর্যাপ্ত ব্যালেন্স নেই! মিনিমাম ৳{min_limit}", show_alert=True)
            return

        update_user_field(uid, "state", f"withdraw_number_{meth}")
        bot.send_message(call.message.chat.id, f"📱 **আপনার {meth} নম্বর/এড্রেস প্রদান করুন:**")

# ============================================
# --- ENGINE START ---
# ============================================
if __name__ == "__main__":
    keep_alive()
    print(f"🚀 {BOT_NAME} Production Engine running on SQLite3...")
    bot.infinity_polling()
