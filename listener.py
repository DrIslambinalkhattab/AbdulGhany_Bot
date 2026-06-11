"""
listener.py — يراقب أحداث تيليجرام ويُسجّلها (مع وقت الحدث)

ملاحظات:
- مصمم ليعمل عبر GitHub Actions على شكل دفعات (Batch) ثم يخرج.
- يحفظ offset في listener_offset.json حتى لا يعيد معالجة نفس الأحداث.
"""

import os
import json
import time
from datetime import datetime

import pytz
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = os.environ["ADMIN_CHAT_ID"]
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Google Apps Script endpoint (كما هو)
SHEETS_URL = os.environ.get(
    "SHEETS_URL",
    "https://script.google.com/macros/s/AKfycbwaOz5e6qHvtse1SqeVePH4eVV_y3WTt2pheEzDInX2VI8QHzSvV-4lafZJ6S73z36I/exec",
)

OFFSET_FILE = "listener_offset.json"
CAIRO_TZ = pytz.timezone("Africa/Cairo")

# مدة التشغيل (ثواني) — مناسب للتشغيل اليومي
MAX_RUNTIME_SEC = int(os.environ.get("MAX_RUNTIME_SEC", "180"))


def load_offset() -> int:
    if os.path.exists(OFFSET_FILE):
        with open(OFFSET_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("offset", 0)
    return 0


def save_offset(offset: int):
    with open(OFFSET_FILE, "w", encoding="utf-8") as f:
        json.dump({"offset": offset}, f)


def fmt_ts(ts: int | None) -> str:
    """ts: unix seconds"""
    if not ts:
        return "غير معروف"
    dt = datetime.fromtimestamp(ts, tz=CAIRO_TZ)
    return dt.strftime("%Y-%m-%d %I:%M:%S %p (Cairo)")


def log_to_sheets(user: dict, event: str, event_ts: int | None):
    """يسجل الحدث مع وقته الحقيقي."""
    payload = {
        "user_id": user.get("id"),
        "name": user.get("first_name", ""),
        "username": user.get("username", ""),
        "event": event,
        "event_count": 1,
        "event_ts": event_ts or 0,  # unix
        "event_time": fmt_ts(event_ts),
    }
    try:
        requests.post(SHEETS_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ Sheets error: {e}")


def send_admin(text: str):
    try:
        requests.post(
            f"{BASE_URL}/sendMessage",
            data={
                "chat_id": ADMIN_ID,
                "text": text,
                "parse_mode": "HTML",
            },
            timeout=15,
        )
    except Exception as e:
        print(f"⚠️ Admin notify error: {e}")


def process_update(update: dict):
    # ─── حد ضغط /start ───
    msg = update.get("message", {})
    if msg.get("text", "").startswith("/start"):
        user = msg.get("from", {})
        event_ts = msg.get("date")  # unix seconds
        name = user.get("first_name", "")
        username = f"@{user['username']}" if user.get("username") else "بدون يوزرنيم"
        uid = user.get("id")

        log_to_sheets(user, "start", event_ts)
        send_admin(
            "🟢 <b>مستخدم بدأ البوت</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            f"👤 الاسم: <b>{name}</b>\n"
            f"🔗 يوزرنيم: {username}\n"
            f"🆔 ID: <code>{uid}</code>\n"
            f"🕒 وقت الحدث: <b>{fmt_ts(event_ts)}</b>"
        )

    # ─── أحداث تغيير حالة البوت لدى المستخدم ───
    member = update.get("my_chat_member", {})
    new_status = member.get("new_chat_member", {}).get("status", "")
    old_status = member.get("old_chat_member", {}).get("status", "")
    event_ts = member.get("date")  # unix seconds

    if new_status == "kicked":
        user = member.get("from", {})
        name = user.get("first_name", "")
        username = f"@{user['username']}" if user.get("username") else "بدون يوزرنيم"
        uid = user.get("id")

        log_to_sheets(user, "blocked", event_ts)
        send_admin(
            "🔴 <b>مستخدم حظر البوت</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            f"👤 الاسم: <b>{name}</b>\n"
            f"🔗 يوزرنيم: {username}\n"
            f"🆔 ID: <code>{uid}</code>\n"
            f"🕒 وقت الحدث: <b>{fmt_ts(event_ts)}</b>"
        )

    if old_status == "kicked" and new_status == "member":
        user = member.get("from", {})
        name = user.get("first_name", "")
        username = f"@{user['username']}" if user.get("username") else "بدون يوزرنيم"
        uid = user.get("id")

        log_to_sheets(user, "unblocked", event_ts)
        send_admin(
            "🔵 <b>مستخدم رجع بعد الحظر</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            f"👤 الاسم: <b>{name}</b>\n"
            f"🔗 يوزرنيم: {username}\n"
            f"🆔 ID: <code>{uid}</code>\n"
            f"🕒 وقت الحدث: <b>{fmt_ts(event_ts)}</b>"
        )


def run_polling():
    offset = load_offset()
    print(f"👂 بدأ الاستماع للأحداث... (offset: {offset}) | max_runtime={MAX_RUNTIME_SEC}s")

    start = time.time()
    while True:
        elapsed = time.time() - start
        if elapsed >= MAX_RUNTIME_SEC:
            print("⏹️ انتهت مدة التشغيل — إغلاق المستمع")
            return

        # نخلي long-polling محترم لكن مايتعدّاش الوقت المتبقي
        remaining = int(MAX_RUNTIME_SEC - elapsed)
        long_poll_timeout = min(30, max(5, remaining))

        try:
            r = requests.get(
                f"{BASE_URL}/getUpdates",
                params={
                    "offset": offset,
                    "timeout": long_poll_timeout,
                    "allowed_updates": ["message", "my_chat_member"],
                },
                timeout=long_poll_timeout + 10,
            )
            data = r.json()
            updates = data.get("result", [])

            for update in updates:
                process_update(update)
                offset = update["update_id"] + 1
                save_offset(offset)

        except Exception as e:
            print(f"⚠️ خطأ: {e}")
            time.sleep(3)


if __name__ == "__main__":
    run_polling()
