  import logging
from datetime import datetime
from telebot import types
from database import get_db
from utils.storage import upload_media_to_channel

logger = logging.getLogger(__name__)
db = get_db()


def handle_name(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    name = message.text.strip()
    
    if len(name) < 2 or len(name) > 50:
        bot.reply_to(message, "❌ Name must be 2-50 characters. Try again:")
        return
    
    user_temp_data[user_id]['name'] = name
    user_states[user_id] = "awaiting_gender"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("👨 Male"), types.KeyboardButton("👩 Female"))
    
    bot.reply_to(message, f"✅ Name: {name}\n\nNow select your **Gender**:", reply_markup=markup)


def handle_gender_callback(bot, message, user_states, user_temp_data):
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
    bot.reply_to(message, f"✅ Gender: {'Male' if gender == 'male' else 'Female'}\n\nNow send your **Age** (18-100):", reply_markup=markup)


def handle_age(bot, message, user_states, user_temp_data):
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
    markup.add(types.KeyboardButton("📍 Send Live Location", request_location=True))
    markup.add(types.KeyboardButton("⏭️ Skip Location"))
    
    bot.reply_to(message, 
        f"✅ Age: {age}\n\n📍 **Share your location for better matches!**\n\n"
        f"⚠️ Location ka upyog:\n├ → Aapke nearby profiles dikhane ke liye\n"
        f"├ → 50km radius ke log dikhenge\n└ → Aapki privacy safe hai\n\n"
        f"**Option 1:** Share live location (recommended)\n"
        f"**Option 2:** Type city name (e.g., Mumbai, Delhi)\n"
        f"**Option 3:** Tap 'Skip Location' to continue\n\n"
        f"📍 Send location or type city name:", 
        reply_markup=markup)


def handle_location(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    
    if message.location:
        user_temp_data[user_id]['latitude'] = message.location.latitude
        user_temp_data[user_id]['longitude'] = message.location.longitude
        user_temp_data[user_id]['location_text'] = f"{message.location.latitude}, {message.location.longitude}"
        user_states[user_id] = "awaiting_about"
        markup = types.ReplyKeyboardRemove()
        bot.reply_to(message, f"✅ Location saved!\n\nNow send your **About** (max 500 chars):\nOr send /skip to skip", reply_markup=markup)


def handle_location_text(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    location = message.text.strip()
    
    if location == "⏭️ Skip Location":
        user_temp_data[user_id]['location_text'] = ""
        user_temp_data[user_id]['latitude'] = None
        user_temp_data[user_id]['longitude'] = None
        user_states[user_id] = "awaiting_about"
        markup = types.ReplyKeyboardRemove()
        bot.reply_to(message, f"✅ Location skipped!\n\nNow send your **About** (max 500 chars):\nOr send /skip to skip", reply_markup=markup)
        return
    
    if len(location) < 2 or len(location) > 100:
        bot.reply_to(message, "❌ Invalid location. Try again or use 'Skip Location':")
        return
    
    user_temp_data[user_id]['location_text'] = location
    user_states[user_id] = "awaiting_about"
    markup = types.ReplyKeyboardRemove()
    bot.reply_to(message, f"✅ Location: {location}\n\nNow send your **About** (max 500 chars):\nOr send /skip to skip", reply_markup=markup)


def handle_about(bot, message, user_states, user_temp_data):
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
    
    bot.reply_to(message, f"Now send **1-3 photos/videos**\nSend one by one, then send /done\n📷 Remaining slots: 3", parse_mode='Markdown')


def handle_media(bot, message, user_states, user_temp_data):
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
    
    media_list.append({'file_id': file_id, 'type': media_type})
    user_temp_data[user_id]['media_list'] = media_list
    remaining = 3 - len(media_list)
    bot.reply_to(message, f"✅ Media {len(media_list)}/3 added!\n📷 {remaining} remaining. Send more or /done")


def confirm_profile(bot, message, user_states, user_temp_data):
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
    preview += f"📷 Media: {len(media_list)} file(s)\n\nConfirm to save?"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("✅ Confirm Profile"), types.KeyboardButton("❌ Cancel"))
    user_states[user_id] = "awaiting_confirm"
    bot.reply_to(message, preview, reply_markup=markup)


def handle_confirm_callback(bot, message, user_states, user_temp_data):
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
    
    if action == "✅ Confirm Profile":
        temp = user_temp_data.get(user_id, {})
        media_list = temp.get('media_list', [])
        
        media_urls = []
        for media in media_list:
            url = upload_media_to_channel(bot, media['file_id'], user_id, media['type'])
            if url:
                media_urls.append(url)
        
        profile = {
            "user_id": user_id, "username": message.from_user.username,
            "name": temp.get('name'), "gender": temp.get('gender'),
            "age": temp.get('age'), "location_text": temp.get('location_text', ''),
            "latitude": temp.get('latitude'), "longitude": temp.get('longitude'),
            "about": temp.get('about', ''), "media": media_urls,
            "created_at": datetime.utcnow(), "is_active": True
        }
        db.get_collection("profiles").insert_one(profile)
        
        user_data = {
            "user_id": user_id, "username": message.from_user.username,
            "first_name": message.from_user.first_name, "setup_complete": False,
            "created_at": datetime.utcnow(), "last_active": datetime.utcnow()
        }
        db.get_collection("users").update_one({"user_id": user_id}, {"$set": user_data}, upsert=True)
        
        if user_id in user_states:
            del user_states[user_id]
        if user_id in user_temp_data:
            del user_temp_data[user_id]
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(types.KeyboardButton("👨 Male"), types.KeyboardButton("👩 Female"), types.KeyboardButton("👥 Both"))
        
        bot.reply_to(message, "🎉 **Profile Created Successfully!** 🎉\n\nWho do you want to see in your feed?", reply_markup=markup)
        return
    
    bot.reply_to(message, "❌ Please use the Confirm or Cancel buttons below.")


def handle_preference_callback(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    pref_text = message.text.strip()
    
    if pref_text == "👨 Male":
        preference = "male"
    elif pref_text == "👩 Female":
        preference = "female"
    elif pref_text == "👥 Both":
        preference = "both"
    else:
        bot.reply_to(message, "❌ Please use the buttons below:")
        return
    
    db.get_collection("users").update_one({"user_id": user_id}, {"$set": {"preference": preference, "setup_complete": True}})
    
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_temp_data:
        del user_temp_data[user_id]
    
    markup = types.ReplyKeyboardRemove()
    bot.reply_to(message, "✅ Preference saved!", reply_markup=markup)
    show_main_menu(bot, message.chat.id)


def show_main_menu(bot, chat_id):
    unread_count = db.get_collection("notifications").count_documents({"user_id": chat_id, "is_read": False})
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("👤 MY PROFILE"), types.KeyboardButton("👀 VIEW PROFILES"))
    markup.add(types.KeyboardButton(f"🔔 NOTIFICATIONS ({unread_count})"), types.KeyboardButton("🎯 CHANGE INTEREST"))
    markup.add(types.KeyboardButton("📊 MY STATS"), types.KeyboardButton("⚙️ SETTINGS"))
    
    bot.send_message(chat_id, "🏠 **Main Menu**\n\nChoose an option from below:", reply_markup=markup)


def handle_edit_profile(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    profile = db.get_collection("profiles").find_one({"user_id": user_id})
    
    if not profile:
        bot.reply_to(message, "❌ Profile not found! Use /start to create one.")
        return
    
    user_temp_data[user_id] = {'edit_mode': True, 'original_profile': profile, 'updated_data': profile.copy()}
    user_states[user_id] = "editing_profile"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("✏️ Edit Name"), types.KeyboardButton("✏️ Edit Age"))
    markup.add(types.KeyboardButton("✏️ Edit Gender"), types.KeyboardButton("✏️ Edit Location"))
    markup.add(types.KeyboardButton("✏️ Edit About"), types.KeyboardButton("✏️ Edit Photos/Videos"))
    markup.add(types.KeyboardButton("💾 Save All Changes"), types.KeyboardButton("❌ Cancel"))
    
    text = f"✏️ **EDIT PROFILE** ✏️\n\nCurrent Details:\n├ Name: {profile.get('name')}\n├ Gender: {profile.get('gender')}\n├ Age: {profile.get('age')}\n├ Location: {profile.get('location_text')}\n├ About: {profile.get('about', '')[:50]}\n└ Media: {len(profile.get('media', []))} files\n\nSelect what to edit:"
    bot.reply_to(message, text, reply_markup=markup, parse_mode='Markdown')


def handle_edit_name(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    user_states[user_id] = "editing_name"
    markup = types.ReplyKeyboardRemove()
    bot.reply_to(message, "✏️ **Edit Name**\n\nSend new name (2-50 chars) or /skip:", reply_markup=markup, parse_mode='Markdown')


def process_edit_name(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    new_name = message.text.strip()
    
    if new_name == '/skip':
        bot.reply_to(message, "✅ Name kept as is.")
    elif len(new_name) < 2 or len(new_name) > 50:
        bot.reply_to(message, "❌ Name must be 2-50 chars. Try again or /skip:")
        return
    else:
        user_temp_data[user_id]['updated_data']['name'] = new_name
        bot.reply_to(message, f"✅ Name updated to: {new_name}")
    
    user_states[user_id] = "editing_profile"
    show_edit_menu(bot, message, user_states, user_temp_data)


def handle_edit_age(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    user_states[user_id] = "editing_age"
    markup = types.ReplyKeyboardRemove()
    bot.reply_to(message, "✏️ **Edit Age**\n\nSend new age (18-100) or /skip:", reply_markup=markup, parse_mode='Markdown')


def process_edit_age(bot, message, user_states, user_temp_data):
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
            bot.reply_to(message, "❌ Invalid age! Send 18-100 or /skip:")
            return
    
    user_states[user_id] = "editing_profile"
    show_edit_menu(bot, message, user_states, user_temp_data)


def handle_edit_gender(bot, message, user_states, user_temp_data):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("👨 Male"), types.KeyboardButton("👩 Female"))
    bot.reply_to(message, "✏️ **Edit Gender**\n\nSelect new gender:", reply_markup=markup, parse_mode='Markdown')


def process_edit_gender(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    gender_text = message.text.strip()
    
    if gender_text == "👨 Male":
        user_temp_data[user_id]['updated_data']['gender'] = "male"
        bot.reply_to(message, "✅ Gender updated to: Male")
    elif gender_text == "👩 Female":
        user_temp_data[user_id]['updated_data']['gender'] = "female"
        bot.reply_to(message, "✅ Gender updated to: Female")
    else:
        bot.reply_to(message, "❌ Please use the buttons below:")
        return
    
    user_states[user_id] = "editing_profile"
    show_edit_menu(bot, message, user_states, user_temp_data)


def handle_edit_location(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    user_states[user_id] = "editing_location"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(types.KeyboardButton("⏭️ Skip (keep current)"))
    
    current_loc = user_temp_data[user_id].get('updated_data', {}).get('location_text', 'Not set')
    bot.reply_to(message, f"✏️ **Edit Location**\n\nCurrent: {current_loc}\n\nSend new location or tap Skip:", reply_markup=markup, parse_mode='Markdown')


def process_edit_location(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    
    if message.text == "⏭️ Skip (keep current)":
        bot.reply_to(message, "✅ Location kept as is.")
    else:
        new_loc = message.text.strip()
        if len(new_loc) < 2:
            bot.reply_to(message, "❌ Invalid location. Try again or Skip:")
            return
        user_temp_data[user_id]['updated_data']['location_text'] = new_loc
        bot.reply_to(message, f"✅ Location updated to: {new_loc}")
    
    user_states[user_id] = "editing_profile"
    show_edit_menu(bot, message, user_states, user_temp_data)


def handle_edit_about(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    user_states[user_id] = "editing_about"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(types.KeyboardButton("⏭️ Skip (keep current)"))
    
    current_about = user_temp_data[user_id].get('updated_data', {}).get('about', 'Not set')[:100]
    bot.reply_to(message, f"✏️ **Edit About**\n\nCurrent: {current_about}\n\nSend new about (max 500 chars) or Skip:", reply_markup=markup, parse_mode='Markdown')


def process_edit_about(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    
    if message.text == "⏭️ Skip (keep current)":
        bot.reply_to(message, "✅ About kept as is.")
    else:
        new_about = message.text.strip()
        if len(new_about) > 500:
            bot.reply_to(message, "❌ Too long! Max 500 chars. Try again or Skip:")
            return
        user_temp_data[user_id]['updated_data']['about'] = new_about
        bot.reply_to(message, "✅ About updated!")
    
    user_states[user_id] = "editing_profile"
    show_edit_menu(bot, message, user_states, user_temp_data)


def handle_edit_media(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    user_states[user_id] = "editing_media"
    user_temp_data[user_id]['new_media_list'] = []
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(types.KeyboardButton("⏭️ Skip (keep current)"), types.KeyboardButton("✅ Done with media"))
    
    bot.reply_to(message, "✏️ **Edit Photos/Videos**\n\nSend new photos/videos (max 3), then tap 'Done'\nor tap 'Skip' to keep current:", reply_markup=markup, parse_mode='Markdown')


def process_edit_media(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    
    if message.text == "⏭️ Skip (keep current)":
        bot.reply_to(message, "✅ Media kept as is.")
        user_states[user_id] = "editing_profile"
        show_edit_menu(bot, message, user_states, user_temp_data)
        return
    
    if message.text == "✅ Done with media":
        new_media = user_temp_data[user_id].get('new_media_list', [])
        if new_media:
            user_temp_data[user_id]['updated_data']['media'] = new_media
            bot.reply_to(message, f"✅ Media updated! {len(new_media)} file(s) saved.")
        else:
            bot.reply_to(message, "✅ No new media added. Keeping current media.")
        user_states[user_id] = "editing_profile"
        show_edit_menu(bot, message, user_states, user_temp_data)
        return
    
    media_list = user_temp_data[user_id].get('new_media_list', [])
    
    if len(media_list) >= 3:
        bot.reply_to(message, "❌ Max 3 files! Tap 'Done' to finish.")
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
    
    url = upload_media_to_channel(bot, file_id, user_id, media_type)
    if url:
        media_list.append(url)
        user_temp_data[user_id]['new_media_list'] = media_list
        remaining = 3 - len(media_list)
        bot.reply_to(message, f"✅ Media {len(media_list)}/3 added!\n📷 {remaining} remaining. Send more or tap 'Done'.")
    else:
        bot.reply_to(message, "❌ Upload failed. Try again.")


def save_edited_profile(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    updated_data = user_temp_data.get(user_id, {}).get('updated_data', {})
    
    if not updated_data:
        bot.reply_to(message, "❌ No changes to save!")
        show_main_menu(bot, message.chat.id)
        return
    
    update_fields = {}
    for key in ['name', 'gender', 'age', 'location_text', 'about', 'media']:
        if key in updated_data:
            update_fields[key] = updated_data[key]
    update_fields['updated_at'] = datetime.utcnow()
    
    result = db.get_collection("profiles").update_one({"user_id": user_id}, {"$set": update_fields})
    
    if result.modified_count > 0:
        bot.reply_to(message, "✅ **Profile updated successfully!**")
    else:
        bot.reply_to(message, "ℹ️ No changes were made to your profile.")
    
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_temp_data:
        del user_temp_data[user_id]
    
    show_main_menu(bot, message.chat.id)


def cancel_edit(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_temp_data:
        del user_temp_data[user_id]
    
    bot.reply_to(message, "❌ Editing cancelled.")
    show_main_menu(bot, message.chat.id)


def show_edit_menu(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    data = user_temp_data.get(user_id, {}).get('updated_data', {})
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("✏️ Edit Name"), types.KeyboardButton("✏️ Edit Age"))
    markup.add(types.KeyboardButton("✏️ Edit Gender"), types.KeyboardButton("✏️ Edit Location"))
    markup.add(types.KeyboardButton("✏️ Edit About"), types.KeyboardButton("✏️ Edit Photos/Videos"))
    markup.add(types.KeyboardButton("💾 Save All Changes"), types.KeyboardButton("❌ Cancel"))
    
    text = f"✏️ **EDIT PROFILE** ✏️\n\nUpdated Details:\n├ Name: {data.get('name', 'Not set')}\n├ Gender: {data.get('gender', 'Not set')}\n├ Age: {data.get('age', 'Not set')}\n├ Location: {data.get('location_text', 'Not set')}\n├ About: {data.get('about', 'Not set')[:50]}\n└ Media: {len(data.get('media', []))} files\n\nSelect option or Save:"
    bot.reply_to(message, text, reply_markup=markup, parse_mode='Markdown')


def handle_change_interest(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    user_states[user_id] = "awaiting_interest_change"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("👨 Male"), types.KeyboardButton("👩 Female"))
    markup.add(types.KeyboardButton("👥 Both"), types.KeyboardButton("🔙 Back to Main Menu"))
    
    bot.reply_to(message, "🎯 **Change Interest / Preference**\n\nSelect who you want to see:", reply_markup=markup)


def handle_update_preference(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    pref_text = message.text.strip()
    
    if pref_text == "👨 Male":
        db.get_collection("users").update_one({"user_id": user_id}, {"$set": {"preference": "male"}})
        bot.reply_to(message, "✅ Preference updated to: Male")
    elif pref_text == "👩 Female":
        db.get_collection("users").update_one({"user_id": user_id}, {"$set": {"preference": "female"}})
        bot.reply_to(message, "✅ Preference updated to: Female")
    elif pref_text == "👥 Both":
        db.get_collection("users").update_one({"user_id": user_id}, {"$set": {"preference": "both"}})
        bot.reply_to(message, "✅ Preference updated to: Both")
    elif pref_text == "🔙 Back to Main Menu":
        show_main_menu(bot, message.chat.id)
        return
    else:
        bot.reply_to(message, "❌ Please use the buttons below:")
        return
    
    if user_id in user_states:
        del user_states[user_id]
    
    show_main_menu(bot, message.chat.id)


def handle_my_stats(bot, message):
    user_id = message.from_user.id
    
    user = db.get_collection("users").find_one({"user_id": user_id})
    profile = db.get_collection("profiles").find_one({"user_id": user_id})
    likes_given = db.get_collection("likes").count_documents({"from_user": user_id})
    likes_received = db.get_collection("likes").count_documents({"to_user": user_id})
    
    stats_text = f"📊 **YOUR STATS** 📊\n\n👤 Profile Views: {profile.get('profile_views', 0) if profile else 0}\n❤️ Likes Given: {likes_given}\n💕 Likes Received: {likes_received}\n🎯 Interest: {user.get('preference', 'Not set') if user else 'Not set'}\n\nKeep interacting! 🔥"
    bot.reply_to(message, stats_text, parse_mode='Markdown')


def handle_settings(bot, message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(types.KeyboardButton("🗑 Delete Account"), types.KeyboardButton("🔙 Back to Main Menu"))
    bot.reply_to(message, "⚙️ **SETTINGS** ⚙️\n\nChoose an option:", reply_markup=markup)


def handle_delete_account(bot, message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("🗑 Confirm Delete"), types.KeyboardButton("🔙 Cancel"))
    bot.reply_to(message, "⚠️ **DELETE ACCOUNT** ⚠️\n\nThis is permanent!\nTap 'Confirm Delete' to proceed:", reply_markup=markup)


def handle_confirm_delete(bot, message):
    user_id = message.from_user.id
    
    db.get_collection("profiles").update_one({"user_id": user_id}, {"$set": {"is_active": False}})
    db.get_collection("users").update_one({"user_id": user_id}, {"$set": {"is_active": False, "setup_complete": False}})
    db.get_collection("likes").delete_many({"$or": [{"from_user": user_id}, {"to_user": user_id}]})
    db.get_collection("notifications").delete_many({"user_id": user_id})
    db.get_collection("messages").delete_many({"$or": [{"from_user": user_id}, {"to_user": user_id}]})
    
    markup = types.ReplyKeyboardRemove()
    bot.reply_to(message, "🗑 Account deleted.\nUse /start to create new profile.", reply_markup=markup)
