"""
AbdulGhanyBot — يشتغل مرة واحدة عن طريق GitHub Actions
"""

import os
import json
import sys
import requests
from datetime import datetime
import pytz
import random

# ─────────────────────────────────────────────
#  الإعدادات
# ─────────────────────────────────────────────
BOT_TOKEN        = os.environ["BOT_TOKEN"]
CHAT_ID          = os.environ.get("CHAT_ID", "-1003844022713")
TOPIC_ID         = os.environ.get("TOPIC_ID", "33")
RELEASE_BASE     = os.environ.get("RELEASE_BASE", "")
RELEASE_BASE_MP3 = os.environ.get("RELEASE_BASE_MP3", "")
RELEASE_KAHF     = os.environ.get("RELEASE_KAHF", "")
CAIRO_TZ         = pytz.timezone("Africa/Cairo")
TOTAL_FILES      = 604
STATE_FILE       = "state.json"
BASE_URL         = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ─────────────────────────────────────────────
#  State
# ─────────────────────────────────────────────
def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        state.setdefault("khatma_count", 1)
        state.setdefault("zikr_index", 0) 
        return state
    return {"current_file": 1, "khatma_count": 1, "zikr_index": 0}

def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"💾 حُفظ التقدم: ملف {state['current_file']} | ختمة {state['khatma_count']}")

# ─────────────────────────────────────────────
#  Telegram helpers
# ─────────────────────────────────────────────
def _base_params() -> dict:
    return {"chat_id": CHAT_ID, "message_thread_id": TOPIC_ID}

def send_text(text: str):
    r = requests.post(
        f"{BASE_URL}/sendMessage",
        data={**_base_params(), "text": text, "parse_mode": "HTML"},
    )
    print(f"📨 نص: {r.status_code}")

def send_error_alert(task_name: str, error: Exception):
    """يُرسل تنبيه خطأ في الشات مع mention للمسؤول"""
    import traceback
    tb = traceback.format_exc()[-800:]  # آخر 800 حرف فقط عشان ما تتجاوزش الحد
    msg = (
        f"⚠️ <b>خطأ في مهمة:</b> <code>{task_name}</code>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"<b>النوع:</b> <code>{type(error).__name__}</code>\n"
        f"<b>التفاصيل:</b> <code>{str(error)[:300]}</code>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"<pre>{tb}</pre>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🔔 <a href='https://t.me/DrIslambinalkhattab_1'>@DrIslambinalkhattab_1</a> راجع الأمر."
    )
    try:
        requests.post(
            f"{BASE_URL}/sendMessage",
            data={**_base_params(), "text": msg, "parse_mode": "HTML"},
        )
    except Exception as e:
        print(f"❌ فشل إرسال تنبيه الخطأ: {e}")

def send_document_bytes(data: bytes, filename: str, caption: str = ""):
    files = {"document": (filename, data, "application/pdf")}
    r = requests.post(
        f"{BASE_URL}/sendDocument",
        data={**_base_params(), "caption": caption, "parse_mode": "HTML"},
        files=files,
    )
    print(f"📄 PDF: {r.status_code} | {r.json().get('description','OK')}")

def send_audio_bytes(data: bytes, filename: str, caption: str = ""):
    files = {"audio": (filename, data, "audio/mpeg")}
    r = requests.post(
        f"{BASE_URL}/sendAudio",
        data={**_base_params(), "caption": caption, "parse_mode": "HTML",
              "title": filename.replace(".mp3",""), "performer": "ختمة القرآن"},
        files=files,
    )
    print(f"🎵 Audio: {r.status_code} | {r.json().get('description','OK')}")

def download(url: str) -> bytes:
    print(f"⬇️  جاري التحميل: {url}")
    headers = {"Accept": "application/octet-stream", "User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, allow_redirects=True)
    print(f"   {'✅' if r.status_code==200 else '❌'} {len(r.content)//1024} KB | {r.status_code}")
    return r.content

# ─────────────────────────────────────────────
#  Progress bar
# ─────────────────────────────────────────────
def progress_bar(current: int, total: int, khatma: int = 1) -> str:
    length    = 8
    filled    = int((current / total) * length)
    pct       = round((current / total) * 100, 1)
    bar       = "🟩" * filled + "⬜" * (length - filled)
    remaining = total - current
    return (
        f"📂 <b>{current}</b> من <b>{total}</b> • ⏳ باقي <b>{remaining}</b>\n"
        f"{bar}  <b>{pct}%</b>"
    )

def motivational(pct: float) -> str:
    if pct < 10:
        msgs = ["🌱 <i>خطوة اليوم هي لبنة في ختمة كاملة بإذن الله.</i>",
                "🌱 <i>خير البدايات ما كان مع كتاب الله.</i>"]
    elif pct < 25:
        msgs = [
            "🌿 <i>مع كل يوم، يزداد نصيبك من صحبة القرآن.</i>",
            "🌿 <i>«خير العمل ما داوم عليه صاحبه وإن قلّ»</i>"]
    elif pct < 50:
        msgs = ["🌸 <i>كل صفحة تُقرأ تقرّبك من تمام الختمة.</i>",
                "🌸 <i>الاستمرار مع القرآن من أعظم ما يعين على الثبات.</i>"]
    elif pct < 75:
        msgs = ["🌺 <i>أكثر من النصف — وما أجمل أن يُتم المؤمن ما بدأ</i>",
                "🌺 <i>ما بقي أقل مما مضى، فاستعن بالله وأكمل.</i>"]
    elif pct < 90:
        msgs = ["🌟 <i>قاربنا الختم — اللهم بلّغنا وتقبّل منا</i>",
                "🌟 <i>الخواتيم بيد الله — اللهم اجعل خواتيمنا خيراً</i>"]
    else:
        msgs = ["✨ <i>على وشك الختمة — اللهم تقبّل منا ومنكم</i>",
                "✨ <i>بقي القليل — نسأل الله أن يتمها علينا بالقبول.</i>"]
    return random.choice(msgs)


# ─────────────────────────────────────────────
#  المهمة الأولى: PDF + MP3
# ─────────────────────────────────────────────
def task_daily_files():
    state  = load_state()
    n      = state["current_file"]
    khatma = state["khatma_count"]

    # 1. تحضير البيانات والنصوص بناءً على الحالة الحالية
    num      = f"{n:03d}"
    pct      = round((n / TOTAL_FILES) * 100, 1)
    bar      = progress_bar(n, TOTAL_FILES, khatma)
    motiv    = motivational(pct)
    date_str = datetime.now(CAIRO_TZ).strftime("%d / %m / %Y")

    caption_pdf = (
        f"<blockquote><b>📖 الورد اليومي - الختمة الـ{khatma}</b></blockquote>\n"
        f"🗓 <i>{date_str}</i> • 📂 الورد الـ<b>{num}</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"<b>📊 تقدّمك:</b> {bar}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{motiv}\n"
        f"<blockquote><b>🤲 نسأل الله أن يجعله نورًا في قلوبنا، وبركةً في أيامنا.</b></blockquote>"
    )
    caption_mp3 = (
        f"<blockquote><b>🎧تلاوة الورد الـ {num}</b></blockquote>\n"
    )

    # 2. إرسال الملفات أولاً
    print(f"📤 إرسال الملف رقم {num} | الختمة {khatma} ({pct}%)")
    send_document_bytes(download(f"{RELEASE_BASE}/{num}.pdf"), f"{num}.pdf", caption_pdf)
    send_audio_bytes(download(f"{RELEASE_BASE_MP3}/{num}.mp3"), f"{num}.mp3", caption_mp3)

    # 3. التحقق من اكتمال الختمة وإرسال التهنئة (بعد إرسال الملفات)
    if n == TOTAL_FILES:
        state["khatma_count"] += 1
        send_text(
            f"<blockquote><b>🎉 بفضل الله اكتملت الختمة الـ{khatma}</b></blockquote>\n"
            f"📖 <i>نسأل الله أن يجعل القرآن ربيع قلوبنا، ونور صدورنا، وأن يتقبله منا خالصًا لوجهه الكريم.</i>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🌱 <b>ومن أجمل ما في الطريق إلى الله أن الختمة لا تكون نهاية، بل بداية لختمة جديدة، وغدًا بإذن الله نبدأ الختمة الـ {state['khatma_count']}، نسأل الله أن يبارك لنا فيها وأن يبلغنا تمامها.</b>\n"
            f"<blockquote><b>🤲 اللهم تقبّل منا إنك أنت السميع العليم، وتب علينا إنك أنت التواب الرحيم.</b></blockquote>"
        )

    # 4. تحديث حالة الملفات للمرة القادمة وحفظ الـ state
    state["current_file"] = (n % TOTAL_FILES) + 1
    save_state(state)

# ─────────────────────────────────────────────
#  أذكار الصباح
# ─────────────────────────────────────────────
def task_sabah():
    print("🌅 إرسال أذكار الصباح")
    send_text(
        "<blockquote><b>أَصْبَحْنَا وَأَصْبَحَ الْمُلْكُ لِلَّهِ</b></blockquote>\n"
        "🤍 <i>ابدأ يومك بذكر الله</i>\n"
        "<blockquote><b>أذكار الصباح من أعظم ما يعين على طمأنينة القلب وحفظ العبد بإذن الله.</b></blockquote>"
    )
    caption = (
        "<blockquote><b>أذكار الصباح</b></blockquote>\n"
        "🌅 <i>اقرأها بهدوء وتدبّر، واجعلها بدايةً ليومك مع الله.</i>"
    )
    with open("Zeikr/al-azkar.pdf", "rb") as f:
        send_document_bytes(f.read(), "al-azkar.pdf", caption)

# ─────────────────────────────────────────────
#  أذكار المساء
# ─────────────────────────────────────────────
def task_masa():
    print("🌆 إرسال أذكار المساء")
    send_text(
        "<blockquote><b>أَمْسَيْنَا وَأَمْسَى الْمُلْكُ لِلَّهِ</b></blockquote>\n"
        "🤍 <i>اختم نهارك بذكر الله</i>\n"
        "<blockquote><b>اجعل لنفسك وردًا ثابتًا من أذكار المساء، فهي من أعظم ما يملأ القلب طمأنينةً وسكينة.</b></blockquote>"
    )
    caption = (
        "<blockquote><b>أذكار المساء</b></blockquote>\n"
        "🌆 <i>اختم بها يومك، واستودع نفسك وأهلك عند الله.</i>"
    )
    with open("Zeikr/al-azkar.pdf", "rb") as f:
        send_document_bytes(f.read(), "al-azkar.pdf", caption)

# ─────────────────────────────────────────────
#  سورة الكهف
# ─────────────────────────────────────────────
def task_friday_kahf():
    print("📖 إرسال سورة الكهف")
    send_text(
        "<blockquote><b>🕌 جمعة مباركة، لا تنسَ سورة الكهف</b></blockquote>\n"
        "<i>«مَنْ قَرَأَ سُورَةَ الْكَهْفِ فِي يَوْمِ الْجُمُعَةِ</i>\n"
        "<i>أَضَاءَ لَهُ مِنَ النُّورِ مَا بَيْنَ الْجُمُعَتَيْنِ»</i>\n"
        "<blockquote><b><i>أكثر من الصلاة على النبي ﷺ، وتحرَّ ساعة الإجابة واجعل لعبدالغني نصيبًا من دعائك 🩶  </i></b></blockquote>"
    )
    send_document_bytes(download(f"{RELEASE_KAHF}/al-kahf.pdf"), "al-kahf.pdf",
        "<blockquote><b>📖 سورة الكهف</b></blockquote>")
    send_audio_bytes(download(f"{RELEASE_KAHF}/al-kahf.mp3"), "al-kahf.mp3",
        "<blockquote><b>🎧 تلاوة سورة الكهف</b></blockquote>")

# ─────────────────────────────────────────────
#  التذكيرات
# ─────────────────────────────────────────────
def task_remind_morning():
    msgs = [
        ("<blockquote><b>تذكير الضحى ☀️</b></blockquote>\n"
         "⏰ <b>النهار في أوله والفرص متاحة:</b>\n"
         "━━━━━━━━━━━━━━━━\n"
         "📖 ورد القرآن — <i>هل أنجزت وِردك اليوم؟</i>\n"
         "🤲 أذكار الصباح — <i>هل حصّنت نفسك؟</i>\n"
         "📿 <i>دقائق مع الله تُبارك يومك كله</i>\n"
         "<blockquote><b><i>«اللهم أعنّا على ذكرك وشكرك وحسن عبادتك»</i></b></blockquote>"),
    ]
    send_text(random.choice(msgs))

def task_remind_midday():
    msgs = [
        ("<blockquote><b>وقفة منتصف النهار 🌤</b></blockquote>\n"
         "⏰ <b>وسط مشاغل الدنيا — لا تنس نصيبك من الله 🤍</b>\n"
         "━━━━━━━━━━━━━━━━\n"
         "📖 <i>لو ما قرأتش ورد القرآن — دلوقتي وقته</i>\n"
         "🤲 <i>فاتك شيء من وِردك؟ لا بأس، ابدأ الآن ولا تؤجل.</i>\n"
         "📿 <i>«من قال: سبحان الله وبحمده مائة مرة، حُطّت خطاياه وإن كانت مثل زبد البحر»</i>\n"
         "<blockquote><b><i>ورد القرآن لسه بينتظرك لو ما كملتش</i></b></blockquote>"),
    ]
    send_text(random.choice(msgs))

def task_remind_night():
    msgs = [
        ("<blockquote><b>محطة آخر النهار 🌙</b></blockquote>\n"
         "⏰ <b>قبل أن تنام، راجع يومك 🤍</b>\n"
         "━━━━━━━━━━━━━━━━\n"
         "<i>📖 القرآن: هل كان لك وِرد اليوم؟</i>\n"
         "<i>🤲 الأذكار: هل حافظت على أذكار الصباح والمساء؟</i>\n"
         "<i>🧭 الذكر: هل ذكرت الله خلال يومك ولو قليلًا؟</i>\n"
         "━━━━━━━━━━━━━━━━\n"
         "<i>إن قصّرت يومًا، فلا تترك الذكر، وجدّد العهد من جديد 🤍</i>\n"
         "<blockquote><b><i>لا تنسَ أذكار النوم، اللهم تقبّل منا ومنكم</i></b></blockquote>"),
    ]
    send_text(random.choice(msgs))

# ─────────────────────────────────────────────
#  الصلاة على النبي ﷺ يوم الجمعة
# ─────────────────────────────────────────────
def task_friday_salah(slot: str = ""):
    slots = {
        "fajr": ("<blockquote><b>فجر الجمعة المباركة 🌙</b></blockquote>\n"
                 "<b>اللهم صلِّ وسلم وبارك على نبينا محمد 💛</b>\n"
                 "━━━━━━━━━━━━━━━━\n"
                 "<i>«من صلى عليّ صلاةً واحدة صلى الله عليه بها عشرًا»</i>\n"
                 "<i>أكثروا من الصلاة على النبي ﷺ في يوم الجمعة 🤍</i>"),
        "morning": ("<blockquote><b>صباح الجمعة ☀️</b></blockquote>\n"
                    "<b>لا تنسَ قراءة سورة الكهف 📖</b>\n"
                    "━━━━━━━━━━━━━━━━\n"
                    "<i>اللهم صلِّ وسلم وبارك على نبينا محمد ﷺ</i>\n"
                    "<i>كما صليت على إبراهيم وعلى آل إبراهيم إنك حميد مجيد 🤍</i>\n"),
        "midday": ("🌤 <b>ظهر الجمعة</b>\n"
                   "<b>لا تنسَ الدعاء، ففي الجمعة ساعةٌ لا يُرد فيها الدعاء 🤲</b>\n"
                   "━━━━━━━━━━━━━━━━\n"
                   "<i>«من صلى عليّ صلاةً واحدة صلى الله عليه بها عشرًا»</i>\n"
                   "<i>أكثر من الدعاء لك ولأحبابك وللمسلمين جميعًا 🤍</i>"),
        "asr": ("🌆 <b>عصر الجمعة</b>\n"
                "<b>تقترب ساعات الجمعة من نهايتها… 🌿</b>\n"
                "━━━━━━━━━━━━━━━━\n"
                "أكثروا من الصلاة على النبي ﷺ\n"
                "<i>«إن لله ملائكة سيّاحين في الأرض يُبلّغوني من أمتي السلام»</i>\n"
                "🌹 <i>صلاة واحدة — تبلغه ﷺ سلامك</i>\n"
                "🤍 <i>جمعة مباركة على الجميع</i>"),
    }
    # fallback لو اتشغل يدوياً بدون slot
    if slot not in slots:
        hour = datetime.now(CAIRO_TZ).hour
        slot = "fajr" if hour < 7 else "morning" if hour < 12 else "midday" if hour < 15 else "asr"
    send_text(slots[slot])

# ─────────────────────────────────────────────
#  ذكر الساعة
# ─────────────────────────────────────────────
AZKAAR = [
    ("💎", "سبحان الله وبحمده",
     "«من قال: سبحان الله وبحمده في يوم مائة مرة حُطَّت خطاياه وإن كانت مثل زبد البحر»"),

    ("💎", "سبحان الله وبحمده، سبحان الله العظيم",
     "«كلمتان خفيفتان على اللسان، ثقيلتان في الميزان، حبيبتان إلى الرحمن: سبحان الله وبحمده، سبحان الله العظيم"),

    ("💎", "سبحان الله والحمد لله ولا إله إلا الله والله أكبر",
     "«لأن أقول: سبحان الله والحمد لله ولا إله إلا الله والله أكبر أحب إلي مما طلعت عليه الشمس» (صحيح مسلم)"),

    ("💎", "سبحان الله وبحمده عدد خلقه ورضا نفسه وزنة عرشه",
     "ذكر عظيم علّمه النبي ﷺ لأم المؤمنين جويرية رضي الله عنها"),

    ("💎", "لا إله إلا أنت سبحانك إني كنت من الظالمين",
     "دعوة ذي النون، قال ﷺ: «ما دعا بها مسلم في شيء إلا استجاب الله له»"),

    ("🌿", "أستغفر الله",
     "كان النبي ﷺ يستغفر الله في اليوم أكثر من سبعين مرة (رواه البخاري)"),

    ("🌿", "أستغفر الله الذي لا إله إلا هو الحي القيوم وأتوب إليه",
     "صيغة استغفار ثابتة ومشهورة عن النبي ﷺ"),

    ("🌹", "اللهم صل وسلم على نبينا محمد ﷺ",
     "«من صلى عليَّ صلاة صلى الله عليه بها عشرًا» (صحيح مسلم)"),

    ("🤲", "اللهم أعنّي على ذكرك وشكرك وحسن عبادتك",
     "دعاء جامع أوصى به النبي صلى الله عليه وسلم"),

    ("🤲", "يا حي يا قيوم برحمتك أستغيث أصلح لي شأني كله",
     "دعاء عظيم في الاستعانة بالله وتفويض الأمر إليه"),

    ("🤲", "ربنا لا تزغ قلوبنا بعد إذ هديتنا وهب لنا من لدنك رحمة",
     "دعاء قرآني من سورة آل عمران"),

    ("🤲", "رب اشرح لي صدري ويسر لي أمري",
     "دعاء موسى عليه السلام (سورة طه)"),

    ("⭐", "حسبي الله لا إله إلا هو عليه توكلت",
     "ذكر عظيم في التوكل على الله (ورد في القرآن)"),

    ("⭐", "لا إله إلا الله وحده لا شريك له له الملك وله الحمد وهو على كل شيء قدير",
     "من أعظم الأذكار، وله فضل كبير في الأحاديث الصحيحة"),
]

def task_hourly_zikr():
    state = load_state()
    idx   = state["zikr_index"]

    icon, zikr, hadith = AZKAAR[idx]
    msg = (
        f"<blockquote><b>{zikr}</b></blockquote>\n"
        f"<i><b>{hadith}</b></i>\n"
    )
    print(f"📿 إرسال الذكر رقم {idx + 1} من {len(AZKAAR)}")
    send_text(msg)

    state["zikr_index"] = (idx + 1) % len(AZKAAR)
    save_state(state)

# ─────────────────────────────────────────────
#  نقطة الدخول
# ─────────────────────────────────────────────
TASKS = {
    "daily_files"          : task_daily_files,
    "sabah"                : task_sabah,
    "masa"                 : task_masa,
    "kahf"                 : task_friday_kahf,
    "remind_morning"       : task_remind_morning,
    "remind_midday"        : task_remind_midday,
    "remind_night"         : task_remind_night,
    "friday_salah"         : task_friday_salah,
    "friday_salah_fajr"    : lambda: task_friday_salah("fajr"),
    "friday_salah_morning" : lambda: task_friday_salah("morning"),
    "friday_salah_midday"  : lambda: task_friday_salah("midday"),
    "friday_salah_asr"     : lambda: task_friday_salah("asr"),
    "hourly_zikr"          : task_hourly_zikr,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in TASKS:
        print(f"الاستخدام: python bot.py <{'|'.join(TASKS)}>")
        sys.exit(1)
    task_name = sys.argv[1]
    print(f"▶️  تشغيل المهمة: {task_name}")
    try:
        TASKS[task_name]()
        print("✅ انتهت المهمة بنجاح")
    except Exception as e:
        print(f"❌ خطأ في المهمة '{task_name}': {e}")
        send_error_alert(task_name, e)
        sys.exit(1)
