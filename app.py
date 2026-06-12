#!/usr/bin/env python3
"""
DEMON DATING BOT - Main Application Entry Point
Telegram Dating & Friendship Bot with Location-Based Matching
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler
)

# Load environment variables
load_dotenv()

# Import handlers
from handlers.start import (
    start,
    verify_callback,
    continue_bot,
    create_profile_callback,
    show_stats,
    my_profile_callback,
    settings_callback
)
from handlers.profile import (
    create_profile_start,
    get_name,
    get_gender,
    get_age,
    get_location,
    get_location_coords,
    get_about,
    get_media,
    confirm_profile,
    save_profile,
    set_preference,
    show_main_menu,
    edit_profile_start,
    edit_name,
    edit_age,
    edit_location,
    edit_about,
    edit_media,
    save_edited_profile,
    delete_account
)
from handlers.view_profiles import (
    view_profiles,
    like_profile,
    skip_profile,
    stop_viewing,
    show_profile,
    show_my_profile
)
from handlers.notifications import view_notifications
from handlers.chat import (
    send_message_start,
    handle_message,
    cancel_chat,
    get_conversation
)

# Import states
from utils.states import (
    NAME, GENDER, AGE, LOCATION, LOCATION_COORDS, ABOUT, MEDIA, CONFIRM, PREFERENCE,
    EDIT_NAME, EDIT_AGE, EDIT_LOCATION, EDIT_ABOUT, EDIT_MEDIA, EDIT_CONFIRM,
    TYPING_MESSAGE
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

# Database check
from database import get_db
try:
    db = get_db()
    logger.info("✅ Database connection established")
except Exception as e:
    logger.error(f"❌ Database connection failed: {e}")
    raise


def setup_handlers(app: Application) -> None:
    """Setup all handlers for the bot"""
    
    # ========== PROFILE CREATION CONVERSATION ==========
    profile_conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", create_profile_start),
            CallbackQueryHandler(create_profile_callback, pattern="^create_profile$")
        ],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GENDER: [CallbackQueryHandler(get_gender, pattern="^gender_")],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_location)],
            LOCATION_COORDS: [
                MessageHandler(filters.LOCATION, get_location_coords),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_location_coords)
            ],
            ABOUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_about),
                CommandHandler("skip", get_about)
            ],
            MEDIA: [
                MessageHandler(filters.PHOTO | filters.VIDEO, get_media),
                CommandHandler("done", confirm_profile)
            ],
            CONFIRM: [CallbackQueryHandler(save_profile, pattern="^confirm_")],
            PREFERENCE: [CallbackQueryHandler(set_preference, pattern="^pref_")],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_chat),
            CallbackQueryHandler(cancel_chat, pattern="^cancel$")
        ],
        allow_reentry=True,
        name="profile_creation"
    )
    
    # ========== EDIT PROFILE CONVERSATION ==========
    edit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_profile_start, pattern="^edit_profile$")],
        states={
            EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_name)],
            EDIT_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_age)],
            EDIT_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_location)],
            EDIT_ABOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_about)],
            EDIT_MEDIA: [
                MessageHandler(filters.PHOTO | filters.VIDEO, edit_media),
                CommandHandler("done", save_edited_profile)
            ],
            EDIT_CONFIRM: [CallbackQueryHandler(save_edited_profile, pattern="^edit_confirm_")]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_chat),
            CallbackQueryHandler(show_main_menu, pattern="^main_menu$")
        ],
        allow_reentry=True,
        name="profile_edit"
    )
    
    # ========== CHAT CONVERSATION ==========
    chat_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(send_message_start, pattern="^chat_")],
        states={
            TYPING_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_chat, pattern="^cancel_chat$"),
            CommandHandler("cancel", cancel_chat)
        ],
        allow_reentry=True,
        name="chat_session"
    )
    
    # ========== BASIC COMMANDS ==========
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel_chat))
    
    # ========== CONVERSATION HANDLERS ==========
    app.add_handler(profile_conv)
    app.add_handler(edit_conv)
    app.add_handler(chat_conv)
    
    # ========== CALLBACK QUERY HANDLERS ==========
    # Verification
    app.add_handler(CallbackQueryHandler(verify_callback, pattern="^verify$"))
    app.add_handler(CallbackQueryHandler(continue_bot, pattern="^continue_bot$"))
    
    # Main menu
    app.add_handler(CallbackQueryHandler(view_profiles, pattern="^view_profiles$"))
    app.add_handler(CallbackQueryHandler(view_notifications, pattern="^notifications$"))
    app.add_handler(CallbackQueryHandler(show_my_profile, pattern="^my_profile$"))
    app.add_handler(CallbackQueryHandler(show_stats, pattern="^show_stats$"))
    app.add_handler(CallbackQueryHandler(settings_callback, pattern="^settings$"))
    app.add_handler(CallbackQueryHandler(show_main_menu, pattern="^main_menu$"))
    
    # Profile viewing actions
    app.add_handler(CallbackQueryHandler(like_profile, pattern="^like_"))
    app.add_handler(CallbackQueryHandler(skip_profile, pattern="^skip_profile$"))
    app.add_handler(CallbackQueryHandler(stop_viewing, pattern="^stop_viewing$"))
    
    # Profile viewing navigation
    app.add_handler(CallbackQueryHandler(view_profiles, pattern="^refresh_profiles$"))
    
    # Chat actions
    app.add_handler(CallbackQueryHandler(get_conversation, pattern="^get_conversation_"))
    
    # Account actions
    app.add_handler(CallbackQueryHandler(delete_account, pattern="^delete_account$"))
    app.add_handler(CallbackQueryHandler(delete_account, pattern="^confirm_delete_"))
    
    # Preference
    app.add_handler(CallbackQueryHandler(set_preference, pattern="^set_preference$"))
    
    # View user profile from notification
    app.add_handler(CallbackQueryHandler(show_profile, pattern="^view_user_"))
    
    # ========== MESSAGE HANDLERS ==========
    # Handle location for edit profile
    app.add_handler(MessageHandler(filters.LOCATION, get_location_coords))
    
    logger.info("✅ All handlers registered successfully")


def error_handler(update: Update, context) -> None:
    """Handle errors in the bot"""
    logger.error(f"Update {update} caused error {context.error}")
    
    # Send error message to user if possible
    if update and update.effective_message:
        update.effective_message.reply_text(
            "❌ **System Error**\n\n"
            "An unexpected error occurred. Please try again later.\n\n"
            "If the problem persists, contact support.",
            parse_mode='Markdown'
        )


def main() -> None:
    """Main function to run the bot"""
    logger.info("🚀 DEMON DATING BOT - Starting up...")
    logger.info(f"📅 Startup time: {datetime.utcnow()}")
    
    try:
        # Create application
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Setup handlers
        setup_handlers(app)
        
        # Add error handler
        app.add_error_handler(error_handler)
        
        # Log startup success
        logger.info("✅ Bot configuration complete")
        logger.info("🔥 DEMON CORE ONLINE - Bot is running")
        
        # Start polling
        app.run_polling(
            allowed_updates=["message", "callback_query", "chat_member"],
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
