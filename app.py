#!/usr/bin/env python3
"""
DEMON DATING BOT - Main Application Entry Point
Library: pyTelegramBotAPI
"""

import os
import logging
import threading
import time
from datetime import datetime
import telebot
from telebot import types
from dotenv import load_dotenv

load_dotenv()

# Import database
from database import get_db

# Import handlers
from handlers.start import handle_start, handle_verify_callback, handle_continue_bot
from handlers.profile import (
    handle_create_profile, handle_name, handle_gender_callback,
    handle_age, handle_location, handle_location_text, handle_about,
    handle_media, handle_confirm_callback, handle_preference_callback,
    show_main_menu
)
from handlers.view_profiles import (
    handle_view_profiles, handle_like_callback, handle_skip_callback,
    handle_stop_callback, show_my_profile
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
    raise ValueError("❌ BOT_TOKEN not found!")

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='Markdown')

# Store user states (in production, use Redis or database)
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
    
    # Confirm callbacks
    elif data.startswith("confirm_"):
        handle_confirm_callback(bot, call, user_states, user_temp_data)
    
    # Preference callbacks
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
        show_my_profile(bot, call)
    
    elif data == "notifications":
        handle_notifications(bot, call)
    
    elif data.startswith("chat_"):
        handle_chat_callback(bot, call, user_states, user_temp_data)
    
    elif data == "cancel_chat":
        handle_cancel_chat(bot, call, user_states, user_temp_data)
    
    elif data == "main_menu":
        show_main_menu(bot, call.message.chat.id, None)
    
    else:
        bot.answer_callback_query(call.id, "Processing...")


# ========== MESSAGE HANDLERS ==========
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'location'])
def handle_messages(message):
    """Handle all text and media messages"""
    user_id = message.from_user.id
    state = user_states.get(user_id)
    
    logger.info(f"Message from user {user_id}, state: {state}")
    
    # Handle location
    if message.location:
        if state == "awaiting_location_coords":
            handle_location(bot, message, user_states, user_temp_data)
        else:
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
        
        elif text == "/done" and state == "awaiting_media":
            from handlers.profile import confirm_profile
            confirm_profile(bot, message, user_states, user_temp_data)
        
        else:
            bot.reply_to(message, "❌ Invalid command. Use /start to begin.")
    
    # Update last activity
    db = get_db()
    db.get_collection("users").update_one(
        {"user_id": user_id},
        {"$set": {"last_active": datetime.utcnow()}},
        upsert=True
    )


# ========== MAIN FUNCTION ==========
def main():
    """Main function to run the bot"""
    logger.info("🚀 DEMON DATING BOT - Starting up...")
    logger.info(f"📅 Startup time: {datetime.utcnow()}")
    logger.info(f"🤖 Bot username: @{bot.get_me().username}")
    
    # Clear pending updates
    bot.delete_webhook()
    
    # Start polling
    logger.info("🔥 DEMON CORE ONLINE - Bot is polling...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)


if __name__ == "__main__":
    main()
