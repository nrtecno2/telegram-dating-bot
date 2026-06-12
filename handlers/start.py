import logging
from telebot import types
from database import get_db
from utils.force_join import check_channel_membership

logger = logging.getLogger(__name__)
db = get_db()


def handle_start(bot, message, user_states, user_temp_data):
    """Handle /start command"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    logger.info(f"User {user_id} ({user_name}) started the bot")
    
    # Check if user has profile
    existing_profile = db.get_collection("profiles").find_one({"user_id": user_id})
    existing_user = db.get_collection("users").find_one({"user_id": user_id})
    
    # Check channel membership
    is_member = check_channel_membership(bot, user_id)
    
    if not is_member:
        # Force join keyboard
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_join = types.InlineKeyboardButton("📢 JOIN CHANNEL", url="https://t.me/nrtecno2")
        btn_verify = types.InlineKeyboardButton("✅ VERIFY MEMBERSHIP", callback_data="verify")
        markup.add(btn_join, btn_verify)
        
        bot.reply_to(
            message,
            "🔐 **ACCESS RESTRICTED** 🔐\n\n"
            "⚠️ You must join our official channel to use this bot!\n\n"
            "📌 **Steps to verify:**\n"
            "1️⃣ Tap the JOIN CHANNEL button below\n"
            "2️⃣ Join @nrtecno2\n"
            "3️⃣ Come back and tap VERIFY MEMBERSHIP\n\n"
            "⚡ Verification is instant and automatic.\n"
            "🔓 No verification = No access\n\n"
            "*This is to prevent spam and ensure quality users.*",
            reply_markup=markup
        )
        return
    
    # User verified, check profile status
    if existing_profile and existing_user and existing_user.get('setup_complete', False):
        show_main_menu(bot, message.chat.id)
    else:
        # Start profile creation
        start_profile_creation(bot, message, user_states, user_temp_data, user_name)


def show_main_menu(bot, chat_id):
    """Show main menu for verified users"""
    # Get user stats for menu
    user_id = chat_id  # In this context, chat_id is user_id
    likes_received = db.get_collection("likes").count_documents({"to_user": user_id})
    unread_notifications = db.get_collection("notifications").count_documents(
        {"user_id": user_id, "is_read": False}
    )
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_profile = types.InlineKeyboardButton("👤 MY PROFILE", callback_data="my_profile")
    btn_view = types.InlineKeyboardButton("👀 VIEW PROFILES 🔥", callback_data="view_profiles")
    btn_notify = types.InlineKeyboardButton(f"🔔 NOTIFICATIONS ({unread_notifications})", callback_data="notifications")
    btn_stats = types.InlineKeyboardButton("📊 STATS", callback_data="show_stats")
    markup.add(btn_profile, btn_view, btn_notify, btn_stats)
    
    bot.send_message(
        chat_id,
        f"⚡ **DEMON DATING SYSTEM** ⚡\n\n"
        f"Welcome back!\n\n"
        f"📊 Your Stats:\n"
        f"├ ❤️ Likes Received: {likes_received}\n"
        f"├ 🔔 Unread: {unread_notifications}\n"
        f"└ 🎯 Status: Active\n\n"
        f"🔥 Select an option below:",
        reply_markup=markup
    )


def start_profile_creation(bot, message, user_states, user_temp_data, user_name):
    """Start profile creation process for new user"""
    user_id = message.from_user.id
    
    # Initialize state and temp data
    user_states[user_id] = "awaiting_name"
    user_temp_data[user_id] = {}
    
    markup = types.InlineKeyboardMarkup()
    btn_start = types.InlineKeyboardButton("🚀 START NOW", callback_data="create_profile")
    markup.add(btn_start)
    
    bot.send_message(
        message.chat.id,
        f"🌟 **WELCOME {user_name.upper()}!** 🌟\n\n"
        f"✅ You've successfully verified channel membership.\n\n"
        f"📝 **Let's create your dating profile!**\n\n"
        f"Here's what we need:\n"
        f"├ ✅ Your Name\n"
        f"├ ✅ Gender (Male/Female)\n"
        f"├ ✅ Age (18-100)\n"
        f"├ ✅ Location\n"
        f"├ ✅ About You (max 500 chars)\n"
        f"└ ✅ 1-3 Photos/Videos\n\n"
        f"⚡ This will take less than 2 minutes!\n"
        f"🔒 All data is private and secure.\n\n"
        f"Ready to find your match? 🔥",
        reply_markup=markup
    )


def handle_verify_callback(bot, call, user_states, user_temp_data):
    """Handle verify button callback"""
    user_id = call.from_user.id
    
    bot.answer_callback_query(call.id)
    
    # Re-check channel membership
    is_member = check_channel_membership(bot, user_id)
    
    if is_member:
        # Verification successful
        markup = types.InlineKeyboardMarkup()
        btn_continue = types.InlineKeyboardButton("🚀 CONTINUE TO BOT", callback_data="continue_bot")
        markup.add(btn_continue)
        
        bot.edit_message_text(
            "✅ **VERIFICATION SUCCESSFUL!** ✅\n\n"
            f"Welcome {call.from_user.first_name}!\n\n"
            "You have been verified as a channel member.\n"
            "Now you can access all bot features.\n\n"
            "🔓 Full access granted.\n"
            "🔥 Let's get started!",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
    else:
        # Still not a member
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_join = types.InlineKeyboardButton("📢 JOIN CHANNEL", url="https://t.me/nrtecno2")
        btn_verify = types.InlineKeyboardButton("🔄 VERIFY AGAIN", callback_data="verify")
        markup.add(btn_join, btn_verify)
        
        bot.edit_message_text(
            "❌ **VERIFICATION FAILED** ❌\n\n"
            "You are still not a member of @nrtecno2.\n\n"
            "📌 Please follow these steps:\n"
            "1️⃣ Click JOIN CHANNEL below\n"
            "2️⃣ Join the channel\n"
            "3️⃣ Click VERIFY AGAIN\n\n"
            "⚡ After joining, verification is instant.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )


def handle_continue_bot(bot, call, user_states, user_temp_data):
    """Handle continue button after verification"""
    user_id = call.from_user.id
    
    bot.answer_callback_query(call.id)
    
    # Check if profile exists
    existing_profile = db.get_collection("profiles").find_one({"user_id": user_id})
    
    if existing_profile:
        show_main_menu(bot, call.message.chat.id)
    else:
        handle_create_profile(bot, call, user_states, user_temp_data)


def handle_create_profile(bot, call, user_states, user_temp_data):
    """Start profile creation from callback"""
    user_id = call.from_user.id
    
    bot.answer_callback_query(call.id)
    
    # Set state
    user_states[user_id] = "awaiting_name"
    user_temp_data[user_id] = {}
    
    bot.edit_message_text(
        "🌟 **Let's create your profile!** 🌟\n\n"
        "Please send your **Name**:\n\n"
        "(Min 2 characters, Max 50 characters)",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )


def handle_my_profile(bot, call):
    """Handle my profile button - defined here but will be expanded in profile.py"""
    bot.answer_callback_query(call.id)
    # This will be implemented in profile.py
    # Temporary response
    bot.edit_message_text(
        "👤 **Your Profile**\n\nUse /start to access your profile.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )
