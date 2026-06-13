import logging
from telebot import types
from database import get_db
from utils.force_join import check_channel_membership
from handlers.profile import show_main_menu

logger = logging.getLogger(__name__)
db = get_db()

# Global dict to store temporary data (will be set from app.py)
user_temp_data = {}


def handle_start(bot, message, user_states, user_temp_data_global):
    """Handle /start command"""
    global user_temp_data
    user_temp_data = user_temp_data_global
    
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    logger.info(f"User {user_id} ({user_name}) started the bot")
    
    # Check if user has profile
    existing_profile = db.get_collection("profiles").find_one({"user_id": user_id})
    existing_user = db.get_collection("users").find_one({"user_id": user_id})
    
    # Check channel membership
    is_member = check_channel_membership(bot, user_id)
    
    if not is_member:
        # Force join keyboard - bottom buttons
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        btn_join = types.KeyboardButton("📢 JOIN CHANNEL")
        btn_verify = types.KeyboardButton("✅ VERIFY MEMBERSHIP")
        markup.add(btn_join, btn_verify)
        
        # Store channel URL for join button handling
        user_temp_data[user_id] = {'awaiting_verification': True}
        
        bot.reply_to(
            message,
            "🔐 **ACCESS RESTRICTED** 🔐\n\n"
            "⚠️ You must join our official channel to use this bot!\n\n"
            "📌 **Steps to verify:**\n"
            "1️⃣ Tap JOIN CHANNEL button below\n"
            "2️⃣ Join @nrtecno2\n"
            "3️⃣ Come back and tap VERIFY MEMBERSHIP\n\n"
            "⚡ Verification is instant and automatic.\n"
            "🔓 No verification = No access",
            reply_markup=markup
        )
        return
    
    # User verified, check profile status
    if existing_profile and existing_user and existing_user.get('setup_complete', False):
        show_main_menu(bot, message.chat.id)
    else:
        # Start profile creation
        start_profile_creation(bot, message, user_states, user_temp_data)


def handle_channel_join(bot, message, user_temp_data_global):
    """Handle JOIN CHANNEL button click"""
    user_id = message.from_user.id
    
    # Send channel invite link
    markup = types.InlineKeyboardMarkup()
    btn_join = types.InlineKeyboardButton("📢 Join @nrtecno2", url="https://t.me/nrtecno2")
    markup.add(btn_join)
    
    bot.reply_to(
        message,
        "🔗 **Join our channel:**\n\n"
        "1. Click the link below\n"
        "2. Join the channel\n"
        "3. Come back and tap VERIFY MEMBERSHIP",
        reply_markup=markup
    )


def handle_verify_membership(bot, message, user_states, user_temp_data_global):
    """Handle VERIFY MEMBERSHIP button click"""
    global user_temp_data
    user_temp_data = user_temp_data_global
    
    user_id = message.from_user.id
    
    # Check membership again
    is_member = check_channel_membership(bot, user_id)
    
    if is_member:
        # Check if user has profile
        existing_profile = db.get_collection("profiles").find_one({"user_id": user_id})
        
        if existing_profile:
            # User has profile, show main menu
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            btn_profile = types.KeyboardButton("👤 MY PROFILE")
            btn_view = types.KeyboardButton("👀 VIEW PROFILES")
            btn_notify = types.KeyboardButton("🔔 NOTIFICATIONS")
            btn_interest = types.KeyboardButton("🎯 CHANGE INTEREST")
            btn_stats = types.KeyboardButton("📊 MY STATS")
            markup.add(btn_profile, btn_view, btn_notify, btn_interest, btn_stats)
            
            bot.reply_to(
                message,
                "✅ **VERIFICATION SUCCESSFUL!** ✅\n\n"
                f"Welcome back {message.from_user.first_name}!\n\n"
                "You are now verified. Choose an option below:",
                reply_markup=markup
            )
        else:
            # New user, start profile creation
            start_profile_creation(bot, message, user_states, user_temp_data)
    else:
        # Still not a member
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        btn_join = types.KeyboardButton("📢 JOIN CHANNEL")
        btn_verify = types.KeyboardButton("🔄 VERIFY AGAIN")
        markup.add(btn_join, btn_verify)
        
        bot.reply_to(
            message,
            "❌ **VERIFICATION FAILED** ❌\n\n"
            "You are still not a member of @nrtecno2.\n\n"
            "📌 Please follow these steps:\n"
            "1️⃣ Tap JOIN CHANNEL\n"
            "2️⃣ Join the channel\n"
            "3️⃣ Tap VERIFY AGAIN",
            reply_markup=markup
        )


def start_profile_creation(bot, message, user_states, user_temp_data_global):
    """Start profile creation process"""
    global user_temp_data
    user_temp_data = user_temp_data_global
    
    user_id = message.from_user.id
    
    # Initialize state and temp data
    user_states[user_id] = "awaiting_name"
    user_temp_data[user_id] = {}
    
    markup = types.ReplyKeyboardRemove()
    
    bot.reply_to(
        message,
        f"🌟 **WELCOME {message.from_user.first_name.upper()}!** 🌟\n\n"
        f"✅ You've successfully verified channel membership.\n\n"
        f"📝 **Let's create your dating profile!**\n\n"
        f"Here's what we need:\n"
        f"├ ✅ Your Name\n"
        f"├ ✅ Gender (Male/Female)\n"
        f"├ ✅ Age (18-100)\n"
        f"├ ✅ Location (Optional - for nearby matches)\n"
        f"├ ✅ About You (max 500 chars)\n"
        f"└ ✅ 1-3 Photos/Videos\n\n"
        f"⚡ This will take less than 2 minutes!\n"
        f"🔒 All data is private and secure.\n\n"
        f"Please send your **Name**:\n"
        f"(Min 2 characters, Max 50 characters)",
        reply_markup=markup
    )


def handle_continue_bot(bot, message, user_states, user_temp_data_global):
    """Handle continue after verification"""
    global user_temp_data
    user_temp_data = user_temp_data_global
    
    user_id = message.from_user.id
    
    # Check if profile exists
    existing_profile = db.get_collection("profiles").find_one({"user_id": user_id})
    
    if existing_profile:
        show_main_menu(bot, message.chat.id)
    else:
        start_profile_creation(bot, message, user_states, user_temp_data)


def handle_create_profile(bot, message, user_states, user_temp_data_global):
    """Handle create profile button"""
    global user_temp_data
    user_temp_data = user_temp_data_global
    
    start_profile_creation(bot, message, user_states, user_temp_data)


def handle_main_menu_button(bot, message):
    """Handle main menu button from anywhere"""
    from handlers.profile import show_main_menu
    show_main_menu(bot, message.chat.id)
