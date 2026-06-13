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
    
    # Gender selection keyboard - ReplyKeyboardMarkup (bottom buttons)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_male = types.KeyboardButton("👨 Male")
    btn_female = types.KeyboardButton("👩 Female")
    markup.add(btn_male, btn_female)
    
    bot.reply_to(
        message,
        f"✅ Name: {name}\n\nNow select your **Gender**:",
        reply_markup=markup
    )


def handle_gender_callback(bot, message, user_states, user_temp_data):
    """Handle gender selection (from bottom buttons)"""
    user_id = message.from_user.id
    gender_text = message.text.strip()
    
    if gender_text == "👨 Male":
        gender = "male"
    elif gender_text == "👩 Female":
        gender = "female"
    else:
        bot.reply_to(message, "❌ Please select gender using the buttons below:")
        return
    
    user_temp_data[user_id]['gender'] = gender
    user_states[user_id] = "awaiting_age"
    
    # Remove gender keyboard, show regular keyboard
    markup = types.ReplyKeyboardRemove()
    
    bot.reply_to(
        message,
        f"✅ Gender: {'Male' if gender == 'male' else 'Female'}\n\n"
        f"Now send your **Age** (18-100):",
        reply_markup=markup
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
    
    # Location keyboard with options - ReplyKeyboardMarkup
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
    btn_location = types.KeyboardButton("📍 Send Live Location", request_location=True)
    btn_skip = types.KeyboardButton("⏭️ Skip Location")
    markup.add(btn_location, btn_skip)
    
    bot.reply_to(
        message,
        f"✅ Age: {age}\n\n"
        f"📍 **Share your location for better matches!**\n\n"
        f"⚠️ Location ka upyog:\n"
        f"├ → Aapke nearby profiles dikhane ke liye\n"
        f"├ → 50km radius ke log dikhenge\n"
        f"└ → Aapki privacy safe hai\n\n"
        f"**Option 1:** Share live location (recommended)\n"
        f"**Option 2:** Type city name (e.g., Mumbai, Delhi)\n"
        f"**Option 3:** Tap 'Skip Location' to continue without location\n\n"
        f"📍 Send location or type city name:",
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
    """Handle text location input or skip"""
    user_id = message.from_user.id
    location = message.text.strip()
    
    # Check for skip button
    if location == "⏭️ Skip Location":
        user_temp_data[user_id]['location_text'] = ""
        user_temp_data[user_id]['latitude'] = None
        user_temp_data[user_id]['longitude'] = None
        user_states[user_id] = "awaiting_about"
        
        # Remove keyboard
        markup = types.ReplyKeyboardRemove()
        
        bot.reply_to(
            message,
            f"✅ Location skipped! Aapko general profiles dikhayi jayengi.\n\n"
            f"Now send your **About** (max 500 chars):\n"
            f"Or send /skip to skip this step",
            reply_markup=markup
        )
        return
    
    # Validate location text
    if len(location) < 2 or len(location) > 100:
        bot.reply_to(message, "❌ Invalid location. Try again or use 'Skip Location':")
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
        bot.reply_to(message, "✅ About skipped!")
    else:
        about = message.text.strip()
        if len(about) > 500:
            bot.reply_to(message, "❌ About too long! Max 500 characters. Try again:")
            return
        user_temp_data[user_id]['about'] = about
        bot.reply_to(message, f"✅ About saved!")
    
    user_states[user_id] = "awaiting_media"
    user_temp_data[user_id]['media_list'] = []
    
    bot.reply_to(
        message,
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
    
    # Confirmation buttons - ReplyKeyboardMarkup
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_yes = types.KeyboardButton("✅ Confirm Profile")
    btn_no = types.KeyboardButton("❌ Cancel")
    markup.add(btn_yes, btn_no)
    
    user_states[user_id] = "awaiting_confirm"
    
    bot.reply_to(message, preview, reply_markup=markup)


def handle_confirm_callback(bot, message, user_states, user_temp_data):
    """Handle profile confirmation (from bottom buttons)"""
    user_id = message.from_user.id
    action = message.text.strip()
    
    if action == "❌ Cancel":
        # Cancel profile creation
        if user_id in user_states:
            del user_states[user_id]
        if user_id in user_temp_data:
            del user_temp_data[user_id]
        
        markup = types.ReplyKeyboardRemove()
        bot.reply_to(message, "❌ Profile creation cancelled. Use /start to try again.", reply_markup=markup)
        return
    
    if action != "✅ Confirm Profile":
        bot.reply_to(message, "❌ Please use the buttons below to confirm or cancel:")
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
        "username": message.from_user.username,
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
        "username": message.from_user.username,
        "first_name": message.from_user.first_name,
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
    
    # Ask for preference - ReplyKeyboardMarkup
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_male = types.KeyboardButton("👨 Male")
    btn_female = types.KeyboardButton("👩 Female")
    btn_both = types.KeyboardButton("👥 Both")
    markup.add(btn_male, btn_female, btn_both)
    
    bot.reply_to(
        message,
        "🎉 **Profile Created Successfully!** 🎉\n\n"
        "Who do you want to see in your feed?",
        reply_markup=markup
    )


def handle_preference_callback(bot, message, user_states, user_temp_data):
    """Handle preference selection (from bottom buttons)"""
    user_id = message.from_user.id
    preference_text = message.text.strip()
    
    if preference_text == "👨 Male":
        preference = "male"
    elif preference_text == "👩 Female":
        preference = "female"
    elif preference_text == "👥 Both":
        preference = "both"
    else:
        bot.reply_to(message, "❌ Please select preference using the buttons below:")
        return
    
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
    
    # Remove keyboard and show main menu
    markup = types.ReplyKeyboardRemove()
    bot.reply_to(message, "✅ Preference saved!", reply_markup=markup)
    
    # Show main menu with bottom buttons
    show_main_menu(bot, message.chat.id)


def show_main_menu(bot, chat_id):
    """Show main menu with bottom buttons (ReplyKeyboardMarkup)"""
    # Get unread notifications count
    unread_count = db.get_collection("notifications").count_documents({"user_id": chat_id, "is_read": False})
    
    # Bottom buttons - ReplyKeyboardMarkup
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_profile = types.KeyboardButton("👤 MY PROFILE")
    btn_view = types.KeyboardButton("👀 VIEW PROFILES")
    btn_notify = types.KeyboardButton(f"🔔 NOTIFICATIONS ({unread_count})")
    btn_interest = types.KeyboardButton("🎯 CHANGE INTEREST")
    btn_stats = types.KeyboardButton("📊 MY STATS")
    btn_settings = types.KeyboardButton("⚙️ SETTINGS")
    markup.add(btn_profile, btn_view, btn_notify, btn_interest, btn_stats, btn_settings)
    
    bot.send_message(
        chat_id,
        "🏠 **Main Menu**\n\nChoose an option from below:",
        reply_markup=markup
    )


def handle_change_interest(bot, message, user_states, user_temp_data):
    """Handle change interest button"""
    user_id = message.from_user.id
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_male = types.KeyboardButton("👨 Male")
    btn_female = types.KeyboardButton("👩 Female")
    btn_both = types.KeyboardButton("👥 Both")
    btn_back = types.KeyboardButton("🔙 Back to Main Menu")
    markup.add(btn_male, btn_female, btn_both, btn_back)
    
    bot.reply_to(
        message,
        "🎯 **Change Interest / Preference**\n\n"
        "Select who you want to see in your feed:\n\n"
        "👨 Male - Only male profiles\n"
        "👩 Female - Only female profiles\n"
        "👥 Both - Both male and female profiles",
        reply_markup=markup
    )


def handle_update_preference(bot, message, user_states, user_temp_data):
    """Handle preference update from change interest menu"""
    user_id = message.from_user.id
    preference_text = message.text.strip()
    
    if preference_text == "👨 Male":
        preference = "male"
    elif preference_text == "👩 Female":
        preference = "female"
    elif preference_text == "👥 Both":
        preference = "both"
    elif preference_text == "🔙 Back to Main Menu":
        show_main_menu(bot, message.chat.id)
        return
    else:
        bot.reply_to(message, "❌ Please use the buttons below:")
        return
    
    # Update preference in database
    db.get_collection("users").update_one(
        {"user_id": user_id},
        {"$set": {"preference": preference}}
    )
    
    bot.reply_to(message, f"✅ Preference updated to: {preference_text}")
    show_main_menu(bot, message.chat.id)


def handle_my_stats(bot, message):
    """Handle my stats button"""
    user_id = message.from_user.id
    
    # Get stats from database
    user = db.get_collection("users").find_one({"user_id": user_id})
    profile = db.get_collection("profiles").find_one({"user_id": user_id})
    likes_given = db.get_collection("likes").count_documents({"from_user": user_id})
    likes_received = db.get_collection("likes").count_documents({"to_user": user_id})
    
    stats_text = f"📊 **YOUR STATS** 📊\n\n"
    stats_text += f"👤 Profile Views: {profile.get('profile_views', 0) if profile else 0}\n"
    stats_text += f"❤️ Likes Given: {likes_given}\n"
    stats_text += f"💕 Likes Received: {likes_received}\n"
    stats_text += f"🎯 Current Interest: {user.get('preference', 'Not set') if user else 'Not set'}\n\n"
    stats_text += f"Keep interacting to find better matches! 🔥"
    
    bot.reply_to(message, stats_text, parse_mode='Markdown')


def handle_settings(bot, message):
    """Handle settings button"""
    user_id = message.from_user.id
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn_delete = types.KeyboardButton("🗑 Delete Account")
    btn_back = types.KeyboardButton("🔙 Back to Main Menu")
    markup.add(btn_delete, btn_back)
    
    bot.reply_to(
        message,
        "⚙️ **SETTINGS** ⚙️\n\n"
        "Choose an option:",
        reply_markup=markup
    )


def handle_delete_account(bot, message):
    """Handle delete account confirmation"""
    user_id = message.from_user.id
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_confirm = types.KeyboardButton("🗑 Confirm Delete")
    btn_cancel = types.KeyboardButton("🔙 Cancel")
    markup.add(btn_confirm, btn_cancel)
    
    bot.reply_to(
        message,
        "⚠️ **DELETE ACCOUNT** ⚠️\n\n"
        "Are you sure? This action is permanent!\n"
        "All your data will be lost.\n\n"
        "Type 'Confirm Delete' to proceed.",
        reply_markup=markup
    )


def handle_confirm_delete(bot, message):
    """Handle account deletion"""
    user_id = message.from_user.id
    
    # Delete user data
    db.get_collection("profiles").delete_one({"user_id": user_id})
    db.get_collection("users").delete_one({"user_id": user_id})
    db.get_collection("likes").delete_many({"$or": [{"from_user": user_id}, {"to_user": user_id}]})
    db.get_collection("notifications").delete_many({"user_id": user_id})
    db.get_collection("messages").delete_many({"$or": [{"from_user": user_id}, {"to_user": user_id}]})
    
    markup = types.ReplyKeyboardRemove()
    bot.reply_to(
        message,
        "🗑 Your account has been deleted.\n\n"
        "Use /start to create a new profile.",
        reply_markup=markup
    )


def handle_edit_profile(bot, message, user_states, user_temp_data):
    """Handle edit profile button"""
    bot.reply_to(message, "✏️ **Edit Profile**\n\nComing soon!")
