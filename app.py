#!/usr/bin/env python3
"""
DEMON DATING BOT - Main Application Entry Point
Library: pyTelegramBotAPI
"""

import os
import logging
from datetime import datetime
import telebot
from telebot import types
from dotenv import load_dotenv

load_dotenv()

# Import database
from database import get_db

# Import handlers
from handlers.start import handle_start, handle_verify_callback, handle_continue_bot, handle_create_profile
from handlers.profile import (
    handle_name, handle_gender_callback, handle_age, handle_location,
    handle_location_text, handle_about, handle_media, handle_confirm_callback,
    handle_preference_callback, show_main_menu, handle_my_profile, handle_edit_profile
)
from handlers.view_profiles import (
    handle_view_profiles, handle_like_callback, handle_skip_callback,
    handle_stop_callback
)
from handlers.notifications import handle_notifications
from handlers.chat import handle_chat_callback, handle_chat_message, handle_cancel_chat

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not found in environment variables!")

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='Markdown')

# Store user states (in production, use Redis)
user_states = {}
user_temp_data = {}


# ========== COMMAND HANDLERS ==========
@bot.message_handler(commands=['start'])
def start_command(message):
    """Handle /start command"""
    handle_start(bot, message, user_states, user_temp_data)


@bot.message_handler(commands=['cancel'])
def cancel_command(message):
    """Handle /cancel command"""
    user_id = message.from_user.id
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_temp_data:
        del user_temp_data[user_id]
    bot.reply_to(message, "❌ Operation cancelled. Use /start to begin again.")


@bot.message_handler(commands=['done'])
def done_command(message):
    """Handle /done command for media completion"""
    user_id = message.from_user.id
    state = user_states.get(user_id)
    
    if state == "awaiting_media":
        from handlers.profile import confirm_profile
        confirm_profile(bot, message, user_states, user_temp_data)
    else:
        bot.reply_to(message, "❌ Nothing to complete.")


# ========== CALLBACK QUERY HANDLERS ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Handle all callback queries"""
    user_id = call.from_user.id
    data = call.data
    
    logger.info(f"Callback received: {data} from user {user_id}")
    
    # Verification callbacks
    if data == "verify":
        handle_verify_callback(bot, call, user_states, user_temp_data)
    
    elif data == "continue_bot":
        handle_continue_bot(bot, call, user_states, user_temp_data)
    
    elif data == "create_profile":
        handle_create_profile(bot, call, user_states, user_temp_data)
    
    # Gender callback
    elif data.startswith("gender_"):
        handle_gender_callback(bot, call, user_states, user_temp_data)
    
    # Confirm callbacks (confirm_yes, confirm_no)
    elif data.startswith("confirm_"):
        handle_confirm_callback(bot, call, user_states, user_temp_data)
    
    # Preference callbacks (pref_male, pref_female, pref_both)
    elif data.startswith("pref_"):
        handle_preference_callback(bot, call, user_states, user_temp_data)
    
    # Profile viewing callbacks
    elif data == "view_profiles":
        handle_view_profiles(bot, call, user_states, user_temp_data)
    
    elif data.startswith("like_"):
        handle_like_callback(bot, call, user_states, user_temp_data)
    
    elif data == "skip_profile":
        handle_skip_callback(bot, call, user_states, user_temp_data)
    
    elif data == "stop_viewing":
        handle_stop_callback(bot, call, user_states, user_temp_data)
    
    elif data == "my_profile":
        handle_my_profile(bot, call)
    
    elif data == "edit_profile":
        handle_edit_profile(bot, call, user_states, user_temp_data)
    
    elif data == "notifications":
        handle_notifications(bot, call)
    
    elif data.startswith("chat_"):
        handle_chat_callback(bot, call, user_states, user_temp_data)
    
    elif data == "cancel_chat":
        handle_cancel_chat(bot, call, user_states, user_temp_data)
    
    elif data == "main_menu":
        show_main_menu(bot, call.message.chat.id)
    
    else:
        bot.answer_callback_query(call.id, "Processing...", show_alert=False)


# ========== MESSAGE HANDLERS ==========
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'location'])
def handle_messages(message):
    """Handle all text, media, and location messages"""
    user_id = message.from_user.id
    state = user_states.get(user_id)
    
    logger.info(f"Message from user {user_id}, state: {state}")
    
    # Handle location
    if message.location:
        handle_location(bot, message, user_states, user_temp_data)
        return
    
    # Handle media (photos/videos)
    if message.photo or message.video:
        if state == "awaiting_media":
            handle_media(bot, message, user_states, user_temp_data)
        elif state == "awaiting_chat_message":
            handle_chat_message(bot, message, user_states, user_temp_data)
        else:
            bot.reply_to(message, "❌ Please use /start to begin.")
        return
    
    # Handle text messages
    if message.text:
        text = message.text.strip()
        
        # Profile creation states
        if state == "awaiting_name":
            handle_name(bot, message, user_states, user_temp_data)
        
        elif state == "awaiting_age":
            handle_age(bot, message, user_states, user_temp_data)
        
        elif state == "awaiting_location_text":
            handle_location_text(bot, message, user_states, user_temp_data)
        
        elif state == "awaiting_about":
            handle_about(bot, message, user_states, user_temp_data)
        
        elif state == "awaiting_chat_message":
            handle_chat_message(bot, message, user_states, user_temp_data)
        
        else:
            bot.reply_to(message, "❌ Invalid command. Use /start to begin.")
    
    # Update last activity
    try:
        db = get_db()
        db.get_collection("users").update_one(
            {"user_id": user_id},
            {"$set": {"last_active": datetime.utcnow()}},
            upsert=True
        )
    except Exception as e:
        logger.error(f"Failed to update last_active: {e}")


# ========== ERROR HANDLER ==========
@bot.message_handler(func=lambda message: True)
def fallback_handler(message):
    """Fallback handler for any unhandled messages"""
    bot.reply_to(message, "❌ I didn't understand that. Use /start to begin.")


# ========== MAIN FUNCTION ==========
def main():
    """Main function to run the bot"""
    logger.info("🚀 DEMON DATING BOT - Starting up...")
    logger.info(f"📅 Startup time: {datetime.utcnow()}")
    
    try:
        bot_info = bot.get_me()
        logger.info(f"🤖 Bot username: @{bot_info.username}")
    except Exception as e:
        logger.error(f"Failed to get bot info: {e}")
    
    # Clear webhook (using polling)
    bot.delete_webhook()
    
    # Start polling
    logger.info("🔥 DEMON CORE ONLINE - Bot is polling...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)


if __name__ == "__main__":
    main()
