import logging
from datetime import datetime
from telebot import types
from database import get_db

logger = logging.getLogger(__name__)
db = get_db()


def handle_notifications(bot, call):
    """Show all unread notifications for user"""
    user_id = call.from_user.id
    
    bot.answer_callback_query(call.id)
    
    # Get unread notifications
    notifications = list(db.get_collection("notifications").find({
        "user_id": user_id,
        "is_read": False
    }).sort("created_at", -1))
    
    if not notifications:
        markup = types.InlineKeyboardMarkup()
        btn_menu = types.InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")
        markup.add(btn_menu)
        
        bot.edit_message_text(
            "🔔 **No new notifications**\n\nYou're all caught up!",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
        return
    
    # Mark all as read
    db.get_collection("notifications").update_many(
        {"user_id": user_id, "is_read": False},
        {"$set": {"is_read": True}}
    )
    
    # Build notification message
    message = f"🔔 **{len(notifications)} New Notification(s)**\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for notif in notifications:
        notif_type = notif.get('type')
        from_name = notif.get('from_name', 'Someone')
        from_user_id = notif.get('from_user_id')
        
        if notif_type == 'like':
            message += f"❤️ **{from_name} liked your profile!**\n"
            if from_user_id:
                btn = types.InlineKeyboardButton(
                    f"👤 View {from_name}",
                    callback_data=f"view_user_{from_user_id}"
                )
                markup.add(btn)
        
        elif notif_type == 'mutual_match':
            message += f"🎉 **Mutual Match!** {from_name} liked you back!\n"
            if from_user_id:
                btn = types.InlineKeyboardButton(
                    f"💬 Chat with {from_name}",
                    callback_data=f"chat_{from_user_id}"
                )
                markup.add(btn)
        
        elif notif_type == 'message':
            msg_preview = notif.get('message', '')[:50]
            message += f"💬 **{from_name} texted you:**\n"
            message += f"_{msg_preview}_\n"
            if from_user_id:
                btn = types.InlineKeyboardButton(
                    f"💬 Reply to {from_name}",
                    callback_data=f"chat_{from_user_id}"
                )
                markup.add(btn)
        
        elif notif_type == 'system':
            message += f"📢 **System:** {notif.get('message', '')}\n"
        
        message += "\n---\n"
    
    btn_menu = types.InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")
    markup.add(btn_menu)
    
    bot.edit_message_text(
        message,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )


def send_like_notification(bot, to_user_id, from_user_id, from_name):
    """Send like notification to user"""
    notification = {
        "user_id": to_user_id,
        "type": "like",
        "from_user_id": from_user_id,
        "from_name": from_name,
        "message": f"❤️ {from_name} liked your profile!",
        "is_read": False,
        "created_at": datetime.utcnow()
    }
    db.get_collection("notifications").insert_one(notification)
    
    # Also create like record
    like_data = {
        "from_user": from_user_id,
        "to_user": to_user_id,
        "from_name": from_name,
        "to_name": None,
        "is_mutual": False,
        "is_read": False,
        "created_at": datetime.utcnow()
    }
    db.get_collection("likes").insert_one(like_data)
    
    # Check for mutual like
    check_mutual_like(bot, from_user_id, to_user_id)


def send_message_notification(bot, to_user_id, from_user_id, from_name, message_preview):
    """Send message notification to user"""
    notification = {
        "user_id": to_user_id,
        "type": "message",
        "from_user_id": from_user_id,
        "from_name": from_name,
        "message": message_preview[:100],
        "is_read": False,
        "created_at": datetime.utcnow()
    }
    db.get_collection("notifications").insert_one(notification)


def send_mutual_match_notification(bot, user1_id, user2_id, user1_name, user2_name):
    """Send mutual match notification to both users"""
    # Notification for user1
    notif1 = {
        "user_id": user1_id,
        "type": "mutual_match",
        "from_user_id": user2_id,
        "from_name": user2_name,
        "message": f"🎉 It's a match! You and {user2_name} liked each other!",
        "is_read": False,
        "created_at": datetime.utcnow()
    }
    db.get_collection("notifications").insert_one(notif1)
    
    # Notification for user2
    notif2 = {
        "user_id": user2_id,
        "type": "mutual_match",
        "from_user_id": user1_id,
        "from_name": user1_name,
        "message": f"🎉 It's a match! You and {user1_name} liked each other!",
        "is_read": False,
        "created_at": datetime.utcnow()
    }
    db.get_collection("notifications").insert_one(notif2)


def check_mutual_like(bot, user1_id, user2_id):
    """Check if two users have liked each other"""
    like1 = db.get_collection("likes").find_one({
        "from_user": user1_id,
        "to_user": user2_id
    })
    
    like2 = db.get_collection("likes").find_one({
        "from_user": user2_id,
        "to_user": user1_id
    })
    
    if like1 and like2:
        # Update both as mutual
        db.get_collection("likes").update_many(
            {"$or": [
                {"from_user": user1_id, "to_user": user2_id},
                {"from_user": user2_id, "to_user": user1_id}
            ]},
            {"$set": {"is_mutual": True}}
        )
        
        # Get names
        user1 = db.get_collection("users").find_one({"user_id": user1_id})
        user2 = db.get_collection("users").find_one({"user_id": user2_id})
        
        user1_name = user1.get('first_name', 'Someone') if user1 else 'Someone'
        user2_name = user2.get('first_name', 'Someone') if user2 else 'Someone'
        
        # Send mutual match notifications
        send_mutual_match_notification(bot, user1_id, user2_id, user1_name, user2_name)
        
        return True
    
    return False


def get_unread_count(user_id):
    """Get unread notification count for user"""
    return db.get_collection("notifications").count_documents({
        "user_id": user_id,
        "is_read": False
    })


def mark_all_as_read(user_id):
    """Mark all notifications as read for user"""
    result = db.get_collection("notifications").update_many(
        {"user_id": user_id, "is_read": False},
        {"$set": {"is_read": True}}
    )
    return result.modified_count


def delete_old_notifications(days=30):
    """Delete notifications older than specified days"""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    result = db.get_collection("notifications").delete_many({
        "created_at": {"$lt": cutoff}
    })
    return result.deleted_count
