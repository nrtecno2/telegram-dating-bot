import logging
from datetime import datetime
from telebot import types
from database import get_db
from handlers.notifications import send_message_notification

logger = logging.getLogger(__name__)
db = get_db()

# Store active chat sessions
active_chats = {}


def start_chat_session(bot, message, user_id, target_id, target_name=None):
    """Start a chat session between two users"""
    if not target_name:
        target_profile = db.get_collection("profiles").find_one({"user_id": target_id})
        target_name = target_profile.get('name', 'User') if target_profile else 'User'
    
    # Store chat session
    active_chats[user_id] = {
        'target_id': target_id,
        'target_name': target_name,
        'chat_id': message.chat.id
    }
    
    # Show chat interface with bottom buttons
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_cancel = types.KeyboardButton("❌ CANCEL CHAT")
    btn_history = types.KeyboardButton("📜 VIEW HISTORY")
    markup.add(btn_cancel, btn_history)
    
    bot.reply_to(
        message,
        f"💬 **Chat with {target_name}** 💬\n\n"
        f"Send your message below.\n"
        f"Supports text, photos, and videos.\n\n"
        f"Press CANCEL CHAT to stop.",
        reply_markup=markup,
        parse_mode='Markdown'
    )


def handle_chat_message(bot, message, user_states, user_temp_data):
    """Handle incoming chat messages"""
    user_id = message.from_user.id
    chat_session = active_chats.get(user_id)
    
    if not chat_session:
        bot.reply_to(message, "❌ No active chat session. Use VIEW PROFILES to find matches.")
        return
    
    target_id = chat_session.get('target_id')
    target_name = chat_session.get('target_name')
    
    if not target_id:
        bot.reply_to(message, "❌ Chat session error. Please start over.")
        return
    
    # Process message based on type
    message_text = None
    media_file_id = None
    media_type = None
    
    if message.text:
        message_text = message.text.strip()
        # Check for cancel/history commands
        if message_text == "❌ CANCEL CHAT":
            handle_cancel_chat(bot, message, user_states, user_temp_data)
            return
        elif message_text == "📜 VIEW HISTORY":
            handle_get_conversation(bot, message, user_id, target_id, target_name)
            return
    elif message.photo:
        media_file_id = message.photo[-1].file_id
        media_type = 'photo'
        message_text = message.caption if message.caption else "📷 Sent a photo"
    elif message.video:
        media_file_id = message.video.file_id
        media_type = 'video'
        message_text = message.caption if message.caption else "🎥 Sent a video"
    else:
        bot.reply_to(message, "❌ Send text, photo, or video only!")
        return
    
    # Save message to database
    msg_data = {
        "from_user": user_id,
        "to_user": target_id,
        "message": message_text,
        "media_file_id": media_file_id,
        "media_type": media_type,
        "is_read": False,
        "created_at": datetime.utcnow()
    }
    db.get_collection("messages").insert_one(msg_data)
    
    # Send notification to target user
    try:
        notification = {
            "user_id": target_id,
            "type": "message",
            "from_user_id": user_id,
            "from_name": message.from_user.first_name,
            "message": message_text[:100],
            "is_read": False,
            "created_at": datetime.utcnow()
        }
        db.get_collection("notifications").insert_one(notification)
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
    
    # Send confirmation to sender
    bot.reply_to(
        message,
        f"✅ **Message sent to {target_name}!**\n\n"
        f"They will be notified when they're online."
    )


def handle_cancel_chat(bot, message, user_states, user_temp_data):
    """Cancel active chat session"""
    user_id = message.from_user.id
    
    # Clear chat session
    if user_id in active_chats:
        del active_chats[user_id]
    
    # Return to main menu with bottom buttons
    from handlers.profile import show_main_menu
    show_main_menu(bot, message.chat.id)


def handle_get_conversation(bot, message, user_id, target_id, target_name):
    """Get conversation history between two users"""
    # Get conversation history
    messages = list(db.get_collection("messages").find({
        "$or": [
            {"from_user": user_id, "to_user": target_id},
            {"from_user": target_id, "to_user": user_id}
        ]
    }).sort("created_at", -1).limit(50))
    
    if not messages:
        bot.reply_to(message, "📭 No conversation history yet!")
        return
    
    # Mark unread messages as read
    db.get_collection("messages").update_many(
        {"to_user": user_id, "from_user": target_id, "is_read": False},
        {"$set": {"is_read": True}}
    )
    
    # Build conversation text
    text = f"💬 **Conversation with {target_name}**\n\n"
    text += "─" * 30 + "\n\n"
    
    for msg in reversed(messages):
        sender = "You" if msg['from_user'] == user_id else target_name
        time_str = msg['created_at'].strftime("%H:%M")
        
        text += f"**{sender}** [{time_str}]: {msg['message']}\n"
        
        if msg.get('media_type'):
            text += f"_[{msg['media_type']} attached]_\n"
        
        text += "\n"
    
    if len(text) > 4000:
        text = text[:4000] + "\n\n... (truncated)"
    
    # Bottom buttons
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_back = types.KeyboardButton("🔙 BACK TO CHAT")
    btn_menu = types.KeyboardButton("🏠 MAIN MENU")
    markup.add(btn_back, btn_menu)
    
    bot.reply_to(message, text, reply_markup=markup, parse_mode='Markdown')


def handle_back_to_chat(bot, message, user_states, user_temp_data):
    """Handle back to chat button from conversation history"""
    user_id = message.from_user.id
    chat_session = active_chats.get(user_id)
    
    if not chat_session:
        bot.reply_to(message, "❌ No active chat session!")
        from handlers.profile import show_main_menu
        show_main_menu(bot, message.chat.id)
        return
    
    target_id = chat_session.get('target_id')
    target_name = chat_session.get('target_name')
    
    # Resume chat
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_cancel = types.KeyboardButton("❌ CANCEL CHAT")
    btn_history = types.KeyboardButton("📜 VIEW HISTORY")
    markup.add(btn_cancel, btn_history)
    
    bot.reply_to(
        message,
        f"💬 **Back to Chat with {target_name}** 💬\n\n"
        f"Send your message below.",
        reply_markup=markup,
        parse_mode='Markdown'
    )


def handle_chat_callback(bot, call, user_states, user_temp_data):
    """Handle chat button from inline keyboard (for backward compatibility)"""
    # Extract target_id from callback data
    try:
        target_id = int(call.data.split('_')[1])
    except:
        target_id = None
    
    if not target_id:
        bot.answer_callback_query(call.id, "Error: User not found!")
        return
    
    # Get target profile
    target_profile = db.get_collection("profiles").find_one({"user_id": target_id})
    if not target_profile:
        bot.answer_callback_query(call.id, "User not found!")
        return
    
    target_name = target_profile.get('name', 'User')
    user_id = call.from_user.id
    
    # Check if mutual match exists
    is_mutual = db.get_collection("likes").find_one({
        "$and": [
            {"from_user": user_id, "to_user": target_id, "is_mutual": True},
            {"from_user": target_id, "to_user": user_id, "is_mutual": True}
        ]
    })
    
    if not is_mutual:
        like1 = db.get_collection("likes").find_one({"from_user": user_id, "to_user": target_id})
        like2 = db.get_collection("likes").find_one({"from_user": target_id, "to_user": user_id})
        
        if not (like1 and like2):
            bot.answer_callback_query(call.id, "❌ You can only chat with mutual matches!", show_alert=True)
            return
    
    bot.answer_callback_query(call.id)
    
    # Create a dummy message object to work with
    class DummyMessage:
        def __init__(self, chat_id, from_user):
            self.chat = type('obj', (object,), {'id': chat_id})
            self.from_user = from_user
    
    dummy_message = DummyMessage(call.message.chat.id, call.from_user)
    
    start_chat_session(bot, dummy_message, user_id, target_id, target_name)


def get_unread_message_count(user_id):
    """Get count of unread messages for user"""
    return db.get_collection("messages").count_documents({
        "to_user": user_id,
        "is_read": False
    })


def mark_messages_as_read(user_id, from_user_id):
    """Mark messages from specific user as read"""
    result = db.get_collection("messages").update_many(
        {"to_user": user_id, "from_user": from_user_id, "is_read": False},
        {"$set": {"is_read": True}}
    )
    return result.modified_count
