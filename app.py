#!/usr/bin/env python3
import os
import logging
import threading
import time
from datetime import datetime
from flask import Flask
import telebot
from telebot import types
from dotenv import load_dotenv

load_dotenv()

# ---------- Flask Health Check ----------
flask_app = Flask(__name__)

@flask_app.route('/')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

# ---------- Database ----------
from database import get_db

# ---------- Handlers (all your functions) ----------
from handlers.start import handle_start, handle_channel_join, handle_verify_membership
from handlers.profile import (
    handle_name, handle_gender_selection, handle_age, handle_location,
    handle_location_text, handle_about, handle_media, handle_done,
    handle_confirm, handle_preference, show_main_menu,
    handle_my_profile, handle_change_interest, handle_update_interest,
    handle_stats, handle_settings, handle_delete_account, handle_confirm_delete
)
from handlers.view_profiles import (
    handle_view_profiles, handle_like_action, handle_skip_action, handle_stop_viewing_action
)
from handlers.notifications import handle_notifications
from handlers.chat import handle_chat_message, handle_cancel_chat

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- Bot ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='Markdown')
user_states = {}
user_temp_data = {}

# ---------- Commands ----------
@bot.message_handler(commands=['start'])
def start_cmd(m):
    handle_start(bot, m, user_states, user_temp_data)

@bot.message_handler(commands=['cancel'])
def cancel_cmd(m):
    uid = m.from_user.id
    user_states.pop(uid, None)
    user_temp_data.pop(uid, None)
    bot.reply_to(m, "❌ Cancelled", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(commands=['done'])
def done_cmd(m):
    handle_done(bot, m, user_states, user_temp_data)

# ---------- Button handlers ----------
@bot.message_handler(func=lambda m: m.text == "📢 JOIN CHANNEL")
def ch_join(m):
    handle_channel_join(bot, m, user_temp_data)

@bot.message_handler(func=lambda m: m.text in ["✅ VERIFY MEMBERSHIP", "🔄 VERIFY AGAIN"])
def ch_verify(m):
    handle_verify_membership(bot, m, user_states, user_temp_data)

@bot.message_handler(func=lambda m: m.text == "👤 MY PROFILE")
def my_prof(m):
    handle_my_profile(bot, m)

@bot.message_handler(func=lambda m: m.text == "👀 VIEW PROFILES")
def view_prof(m):
    handle_view_profiles(bot, m, user_states, user_temp_data)

@bot.message_handler(func=lambda m: m.text == "🔔 NOTIFICATIONS")
def notif(m):
    handle_notifications(bot, m)

@bot.message_handler(func=lambda m: m.text == "🎯 CHANGE INTEREST")
def ch_int(m):
    handle_change_interest(bot, m, user_states, user_temp_data)

@bot.message_handler(func=lambda m: m.text == "📊 STATS")
def stats(m):
    handle_stats(bot, m)

@bot.message_handler(func=lambda m: m.text == "⚙️ SETTINGS")
def settings(m):
    handle_settings(bot, m)

@bot.message_handler(func=lambda m: m.text in ["🏠 Main Menu", "🔙 BACK"])
def back(m):
    show_main_menu(bot, m.chat.id)

@bot.message_handler(func=lambda m: m.text in ["👨 Male", "👩 Female", "👥 Both"])
def pref_int(m):
    uid = m.from_user.id
    state = user_states.get(uid)
    if state == "awaiting_preference":
        handle_preference(bot, m, user_states, user_temp_data)
    elif state == "changing_interest":
        handle_update_interest(bot, m, user_states, user_temp_data)

@bot.message_handler(func=lambda m: m.text in ["✅ CONFIRM", "❌ CANCEL"])
def conf_cancel(m):
    if user_states.get(m.from_user.id) == "awaiting_confirm":
        handle_confirm(bot, m, user_states, user_temp_data)

@bot.message_handler(func=lambda m: m.text == "❤️ LIKE")
def like(m):
    handle_like_action(bot, m, user_states, user_temp_data)

@bot.message_handler(func=lambda m: m.text == "⏭️ SKIP")
def skip(m):
    handle_skip_action(bot, m, user_states, user_temp_data)

@bot.message_handler(func=lambda m: m.text == "🛑 STOP")
def stop(m):
    handle_stop_viewing_action(bot, m, user_states, user_temp_data)

@bot.message_handler(func=lambda m: m.text == "🗑 DELETE ACCOUNT")
def del_acc(m):
    handle_delete_account(bot, m)

@bot.message_handler(func=lambda m: m.text == "✅ CONFIRM DELETE")
def confirm_del(m):
    handle_confirm_delete(bot, m)

# ---------- Media / Location / Text ----------
@bot.message_handler(content_types=['location'])
def location_handler(m):
    if user_states.get(m.from_user.id) == "awaiting_location":
        handle_location(bot, m, user_states, user_temp_data)

@bot.message_handler(content_types=['photo', 'video'])
def media_handler(m):
    if user_states.get(m.from_user.id) == "awaiting_media":
        handle_media(bot, m, user_states, user_temp_data)
    else:
        bot.reply_to(m, "❌ Use /start")

@bot.message_handler(func=lambda m: True, content_types=['text'])
def text_handler(m):
    uid = m.from_user.id
    state = user_states.get(uid)
    text = m.text.strip()

    if state == "awaiting_name":
        handle_name(bot, m, user_states, user_temp_data)
    elif state == "awaiting_gender":
        handle_gender_selection(bot, m, user_states, user_temp_data)
    elif state == "awaiting_age":
        handle_age(bot, m, user_states, user_temp_data)
    elif state == "awaiting_location":
        handle_location_text(bot, m, user_states, user_temp_data)
    elif state == "awaiting_about":
        handle_about(bot, m, user_states, user_temp_data)
    else:
        # update last active
        try:
            db = get_db()
            db.get_collection("users").update_one(
                {"user_id": uid},
                {"$set": {"last_active": datetime.utcnow()}},
                upsert=True
            )
        except:
            pass

# ---------- Main ----------
def main():
    # Start Flask in background
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(1)

    logger.info("🚀 Starting bot...")
    try:
        logger.info(f"✅ Bot @{bot.get_me().username}")
    except Exception as e:
        logger.error(f"Telegram error: {e}")
        return

    bot.delete_webhook()
    logger.info("🔥 Polling...")
    bot.infinity_polling(timeout=60)

if __name__ == "__main__":
    main()
