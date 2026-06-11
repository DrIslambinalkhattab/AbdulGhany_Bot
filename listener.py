"""
listener.py — يراقب الأحداث ويبعت notifications للأدمن
"""

import os
import json
import time
import requests

BOT_TOKEN  = os.environ["BOT_TOKEN"]
ADMIN_ID   = os.environ["ADMIN_CHAT_ID"]
BASE_URL   = f"https://api.telegram.org/bot{BOT_TOKEN}"
SHEETS_URL = "https://script.google.com/macros/s/AKfycbwaOz5e6qHvtse1SqeVePH4eVV_y3WTt2pheEzDInX2VI8QHzSvV-4lafZJ6S73z36I/exec"
OFFSET_FILE = "listener_offset.json"

def load_offset() -> int:
    if os.path.exists(OFFSET_FILE):
        with open(OFFSET_FILE) as f:
            return json.load(f).get("offset", 0)
    return 0

def save_offset(offset: int):
    with open(OFFSET_FILE, "w") as f:
        json.dump({"offset": offset}, f)

def log_to_sheets(user: dict, event: str):
    try:
        requests.post(SHEETS_URL, json={
            "user_id"    : user["id"],
            "name"       : user.get("first_name", ""),
            "username"   : user.get("username", ""),
            "event"      : event,
            "event_count": 1
        }, timeout=10)
    except Exception as e:
        print(f"⚠️ Sheets error: {e}")

def send_admin(text: str):
    requests.post(f"{BASE_URL}/sendMessage", data={
        "chat_id"   : ADMIN_ID,
        "text"      : text,
        "parse_mode": "HTML"
    })

def process_update(update: dict):
    # ─── حد ضغط /start ───
    msg = update.get("message", {})
    if msg.get("text", "").startswith("/start"):
        user     = msg["from"]
        name     = user.get("first_name", "")
        username = f"@{user['username']}" if user.get("username") else "بدون يوزرنيم"
        uid      = user["id"]
        log_to_sheets(user, "start")
        send_admin(
            f"🟢 <b>مستخدم جديد بدأ البوت</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"👤 الاسم: <b>{name}</b>\n"
            f"🔗 يوزرنيم: {username}\n"
            f"🆔 ID: <code>{uid}</code>"
        )

    # ─── حد حظر البوت ───
    member     = update.get("my_chat_member", {})
    new_status = member.get("new_chat_member", {}).get("status", "")
    old_status = member.get("old_chat_member", {}).get("status", "")

    if new_status == "kicked":
        user     = member["from"]
        name     = user.get("first_name", "")
        username = f"@{user['username']}" if user.get("username") else "بدون يوزرنيم"
        uid      = user["id"]
        log_to_sheets(user, "blocked")
        send_admin(
            f"🔴 <b>مستخدم حظر البوت</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"👤 الاسم: <b>{name}</b>\n"
            f"🔗 يوزرنيم: {username}\n"
            f"🆔 ID: <code>{uid}</code>"
        )

    # ─── حد رجع بعد الحظر ───
    if old_status == "kicked" and new_status == "member":
        user     = member["from"]
        name     = user.get("first_name", "")
        username = f"@{user['username']}" if user.get("username") else "بدون يوزرنيم"
        uid      = user["id"]
        log_to_sheets(user, "unblocked")
        send_admin(
            f"🔵 <b>مستخدم رجع بعد الحظر</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"👤 الاسم: <b>{name}</b>\n"
            f"🔗 يوزرنيم: {username}\n"
            f"🆔 ID: <code>{uid}</code>"
        )

def run_polling():
    offset = load_offset()
    print(f"👂 بدأ الاستماع للأحداث... (offset: {offset})")
    while True:
        try:
            r = requests.get(f"{BASE_URL}/getUpdates", params={
                "offset"         : offset,
                "timeout"        : 30,
                "allowed_updates": ["message", "my_chat_member"]
            }, timeout=35)
            updates = r.json().get("result", [])
            for update in updates:
                process_update(update)
                offset = update["update_id"] + 1
                save_offset(offset)
        except Exception as e:
            print(f"⚠️ خطأ: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_polling()
