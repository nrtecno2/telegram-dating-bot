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
    bot.reply_to(message, f"✅ Age: {age}\n\n📍 Share location or type city name:", reply_markup=markup)


def handle_location(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    
    if message.location:
        user_temp_data[user_id]['latitude'] = message.location.latitude
        user_temp_data[user_id]['longitude'] = message.location.longitude
        user_temp_data[user_id]['location_text'] = f"{message.location.latitude}, {message.location.longitude}"
        user_states[user_id] = "awaiting_about"
        markup = types.ReplyKeyboardRemove()
        bot.reply_to(message, "✅ Location saved!\n\nSend your **About** (max 500 chars) or /skip:", reply_markup=markup)


def handle_location_text(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    location = message.text.strip()
    
    if location == "⏭️ Skip Location":
        user_temp_data[user_id]['location_text'] = ""
        user_states[user_id] = "awaiting_about"
        markup = types.ReplyKeyboardRemove()
        bot.reply_to(message, "✅ Location skipped!\n\nSend your **About** (max 500 chars) or /skip:", reply_markup=markup)
        return
    
    if len(location) < 2:
        bot.reply_to(message, "❌ Invalid location. Try again or use Skip:")
        return
    
    user_temp_data[user_id]['location_text'] = location
    user_states[user_id] = "awaiting_about"
    markup = types.ReplyKeyboardRemove()
    bot.reply_to(message, f"✅ Location: {location}\n\nSend your **About** (max 500 chars) or /skip:", reply_markup=markup)


def handle_about(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    
    if message.text and message.text == '/skip':
        user_temp_data[user_id]['about'] = ""
        bot.reply_to(message, "✅ About skipped!")
    else:
        about = message.text.strip()
        if len(about) > 500:
            bot.reply_to(message, "❌ About too long! Max 500 characters:")
            return
        user_temp_data[user_id]['about'] = about
        bot.reply_to(message, "✅ About saved!")
    
    user_states[user_id] = "awaiting_media"
    user_temp_data[user_id]['media_list'] = []
    bot.reply_to(message, "Send **1-3 photos/videos**, then send /done\n📷 Remaining: 3")


def handle_media(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    media_list = user_temp_data[user_id].get('media_list', [])
    
    if len(media_list) >= 3:
        bot.reply_to(message, "❌ Max 3 files! Send /done")
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
    bot.reply_to(message, f"✅ Media {len(media_list)}/3 added!\n📷 {remaining} remaining. Send more or /done")


def confirm_profile(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    temp = user_temp_data.get(user_id, {})
    media_list = temp.get('media_list', [])
    
    if not temp.get('name') or not temp.get('gender') or not temp.get('age'):
        bot.reply_to(message, "❌ Profile incomplete! Start over with /start")
        return
    
    preview = f"📋 **Profile Preview**\n\n"
    preview += f"👤 Name: {temp.get('name')}\n"
    preview += f"⚧ Gender: {'Male' if temp.get('gender') == 'male' else 'Female'}\n"
    preview += f"🎂 Age: {temp.get('age')}\n"
    preview += f"📍 Location: {temp.get('location_text', 'Not provided')}\n"
    preview += f"📝 About: {temp.get('about', 'Not provided')[:100]}\n"
    preview += f"📷 Media: {len(media_list)} file(s)\n\nConfirm to save?"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("✅ Confirm"), types.KeyboardButton("❌ Cancel"))
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
        bot.reply_to(message, "❌ Profile creation cancelled.", reply_markup=markup)
        return
    
    if action == "✅ Confirm":
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
        db.get_collection("users").update_one({"user_id": user_id}, {"$set": user_data}, upsert=True)
        
        if user_id in user_states:
            del user_states[user_id]
        if user_id in user_temp_data:
            del user_temp_data[user_id]
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(types.KeyboardButton("👨 Male"), types.KeyboardButton("👩 Female"), types.KeyboardButton("👥 Both"))
        bot.reply_to(message, "🎉 **Profile Created!** 🎉\n\nWho do you want to see?", reply_markup=markup)
        return
    
    bot.reply_to(message, "❌ Please use Confirm or Cancel buttons.")


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
        bot.reply_to(message, "❌ Use the buttons below:")
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
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("👤 MY PROFILE"), types.KeyboardButton("👀 VIEW PROFILES"))
    markup.add(types.KeyboardButton("🔔 NOTIFICATIONS"), types.KeyboardButton("🎯 CHANGE INTEREST"))
    markup.add(types.KeyboardButton("📊 STATS"), types.KeyboardButton("⚙️ SETTINGS"))
    bot.send_message(chat_id, "🏠 **Main Menu**\n\nChoose an option:", reply_markup=markup)


def handle_my_profile(bot, message):
    user_id = message.from_user.id
    profile = db.get_collection("profiles").find_one({"user_id": user_id, "is_active": True})
    
    if not profile:
        bot.reply_to(message, "❌ No profile found. Use /start")
        return
    
    text = f"👤 **YOUR PROFILE**\n\n📛 Name: {profile['name']}\n⚧ Gender: {profile['gender']}\n🎂 Age: {profile['age']}\n📍 Location: {profile.get('location_text', 'Not set')}"
    bot.reply_to(message, text)


def handle_view_profiles(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    my_profile = db.get_collection("profiles").find_one({"user_id": user_id, "is_active": True})
    
    if not my_profile:
        bot.reply_to(message, "❌ Create profile first! Use /start")
        return
    
    user = db.get_collection("users").find_one({"user_id": user_id})
    preference = user.get('preference', 'both')
    
    query = {"user_id": {"$ne": user_id}, "is_active": True}
    if preference == 'male':
        query["gender"] = "male"
    elif preference == 'female':
        query["gender"] = "female"
    
    liked = db.get_collection("likes").distinct("to_user", {"from_user": user_id})
    query["user_id"] = {"$nin": liked}
    
    profiles = list(db.get_collection("profiles").find(query).limit(50))
    
    if not profiles:
        bot.reply_to(message, "😔 No profiles found!\nTry changing your preference.")
        return
    
    user_states[user_id] = {'profiles': profiles, 'index': 0}
    show_profile(bot, user_id, user_states)


def show_profile(bot, user_id, user_states):
    data = user_states.get(user_id)
    if not data:
        return
    
    profiles = data['profiles']
    index = data['index']
    
    if index >= len(profiles):
        bot.send_message(user_id, "🏁 No more profiles!\nStart over with VIEW PROFILES")
        return
    
    profile = profiles[index]
    text = f"👤 {profile['name']}\n🎂 Age: {profile['age']}\n📍 {profile.get('location_text', 'No location')}"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("❤️ LIKE"), types.KeyboardButton("⏭️ SKIP"))
    markup.add(types.KeyboardButton("🛑 STOP"))
    
    bot.send_message(user_id, text, reply_markup=markup)
    user_states[user_id]['current_profile'] = profile['user_id']


def handle_like(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    data = user_states.get(user_id)
    
    if not data:
        bot.reply_to(message, "❌ No active session. Use VIEW PROFILES")
        return
    
    target_id = data.get('current_profile')
    if not target_id:
        bot.reply_to(message, "❌ Error")
        return
    
    like_data = {"from_user": user_id, "to_user": target_id, "created_at": datetime.utcnow()}
    db.get_collection("likes").insert_one(like_data)
    
    bot.reply_to(message, "❤️ Liked!")
    data['index'] += 1
    show_profile(bot, user_id, user_states)


def handle_skip(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    data = user_states.get(user_id)
    
    if not data:
        bot.reply_to(message, "❌ No active session")
        return
    
    bot.reply_to(message, "⏭️ Skipped!")
    data['index'] += 1
    show_profile(bot, user_id, user_states)


def handle_stop(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    if user_id in user_states:
        del user_states[user_id]
    bot.reply_to(message, "🛑 Stopped viewing profiles.")
    show_main_menu(bot, message.chat.id)


def handle_notifications(bot, message):
    user_id = message.from_user.id
    notifs = list(db.get_collection("notifications").find({"user_id": user_id, "is_read": False}))
    
    if not notifs:
        bot.reply_to(message, "🔔 No new notifications")
        return
    
    for n in notifs:
        bot.reply_to(message, n.get('message', 'New notification'))
    
    db.get_collection("notifications").update_many({"user_id": user_id}, {"$set": {"is_read": True}})


def handle_change_interest(bot, message, user_states, user_temp_data):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("👨 Male"), types.KeyboardButton("👩 Female"), types.KeyboardButton("👥 Both"))
    bot.reply_to(message, "🎯 Who do you want to see?", reply_markup=markup)
    user_states[message.from_user.id] = "changing_interest"


def handle_update_interest(bot, message, user_states, user_temp_data):
    user_id = message.from_user.id
    text = message.text.strip()
    
    if text == "👨 Male":
        pref = "male"
    elif text == "👩 Female":
        pref = "female"
    elif text == "👥 Both":
        pref = "both"
    else:
        bot.reply_to(message, "❌ Use the buttons")
        return
    
    db.get_collection("users").update_one({"user_id": user_id}, {"$set": {"preference": pref}})
    bot.reply_to(message, f"✅ Preference updated to {text}")
    show_main_menu(bot, message.chat.id)


def handle_stats(bot, message):
    user_id = message.from_user.id
    given = db.get_collection("likes").count_documents({"from_user": user_id})
    received = db.get_collection("likes").count_documents({"to_user": user_id})
    bot.reply_to(message, f"📊 **STATS**\n\n❤️ Likes Given: {given}\n💕 Likes Received: {received}")


def handle_settings(bot, message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(types.KeyboardButton("🗑 DELETE ACCOUNT"), types.KeyboardButton("🔙 BACK"))
    bot.reply_to(message, "⚙️ **SETTINGS**", reply_markup=markup)


def handle_delete_account(bot, message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("✅ CONFIRM DELETE"), types.KeyboardButton("❌ CANCEL"))
    bot.reply_to(message, "⚠️ **PERMANENT!** Are you sure?", reply_markup=markup)


def handle_confirm_delete(bot, message):
    user_id = message.from_user.id
    db.get_collection("profiles").update_one({"user_id": user_id}, {"$set": {"is_active": False}})
    db.get_collection("users").update_one({"user_id": user_id}, {"$set": {"is_active": False}})
    bot.reply_to(message, "🗑 Account deleted. Use /start to create new.")
    show_main_menu(bot, message.chat.id)
