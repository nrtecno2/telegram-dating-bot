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

# ---------- Flask app for Render Web Service ----------
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "✅ DEMON BOT IS RUNNING", 200

@flask_app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

# ---------- Database ----------
from database import get_db

# ---------- Handlers ----------
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
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------- Bot config ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not found!")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='Markdown')

# User state storage
user_states = {}
user_temp_data = {}


# ========== COMMAND HANDLERS ==========
@bot.message_handler(commands=['start'])
def start_cmd(message):
    handle_start(bot, message, user_states, user_temp_data)

@bot.message_handler(commands=['cancel'])
def cancel_cmd(message):
    user_id = message.from_user.id
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_temp_data:
        del user_temp_data[user_id]
    markup = types.ReplyKeyboardRemove()
    bot.reply_to(message, "❌ Cancelled. Use /start", reply_markup=markup)

@bot.message_handler(commands=['done'])
def done_cmd(message):
    handle_done(bot, message, user_states, user_temp_data)


# ========== BOTTOM BUTTON HANDLERS ==========
@bot.message_handler(func=lambda m: m.text == "📢 JOIN CHANNEL")
def channel_join(m):
    handle_channel_join(bot, m, user_temp_data)

@bot.message_handler(func=lambda m: m.text in ["✅ VERIFY MEMBERSHIP", "🔄 VERIFY AGAIN"])
def verify_member(m):
    handle_verify_membership(bot, m, user_states, user_temp_data)

@bot.message_handler(func=lambda m: m.text == "👤 MY PROFILE")
def my_profile(m):
    handle_my_profile(bot, m)

@bot.message_handler(func=lambda m: m.text == "👀 VIEW PROFILES")
def view_profiles(m):
    handle_view_profiles(bot, m, user_states, user_temp_data)

@bot.message_handler(func=lambda m: m.text == "🔔 NOTIFICATIONS")
def notifications(m):
    handle_notifications(bot, m)

@bot.message_handler(func=lambda m: m.text == "🎯 CHANGE INTEREST")
def change_interest(m):
    handle_change_interest(bot, m, user_states, user_temp_data)

@bot.message_handler(func=lambda m: m.text == "📊 STATS")
def stats(m):
    handle_stats(bot, m)

@bot.message_handler(func=lambda m: m.text == "⚙️ SETTINGS")
def settings(m):
    handle_settings(bot, m)

@bot.message_handler(func=lambda m: m.text in ["🏠 Main Menu", "🔙 BACK", "🔙 Back to Main Menu"])
def back_menu(m):
    show_main_menu(bot, m.chat.id)

@bot.message_handler(func=lambda m: m.text in ["👨 Male", "👩 Female", "👥 Both"])
def preference_or_interest(m):
    user_id = m.from_user.id
    state = user_states.get(user_id)
    if state == "awaiting_preference":
        handle_preference(bot, m, user_states, user_temp_data)
    elif state == "changing_interest":
        handle_update_interest(bot, m, user_states, user_temp_data)

@bot.message_handler(func=lambda m: m.text in ["✅ CONFIRM", "❌ CANCEL"])
def confirm_cancel(m):
    user_id = m.from_user.id
    state = user_states.get(user_id)
    if state == "awaiting_confirm":
        handle_confirm(bot, m, user_states, user_temp_data)

@bot.message_handler(func=lambda m: m.text == "❤️ LIKE")
def like_action(m):
    handle_like_action(bot, m, user_states, user_temp_data)

@bot.message_handler(func=lambda m: m.text == "⏭️ SKIP")
def skip_action(m):
    handle_skip_action(bot, m, user_states, user_temp_data)

@bot.message_handler(func=lambda m: m.text == "🛑 STOP")
def stop_action(m):
    handle_stop_viewing_action(bot, m, user_states, user_temp_data)

@bot.message_handler(func=lambda m: m.text == "🗑 DELETE ACCOUNT")
def delete_acc(m):
    handle_delete_account(bot, m)

@bot.message_handler(func=lambda m: m.text == "✅ CONFIRM DELETE")
def confirm_del(m):
    handle_confirm_delete(bot, m)


# ========== TEXT, MEDIA, LOCATION HANDLERS ==========
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video', 'location'])
def handle_all_messages(m):
    user_id = m.from_user.id
    state = user_states.get(user_id)

    # Location (live or manual)
    if m.location:
        if state == "awaiting_location":
            handle_location(bot, m, user_states, user_temp_data)
        return

    # Photo/Video
    if m.photo or m.video:
        if state == "awaiting_media":
            handle_media(bot, m, user_states, user_temp_data)
        else:
            bot.reply_to(m, "❌ Use /start to begin")
        return

    # Text
    if m.text:
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
            # ignore if already handled by button handlers
            pass

    # Update last activity
    try:
        db = get_db()
        db.get_collection("users").update_one(
            {"user_id": user_id},
            {"$set": {"last_active": datetime.utcnow()}},
            upsert=True
        )
    except Exception as e:
        logger.error(f"Update last_active failed: {e}")


# ========== FALLBACK HANDLER ==========
@bot.message_handler(func=lambda m: True)
def fallback(m):
    bot.reply_to(m, "❌ Use /start or use the buttons below")


# ========== MAIN FUNCTION ==========
def main():
    # Start Flask health check server in background
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(2)

    logger.info("🚀 DEMON DATING BOT STARTING...")
    logger.info(f"Time: {datetime.utcnow()}")

    try:
        bot_info = bot.get_me()
        logger.info(f"✅ Bot @{bot_info.username} is active")
    except Exception as e:
        logger.error(f"Bot connection error: {e}")
        return

    # Clear any existing webhook and start polling
    bot.delete_webhook()
    time.sleep(1)

    logger.info("🔥 BOT IS POLLING...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)


if __name__ == "__main__":
    main()
