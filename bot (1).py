# -*- coding: utf-8 -*-
import json
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler,
    CallbackContext, MessageHandler, Filters
)

TOKEN = "8652179755:AAHIDbbPgfJg4PwMbEA_mpNtblcxZRpUyn0"
DATA_FILE = "questions_data.json"

# ─── Monetag Ad Config ────────────────────────────────────────────────────────
# WebApp URL-ləri — bu HTML səhifələr show_10878049() çağırır və nəticəni
# Telegram-a postMessage ilə göndərir. Öz domeninizdə yerləşdirin.
AD_WEBAPP_REWARDED_URL   = "https://ibrahimibrahimliei-spec.github.io/adsgram-bot/ad_rewarded.html"
AD_WEBAPP_INTERSTITIAL_URL = "https://ibrahimibrahimliei-spec.github.io/adsgram-bot/ad_interstitial.html"

AD_EVERY_N_QUESTIONS = 5   # hər 5 sualdan bir aralıq reklam

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load questions
with open(DATA_FILE, 'r', encoding='utf-8') as f:
    DATA = json.load(f)

TOPICS = DATA['topics']
ALL_QUESTIONS = DATA['all_questions']

# User session storage
user_sessions = {}

# ─── Reklam göstər ────────────────────────────────────────────────────────────

def show_rewarded_ad(chat_id, context: CallbackContext, after_ad_callback: str):
    """
    Giriş reklamı (Rewarded Interstitial / Popup).
    İstifadəçi reklamı izləyir → 'Davam et' basır → test açılır.
    WebApp-da show_10878049() və ya show_10878049('pop') çağırılır.
    """
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "📢 Reklamı izlə (Testə başla)",
            web_app=WebAppInfo(url=AD_WEBAPP_REWARDED_URL)
        )],
        [InlineKeyboardButton("▶️ Reklamı izlədim, testi başlat", callback_data=after_ad_callback)]
    ])
    context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🎯 *Testə başlamaq üçün qısa reklam izləyin*\n\n"
            "1️⃣ \"Reklamı izlə\" düyməsinə basın\n"
            "2️⃣ Reklam bitdikdən sonra geri qayıdın\n"
            "3️⃣ \"Testi başlat\" düyməsinə basın"
        ),
        parse_mode='Markdown',
        reply_markup=keyboard
    )


def show_interstitial_ad(chat_id, context: CallbackContext, after_ad_callback: str):
    """
    Aralıq reklam (hər 5 sualdan bir).
    WebApp-da show_10878049({ type:'inApp', ... }) çağırılır.
    5 saniyə gözlədikdən sonra avtomatik bağlanır.
    """
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "⏱ Reklam izlə (5 san)",
            web_app=WebAppInfo(url=AD_WEBAPP_INTERSTITIAL_URL)
        )],
        [InlineKeyboardButton("▶️ Davam et", callback_data=after_ad_callback)]
    ])
    context.bot.send_message(
        chat_id=chat_id,
        text=(
            "📢 *Qısa fasilə — 5 saniyelik reklam*\n\n"
            "Reklamı izlədikdən sonra testə davam edə bilərsiniz."
        ),
        parse_mode='Markdown',
        reply_markup=keyboard
    )

# ─── /start ───────────────────────────────────────────────────────────────────

def start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    # Giriş reklamı: test açılmadan əvvəl
    show_rewarded_ad(chat_id, context, after_ad_callback="ad_done_start")

def show_main_menu(chat_id, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("📚 Mövzuya görə sınaq", callback_data="menu_topic")],
        [InlineKeyboardButton("🎲 Ümumi sınaq", callback_data="menu_general")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🛡 *Mülki Müdafiə Test Botu*\n\n"
            "Sınaq növünü seçin:"
        ),
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

# ─── CALLBACK ROUTER ──────────────────────────────────────────────────────────

def callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data
    chat_id = query.message.chat_id

    # ── Giriş reklamı bitdi → menü aç ──
    if data == "ad_done_start":
        try:
            query.message.delete()
        except:
            pass
        show_main_menu(chat_id, context)

    # ── Aralıq reklam bitdi → növbəti sual ──
    elif data == "ad_done_continue":
        try:
            query.message.delete()
        except:
            pass
        send_next_question(chat_id, context)

    elif data == "menu_topic":
        show_topic_menu(query, context)
    elif data == "menu_general":
        ask_question_count(query, context)
    elif data.startswith("topic_"):
        topic_idx = int(data.split("_")[1])
        start_topic_quiz(query, context, topic_idx)
    elif data.startswith("count_"):
        count = int(data.split("_")[1])
        start_general_quiz(query, context, count)
    elif data.startswith("ans_"):
        handle_answer(query, context)

    # ── Növbəti sual düyməsi ──
    elif data == "next":
        session = user_sessions.get(chat_id, {})
        current = session.get('current', 0)
        # Hər AD_EVERY_N_QUESTIONS sualdan bir aralıq reklam göstər
        if current > 0 and current % AD_EVERY_N_QUESTIONS == 0:
            try:
                query.message.delete()
            except:
                pass
            show_interstitial_ad(chat_id, context, after_ad_callback="ad_done_continue")
        else:
            send_next_question(chat_id, context, query.message.message_id)

    elif data == "finish":
        show_result(chat_id, context, edit_message_id=query.message.message_id)
    elif data == "restart":
        try:
            query.message.delete()
        except:
            pass
        show_main_menu(chat_id, context)

# ─── TOPIC MENU ───────────────────────────────────────────────────────────────

def show_topic_menu(query, context: CallbackContext):
    keyboard = []
    for i, topic in enumerate(TOPICS):
        q_count = len(topic['questions'])
        btn = InlineKeyboardButton(
            f"📖 Mövzu {topic['num']}: {topic['name'][:35]}... ({q_count} sual)",
            callback_data=f"topic_{i}"
        )
        keyboard.append([btn])
    keyboard.append([InlineKeyboardButton("⬅️ Geri", callback_data="restart")])

    query.edit_message_text(
        text="📚 *Mövzu seçin:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ─── GENERAL QUIZ - ASK COUNT ─────────────────────────────────────────────────

def ask_question_count(query, context: CallbackContext):
    keyboard = [
        [
            InlineKeyboardButton("5", callback_data="count_5"),
            InlineKeyboardButton("10", callback_data="count_10"),
            InlineKeyboardButton("20", callback_data="count_20"),
        ],
        [
            InlineKeyboardButton("30", callback_data="count_30"),
            InlineKeyboardButton("50", callback_data="count_50"),
            InlineKeyboardButton("Hamısı (352)", callback_data="count_352"),
        ],
        [InlineKeyboardButton("⬅️ Geri", callback_data="restart")],
    ]
    query.edit_message_text(
        text="🎲 *Ümumi sınaq*\n\nNeçə sual istəyirsiniz?",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ─── START TOPIC QUIZ ─────────────────────────────────────────────────────────

def start_topic_quiz(query, context: CallbackContext, topic_idx: int):
    chat_id = query.message.chat_id
    topic = TOPICS[topic_idx]
    questions = topic['questions'].copy()
    random.shuffle(questions)

    user_sessions[chat_id] = {
        'questions': questions,
        'current': 0,
        'score': 0,
        'wrong': 0,
        'mode': 'topic',
        'topic_name': f"Mövzu {topic['num']}: {topic['name']}"
    }
    try:
        query.message.delete()
    except:
        pass
    send_next_question(chat_id, context)

# ─── START GENERAL QUIZ ───────────────────────────────────────────────────────

def start_general_quiz(query, context: CallbackContext, count: int):
    chat_id = query.message.chat_id
    questions = ALL_QUESTIONS.copy()
    random.shuffle(questions)
    questions = questions[:count]

    user_sessions[chat_id] = {
        'questions': questions,
        'current': 0,
        'score': 0,
        'wrong': 0,
        'mode': 'general',
        'topic_name': 'Ümumi Sınaq'
    }
    try:
        query.message.delete()
    except:
        pass
    send_next_question(chat_id, context)

# ─── SEND QUESTION ────────────────────────────────────────────────────────────

def send_next_question(chat_id, context: CallbackContext, prev_msg_id=None):
    session = user_sessions.get(chat_id)
    if not session:
        show_main_menu(chat_id, context)
        return

    idx = session['current']
    total = len(session['questions'])

    if idx >= total:
        show_result(chat_id, context)
        return

    q = session['questions'][idx]
    answers = q['answers'].copy()
    random.shuffle(answers)
    session['shuffled_answers'] = answers

    labels = ['🅰', '🅱', '🇨', '🇩', '🇪']
    keyboard = []
    for i, ans in enumerate(answers):
        label = labels[i] if i < len(labels) else f"{i+1}."
        short = ans[:40] + ('…' if len(ans) > 40 else '')
        keyboard.append([InlineKeyboardButton(
            f"{label} {short}", callback_data=f"ans_{i}"
        )])

    progress = f"❓ Sual {idx+1}/{total}"
    score_line = f"✅ {session['score']}  ❌ {session['wrong']}"

    options_text = "\n".join(
        f"{labels[i] if i < len(labels) else str(i+1)} {ans}"
        for i, ans in enumerate(answers)
    )

    text = (
        f"{progress}  |  {score_line}\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"*{q['q']}*\n\n"
        f"{options_text}"
    )

    context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ─── HANDLE ANSWER ────────────────────────────────────────────────────────────

def handle_answer(query, context: CallbackContext):
    chat_id = query.message.chat_id
    session = user_sessions.get(chat_id)
    if not session:
        return

    idx = session['current']
    q = session['questions'][idx]
    chosen_idx = int(query.data.split("_")[1])
    answers = session.get('shuffled_answers', q['answers'])
    chosen = answers[chosen_idx]
    correct = q['correct']

    labels = ['🅰', '🅱', '🇨', '🇩', '🇪']
    if chosen == correct:
        session['score'] += 1
        result_icon = "✅"
        result_text = "Düzgün cavab!"
    else:
        session['wrong'] += 1
        result_icon = "❌"
        result_text = f"Səhv cavab!\n✅ Düzgün: *{correct}*"

    session['current'] += 1
    total = len(session['questions'])
    remaining = total - session['current']

    if session['current'] >= total:
        nav_btn = InlineKeyboardButton("📊 Nəticə", callback_data="finish")
    else:
        nav_btn = InlineKeyboardButton(f"▶️ Növbəti sual ({remaining} qaldı)", callback_data="next")

    keyboard = InlineKeyboardMarkup([[nav_btn]])

    options_text = "\n".join(
        f"{labels[i] if i < len(labels) else str(i+1)} {ans}"
        for i, ans in enumerate(answers)
    )

    progress = f"❓ Sual {idx+1}/{total}"
    score_line = f"✅ {session['score']}  ❌ {session['wrong']}"

    text = (
        f"{progress}  |  {score_line}\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"*{q['q']}*\n\n"
        f"{options_text}\n\n"
        f"{result_icon} *{result_text}*"
    )

    query.edit_message_text(
        text=text,
        parse_mode='Markdown',
        reply_markup=keyboard
    )

# ─── SHOW RESULT ──────────────────────────────────────────────────────────────

def show_result(chat_id, context: CallbackContext, edit_message_id=None):
    session = user_sessions.get(chat_id, {})
    score = session.get('score', 0)
    wrong = session.get('wrong', 0)
    total = len(session.get('questions', []))
    topic_name = session.get('topic_name', '')

    if total == 0:
        pct = 0
    else:
        pct = round(score / total * 100)

    if pct >= 90:
        grade = "🏆 Əla!"
    elif pct >= 75:
        grade = "👍 Yaxşı"
    elif pct >= 50:
        grade = "😐 Orta"
    else:
        grade = "😞 Zəif"

    bar_filled = round(pct / 10)
    bar = "🟩" * bar_filled + "⬜" * (10 - bar_filled)

    text = (
        f"📊 *Sınaq Nəticəsi*\n"
        f"📖 {topic_name}\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"✅ Düzgün: *{score}*\n"
        f"❌ Səhv: *{wrong}*\n"
        f"📝 Cəmi: *{total}*\n\n"
        f"{bar}\n"
        f"Nəticə: *{pct}%* — {grade}"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Yenidən başla", callback_data="restart")]
    ])

    context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode='Markdown',
        reply_markup=keyboard
    )

    if chat_id in user_sessions:
        del user_sessions[chat_id]

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(callback_handler))

    updater.start_polling()
    logging.info("Bot işə düşdü...")
    updater.idle()

if __name__ == '__main__':
    main()
