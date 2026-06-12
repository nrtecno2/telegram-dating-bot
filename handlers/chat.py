import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime
from database import get_db

logger = logging.getLogger(__name__)

# States for chat conversation
TYPING_MESSAGE = 1

db = get_db()

async def send_message_start(update: Update, context: ContextTypes.DEFAULT_TYPE, target_user_id: int, target_name: str):
    """Start a chat conversation with a user"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['chat_target_id'] = target_user_id
    context.user_data['chat_target_name'] = target_name
    
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_chat")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"💬 **Chat with {target_name}**\n\n"
        f"Send your message below.\n"
        f"Press Cancel to stop.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return TYPING_MESSAGE

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming chat messages"""
    user_id = update.effective_user.id
    message_text = update.message.text
    
    target_user_id = context.user_data.get('chat_target_id')
    target_name = context.user_data.get('chat_target_name')
    
    if not target_user_id:
        await update.message.reply_text("⚠️ Chat session expired. Start again.")
        return ConversationHandler.END
    
    # Save message to database
    chat_data = {
        "from_user": user_id,
        "to_user": target_user_id,
        "message": message_text,
        "is_read": False,
        "created_at": datetime.utcnow(),
        "message_type": "text"
    }
    db.get_collection("messages").insert_one(chat_data)
    
    # Create notification for target user
    notification = {
        "user_id": target_user_id,
        "type": "message",
        "from_user": user_id,
        "from_name": update.effective_user.first_name,
        "message_preview": message_text[:50],
        "is_read": False,
        "created_at": datetime.utcnow()
    }
    db.get_collection("notifications").insert_one(notification)
    
    # Send confirmation to sender
    keyboard = [[InlineKeyboardButton("✅ View Profile", callback_data=f"view_user_{target_user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ **Message sent to {target_name}!**\n\n"
        f"They will be notified.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return ConversationHandler.END

async def cancel_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel chat session"""
    query = update.callback_query
    await query.answer()
    
    context.user_data.pop('chat_target_id', None)
    context.user_data.pop('chat_target_name', None)
    
    await query.edit_message_text("❌ Chat session cancelled.")
    return ConversationHandler.END

async def get_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE, other_user_id: int):
    """Get conversation history between two users"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Get all messages between users
    messages = db.get_collection("messages").find({
        "$or": [
            {"from_user": user_id, "to_user": other_user_id},
            {"from_user": other_user_id, "to_user": user_id}
        ]
    }).sort("created_at", -1).limit(50)
    
    if not messages:
        await query.edit_message_text("📭 No conversation history yet.")
        return
    
    # Mark messages as read
    db.get_collection("messages").update_many(
        {"to_user": user_id, "from_user": other_user_id, "is_read": False},
        {"$set": {"is_read": True}}
    )
    
    conversation_text = "💬 **Conversation History**\n\n"
    messages_list = list(messages)
    
    for msg in reversed(messages_list):
        sender = "You" if msg['from_user'] == user_id else "Them"
        conversation_text += f"**{sender}:** {msg['message']}\n"
    
    keyboard = [[InlineKeyboardButton("✏️ Send New Message", callback_data=f"chat_{other_user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        conversation_text[:4000],  # Telegram limit
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
