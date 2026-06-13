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
        user_temp_data[user_id]['latitude'] = message.location.latitude
        user_temp_data[user_id]['longitude'] = message.location.longitude
        user_temp_data[user_id]['location_text'] = f"{message.location.latitude}, {message.location.longitude}"
        
        user_states[user_id] = "awaiting_about"
        
        markup = types.ReplyKeyboardRemove()
        
        bot.reply_to(
            message,
            f"✅ Location saved! (Coordinates received)\n\n"
            f"Now send your **About** (max 500 chars):\n"
            f"Or send /skip to skip this step",
            reply_markup=markup
        )
    else:
        pass


def handle_location_text(bot, message, user_states, user_temp_data):
    """Handle text location input or skip"""
    user_id = message.from_user.id
    location = message.text.strip()
    
    if location == "⏭️ Skip Location":
        user_temp_data[user_id]['location_text'] = ""
        user_temp_data[user_id]['latitude'] = None
        user_temp_data[user_id]['longitude'] = None
        user_states[user_id] = "awaiting_about"
        
        markup = types.ReplyKeyboardRemove()
        
        bot.reply_to(
            message,
            f"✅ Location skipped! Aapko general profiles dikhayi jayengi.\n\n"
            f"Now send your **About** (max 500 chars):\n"
            f"Or send /skip to skip this step",
            reply_markup=markup
        )
        return
    
    if len(location) < 2 or len(location) > 100:
        bot.reply_to(message, "❌ Invalid location. Try again or use 'Skip Location':")
        return
    
    user_temp_data[user_id]['location_text'] = location
    user_states[user_id] = "awaiting_about"
    
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
    
    preview = f"📋 **Profile Preview**\n\n"
    preview += f"👤 Name: {temp.get('name')}\n"
    preview += f"⚧ Gender: {'Male' if temp.get('gender') == 'male' else 'Female'}\n"
    preview += f"🎂 Age: {temp.get('age')}\n"
    preview += f"📍 Location: {temp.get('location_text', 'Not provided')}\n"
    preview += f"📝 About: {temp.get('about', 'Not provided')[:100]}\n"
    preview += f"📷 Media: {len(media_list)} file(s)\n\n"
    preview += f"Confirm to save your profile?"
    
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
    
    temp = user_temp_data.get(user_id, {})
    media_list = temp.get('media_list', [])
    
    media_urls = []
    for media in media_list:
        url = upload_media_to_channel(bot, media['file_id'], user_id, media['type'])
        if url:
            media_urls.append(url)
    
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
    
    db.get_collection("users").update_one(
        {"user_id": user_id},
        {"$set": {"preference": preference, "setup_complete": True}}
    )
    
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_temp_data:
        del user_temp_data[user_id]
    
    markup = types.ReplyKeyboardRemove()
    bot.reply_to(message, "✅ Preference saved!", reply_markup=markup)
    
    show_main_menu(bot, message.chat.id)


def show_main_menu(bot, chat_id):
    """Show main menu with bottom buttons"""
    unread_count = db.get_collection("notifications").count_documents({"user_id": chat_id, "is_read": False})
    
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


# ========== EDIT PROFILE FUNCTIONS ==========

def handle_edit_profile(bot, message, user_states, user_temp_data):
    """Handle edit profile button - start edit process"""
    user_id = message.from_user.id
    
    # Get current profile
    profile = db.get_collection("profiles").find_one({"user_id": user_id})
    if not profile:
        bot.reply_to(message, "❌ Profile not found! Use /start to create one.")
        return
    
    # Store current profile in temp data for editing
    user_temp_data[user_id] = {
        'edit_mode': True,
        'original_profile': profile,
        'updated_data': profile.copy()
    }
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_name = types.KeyboardButton("✏️ Edit Name")
    btn_age = types.KeyboardButton("✏️ Edit Age")
    btn_gender = types.KeyboardButton("✏️ Edit Gender")
    btn_location = types.KeyboardButton("✏️ Edit Location")
    btn_about = types.KeyboardButton("✏️ Edit About")
    btn_media = types.KeyboardButton("✏️ Edit Photos/Videos")
    btn_done = types.KeyboardButton("✅ Done Editing")
    btn_cancel = types.KeyboardButton("❌ Cancel")
    markup.add(btn_name, btn_age, btn_gender, btn_location, btn_about, btn_media, btn_done, btn_cancel)
    
    current_text = f"✏️ **EDIT PROFILE** ✏️\n\n"
    current_text += f"Current Details:\n"
    current_text += f"├ 📛 Name: {profile.get('name', 'Not set')}\n"
    current_text += f"├ ⚧ Gender: {profile.get('gender', 'Not set')}\n"
    current_text += f"├ 🎂 Age: {profile.get('age', 'Not set')}\n"
    current_text += f"├ 📍 Location: {profile.get('location_text', 'Not set')}\n"
    current_text += f"├ 📝 About: {profile.get('about', 'Not set')[:50]}...\n"
    current_text += f"└ 📷 Media: {len(profile.get('media', []))} file(s)\n\n"
    current_text += f"Select what you want to edit:"
    
    user_states[user_id] = "editing_profile"
    
    bot.reply_to(message, current_text, reply_markup=markup, parse_mode='Markdown')


def handle_edit_name(bot, message, user_states, user_temp_data):
    """Handle edit name"""
    user_id = message.from_user.id
    
    user_states[user_id] = "editing_name"
    
    markup = types.ReplyKeyboardRemove()
    
    bot.reply_to(
        message,
        "✏️ **Edit Name**\n\n"
        f"Current Name: {user_temp_data[user_id].get('updated_data', {}).get('name', 'Not set')}\n\n"
        "Send your new name (2-50 characters):\n"
        "Or send /skip to keep current name:",
        reply_markup=markup,
        parse_mode='Markdown'
    )


def process_edit_name(bot, message, user_states, user_temp_data):
    """Process new name input"""
    user_id = message.from_user.id
    new_name = message.text.strip()
    
    if new_name == '/skip':
        bot.reply_to(message, "✅ Name kept as is.")
    elif len(new_name) < 2 or len(new_name) > 50:
        bot.reply_to(message, "❌ Name must be 2-50 characters. Try again or /skip:")
        return
    else:
        user_temp_data[user_id]['updated_data']['name'] = new_name
        bot.reply_to(message, f"✅ Name updated to: {new_name}")
    
    user_states[user_id] = "editing_profile"
    show_edit_menu(bot, message, user_states, user_temp_data)


def handle_edit_age(bot, message, user_states, user_temp_data):
    """Handle edit age"""
    user_id = message.from_user.id
    
    user_states[user_id] = "editing_age"
    
    markup = types.ReplyKeyboardRemove()
    
    bot.reply_to(
        message,
        "✏️ **Edit Age**\n\n"
        f"Current Age: {user_temp_data[user_id].get('updated_data', {}).get('age', 'Not set')}\n\n"
        "Send your new age (18-100):\n"
        "Or send /skip to keep current age:",
        reply_markup=markup,
        parse_mode='Markdown'
    )


def process_edit_age(bot, message, user_states, user_temp_data):
    """Process new age input"""
    user_id = message.from_user.id
    
    if message.text == '/skip':
        bot.reply_to(message, "✅ Age kept as is.")
    else:
        try:
            new_age = int(message.text.strip())
            if new_age < 18 or new_age > 100:
                raise ValueError
            user_temp_data[user_id]['updated_data']['age'] = new_age
            bot.reply_to(message, f"✅ Age updated to: {new_age}")
        except:
            bot.reply_to(message, "❌ Invalid age! Send number between 18-100 or /skip:")
            return
    
    user_states[user_id] = "editing_profile"
    show_edit_menu(bot, message, user_states, user_temp_data)


def handle_edit_gender(bot, message, user_states, user_temp_data):
    """Handle edit gender"""
    user_id = message.from_user.id
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_male = types.KeyboardButton("👨 Male")
    btn_female = types.KeyboardButton("👩 Female")
    markup.add(btn_male, btn_female)
    
    current_gender = user_temp_data[user_id].get('updated_data', {}).get('gender', 'Not set')
    
    bot.reply_to(
        message,
        "✏️ **Edit Gender**\n\n"
        f"Current Gender: {current_gender}\n\n"
        "Select new gender:",
        reply_markup=markup,
        parse_mode='Markdown'
    )


def process_edit_gender(bot, message, user_states, user_temp_data):
    """Process new gender selection"""
    user_id = message.from_user.id
    gender_text = message.text.strip()
    
    if gender_text == "👨 Male":
        new_gender = "male"
    elif gender_text == "👩 Female":
        new_gender = "female"
    else:
        bot.reply_to(message, "❌ Please select gender using the buttons below:")
        return
    
    user_temp_data[user_id]['updated_data']['gender'] = new_gender
    bot.reply_to(message, f"✅ Gender updated to: {gender_text}")
    
    user_states[user_id] = "editing_profile"
    show_edit_menu(bot, message, user_states, user_temp_data)


def handle_edit_location(bot, message, user_states, user_temp_data):
    """Handle edit location"""
    user_id = message.from_user.id
    
    user_states[user_id] = "editing_location"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_skip = types.KeyboardButton("⏭️ Skip (keep current)")
    markup.add(btn_skip)
    
    current_location = user_temp_data[user_id].get('updated_data', {}).get('location_text', 'Not set')
    
    bot.reply_to(
        message,
        "✏️ **Edit Location**\n\n"
        f"Current Location: {current_location}\n\n"
        "Send new location (city name):\n"
        "Or tap 'Skip' to keep current location:",
        reply_markup=markup,
        parse_mode='Markdown'
    )


def process_edit_location(bot, message, user_states, user_temp_data):
    """Process new location input"""
    user_id = message.from_user.id
    
    if message.text == "⏭️ Skip (keep current)":
        bot.reply_to(message, "✅ Location kept as is.")
    else:
        new_location = message.text.strip()
        if len(new_location) < 2:
            bot.reply_to(message, "❌ Invalid location. Try again or tap Skip:")
            return
        user_temp_data[user_id]['updated_data']['location_text'] = new_location
        bot.reply_to(message, f"✅ Location updated to: {new_location}")
    
    user_states[user_id] = "editing_profile"
    show_edit_menu(bot, message, user_states, user_temp_data)


def handle_edit_about(bot, message, user_states, user_temp_data):
    """Handle edit about"""
    user_id = message.from_user.id
    
    user_states[user_id] = "editing_about"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn_skip = types.KeyboardButton("⏭️ Skip (keep current)")
    markup.add(btn_skip)
    
    current_about = user_temp_data[user_id].get('updated_data', {}).get('about', 'Not set')
    
    bot.reply_to(
        message,
        "✏️ **Edit About**\n\n"
        f"Current About: {current_about[:100]}\n\n"
        "Send new about (max 500 characters):\n"
        "Or tap 'Skip' to keep current about:",
        reply_markup=markup,
        parse_mode='Markdown'
    )


def process_edit_about(bot, message, user_states, user_temp_data):
    """Process new about input"""
    user_id = message.from_user.id
    
    if message.text == "⏭️ Skip (keep current)":
        bot.reply_to(message, "✅ About kept as is.")
    else:
        new_about = message.text.strip()
        if len(new_about) > 500:
            bot.reply_to(message, "❌ About too long! Max 500 characters. Try again or Skip:")
            return
        user_temp_data[user_id]['updated_data']['about'] = new_about
        bot.reply_to(message, f"✅ About updated!")
    
    user_states[user_id] = "editing_profile"
    show_edit_menu(bot, message, user_states, user_temp_data)


def handle_edit_media(bot, message, user_states, user_temp_data):
    """Handle edit media"""
    user_id = message.from_user.id
    
    user_states[user_id] = "editing_media"
    user_temp_data[user_id]['new_media_list'] = []
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn_skip = types.KeyboardButton("⏭️ Skip (keep current)")
    btn_done = types.KeyboardButton("✅ Done with media")
    markup.add(btn_skip, btn_done)
    
    current_media_count = len(user_temp_data[user_id].get('updated_data', {}).get('media', []))
    
    bot.reply_to(
        message,
        "✏️ **Edit Photos/Videos**\n\n"
        f"Current Media: {current_media_count} file(s)\n\n"
        "Send new photos/videos (max 3):\n"
        "Send one by one, then tap 'Done with media'\n"
        "Or tap 'Skip' to keep current media:",
        reply_markup=markup,
        parse_mode='Markdown'
    )


def process_edit_media(bot, message, user_states, user_temp_data):
    """Process new media input"""
    user_id = message.from_user.id
    
    if message.text == "⏭️ Skip (keep current)":
        bot.reply_to(message, "✅ Media kept as is.")
        user_states[user_id] = "editing_profile"
        show_edit_menu(bot, message, user_states, user_temp_data)
        return
    
    if message.text == "✅ Done with media":
        # Save new media to updated_data
        new_media = user_temp_data[user_id].get('new_media_list', [])
        if new_media:
            user_temp_data[user_id]['updated_data']['media'] = new_media
            bot.reply_to(message, f"✅ Media updated! {len(new_media)} file(s) saved.")
        else:
            bot.reply_to(message, "✅ No new media added. Keeping current media.")
        user_states[user_id] = "editing_profile"
        show_edit_menu(bot, message, user_states, user_temp_data)
        return
    
    # Handle photo/video upload
    media_list = user_temp_data[user_id].get('new_media_list', [])
    
    if len(media_list) >= 3:
        bot.reply_to(message, "❌ Max 3 media files already! Tap 'Done with media' to finish.")
        return
    
    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = 'photo'
    elif message.video:
        file_id = message.video.file_id
        media_type = 'video'
    else:
        bot.reply_to(message, "❌ Please send photo or video only!")
        return
    
    # Upload to channel
    url = upload_media_to_channel(bot, file_id, user_id, media_type)
    if url:
        media_list.append(url)
        user_temp_data[user_id]['new_media_list'] = media_list
        remaining = 3 - len(media_list)
        bot.reply_to(message, f"✅ Media {len(media_list)}/3 added!\n📷 {remaining} remaining. Send more or tap 'Done with media'.")
    else:
        bot.reply_to(message, "❌ Failed to upload media. Try again.")


def save_edited_profile(bot, message, user_states, user_temp_data):
    """Save all edited changes to database"""
    user_id = message.from_user.id
    updated_data = user_temp_data.get(user_id, {}).get('updated_data', {})
    
    if not updated_data:
        bot.reply_to(message, "❌ No changes to save!")
        show_main_menu(bot, message.chat.id)
        return
    
    # Update profile in database
    update_fields = {}
    for key in ['name', 'gender', 'age', 'location_text', 'about', 'media']:
        if key in updated_data:
            update_fields[key] = updated_data[key]
    
    update_fields['updated_at'] = datetime.utcnow()
    
    result = db.get_collection("profiles").update_one(
        {"user_id": user_id},
        {"$set": update_fields}
    )
    
    if result.modified_count > 0:
        bot.reply_to(message, "✅ **Profile updated successfully!**")
    else:
        bot.reply_to(message, "ℹ️ No changes were made to your profile.")
    
    # Clean up
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_temp_data:
        del user_temp_data[user_id]
    
    show_main_menu(bot, message.chat.id)


def cancel_edit(bot, message, user_states, user_temp_data):
    """Cancel editing"""
    user_id = message.from_user.id
    
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_temp_data:
        del user_temp_data[user_id]
    
    bot.reply_to(message, "❌ Editing cancelled.")
    show_main_menu(bot, message.chat.id)


def show_edit_menu(bot, message, user_states, user_temp_data):
    """Show edit menu again after each edit"""
    user_id = message.from_user.id
    updated_data = user_temp_data.get(user_id, {}).get('updated_data', {})
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_name = types.KeyboardButton("✏️ Edit Name")
    btn_age = types.KeyboardButton("✏️ Edit Age")
    btn_gender = types.KeyboardButton("✏️ Edit Gender")
    btn_location = types.KeyboardButton("✏️ Edit Location")
    btn_about = types.KeyboardButton("✏️ Edit About")
    btn_media = types.KeyboardButton("✏️ Edit Photos/Videos")
    btn_save = types.KeyboardButton("💾 Save All Changes")
    btn_cancel = types.KeyboardButton("❌ Cancel")
    markup.add(btn_name, btn_age, btn_gender, btn_location, btn_about, btn_media, btn_save, btn_cancel)
    
    text = f"✏️ **EDIT PROFILE** ✏️\n\n"
    text += f"Updated Details:\n"
    text += f"├ 📛 Name: {updated_data.get('name', 'Not set')}\n"
    text += f"├ ⚧ Gender: {updated_data.get('gender', 'Not set')}\n"
    text += f"├ 🎂 Age: {updated_data.get('age', 'Not set')}\n"
    text += f"├ 📍 Location: {updated_data.get('location_text', 'Not set')}\n"
    text += f"├ 📝 About: {updated_data.get('about', 'Not set')[:50]}...\n"
    text += f"└ 📷 Media: {len(updated_data.get('media', []))} file(s)\n\n"
    text += f"Select what you want to edit, or click Save when done:"
    
    bot.reply_to(message, text, reply_markup=markup, parse_mode='Markdown')


# ========== CHANGE INTEREST FUNCTIONS ==========

def handle_change_interest(bot, message, user_states, user_temp_data):
    """Handle change interest button"""
    user_id = message.from_user.id
    user_states[user_id] = "awaiting_interest_change"
    
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
    
    db.get_collection("users").update_one(
        {"user_id": user_id},
        {"$set": {"preference": preference}}
    )
    
    if user_id in user_states:
        del user_states[user_id]
    
    bot.reply_to(message, f"✅ Preference updated to: {preference_text}")
    show_main_menu(bot, message.chat.id)


# ========== STATS & SETTINGS FUNCTIONS ==========

def handle_my_stats(bot, message):
    """Handle my stats button"""
    user_id = message.from_user.id
    
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
        "Tap 'Confirm Delete' to proceed.",
        reply_markup=markup
    )


def handle_confirm_delete(bot, message):
    """Handle account deletion - SET is_active = False"""
    user_id = message.from_user.id
    
    # Soft delete - set is_active to False
    db.get_collection("profiles").update_one(
        {"user_id": user_id},
        {"$set": {"is_active": False}}
    )
    
    # Also update users collection
    db.get_collection("users").update_one(
        {"user_id": user_id},
        {"$set": {"is_active": False, "setup_complete": False}}
    )
    
    # Delete likes, notifications, messages (optional - or keep for history)
    db.get_collection("likes").delete_many({"$or": [{"from_user": user_id}, {"to_user": user_id}]})
    db.get_collection("notifications").delete_many({"user_id": user_id})
    db.get_collection("messages").delete_many({"$or": [{"from_user": user_id}, {"to_user": user_id}]})
    
    markup = types.ReplyKeyboardRemove()
    bot.reply_to(
        message,
        "🗑 Your account has been deactivated.\n\n"
        "Your profile will no longer be visible to others.\n"
        "Use /start to create a new profile.",
        reply_markup=markup
    )
```

---


📋 Is file mein kya add/change hua:

Change Description
1. Edit Profile - Full edit functionality added (name, age, gender, location, about, media)
2. Delete Account - is_active = False set karta hai (soft delete)
3. Edit menu - Saare options ke saath edit menu
4. Save changes - Database update karta hai

---

🔥 Agli file (2/4) konsi hai?

Batao:

· handlers/view_profiles.py (Media display + Deleted profiles filter + Chat fix)
· handlers/chat.py
· app.py
