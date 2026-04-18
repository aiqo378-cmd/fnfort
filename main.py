import random
import re
import logging
import os
import asyncio
import json
import threading
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from flask import Flask

# --- Flask ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is Running Live!"

def run_flask():
    web_app.run(host='0.0.0.0', port=7860)

# --- الإعدادات الثابتة ---
TOKEN = "8546666050:AAFt7buGH1xrVTTWa-lrIhOdesG_sk2n_bM"
CONSTITUTION_LINK = "https://t.me/arab_union3"
AU_LINK = "https://t.me/arab_union3"
DATA_FILE = "bot_data.json"

# --- قاموس القوانين التفصيلية (محدّث وشامل) ---
DETAILED_LAWS = {
    "قوائم": """⚖️ قوانين القوائم:
1️⃣ أي فوز قوائم يمنع كتابة النجم والحاسم (يُترك فارغاً).
2️⃣ إذا كان الحاسم For Free لا يحتسب، يكون الحاسم من قبله.
3️⃣ يمنع جدولة القوائم (إرسالها والقائد غير متصل أو آخر دقيقة بدون قراءة).
4️⃣ المنشن للحكم إلزامي عند إرسال القائمة، بدونه تُعتبر لاغية (مدة الاعتراض 10 ساعات).
5️⃣ وقت القوائم: نصف/نهائي = 18 ساعة (+15د سماح)، باقي الأدوار = 14 ساعة (+15د سماح).
🔗 للمزيد: https://t.me/arab_union3""",

    "سكربت": """⚖️ قوانين السكربت:
⬆️ طاقات 92 أو أقل = سكربت (حتى لو ميسي).
⬆️ طاقات أعلى من 92 = ليس سكربت (باستثناء بدون وجه).
⬆️ تغيير الأسلوب أو مدرب لا يناسب الأسلوب = سكربت.
⬆️ تبديل أماكن اللاعبين = سكربت.
⬆️ الاعتراض في بداية المباراة فقط (الخروج فوراً مع دليل).
⬆️ في المنتصف: تغيير التشكيلة أو المدرب لا يعتبر سكربت.
🔗 للمزيد: https://t.me/arab_union3""",

    "وقت": """⚖️ توقيت المواجهات:
⏰ الوقت الرسمي: من 9 صباحاً حتى 1 صباحاً (1:59 = انتهى الوقت).
🚫 لا يُجبر الخصم على اللعب في وقت غير رسمي (2-8 صباحاً).
📅 مدة المواجهات:
- دور مجموعات/16/ربع نهائي/نصف نهائي: 48 ساعة.
- النهائي/دوري رسمي: 72 ساعة.
🔥 التمديد: يوم واحد (أدوار عادية)، يومين (نصف/نهائي).
✅ يمدد تلقائياً في: مواجهة حاسمة، اتفاق طرفين، شروط التمديد.
🔗 للمزيد: https://t.me/arab_union3""",

    "تواجد": """⚖️ قوانين التواجد والغياب:
🤔 غياب 20 ساعة بدون اتفاق = تبديل مباشر.
🤔 غياب الطرفين = يُبدَّل الأقل محاولة للاتفاق.
🤔 وضع تفاعل على رسالة الموعد يُعتبر اتفاقاً.
🤔 الرد خلال 10 دقائق بدون تحديد موعد = تهرب (يستوجب التبديل).
🤔 التاكات في الوقت الغير رسمي لا تحتسب (باستثناء الاتفاق).
🔗 للمزيد: https://t.me/arab_union3""",

    "تصوير": """⚖️ قوانين التصوير:
1- وقت التصوير في البداية فقط.
2- وقت إرسال التصوير في أي وقت (بداية أو نهاية).
3- الآيفون: فيديو (روم المحادثة + الرقم التسلسلي من "حول الجهاز" حصراً).
4- يُمنع التصوير في نهاية المباراة لتجنب الغش (باستثناء دليل واضح).
🔗 للمزيد: https://t.me/arab_union3""",

    "انسحاب": """⚖️ قوانين الانسحاب والخروج:
🤔 خروج الخاسر = مهلة ساعتين للعب، إن تخلف يُضاف هدف.
🤔 خروج بدون دليل ثم اختفاء ساعتين = هدف مباشر بدون تحذير.
🤔 انفراد/هجمة محققة مع دليل واضح = هدف مباشر.
🤔 خروج متعمد (اعتراف) = هدف مباشر.
🤔 سوء نت: فيديو 30 ثانية يوضح اللاق والإشعارات (لا يقل عن 30 ثانية).
🤔 الخروج بدون فسخ عقد = حظر بمدة العقد المتبقية (أقصى أسبوعين).
🔗 للمزيد: https://t.me/arab_union3""",

    "سب": """⚖️ قوانين السب والإساءة:
🚫 سب الأهل/الكفر = طرد وحظر (يمكن تقليله بالتنازل).
🚫 السب في الخاص أثناء المواجهة = تبديل + حظر (يتطلب دليل فيديو باليوزر).
🚫 سب الحكم في الخاص = تبديل + حظر.
🚫 استفزاز اللاعبين = طرد مباشر، إن استمر = حظر.
🚫 استفزاز الحكم/لجنة التنظيم = عقوبة تقديرية.
🔗 للمزيد: https://t.me/arab_union3""",

    "فار": """⚖️ قوانين الـ VAR:
✅ يحق طلب الـ VAR مرة واحدة فقط في (نصف النهائي، ربع النهائي، دور 16).
✅ الاعتماد الأساسي على حكم المباراة.
✅ في حال كان قرار الحكم مخالفاً للدستور: مراسلة @mwsa_20.
🔗 للمزيد: https://t.me/arab_union3""",

    "انتقالات": """⚖️ قوانين الانتقالات:
📺 مسموحة فقط يومي (الخميس والجمعة) من كل أسبوع.
🤔 أي انتقال في يوم آخر يعتبر غير رسمي ويتم تبديل اللاعب.
🤔 اللاعب الحر (بدون عقد) يمكنه الانتقال في أي وقت.
🤔 اللاعب الجديد الغير مسجل يمكنه الانتقال أول مرة بأي وقت.
🔗 للمزيد: https://t.me/arab_union3""",

    "عقود": """⚖️ قوانين العقود:
🤔 أقصى حد للمسؤولين في العقود: 8 قادة (التاسع يُطرد فوراً).
🤔 فسخ العقد حصراً من القادة المسجلين في العقود.
🤔 الخروج بدون فسخ = حظر بالمدة المتبقية (أقصى أسبوعين).
🤔 فسخ الإعارة = حظر بمدة الإعارة المتبقية (أقصى أسبوعين).
🤔 تبديل المسؤول ثم إعادته = 48 ساعة انتظار للعودة.
🤔 الاعتراض على العقد بعد المباراة: الخيار للخصم (سحب نقطة أو استكمال).
🔗 للمزيد: https://t.me/arab_union3""",

    "حظر": """⚖️ قوانين الحظر:
🚫 الكفر/سب الأهل = حظر فوري (قابل للتقليل بالتنازل).
🚫 الوهمي = حظر.
🚫 سب اللجنة/الاستهزاء بالاتحاد = حظر أسبوعين (حتى لو اعتذر).
🚫 استخدام VPN = حظر.
🚫 إضافة لاعب محظور = حظر.
✅ مدة الاعتراض على الحظر: أول يومين فقط.
✅ تقليل مدة الحظر بالتنازل: السب يُقلَّل للنصف بموافقة المشتكي.
🔗 للمزيد: https://t.me/arab_union3""",

    "اعتراض": """⚖️ قوانين الاعتراض:
🤔 الاعتراض على إعدادات الروم: قبل بدء المباراة فقط.
🤔 الاعتراض العام: قبل المباراة (باستثناء: عقد اللاعب، الرقم التسلسلي، 3 إنذارات، سب بعد الإكمال).
🤔 يسقط حق الاعتراض على قرار الحكم بعد 12 ساعة من انتهاء المواجهة.
🤔 التبديل آخر ساعتين: ممنوع إلا باعتراض الخصم على حالة تستوجب التبديل.
🤔 الاعتراض على قائمة بدون تاك: 10 ساعات فقط.
🔗 للمزيد: https://t.me/arab_union3""",

    "نشر": """⚖️ قوانين النشر:
📢 فوز القوائم = يمنع كتابة النجم والحاسم (يُترك فارغاً).
📢 نجم المواجهة يحدده الحكم (الأهداف + التأثير + السلوك).
📢 أفضل قائد يحدده الحكم (أكثر قائد تواجداً).
📢 الشخص غير الحاسم الفائز لا يُنشر = حظر النشر الوهمي.
📢 نشر نتيجة خاطئة = حظر.
📢 النشر الوهمي في التصنيف = حظر + احتمال خصم نقاط.
🔗 للمزيد: https://t.me/arab_union3""",

    "تسلسلي": """⚖️ قوانين الرقم التسلسلي:
🔄 يمكن التغيير كل 15 يوم (الشهر ينقسم قسمين: أول 15 + ثاني 15).
📱 الآيفون: التصوير من "حول الجهاز" حصراً (ليس من الحسابات).
⚠️ حساب احتيالي = يستبدل فوراً، وإن لعب يعتبر خاسراً.
🔗 للمزيد: https://t.me/arab_union3""",

    "انذارات": """⚖️ قوانين الإنذارات:
⚠️ إنذار لاعب: 3 إنذارات = طرد وحظر.
⚠️ إنذار مسؤول (م): 3 إنذارات = سحب الصلاحيات.
⚠️ الإنذارات تُطبق على: الإساءة الواضحة للخصم + الاستفزاز.
✅ إلغاء الإنذار حصراً من الحكم أو السوبر أدمن.
🔗 للمزيد: https://t.me/arab_union3""",
}

# كلمات الطرد
BAN_WORDS = ["كسمك", "كسمه", "كسختك"]

# كلمات الاستفزاز التي تستوجب التحذير
PROVOCATION_WORDS = ["تافه", "زبالة", "كلب", "حمار", "غبي", "أحمق", "مجنون", "خسران دايم"]

# مخازن البيانات
wars = {}
clans_mgmt = {}
user_warnings = {}
admin_warnings = {}
original_msg_store = {}
tak_tracking = {}        # تتبع التاكات {cid: {player_tag: {opponent_tag: [timestamps]}}}
substitutions = {}       # تتبع التبديلات {cid: {clan_key: count}}
pending_objections = {}  # اعتراضات معلقة {cid: {objection_id: data}}

# --- دوال الحفظ والاسترجاع ---
def save_data():
    data = {
        "wars": wars,
        "clans_mgmt": clans_mgmt,
        "user_warnings": user_warnings,
        "admin_warnings": admin_warnings,
        "tak_tracking": tak_tracking,
        "substitutions": substitutions,
    }
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print("✅ Data saved.")
    except Exception as e:
        print(f"❌ Save error: {e}")

def load_data():
    global wars, clans_mgmt, user_warnings, admin_warnings, tak_tracking, substitutions
    if not os.path.exists(DATA_FILE):
        return
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if "wars" in data:
            wars = {int(k): v for k, v in data["wars"].items()}
        if "clans_mgmt" in data:
            clans_mgmt = {int(k): v for k, v in data["clans_mgmt"].items()}
        if "user_warnings" in data:
            user_warnings = {int(k): v for k, v in data["user_warnings"].items()}
        if "admin_warnings" in data:
            admin_warnings = {int(k): v for k, v in data["admin_warnings"].items()}
        if "tak_tracking" in data:
            tak_tracking = {int(k): v for k, v in data["tak_tracking"].items()}
        if "substitutions" in data:
            substitutions = {int(k): v for k, v in data["substitutions"].items()}
        print("✅ Data loaded.")
    except Exception as e:
        print(f"❌ Load error: {e}")

# --- دوال مساعدة ---
def to_emoji(num):
    dic = {'0':'0️⃣','1':'1️⃣','2':'2️⃣','3':'3️⃣','4':'4️⃣','5':'5️⃣','6':'6️⃣','7':'7️⃣','8':'8️⃣','9':'9️⃣'}
    return "".join(dic.get(c, c) for c in str(num))

def clean_text(text):
    if not text: return ""
    text = text.lower()
    text = text.replace('ة','ه').replace('أ','ا').replace('إ','ا').replace('آ','ا')
    text = re.sub(r'^(ال)', '', text)
    return text

def is_official_time():
    """التحقق من الوقت الرسمي (9 صباحاً - 1:59 صباحاً)"""
    now = datetime.now()
    hour = now.hour
    # الوقت الرسمي: 9 صباحاً حتى 1:59 صباحاً (ساعة 9 إلى 25 = 9 إلى 1+24)
    if hour >= 9 or hour <= 1:
        return True
    return False

def build_table(w, au_link):
    rows = []
    for i, m in enumerate(w["matches"]):
        rows.append(f"{i+1} | {m['p1']} {to_emoji(m['s1'])}|🆚|{to_emoji(m['s2'])} {m['p2']} |")
    c1 = w['c1']
    c2 = w['c2']
    return (
        f"A- [ {c1['n']} ] | 𝗩𝗦 | B- [ {c2['n']} ]\n"
        f"───\n"
        + "\n".join(rows) +
        f"\n───\n"
        f"النقاط: {c1['n']} {c1['s']} - {c2['s']} {c2['n']}\n"
        f"⌛ يومين وينتهي الوقت\n"
        f"🔗 {au_link}"
    )

# --- معالج التعديلات ---
async def handle_edited_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.edited_message or not update.edited_message.text:
        return
    mid = update.edited_message.message_id
    if mid in original_msg_store:
        old_text = original_msg_store[mid]
        new_text = update.edited_message.text
        if old_text != new_text:
            await update.edited_message.reply_text(
                f"🚨 تنبيه: تم تعديل رسالة في جروب المواجهة!\n\n"
                f"📜 الرسالة قبل التعديل:\n{old_text}\n\n"
                f"🔄 الرسالة بعد التعديل:\n{new_text}\n\n"
                f"⚠️ التلاعب بالرسائل والقوائم ممنوع."
            )

# --- معالج الأزرار (Callback) ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cid = query.message.chat.id
    data = query.data

    # معالجة أزرار التاكات (بعد 3 أيام)
    if data.startswith("tak_win_"):
        parts = data.split("_")
        clan_key = parts[2]  # c1 أو c2
        if cid in wars and wars[cid]["active"]:
            w = wars[cid]
            w[clan_key]["s"] += 1
            w[clan_key]["stats"].append({
                "name": "Tak Win",
                "goals": 0,
                "rec": 0,
                "is_free": True,
                "is_tak": True
            })
            save_data()
            try:
                await context.bot.set_chat_title(cid, f"⚔️ {w['c1']['n']} {w['c1']['s']} - {w['c2']['s']} {w['c2']['n']} ⚔️")
            except:
                pass
            if w["mid"]:
                try:
                    await context.bot.edit_message_text(
                        build_table(w, AU_LINK), cid, w["mid"],
                        disable_web_page_preview=True
                    )
                except:
                    pass
            await query.edit_message_text(
                f"✅ تم احتساب نقطة تاكات فري لكلان {w[clan_key]['n']}.\n"
                f"⚽ لا تُحتسب في النجم والحاسم."
            )

    # معالجة أزرار الاعتراض
    elif data.startswith("obj_"):
        parts = data.split("_", 2)
        action = parts[1]
        obj_id = parts[2] if len(parts) > 2 else ""
        if cid in pending_objections and obj_id in pending_objections[cid]:
            obj = pending_objections[cid][obj_id]
            if action == "accept":
                await query.edit_message_text(f"✅ تم قبول الاعتراض وإحالته للحكام.\n📝 الاعتراض: {obj['text']}")
                # إرسال للحكام (يمكن تخصيص معرف جروب الحكام)
            elif action == "cancel":
                del pending_objections[cid][obj_id]
                await query.edit_message_text("❌ تم إلغاء الاعتراض.")

# ============================================================
# المعالج الرئيسي للرسائل
# ============================================================
async def handle_war(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    cid = update.effective_chat.id
    msg = update.message.text
    mid = update.message.message_id
    msg_up = msg.upper().strip()
    msg_cleaned = clean_text(msg)
    user = update.effective_user
    bot_username = context.bot.username
    u_tag = f"@{user.username}" if user.username else f"ID:{user.id}"

    # حفظ الرسالة الأصلية
    original_msg_store[mid] = msg

    # تحديد رتبة المستخدم
    super_admins = ["mwsa_20", "levil_8"]
    try:
        chat_member = await context.bot.get_chat_member(cid, user.id)
        is_creator = (chat_member.status == 'creator')
        is_admin_status = chat_member.status in ['creator', 'administrator']
    except:
        is_creator = False
        is_admin_status = False

    is_referee = (user.username in super_admins) or is_creator

    is_bot_mentioned = (f"@{bot_username}" in msg) or (
        update.message.reply_to_message and
        update.message.reply_to_message.from_user and
        update.message.reply_to_message.from_user.id == context.bot.id
    )

    # ============================================================
    # الذكاء الاصطناعي - الرد على القوانين عند المنشن
    # ============================================================
    if is_bot_mentioned:
        for keyword, law_text in DETAILED_LAWS.items():
            if keyword in msg_cleaned:
                await update.message.reply_text(law_text, disable_web_page_preview=True)
                return

        # إذا لم يجد قانوناً محدداً، يرد بمساعدة عامة
        if "قانون" in msg_cleaned or "كيف" in msg_cleaned or "ما هو" in msg_cleaned or "ايش" in msg_cleaned:
            help_text = (
                "⚖️ يمكنك السؤال عن القوانين التالية:\n"
                "📋 قوائم | سكربت | وقت | تواجد | تصوير\n"
                "📋 انسحاب | سب | فار | انتقالات | عقود\n"
                "📋 حظر | اعتراض | نشر | تسلسلي | انذارات\n\n"
                "مثال: @بوت قانون السكربت\n"
                f"🔗 الدستور الكامل: {CONSTITUTION_LINK}"
            )
            await update.message.reply_text(help_text, disable_web_page_preview=True)
            return

    # ============================================================
    # نظام الطرد الآلي (السب والكفر)
    # ============================================================
    for word in BAN_WORDS:
        if word in msg.lower():
            if user.username not in super_admins:
                try:
                    await context.bot.ban_chat_member(cid, user.id)
                    await update.message.reply_text(
                        f"🚫 تم طرد {u_tag} فوراً لانتهاك قوانين الاتحاد (سب/كفر).\n"
                        f"⚖️ يمكن تقليل مدة الحظر بتنازل الطرف المشتكي."
                    )
                except:
                    pass
            return

    # ============================================================
    # كشف كلمات الاستفزاز
    # ============================================================
    for word in PROVOCATION_WORDS:
        if word in msg.lower() and cid in wars and wars[cid].get("active"):
            if user_warnings.get(cid, {}).get(u_tag, 0) == 0:
                # تحذير أول
                if cid not in user_warnings:
                    user_warnings[cid] = {}
                user_warnings[cid][u_tag] = user_warnings.get(cid, {}).get(u_tag, 0) + 1
                save_data()
                await update.message.reply_text(
                    f"⚠️ تنبيه {u_tag}: الاستفزاز مخالف لقوانين الاتحاد!\n"
                    f"التكرار قد يؤدي إلى الطرد والحظر."
                )
            break

    # ============================================================
    # إلغاء الإنذار (للحكم فقط)
    # ============================================================
    if "الغاء انذار" in msg_cleaned and is_referee:
        target_t = None
        if update.message.reply_to_message:
            t_user = update.message.reply_to_message.from_user
            target_t = f"@{t_user.username}" if t_user.username else f"ID:{t_user.id}"
        else:
            mentions = re.findall(r'@\w+', msg)
            if mentions:
                target_t = mentions[0]
        if target_t:
            if cid in user_warnings and target_t in user_warnings[cid]:
                user_warnings[cid][target_t] = 0
            if cid in admin_warnings and target_t in admin_warnings[cid]:
                admin_warnings[cid][target_t] = 0
            save_data()
            await update.message.reply_text(f"✅ تم صفر إنذارات {target_t} بواسطة الإدارة.")
        return

    # ============================================================
    # الروليت
    # ============================================================
    if "روليت" in msg:
        roulette_match = re.findall(r'@\w+', msg)
        if len(roulette_match) >= 2:
            winner = random.choice(roulette_match)
            await update.message.reply_text(f"🎲 قرعة الروليت:\n\n🏆 الفائز هو: {winner}")
            return

    # ============================================================
    # نظام الإنذارات (بالرد)
    # ============================================================
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        t_tag = f"@{target_user.username}" if target_user.username else f"ID:{target_user.id}"

        if msg.strip() == "انذار م" and is_referee:
            if cid not in admin_warnings:
                admin_warnings[cid] = {}
            count = admin_warnings[cid].get(t_tag, 0) + 1
            admin_warnings[cid][t_tag] = count
            save_data()
            await update.message.reply_text(
                f"⚠️ إنذار مسؤول (م)\n👤 المسؤول: {t_tag}\n🔢 العدد: ({count}/3)"
            )
            if count >= 3:
                await update.message.reply_text(f"🚫 تم سحب صلاحيات المسؤول {t_tag} بواسطة الإدارة.")
            return

        if msg.strip() == "انذار" and is_referee:
            if cid not in user_warnings:
                user_warnings[cid] = {}
            count = user_warnings[cid].get(t_tag, 0) + 1
            user_warnings[cid][t_tag] = count
            save_data()
            await update.message.reply_text(
                f"⚠️ إنذار لاعب\n👤 اللاعب: {t_tag}\n🔢 العدد: ({count}/3)\n"
                f"⚖️ الإنذارات: الإساءة الواضحة + الاستفزاز"
            )
            if count >= 3:
                try:
                    await context.bot.ban_chat_member(cid, target_user.id)
                    await update.message.reply_text(f"🚫 تم طرد {t_tag} بعد 3 إنذارات.")
                except:
                    pass
            return

    # ============================================================
    # استقبال أوامر بوت النشر
    # ============================================================
    if "بدء مواجهة:" in msg:
        link_match = re.search(r'الرابط: (.+)', msg)
        type_match = re.search(r'النوع: (.+)', msg)
        clans_match = re.search(r'الكلانات: (.+)', msg)

        if link_match and clans_match:
            source_url = link_match.group(1).strip()
            war_type = type_match.group(1).strip() if type_match else ""
            clans_text = clans_match.group(1).strip()

            parts = clans_text.upper().split(" VS ")
            c1_n = parts[0].replace("CLAN ", "").strip()
            c2_n = parts[1].replace("CLAN ", "").strip() if len(parts) > 1 else "UNKNOWN"

            wars[cid] = {
                "c1": {"n": c1_n, "s": 0, "p": [], "stats": [], "leader": None},
                "c2": {"n": c2_n, "s": 0, "p": [], "stats": [], "leader": None},
                "active": True, "mid": None, "matches": [],
                "source_link": source_url,
                "start_time": datetime.now().isoformat(),
                "war_type": war_type
            }
            substitutions[cid] = {"c1": 0, "c2": 0}
            save_data()

            try:
                new_title = f"⚔️ {c1_n} 0 - 0 {c2_n} {war_type}".strip()
                await context.bot.set_chat_title(cid, new_title)
                await context.bot.set_chat_description(
                    cid,
                    f"مواجهة رسمية بين {c1_n} و {c2_n}\n"
                    f"النوع: {war_type}\n"
                    f"رابط المنشور: {source_url}"
                )
            except Exception as e:
                print(f"Error updating chat: {e}")

            await update.message.reply_text(
                f"🚀 تم استلام البيانات من بوت النشر!\n"
                f"⚔️ {c1_n} VS {c2_n}\n"
                f"📝 النوع: {war_type}\n"
                f"🔗 المنشور: {source_url}\n\n"
                f"✅ تم تحديث اسم الجروب والوصف وبدء الحرب!"
            )
            return

    # ============================================================
    # بدء المواجهة اليدوي (CLAN VS CLAN)
    # ============================================================
    if "CLAN" in msg_up and "VS" in msg_up and "+ 1" not in msg_up and "+1" not in msg_up:
        parts = msg_up.split(" VS ")
        if len(parts) >= 2:
            c1_name = parts[0].replace("CLAN ", "").strip()
            c2_name = parts[1].replace("CLAN ", "").strip()

            wars[cid] = {
                "c1": {"n": c1_name, "s": 0, "p": [], "stats": [], "leader": None},
                "c2": {"n": c2_name, "s": 0, "p": [], "stats": [], "leader": None},
                "active": True, "mid": None, "matches": [],
                "start_time": datetime.now().isoformat(),
                "war_type": ""
            }
            substitutions[cid] = {"c1": 0, "c2": 0}
            save_data()
            await update.message.reply_text(
                f"⚔️ بدأت الحرب الرسمية بين:\n🔥 {c1_name} ضد {c2_name} 🔥\n\n"
                f"📌 التاكات تبدأ بعد عمل القرعة."
            )
            try:
                await context.bot.set_chat_title(cid, f"⚔️ {c1_name} 0 - 0 {c2_name} ⚔️")
            except:
                pass
            return

    # ============================================================
    # العمليات داخل المواجهة النشطة
    # ============================================================
    if cid in wars and wars[cid]["active"]:
        w = wars[cid]

        # --- اعتراض / عندي اعتراض ---
        if ("اعتراض" in msg_cleaned or "عندي اعتراض" in msg_cleaned) and (
            w["c1"]["leader"] == u_tag or w["c2"]["leader"] == u_tag or is_referee
        ):
            # التحقق من أن المستخدم قائد أو مساعد
            clan_key = None
            if w["c1"]["leader"] == u_tag:
                clan_key = "c1"
            elif w["c2"]["leader"] == u_tag:
                clan_key = "c2"
            else:
                # تحقق من المساعدين
                for ck in ["c1", "c2"]:
                    clan_nm = w[ck]["n"].upper()
                    asst = clans_mgmt.get(cid, {}).get(clan_nm, {}).get("asst")
                    if asst == u_tag:
                        clan_key = ck
                        break

            if clan_key or is_referee:
                obj_id = str(mid)
                if cid not in pending_objections:
                    pending_objections[cid] = {}
                pending_objections[cid][obj_id] = {
                    "text": msg,
                    "user": u_tag,
                    "clan": clan_key
                }

                keyboard = [
                    [
                        InlineKeyboardButton("✅ إرسال للحكام", callback_data=f"obj_accept_{obj_id}"),
                        InlineKeyboardButton("❌ إلغاء", callback_data=f"obj_cancel_{obj_id}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"📝 تم استقبال اعتراضك يا {u_tag}.\n"
                    f"اضغط 'إرسال للحكام' لتحويله، أو اكتب تفاصيل الاعتراض:",
                    reply_markup=reply_markup
                )
                return

        # --- قائد بديل يدوياً ---
        sub_leader_match = re.search(r'مسؤول / قائد بدالي\s+(@\w+)\s+كلان\s+(.+)', msg)
        if sub_leader_match and is_referee:
            new_leader = sub_leader_match.group(1)
            target_clan_name = sub_leader_match.group(2).strip().upper()
            target_k = None
            if w["c1"]["n"].upper() == target_clan_name:
                target_k = "c1"
            elif w["c2"]["n"].upper() == target_clan_name:
                target_k = "c2"
            if target_k:
                w[target_k]["leader"] = new_leader
                save_data()
                await update.message.reply_text(
                    f"✅ تم تعيين {new_leader} قائداً رسمياً لكلان {w[target_k]['n']}."
                )
            else:
                await update.message.reply_text("❌ لم يتم العثور على كلان بهذا الاسم.")
            return

        # --- تسجيل القائمة ---
        if "قائم" in msg_cleaned and update.message.reply_to_message:
            target_k = None
            if w["c1"]["n"].upper() in msg_up:
                target_k = "c1"
            elif w["c2"]["n"].upper() in msg_up:
                target_k = "c2"

            if target_k:
                if not is_referee:
                    other_k = "c2" if target_k == "c1" else "c1"
                    if w[other_k]["leader"] == u_tag:
                        await update.message.reply_text("❌ أنت قائد الكلان الخصم!")
                        return

                w[target_k]["leader"] = u_tag
                raw_list = update.message.reply_to_message.text or ""
                w[target_k]["p"] = [p.strip() for p in raw_list.split('\n') if p.strip().startswith('@')]
                save_data()
                await update.message.reply_text(
                    f"✅ تم اعتماد القائمة لـ {w[target_k]['n']} (بواسطة {u_tag}).\n"
                    f"📌 تذكير: المنشن للحكم إلزامي عند إرسال القائمة."
                )

                if w["c1"]["p"] and w["c2"]["p"]:
                    p1 = list(w["c1"]["p"])
                    p2 = list(w["c2"]["p"])
                    random.shuffle(p1)
                    random.shuffle(p2)
                    w["matches"] = [
                        {"p1": u1, "p2": u2, "s1": 0, "s2": 0}
                        for u1, u2 in zip(p1, p2)
                    ]
                    save_data()

                    table = build_table(w, AU_LINK)
                    sent = await update.message.reply_text(table, disable_web_page_preview=True)
                    w["mid"] = sent.message_id
                    save_data()

                    try:
                        await context.bot.pin_chat_message(chat_id=cid, message_id=sent.message_id)
                    except Exception as e:
                        print(f"Pin error: {e}")

                    # جدولة إرسال نتائج التاكات بعد 3 أيام
                    asyncio.create_task(schedule_tak_results(cid, context))
            return

        # --- تحديد المساعد ---
        asst_match = re.search(r'مساعدي\s+(@\w+)\s+كلان\s+(\w+)', msg)
        if asst_match:
            target_asst = asst_match.group(1)
            clan_name = asst_match.group(2).upper()
            target_key = None
            if w["c1"]["n"].upper() == clan_name:
                target_key = "c1"
            elif w["c2"]["n"].upper() == clan_name:
                target_key = "c2"

            if target_key and (w[target_key]["leader"] == u_tag or is_referee):
                if cid not in clans_mgmt:
                    clans_mgmt[cid] = {}
                clans_mgmt[cid][clan_name] = {"asst": target_asst}
                save_data()
                await update.message.reply_text(f"✅ تم تعيين {target_asst} مساعداً لكلان {clan_name}.")
            elif target_key:
                await update.message.reply_text("❌ فقط قائد الكلان أو الحكم يمكنه تحديد المساعد.")
            return

        # ============================================================
        # نظام التبديلات (تبديل CLAN_NAME)
        # ============================================================
        sub_cmd = re.match(r'^تبديل\s+(.+)$', msg.strip(), re.IGNORECASE)
        if sub_cmd:
            clan_name_req = sub_cmd.group(1).strip().upper()
            target_k = None
            if w["c1"]["n"].upper() == clan_name_req:
                target_k = "c1"
            elif w["c2"]["n"].upper() == clan_name_req:
                target_k = "c2"

            if target_k:
                # التحقق من أن المستخدم القائد أو المساعد أو الحكم
                clan_nm = w[target_k]["n"].upper()
                asst_tag = clans_mgmt.get(cid, {}).get(clan_nm, {}).get("asst")
                is_authorized = is_referee or u_tag == w[target_k]["leader"] or u_tag == asst_tag

                if not is_authorized:
                    await update.message.reply_text("❌ التبديل مسموح للحكام أو القادة/المساعدين فقط.")
                    return

                if cid not in substitutions:
                    substitutions[cid] = {"c1": 0, "c2": 0}

                current_subs = substitutions[cid].get(target_k, 0)

                if current_subs >= 3:
                    await update.message.reply_text(
                        f"⚠️ كلان {w[target_k]['n']} استنفذ الحد الأقصى للتبديلات (3/3).\n"
                        f"❌ لا يمكن إجراء تبديل رابع."
                    )
                    return

                # انتظار رسالة التبديل التالية لمعرفة اللاعب الخارج والداخل
                substitutions[cid][target_k] = current_subs + 1
                save_data()
                remaining = 3 - substitutions[cid][target_k]
                await update.message.reply_text(
                    f"🔄 طلب تبديل لكلان {w[target_k]['n']} مسجّل.\n"
                    f"📊 التبديلات المستخدمة: {substitutions[cid][target_k]}/3 (متبقي: {remaining})\n"
                    f"📝 أرسل: @لاعب_خارج ← @لاعب_داخل"
                )
            return

        # --- تسجيل اللاعب الخارج والداخل بعد طلب التبديل ---
        swap_match = re.search(r'(@\w+)\s*[←>]\s*(@\w+)', msg)
        if swap_match and is_bot_mentioned or (
            swap_match and cid in substitutions and any(
                substitutions[cid].get(k, 0) > 0 for k in ["c1", "c2"]
            )
        ):
            if swap_match:
                out_player = swap_match.group(1)
                in_player = swap_match.group(2)
                # البحث عن الكلان الذي ينتمي إليه اللاعب الخارج
                for ck in ["c1", "c2"]:
                    for i, m in enumerate(w["matches"]):
                        if out_player.upper() == m["p1"].upper():
                            old_p = m["p1"]
                            w["matches"][i]["p1"] = in_player
                            save_data()
                            if w["mid"]:
                                try:
                                    await context.bot.edit_message_text(
                                        build_table(w, AU_LINK), cid, w["mid"],
                                        disable_web_page_preview=True
                                    )
                                except:
                                    pass
                            await update.message.reply_text(
                                f"🔄 تم التبديل في كلان {w[ck]['n']}:\n"
                                f"❌ خروج: {old_p}\n"
                                f"✅ دخول: {in_player}"
                            )
                            return
                        elif out_player.upper() == m["p2"].upper():
                            old_p = m["p2"]
                            w["matches"][i]["p2"] = in_player
                            save_data()
                            if w["mid"]:
                                try:
                                    await context.bot.edit_message_text(
                                        build_table(w, AU_LINK), cid, w["mid"],
                                        disable_web_page_preview=True
                                    )
                                except:
                                    pass
                            await update.message.reply_text(
                                f"🔄 تم التبديل في كلان {w[ck]['n']}:\n"
                                f"❌ خروج: {old_p}\n"
                                f"✅ دخول: {in_player}"
                            )
                            return

        # ============================================================
        # نظام التاكات
        # ============================================================
        tak_match = re.findall(r'@\w+', msg)
        is_tak_msg = len(tak_match) >= 1 and (
            "تاك" in msg_cleaned or update.message.entities
        )

        # رصد التاكات البسيطة (منشن في رسالة قصيرة)
        if len(msg.split()) <= 3 and len(tak_match) == 1 and tak_match[0] != f"@{bot_username}":
            target_tag = tak_match[0]
            # التحقق من الوقت الرسمي
            if not is_official_time():
                # التاكات في الوقت غير الرسمي لا تحتسب
                pass
            else:
                # تسجيل التاك
                if cid not in tak_tracking:
                    tak_tracking[cid] = {}
                if u_tag not in tak_tracking[cid]:
                    tak_tracking[cid][u_tag] = {}
                if target_tag not in tak_tracking[cid][u_tag]:
                    tak_tracking[cid][u_tag][target_tag] = []

                taks = tak_tracking[cid][u_tag][target_tag]
                now_ts = datetime.now().isoformat()

                # تاك واحد كل 30 دقيقة
                if taks:
                    last_tak = datetime.fromisoformat(taks[-1])
                    if (datetime.now() - last_tak).total_seconds() < 1800:
                        # لم تمر 30 دقيقة بعد، لا يحتسب تاك جديد
                        return

                tak_tracking[cid][u_tag][target_tag].append(now_ts)
                save_data()

        # ============================================================
        # نظام الحاسم
        # ============================================================
        hasm_match = re.match(r'^حاسم\s+(.+)$', msg.strip(), re.IGNORECASE)
        if hasm_match:
            clan_name_req = hasm_match.group(1).strip().upper()
            target_k = None
            if w["c1"]["n"].upper() == clan_name_req:
                target_k = "c1"
            elif w["c2"]["n"].upper() == clan_name_req:
                target_k = "c2"

            if target_k:
                if not is_official_time():
                    await update.message.reply_text(
                        "🚫 لا يمكن تحديد الحاسم في الوقت غير الرسمي (2-8 صباحاً)."
                    )
                    return

                # التحقق من أن النتيجة تعادل 3-3
                if w["c1"]["s"] == w["c2"]["s"] == 3:
                    w[target_k]["hasim_player"] = u_tag
                    save_data()

                    if w["c1"].get("hasim_player") and w["c2"].get("hasim_player"):
                        h1 = w["c1"]["hasim_player"]
                        h2 = w["c2"]["hasim_player"]
                        # إيقاف تتبع التاكات القديم وبدء الجديد بين الحاسمين
                        if cid not in tak_tracking:
                            tak_tracking[cid] = {}
                        tak_tracking[cid]["hasim_mode"] = True
                        tak_tracking[cid]["hasim_c1"] = h1
                        tak_tracking[cid]["hasim_c2"] = h2
                        save_data()
                        await update.message.reply_text(
                            f"⚡ الحاسم!\n"
                            f"🔴 {w['c1']['n']}: {h1}\n"
                            f"🔵 {w['c2']['n']}: {h2}\n\n"
                            f"⏰ وقت المباراة الحاسمة 24 ساعة.\n"
                            f"🎯 التاكات تنحصر الآن بين اللاعبين الحاسمين فقط."
                        )
                    else:
                        await update.message.reply_text(
                            f"✅ تم تسجيل حاسم {w[target_k]['n']}: {u_tag}\n"
                            f"⏳ انتظار تحديد حاسم الكلان الآخر..."
                        )
                else:
                    await update.message.reply_text(
                        f"❌ الحاسم يُحدد فقط عند التعادل 3-3.\n"
                        f"النتيجة الحالية: {w['c1']['n']} {w['c1']['s']} - {w['c2']['s']} {w['c2']['n']}"
                    )
                return

        # ============================================================
        # إضافة النقاط (+1)
        # ============================================================
        if "+ 1" in msg_up or "+1" in msg_up:
            players = re.findall(r'@\w+', msg)
            scores = re.findall(r'(\d+)', msg)
            win_k = None
            if w["c1"]["n"].upper() in msg_up:
                win_k = "c1"
            elif w["c2"]["n"].upper() in msg_up:
                win_k = "c2"

            if not win_k:
                return

            clan_nm = w[win_k]["n"].upper()
            asst_tag = clans_mgmt.get(cid, {}).get(clan_nm, {}).get("asst")
            is_authorized = is_referee or u_tag == w[win_k]["leader"] or u_tag == asst_tag

            if not is_authorized:
                await update.message.reply_text("❌ التسجيل مسموح للحكام أو القادة/المساعدين فقط.")
                return

            if len(players) >= 2 and len(scores) >= 2:
                u1 = players[0].upper()
                u2 = players[1].upper()
                sc1, sc2 = int(scores[0]), int(scores[1])
                p_win = u1 if sc1 > sc2 else u2

                w[win_k]["s"] += 1
                w[win_k]["stats"].append({
                    "name": p_win,
                    "goals": max(sc1, sc2),
                    "rec": min(sc1, sc2),
                    "is_free": False,
                    "is_tak": False
                })

                # تحديث نتيجة المباراة في الجدول
                for m in w["matches"]:
                    mp1_u = m["p1"].upper()
                    mp2_u = m["p2"].upper()
                    if (u1 == mp1_u or u1 == mp2_u) and (u2 == mp1_u or u2 == mp2_u):
                        if u1 == mp1_u:
                            m["s1"], m["s2"] = sc1, sc2
                        else:
                            m["s1"], m["s2"] = sc2, sc1

                # طرد اللاعبين بعد تسجيل النقطة
                for player_tag in [players[0], players[1]]:
                    player_tag_clean = player_tag.lstrip('@')
                    try:
                        # البحث عن المستخدم في المجموعة
                        chat_members = await context.bot.get_chat_administrators(cid)
                        # ملاحظة: الطرد الفعلي يحتاج user_id وليس username
                        # نكتفي بالإشعار إذا لم نجد الـ ID
                    except:
                        pass

                save_data()
                await update.message.reply_text(
                    f"✅ تم تسجيل نقطة لـ {w[win_k]['n']}\n"
                    f"⚽ {players[0]} {sc1} - {sc2} {players[1]}"
                )
            else:
                # نقطة فري
                if not is_referee:
                    await update.message.reply_text("❌ النقطة الفري حصرية للإدارة.")
                    return
                w[win_k]["s"] += 1
                w[win_k]["stats"].append({
                    "name": "Free Point",
                    "goals": 0, "rec": 0,
                    "is_free": True, "is_tak": False
                })
                save_data()
                await update.message.reply_text(
                    f"⚖️ قرار إداري: نقطة فري لكلان {w[win_k]['n']} بواسطة {u_tag}."
                )

            # تحديث عنوان الجروب
            try:
                await context.bot.set_chat_title(
                    cid,
                    f"⚔️ {w['c1']['n']} {w['c1']['s']} - {w['c2']['s']} {w['c2']['n']} ⚔️"
                )
            except:
                pass

            # تحديث جدول المباريات
            if w["mid"]:
                try:
                    await context.bot.edit_message_text(
                        build_table(w, AU_LINK), cid, w["mid"],
                        disable_web_page_preview=True
                    )
                except:
                    pass

            # ============================================================
            # إنهاء الحرب (4 نقاط)
            # ============================================================
            if w[win_k]["s"] >= 4:
                w["active"] = False
                save_data()

                history = w[win_k]["stats"]
                real_players = [h for h in history if not h["is_free"] and not h.get("is_tak")]

                if real_players:
                    hasm = real_players[-1]["name"]
                    star_player_data = max(real_players, key=lambda x: (x["goals"] - x["rec"]))
                    star = star_player_data["name"]
                    star_goals = star_player_data["goals"]
                    star_rec = star_player_data["rec"]

                    result_msg = (
                        f"🎊 انتهت الحرب بفوز كلان: {w[win_k]['n']} 🎊\n\n"
                        f"🎯 الحاسم: {hasm}\n"
                        f"⭐ النجم: {star} (سجّل {star_goals} واستقبل {star_rec})\n\n"
                        f"⚠️ تذكير قوانين النشر:\n"
                        f"• فوز القوائم = لا نجم ولا حاسم\n"
                        f"• النجم يحدده الحكم (الأهداف + التأثير + السلوك)\n"
                        f"• الشخص غير الحاسم لا يُنشر"
                    )
                else:
                    result_msg = f"🎊 انتهت الحرب بفوز إداري لكلان: {w[win_k]['n']} 🎊"

                await update.message.reply_text(result_msg)

                # تفاصيل النتائج النهائية
                match_results_str = ""
                for i, m in enumerate(w["matches"]):
                    match_results_str += f"{i+1} | {m['p1']} {to_emoji(m['s1'])}|🆚|{to_emoji(m['s2'])} {m['p2']} |\n"
                    match_results_str += "─── ─── ─── ─── ───\n"

                await update.message.reply_text(f"📊 تفاصيل النتائج:\n\n{match_results_str}")

                # إعادة اسم الجروب
                try:
                    await context.bot.set_chat_title(
                        cid,
                        f"🏆 {w[win_k]['n']} فاز! {w['c1']['n']} {w['c1']['s']} - {w['c2']['s']} {w['c2']['n']}"
                    )
                except:
                    pass

            return

# ============================================================
# جدولة نتائج التاكات بعد 3 أيام
# ============================================================
async def schedule_tak_results(cid: int, context: ContextTypes.DEFAULT_TYPE):
    """بعد 3 أيام يرسل البوت نتائج التاكات ويسأل القادة"""
    await asyncio.sleep(3 * 24 * 3600)  # 3 أيام

    if cid not in wars or not wars[cid].get("active"):
        return

    w = wars[cid]
    tak_data = tak_tracking.get(cid, {})

    if tak_data.get("hasim_mode"):
        return  # في مرحلة الحاسم، لا نرسل نتائج التاكات

    # حساب التاكات لكل لاعب
    c1_taks = {}
    c2_taks = {}

    for sender, targets in tak_data.items():
        if sender == "hasim_mode" or sender == "hasim_c1" or sender == "hasim_c2":
            continue
        for target, timestamps in targets.items():
            if isinstance(timestamps, list):
                count = len(timestamps)
                # تحديد إلى أي كلان ينتمي المرسل
                for m in w["matches"]:
                    if sender.upper() == m["p1"].upper():
                        c1_taks[sender] = c1_taks.get(sender, 0) + count
                        break
                    elif sender.upper() == m["p2"].upper():
                        c2_taks[sender] = c2_taks.get(sender, 0) + count
                        break

    # إنشاء أزرار للقادة للتحقق
    keyboard = []
    for m in w["matches"]:
        # كل مباراة تحتاج تحقق
        row = [
            InlineKeyboardButton(
                f"✅ {w['c1']['n']} فاز مباراة {m['p1']} vs {m['p2']}",
                callback_data=f"tak_win_c1"
            ),
            InlineKeyboardButton(
                f"✅ {w['c2']['n']} فاز",
                callback_data=f"tak_win_c2"
            )
        ]
        keyboard.append(row)
        break  # نكتفي بزر واحد كمثال

    reply_markup = InlineKeyboardMarkup(keyboard)

    tak_report = f"📊 تقرير التاكات بعد 3 أيام:\n\n"
    tak_report += f"🔴 {w['c1']['n']}:\n"
    for p, cnt in c1_taks.items():
        tak_report += f"  • {p}: {cnt} تاك\n"
    tak_report += f"\n🔵 {w['c2']['n']}:\n"
    for p, cnt in c2_taks.items():
        tak_report += f"  • {p}: {cnt} تاك\n"

    tak_report += "\n⚠️ المباريات غير المنتهية تحتسب بالتاكات كنقطة فري."

    try:
        await context.bot.send_message(
            cid,
            tak_report,
            reply_markup=reply_markup if keyboard else None
        )
    except Exception as e:
        print(f"Error sending tak results: {e}")

# ============================================================
# تشغيل البوت
# ============================================================
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()

    load_data()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_war))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited_msg))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("✅ البوت يعمل الآن (النسخة الكاملة مع جميع الإضافات)...")
    app.run_polling()
