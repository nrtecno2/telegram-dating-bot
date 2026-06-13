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

# Flask app for health check
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "✅ DEMON BOT IS RUNNING", 200

@flask_app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.getenv("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

# Database
from database import get_db

# Handlers
from handlers.start import handle_start, handle_channel_join, handle_verify_membership
from handlers.profile import (
    handle_name, handle_gender_callback, handle_age, handle_location,
    handle_location_text, handle_about, handle_media, confirm_profile,
    handle_confirm_callback, handle_preference_callback, show_main_menu,
    handle_my_profile, handle_change_interest, handle_update_interest,
    handle_stats, handle_settings, handle_delete_account, handle_confirm_delete
)
from handlers.view_profiles import (
    handle_view_profiles, handle_like, handle_skip, handle_stop
)
from handlers.notifications import handle_notifications
from handlers.chat import handle_chat_message, handle_cancel_chat

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot config
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not found!")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='Markdown')

# User data storage
user_states = {}
user_temp_data = {}


# ========== COMMANDS ==========
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
    bot.reply_to(message, "❌ Cancelled. Use /start")

@bot.message_handler(commands=['done'])
def done_cmd(message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    if state == "awaiting_media":
        confirm_profile(bot, message, user_states, user_temp_data)
    else:
        bot.reply_to(message, "❌ Nothing to complete")


# ========== BOTTOM BUTTON HANDLERS ==========
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
def ch_interest(m):
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
def pref_interest(m):
    user_id = m.from_user.id
    state = user_states.get(user_id)
    if state == "awaiting_preference":
        handle_preference_callback(bot, m, user_states, user_temp_data)
    elif state == "changing_interest":
        handle_update_interest(bot, m, user_states, user_temp_data)

@bot.message_handler(func=lambda m: m.text in ["✅ Confirm", "❌ Cancel"])
def confirm_action(m):
    user_id = m.from_user.id
    state = user_states.get(user_id)
    if state == "awaiting_confirm":
        handle_confirm_callback(bot, m, user_states, user_temp_data)
    elif m.text == "❌ Cancel" and state == "awaiting_media":
        cancel_cmd(m)

@bot.message_handler(func=lambda m: m.text == "❤️ LIKE")
def like_action(m):
    handle_like(bot, m, user_states, user_temp_data)

@bot.message_handler(func=lambda m: m.text == "⏭️ SKIP")
def skip_action(m):
    handle_skip(bot, m, user_states, user_temp_data)

@bot.message_handler(func=lambda m: m.text == "🛑 STOP")
def stop_action(m):
    handle_stop(bot, m, user_states, user_temp_data)

@bot.message_handler(func=lambda m: m.text == "🗑 DELETE ACCOUNT")
def del_acc(m):
    handle_delete_account(bot, m)

@bot.message_handler(func=lambda m: m.text == "✅ CONFIRM DELETE")
def confirm_del(m):
    handle_confirm_delete(bot, m)


# ========== TEXT, MEDIA, LOCATION HANDLERS ==========
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video', 'location'])
def all_messages(m):
    user_id = m.from_user.id
    state = user_states.get(user_id)

    # Location
    if m.location:
        if state == "awaiting_location":
            handle_location(bot, m, user_states, user_temp_data)
        return

    # Media
    if m.photo or m.video:
        if state == "awaiting_media":
            handle_media(bot, m, user_states, user_temp_data)
        else:
            bot.reply_to(m, "❌ Send /start to begin")
        return

    # Text
    if m.text:
        text = m.text.strip()

        if state == "awaiting_name":
            handle_name(bot, m, user_states, user_temp_data)
        elif state == "awaiting_age":
            handle_age(bot, m, user_states, user_temp_data)
        elif state == "awaiting_location":
            handle_location_text(bot, m, user_states, user_temp_data)
        elif state == "awaiting_about":
            handle_about(bot, m, user_states, user_temp_data)
        else:
            # Ignore if already handled by button handlers
            pass

    # Update last active
    try:
        db = get_db()
        db.get_collection("users").update_one(
            {"user_id": user_id},
            {"$set": {"last_active": datetime.utcnow()}},
            upsert=True
        )
    except:
        pass


@bot.message_handler(func=lambda m: True)
def fallback(m):
    bot.reply_to(m, "❌ Use /start or buttons below")


# ========== MAIN ==========
def main():
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(1)

    logger.info("🚀 DEMON BOT STARTING...")
    logger.info(f"Time: {datetime.utcnow()}")

    try:
        bot_info = bot.get_me()
        logger.info(f"✅ Bot: @{bot_info.username}")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        return

    bot.delete_webhook()
    time.sleep(1)

    logger.info("🔥 POLLING STARTED")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)


if __name__ == "__main__":
    main()
