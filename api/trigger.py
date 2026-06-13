"""
AbdulGhanyBot — Serverless API for Vercel
POST /api/trigger  →  {"task": "<task_name>"}
"""

import os
import json
import html
import random
import traceback
from datetime import datetime

import pytz
import requests
import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

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
BASE_URL         = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ─────────────────────────────────────────────
#  Redis State (Upstash)
# ─────────────────────────────────────────────
STATE_KEY = "bot_state"
DEFAULT_STATE = {"current_file": 1, "khatma_count": 1, "zikr_index": 0}

def _redis_client():
    return redis.from_url(
        os.environ["REDIS_URL"],
        decode_responses=True,
        socket_connect_timeout=5,
    )

def load_state() -> dict:
    try:
        r = _redis_client()
        raw = r.get(STATE_KEY)
        if raw:
            state = json.loads(raw)
            state.setdefault("current_file", 1)
            state.setdefault("khatma_count", 1)
            state.setdefault("zikr_index", 0)
            return state
    except Exception as e:
        print(f"⚠️ Redis load error: {e}")
    return dict(DEFAULT_STATE)

def save_state(state: dict):
    try:
        r = _redis_client()
        r.set(STATE_KEY, json.dumps(state, ensure_ascii=False))
        print(f"💾 حُفظ التقدم: ملف {state['current_file']} | ختمة {state['khatma_count']}")
    except Exception as e:
        print(f"⚠️ Redis save error: {e}")

# ─────────────────────────────────────────────
#  Telegram helpers
# ─────────────────────────────────────────────
def _base_params() -> dict:
    return {"chat_id": CHAT_ID, "message_thread_id": TOPIC_ID}

def send_text(text: str):
    r = requests.post(
        f"{BASE_URL}/sendMessage",
        data={**_base_params(), "text": text, "parse_mode": "HTML"},
        timeout=10,
    )
    print(f"📨 {r.status_code}")

def send_error_alert(task_name: str, error: Exception):
    raw_tb = traceback.format_exc()
    if not raw_tb or raw_tb.strip() == "NoneType: None":
        raw_tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))

    tb_safe          = html.escape(raw_tb[-800:])
    task_safe        = html.escape(str(task_name)[:100])
    error_type_safe  = html.escape(type(error).__name__)
    error_details_safe = html.escape(str(error)[:400])

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
            timeout=10,
        )
        if not response.ok:
            print(f"❌ تليجرام رفض إرسال التنبيه: {response.text}")
    except Exception as e:
        print(f"❌ فشل اتصال إرسال تنبيه الخطأ: {e}")

def send_document_bytes(data: bytes, filename: str, caption: str = ""):
    files = {"document": (filename, data, "application/pdf")}
    r = requests.post(
        f"{BASE_URL}/sendDocument",
        data={**_base_params(), "caption": caption, "parse_mode": "HTML"},
        files=files,
    )
    print(f"📄 PDF: {r.status_code} | {r.json().get('description', 'OK')}")

def send_audio_bytes(data: bytes, filename: str, caption: str = ""):
    files = {"audio": (filename, data, "audio/mpeg")}
    r = requests.post(
        f"{BASE_URL}/sendAudio",
        data={
            **_base_params(),
            "caption": caption,
            "parse_mode": "HTML",
            "title": filename.replace(".mp3", ""),
            "performer": "ختمة القرآن",
        },
        files=files,
    )
    print(f"🎵 Audio: {r.status_code} | {r.json().get('description', 'OK')}")

def download(url: str) -> bytes:
    print(f"⬇️  جاري التحميل: {url}")
    headers = {"Accept": "application/octet-stream", "User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, allow_redirects=True, timeout=60)
    r.raise_for_status()
    size_kb = len(r.content) // 1024
    print(f"   ✅ {size_kb} KB | {r.status_code}")
    if size_kb > 50 * 1024:
        raise ValueError(f"الملف أكبر من 50 MB ({size_kb} KB) — تليجرام سيرفضه")
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
        msgs = [
            "🌱 <i>خطوة اليوم هي لبنة في ختمة كاملة بإذن الله.</i>",
            "🌱 <i>خير البدايات ما كان مع كتاب الله.</i>",
        ]
    elif pct < 25:
        msgs = [
            "🌿 <i>مع كل يوم، يزداد نصيبك من صحبة القرآن.</i>",
            "🌿 <i>«خير العمل ما داوم عليه صاحبه وإن قلّ»</i>",
        ]
    elif pct < 50:
        msgs = [
            "🌸 <i>كل صفحة تُقرأ تقرّبك من تمام الختمة.</i>",
            "🌸 <i>الاستمرار مع القرآن من أعظم ما يعين على الثبات.</i>",
        ]
    elif pct < 75:
        msgs = [
            "🌺 <i>أكثر من النصف — وما أجمل أن يُتم المؤمن ما بدأ</i>",
            "🌺 <i>ما بقي أقل مما مضى، فاستعن بالله وأكمل.</i>",
        ]
    elif pct < 90:
        msgs = [
            "🌟 <i>قاربنا الختم — اللهم بلّغنا وتقبّل منا</i>",
            "🌟 <i>الخواتيم بيد الله — اللهم اجعل خواتيمنا خيراً</i>",
        ]
    else:
        msgs = [
            "✨ <i>على وشك الختمة — اللهم تقبّل منا ومنكم</i>",
            "✨ <i>بقي القليل — نسأل الله أن يتمها علينا بالقبول.</i>",
        ]
    return random.choice(msgs)

# ─────────────────────────────────────────────
#  المهام
# ─────────────────────────────────────────────

# — PDF + MP3 —
def task_daily_files():
    state  = load_state()
    n      = state["current_file"]
    khatma = state["khatma_count"]

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
        f"<blockquote><b>🎧 تلاوة الورد الـ{num}</b></blockquote>"
    )

    print(f"📤 إرسال الملف رقم {num} | الختمة {khatma} ({pct}%)")
    send_document_bytes(download(f"{RELEASE_BASE}/{num}.pdf"), f"{num}.pdf", caption_pdf)
    send_audio_bytes(download(f"{RELEASE_BASE_MP3}/{num}.mp3"), f"{num}.mp3", caption_mp3)

    if n == TOTAL_FILES:
        state["khatma_count"] += 1
        send_text(
            f"<blockquote><b>🎉 بفضل الله اكتملت الختمة الـ{khatma}</b></blockquote>\n"
            f"📖 <i>نسأل الله أن يجعل القرآن ربيع قلوبنا، ونور صدورنا، وأن يتقبله منا خالصًا لوجهه الكريم.</i>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🌱 <b>ومن أجمل ما في الطريق إلى الله أن الختمة لا تكون نهاية، بل بداية لختمة جديدة، وغدًا بإذن الله نبدأ الختمة الـ {state['khatma_count']}، نسأل الله أن يبارك لنا فيها وأن يبلغنا تمامها.</b>\n"
            f"<blockquote><b>🤲 اللهم تقبّل منا إنك أنت السميع العليم، وتب علينا إنك أنت التواب الرحيم.</b></blockquote>"
        )

    state["current_file"] = (n % TOTAL_FILES) + 1
    save_state(state)


# — أذكار الصباح —
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


# — أذكار المساء —
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


# — سورة الكهف —
def task_friday_kahf():
    print("📖 إرسال سورة الكهف")
    send_text(
        "<blockquote><b>🕌 جمعة مباركة، لا تنسَ سورة الكهف</b></blockquote>\n"
        "<i>«مَنْ قَرَأَ سُورَةَ الْكَهْفِ فِي يَوْمِ الْجُمُعَةِ</i>\n"
        "<i>أَضَاءَ لَهُ مِنَ النُّورِ مَا بَيْنَ الْجُمُعَتَيْنِ»</i>\n"
        "<blockquote><b><i>أكثر من الصلاة على النبي ﷺ، وتحرَّ ساعة الإجابة واجعل لعبدالغني نصيبًا من دعائك 🩶  </i></b></blockquote>"
    )
    send_document_bytes(
        download(f"{RELEASE_KAHF}/al-kahf.pdf"),
        "al-kahf.pdf",
        "<blockquote><b>📖 سورة الكهف</b></blockquote>",
    )
    send_audio_bytes(
        download(f"{RELEASE_KAHF}/al-kahf.mp3"),
        "al-kahf.mp3",
        "<blockquote><b>🎧 تلاوة سورة الكهف</b></blockquote>",
    )


# — التذكيرات —
def task_remind_morning():
    msgs = [
        (
            "<blockquote><b>تذكير الضحى ☀️</b></blockquote>\n"
            "⏰ <b>النهار في أوله والفرص متاحة:</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            "📖 ورد القرآن — <i>هل أنجزت وِردك اليوم؟</i>\n"
            "🤲 أذكار الصباح — <i>هل حصّنت نفسك؟</i>\n"
            "📿 <i>دقائق مع الله تُبارك يومك كله</i>\n"
            "<blockquote><b><i>«اللهم أعنّا على ذكرك وشكرك وحسن عبادتك»</i></b></blockquote>"
        ),
    ]
    send_text(random.choice(msgs))


def task_remind_midday():
    msgs = [
        (
            "<blockquote><b>وقفة منتصف النهار 🌤</b></blockquote>\n"
            "⏰ <b>وسط مشاغل الدنيا — لا تنس نصيبك من الله 🤍</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            "📖 <i>لو ما قرأتش ورد القرآن — دلوقتي وقته</i>\n"
            "🤲 <i>فاتك شيء من وِردك؟ لا بأس، ابدأ الآن ولا تؤجل.</i>\n"
            "📿 <i>«من قال: سبحان الله وبحمده مائة مرة، حُطّت خطاياه وإن كانت مثل زبد البحر»</i>\n"
            "<blockquote><b><i>ورد القرآن لسه بينتظرك لو ما كملتش</i></b></blockquote>"
        ),
    ]
    send_text(random.choice(msgs))


def task_remind_night():
    msgs = [
        (
            "<blockquote><b>محطة آخر النهار 🌙</b></blockquote>\n"
            "⏰ <b>قبل أن تنام، راجع يومك 🤍</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            "<i>📖 القرآن: هل كان لك وِرد اليوم؟</i>\n"
            "<i>🤲 الأذكار: هل حافظت على أذكار الصباح والمساء؟</i>\n"
            "<i>🧭 الذكر: هل ذكرت الله خلال يومك ولو قليلًا؟</i>\n"
            "━━━━━━━━━━━━━━━━\n"
            "<i>إن قصّرت يومًا، فلا تترك الذكر، وجدّد العهد من جديد 🤍</i>\n"
            "<blockquote><b><i>لا تنسَ أذكار النوم، اللهم تقبّل منا ومنكم</i></b></blockquote>"
        ),
    ]
    send_text(random.choice(msgs))


# — الصلاة على النبي ﷺ يوم الجمعة —
def task_friday_salah(slot: str = ""):
    slots = {
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
    if not slot:
        slot = "morning"
    if slot not in slots:
        raise ValueError(f"❌ slot غير معروف: '{slot}' — القيم المتاحة هي: {list(slots.keys())}")
    send_text(slots[slot])


# — ذكر الساعة —
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


# — تذكيرات الصيام (من weekly_content.py) —
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
    send_text(FASTING_TEMPLATE.format(day="الإثنين"))

def task_remind_fasting_thursday():
    print("🌙 تذكير صيام الخميس")
    send_text(FASTING_TEMPLATE.format(day="الخميس"))


# ─────────────────────────────────────────────
#  قاموس المهام الموحّد
# ─────────────────────────────────────────────
TASKS: dict[str, callable] = {
    "daily_files"           : task_daily_files,
    "sabah"                 : task_sabah,
    "masa"                  : task_masa,
    "kahf"                  : task_friday_kahf,
    "remind_morning"        : task_remind_morning,
    "remind_midday"         : task_remind_midday,
    "remind_night"          : task_remind_night,
    "friday_salah"          : task_friday_salah,
    "friday_salah_fajr"     : lambda: task_friday_salah("fajr"),
    "friday_salah_morning"  : lambda: task_friday_salah("morning"),
    "friday_salah_midday"   : lambda: task_friday_salah("midday"),
    "friday_salah_asr"      : lambda: task_friday_salah("asr"),
    "hourly_zikr"           : task_hourly_zikr,
    "fasting_monday"        : task_remind_fasting_monday,
    "fasting_thursday"      : task_remind_fasting_thursday,
}

# ─────────────────────────────────────────────
#  FastAPI App
# ─────────────────────────────────────────────
app = FastAPI(title="AbdulGhanyBot API")

class TriggerRequest(BaseModel):
    task: str

@app.post("/api/trigger")
async def trigger_task(body: TriggerRequest):
    task_name = body.task.strip()

    if task_name not in TASKS:
        raise HTTPException(
            status_code=400,
            detail=f"مهمة غير معروفة: '{task_name}'. المتاح: {list(TASKS.keys())}",
        )

    print(f"▶️  تشغيل المهمة: {task_name}")
    try:
        TASKS[task_name]()
        print("✅ انتهت المهمة بنجاح")
        return {"status": "success", "task": task_name}
    except Exception as e:
        print(f"❌ خطأ في المهمة '{task_name}': {e}")
        send_error_alert(task_name, e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health():
    return {"status": "ok"}
