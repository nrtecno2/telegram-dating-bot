import logging
import random
from datetime import datetime
from telebot import types
from database import get_db
from utils.location import get_nearby_profiles

logger = logging.getLogger(__name__)
db = get_db()

# Store active viewing sessions
active_sessions = {}


def handle_view_profiles(bot, call, user_states, user_temp_data):
    """Start viewing profiles based on user preference"""
    user_id = call.from_user.id
    
    bot.answer_callback_query(call.id)
    
    # Check if user has profile
    my_profile = db.get_collection("profiles").find_one({"user_id": user_id})
    if not my_profile:
        bot.edit_message_text(
            "❌ You need to create a profile first!\nUse /start to begin.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        return
    
    # Get user preference
    user = db.get_collection("users").find_one({"user_id": user_id})
    if not user or not user.get('preference'):
        markup = types.InlineKeyboardMarkup()
        btn_pref = types.InlineKeyboardButton("⚙️ Set Preference", callback_data="set_preference")
        markup.add(btn_pref)
        
        bot.edit_message_text(
            "⚠️ Please set your preference first!\n\nChoose who you want to see:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
        return
    
    preference = user.get('preference', 'both')
    
    # Build query filter
    query_filter = {
        "user_id": {"$ne": user_id},
        "is_active": True
    }
    
    if preference == 'male':
        query_filter["gender"] = "male"
    elif preference == 'female':
        query_filter["gender"] = "female"
    
    # Get already liked users
    liked_users = db.get_collection("likes").distinct("to_user", {"from_user": user_id})
    query_filter["user_id"] = {"$nin": liked_users + [user_id]}
    
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
    else:
        profiles = list(db.get_collection("profiles").find(query_filter).limit(100))
        random.shuffle(profiles)
    
    if not profiles:
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_refresh = types.InlineKeyboardButton("🔄 Refresh", callback_data="view_profiles")
        btn_menu = types.InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")
        markup.add(btn_refresh, btn_menu)
        
        bot.edit_message_text(
            "😔 **No profiles found!**\n\n"
            "Possible reasons:\n"
            "├ ─ No users matching your preference\n"
            "├ ─ You've liked everyone available\n"
            "└ ─ Try changing your preference\n\n"
            "🔄 Click Refresh to check again.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
        return
    
    # Store session
    active_sessions[user_id] = {
        'profiles': profiles,
        'current_index': 0,
        'message_id': call.message.message_id,
        'chat_id': call.message.chat.id
    }
    
    # Show first profile
    show_profile(bot, user_id)


def show_profile(bot, user_id):
    """Display current profile to user"""
    session = active_sessions.get(user_id)
    if not session:
        return
    
    profiles = session['profiles']
    index = session['current_index']
    
    if index >= len(profiles):
        # No more profiles
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_restart = types.InlineKeyboardButton("🔄 Start Over", callback_data="view_profiles")
        btn_menu = types.InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")
        markup.add(btn_restart, btn_menu)
        
        bot.edit_message_text(
            "🏁 **You've viewed all profiles!**\n\n"
            "No more profiles available right now.\n"
            "Come back later for new matches!",
            chat_id=session['chat_id'],
            message_id=session['message_id'],
            reply_markup=markup
        )
        
        # Clean up session
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
    
    # Build action buttons
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_like = types.InlineKeyboardButton("❤️ LIKE", callback_data=f"like_{profile['user_id']}")
    btn_chat = types.InlineKeyboardButton("💬 CHAT", callback_data=f"chat_{profile['user_id']}")
    btn_skip = types.InlineKeyboardButton("⏭️ SKIP", callback_data="skip_profile")
    btn_stop = types.InlineKeyboardButton("🛑 STOP", callback_data="stop_viewing")
    markup.add(btn_like, btn_chat, btn_skip, btn_stop)
    
    # Send or edit message with media
    if profile.get('media') and len(profile['media']) > 0:
        # For now, send text only (media handling can be added later)
        bot.edit_message_text(
            text,
            chat_id=session['chat_id'],
            message_id=session['message_id'],
            reply_markup=markup
        )
    else:
        bot.edit_message_text(
            text,
            chat_id=session['chat_id'],
            message_id=session['message_id'],
            reply_markup=markup
        )


def handle_like_callback(bot, call, user_states, user_temp_data):
    """Like the current profile"""
    user_id = call.from_user.id
    target_id = int(call.data.split('_')[1])
    
    bot.answer_callback_query(call.id, "❤️ Liked! Moving to next...")
    
    # Get target profile
    target_profile = db.get_collection("profiles").find_one({"user_id": target_id})
    if not target_profile:
        bot.edit_message_text(
            "❌ Profile not found!",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
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
            "from_name": call.from_user.first_name,
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
            "from_user": user_id,
            "from_name": call.from_user.first_name,
            "message": f"❤️ {call.from_user.first_name} liked your profile!",
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
            for uid, name in [(target_id, call.from_user.first_name), (user_id, target_profile.get('name'))]:
                match_notification = {
                    "user_id": uid,
                    "type": "mutual_match",
                    "from_user": user_id if uid == target_id else target_id,
                    "from_name": name,
                    "message": f"🎉 It's a match! You and {name} liked each other!",
                    "is_read": False,
                    "created_at": datetime.utcnow()
                }
                db.get_collection("notifications").insert_one(match_notification)
            
            bot.answer_callback_query(call.id, "🎉 It's a match! 🎉", show_alert=True)
    
    # Move to next profile
    session = active_sessions.get(user_id)
    if session:
        session['current_index'] += 1
        show_profile(bot, user_id)
    else:
        # Create new view profiles callback
        handle_view_profiles(bot, call, user_states, user_temp_data)


def handle_skip_callback(bot, call, user_states, user_temp_data):
    """Skip current profile"""
    user_id = call.from_user.id
    
    bot.answer_callback_query(call.id, "⏭️ Skipped")
    
    session = active_sessions.get(user_id)
    if session:
        session['current_index'] += 1
        show_profile(bot, user_id)
    else:
        handle_view_profiles(bot, call, user_states, user_temp_data)


def handle_stop_callback(bot, call, user_states, user_temp_data):
    """Stop viewing profiles"""
    user_id = call.from_user.id
    
    bot.answer_callback_query(call.id)
    
    # Clean up session
    if user_id in active_sessions:
        del active_sessions[user_id]
    
    # Return to main menu
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_profile = types.InlineKeyboardButton("👤 MY PROFILE", callback_data="my_profile")
    btn_view = types.InlineKeyboardButton("👀 VIEW PROFILES", callback_data="view_profiles")
    btn_notify = types.InlineKeyboardButton("🔔 NOTIFICATIONS", callback_data="notifications")
    markup.add(btn_profile, btn_view, btn_notify)
    
    bot.edit_message_text(
        "🏠 **Main Menu**\n\nViewing stopped. Choose an option:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )


def handle_my_profile(bot, call):
    """Show user's own profile"""
    user_id = call.from_user.id
    
    bot.answer_callback_query(call.id)
    
    profile = db.get_collection("profiles").find_one({"user_id": user_id})
    if not profile:
        bot.edit_message_text(
            "❌ No profile found. Use /start to create one.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
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
    
    # Action buttons
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_edit = types.InlineKeyboardButton("✏️ Edit Profile", callback_data="edit_profile")
    btn_menu = types.InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")
    markup.add(btn_edit, btn_menu)
    
    bot.edit_message_text(
        text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )
