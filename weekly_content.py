import os
import sys
import requests
from datetime import datetime
import pytz
import random

# جلب المتغيرات (تنظيف المسافات المخفية)
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ.get("CHAT_ID", "-1003844022713")
TOPIC_ID = os.environ.get("TOPIC_ID", "33")
CAIRO_TZ = pytz.timezone("Africa/Cairo")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

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
            "<blockquote><b>تذكير صيامُ يومِ غدٍ الإثنين 🌙.</b></blockquote>\n"
            "<b>إغتنِمْ ما تَبقى مِن أيامِكَ المَعدودةِ بالصِّيام.</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            "<b>قال الله تعالى في الحديث القدسي:</b>\n"
            "<i>«كلُّ عملِ ابنِ آدمَ له إلا الصومَ، فإنه لي وأنا أجزي به».</i>\n\n"
            "<b>قال رسول الله صلى الله عليه وسلم:</b>\n"
            "<i>«مَن صام يومًا في سبيلِ الله، باعدَ اللهُ وجهَهُ عن النارِ سبعينَ خريفًا»</i>\n"
            "━━━━━━━━━━━━━━━━\n"
            "<b>فمَن أرَادَ أن يَفُوز بالدخولِ من بابِ الريَّان فليُبادِر بالصيام 🩶</b>\n"
            "<blockquote><b>إن لم تصم فذكّر غيرك فـ هنيئاً لمن صام واحتسب، وكتب الله لنا ولكم الأجر.</b></blockquote>"
        ),
    ],
    "thursday": [
        (
            "<blockquote><b>تذكير صيامُ يومِ غدٍ الخميس 🌙.</b></blockquote>\n"
            "<b>إغتنِمْ ما تَبقى مِن أيامِكَ المَعدودةِ بالصِّيام.</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            "<b>قال الله تعالى في الحديث القدسي:</b>\n"
            "<i>«كلُّ عملِ ابنِ آدمَ له إلا الصومَ، فإنه لي وأنا أجزي به».</i>\n\n"
            "<b>قال رسول الله صلى الله عليه وسلم:</b>\n"
            "<i>«مَن صام يومًا في سبيلِ الله، باعدَ اللهُ وجهَهُ عن النارِ سبعينَ خريفًا»</i>\n"
            "━━━━━━━━━━━━━━━━\n"
            "<b>فمَن أرَادَ أن يَفُوز بالدخولِ من بابِ الريَّان فليُبادِر بالصيام 🩶</b>\n"
            "<blockquote><b>إن لم تصم فذكّر غيرك فـ هنيئاً لمن صام واحتسب، وكتب الله لنا ولكم الأجر.</b></blockquote>"
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
    "fasting_monday": task_remind_fasting_monday,
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
