import logging
from datetime import datetime
from telebot import types
from database import get_db

logger = logging.getLogger(__name__)
db = get_db()


def handle_notifications(bot, message):
    """Show all notifications for user"""
    user_id = message.from_user.id
    
    # Get unread notifications
    notifications = list(db.get_collection("notifications").find({
        "user_id": user_id,
        "is_read": False
    }).sort("created_at", -1))
    
    if not notifications:
        # Check if there are any read notifications to show
        all_notifications = list(db.get_collection("notifications").find({
            "user_id": user_id
        }).sort("created_at", -1).limit(20))
        
        if not all_notifications:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            btn_menu = types.KeyboardButton("🏠 Main Menu")
            markup.add(btn_menu)
            
            bot.reply_to(
                message,
                "🔔 **No notifications**\n\nYou don't have any notifications yet.\n\n"
                "💡 Tip: Like more profiles to get matches!",
                reply_markup=markup,
                parse_mode='Markdown'
            )
            return
        else:
            notifications = all_notifications
    
    # Mark all as read
    db.get_collection("notifications").update_many(
        {"user_id": user_id, "is_read": False},
        {"$set": {"is_read": True}}
    )
    
    # Send each notification individually with action buttons
    for notif in notifications:
        notif_type = notif.get('type')
        from_name = notif.get('from_name', 'Someone')
        from_user_id = notif.get('from_user_id')
        
        if notif_type == 'like':
            text = f"❤️ **{from_name} liked your profile!**"
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            btn_view = types.KeyboardButton(f"👤 View {from_name}")
            btn_menu = types.KeyboardButton("🏠 Main Menu")
            markup.add(btn_view, btn_menu)
            
            from handlers.start import user_temp_data
            user_temp_data[user_id] = {'view_user_id': from_user_id, 'view_user_name': from_name}
            
            bot.send_message(
                message.chat.id,
                text,
                reply_markup=markup,
                parse_mode='Markdown'
            )
        
        elif notif_type == 'mutual_match':
            text = f"🎉 **Mutual Match!** {from_name} liked you back!"
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            btn_view = types.KeyboardButton(f"👤 View {from_name}")
            btn_chat = types.KeyboardButton(f"💬 Chat with {from_name}")
            btn_menu = types.KeyboardButton("🏠 Main Menu")
            markup.add(btn_view, btn_chat, btn_menu)
            
            from handlers.start import user_temp_data
            user_temp_data[user_id] = {'view_user_id': from_user_id, 'view_user_name': from_name, 'is_mutual': True}
            
            bot.send_message(
                message.chat.id,
                text,
                reply_markup=markup,
                parse_mode='Markdown'
            )
        
        elif notif_type == 'message':
            msg_preview = notif.get('message', '')[:100]
            text = f"💬 **{from_name} sent you a message:**\n\n_{msg_preview}_"
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            btn_reply = types.KeyboardButton(f"💬 Reply to {from_name}")
            btn_view = types.KeyboardButton(f"👤 View {from_name}")
            btn_menu = types.KeyboardButton("🏠 Main Menu")
            markup.add(btn_reply, btn_view, btn_menu)
            
            from handlers.start import user_temp_data
            user_temp_data[user_id] = {'chat_user_id': from_user_id, 'chat_user_name': from_name}
            
            bot.send_message(
                message.chat.id,
                text,
                reply_markup=markup,
                parse_mode='Markdown'
            )
        
        elif notif_type == 'system':
            text = f"📢 **System:** {notif.get('message', '')}"
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            btn_menu = types.KeyboardButton("🏠 Main Menu")
            markup.add(btn_menu)
            
            bot.send_message(
                message.chat.id,
                text,
                reply_markup=markup,
                parse_mode='Markdown'
            )
    
    if not notifications:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        btn_menu = types.KeyboardButton("🏠 Main Menu")
        markup.add(btn_menu)
        
        bot.send_message(
            message.chat.id,
            "🔔 **All caught up!**\n\nYou have no new notifications.",
            reply_markup=markup,
            parse_mode='Markdown'
        )


def send_message_notification(bot, to_user_id, from_user_id, from_name, message_preview):
    """Send message notification to user"""
    try:
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
        logger.info(f"Message notification sent to {to_user_id} from {from_user_id}")
    except Exception as e:
        logger.error(f"Failed to send message notification: {e}")


def handle_view_user_from_notification(bot, message, user_temp_data):
    """Handle view user button from notification"""
    user_id = message.from_user.id
    data = user_temp_data.get(user_id, {})
    target_id = data.get('view_user_id')
    target_name = data.get('view_user_name', 'User')
    
    if not target_id:
        bot.reply_to(message, "❌ User not found!")
        from handlers.profile import show_main_menu
        show_main_menu(bot, message.chat.id)
        return
    
    target_profile = db.get_collection("profiles").find_one({"user_id": target_id})
    if not target_profile:
        bot.reply_to(message, "❌ User profile not found!")
        from handlers.profile import show_main_menu
        show_main_menu(bot, message.chat.id)
        return
    
    text = f"👤 **{target_profile['name']}**\n"
    text += f"🎂 Age: {target_profile['age']}\n"
    text += f"📍 {target_profile.get('location_text', 'Location not specified')}\n"
    
    if target_profile.get('about'):
        text += f"\n📝 **About:**\n{target_profile['about'][:200]}\n"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_like = types.KeyboardButton(f"❤️ Like {target_profile['name']}")
    btn_chat = types.KeyboardButton(f"💬 Chat with {target_profile['name']}")
    btn_menu = types.KeyboardButton("🏠 Main Menu")
    markup.add(btn_like, btn_chat, btn_menu)
    
    user_temp_data[user_id] = {'view_user_id': target_id, 'view_user_name': target_profile['name']}
    
    media_list = target_profile.get('media', [])
    if media_list and len(media_list) > 0:
        try:
            bot.send_photo(
                message.chat.id,
                photo=media_list[0],
                caption=text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send photo: {e}")
            bot.send_message(message.chat.id, text, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, text, parse_mode='Markdown')
    
    bot.send_message(
        message.chat.id,
        "What would you like to do?",
        reply_markup=markup
    )


def handle_like_from_notification(bot, message, user_temp_data):
    """Handle like button from notification view"""
    user_id = message.from_user.id
    data = user_temp_data.get(user_id, {})
    target_id = data.get('view_user_id')
    target_name = data.get('view_user_name')
    
    if not target_id:
        bot.reply_to(message, "❌ User not found!")
        from handlers.profile import show_main_menu
        show_main_menu(bot, message.chat.id)
        return
    
    existing_like = db.get_collection("likes").find_one({
        "from_user": user_id,
        "to_user": target_id
    })
    
    if existing_like:
        bot.reply_to(message, f"❤️ You already liked {target_name}!")
    else:
        like_data = {
            "from_user": user_id,
            "to_user": target_id,
            "from_name": message.from_user.first_name,
            "to_name": target_name,
            "is_mutual": False,
            "is_read": False,
            "created_at": datetime.utcnow()
        }
        db.get_collection("likes").insert_one(like_data)
        
        notification = {
            "user_id": target_id,
            "type": "like",
            "from_user_id": user_id,
            "from_name": message.from_user.first_name,
            "message": f"❤️ {message.from_user.first_name} liked your profile!",
            "is_read": False,
            "created_at": datetime.utcnow()
        }
        db.get_collection("notifications").insert_one(notification)
        
        mutual = db.get_collection("likes").find_one({
            "from_user": target_id,
            "to_user": user_id
        })
        
        if mutual:
            db.get_collection("likes").update_many(
                {"$or": [
                    {"from_user": user_id, "to_user": target_id},
                    {"from_user": target_id, "to_user": user_id}
                ]},
                {"$set": {"is_mutual": True}}
            )
            
            match_notification = {
                "user_id": target_id,
                "type": "mutual_match",
                "from_user_id": user_id,
                "from_name": message.from_user.first_name,
                "message": f"🎉 It's a match! You and {message.from_user.first_name} liked each other!",
                "is_read": False,
                "created_at": datetime.utcnow()
            }
            db.get_collection("notifications").insert_one(match_notification)
            
            bot.reply_to(message, f"🎉 **It's a match!** 🎉\n\nYou and {target_name} liked each other!")
        else:
            bot.reply_to(message, f"❤️ You liked {target_name}!")
    
    from handlers.profile import show_main_menu
    show_main_menu(bot, message.chat.id)


def handle_reply_from_notification(bot, message, user_temp_data):
    """Handle reply button from message notification"""
    user_id = message.from_user.id
    data = user_temp_data.get(user_id, {})
    target_id = data.get('chat_user_id')
    target_name = data.get('chat_user_name')
    
    if not target_id:
        bot.reply_to(message, "❌ User not found!")
        from handlers.profile import show_main_menu
        show_main_menu(bot, message.chat.id)
        return
    
    from handlers.chat import start_chat_session
    start_chat_session(bot, message, user_id, target_id, target_name)


def handle_chat_from_notification(bot, message, user_temp_data):
    """Handle chat button from notification (mutual match)"""
    user_id = message.from_user.id
    data = user_temp_data.get(user_id, {})
    target_id = data.get('view_user_id')
    target_name = data.get('view_user_name')
    
    if not target_id:
        bot.reply_to(message, "❌ User not found!")
        from handlers.profile import show_main_menu
        show_main_menu(bot, message.chat.id)
        return
    
    from handlers.chat import start_chat_session
    start_chat_session(bot, message, user_id, target_id, target_name)
