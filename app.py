#!/usr/bin/env python3
import os
import logging
import threading
import time
import random
from datetime import datetime
from flask import Flask
import telebot
from telebot import types
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

# ---------- Flask health check ----------
flask_app = Flask(__name__)

@flask_app.route('/')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port, debug=False)

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- MongoDB ----------
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI missing")
client = MongoClient(MONGO_URI)
db = client.get_database("dating_bot")

# ---------- Private channel for media ----------
PRIVATE_CHANNEL_ID = os.getenv("PRIVATE_CHANNEL_ID")
if not PRIVATE_CHANNEL_ID:
    logger.warning("PRIVATE_CHANNEL_ID not set. Media will not be stored permanently.")

# ---------- Bot ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='Markdown')

# ---------- In-memory stores ----------
user_states = {}
user_temp_data = {}
swipe_sessions = {}

# ---------- Helper: upload media to private channel ----------
def upload_media_to_channel(file_id, user_id, media_type):
    if not PRIVATE_CHANNEL_ID:
        return file_id
    try:
        if media_type == 'photo':
            msg = bot.send_photo(PRIVATE_CHANNEL_ID, file_id, caption=f"User: {user_id}")
        else:
            msg = bot.send_video(PRIVATE_CHANNEL_ID, file_id, caption=f"User: {user_id}")
        return f"https://t.me/c/{str(PRIVATE_CHANNEL_ID)[4:]}/{msg.message_id}"
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return file_id

# ---------- Main menu (bottom buttons) ----------
def show_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("👤 MY PROFILE"),
        types.KeyboardButton("👀 VIEW PROFILES"),
        types.KeyboardButton("🔔 NOTIFICATIONS"),
        types.KeyboardButton("🎯 CHANGE INTEREST"),
        types.KeyboardButton("📊 STATS"),
        types.KeyboardButton("⚙️ SETTINGS")
    )
    bot.send_message(chat_id, "🏠 **Main Menu**\nChoose an option:", reply_markup=markup)

# ---------- /start ----------
@bot.message_handler(commands=['start'])
def start_cmd(message):
    chat_id = message.chat.id
    existing = db.profiles.find_one({"user_id": chat_id, "is_active": True})
    if existing:
        show_main_menu(chat_id)
        return
    user_states[chat_id] = "awaiting_name"
    user_temp_data[chat_id] = {}
    bot.reply_to(message, "🌟 Let's create your profile!\nSend your **Name** (2-50 chars):", reply_markup=types.ReplyKeyboardRemove())

# ---------- Name ----------
@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "awaiting_name")
def process_name(message):
    chat_id = message.chat.id
    name = message.text.strip()
    if len(name) < 2 or len(name) > 50:
        bot.reply_to(message, "❌ Name must be 2-50 chars. Try again.")
        return
    user_temp_data[chat_id]['name'] = name
    user_states[chat_id] = "awaiting_gender"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("👨 Male"), types.KeyboardButton("👩 Female"))
    bot.reply_to(message, f"✅ Name: {name}\n\nSelect your Gender:", reply_markup=markup)

# ---------- Gender ----------
@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "awaiting_gender")
def process_gender(message):
    chat_id = message.chat.id
    text = message.text.strip()
    if text == "👨 Male":
        gender = "male"
    elif text == "👩 Female":
        gender = "female"
    else:
        bot.reply_to(message, "❌ Please tap Male or Female button.")
        return
    user_temp_data[chat_id]['gender'] = gender
    user_states[chat_id] = "awaiting_age"
    bot.reply_to(message, f"✅ Gender: {text.replace('👨 ', '').replace('👩 ', '')}\n\nSend your **Age** (18-100):", reply_markup=types.ReplyKeyboardRemove())

# ---------- Age ----------
@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "awaiting_age")
def process_age(message):
    chat_id = message.chat.id
    try:
        age = int(message.text.strip())
        if age < 18 or age > 100:
            raise ValueError
    except:
        bot.reply_to(message, "❌ Invalid age. Send number between 18-100.")
        return
    user_temp_data[chat_id]['age'] = age
    user_states[chat_id] = "awaiting_location"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("📍 Send Location", request_location=True))
    markup.add(types.KeyboardButton("⏭️ Skip Location"))
    bot.reply_to(message, f"✅ Age: {age}\n\nShare location or type city name (or tap Skip):", reply_markup=markup)

# ---------- Location (live) ----------
@bot.message_handler(content_types=['location'])
def location_live(message):
    chat_id = message.chat.id
    if user_states.get(chat_id) != "awaiting_location":
        return
    lat = message.location.latitude
    lon = message.location.longitude
    user_temp_data[chat_id]['location'] = f"{lat},{lon}"
    user_states[chat_id] = "awaiting_about"
    bot.reply_to(message, "✅ Location saved!\n\nSend your **About** (max 500 chars):", reply_markup=types.ReplyKeyboardRemove())

# ---------- Location (text or skip) ----------
@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "awaiting_location")
def location_text(message):
    chat_id = message.chat.id
    text = message.text.strip()
    if text == "⏭️ Skip Location":
        user_temp_data[chat_id]['location'] = ""
        user_states[chat_id] = "awaiting_about"
        bot.reply_to(message, "✅ Location skipped.\n\nSend your **About** (max 500 chars):", reply_markup=types.ReplyKeyboardRemove())
        return
    if len(text) < 2:
        bot.reply_to(message, "❌ Invalid location. Type city name or tap Skip.")
        return
    user_temp_data[chat_id]['location'] = text
    user_states[chat_id] = "awaiting_about"
    bot.reply_to(message, f"✅ Location: {text}\n\nSend your **About** (max 500 chars):", reply_markup=types.ReplyKeyboardRemove())

# ---------- About ----------
@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "awaiting_about")
def process_about(message):
    chat_id = message.chat.id
    about = message.text.strip()
    if len(about) > 500:
        bot.reply_to(message, "❌ Too long. Max 500 chars.")
        return
    user_temp_data[chat_id]['about'] = about
    user_states[chat_id] = "awaiting_media"
    user_temp_data[chat_id]['media_list'] = []
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(types.KeyboardButton("📷 Done (Finish Media)"))
    bot.reply_to(message, "✅ About saved.\nSend **1-3 photos/videos**, then tap 'Done (Finish Media)':", reply_markup=markup)

@bot.message_handler(commands=['skip'])
def skip_about(message):
    chat_id = message.chat.id
    if user_states.get(chat_id) == "awaiting_about":
        user_temp_data[chat_id]['about'] = ""
        user_states[chat_id] = "awaiting_media"
        user_temp_data[chat_id]['media_list'] = []
        bot.reply_to(message, "✅ About skipped. Send **1-3 photos/videos**, then tap 'Done (Finish Media)':", reply_markup=types.ReplyKeyboardRemove())

# ---------- Media collection ----------
@bot.message_handler(content_types=['photo', 'video'])
def collect_media(message):
    chat_id = message.chat.id
    if user_states.get(chat_id) != "awaiting_media":
        return
    media_list = user_temp_data[chat_id].get('media_list', [])
    if len(media_list) >= 3:
        bot.reply_to(message, "❌ Max 3 files. Tap 'Done (Finish Media)'.")
        return
    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = 'photo'
    elif message.video:
        file_id = message.video.file_id
        media_type = 'video'
    else:
        return
    media_list.append({'file_id': file_id, 'type': media_type})
    user_temp_data[chat_id]['media_list'] = media_list
    remaining = 3 - len(media_list)
    bot.reply_to(message, f"✅ Media {len(media_list)}/3 added. {remaining} remaining. Send more or tap 'Done'.")

# ---------- Done button ----------
@bot.message_handler(func=lambda m: m.text == "📷 Done (Finish Media)")
def done_media(message):
    chat_id = message.chat.id
    if user_states.get(chat_id) != "awaiting_media":
        return
    media_list = user_temp_data[chat_id].get('media_list', [])
    if len(media_list) == 0:
        bot.reply_to(message, "❌ Please send at least 1 photo or video.")
        return
    temp = user_temp_data[chat_id]
    preview = f"📋 **Profile Preview**\n"
    preview += f"👤 Name: {temp.get('name')}\n"
    preview += f"⚧ Gender: {'Male' if temp.get('gender')=='male' else 'Female'}\n"
    preview += f"🎂 Age: {temp.get('age')}\n"
    preview += f"📍 Location: {temp.get('location', 'Not provided')}\n"
    preview += f"📝 About: {temp.get('about', 'Not provided')[:100]}\n"
    preview += f"📷 Media: {len(media_list)} file(s)\n\nConfirm to save?"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("CONFIRM"), types.KeyboardButton("CANCEL"))
    user_states[chat_id] = "awaiting_confirm"
    bot.send_message(chat_id, preview, reply_markup=markup)

# ---------- Confirm / Cancel ----------
@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "awaiting_confirm" and m.text == "CONFIRM")
def confirm_profile(message):
    chat_id = message.chat.id
    temp = user_temp_data.pop(chat_id, {})
    user_states.pop(chat_id, None)
    media_urls = []
    for media in temp.get('media_list', []):
        url = upload_media_to_channel(media['file_id'], chat_id, media['type'])
        media_urls.append(url)
    profile = {
        "user_id": chat_id,
        "username": message.from_user.username,
        "name": temp.get('name'),
        "gender": temp.get('gender'),
        "age": temp.get('age'),
        "location_text": temp.get('location', ''),
        "about": temp.get('about', ''),
        "media": media_urls,
        "created_at": datetime.utcnow(),
        "is_active": True
    }
    db.profiles.update_one({"user_id": chat_id}, {"$set": profile}, upsert=True)
    db.users.update_one({"user_id": chat_id}, {"$set": {"setup_complete": True, "last_active": datetime.utcnow()}}, upsert=True)

    bot.reply_to(message, "🎉 **Profile Created!** 🎉\n\nNow set your preference.", reply_markup=types.ReplyKeyboardRemove())
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("👨 Male"), types.KeyboardButton("👩 Female"), types.KeyboardButton("👥 Both"))
    user_states[chat_id] = "awaiting_preference"
    bot.send_message(chat_id, "Who do you want to see in your feed?", reply_markup=markup)

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "awaiting_confirm" and m.text == "CANCEL")
def cancel_profile(message):
    chat_id = message.chat.id
    user_states.pop(chat_id, None)
    user_temp_data.pop(chat_id, None)
    bot.reply_to(message, "❌ Profile creation cancelled. Use /start.", reply_markup=types.ReplyKeyboardRemove())

# ---------- Preference ----------
@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "awaiting_preference")
def set_preference(message):
    chat_id = message.chat.id
    text = message.text.strip()
    if text == "👨 Male":
        pref = "male"
    elif text == "👩 Female":
        pref = "female"
    elif text == "👥 Both":
        pref = "both"
    else:
        bot.reply_to(message, "❌ Tap Male, Female or Both button.")
        return
    db.users.update_one({"user_id": chat_id}, {"$set": {"preference": pref}}, upsert=True)
    user_states.pop(chat_id, None)
    bot.reply_to(message, f"✅ Preference set to {text}.", reply_markup=types.ReplyKeyboardRemove())
    show_main_menu(chat_id)

# ---------- MY PROFILE ----------
@bot.message_handler(func=lambda m: m.text == "👤 MY PROFILE")
def my_profile(message):
    chat_id = message.chat.id
    profile = db.profiles.find_one({"user_id": chat_id, "is_active": True})
    if not profile:
        bot.reply_to(message, "❌ No profile found. Use /start to create one.")
        show_main_menu(chat_id)
        return
    text = f"👤 **YOUR PROFILE**\n\n📛 Name: {profile.get('name')}\n⚧ Gender: {'Male' if profile.get('gender')=='male' else 'Female'}\n🎂 Age: {profile.get('age')}\n📍 Location: {profile.get('location_text', 'Not set')}\n📝 About: {profile.get('about', 'Not set')[:200]}\n📷 Media: {len(profile.get('media', []))} file(s)"
    media_list = profile.get('media', [])
    if media_list:
        try:
            bot.send_photo(chat_id, media_list[0], caption=text, parse_mode='Markdown')
        except:
            bot.send_message(chat_id, text, parse_mode='Markdown')
    else:
        bot.send_message(chat_id, text, parse_mode='Markdown')
    # Edit and Main Menu buttons
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("✏️ EDIT PROFILE"), types.KeyboardButton("🏠 MAIN MENU"))
    bot.send_message(chat_id, "What would you like to do?", reply_markup=markup)

# ---------- EDIT PROFILE (simple version – only name, age, gender, location, about) ----------
@bot.message_handler(func=lambda m: m.text == "✏️ EDIT PROFILE")
def edit_profile_start(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("📛 Name"), types.KeyboardButton("🎂 Age"))
    markup.add(types.KeyboardButton("⚧ Gender"), types.KeyboardButton("📍 Location"))
    markup.add(types.KeyboardButton("📝 About"), types.KeyboardButton("❌ Cancel"))
    bot.send_message(chat_id, "✏️ **Edit Profile**\nChoose what to edit:", reply_markup=markup)
    user_states[chat_id] = "editing_choose"

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "editing_choose")
def edit_choose(message):
    chat_id = message.chat.id
    choice = message.text.strip()
    if choice == "❌ Cancel":
        user_states.pop(chat_id, None)
        show_main_menu(chat_id)
        return
    elif choice == "📛 Name":
        user_states[chat_id] = "editing_name"
        bot.send_message(chat_id, "Send new name (2-50 chars) or /skip:", reply_markup=types.ReplyKeyboardRemove())
    elif choice == "🎂 Age":
        user_states[chat_id] = "editing_age"
        bot.send_message(chat_id, "Send new age (18-100) or /skip:", reply_markup=types.ReplyKeyboardRemove())
    elif choice == "⚧ Gender":
        user_states[chat_id] = "editing_gender"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(types.KeyboardButton("👨 Male"), types.KeyboardButton("👩 Female"))
        bot.send_message(chat_id, "Select new gender:", reply_markup=markup)
    elif choice == "📍 Location":
        user_states[chat_id] = "editing_location"
        bot.send_message(chat_id, "Send new location or /skip:", reply_markup=types.ReplyKeyboardRemove())
    elif choice == "📝 About":
        user_states[chat_id] = "editing_about"
        bot.send_message(chat_id, "Send new about (max 500 chars) or /skip:", reply_markup=types.ReplyKeyboardRemove())
    else:
        edit_profile_start(message)

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "editing_name")
def edit_name(message):
    chat_id = message.chat.id
    new_name = message.text.strip()
    if new_name == "/skip":
        bot.reply_to(message, "✅ Name kept.")
    elif len(new_name) < 2 or len(new_name) > 50:
        bot.reply_to(message, "❌ Name must be 2-50 chars. Try again or /skip:")
        return
    else:
        db.profiles.update_one({"user_id": chat_id}, {"$set": {"name": new_name}})
        bot.reply_to(message, f"✅ Name updated to {new_name}.")
    user_states.pop(chat_id, None)
    show_main_menu(chat_id)

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "editing_age")
def edit_age(message):
    chat_id = message.chat.id
    if message.text == "/skip":
        bot.reply_to(message, "✅ Age kept.")
    else:
        try:
            new_age = int(message.text.strip())
            if new_age < 18 or new_age > 100:
                raise ValueError
            db.profiles.update_one({"user_id": chat_id}, {"$set": {"age": new_age}})
            bot.reply_to(message, f"✅ Age updated to {new_age}.")
        except:
            bot.reply_to(message, "❌ Invalid age. Send 18-100 or /skip:")
            return
    user_states.pop(chat_id, None)
    show_main_menu(chat_id)

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "editing_gender")
def edit_gender(message):
    chat_id = message.chat.id
    text = message.text.strip()
    if text == "👨 Male":
        new_gender = "male"
    elif text == "👩 Female":
        new_gender = "female"
    else:
        bot.reply_to(message, "❌ Tap Male or Female button.")
        return
    db.profiles.update_one({"user_id": chat_id}, {"$set": {"gender": new_gender}})
    bot.reply_to(message, f"✅ Gender updated to {text}.")
    user_states.pop(chat_id, None)
    show_main_menu(chat_id)

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "editing_location")
def edit_location(message):
    chat_id = message.chat.id
    if message.text == "/skip":
        bot.reply_to(message, "✅ Location kept.")
    else:
        new_loc = message.text.strip()
        if len(new_loc) < 2:
            bot.reply_to(message, "❌ Invalid location. Try again or /skip.")
            return
        db.profiles.update_one({"user_id": chat_id}, {"$set": {"location_text": new_loc}})
        bot.reply_to(message, f"✅ Location updated to {new_loc}.")
    user_states.pop(chat_id, None)
    show_main_menu(chat_id)

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "editing_about")
def edit_about(message):
    chat_id = message.chat.id
    if message.text == "/skip":
        bot.reply_to(message, "✅ About kept.")
    else:
        new_about = message.text.strip()
        if len(new_about) > 500:
            bot.reply_to(message, "❌ Too long (max 500). Try again or /skip.")
            return
        db.profiles.update_one({"user_id": chat_id}, {"$set": {"about": new_about}})
        bot.reply_to(message, "✅ About updated.")
    user_states.pop(chat_id, None)
    show_main_menu(chat_id)

# ---------- VIEW PROFILES (with swipe logic) ----------
@bot.message_handler(func=lambda m: m.text == "👀 VIEW PROFILES")
def view_profiles(message):
    chat_id = message.chat.id
    my_profile = db.profiles.find_one({"user_id": chat_id, "is_active": True})
    if not my_profile:
        bot.reply_to(message, "❌ Create profile first using /start.")
        show_main_menu(chat_id)
        return
    user = db.users.find_one({"user_id": chat_id})
    pref = user.get("preference", "both") if user else "both"
    query = {"user_id": {"$ne": chat_id}, "is_active": True}
    if pref == "male":
        query["gender"] = "male"
    elif pref == "female":
        query["gender"] = "female"
    # Exclude already liked profiles (optional: keep them for repeat)
    liked = db.likes.distinct("to_user", {"from_user": chat_id})
    query["user_id"] = {"$nin": liked}
    profiles = list(db.profiles.find(query).limit(200))
    if not profiles:
        bot.reply_to(message, "😔 No other active profiles found. Try changing preference.")
        show_main_menu(chat_id)
        return
    random.shuffle(profiles)
    swipe_sessions[chat_id] = {"profiles": profiles, "index": 0}
    send_profile(chat_id)

def send_profile(chat_id):
    session = swipe_sessions.get(chat_id)
    if not session:
        return
    profiles = session["profiles"]
    idx = session["index"]
    if idx >= len(profiles):
        # Loop back to start
        idx = 0
        session["index"] = 0
    p = profiles[idx]
    text = f"👤 {p.get('name')}\n🎂 Age: {p.get('age')}\n📍 {p.get('location_text', 'No location')}\n📝 {p.get('about', '')[:100]}"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("❤️ LIKE"),
        types.KeyboardButton("⏭️ SKIP"),
        types.KeyboardButton("🛑 STOP VIEWING")
    )
    media = p.get('media', [])
    if media:
        try:
            bot.send_photo(chat_id, media[0], caption=text, parse_mode='Markdown', reply_markup=markup)
        except:
            bot.send_message(chat_id, text, reply_markup=markup)
    else:
        bot.send_message(chat_id, text, reply_markup=markup)
    session["current_profile_id"] = p["user_id"]

# ---------- LIKE ----------
@bot.message_handler(func=lambda m: m.text == "❤️ LIKE")
def like_profile(message):
    chat_id = message.chat.id
    session = swipe_sessions.get(chat_id)
    if not session:
        bot.reply_to(message, "No active swipe session. Use VIEW PROFILES.")
        return
    target_id = session.get("current_profile_id")
    if not target_id:
        return
    # Insert like (idempotent)
    db.likes.update_one(
        {"from_user": chat_id, "to_user": target_id},
        {"$set": {"created_at": datetime.utcnow()}},
        upsert=True
    )
    bot.reply_to(message, "❤️ Liked!")
    # Move to next profile
    session["index"] += 1
    send_profile(chat_id)

# ---------- SKIP ----------
@bot.message_handler(func=lambda m: m.text == "⏭️ SKIP")
def skip_profile(message):
    chat_id = message.chat.id
    session = swipe_sessions.get(chat_id)
    if not session:
        bot.reply_to(message, "No active session. Tap VIEW PROFILES first.")
        return
    session["index"] += 1
    if session["index"] >= len(session["profiles"]):
        # End reached: reshuffle and restart
        random.shuffle(session["profiles"])
        session["index"] = 0
    send_profile(chat_id)

# ---------- STOP VIEWING ----------
@bot.message_handler(func=lambda m: m.text == "🛑 STOP VIEWING")
def stop_viewing(message):
    chat_id = message.chat.id
    swipe_sessions.pop(chat_id, None)
    show_main_menu(chat_id)

# ---------- CHANGE INTEREST ----------
@bot.message_handler(func=lambda m: m.text == "🎯 CHANGE INTEREST")
def change_interest(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("👨 Male"), types.KeyboardButton("👩 Female"), types.KeyboardButton("👥 Both"))
    bot.reply_to(message, "Select your new preference:", reply_markup=markup)
    user_states[chat_id] = "changing_interest"

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "changing_interest")
def update_interest(message):
    chat_id = message.chat.id
    text = message.text.strip()
    if text == "👨 Male":
        pref = "male"
    elif text == "👩 Female":
        pref = "female"
    elif text == "👥 Both":
        pref = "both"
    else:
        bot.reply_to(message, "❌ Use the buttons.")
        return
    db.users.update_one({"user_id": chat_id}, {"$set": {"preference": pref}})
    user_states.pop(chat_id, None)
    bot.reply_to(message, f"Preference changed to {text}.", reply_markup=types.ReplyKeyboardRemove())
    show_main_menu(chat_id)

# ---------- STATS ----------
@bot.message_handler(func=lambda m: m.text == "📊 STATS")
def stats(message):
    chat_id = message.chat.id
    given = db.likes.count_documents({"from_user": chat_id})
    received = db.likes.count_documents({"to_user": chat_id})
    bot.reply_to(message, f"📊 **Stats**\nLikes given: {given}\nLikes received: {received}")
    show_main_menu(chat_id)

# ---------- SETTINGS & DELETE ----------
@bot.message_handler(func=lambda m: m.text == "⚙️ SETTINGS")
def settings(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(types.KeyboardButton("🗑 DELETE ACCOUNT"), types.KeyboardButton("🔙 BACK"))
    bot.reply_to(message, "⚙️ Settings", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🗑 DELETE ACCOUNT")
def ask_delete(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("✅ CONFIRM DELETE"), types.KeyboardButton("❌ CANCEL"))
    bot.reply_to(message, "⚠️ Are you sure? This is permanent.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "✅ CONFIRM DELETE")
def confirm_delete(message):
    chat_id = message.chat.id
    db.profiles.update_one({"user_id": chat_id}, {"$set": {"is_active": False}})
    db.users.update_one({"user_id": chat_id}, {"$set": {"is_active": False}})
    bot.reply_to(message, "Account deleted. Use /start to create new.", reply_markup=types.ReplyKeyboardRemove())
    user_states.pop(chat_id, None)
    swipe_sessions.pop(chat_id, None)
    show_main_menu(chat_id)

@bot.message_handler(func=lambda m: m.text == "❌ CANCEL")
def cancel_action(message):
    show_main_menu(message.chat.id)

@bot.message_handler(func=lambda m: m.text == "🔙 BACK")
def back_main(message):
    show_main_menu(message.chat.id)

# ---------- NOTIFICATIONS (placeholder) ----------
@bot.message_handler(func=lambda m: m.text == "🔔 NOTIFICATIONS")
def notifications(message):
    bot.reply_to(message, "🔔 No new notifications.", reply_markup=types.ReplyKeyboardRemove())
    show_main_menu(message.chat.id)

# ---------- FALLBACK (MUST BE LAST) ----------
@bot.message_handler(func=lambda m: True)
def fallback(message):
    bot.reply_to(message, "❌ Invalid command. Use /start or buttons.", reply_markup=types.ReplyKeyboardRemove())

# ---------- MAIN ----------
def main():
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(2)
    try:
        bot.remove_webhook()
        time.sleep(1)
        logger.info("Webhook removed")
    except Exception as e:
        logger.error(f"Webhook removal failed: {e}")
    logger.info("Bot polling started...")
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)

if __name__ == "__main__":
    main()
