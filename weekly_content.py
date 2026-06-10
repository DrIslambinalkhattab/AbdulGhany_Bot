"""
weekly_content.py — AbdulGhanyBot | صدقة جارية عَنْ عبد الغني
"""

import os
import sys
import requests
from datetime import datetime
import pytz
import random

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID   = os.environ.get("CHAT_ID", "-1003844022713")
TOPIC_ID  = os.environ.get("TOPIC_ID", "33")
CAIRO_TZ  = pytz.timezone("Africa/Cairo")
BASE_URL  = f"https://api.telegram.org/bot{BOT_TOKEN}"

def _base_params():
    return {"chat_id": CHAT_ID, "message_thread_id": TOPIC_ID}

def send_text(text: str):
    r = requests.post(
        f"{BASE_URL}/sendMessage",
        data={**_base_params(), "text": text, "parse_mode": "HTML"},
    )
    print(f"📨 {r.status_code}")

# ─────────────────────────────────────────────
#  تذكير الصيام
# ─────────────────────────────────────────────
FASTING_MSGS = {
    "monday": [
        (
            "🌙 <b>تذكير | صيام الاثنين</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "غداً الاثنين — من السنة صيامه 🤍\n\n"
            "<i>«كان النبي ﷺ يصوم الاثنين والخميس\n"
            "فقيل له — فقال:\n"
            "تُعرض الأعمال يوم الاثنين والخميس\n"
            "فأحب أن يُعرض عملي وأنا صائم»</i>\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🌿 <i>بيّت النية الليلة — والأجر عند الله</i>"
        ),
        (
            "🌙 <b>الاثنين على الأبواب</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "فرصة جديدة للصيام غداً 🌿\n\n"
            "<i>«من صام يوماً في سبيل الله\n"
            "باعد الله وجهه عن النار سبعين خريفاً»</i>\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🤍 <i>يوم واحد — أجر لا يُحصى</i>"
        ),
    ],
    "thursday": [
        (
            "🌙 <b>تذكير | صيام الخميس</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "غداً الخميس — يوم تُعرض فيه الأعمال على الله 🤍\n\n"
            "<i>«أحب أن يُعرض عملي\n"
            "وأنا صائم»</i>\n"
            "— النبي ﷺ\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🌿 <i>اجعل الخميس يوم صومك — يُرفع عملك وأنت في أفضل حال</i>"
        ),
        (
            "🌙 <b>الخميس يطلّ علينا</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "تذكير بسنّة النبي ﷺ في صيام الخميس 🌿\n\n"
            "<i>«الصيام جُنّة — وإذا كان يوم صوم أحدكم\n"
            "فلا يرفث ولا يصخب\n"
            "فإن سابّه أحد أو قاتله\n"
            "فليقل: إني امرؤ صائم»</i>\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🤲 <i>اللهم أعنّا على صيامه وقيامه</i>"
        ),
    ],
}

def task_remind_fasting_monday():
    print("🌙 تذكير صيام الاثنين")
    send_text(random.choice(FASTING_MSGS["monday"]))

def task_remind_fasting_thursday():
    print("🌙 تذكير صيام الخميس")
    send_text(random.choice(FASTING_MSGS["thursday"]))

# ─────────────────────────────────────────────
#  نقطة الدخول
# ─────────────────────────────────────────────
TASKS = {
    "fasting_monday"  : task_remind_fasting_monday,
    "fasting_thursday": task_remind_fasting_thursday,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in TASKS:
        print(f"الاستخدام: python weekly_content.py <{'|'.join(TASKS)}>")
        sys.exit(1)
    task = sys.argv[1]
    print(f"▶️  {task}")
    TASKS[task]()
    print("✅ انتهت المهمة")
