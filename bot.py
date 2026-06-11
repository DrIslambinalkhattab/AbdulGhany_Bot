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
            return json.load(f)
    return {"current_file": 1}

def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"💾 حُفظ التقدم: ملف رقم {state['current_file']}")

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
def progress_bar(current: int, total: int) -> str:
    length    = 12
    filled    = int((current / total) * length)
    pct       = round((current / total) * 100, 1)
    bar       = "█" * filled + "░" * (length - filled)
    remaining = total - current
    if pct < 25:   stars = "⭐"
    elif pct < 50: stars = "⭐⭐"
    elif pct < 75: stars = "⭐⭐⭐"
    else:          stars = "⭐⭐⭐⭐"
    return (
        f"<code>|{bar}|</code>  <b>{pct}%</b>  {stars}\n"
        f"📂 <b>{current}</b> من <b>{total}</b>  •  ⏳ باقي <b>{remaining}</b>"
    )

def motivational(pct: float) -> str:
    if pct < 10:
        msgs = ["🌱 <i>كل رحلة تبدأ بخطوة — بارك الله في بدايتكم</i>",
                "🌱 <i>البداية نور، والنور يكبر مع كل يوم</i>"]
    elif pct < 25:
        msgs = ["🌿 <i>ماشيين بثبات — والثبات أعظم من العجلة</i>",
                "🌿 <i>خير العمل ما داوم عليه صاحبه وإن قلّ</i>"]
    elif pct < 50:
        msgs = ["🌸 <i>ربع الطريق خلفنا — اللهم أعنّا على إتمامه</i>",
                "🌸 <i>كل يوم خطوة — وكل خطوة في ميزان حسناتكم</i>"]
    elif pct < 75:
        msgs = ["🌺 <i>أكثر من النصف — وما أجمل أن يُتم المؤمن ما بدأ</i>",
                "🌺 <i>في منتصف الطريق والهمم عالية — بارك الله فيكم</i>"]
    elif pct < 90:
        msgs = ["🌟 <i>قاربنا الختم — اللهم بلّغنا وتقبّل منا</i>",
                "🌟 <i>الخواتيم بيد الله — اللهم اجعل خواتيمنا خيراً</i>"]
    else:
        msgs = ["✨ <i>على وشك الختمة — اللهم تقبّل منا ومنكم</i>",
                "✨ <i>لحظات وتكتمل الختمة — فلا تفوّتوا هذا الشرف</i>"]
    return random.choice(msgs)


# ─────────────────────────────────────────────
#  المهمة الأولى: PDF + MP3
# ─────────────────────────────────────────────
def task_daily_files():
    state     = load_state()
    n         = state["current_file"]
    num       = f"{n:03d}"
    pct       = round((n / TOTAL_FILES) * 100, 1)
    bar       = progress_bar(n, TOTAL_FILES)
    motiv     = motivational(pct)
    date_str  = datetime.now(CAIRO_TZ).strftime("%d / %m / %Y")

    caption_pdf = (
        f"📖 <b>ختمة القرآن الكريم</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🗓 <i>{date_str}</i>   •   📂 الجزء <b>{num}</b>\n\n"
        f"{bar}\n\n"
        f"{motiv}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🤲 <i>اللهم اجعله في ميزان حسناتنا جميعاً</i>"
    )
    caption_mp3 = (
        f"🎧 <b>تلاوة الجزء {num}</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"<i>«وَرَتِّلِ الْقُرْآنَ تَرْتِيلًا»</i>\n"
        f"<i>استمع وقلبك حاضر — الأجر مضاعف</i>"
    )

    print(f"📤 إرسال الملف رقم {num} ({pct}%)")
    send_document_bytes(download(f"{RELEASE_BASE}/{num}.pdf"), f"{num}.pdf", caption_pdf)
    send_audio_bytes(download(f"{RELEASE_BASE_MP3}/{num}.mp3"), f"{num}.mp3", caption_mp3)

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
        "🌅 <blockquote><b>اقرأها بتأمل — كل ذكر له أثر</b></blockquote>"
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
        "<blockquote><b>أذكار الصباح من أعظم ما يعين على طمأنينة القلب وحفظ العبد بإذن الله.</b></blockquote>"
    )
    caption = (
        "🌆 <blockquote><b>اقرأها بتأمل — كل ذكر له أثر</b></blockquote>"
    )
    with open("Zeikr/al-azkar.pdf", "rb") as f:
        send_document_bytes(f.read(), "al-azkar.pdf", caption)

# ─────────────────────────────────────────────
#  سورة الكهف
# ─────────────────────────────────────────────
def task_friday_kahf():
    print("📖 إرسال سورة الكهف")
    send_text(
        "🕌 <blockquote><b>جمعة مباركة</b></blockquote>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "📖 <b>لا تنسَ سورة الكهف اليوم</b>\n\n"
        "<i>«مَنْ قَرَأَ سُورَةَ الْكَهْفِ فِي يَوْمِ الْجُمُعَةِ</i>\n"
        "<i>أَضَاءَ لَهُ مِنَ النُّورِ مَا بَيْنَ الْجُمُعَتَيْنِ»</i>\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "🤲 <i>تقبّل الله منا ومنكم صالح الأعمال</i>"
    )
    send_document_bytes(download(f"{RELEASE_KAHF}/al-kahf.pdf"), "al-kahf.pdf",
        "📗 <b>سورة الكهف</b>\n━━━━━━━━━━━━━━━━\n<i>اقرأ واحتسب — النور ينتظرك</i>")
    send_audio_bytes(download(f"{RELEASE_KAHF}/al-kahf.mp3"), "al-kahf.mp3",
        "🎧 <b>تلاوة سورة الكهف</b>\n━━━━━━━━━━━━━━━━\n<i>«وَرَتِّلِ الْقُرْآنَ تَرْتِيلًا»</i>")

# ─────────────────────────────────────────────
#  التذكيرات
# ─────────────────────────────────────────────
def task_remind_morning():
    msgs = [
        ("☀️ <blockquote><b>تذكير الضحى</b></blockquote>\n"
         "━━━━━━━━━━━━━━━━\n\n"
         "📌 <b>مهام اليوم:</b>\n\n"
         "📖 ورد القرآن — <i>هل قرأت جزءك؟</i>\n"
         "🤲 أذكار الصباح — <i>هل حصّنت نفسك؟</i>\n"
         "📿 الأذكار المطلقة — <i>سبّح واستغفر في أي وقت</i>\n\n"
         "━━━━━━━━━━━━━━━━\n"
         "<i>«وَمَن يَتَّقِ اللَّهَ يَجْعَل لَّهُ مَخْرَجًا»</i>"),
        ("☀️ <b>صباح الخير والبركة</b>\n"
         "━━━━━━━━━━━━━━━━\n\n"
         "⏰ النهار في أوله والفرص متاحة!\n\n"
         "📖 <i>ورد القرآن ينتظرك</i>\n"
         "🌿 <i>الأذكار تُحصّن يومك</i>\n"
         "💡 <i>دقائق مع الله تُصلح بقية يومك كله</i>\n\n"
         "━━━━━━━━━━━━━━━━\n"
         "🤲 <i>اللهم أعنّا على ذكرك وشكرك وحسن عبادتك</i>"),
    ]
    send_text(random.choice(msgs))

def task_remind_midday():
    msgs = [
        ("🌤 <blockquote><b>وقفة منتصف النهار</b></blockquote>\n"
         "━━━━━━━━━━━━━━━━\n\n"
         "النهار مضى نصفه — كيف حالك مع الله؟\n\n"
         "📖 <i>لو ما قرأتش ورد القرآن — دلوقتي وقته</i>\n"
         "🤲 <i>لو نسيت الأذكار — الله غفور رحيم، ابدأ من جديد</i>\n"
         "📿 <i>سبحان الله وبحمده — مائة مرة تمحو الخطايا</i>\n\n"
         "━━━━━━━━━━━━━━━━\n"
         "<i>«أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ»</i>"),
        ("🌤 <b>لحظة وسط الزحمة</b>\n"
         "━━━━━━━━━━━━━━━━\n\n"
         "وسط مشاغل الدنيا — لا تنس نصيبك من الله 🤍\n\n"
         "💬 قل: <b>سبحان الله وبحمده سبحان الله العظيم</b>\n"
         "<i>كلمتان خفيفتان على اللسان</i>\n"
         "<i>ثقيلتان في الميزان — حبيبتان إلى الرحمن</i>\n\n"
         "━━━━━━━━━━━━━━━━\n"
         "📖 <i>ورد القرآن لسه بينتظرك لو ما كملتش</i>"),
    ]
    send_text(random.choice(msgs))

def task_remind_night():
    msgs = [
        ("🌙 <b>محطة آخر النهار</b>\n"
         "━━━━━━━━━━━━━━━━\n\n"
         "قبل ما ينتهي يومك — حاسب نفسك بهدوء:\n\n"
         "✅ <i>هل قرأت وردك اليوم؟</i>\n"
         "✅ <i>هل قلت أذكار الصباح والمساء؟</i>\n"
         "✅ <i>هل ذكرت الله في غيرها؟</i>\n\n"
         "━━━━━━━━━━━━━━━━\n"
         "🌙 <b>أذكار النوم — لا تنم بدونها</b>\n"
         "<i>آية الكرسي • الإخلاص • المعوذتان</i>\n"
         "<i>«اللهم باسمك أموت وأحيا»</i>\n\n"
         "🤲 <i>اللهم اجعل آخر كلامنا لا إله إلا الله</i>"),
        ("🌙 <b>الليل على الأبواب</b>\n"
         "━━━━━━━━━━━━━━━━\n\n"
         "المداومة هي السر 🌟\n\n"
         "<i>«إن أحب الأعمال إلى الله أدومها وإن قلّ»</i>\n\n"
         "كل يوم بتلتزم فيه — هو انتصار 🏆\n"
         "وكل تقصير — فرصة للتوبة والبداية من جديد\n\n"
         "━━━━━━━━━━━━━━━━\n"
         "💤 <i>نامو على ذكر الله</i>\n"
         "🤲 <i>اللهم تقبّل منا ومنكم</i>"),
    ]
    send_text(random.choice(msgs))

# ─────────────────────────────────────────────
#  الصلاة على النبي ﷺ يوم الجمعة
# ─────────────────────────────────────────────
def task_friday_salah():
    now  = datetime.now(CAIRO_TZ)
    hour = now.hour
    if hour < 8:
        msg = ("🌙 <b>فجر الجمعة المباركة</b>\n"
               "━━━━━━━━━━━━━━━━\n\n"
               "💛 <b>اللهم صلِّ وسلم وبارك على نبينا محمد</b>\n\n"
               "<i>«مَن صلّى عليّ صلاةً واحدة صلّى الله عليه بها عشرًا»</i>\n\n"
               "🤍 <i>أكثروا من الصلاة على النبي يوم الجمعة</i>")
    elif hour < 12:
        msgs = [
            ("☀️ <b>صباح الجمعة</b>\n"
             "━━━━━━━━━━━━━━━━\n\n"
             "يوم الجمعة — سيد الأيام 👑\n\n"
             "🌹 <i>اللهم صلِّ على محمد وعلى آل محمد</i>\n"
             "<i>كما صليت على إبراهيم وعلى آل إبراهيم إنك حميد مجيد</i>\n\n"
             "<i>«إن من أفضل أيامكم يوم الجمعة»</i>"),
            ("☀️ <b>لحظة من الجمعة</b>\n"
             "━━━━━━━━━━━━━━━━\n\n"
             "💛 قل من قلبك:\n"
             "<b>اللهم صلِّ وسلم وبارك على سيدنا محمد</b>\n\n"
             "<i>كل صلاة ترفعك درجة عنده ﷺ</i>\n\n"
             "🤍 <i>أكثروا منها — اليوم له ميزة لا تعوّض</i>"),
        ]
        msg = random.choice(msgs)
    elif hour < 15:
        msg = ("🌤 <b>ظهر الجمعة</b>\n"
               "━━━━━━━━━━━━━━━━\n\n"
               "💛 <b>اللهم صلِّ على محمد النبي الأمي وعلى آله وصحبه وسلم</b>\n\n"
               "<i>«الدعاء بين الأذان والإقامة لا يُرد»</i>\n"
               "🕌 <i>وصلّوا الجمعة بخشوع</i>")
    else:
        msg = ("🌆 <b>عصر الجمعة</b>\n"
               "━━━━━━━━━━━━━━━━\n\n"
               "آخر ساعات الجمعة — ولا تزال الفرصة قائمة 🌟\n\n"
               "💛 <b>أكثروا من الصلاة على النبي ﷺ</b>\n\n"
               "<i>«إن لله ملائكة سيّاحين في الأرض يُبلّغوني من أمتي السلام»</i>\n\n"
               "🌹 <i>صلاة واحدة — تبلغه ﷺ سلامك</i>\n"
               "🤍 <i>جمعة مباركة على الجميع</i>")
    send_text(msg)

# ─────────────────────────────────────────────
#  ذكر الساعة
# ─────────────────────────────────────────────
AZKAAR = [
    ("💎", "سبحان الله",
     "«مَن قال: سبحان الله وبحمده، في يوم مائة مرة حُطَّت خطاياه وإن كانت مثل زبد البحر»"),
    
    ("💎", "الحمد لله",
     "«الحمد لله تملأ الميزان»"),
    
    ("💎", "الله أكبر",
     "من أحب الأذكار وأعظمها أجراً، وهي من الباقيات الصالحات."),
    
    ("💎", "سبحان الله والحمد لله ولا إله إلا الله والله أكبر",
     "«لأن أقول: سبحان الله والحمد لله ولا إله إلا الله والله أكبر أحب إلي مما طلعت عليه الشمس»"),
    
    ("💎", "لا إله إلا أنت سبحانك إني كنت من الظالمين",
     "دعوة ذي النون، ما دعا بها مسلم في شيء إلا استجاب الله له."),
    
    ("🌿", "أستغفر الله",
     "كان النبي ﷺ يستغفر الله في اليوم أكثر من سبعين مرة."),
    
    ("🌿", "أستغفر الله الذي لا إله إلا هو الحي القيوم وأتوب إليه",
     "من صيغ الاستغفار المشهورة والثابتة."),
    
    ("🌹", "الصلاة على النبي ﷺ",
     "«من صلى عليّ صلاة صلى الله عليه بها عشراً»"),
    
    ("🤲", "اللهم إنك عفو تحب العفو فاعف عني",
     "من أجلِّ الأدعية، وقد أوصى به النبي ﷺ."),
    
    ("🤲", "يا حي يا قيوم برحمتك أستغيث أصلح لي شأني كله ولا تكلني إلى نفسي طرفة عين",
     "دعاء عظيم يجمع الاستعانة والافتقار إلى الله."),
    
    ("🤲", "ربنا لا تزغ قلوبنا بعد إذ هديتنا وهب لنا من لدنك رحمة إنك أنت الوهاب",
     "من الأدعية القرآنية الجامعة."),
    
    ("🤲", "رب اشرح لي صدري ويسر لي أمري واحلل عقدة من لساني يفقهوا قولي",
     "دعاء مبارك من دعاء موسى عليه السلام."),
    
    ("⭐", "حسبي الله لا إله إلا هو عليه توكلت وهو رب العرش العظيم",
     "ذكرٌ عظيم في التوكل والاعتماد على الله."),
    
    ("⭐", "لا إله إلا الله وحده لا شريك له، له الملك وله الحمد وهو على كل شيء قدير",
     "من أفضل الأذكار، وثبتت له فضائل كثيرة في السنة."),
    
    ("⭐", "سبحان الله وبحمده، عدد خلقه، ورضا نفسه، وزنة عرشه، ومداد كلماته",
     "ذكرٌ عظيمٌ علّمه النبي ﷺ لأم المؤمنين جويرية رضي الله عنها."),
]

def task_hourly_zikr():
    now  = datetime.now(CAIRO_TZ)
    idx  = (now.hour + now.day) % len(AZKAAR)
    icon, zikr, hadith = AZKAAR[idx]
    msg = (
        #f"{icon} <b>ذكر الساعة</b>\n"
        f"<blockquote><b>{zikr}</b></blockquote>\n"
        f"<i><b>{hadith}</b></i>\n"
    )
    print("📿 إرسال الذكر العشوائي")
    send_text(msg)

# ─────────────────────────────────────────────
#  نقطة الدخول
# ─────────────────────────────────────────────
TASKS = {
    "daily_files"    : task_daily_files,
    "sabah"          : task_sabah,
    "masa"           : task_masa,
    "kahf"           : task_friday_kahf,
    "remind_morning" : task_remind_morning,
    "remind_midday"  : task_remind_midday,
    "remind_night"   : task_remind_night,
    "friday_salah"   : task_friday_salah,
    "hourly_zikr"    : task_hourly_zikr,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in TASKS:
        print(f"الاستخدام: python bot.py <{'|'.join(TASKS)}>")
        sys.exit(1)
    task_name = sys.argv[1]
    print(f"▶️  تشغيل المهمة: {task_name}")
    TASKS[task_name]()
    print("✅ انتهت المهمة بنجاح")
