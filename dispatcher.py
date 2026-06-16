"""
AbdulGhanyBot — Dispatcher
يُشغَّل مرة واحدة يومياً ويجدول كل مهام الغد في تيليجرام مباشرةً.
"""

import os
import json
import sys
import random
import requests
import traceback
import html
from datetime import datetime, timedelta
import pytz

# ─────────────────────────────────────────────
#  الإعدادات
# ─────────────────────────────────────────────
BOT_TOKEN        = os.environ["BOT_TOKEN"]
CHAT_ID          = os.environ.get("CHAT_ID",  "-1001949919685")
TOPIC_ID         = os.environ.get("TOPIC_ID", "25894")
RELEASE_BASE     = os.environ.get("RELEASE_BASE", "")
RELEASE_BASE_MP3 = os.environ.get("RELEASE_BASE_MP3", "")
RELEASE_KAHF     = os.environ.get("RELEASE_KAHF", "")
CAIRO_TZ         = pytz.timezone("Africa/Cairo")
TOTAL_FILES      = 604
STATE_FILE       = "state.json"
ZIKR_FILE        = "zikr.json"
BASE_URL         = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ─────────────────────────────────────────────
#  Telegram — الإرسال الفوري والمجدوَل
# ─────────────────────────────────────────────
def _base_params(schedule_date: int = None) -> dict:
    p = {"chat_id": CHAT_ID, "message_thread_id": TOPIC_ID}
    if schedule_date:
        p["schedule_date"] = schedule_date
    return p

def send_text(text: str, schedule_date: int = None):
    r = requests.post(
        f"{BASE_URL}/sendMessage",
        data={**_base_params(schedule_date), "text": text, "parse_mode": "HTML"},
        timeout=10,
    )
    _log_response("📨", r)

def send_document_bytes(data: bytes, filename: str, caption: str = "", schedule_date: int = None):
    files = {"document": (filename, data, "application/pdf")}
    r = requests.post(
        f"{BASE_URL}/sendDocument",
        data={**_base_params(schedule_date), "caption": caption, "parse_mode": "HTML"},
        files=files,
        timeout=120,
    )
    _log_response("📄", r)

def send_audio_bytes(data: bytes, filename: str, caption: str = "", schedule_date: int = None):
    files = {"audio": (filename, data, "audio/mpeg")}
    r = requests.post(
        f"{BASE_URL}/sendAudio",
        data={**_base_params(schedule_date), "caption": caption, "parse_mode": "HTML",
              "title": filename.replace(".mp3", ""), "performer": "ختمة القرآن"},
        files=files,
        timeout=120,
    )
    _log_response("🎵", r)

def _log_response(icon: str, r: requests.Response):
    desc = r.json().get("description", "OK") if not r.ok else "OK"
    print(f"{icon} {r.status_code} | {desc}")
    if not r.ok:
        raise RuntimeError(f"Telegram API error {r.status_code}: {desc}")

def send_error_alert(task_name: str, error: Exception):
    raw_tb = traceback.format_exc()
    if not raw_tb or raw_tb.strip() == "NoneType: None":
        raw_tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    tb_safe          = html.escape(raw_tb[-800:])
    task_safe        = html.escape(str(task_name)[:100])
    error_type_safe  = html.escape(type(error).__name__)
    error_details_safe = html.escape(str(error)[:400])
    msg = (
        f"<blockquote><b>⚠️ خطأ في مهمة:</b> <code>{task_safe}</code></blockquote>\n\n"
        f"<b>النوع:</b> <code>{error_type_safe}</code>\n"
        f"<b>التفاصيل:</b> <code>{error_details_safe}</code>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"<b>الـ Traceback:</b>\n<code>{tb_safe}</code>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"<blockquote>🔔 <b><a href='tg://user?id=1640238709'>د. إسلام</a> راجع الأمر.</b></blockquote>"
    )
    try:
        requests.post(
            f"{BASE_URL}/sendMessage",
            data={"chat_id": CHAT_ID, "message_thread_id": TOPIC_ID,
                  "text": msg, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        print(f"❌ فشل إرسال تنبيه الخطأ: {e}")

# ─────────────────────────────────────────────
#  Download
# ─────────────────────────────────────────────
def download(url: str) -> bytes:
    print(f"⬇️  {url}")
    headers = {"Accept": "application/octet-stream", "User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, allow_redirects=True, timeout=60)
    r.raise_for_status()
    size_kb = len(r.content) // 1024
    print(f"   ✅ {size_kb} KB")
    if size_kb > 50 * 1024:
        raise ValueError(f"الملف أكبر من 50 MB ({size_kb} KB) — تليجرام سيرفضه")
    return r.content

# ─────────────────────────────────────────────
#  Timestamp Helper
# ─────────────────────────────────────────────
def ts(tomorrow: datetime.date, hour: int, minute: int) -> int:
    """يُعيد Unix timestamp لوقت محدد غداً بتوقيت القاهرة."""
    dt = CAIRO_TZ.localize(datetime(tomorrow.year, tomorrow.month, tomorrow.day, hour, minute))
    return int(dt.timestamp())

# ─────────────────────────────────────────────
#  State — القرآن
# ─────────────────────────────────────────────
def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        state.setdefault("khatma_count", 1)
        state.setdefault("current_file", 1)
        return state
    return {"current_file": 1, "khatma_count": 1}

def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"💾 state.json → ملف {state['current_file']} | ختمة {state['khatma_count']}")

# ─────────────────────────────────────────────
#  State — الذكر
# ─────────────────────────────────────────────
def load_zikr_state() -> dict:
    if os.path.exists(ZIKR_FILE):
        with open(ZIKR_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_scheduled_day": "", "tomorrow_order": []}

def save_zikr_state(state: dict):
    with open(ZIKR_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"💾 zikr.json → آخر يوم مجدوَل: {state['last_scheduled_day']}")

# ─────────────────────────────────────────────
#  Progress bar + Motivational
# ─────────────────────────────────────────────
def progress_bar(current: int, total: int) -> str:
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
        msgs = ["🌿 <i>مع كل يوم، يزداد نصيبك من صحبة القرآن.</i>",
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
#  الأذكار
# ─────────────────────────────────────────────
AZKAAR = [
    ("💎", "سبحان الله وبحمده",
     "«من قال: سبحان الله وبحمده في يوم مائة مرة حُطَّت خطاياه وإن كانت مثل زبد البحر»"),
    ("💎", "سبحان الله وبحمده، سبحان الله العظيم",
     "«كلمتان خفيفتان على اللسان، ثقيلتان في الميزان، حبيبتان إلى الرحمن: سبحان الله وبحمده، سبحان الله العظيم»"),
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
     "«من صلى عليَّ صلاة صلى الله عليه بها عشرًا» (صحيح مسلم)"),
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

# ─────────────────────────────────────────────
#  جدولة مهام الغد
# ─────────────────────────────────────────────

def schedule_daily_files(tomorrow, state: dict):
    """يجدول الورد القرآني (PDF + MP3) للغد ويُحدّث state.json."""
    n      = state["current_file"]
    khatma = state["khatma_count"]
    num    = f"{n:03d}"
    pct    = round((n / TOTAL_FILES) * 100, 1)
    bar    = progress_bar(n, TOTAL_FILES)
    motiv  = motivational(pct)
    date_str = tomorrow.strftime("%d / %m / %Y")
    sched  = ts(tomorrow, 5, 30)  # 5:30 ص

    caption_pdf = (
        f"<blockquote><b>📖 الورد اليومي - الختمة الـ{khatma}</b></blockquote>\n"
        f"🗓 <i>{date_str}</i> • 📂 الورد الـ<b>{num}</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"<b>📊 تقدّمك:</b> {bar}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{motiv}\n"
        f"<blockquote><b>🤲 نسأل الله أن يجعله نورًا في قلوبنا، وبركةً في أيامنا.</b></blockquote>"
    )
    caption_mp3 = f"<blockquote><b>🎧 تلاوة الورد الـ{num}</b></blockquote>"

    print(f"📤 جدولة الملف {num} | الختمة {khatma} ({pct}%) → {date_str} 5:30ص")
    send_document_bytes(download(f"{RELEASE_BASE}/{num}.pdf"), f"{num}.pdf", caption_pdf, sched)
    send_audio_bytes(download(f"{RELEASE_BASE_MP3}/{num}.mp3"), f"{num}.mp3", caption_mp3, sched)

    # إذا كانت الختمة تكتمل غداً، نجدول رسالة التهنئة بعد الملفات مباشرةً
    if n == TOTAL_FILES:
        state["khatma_count"] += 1
        send_text(
            f"<blockquote><b>🎉 بفضل الله اكتملت الختمة الـ{khatma}</b></blockquote>\n"
            f"📖 <i>نسأل الله أن يجعل القرآن ربيع قلوبنا، ونور صدورنا، وأن يتقبله منا خالصًا لوجهه الكريم.</i>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🌱 <b>ومن أجمل ما في الطريق إلى الله أن الختمة لا تكون نهاية، بل بداية لختمة جديدة، "
            f"وغدًا بإذن الله نبدأ الختمة الـ {state['khatma_count']}، نسأل الله أن يبارك لنا فيها وأن يبلغنا تمامها.</b>\n"
            f"<blockquote><b>🤲 اللهم تقبّل منا إنك أنت السميع العليم، وتب علينا إنك أنت التواب الرحيم.</b></blockquote>",
            sched + 60,  # دقيقة بعد الورد
        )

    state["current_file"] = (n % TOTAL_FILES) + 1
    save_state(state)


def schedule_sabah(tomorrow):
    sched = ts(tomorrow, 6, 0)
    print(f"🌅 جدولة أذكار الصباح → 6:00ص")
    send_text(
        "<blockquote><b>أَصْبَحْنَا وَأَصْبَحَ الْمُلْكُ لِلَّهِ</b></blockquote>\n"
        "🤍 <i>ابدأ يومك بذكر الله</i>\n"
        "<blockquote><b>أذكار الصباح من أعظم ما يعين على طمأنينة القلب وحفظ العبد بإذن الله.</b></blockquote>",
        sched,
    )
    caption = (
        "<blockquote><b>أذكار الصباح</b></blockquote>\n"
        "🌅 <i>اقرأها بهدوء وتدبّر، واجعلها بدايةً ليومك مع الله.</i>"
    )
    with open("Zeikr/al-azkar.pdf", "rb") as f:
        send_document_bytes(f.read(), "al-azkar.pdf", caption, sched + 5)


def schedule_masa(tomorrow):
    sched = ts(tomorrow, 16, 30)
    print(f"🌆 جدولة أذكار المساء → 4:30م")
    send_text(
        "<blockquote><b>أَمْسَيْنَا وَأَمْسَى الْمُلْكُ لِلَّهِ</b></blockquote>\n"
        "🤍 <i>اختم نهارك بذكر الله</i>\n"
        "<blockquote><b>اجعل لنفسك وردًا ثابتًا من أذكار المساء، فهي من أعظم ما يملأ القلب طمأنينةً وسكينة.</b></blockquote>",
        sched,
    )
    caption = (
        "<blockquote><b>أذكار المساء</b></blockquote>\n"
        "🌆 <i>اختم بها يومك، واستودع نفسك وأهلك عند الله.</i>"
    )
    with open("Zeikr/al-azkar.pdf", "rb") as f:
        send_document_bytes(f.read(), "al-azkar.pdf", caption, sched + 5)


def schedule_remind_morning(tomorrow):
    sched = ts(tomorrow, 10, 0)
    print(f"☀️ جدولة تذكير الضحى → 10:00ص")
    send_text(
        "<blockquote><b>تذكير الضحى ☀️</b></blockquote>\n"
        "⏰ <b>النهار في أوله والفرص متاحة:</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        "📖 ورد القرآن — <i>هل أنجزت وِردك اليوم؟</i>\n"
        "🤲 أذكار الصباح — <i>هل حصّنت نفسك؟</i>\n"
        "📿 <i>دقائق مع الله تُبارك يومك كله</i>\n"
        "<blockquote><b><i>«اللهم أعنّا على ذكرك وشكرك وحسن عبادتك»</i></b></blockquote>",
        sched,
    )


def schedule_remind_midday(tomorrow):
    sched = ts(tomorrow, 14, 0)
    print(f"🌤 جدولة تذكير الظهر → 2:00م")
    send_text(
        "<blockquote><b>وقفة منتصف النهار 🌤</b></blockquote>\n"
        "⏰ <b>وسط مشاغل الدنيا — لا تنس نصيبك من الله 🤍</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        "📖 <i>لو ما قرأتش ورد القرآن — دلوقتي وقته</i>\n"
        "🤲 <i>فاتك شيء من وِردك؟ لا بأس، ابدأ الآن ولا تؤجل.</i>\n"
        "📿 <i>«من قال: سبحان الله وبحمده مائة مرة، حُطّت خطاياه وإن كانت مثل زبد البحر»</i>\n"
        "<blockquote><b><i>ورد القرآن لسه بينتظرك لو ما كملتش</i></b></blockquote>",
        sched,
    )


def schedule_remind_night(tomorrow):
    sched = ts(tomorrow, 21, 0)
    print(f"🌙 جدولة تذكير الليل → 9:00م")
    send_text(
        "<blockquote><b>محطة آخر النهار 🌙</b></blockquote>\n"
        "⏰ <b>قبل أن تنام، راجع يومك 🤍</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        "<i>📖 القرآن: هل كان لك وِرد اليوم؟</i>\n"
        "<i>🤲 الأذكار: هل حافظت على أذكار الصباح والمساء؟</i>\n"
        "<i>🧭 الذكر: هل ذكرت الله خلال يومك ولو قليلًا؟</i>\n"
        "━━━━━━━━━━━━━━━━\n"
        "<i>إن قصّرت يومًا، فلا تترك الذكر، وجدّد العهد من جديد 🤍</i>\n"
        "<blockquote><b><i>لا تنسَ أذكار النوم، اللهم تقبّل منا ومنكم</i></b></blockquote>",
        sched,
    )


def schedule_friday_salah(tomorrow):
    """يجدول الـ 4 رسائل على مدار يوم الجمعة."""
    slots = [
        (8,  0,  "fajr"),
        (10, 0,  "morning"),
        (12, 0,  "midday"),
        (16, 0,  "asr"),
    ]
    texts = {
        "fajr": (
            "<blockquote><b>فجر الجمعة المباركة 🌙</b></blockquote>\n"
            "<b>اللهم صلِّ وسلم وبارك على نبينا محمد 💛</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            "<i>«من صلى عليّ صلاةً واحدة صلى الله عليه بها عشرًا»</i>\n"
            "<i>أكثروا من الصلاة على النبي ﷺ في يوم الجمعة 🤍</i>"
        ),
        "morning": (
            "<blockquote><b>صباح الجمعة ☀️</b></blockquote>\n"
            "<b>لا تنسَ قراءة سورة الكهف 📖</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            "<i>اللهم صلِّ وسلم وبارك على نبينا محمد ﷺ</i>\n"
            "<i>كما صليت على إبراهيم وعلى آل إبراهيم إنك حميد مجيد 🤍</i>\n"
        ),
        "midday": (
            "<blockquote><b>ظهر الجمعة 🌤</b></blockquote>\n"
            "<b>لا تنسَ الدعاء، ففي الجمعة ساعةٌ لا يُرد فيها الدعاء 🤲</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            "<i>«من صلى عليّ صلاةً واحدة صلى الله عليه بها عشرًا»</i>\n"
            "<i>أكثر من الدعاء لك ولأحبابك وللمسلمين جميعًا 🤍</i>"
        ),
        "asr": (
            "<blockquote><b>عصر الجمعة 🌆</b></blockquote>\n"
            "<b>تقترب ساعات الجمعة من نهايتها… 🌿</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            "أكثروا من الصلاة على النبي ﷺ\n"
            "<i>«إن لله ملائكة سيّاحين في الأرض يُبلّغوني من أمتي السلام»</i>\n"
            "🌹 <i>صلاة واحدة — تبلغه ﷺ سلامك</i>\n"
            "🤍 <i>جمعة مباركة على الجميع</i>"
        ),
    }
    for hour, minute, slot in slots:
        sched = ts(tomorrow, hour, minute)
        print(f"💛 جدولة الصلاة على النبي [{slot}] → {hour}:{minute:02d}")
        send_text(texts[slot], sched)


def schedule_friday_kahf(tomorrow):
    sched = ts(tomorrow, 10, 30)
    print(f"📖 جدولة سورة الكهف → 10:30ص")
    send_text(
        "<blockquote><b>🕌 جمعة مباركة، لا تنسَ سورة الكهف</b></blockquote>\n"
        "<i>«مَنْ قَرَأَ سُورَةَ الْكَهْفِ فِي يَوْمِ الْجُمُعَةِ</i>\n"
        "<i>أَضَاءَ لَهُ مِنَ النُّورِ مَا بَيْنَ الْجُمُعَتَيْنِ»</i>\n"
        "<blockquote><b><i>أكثر من الصلاة على النبي ﷺ، وتحرَّ ساعة الإجابة واجعل لعبدالغني نصيبًا من دعائك 🩶  </i></b></blockquote>",
        sched,
    )
    send_document_bytes(
        download(f"{RELEASE_KAHF}/al-kahf.pdf"), "al-kahf.pdf",
        "<blockquote><b>📖 سورة الكهف</b></blockquote>",
        sched + 10,
    )
    send_audio_bytes(
        download(f"{RELEASE_KAHF}/al-kahf.mp3"), "al-kahf.mp3",
        "<blockquote><b>🎧 تلاوة سورة الكهف</b></blockquote>",
        sched + 20,
    )


def schedule_fasting_reminder(tomorrow, day_name: str):
    sched = ts(tomorrow, 20, 0)
    print(f"🌙 جدولة تذكير صيام {day_name} → 8:00م")
    msg = (
        f"<blockquote><b>تذكير صيامُ يومِ غدٍ {day_name} 🌙.</b></blockquote>\n"
        f"<b>إغتنِمْ ما تَبقى مِن أيامِكَ المَعدودةِ بالصِّيام.</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        "<b>قال الله تعالى في الحديث القدسي:</b>\n"
        "<i>«كلُّ عملِ ابنِ آدمَ له إلا الصومَ، فإنه لي وأنا أجزي به».</i>\n\n"
        "<b>قال رسول الله صلى الله عليه وسلم:</b>\n"
        "<i>«مَن صام يومًا في سبيلِ الله, باعدَ اللهُ وجهَهُ عن النارِ سبعينَ خريفًا»</i>\n"
        "━━━━━━━━━━━━━━━━\n"
        "<b>فمَن أرَادَ أن يَفُوز بالدخولِ من بابِ الريَّان فليُبادِر بالصيام 🩶</b>\n"
        "<blockquote><b>إن لم تصم فذكّر غيرك فـ هنيئاً لمن صام واحتسب، وكتب الله لنا ولكم الأجر.</b></blockquote>"
    )
    send_text(msg, sched)


def schedule_hourly_zikr(tomorrow, order: list):
    """يجدول الـ 14 ذكراً كل ساعة من 7ص لـ 11م."""
    # الساعات المستهدفة بتوقيت القاهرة
    hours = [7, 8, 9, 11, 12, 13, 15, 16, 17, 18, 19, 20, 22, 23]
    print(f"📿 جدولة {len(order)} أذكار لـ {len(hours)} ساعة")
    for i, zikr_idx in enumerate(order):
        hour = hours[i]
        _, zikr, hadith = AZKAAR[zikr_idx]
        msg = (
            f"<blockquote><b>{zikr}</b></blockquote>\n"
            f"<i><b>{hadith}</b></i>\n"
        )
        sched = ts(tomorrow, hour, 13)
        send_text(msg, sched)
        print(f"   📿 ذكر {i+1}/14 [{hour}:13] → index {zikr_idx}")


# ─────────────────────────────────────────────
#  الـ Dispatcher الرئيسي
# ─────────────────────────────────────────────
def run_dispatcher():
    now      = datetime.now(CAIRO_TZ)
    tomorrow = (now + timedelta(days=1)).date()
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")
    weekday  = tomorrow.weekday()  # 0=الاثنين … 6=الأحد، 4=الجمعة

    print(f"\n🗓 الـ Dispatcher يعمل الآن | اليوم: {now.strftime('%Y-%m-%d %H:%M')} | الغد: {tomorrow_str}")

    # ──── Idempotency Check (ذكر اليوم) ────
    zikr_state = load_zikr_state()
    if zikr_state.get("last_scheduled_day") == tomorrow_str:
        print(f"⚠️  الغد ({tomorrow_str}) مجدوَل مسبقاً — لا حاجة للتكرار. خروج.")
        return

    # ──── 1. الورد القرآني (كل يوم) ────
    quran_state = load_state()
    schedule_daily_files(tomorrow, quran_state)

    # ──── 2. أذكار الصباح والمساء (كل يوم) ────
    schedule_sabah(tomorrow)
    schedule_masa(tomorrow)

    # ──── 3. التذكيرات اليومية ────
    schedule_remind_morning(tomorrow)
    schedule_remind_midday(tomorrow)
    schedule_remind_night(tomorrow)

    # ──── 4. مهام الجمعة (weekday == 4) ────
    if weekday == 4:
        schedule_friday_salah(tomorrow)
        schedule_friday_kahf(tomorrow)

    # ──── 5. تذكير صيام الاثنين (يُرسَل مساء الأحد، weekday غد == 0) ────
    if weekday == 0:
        schedule_fasting_reminder(tomorrow, "الإثنين")

    # ──── 6. تذكير صيام الخميس (يُرسَل مساء الأربعاء، weekday غد == 3) ────
    if weekday == 3:
        schedule_fasting_reminder(tomorrow, "الخميس")

    # ──── 7. أذكار الساعة ────
    order = list(range(len(AZKAAR)))
    random.shuffle(order)
    schedule_hourly_zikr(tomorrow, order)

    # ──── حفظ الـ State (مرة واحدة فقط في النهاية) ────
    new_zikr_state = {
        "last_scheduled_day": tomorrow_str,
        "tomorrow_order": order,
    }
    save_zikr_state(new_zikr_state)

    print(f"\n✅ انتهى الـ Dispatcher — جُدولت مهام يوم {tomorrow_str} بنجاح 🎉")


# ─────────────────────────────────────────────
#  نقطة الدخول
# ─────────────────────────────────────────────
if __name__ == "__main__":
    try:
        run_dispatcher()
    except Exception as e:
        print(f"❌ خطأ في الـ Dispatcher: {e}")
        send_error_alert("dispatcher", e)
        sys.exit(1)
