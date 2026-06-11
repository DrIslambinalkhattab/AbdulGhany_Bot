"""
listener.py — يراقب الأحداث ويبعت notifications للأدمن
"""

import os
import time
import requests

BOT_TOKEN  = os.environ["BOT_TOKEN"]
ADMIN_ID   = os.environ["ADMIN_CHAT_ID"]   # ID بتاعك الشخصي
BASE_URL   = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_admin(text: str):
    """يبعت رسالة لك أنت مباشرة"""
    requests.post(f"{BASE_URL}/sendMessage", data={
        "chat_id": ADMIN_ID,
        "text": text,
        "parse_mode": "HTML"
    })

def process_update(update: dict):
    # ─── حد ضغط /start ───
    msg = update.get("message", {})
    if msg.get("text", "").startswith("/start"):
        user = msg["from"]
        name = user.get("first_name", "")
        username = f"@{user['username']}" if user.get("username") else "بدون يوزرنيم"
        uid  = user["id"]
        send_admin(
            f"🟢 <b>مستخدم جديد بدأ البوت</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"👤 الاسم: <b>{name}</b>\n"
            f"🔗 يوزرنيم: {username}\n"
            f"🆔 ID: <code>{uid}</code>"
        )

    # ─── حد حظر البوت ───
    member = update.get("my_chat_member", {})
    new_status = member.get("new_chat_member", {}).get("status", "")
    if new_status == "kicked":
        user = member["from"]
        name = user.get("first_name", "")
        username = f"@{user['username']}" if user.get("username") else "بدون يوزرنيم"
        uid  = user["id"]
        send_admin(
            f"🔴 <b>مستخدم حظر البوت</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"👤 الاسم: <b>{name}</b>\n"
            f"🔗 يوزرنيم: {username}\n"
            f"🆔 ID: <code>{uid}</code>"
        )

def run_polling():
    offset = 0
    print("👂 بدأ الاستماع للأحداث...")
    while True:
        try:
            r = requests.get(f"{BASE_URL}/getUpdates", params={
                "offset": offset,
                "timeout": 30,
                "allowed_updates": ["message", "my_chat_member"]
            }, timeout=35)
            updates = r.json().get("result", [])
            for update in updates:
                process_update(update)
                offset = update["update_id"] + 1
        except Exception as e:
            print(f"⚠️ خطأ: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_polling()
