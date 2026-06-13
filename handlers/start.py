import logging
from telebot import types
from database import get_db
from utils.force_join import check_channel_membership

logger = logging.getLogger(__name__)
db = get_db()


def handle_start(bot, message, user_states, user_temp_data):
    """Handle /start command"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    logger.info(f"User {user_id} ({user_name}) started the bot")
    
    # Check if user has profile
    existing_profile = db.get_collection("profiles").find_one({"user_id": user_id, "is_active": True})
    existing_user = db.get_collection("users").find_one({"user_id": user_id})
    
    # Check channel membership
    is_member = check_channel_membership(bot, user_id)
    
    if not is_member:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        btn_join = types.KeyboardButton("📢 JOIN CHANNEL")
        btn_verify = types.KeyboardButton("✅ VERIFY")
        markup.add(btn_join, btn_verify)
        
        bot.reply_to(
            message,
            "🔐 **ACCESS RESTRICTED**\n\n"
            "You must join @nrtecno2 to use this bot!\n\n"
            "1. Tap JOIN CHANNEL\n"
            "2. Join the channel\n"
            "3. Tap VERIFY",
            reply_markup=markup
        )
        return
    
    if existing_profile and existing_user and existing_user.get('setup_complete', False):
        show_main_menu(bot, message.chat.id)
    else:
        start_profile_creation(bot, message, user_states, user_temp_data)


def handle_join_channel(bot, message):
    """Handle JOIN CHANNEL button"""
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("📢 Join @nrtecno2", url="https://t.me/nrtecno2")
    markup.add(btn)
    bot.reply_to(message, "🔗 Click below to join:", reply_markup=markup)


def handle_verify(bot, message, user_states, user_temp_data):
    """Handle VERIFY button"""
    user_id = message.from_user.id
    
    is_member = check_channel_membership(bot, user_id)
    
    if is_member:
        existing_profile = db.get_collection("profiles").find_one({"user_id": user_id, "is_active": True})
        
        if existing_profile:
            show_main_menu(bot, message.chat.id)
        else:
            start_profile_creation(bot, message, user_states, user_temp_data)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        btn_join = types.KeyboardButton("📢 JOIN CHANNEL")
        btn_verify = types.KeyboardButton("🔄 VERIFY AGAIN")
        markup.add(btn_join, btn_verify)
        
        bot.reply_to(
            message,
            "❌ Still not a member of @nrtecno2!\n\nPlease join and verify again.",
            reply_markup=markup
        )


def start_profile_creation(bot, message, user_states, user_temp_data):
    """Start profile creation process"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    user_states[user_id] = "awaiting_name"
    user_temp_data[user_id] = {}
    
    markup = types.ReplyKeyboardRemove()
    
    bot.reply_to(
        message,
        f"🌟 **WELCOME {user_name.upper()}!** 🌟\n\n"
        f"Let's create your dating profile!\n\n"
        f"**Step 1/7: Your Name**\n"
        f"Send your name (2-50 characters):",
        reply_markup=markup
    )


def process_name(bot, message, user_states, user_temp_data):
    """Process name input and ask for gender"""
    user_id = message.from_user.id
    name = message.text.strip()
    
    if len(name) < 2 or len(name) > 50:
        bot.reply_to(message, "❌ Name must be 2-50 characters. Try again:")
        bot.register_next_step_handler(message, process_name, user_states, user_temp_data)
        return
    
    user_temp_data[user_id]['name'] = name
    user_states[user_id] = "awaiting_gender"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("👨 Male"), types.KeyboardButton("👩 Female"))
    
    bot.reply_to(
        message,
        f"✅ Name: {name}\n\n**Step 2/7: Your Gender**\n"
        f"Select your gender:",
        reply_markup=markup
    )


def process_gender(bot, message, user_states, user_temp_data):
    """Process gender selection and ask for age"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    if text == "👨 Male":
        gender = "male"
    elif text == "👩 Female":
        gender = "female"
    else:
        bot.reply_to(message, "❌ Please tap Male or Female button:")
        bot.register_next_step_handler(message, process_gender, user_states, user_temp_data)
        return
    
    user_temp_data[user_id]['gender'] = gender
    user_states[user_id] = "awaiting_age"
    
    markup = types.ReplyKeyboardRemove()
    
    bot.reply_to(
        message,
        f"✅ Gender: {text}\n\n**Step 3/7: Your Age**\n"
        f"Send your age (18-100):",
        reply_markup=markup
    )


def process_age(bot, message, user_states, user_temp_data):
    """Process age input and ask for location"""
    user_id = message.from_user.id
    
    try:
        age = int(message.text.strip())
        if age < 18 or age > 100:
            raise ValueError
    except:
        bot.reply_to(message, "❌ Invalid age! Send number between 18-100:")
        bot.register_next_step_handler(message, process_age, user_states, user_temp_data)
        return
    
    user_temp_data[user_id]['age'] = age
    user_states[user_id] = "awaiting_location"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("📍 Send Location", request_location=True))
    markup.add(types.KeyboardButton("⏭️ Skip"))
    
    bot.reply_to(
        message,
        f"✅ Age: {age}\n\n**Step 4/7: Your Location (Optional)**\n\n"
        f"📍 Share your location for better nearby matches!\n\n"
        f"Options:\n"
        f"• Tap 'Send Location' to share\n"
        f"• Type city name (e.g., Mumbai)\n"
        f"• Tap 'Skip' to skip location\n\n"
        f"Send location or type city name:",
        reply_markup=markup
    )


def process_location(bot, message, user_states, user_temp_data):
    """Process location and ask for about"""
    user_id = message.from_user.id
    
    if message.location:
        user_temp_data[user_id]['latitude'] = message.location.latitude
        user_temp_data[user_id]['longitude'] = message.location.longitude
        user_temp_data[user_id]['location_text'] = f"{message.location.latitude}, {message.location.longitude}"
        bot.reply_to(message, "✅ Location saved!")
    elif message.text and message.text.strip() == "⏭️ Skip":
        user_temp_data[user_id]['location_text'] = ""
        bot.reply_to(message, "✅ Location skipped!")
    elif message.text:
        location = message.text.strip()
        if len(location) < 2:
            bot.reply_to(message, "❌ Invalid location. Try again or tap Skip:")
            bot.register_next_step_handler(message, process_location, user_states, user_temp_data)
            return
        user_temp_data[user_id]['location_text'] = location
        bot.reply_to(message, f"✅ Location: {location}")
    else:
        bot.reply_to(message, "❌ Please send location or type city name:")
        bot.register_next_step_handler(message, process_location, user_states, user_temp_data)
        return
    
    user_states[user_id] = "awaiting_about"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(types.KeyboardButton("/skip"))
    
    bot.reply_to(
        message,
        f"**Step 5/7: About You (Optional)**\n\n"
        f"Send a short bio (max 500 characters)\n"
        f"Or tap /skip to skip:",
        reply_markup=markup
    )


def process_about(bot, message, user_states, user_temp_data):
    """Process about and ask for media"""
    user_id = message.from_user.id
    
    if message.text and message.text.strip() == "/skip":
        user_temp_data[user_id]['about'] = ""
        bot.reply_to(message, "✅ About skipped!")
    else:
        about = message.text.strip()
        if len(about) > 500:
            bot.reply_to(message, "❌ Too long! Max 500 characters:")
            bot.register_next_step_handler(message, process_about, user_states, user_temp_data)
            return
        user_temp_data[user_id]['about'] = about
        bot.reply_to(message, "✅ About saved!")
    
    user_states[user_id] = "awaiting_media"
    user_temp_data[user_id]['media_list'] = []
    
    markup = types.ReplyKeyboardRemove()
    
    bot.reply_to(
        message,
        f"**Step 6/7: Photos/Videos**\n\n"
        f"Send 1-3 photos or videos\n"
        f"Send one by one, then type **/done**\n\n"
        f"📷 Remaining: 3",
        reply_markup=markup
    )


def process_media(bot, message, user_states, user_temp_data):
    """Process media upload"""
    user_id = message.from_user.id
    media_list = user_temp_data[user_id].get('media_list', [])
    
    if len(media_list) >= 3:
        bot.reply_to(message, "❌ Max 3 files! Type /done to continue")
        return
    
    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = 'photo'
    elif message.video:
        file_id = message.video.file_id
        media_type = 'video'
    else:
        bot.reply_to(message, "❌ Send photo or video only!")
        return
    
    media_list.append({'file_id': file_id, 'type': media_type})
    user_temp_data[user_id]['media_list'] = media_list
    remaining = 3 - len(media_list)
    
    if remaining == 0:
        bot.reply_to(message, f"✅ Media {len(media_list)}/3 added!\n\nType /done to continue")
    else:
        bot.reply_to(message, f"✅ Media {len(media_list)}/3 added!\n📷 {remaining} remaining. Send more or /done")


def process_done(bot, message, user_states, user_temp_data):
    """Process /done and show profile preview"""
    user_id = message.from_user.id
    temp = user_temp_data.get(user_id, {})
    media_list = temp.get('media_list', [])
    
    if not temp.get('name') or not temp.get('gender') or not temp.get('age'):
        bot.reply_to(message, "❌ Profile incomplete! Start over with /start")
        return
    
    if len(media_list) == 0:
        bot.reply_to(message, "❌ Please send at least 1 photo or video, then /done")
        return
    
    preview = f"📋 **PROFILE PREVIEW**\n\n"
    preview += f"👤 Name: {temp.get('name')}\n"
    preview += f"⚧ Gender: {'Male' if temp.get('gender') == 'male' else 'Female'}\n"
    preview += f"🎂 Age: {temp.get('age')}\n"
    preview += f"📍 Location: {temp.get('location_text', 'Not provided')}\n"
    preview += f"📝 About: {temp.get('about', 'Not provided')[:100]}\n"
    preview += f"📷 Media: {len(media_list)} file(s)\n\n"
    preview += f"**Step 7/7: Confirm Profile**\n\n"
    preview += f"Tap CONFIRM to save or CANCEL to cancel:"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("✅ CONFIRM"), types.KeyboardButton("❌ CANCEL"))
    
    user_states[user_id] = "awaiting_confirm"
    bot.reply_to(message, preview, reply_markup=markup)


def process_confirm(bot, message, user_states, user_temp_data):
    """Process confirm and save profile to database"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    if text == "❌ CANCEL":
        if user_id in user_states:
            del user_states[user_id]
        if user_id in user_temp_data:
            del user_temp_data[user_id]
        markup = types.ReplyKeyboardRemove()
        bot.reply_to(message, "❌ Profile creation cancelled. Use /start to try again.", reply_markup=markup)
        return
    
    if text != "✅ CONFIRM":
        bot.reply_to(message, "❌ Tap CONFIRM or CANCEL button:")
        return
    
    temp = user_temp_data.get(user_id, {})
    media_list = temp.get('media_list', [])
    
    from utils.storage import upload_media_to_channel
    
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
    db.get_collection("users").update_one({"user_id": user_id}, {"$set": user_data}, upsert=True)
    
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_temp_data:
        del user_temp_data[user_id]
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("👨 Male"), types.KeyboardButton("👩 Female"), types.KeyboardButton("👥 Both"))
    
    bot.reply_to(
        message,
        "🎉 **PROFILE CREATED!** 🎉\n\n"
        "**Final Step: Set Your Preference**\n\n"
        "Who do you want to see in your feed?",
        reply_markup=markup
    )
    
    user_states[user_id] = "awaiting_preference"


def process_preference(bot, message, user_states, user_temp_data):
    """Process preference selection and show main menu"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    if text == "👨 Male":
        preference = "male"
    elif text == "👩 Female":
        preference = "female"
    elif text == "👥 Both":
        preference = "both"
    else:
        bot.reply_to(message, "❌ Tap Male, Female or Both button:")
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
    bot.reply_to(message, f"✅ Preference set to: {text}", reply_markup=markup)
    
    show_main_menu(bot, message.chat.id)


def show_main_menu(bot, chat_id):
    """Show main menu with bottom buttons"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("👤 MY PROFILE"),
        types.KeyboardButton("👀 VIEW PROFILES"),
        types.KeyboardButton("🔔 NOTIFICATIONS"),
        types.KeyboardButton("🎯 CHANGE INTEREST"),
        types.KeyboardButton("📊 STATS"),
        types.KeyboardButton("⚙️ SETTINGS")
    )
    bot.send_message(chat_id, "🏠 **MAIN MENU**\n\nChoose an option:", reply_markup=markup)
