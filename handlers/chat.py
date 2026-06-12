import logging
from datetime import datetime
from telebot import types
from database import get_db
from handlers.notifications import send_message_notification

logger = logging.getLogger(__name__)
db = get_db()

# Store active chat sessions
active_chats = {}


def handle_chat_callback(bot, call, user_states, user_temp_data):
    """Handle chat button callback - start a chat session"""
    user_id = call.from_user.id
    target_id = int(call.data.split('_')[1])
    
    bot.answer_callback_query(call.id)
    
    # Get target profile
    target_profile = db.get_collection("profiles").find_one({"user_id": target_id})
    if not target_profile:
        bot.edit_message_text(
            "❌ User not found!",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        return
    
    target_name = target_profile.get('name', 'User')
    
    # Check if mutual match exists
    is_mutual = db.get_collection("likes").find_one({
        "$and": [
            {"from_user": user_id, "to_user": target_id, "is_mutual": True},
            {"from_user": target_id, "to_user": user_id, "is_mutual": True}
        ]
    })
    
    if not is_mutual:
        # Check if they have liked each other
        like1 = db.get_collection("likes").find_one({"from_user": user_id, "to_user": target_id})
        like2 = db.get_collection("likes").find_one({"from_user": target_id, "to_user": user_id})
        
        if like1 and like2:
            is_mutual = True
        else:
            # Not mutual match - cannot chat
            markup = types.InlineKeyboardMarkup()
            btn_like = types.InlineKeyboardButton("❤️ Like First", callback_data=f"like_{target_id}")
            btn_back = types.InlineKeyboardButton("🔙 Back", callback_data="view_profiles")
            markup.add(btn_like, btn_back)
            
            bot.edit_message_text(
                f"💬 **Cannot Chat with {target_name}**\n\n"
                f"You can only chat with mutual matches.\n\n"
                f"💡 Tip: Like each other first to start chatting!",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
            return
    
    # Store chat session
    active_chats[user_id] = {
        'target_id': target_id,
        'target_name': target_name,
        'chat_id': call.message.chat.id,
        'message_id': call.message.message_id
    }
    
    # Set user state
    user_states[user_id] = "awaiting_chat_message"
    user_temp_data[user_id] = {'chat_target': target_id, 'chat_target_name': target_name}
    
    # Show chat interface
    markup = types.InlineKeyboardMarkup()
    btn_cancel = types.InlineKeyboardButton("❌ Cancel Chat", callback_data="cancel_chat")
    btn_history = types.InlineKeyboardButton("📜 View History", callback_data=f"get_conversation_{target_id}")
    markup.add(btn_cancel, btn_history)
    
    bot.edit_message_text(
        f"💬 **Chat with {target_name}** 💬\n\n"
        f"Send your message below.\n"
        f"Supports text, photos, and videos.\n\n"
        f"Press Cancel to stop chatting.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )


def handle_chat_message(bot, message, user_states, user_temp_data):
    """Handle incoming chat messages"""
    user_id = message.from_user.id
    chat_data = user_temp_data.get(user_id, {})
    target_id = chat_data.get('chat_target')
    target_name = chat_data.get('chat_target_name')
    
    if not target_id:
        bot.reply_to(message, "❌ No active chat session. Use /start to begin.")
        if user_id in user_states:
            del user_states[user_id]
        return
    
    # Process message based on type
    message_text = None
    media_file_id = None
    media_type = None
    
    if message.text:
        message_text = message.text.strip()
    elif message.photo:
        media_file_id = message.photo[-1].file_id
        media_type = 'photo'
        message_text = message.caption if message.caption else "📷 Sent a photo"
    elif message.video:
        media_file_id = message.video.file_id
        media_type = 'video'
        message_text = message.caption if message.caption else "🎥 Sent a video"
    else:
        bot.reply_to(message, "❌ Unsupported message type. Send text, photo, or video.")
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
        send_message_notification(
            bot, target_id, user_id, 
            message.from_user.first_name, 
            message_text[:100]
        )
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
    
    # Send confirmation to sender
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("🔙 Continue Chatting", callback_data=f"chat_{target_id}")
    btn_menu = types.InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
    markup.add(btn_back, btn_menu)
    
    bot.reply_to(
        message,
        f"✅ **Message sent to {target_name}!**\n\n"
        f"They will be notified when they're online.",
        reply_markup=markup
    )


def handle_cancel_chat(bot, call, user_states, user_temp_data):
    """Cancel active chat session"""
    user_id = call.from_user.id
    
    bot.answer_callback_query(call.id)
    
    # Clear chat session
    if user_id in active_chats:
        del active_chats[user_id]
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_temp_data:
        del user_temp_data[user_id]
    
    # Return to main menu
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_profile = types.InlineKeyboardButton("👤 MY PROFILE", callback_data="my_profile")
    btn_view = types.InlineKeyboardButton("👀 VIEW PROFILES", callback_data="view_profiles")
    btn_notify = types.InlineKeyboardButton("🔔 NOTIFICATIONS", callback_data="notifications")
    markup.add(btn_profile, btn_view, btn_notify)
    
    bot.edit_message_text(
        "❌ **Chat cancelled**\n\n"
        "Returning to main menu...",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )


def get_conversation(bot, call, user_states, user_temp_data):
    """Get conversation history between two users"""
    user_id = call.from_user.id
    target_id = int(call.data.split('_')[2])  # format: get_conversation_12345
    
    bot.answer_callback_query(call.id)
    
    # Get conversation history
    messages = list(db.get_collection("messages").find({
        "$or": [
            {"from_user": user_id, "to_user": target_id},
            {"from_user": target_id, "to_user": user_id}
        ]
    }).sort("created_at", -1).limit(50))
    
    if not messages:
        bot.answer_callback_query(call.id, "No conversation history yet!", show_alert=True)
        return
    
    # Mark unread messages as read
    db.get_collection("messages").update_many(
        {"to_user": user_id, "from_user": target_id, "is_read": False},
        {"$set": {"is_read": True}}
    )
    
    # Build conversation text
    target_profile = db.get_collection("profiles").find_one({"user_id": target_id})
    target_name = target_profile.get('name', 'User') if target_profile else 'User'
    
    text = f"💬 **Conversation with {target_name}**\n\n"
    
    for msg in reversed(messages):
        sender = "You" if msg['from_user'] == user_id else target_name
        time_str = msg['created_at'].strftime("%H:%M")
        
        text += f"**{sender}** [{time_str}]: {msg['message']}\n"
        
        if msg.get('media_type'):
            text += f"_[{msg['media_type']} attached]_\n"
        
        text += "\n"
    
    if len(text) > 4000:
        text = text[:4000] + "\n\n... (truncated)"
    
    # Add reply button
    markup = types.InlineKeyboardMarkup()
    btn_reply = types.InlineKeyboardButton("✏️ Send Message", callback_data=f"chat_{target_id}")
    btn_back = types.InlineKeyboardButton("🔙 Back to Chat", callback_data=f"chat_{target_id}")
    markup.add(btn_reply, btn_back)
    
    bot.edit_message_text(
        text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )


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
