import logging
from datetime import datetime
from telebot import types
from database import get_db
from utils.storage import upload_media_to_channel

logger = logging.getLogger(__name__)
db = get_db()


def handle_name(bot, message, user_states, user_temp_data):
    """Handle name input"""
    user_id = message.from_user.id
    name = message.text.strip()
    
    if len(name) < 2 or len(name) > 50:
        bot.reply_to(message, "❌ Name must be 2-50 characters. Try again:")
        return
    
    user_temp_data[user_id]['name'] = name
    user_states[user_id] = "awaiting_gender"
    
    # Gender selection keyboard
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_male = types.InlineKeyboardButton("👨 Male", callback_data="gender_male")
    btn_female = types.InlineKeyboardButton("👩 Female", callback_data="gender_female")
    markup.add(btn_male, btn_female)
    
    bot.reply_to(
        message,
        f"✅ Name: {name}\n\nNow select your **Gender**:",
        reply_markup=markup
    )


def handle_gender_callback(bot, call, user_states, user_temp_data):
    """Handle gender selection callback"""
    user_id = call.from_user.id
    gender = call.data.split('_')[1]
    
    bot.answer_callback_query(call.id)
    
    user_temp_data[user_id]['gender'] = gender
    user_states[user_id] = "awaiting_age"
    
    bot.edit_message_text(
        f"✅ Gender: {'Male' if gender == 'male' else 'Female'}\n\n"
        f"Now send your **Age** (18-100):",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )


def handle_age(bot, message, user_states, user_temp_data):
    """Handle age input"""
    user_id = message.from_user.id
    
    try:
        age = int(message.text.strip())
        if age < 18 or age > 100:
            raise ValueError
    except:
        bot.reply_to(message, "❌ Invalid age! Send number between 18-100:")
        return
    
    user_temp_data[user_id]['age'] = age
    user_states[user_id] = "awaiting_location"
    
    # Location keyboard with option to share live location
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_location = types.KeyboardButton("📍 Send Live Location", request_location=True)
    btn_skip = types.KeyboardButton("⏭️ Skip Location")
    markup.add(btn_location, btn_skip)
    
    bot.reply_to(
        message,
        f"✅ Age: {age}\n\n"
        f"Now send your **Location** (City/Area):\n"
        f"Or share live location for better matches:",
        reply_markup=markup
    )


def handle_location(bot, message, user_states, user_temp_data):
    """Handle location (live location or coordinates)"""
    user_id = message.from_user.id
    
    if message.location:
        # User shared live location
        user_temp_data[user_id]['latitude'] = message.location.latitude
        user_temp_data[user_id]['longitude'] = message.location.longitude
        user_temp_data[user_id]['location_text'] = f"{message.location.latitude}, {message.location.longitude}"
        
        user_states[user_id] = "awaiting_about"
        
        # Remove keyboard
        markup = types.ReplyKeyboardRemove()
        
        bot.reply_to(
            message,
            f"✅ Location saved! (Coordinates received)\n\n"
            f"Now send your **About** (max 500 chars):\n"
            f"Or send /skip to skip this step",
            reply_markup=markup
        )
    else:
        # Will be handled by handle_location_text
        pass


def handle_location_text(bot, message, user_states, user_temp_data):
    """Handle text location input"""
    user_id = message.from_user.id
    location = message.text.strip()
    
    if location == "⏭️ Skip Location":
        user_temp_data[user_id]['location_text'] = ""
        user_states[user_id] = "awaiting_about"
        
        # Remove keyboard
        markup = types.ReplyKeyboardRemove()
        
        bot.reply_to(
            message,
            f"✅ Location skipped!\n\n"
            f"Now send your **About** (max 500 chars):\n"
            f"Or send /skip to skip this step",
            reply_markup=markup
        )
        return
    
    if len(location) < 2:
        bot.reply_to(message, "❌ Invalid location. Try again:")
        return
    
    user_temp_data[user_id]['location_text'] = location
    user_states[user_id] = "awaiting_about"
    
    # Remove keyboard
    markup = types.ReplyKeyboardRemove()
    
    bot.reply_to(
        message,
        f"✅ Location: {location}\n\n"
        f"Now send your **About** (max 500 chars):\n"
        f"Or send /skip to skip this step",
        reply_markup=markup
    )


def handle_about(bot, message, user_states, user_temp_data):
    """Handle about text input"""
    user_id = message.from_user.id
    
    if message.text and message.text == '/skip':
        user_temp_data[user_id]['about'] = ""
    else:
        about = message.text.strip()
        if len(about) > 500:
            bot.reply_to(message, "❌ About too long! Max 500 characters. Try again:")
            return
        user_temp_data[user_id]['about'] = about
    
    user_states[user_id] = "awaiting_media"
    user_temp_data[user_id]['media_list'] = []
    
    bot.reply_to(
        message,
        f"✅ About saved!\n\n"
        f"Now send **1-3 photos/videos**\n"
        f"Send media one by one, then send /done when finished\n\n"
        f"📷 Remaining slots: 3",
        parse_mode='Markdown'
    )


def handle_media(bot, message, user_states, user_temp_data):
    """Handle media (photos/videos) input"""
    user_id = message.from_user.id
    media_list = user_temp_data[user_id].get('media_list', [])
    
    if len(media_list) >= 3:
        bot.reply_to(message, "❌ Max 3 media files already! Send /done to continue.")
        return
    
    # Get file_id based on media type
    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = 'photo'
    elif message.video:
        file_id = message.video.file_id
        media_type = 'video'
    else:
        bot.reply_to(message, "❌ Please send photo or video only!")
        return
    
    media_list.append({
        'file_id': file_id,
        'type': media_type
    })
    
    user_temp_data[user_id]['media_list'] = media_list
    remaining = 3 - len(media_list)
    
    bot.reply_to(
        message,
        f"✅ Media {len(media_list)}/3 added!\n"
        f"📷 {remaining} remaining. Send more or /done"
    )


def confirm_profile(bot, message, user_states, user_temp_data):
    """Show profile preview and ask for confirmation"""
    user_id = message.from_user.id
    temp = user_temp_data.get(user_id, {})
    media_list = temp.get('media_list', [])
    
    if not temp.get('name') or not temp.get('gender') or not temp.get('age'):
        bot.reply_to(message, "❌ Profile incomplete! Please start over with /start")
        return
    
    # Build preview text
    preview = f"📋 **Profile Preview**\n\n"
    preview += f"👤 Name: {temp.get('name')}\n"
    preview += f"⚧ Gender: {'Male' if temp.get('gender') == 'male' else 'Female'}\n"
    preview += f"🎂 Age: {temp.get('age')}\n"
    preview += f"📍 Location: {temp.get('location_text', 'Not provided')}\n"
    preview += f"📝 About: {temp.get('about', 'Not provided')[:100]}\n"
    preview += f"📷 Media: {len(media_list)} file(s)\n\n"
    preview += f"Confirm to save your profile?"
    
    # Confirmation buttons
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_yes = types.InlineKeyboardButton("✅ Confirm", callback_data="confirm_yes")
    btn_no = types.InlineKeyboardButton("❌ Cancel", callback_data="confirm_no")
    markup.add(btn_yes, btn_no)
    
    user_states[user_id] = "awaiting_confirm"
    
    bot.reply_to(message, preview, reply_markup=markup)


def handle_confirm_callback(bot, call, user_states, user_temp_data):
    """Handle profile confirmation callback"""
    user_id = call.from_user.id
    action = call.data.split('_')[1]
    
    bot.answer_callback_query(call.id)
    
    if action == "no":
        # Cancel profile creation
        if user_id in user_states:
            del user_states[user_id]
        if user_id in user_temp_data:
            del user_temp_data[user_id]
        
        bot.edit_message_text(
            "❌ Profile creation cancelled. Use /start to try again.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        return
    
    # Save profile
    temp = user_temp_data.get(user_id, {})
    media_list = temp.get('media_list', [])
    
    # Upload media to private channel
    media_urls = []
    for media in media_list:
        url = upload_media_to_channel(bot, media['file_id'], user_id, media['type'])
        if url:
            media_urls.append(url)
    
    # Save profile to database
    profile = {
        "user_id": user_id,
        "username": call.from_user.username,
        "name": temp.get('name'),
        "gender": temp.get('gender'),
        "age": temp.get('age'),
        "location_text": temp.get('location_text', ''),
        "latitude": temp.get('latitude'),
        "longitude": temp.get('longitude'),
        "about": temp.get('about', ''),
        "media": media_urls,
        "created_at": datetime.utcnow(),
        "is_active": True
    }
    
    db.get_collection("profiles").insert_one(profile)
    
    # Create user entry
    user_data = {
        "user_id": user_id,
        "username": call.from_user.username,
        "first_name": call.from_user.first_name,
        "setup_complete": False,
        "created_at": datetime.utcnow(),
        "last_active": datetime.utcnow()
    }
    db.get_collection("users").update_one(
        {"user_id": user_id},
        {"$set": user_data},
        upsert=True
    )
    
    user_states[user_id] = "awaiting_preference"
    
    # Ask for preference
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_male = types.InlineKeyboardButton("👨 Male", callback_data="pref_male")
    btn_female = types.InlineKeyboardButton("👩 Female", callback_data="pref_female")
    btn_both = types.InlineKeyboardButton("👥 Both", callback_data="pref_both")
    markup.add(btn_male, btn_female, btn_both)
    
    bot.edit_message_text(
        "🎉 **Profile Created Successfully!** 🎉\n\n"
        "Who do you want to see in your feed?",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )


def handle_preference_callback(bot, call, user_states, user_temp_data):
    """Handle preference selection callback"""
    user_id = call.from_user.id
    preference = call.data.split('_')[1]
    
    bot.answer_callback_query(call.id)
    
    # Update user with preference
    db.get_collection("users").update_one(
        {"user_id": user_id},
        {"$set": {"preference": preference, "setup_complete": True}}
    )
    
    # Clear temp data and state
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_temp_data:
        del user_temp_data[user_id]
    
    # Show main menu
    show_main_menu(bot, call.message.chat.id)


def show_main_menu(bot, chat_id):
    """Show main menu after profile creation"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_profile = types.InlineKeyboardButton("👤 MY PROFILE", callback_data="my_profile")
    btn_view = types.InlineKeyboardButton("👀 VIEW PROFILES", callback_data="view_profiles")
    btn_notify = types.InlineKeyboardButton("🔔 NOTIFICATIONS", callback_data="notifications")
    markup.add(btn_profile, btn_view, btn_notify)
    
    bot.send_message(
        chat_id,
        "🏠 **Main Menu**\n\nChoose an option:",
        reply_markup=markup
    )


def handle_edit_profile(bot, call, user_states, user_temp_data):
    """Handle edit profile button (placeholder)"""
    bot.answer_callback_query(call.id)
    
    bot.edit_message_text(
        "✏️ **Edit Profile**\n\n"
        "Coming soon!",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )
