import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
from database import get_db

logger = logging.getLogger(__name__)

db = get_db()

async def view_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all unread notifications for user"""
    query = update.callback_query
    user_id = update.effective_user.id if update.effective_user else update.message.from_user.id
    
    if query:
        await query.answer()
    
    # Get unread notifications
    notifications = list(db.get_collection("notifications").find({
        "user_id": user_id,
        "is_read": False
    }).sort("created_at", -1))
    
    if not notifications:
        msg = "🔔 **No new notifications**\n\nYou're all caught up!"
        if query:
            await query.edit_message_text(msg, parse_mode='Markdown')
        else:
            await update.message.reply_text(msg, parse_mode='Markdown')
        return
    
    # Mark as read
    db.get_collection("notifications").update_many(
        {"user_id": user_id, "is_read": False},
        {"$set": {"is_read": True}}
    )
    
    # Build notification message
    message = f"🔔 **{len(notifications)} New Notification(s)**\n\n"
    keyboard = []
    
    for notif in notifications:
        notif_type = notif['type']
        
        if notif_type == 'like':
            message += f"❤️ **{notif['from_name']} liked your profile!**\n"
            keyboard.append([InlineKeyboardButton(
                f"👤 View {notif['from_name']}", 
                callback_data=f"view_user_{notif['from_user']}"
            )])
            
        elif notif_type == 'message':
            message += f"💬 **{notif['from_name']} texted you:**\n"
            message += f"_{notif['message_preview']}_\n"
            keyboard.append([InlineKeyboardButton(
                f"💬 Chat with {notif['from_name']}", 
                callback_data=f"chat_{notif['from_user']}"
            )])
        
        message += "\n---\n"
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def send_like_notification(context: ContextTypes.DEFAULT_TYPE, from_user_id: int, to_user_id: int, from_name: str):
    """Send like notification to user"""
    notification = {
        "user_id": to_user_id,
        "type": "like",
        "from_user": from_user_id,
        "from_name": from_name,
        "is_read": False,
        "created_at": datetime.utcnow()
    }
    db.get_collection("notifications").insert_one(notification)
    
    # Also create like record
    like_data = {
        "from_user": from_user_id,
        "to_user": to_user_id,
        "is_mutual": False,
        "created_at": datetime.utcnow()
    }
    db.get_collection("likes").insert_one(like_data)
    
    # Check for mutual like
    mutual_like = db.get_collection("likes").find_one({
        "from_user": to_user_id,
        "to_user": from_user_id
    })
    
    if mutual_like:
        await send_mutual_like_notification(context, from_user_id, to_user_id)

async def send_mutual_like_notification(context: ContextTypes.DEFAULT_TYPE, user1: int, user2: int):
    """Send mutual like notification to both users"""
    for user_id in [user1, user2]:
        notification = {
            "user_id": user_id,
            "type": "mutual_like",
            "from_user": user1 if user_id == user2 else user2,
            "from_name": "Someone",
            "is_read": False,
            "created_at": datetime.utcnow(),
            "is_mutual": True
        }
        db.get_collection("notifications").insert_one(notification)
