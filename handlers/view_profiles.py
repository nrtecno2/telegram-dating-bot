import logging
import random
from datetime import datetime
from telebot import types
from database import get_db
from utils.location import get_nearby_profiles, calculate_distance

logger = logging.getLogger(__name__)
db = get_db()

# Store active viewing sessions
active_sessions = {}


def handle_view_profiles(bot, message, user_states, user_temp_data):
    """Start viewing profiles based on user preference"""
    user_id = message.from_user.id
    
    # Check if user has profile
    my_profile = db.get_collection("profiles").find_one({"user_id": user_id, "is_active": True})
    if not my_profile:
        bot.reply_to(message, "❌ You need to create a profile first!\nUse /start to begin.")
        return
    
    # Get user preference
    user = db.get_collection("users").find_one({"user_id": user_id})
    if not user or not user.get('preference'):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        btn_male = types.KeyboardButton("👨 Male")
        btn_female = types.KeyboardButton("👩 Female")
        btn_both = types.KeyboardButton("👥 Both")
        markup.add(btn_male, btn_female, btn_both)
        
        bot.reply_to(
            message,
            "⚠️ Please set your preference first!\n\n"
            "Who do you want to see?",
            reply_markup=markup
        )
        return
    
    preference = user.get('preference', 'both')
    
    # Build query filter - ONLY ACTIVE PROFILES
    query_filter = {
        "user_id": {"$ne": user_id},
        "is_active": True  # IMPORTANT: Exclude deleted profiles
    }
    
    if preference == 'male':
        query_filter["gender"] = "male"
    elif preference == 'female':
        query_filter["gender"] = "female"
    
    # Get already liked users to exclude them
    liked_users = db.get_collection("likes").distinct("to_user", {"from_user": user_id})
    
    # Get profiles
    profiles = []
    
    if my_profile.get('latitude') and my_profile.get('longitude'):
        nearby = get_nearby_profiles(
            my_profile['latitude'],
            my_profile['longitude'],
            query_filter,
            max_distance_km=50
        )
        profiles = list(nearby)
        # Filter out liked users
        profiles = [p for p in profiles if p['user_id'] not in liked_users]
    else:
        profiles = list(db.get_collection("profiles").find(query_filter))
        # Filter out liked users
        profiles = [p for p in profiles if p['user_id'] not in liked_users]
        random.shuffle(profiles)
    
    # If no profiles found, reset and show all except liked ones
    if not profiles:
        # Get all profiles again without liked filter (but still exclude self and deleted)
        if my_profile.get('latitude') and my_profile.get('longitude'):
            nearby = get_nearby_profiles(
                my_profile['latitude'],
                my_profile['longitude'],
                query_filter,
                max_distance_km=50
            )
            profiles = list(nearby)
        else:
            profiles = list(db.get_collection("profiles").find(query_filter))
        
        # Still exclude liked users
        profiles = [p for p in profiles if p['user_id'] not in liked_users]
        
        if not profiles:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            btn_refresh = types.KeyboardButton("🔄 Refresh")
            btn_menu = types.KeyboardButton("🏠 Main Menu")
            markup.add(btn_refresh, btn_menu)
            
            bot.reply_to(
                message,
                "😔 **No profiles found!**\n\n"
                "Possible reasons:\n"
                "├ ─ No users matching your preference\n"
                "├ ─ You've liked everyone available\n"
                "└ ─ Try changing your preference\n\n"
                "🔄 Click Refresh to check again.",
                reply_markup=markup
            )
            return
    
    # Store session
    active_sessions[user_id] = {
        'profiles': profiles,
        'current_index': 0,
        'chat_id': message.chat.id,
        'preference': preference
    }
    
    # Show first profile
    show_profile(bot, user_id)


def show_profile(bot, user_id):
    """Display current profile to user with media"""
    session = active_sessions.get(user_id)
    if not session:
        return
    
    profiles = session['profiles']
    index = session['current_index']
    
    if index >= len(profiles):
        # No more profiles - loop back to start
        session['current_index'] = 0
        index = 0
        
        if len(profiles) == 0:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            btn_menu = types.KeyboardButton("🏠 Main Menu")
            markup.add(btn_menu)
            bot.send_message(
                session['chat_id'],
                "🏁 **No profiles available!**\n\nPlease check back later.",
                reply_markup=markup
            )
            del active_sessions[user_id]
            return
    
    profile = profiles[index]
    
    # Build profile display text
    text = f"👤 **{profile['name']}**\n"
    text += f"🎂 Age: {profile['age']}\n"
    text += f"📍 {profile.get('location_text', 'Location not specified')}\n"
    
    if profile.get('about'):
        about_preview = profile['about'][:200]
        if len(profile['about']) > 200:
            about_preview += "..."
        text += f"\n📝 **About:**\n{about_preview}\n"
    
    text += f"\n👥 Profile {index + 1} of {len(profiles)}"
    
    # Build action buttons - ReplyKeyboardMarkup (bottom buttons)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    btn_like = types.KeyboardButton("❤️ LIKE")
    btn_chat = types.KeyboardButton("💬 CHAT")
    btn_skip = types.KeyboardButton("⏭️ SKIP")
    btn_stop = types.KeyboardButton("🛑 STOP VIEWING")
    markup.add(btn_like, btn_chat, btn_skip, btn_stop)
    
    # Store current profile user_id in session for actions
    session['current_profile_id'] = profile['user_id']
    
    # Send media if available - FIXED to show photos/videos properly
    media_list = profile.get('media', [])
    if media_list and len(media_list) > 0:
        # Send first media with caption
        first_media = media_list[0]
        
        try:
            # Try to send as photo (most common)
            bot.send_photo(
                session['chat_id'],
                photo=first_media,
                caption=text,
                parse_mode='Markdown'
            )
        except Exception as e:
            try:
                # If photo fails, try as video
                bot.send_video(
                    session['chat_id'],
                    video=first_media,
                    caption=text,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send media: {e}")
                bot.send_message(session['chat_id'], text, parse_mode='Markdown')
        
        # Send remaining media (max 2 more)
        for media_url in media_list[1:3]:
            try:
                if media_url.endswith(('jpg', 'jpeg', 'png', 'gif', 'webp')):
                    bot.send_photo(session['chat_id'], photo=media_url)
                else:
                    bot.send_video(session['chat_id'], video=media_url)
            except Exception as e:
                logger.error(f"Failed to send additional media: {e}")
    else:
        # No media, just text
        bot.send_message(session['chat_id'], text, parse_mode='Markdown')
    
    # Send action buttons
    bot.send_message(
        session['chat_id'],
        "What would you like to do?",
        reply_markup=markup
    )


def handle_like_action(bot, message, user_states, user_temp_data):
    """Handle like action from bottom button"""
    user_id = message.from_user.id
    session = active_sessions.get(user_id)
    
    if not session:
        bot.reply_to(message, "❌ No active session. Use VIEW PROFILES to start.")
        return
    
    target_id = session.get('current_profile_id')
    if not target_id:
        bot.reply_to(message, "❌ Error: No profile selected.")
        return
    
    # Get target profile
    target_profile = db.get_collection("profiles").find_one({"user_id": target_id, "is_active": True})
    if not target_profile:
        bot.reply_to(message, "❌ Profile not found or deleted!")
        session['current_index'] += 1
        show_profile(bot, user_id)
        return
    
    # Check if already liked
    existing_like = db.get_collection("likes").find_one({
        "from_user": user_id,
        "to_user": target_id
    })
    
    if not existing_like:
        # Create like record
        like_data = {
            "from_user": user_id,
            "to_user": target_id,
            "from_name": message.from_user.first_name,
            "to_name": target_profile.get('name'),
            "is_mutual": False,
            "is_read": False,
            "created_at": datetime.utcnow()
        }
        db.get_collection("likes").insert_one(like_data)
        
        # Create notification for target
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
        
        # Check for mutual like
        mutual = db.get_collection("likes").find_one({
            "from_user": target_id,
            "to_user": user_id
        })
        
        if mutual:
            # Update as mutual
            db.get_collection("likes").update_many(
                {"$or": [
                    {"from_user": user_id, "to_user": target_id},
                    {"from_user": target_id, "to_user": user_id}
                ]},
                {"$set": {"is_mutual": True}}
            )
            
            # Send mutual match notification to both
            match_notification1 = {
                "user_id": target_id,
                "type": "mutual_match",
                "from_user_id": user_id,
                "from_name": message.from_user.first_name,
                "message": f"🎉 It's a match! You and {message.from_user.first_name} liked each other!",
                "is_read": False,
                "created_at": datetime.utcnow()
            }
            db.get_collection("notifications").insert_one(match_notification1)
            
            match_notification2 = {
                "user_id": user_id,
                "type": "mutual_match",
                "from_user_id": target_id,
                "from_name": target_profile.get('name'),
                "message": f"🎉 It's a match! You and {target_profile.get('name')} liked each other!",
                "is_read": False,
                "created_at": datetime.utcnow()
            }
            db.get_collection("notifications").insert_one(match_notification2)
            
            bot.reply_to(message, "🎉 **It's a match!** 🎉\n\nYou can now chat with this user!")
        else:
            bot.reply_to(message, "❤️ Liked! Moving to next profile...")
    else:
        bot.reply_to(message, "❤️ You already liked this profile!")
    
    # Move to next profile
    session['current_index'] += 1
    show_profile(bot, user_id)


def handle_skip_action(bot, message, user_states, user_temp_data):
    """Handle skip action from bottom button"""
    user_id = message.from_user.id
    session = active_sessions.get(user_id)
    
    if not session:
        bot.reply_to(message, "❌ No active session. Use VIEW PROFILES to start.")
        return
    
    bot.reply_to(message, "⏭️ Skipped!")
    
    # Move to next profile
    session['current_index'] += 1
    show_profile(bot, user_id)


def handle_stop_viewing_action(bot, message, user_states, user_temp_data):
    """Handle stop viewing action from bottom button"""
    user_id = message.from_user.id
    
    # Clean up session
    if user_id in active_sessions:
        del active_sessions[user_id]
    
    # Return to main menu
    from handlers.profile import show_main_menu
    show_main_menu(bot, message.chat.id)


def handle_chat_from_profile(bot, message, user_states, user_temp_data):
    """Handle chat action from profile viewing"""
    user_id = message.from_user.id
    session = active_sessions.get(user_id)
    
    if not session:
        bot.reply_to(message, "❌ No active session. Use VIEW PROFILES to start.")
        return
    
    target_id = session.get('current_profile_id')
    if not target_id:
        bot.reply_to(message, "❌ Error: No profile selected.")
        return
    
    # Get target profile
    target_profile = db.get_collection("profiles").find_one({"user_id": target_id})
    if not target_profile:
        bot.reply_to(message, "❌ User not found!")
        return
    
    target_name = target_profile.get('name', 'User')
    
    # Check if mutual match exists
    is_mutual = db.get_collection("likes").find_one({
        "from_user": user_id,
        "to_user": target_id,
        "is_mutual": True
    })
    
    if not is_mutual:
        # Check if both have liked each other
        like1 = db.get_collection("likes").find_one({"from_user": user_id, "to_user": target_id})
        like2 = db.get_collection("likes").find_one({"from_user": target_id, "to_user": user_id})
        
        if like1 and like2:
            is_mutual = True
        
        if not is_mutual:
            bot.reply_to(
                message,
                "💬 **Cannot Chat**\n\n"
                "You can only chat with mutual matches.\n\n"
                "💡 Tip: Like each other first to start chatting!"
            )
            return
    
    # Start chat session
    from handlers.chat import start_chat_session
    start_chat_session(bot, message, user_id, target_id, target_name)


def handle_my_profile(bot, message):
    """Show user's own profile with media"""
    user_id = message.from_user.id
    
    profile = db.get_collection("profiles").find_one({"user_id": user_id, "is_active": True})
    if not profile:
        bot.reply_to(message, "❌ No profile found. Use /start to create one.")
        return
    
    # Get stats
    likes_received = db.get_collection("likes").count_documents({"to_user": user_id})
    
    # Build profile text
    text = f"👤 **YOUR PROFILE**\n\n"
    text += f"📛 Name: {profile['name']}\n"
    text += f"⚧ Gender: {'Male' if profile['gender'] == 'male' else 'Female'}\n"
    text += f"🎂 Age: {profile['age']}\n"
    text += f"📍 Location: {profile.get('location_text', 'Not set')}\n"
    text += f"❤️ Likes received: {likes_received}\n\n"
    
    if profile.get('about'):
        text += f"📝 **About:**\n{profile['about']}\n\n"
    
    text += f"📷 Media: {len(profile.get('media', []))} file(s)"
    
    # Action buttons - bottom
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_edit = types.KeyboardButton("✏️ EDIT PROFILE")
    btn_menu = types.KeyboardButton("🏠 Main Menu")
    markup.add(btn_edit, btn_menu)
    
    # Send media if available - FIXED to show photos/videos
    media_list = profile.get('media', [])
    if media_list and len(media_list) > 0:
        try:
            bot.send_photo(
                message.chat.id,
                photo=media_list[0],
                caption=text,
                parse_mode='Markdown'
            )
        except Exception as e:
            try:
                bot.send_video(
                    message.chat.id,
                    video=media_list[0],
                    caption=text,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send profile media: {e}")
                bot.send_message(message.chat.id, text, parse_mode='Markdown')
        
        # Send remaining media
        for media_url in media_list[1:3]:
            try:
                if media_url.endswith(('jpg', 'jpeg', 'png', 'gif', 'webp')):
                    bot.send_photo(message.chat.id, photo=media_url)
                else:
                    bot.send_video(message.chat.id, video=media_url)
            except Exception as e:
                logger.error(f"Failed to send additional media: {e}")
    else:
        bot.send_message(message.chat.id, text, parse_mode='Markdown')
    
    bot.send_message(
        message.chat.id,
        "Choose an option:",
        reply_markup=markup
    )


def handle_refresh_profiles(bot, message, user_states, user_temp_data):
    """Handle refresh button when no profiles found"""
    user_id = message.from_user.id
    
    # Clear session and restart
    if user_id in active_sessions:
        del active_sessions[user_id]
    
    handle_view_profiles(bot, message, user_states, user_temp_data)
