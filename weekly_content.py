import os
import sys
import requests
from datetime import datetime
import pytz
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
        timeout=10,
    )
    print(f"📨 {r.status_code}")

def send_error_alert(task_name: str, error: Exception):
    """يُرسل تنبيه خطأ في الشات مع mention للمسؤول بشكل آمن تماماً"""
    import traceback
    import html

    # 1. جلب الـ Traceback بأمان والتعامل معه بنظافة
    raw_tb = traceback.format_exc()
    if not raw_tb or raw_tb.strip() == "NoneType: None":
        # إذا لم يكن هناك traceback (تم استدعاء الدالة خارج الـ except مثلاً)
        raw_tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))

    # نأخذ آخر 800 حرف من الـ traceback الخام أولاً ثم ننظفه بـ html.escape
    tb_safe = html.escape(raw_tb[-800:])
    
    # 2. تنظيف وتحديد طول النصوص الأخرى لضمان عدم تخطي حد تليجرام الكلي (4096 حرف)
    task_safe = html.escape(str(task_name)[:100]) # تحديد الطول بـ 100 حرف كمثال لحمايتك
    error_type_safe = html.escape(type(error).__name__)
    error_details_safe = html.escape(str(error)[:400]) # رفعناها لـ 400 حرف لأنها الأهم
    
    # 3. بناء الرسالة مع تاغات HTML المتوافقة تماماً
    msg = (
        f"⚠️ <blockquote><b>خطأ في مهمة:</b> <code>{task_safe}</code></blockquote>\n\n"
        f"<b>النوع:</b> <code>{error_type_safe}</code>\n"
        f"<b>التفاصيل:</b> <code>{error_details_safe}</code>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"<b>الـ Traceback:</b>\n<code>{tb_safe}</code>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"<blockquote>🔔 <b><a href='https://t.me/DrIslambinalkhattab_1'>@DrIslambinalkhattab_1</a> راجع الأمر.</b></blockquote>"
    )
    
    try:
        response = requests.post(
            f"{BASE_URL}/sendMessage",
            data={**_base_params(), "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
        if not response.ok:
            print(f"❌ تليجرام رفض إرسال التنبيه: {response.text}")
            
    except Exception as e:
        print(f"❌ فشل اتصال إرسال تنبيه الخطأ: {e}")

# ─────────────────────────────────────────────
#  تذكير الصيام
# ─────────────────────────────────────────────
FASTING_TEMPLATE = (
    "<blockquote><b>تذكير صيامُ يومِ غدٍ {day} 🌙.</b></blockquote>\n"
    "<b>إغتنِمْ ما تَبقى مِن أيامِكَ المَعدودةِ بالصِّيام.</b>\n"
    "━━━━━━━━━━━━━━━━\n"
    "<b>قال الله تعالى في الحديث القدسي:</b>\n"
    "<i>«كلُّ عملِ ابنِ آدمَ له إلا الصومَ، فإنه لي وأنا أجزي به».</i>\n\n"
    "<b>قال رسول الله صلى الله عليه وسلم:</b>\n"
    "<i>«مَن صام يومًا في سبيلِ الله, باعدَ اللهُ وجهَهُ عن النارِ سبعينَ خريفًا»</i>\n"
    "━━━━━━━━━━━━━━━━\n"
    "<b>فمَن أرَادَ أن يَفُوز بالدخولِ من بابِ الريَّان فليُبادِر بالصيام 🩶</b>\n"
    "<blockquote><b>إن لم تصم فذكّر غيرك فـ هنيئاً لمن صام واحتسب، وكتب الله لنا ولكم الأجر.</b></blockquote>"
)

def task_remind_fasting_monday():
    print("🌙 تذكير صيام الاثنين")
    msg = FASTING_TEMPLATE.format(day="الإثنين")
    send_text(msg)

def task_remind_fasting_thursday():
    print("🌙 تذكير صيام الخميس")
    msg = FASTING_TEMPLATE.format(day="الخميس")
    send_text(msg)

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
    try:
        TASKS[task]()
        print("✅ انتهت المهمة")
    except Exception as e:
        print(f"❌ خطأ في المهمة '{task}': {e}")
        send_error_alert(task, e)
        sys.exit(1)
