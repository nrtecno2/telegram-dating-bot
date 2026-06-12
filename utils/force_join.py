import logging
import os
from telebot import TeleBot

logger = logging.getLogger(__name__)

# Channel username from environment
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@nrtecno2")
# Remove @ if present for API calls
CHANNEL_ID = CHANNEL_USERNAME.replace("@", "")


def check_channel_membership(bot: TeleBot, user_id: int) -> bool:
    """
    Check if a user is a member of the required channel
    Returns True if member, False otherwise
    """
    try:
        # Get chat member status
        chat_member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        status = chat_member.status
        
        # Member statuses that grant access
        allowed_statuses = ['member', 'administrator', 'creator']
        
        is_member = status in allowed_statuses
        
        if not is_member:
            logger.info(f"User {user_id} is not a member of {CHANNEL_USERNAME}. Status: {status}")
        
        return is_member
        
    except Exception as e:
        logger.error(f"Failed to check membership for user {user_id}: {e}")
        # If we can't verify, return False to be safe
        return False


def get_join_button():
    """Get inline keyboard button for channel join"""
    from telebot import types
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_join = types.InlineKeyboardButton(
        "📢 JOIN CHANNEL", 
        url=f"https://t.me/{CHANNEL_ID}"
    )
    btn_verify = types.InlineKeyboardButton(
        "✅ VERIFY MEMBERSHIP", 
        callback_data="verify"
    )
    markup.add(btn_join, btn_verify)
    
    return markup


def get_force_join_message():
    """Get force join message text"""
    return (
        "🔐 **ACCESS RESTRICTED** 🔐\n\n"
        "⚠️ You must join our official channel to use this bot!\n\n"
        "📌 **Steps to verify:**\n"
        "1️⃣ Tap the JOIN CHANNEL button below\n"
        f"2️⃣ Join {CHANNEL_USERNAME}\n"
        "3️⃣ Come back and tap VERIFY MEMBERSHIP\n\n"
        "⚡ Verification is instant and automatic.\n"
        "🔓 No verification = No access\n\n"
        "*This is to prevent spam and ensure quality users.*"
    )


def get_verification_success_message(user_name: str = None):
    """Get verification success message"""
    name_part = f" {user_name}!" if user_name else "!"
    return (
        "✅ **VERIFICATION SUCCESSFUL** ✅\n\n"
        f"Welcome{name_part}\n\n"
        "You have been verified as a channel member.\n"
        "Now you can access all bot features.\n\n"
        "🔓 Full access granted.\n"
        "🔥 Let's get started!"
    )


def get_verification_failed_message():
    """Get verification failed message"""
    return (
        "❌ **VERIFICATION FAILED** ❌\n\n"
        f"You are still not a member of {CHANNEL_USERNAME}.\n\n"
        "📌 Please follow these steps:\n"
        "1️⃣ Click JOIN CHANNEL below\n"
        "2️⃣ Join the channel\n"
        "3️⃣ Click VERIFY AGAIN\n\n"
        "⚡ After joining, verification is instant."
    )
