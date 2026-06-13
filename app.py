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

# Flask app for health check (required for Render Web Service)
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

# Import database
from database import get_db

# Import handlers
from handlers.start import handle_start, handle_channel_join, handle_verify_membership
from handlers.profile import (
    handle_name, handle_gender_callback, handle_age, handle_location,
    handle_location_text, handle_about, handle_media, handle_confirm_callback,
    handle_preference_callback, show_main_menu, 
    handle_edit_profile, handle_edit_name, process_edit_name,
    handle_edit_age, process_edit_age, handle_edit_gender, process_edit_gender,
    handle_edit_location, process_edit_location, handle_edit_about, process_edit_about,
    handle_edit_media, process_edit_media, save_edited_profile, cancel_edit,
    handle_change_interest, handle_update_preference,
    handle_my_stats, handle_settings, handle_delete_account, handle_confirm_delete
)
from handlers.view_profiles import (
    handle_view_profiles, handle_like_action, handle_skip_action,
    handle_stop_viewing_action, handle_chat_from_profile, handle_my_profile,
    handle_refresh_profiles
)
from handlers.notifications import (
    handle_notifications, handle_view_user_from_notification,
    handle_like_from_notification, handle_reply_from_notification,
    handle_chat_from_notification, send_message_notification
)
from handlers.chat import (
    start_chat_session, handle_chat_message, handle_cancel_chat,
    handle_get_conversation, handle_back_to_chat, handle_chat_callback
)

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

# Store user states and temp data
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


# ========== BOTTOM BUTTON HANDLERS (ReplyKeyboardMarkup) ==========

# Channel verification buttons
@bot.message_handler(func=lambda message: message.text == "📢 JOIN CHANNEL")
def channel_join_handler(message):
    handle_channel_join(bot, message, user_temp_data)


@bot.message_handler(func=lambda message: message.text in ["✅ VERIFY MEMBERSHIP", "🔄 VERIFY AGAIN"])
def verify_membership_handler(message):
    handle_verify_membership(bot, message, user_states, user_temp_data)


# Main Menu Bottom Buttons
@bot.message_handler(func=lambda message: message.text == "👤 MY PROFILE")
def my_profile_handler(message):
    handle_my_profile(bot, message)


@bot.message_handler(func=lambda message: message.text == "👀 VIEW PROFILES")
def view_profiles_handler(message):
    handle_view_profiles(bot, message, user_states, user_temp_data)


@bot.message_handler(func=lambda message: message.text == "🔔 NOTIFICATIONS" or message.text.startswith("🔔 NOTIFICATIONS"))
def notifications_handler(message):
    handle_notifications(bot, message)


@bot.message_handler(func=lambda message: message.text == "🎯 CHANGE INTEREST")
def change_interest_handler(message):
    handle_change_interest(bot, message, user_states, user_temp_data)


@bot.message_handler(func=lambda message: message.text == "📊 MY STATS")
def my_stats_handler(message):
    handle_my_stats(bot, message)


@bot.message_handler(func=lambda message: message.text == "⚙️ SETTINGS")
def settings_handler(message):
    handle_settings(bot, message)


@bot.message_handler(func=lambda message: message.text in ["🏠 Main Menu", "🏠 MAIN MENU", "🔙 Back to Main Menu"])
def main_menu_handler(message):
    show_main_menu(bot, message.chat.id)


# Profile Creation Bottom Buttons
@bot.message_handler(func=lambda message: message.text in ["👨 Male", "👩 Female"])
def gender_selection_handler(message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    if state == "awaiting_gender":
        handle_gender_callback(bot, message, user_states, user_temp_data)
    elif state == "editing_profile":
        process_edit_gender(bot, message, user_states, user_temp_data)


@bot.message_handler(func=lambda message: message.text in ["👨 Male", "👩 Female", "👥 Both"])
def preference_selection_handler(message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    
    if state == "awaiting_preference":
        handle_preference_callback(bot, message, user_states, user_temp_data)
    elif state == "awaiting_interest_change":
        handle_update_preference(bot, message, user_states, user_temp_data)


@bot.message_handler(func=lambda message: message.text in ["✅ Confirm Profile", "❌ Cancel"])
def confirm_profile_handler(message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    if state == "awaiting_confirm":
        handle_confirm_callback(bot, message, user_states, user_temp_data)


# Profile Viewing Bottom Buttons
@bot.message_handler(func=lambda message: message.text == "❤️ LIKE")
def like_action_handler(message):
    handle_like_action(bot, message, user_states, user_temp_data)


@bot.message_handler(func=lambda message: message.text == "⏭️ SKIP")
def skip_action_handler(message):
    handle_skip_action(bot, message, user_states, user_temp_data)


@bot.message_handler(func=lambda message: message.text == "🛑 STOP VIEWING")
def stop_viewing_handler(message):
    handle_stop_viewing_action(bot, message, user_states, user_temp_data)


@bot.message_handler(func=lambda message: message.text == "💬 CHAT")
def chat_from_profile_handler(message):
    handle_chat_from_profile(bot, message, user_states, user_temp_data)


@bot.message_handler(func=lambda message: message.text == "🔄 Refresh")
def refresh_profiles_handler(message):
    handle_refresh_profiles(bot, message, user_states, user_temp_data)


# Profile Edit Bottom Buttons
@bot.message_handler(func=lambda message: message.text == "✏️ EDIT PROFILE")
def edit_profile_handler(message):
    handle_edit_profile(bot, message, user_states, user_temp_data)


@bot.message_handler(func=lambda message: message.text == "✏️ Edit Name")
def edit_name_handler(message):
    handle_edit_name(bot, message, user_states, user_temp_data)


@bot.message_handler(func=lambda message: message.text == "✏️ Edit Age")
def edit_age_handler(message):
    handle_edit_age(bot, message, user_states, user_temp_data)


@bot.message_handler(func=lambda message: message.text == "✏️ Edit Gender")
def edit_gender_handler(message):
    handle_edit_gender(bot, message, user_states, user_temp_data)


@bot.message_handler(func=lambda message: message.text == "✏️ Edit Location")
def edit_location_handler(message):
    handle_edit_location(bot, message, user_states, user_temp_data)


@bot.message_handler(func=lambda message: message.text == "✏️ Edit About")
def edit_about_handler(message):
    handle_edit_about(bot, message, user_states, user_temp_data)


@bot.message_handler(func=lambda message: message.text == "✏️ Edit Photos/Videos")
def edit_media_handler(message):
    handle_edit_media(bot, message, user_states, user_temp_data)


@bot.message_handler(func=lambda message: message.text == "💾 Save All Changes")
def save_edit_handler(message):
    save_edited_profile(bot, message, user_states, user_temp_data)


@bot.message_handler(func=lambda message: message.text == "❌ Cancel")
def cancel_edit_handler(message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    if state in ["editing_profile", "editing_name", "editing_age", "editing_gender", "editing_location", "editing_about", "editing_media"]:
        cancel_edit(bot, message, user_states, user_temp_data)
    else:
        cancel_command(message)


# Settings Bottom Buttons
@bot.message_handler(func=lambda message: message.text == "🗑 Delete Account")
def delete_account_handler(message):
    handle_delete_account(bot, message)


@bot.message_handler(func=lambda message: message.text == "🗑 Confirm Delete")
def confirm_delete_handler(message):
    handle_confirm_delete(bot, message)


# Notification Action Bottom Buttons
@bot.message_handler(func=lambda message: message.text.startswith("👤 View "))
def view_user_from_notification(message):
    handle_view_user_from_notification(bot, message, user_temp_data)


@bot.message_handler(func=lambda message: message.text.startswith("❤️ Like "))
def like_from_notification(message):
    handle_like_from_notification(bot, message, user_temp_data)


@bot.message_handler(func=lambda message: message.text.startswith("💬 Reply to "))
def reply_from_notification(message):
    handle_reply_from_notification(bot, message, user_temp_data)


@bot.message_handler(func=lambda message: message.text.startswith("💬 Chat with "))
def chat_from_notification(message):
    handle_chat_from_notification(bot, message, user_temp_data)


# Chat Bottom Buttons
@bot.message_handler(func=lambda message: message.text == "❌ CANCEL CHAT")
def cancel_chat_handler(message):
    handle_cancel_chat(bot, message, user_states, user_temp_data)


@bot.message_handler(func=lambda message: message.text == "📜 VIEW HISTORY")
def view_history_handler(message):
    user_id = message.from_user.id
    chat_session = None
    from handlers.chat import active_chats
    if user_id in active_chats:
        chat_session = active_chats[user_id]
    
    if chat_session:
        target_id = chat_session.get('target_id')
        target_name = chat_session.get('target_name')
        handle_get_conversation(bot, message, user_id, target_id, target_name)
    else:
        bot.reply_to(message, "❌ No active chat session!")


@bot.message_handler(func=lambda message: message.text == "🔙 BACK TO CHAT")
def back_to_chat_handler(message):
    handle_back_to_chat(bot, message, user_states, user_temp_data)


# ========== CALLBACK QUERY HANDLERS (for backward compatibility) ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Handle callback queries for inline keyboards"""
    user_id = call.from_user.id
    data = call.data
    logger.info(f"Callback received: {data} from user {user_id}")
    
    if data.startswith("chat_"):
        handle_chat_callback(bot, call, user_states, user_temp_data)
    else:
        bot.answer_callback_query(call.id, "Processing...", show_alert=False)


# ========== MESSAGE HANDLERS FOR PROFILE CREATION STATES ==========
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'location'])
def handle_all_messages(message):
    """Handle all messages based on user state"""
    user_id = message.from_user.id
    state = user_states.get(user_id)
    
    logger.info(f"Message from user {user_id}, state: {state}")
    
    # Handle location
    if message.location:
        if state == "awaiting_location":
            handle_location(bot, message, user_states, user_temp_data)
        return
    
    # Handle media (photos/videos)
    if message.photo or message.video:
        if state == "awaiting_media":
            handle_media(bot, message, user_states, user_temp_data)
        elif state == "awaiting_chat_message":
            handle_chat_message(bot, message, user_states, user_temp_data)
        elif state == "editing_media":
            process_edit_media(bot, message, user_states, user_temp_data)
        else:
            bot.reply_to(message, "❌ Please use /start to begin or use the buttons below.")
        return
    
    # Handle text messages
    if message.text:
        text = message.text.strip()
        
        # Profile creation states
        if state == "awaiting_name":
            handle_name(bot, message, user_states, user_temp_data)
        
        elif state == "awaiting_age":
            handle_age(bot, message, user_states, user_temp_data)
        
        elif state == "awaiting_location":
            handle_location_text(bot, message, user_states, user_temp_data)
        
        elif state == "awaiting_about":
            handle_about(bot, message, user_states, user_temp_data)
        
        elif state == "awaiting_chat_message":
            handle_chat_message(bot, message, user_states, user_temp_data)
        
        # Edit profile states
        elif state == "editing_name":
            process_edit_name(bot, message, user_states, user_temp_data)
        
        elif state == "editing_age":
            process_edit_age(bot, message, user_states, user_temp_data)
        
        elif state == "editing_location":
            process_edit_location(bot, message, user_states, user_temp_data)
        
        elif state == "editing_about":
            process_edit_about(bot, message, user_states, user_temp_data)
        
        # Skip if state is not set - these are handled by specific handlers above
        elif state is None:
            # Check if it's a main menu button that wasn't caught
            if text in ["👤 MY PROFILE", "👀 VIEW PROFILES", "🔔 NOTIFICATIONS", 
                       "🎯 CHANGE INTEREST", "📊 MY STATS", "⚙️ SETTINGS",
                       "🏠 Main Menu", "🏠 MAIN MENU", "🔙 Back to Main Menu"]:
                pass
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


# ========== FALLBACK HANDLER ==========
@bot.message_handler(func=lambda message: True)
def fallback_handler(message):
    """Fallback handler for any unhandled messages"""
    bot.reply_to(message, "❌ I didn't understand that. Use /start to begin or use the buttons below.")


# ========== MAIN FUNCTION ==========
def main():
    """Main function to run the bot"""
    # Start Flask in background thread for health check (Render Web Service requirement)
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    time.sleep(2)
    
    logger.info("🚀 DEMON DATING BOT - Starting up...")
    logger.info(f"📅 Startup time: {datetime.utcnow()}")
    
    # Retry bot connection with error handling
    max_retries = 3
    for attempt in range(max_retries):
        try:
            bot_info = bot.get_me()
            logger.info(f"🤖 Bot username: @{bot_info.username}")
            break
        except Exception as e:
            logger.error(f"Attempt {attempt + 1}/{max_retries} - Failed to get bot info: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                logger.error("Could not connect to Telegram API after multiple attempts")
                return
    
    # Clear webhook and start polling
    try:
        bot.delete_webhook()
        time.sleep(1)
        bot.remove_webhook()
        time.sleep(1)
    except Exception as e:
        logger.warning(f"Webhook cleanup warning: {e}")
    
    logger.info("🔥 DEMON CORE ONLINE - Bot is polling...")
    
    # Start polling with error recovery
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            logger.info("Restarting polling in 10 seconds...")
            time.sleep(10)


if __name__ == "__main__":
    main()
