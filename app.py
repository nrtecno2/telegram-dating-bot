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

# ---------- Flask Health Check ----------
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

# ---------- Private Channel ----------
PRIVATE_CHANNEL_ID = os.getenv("PRIVATE_CHANNEL_ID")
if not PRIVATE_CHANNEL_ID:
    logger.warning("PRIVATE_CHANNEL_ID not set")

# ---------- Bot ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='Markdown')

# ---------- Stores ----------
user_states = {}
user_temp_data = {}
swipe_sessions = {}

# ---------- Helper: Upload media ----------
def upload_media_to_channel(file_id, user_id, media_type):
    if not PRIVATE_CHANNEL_ID:
        return file_id
    try:
        if media_type == 'photo':
            msg = bot.send_photo(PRIVATE_CHANNEL_ID, file_id, caption=f"User: {user_id}")
        else:
            msg = bot.send_video(PRIVATE_CHANNEL_ID, file_id, caption=f"User: {user_id}")
        return f"https://t.me/c/{str(PRIVATE_CHANNEL_ID)[4:]}/{msg.message_id}"
    except:
        return file_id

# ---------- Main Menu ----------
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
    user_id = message.from_user.id
    existing = db.profiles.find_one({"user_id": user_id, "is_active": True})
    if existing:
        show_main_menu(message.chat.id)
        return
    user_states[user_id] = "awaiting_name"
    user_temp_data[user_id] = {}
    bot.reply_to(message, "🌟 Let's create your profile!\nSend your **Name** (2-50 chars):", reply_markup=types.ReplyKeyboardRemove())

# ---------- Name ----------
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_name")
def process_name(m):
    uid = m.from_user.id
    name = m.text.strip()
    if len(name) < 2 or len(name) > 50:
        bot.reply_to(m, "❌ Name must be 2-50 chars. Try again.")
        return
    user_temp_data[uid]['name'] = name
    user_states[uid] = "awaiting_gender"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("👨 Male"), types.KeyboardButton("👩 Female"))
    bot.reply_to(m, f"✅ Name: {name}\n\nSelect your Gender:", reply_markup=markup)

# ---------- Gender ----------
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_gender")
def process_gender(m):
    uid = m.from_user.id
    text = m.text.strip()
    if text == "👨 Male":
        gender = "male"
    elif text == "👩 Female":
        gender = "female"
    else:
        bot.reply_to(m, "❌ Please tap Male or Female button.")
        return
    user_temp_data[uid]['gender'] = gender
    user_states[uid] = "awaiting_age"
    bot.reply_to(m, f"✅ Gender: {text.replace('👨 ', '').replace('👩 ', '')}\n\nSend your **Age** (18-100):", reply_markup=types.ReplyKeyboardRemove())

# ---------- Age ----------
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_age")
def process_age(m):
    uid = m.from_user.id
    try:
        age = int(m.text.strip())
        if age < 18 or age > 100:
            raise ValueError
    except:
        bot.reply_to(m, "❌ Invalid age. Send 18-100.")
        return
    user_temp_data[uid]['age'] = age
    user_states[uid] = "awaiting_location"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("📍 Send Location", request_location=True))
    markup.add(types.KeyboardButton("⏭️ Skip Location"))
    bot.reply_to(m, f"✅ Age: {age}\n\nShare location or type city (or tap Skip):", reply_markup=markup)

# ---------- Location (live) ----------
@bot.message_handler(content_types=['location'])
def location_live(m):
    uid = m.from_user.id
    if user_states.get(uid) != "awaiting_location":
        return
    user_temp_data[uid]['location'] = f"{m.location.latitude},{m.location.longitude}"
    user_states[uid] = "awaiting_about"
    bot.reply_to(m, "✅ Location saved!\n\nSend your **About** (max 500 chars):", reply_markup=types.ReplyKeyboardRemove())

# ---------- Location (text or skip) ----------
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_location")
def location_text(m):
    uid = m.from_user.id
    text = m.text.strip()
    if text == "⏭️ Skip Location":
        user_temp_data[uid]['location'] = ""
        user_states[uid] = "awaiting_about"
        bot.reply_to(m, "✅ Location skipped.\n\nSend your **About** (max 500 chars):", reply_markup=types.ReplyKeyboardRemove())
        return
    if len(text) < 2:
        bot.reply_to(m, "❌ Invalid location. Type city name or tap Skip.")
        return
    user_temp_data[uid]['location'] = text
    user_states[uid] = "awaiting_about"
    bot.reply_to(m, f"✅ Location: {text}\n\nSend your **About** (max 500 chars):", reply_markup=types.ReplyKeyboardRemove())

# ---------- About ----------
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_about")
def process_about(m):
    uid = m.from_user.id
    about = m.text.strip()
    if len(about) > 500:
        bot.reply_to(m, "❌ Too long. Max 500 chars.")
        return
    user_temp_data[uid]['about'] = about
    user_states[uid] = "awaiting_media"
    user_temp_data[uid]['media_list'] = []
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(types.KeyboardButton("📷 Done (Finish Media)"))
    bot.reply_to(m, "About saved.\nSend **1-3 photos/videos**, then tap 'Done (Finish Media)':", reply_markup=markup)

# ---------- Media collection ----------
@bot.message_handler(content_types=['photo', 'video'])
def collect_media(m):
    uid = m.from_user.id
    if user_states.get(uid) != "awaiting_media":
        return
    media_list = user_temp_data[uid].get('media_list', [])
    if len(media_list) >= 3:
        bot.reply_to(m, "❌ Max 3 files. Tap 'Done'.")
        return
    if m.photo:
        file_id = m.photo[-1].file_id
        media_type = 'photo'
    elif m.video:
        file_id = m.video.file_id
        media_type = 'video'
    else:
        return
    media_list.append({'file_id': file_id, 'type': media_type})
    user_temp_data[uid]['media_list'] = media_list
    remaining = 3 - len(media_list)
    bot.reply_to(m, f"✅ Media {len(media_list)}/3 added. {remaining} remaining. Send more or tap 'Done'.")

# ---------- Done button (preview) ----------
@bot.message_handler(func=lambda m: m.text == "📷 Done (Finish Media)")
def done_media(m):
    uid = m.from_user.id
    if user_states.get(uid) != "awaiting_media":
        return
    media_list = user_temp_data[uid].get('media_list', [])
    if len(media_list) == 0:
        bot.reply_to(m, "❌ Please send at least 1 photo or video.")
        return
    temp = user_temp_data[uid]
    preview = f"📋 **Profile Preview**\n"
    preview += f"👤 Name: {temp.get('name')}\n"
    preview += f"⚧ Gender: {'Male' if temp.get('gender')=='male' else 'Female'}\n"
    preview += f"🎂 Age: {temp.get('age')}\n"
    preview += f"📍 Location: {temp.get('location', 'Not provided')}\n"
    preview += f"📝 About: {temp.get('about', 'Not provided')[:100]}\n"
    preview += f"📷 Media: {len(media_list)} file(s)\n\nConfirm to save?"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("CONFIRM"), types.KeyboardButton("CANCEL"))
    first = media_list[0]
    try:
        if first['type'] == 'photo':
            bot.send_photo(m.chat.id, first['file_id'], caption=preview, parse_mode='Markdown', reply_markup=markup)
        else:
            bot.send_video(m.chat.id, first['file_id'], caption=preview, parse_mode='Markdown', reply_markup=markup)
    except:
        bot.reply_to(m, preview, reply_markup=markup)
    for media in media_list[1:]:
        try:
            if media['type'] == 'photo':
                bot.send_photo(m.chat.id, media['file_id'])
            else:
                bot.send_video(m.chat.id, media['file_id'])
        except:
            pass
    user_states[uid] = "awaiting_confirm"
    # ---------- Confirm / Cancel ----------
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_confirm" and m.text == "CONFIRM")
def confirm_profile(m):
    uid = m.from_user.id
    temp = user_temp_data.pop(uid, {})
    user_states.pop(uid, None)
    media_urls = []
    for media in temp.get('media_list', []):
        url = upload_media_to_channel(media['file_id'], uid, media['type'])
        media_urls.append(url)
    loc = temp.get('location')
    if not loc or loc == "":
        loc = None
    profile = {
        "user_id": uid,
        "username": m.from_user.username,
        "name": temp.get('name'),
        "gender": temp.get('gender'),
        "age": temp.get('age'),
        "location": loc,
        "location_text": temp.get('location', ''),
        "about": temp.get('about', ''),
        "media": media_urls,
        "created_at": datetime.utcnow(),
        "is_active": True
    }
    db.profiles.update_one({"user_id": uid}, {"$set": profile}, upsert=True)
    db.users.update_one({"user_id": uid}, {"$set": {"setup_complete": True, "last_active": datetime.utcnow()}}, upsert=True)

    bot.reply_to(m, "🎉 **Profile Created!** 🎉\n\nNow set your preference.", reply_markup=types.ReplyKeyboardRemove())
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("👨 Male"), types.KeyboardButton("👩 Female"), types.KeyboardButton("👥 Both"))
    user_states[uid] = "awaiting_preference"
    bot.reply_to(m, "Who do you want to see in your feed?", reply_markup=markup)

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_confirm" and m.text == "CANCEL")
def cancel_profile(m):
    uid = m.from_user.id
    user_states.pop(uid, None)
    user_temp_data.pop(uid, None)
    bot.reply_to(m, "❌ Profile creation cancelled. Use /start.", reply_markup=types.ReplyKeyboardRemove())

# ---------- Preference ----------
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_preference")
def set_preference(m):
    uid = m.from_user.id
    text = m.text.strip()
    if text == "👨 Male":
        pref = "male"
    elif text == "👩 Female":
        pref = "female"
    elif text == "👥 Both":
        pref = "both"
    else:
        bot.reply_to(m, "❌ Tap Male, Female or Both button.")
        return
    db.users.update_one({"user_id": uid}, {"$set": {"preference": pref}}, upsert=True)
    user_states.pop(uid, None)
    bot.reply_to(m, f"✅ Preference set to {text}.", reply_markup=types.ReplyKeyboardRemove())
    show_main_menu(m.chat.id)

# ---------- MY PROFILE (with Edit button) ----------
@bot.message_handler(func=lambda m: m.text == "👤 MY PROFILE")
def my_profile(m):
    uid = m.from_user.id
    profile = db.profiles.find_one({"user_id": uid, "is_active": True})
    if not profile:
        bot.reply_to(m, "❌ No profile found. Use /start to create one.")
        show_main_menu(m.chat.id)
        return
    text = f"👤 **YOUR PROFILE**\n\n📛 Name: {profile.get('name')}\n⚧ Gender: {'Male' if profile.get('gender')=='male' else 'Female'}\n🎂 Age: {profile.get('age')}\n📍 Location: {profile.get('location_text', 'Not set')}\n📝 About: {profile.get('about', 'Not set')[:200]}\n📷 Media: {len(profile.get('media', []))} file(s)"
    
    media_list = profile.get('media', [])
    if media_list:
        try:
            bot.send_photo(m.chat.id, media_list[0], caption=text, parse_mode='Markdown')
        except:
            bot.send_message(m.chat.id, text, parse_mode='Markdown')
        for url in media_list[1:]:
            try:
                bot.send_photo(m.chat.id, url)
            except:
                pass
    else:
        bot.reply_to(m, text, parse_mode='Markdown')
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("✏️ EDIT PROFILE"), types.KeyboardButton("🏠 MAIN MENU"))
    bot.send_message(m.chat.id, "What would you like to do?", reply_markup=markup)

# ---------- EDIT PROFILE helpers ----------
def edit_send_current(chat_id, uid, edit_step):
    profile = db.profiles.find_one({"user_id": uid, "is_active": True})
    if not profile:
        bot.send_message(chat_id, "❌ Profile not found.")
        show_main_menu(chat_id)
        return
    if edit_step == "name":
        bot.send_message(chat_id, f"✏️ Current Name: {profile.get('name')}\nSend new name (2-50 chars) or /skip:", reply_markup=types.ReplyKeyboardRemove())
    elif edit_step == "age":
        bot.send_message(chat_id, f"✏️ Current Age: {profile.get('age')}\nSend new age (18-100) or /skip:", reply_markup=types.ReplyKeyboardRemove())
    elif edit_step == "gender":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(types.KeyboardButton("👨 Male"), types.KeyboardButton("👩 Female"))
        bot.send_message(chat_id, f"✏️ Current Gender: {'Male' if profile.get('gender')=='male' else 'Female'}\nSelect new gender:", reply_markup=markup)
    elif edit_step == "location":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(types.KeyboardButton("⏭️ Skip (keep current)"))
        bot.send_message(chat_id, f"✏️ Current Location: {profile.get('location_text', 'Not set')}\nSend new location or tap Skip:", reply_markup=markup)
    elif edit_step == "about":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(types.KeyboardButton("⏭️ Skip (keep current)"))
        bot.send_message(chat_id, f"✏️ Current About: {profile.get('about', 'Not set')[:100]}\nSend new about (max 500 chars) or Skip:", reply_markup=markup)
    elif edit_step == "media":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(types.KeyboardButton("📷 Done (Finish Media)"), types.KeyboardButton("⏭️ Skip (keep current)"))
        bot.send_message(chat_id, "✏️ Edit Media\nSend new photos/videos (max 3), then tap 'Done' or 'Skip':", reply_markup=markup)
        user_temp_data[uid] = {'edit_media_list': []}

@bot.message_handler(func=lambda m: m.text == "✏️ EDIT PROFILE")
def edit_profile_start(m):
    uid = m.from_user.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("📛 Name"), types.KeyboardButton("🎂 Age"))
    markup.add(types.KeyboardButton("⚧ Gender"), types.KeyboardButton("📍 Location"))
    markup.add(types.KeyboardButton("📝 About"), types.KeyboardButton("📷 Photos/Videos"))
    markup.add(types.KeyboardButton("❌ Cancel"))
    bot.send_message(m.chat.id, "✏️ **Edit Profile**\nChoose what to edit:", reply_markup=markup)
    user_states[uid] = "editing_choose"

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "editing_choose")
def edit_choose(m):
    uid = m.from_user.id
    choice = m.text.strip()
    if choice == "❌ Cancel":
        user_states.pop(uid, None)
        show_main_menu(m.chat.id)
        return
    elif choice == "📛 Name":
        user_states[uid] = "editing_name"
        edit_send_current(m.chat.id, uid, "name")
    elif choice == "🎂 Age":
        user_states[uid] = "editing_age"
        edit_send_current(m.chat.id, uid, "age")
    elif choice == "⚧ Gender":
        user_states[uid] = "editing_gender"
        edit_send_current(m.chat.id, uid, "gender")
    elif choice == "📍 Location":
        user_states[uid] = "editing_location"
        edit_send_current(m.chat.id, uid, "location")
    elif choice == "📝 About":
        user_states[uid] = "editing_about"
        edit_send_current(m.chat.id, uid, "about")
    elif choice == "📷 Photos/Videos":
        user_states[uid] = "editing_media"
        edit_send_current(m.chat.id, uid, "media")
    else:
        bot.reply_to(m, "Please use the buttons.")

# Name edit
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "editing_name")
def edit_name(m):
    uid = m.from_user.id
    new_name = m.text.strip()
    if new_name == "/skip":
        bot.reply_to(m, "✅ Name kept.")
    elif len(new_name) < 2 or len(new_name) > 50:
        bot.reply_to(m, "❌ Name must be 2-50 chars. Try again or /skip:")
        return
    else:
        db.profiles.update_one({"user_id": uid}, {"$set": {"name": new_name}})
        bot.reply_to(m, f"✅ Name updated to {new_name}.")
    user_states.pop(uid, None)
    show_main_menu(m.chat.id)

# Age edit
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "editing_age")
def edit_age(m):
    uid = m.from_user.id
    if m.text == "/skip":
        bot.reply_to(m, "✅ Age kept.")
    else:
        try:
            new_age = int(m.text.strip())
            if new_age < 18 or new_age > 100:
                raise ValueError
            db.profiles.update_one({"user_id": uid}, {"$set": {"age": new_age}})
            bot.reply_to(m, f"✅ Age updated to {new_age}.")
        except:
            bot.reply_to(m, "❌ Invalid age. Send 18-100 or /skip:")
            return
    user_states.pop(uid, None)
    show_main_menu(m.chat.id)

# Gender edit
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "editing_gender")
def edit_gender(m):
    uid = m.from_user.id
    text = m.text.strip()
    if text == "👨 Male":
        new_gender = "male"
    elif text == "👩 Female":
        new_gender = "female"
    else:
        bot.reply_to(m, "❌ Tap Male or Female button.")
        return
    db.profiles.update_one({"user_id": uid}, {"$set": {"gender": new_gender}})
    bot.reply_to(m, f"✅ Gender updated to {text}.")
    user_states.pop(uid, None)
    show_main_menu(m.chat.id)

# Location edit
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "editing_location")
def edit_location(m):
    uid = m.from_user.id
    if m.text == "⏭️ Skip (keep current)":
        bot.reply_to(m, "✅ Location kept.")
    else:
        new_loc = m.text.strip()
        if len(new_loc) < 2:
            bot.reply_to(m, "❌ Invalid location. Try again or Skip.")
            return
        db.profiles.update_one({"user_id": uid}, {"$set": {"location_text": new_loc, "location": None}})
        bot.reply_to(m, f"✅ Location updated to {new_loc}.")
    user_states.pop(uid, None)
    show_main_menu(m.chat.id)

# About edit
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "editing_about")
def edit_about(m):
    uid = m.from_user.id
    if m.text == "⏭️ Skip (keep current)":
        bot.reply_to(m, "✅ About kept.")
    else:
        new_about = m.text.strip()
        if len(new_about) > 500:
            bot.reply_to(m, "❌ Too long (max 500). Try again or Skip.")
            return
        db.profiles.update_one({"user_id": uid}, {"$set": {"about": new_about}})
        bot.reply_to(m, "✅ About updated.")
    user_states.pop(uid, None)
    show_main_menu(m.chat.id)

# Media edit - collect new media
@bot.message_handler(content_types=['photo', 'video'])
def edit_collect_media(m):
    uid = m.from_user.id
    if user_states.get(uid) != "editing_media":
        return
    temp = user_temp_data.get(uid, {})
    media_list = temp.get('edit_media_list', [])
    if len(media_list) >= 3:
        bot.reply_to(m, "❌ Max 3 files. Tap 'Done'.")
        return
    if m.photo:
        file_id = m.photo[-1].file_id
        media_type = 'photo'
    elif m.video:
        file_id = m.video.file_id
        media_type = 'video'
    else:
        return
    media_list.append({'file_id': file_id, 'type': media_type})
    user_temp_data[uid] = {'edit_media_list': media_list}
    remaining = 3 - len(media_list)
    bot.reply_to(m, f"✅ Media {len(media_list)}/3 added. {remaining} remaining. Send more or tap 'Done'.")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "editing_media" and m.text == "📷 Done (Finish Media)")
def edit_media_done(m):
    uid = m.from_user.id
    temp = user_temp_data.pop(uid, {})
    media_list = temp.get('edit_media_list', [])
    if not media_list:
        bot.reply_to(m, "No new media sent. Keeping existing.")
        user_states.pop(uid, None)
        show_main_menu(m.chat.id)
        return
    media_urls = []
    for media in media_list:
        url = upload_media_to_channel(media['file_id'], uid, media['type'])
        media_urls.append(url)
    db.profiles.update_one({"user_id": uid}, {"$set": {"media": media_urls}})
    bot.reply_to(m, f"✅ Media updated! {len(media_urls)} file(s) saved.")
    user_states.pop(uid, None)
    show_main_menu(m.chat.id)

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "editing_media" and m.text == "⏭️ Skip (keep current)")
def edit_media_skip(m):
    uid = m.from_user.id
    user_temp_data.pop(uid, None)
    user_states.pop(uid, None)
    bot.reply_to(m, "✅ Media kept.")
    show_main_menu(m.chat.id)
    # ---------- VIEW PROFILES ----------
@bot.message_handler(func=lambda m: m.text == "👀 VIEW PROFILES")
def view_profiles(m):
    uid = m.from_user.id
    my_profile = db.profiles.find_one({"user_id": uid, "is_active": True})
    if not my_profile:
        bot.reply_to(m, "❌ Create profile first using /start.")
        show_main_menu(m.chat.id)
        return
    
    user = db.users.find_one({"user_id": uid})
    pref = user.get("preference", "both") if user else "both"
    
    query = {"user_id": {"$ne": uid}, "is_active": True}
    if pref == "male":
        query["gender"] = "male"
    elif pref == "female":
        query["gender"] = "female"
    
    profiles = list(db.profiles.find(query).limit(200))
    if not profiles:
        bot.reply_to(m, "😔 No other active profiles found. Ask friends to join!")
        show_main_menu(m.chat.id)
        return
    
    random.shuffle(profiles)
    swipe_sessions[uid] = {"profiles": profiles, "index": 0}
    send_profile(m.chat.id, uid)

def send_profile(chat_id, uid):
    session = swipe_sessions.get(uid)
    if not session:
        return
    profiles = session["profiles"]
    if not profiles:
        bot.send_message(chat_id, "❌ No profiles available.")
        return
    idx = session["index"]
    if idx >= len(profiles):
        idx = 0
        session["index"] = 0
    p = profiles[idx]
    text = f"👤 {p.get('name')}\n🎂 Age: {p.get('age')}\n📍 {p.get('location_text', 'No location')}\n📝 {p.get('about', '')[:100]}"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("❤️ LIKE"),
        types.KeyboardButton("💬 CHAT"),
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
def like_profile(m):
    uid = m.from_user.id
    session = swipe_sessions.get(uid)
    if not session:
        bot.reply_to(m, "No active swipe session.")
        return
    target_id = session.get("current_profile_id")
    if not target_id:
        return
    
    db.likes.update_one(
        {"from_user": uid, "to_user": target_id},
        {"$set": {"created_at": datetime.utcnow()}},
        upsert=True
    )
    mutual = db.likes.find_one({"from_user": target_id, "to_user": uid})
    if mutual:
        db.likes.update_many(
            {"$or": [{"from_user": uid, "to_user": target_id}, {"from_user": target_id, "to_user": uid}]},
            {"$set": {"is_mutual": True}}
        )
        bot.reply_to(m, "🎉 It's a match! You can now chat.")
    else:
        bot.reply_to(m, "❤️ Liked!")
    session["index"] += 1
    send_profile(m.chat.id, uid)

# ---------- CHAT (only after mutual match) ----------
@bot.message_handler(func=lambda m: m.text == "💬 CHAT")
def chat_handler(m):
    uid = m.from_user.id
    session = swipe_sessions.get(uid)
    if not session:
        bot.reply_to(m, "❌ No active swipe session. Use VIEW PROFILES.")
        return
    target_id = session.get("current_profile_id")
    if not target_id:
        bot.reply_to(m, "❌ Profile not found.")
        return
    
    user_likes_target = db.likes.find_one({"from_user": uid, "to_user": target_id})
    target_likes_user = db.likes.find_one({"from_user": target_id, "to_user": uid})
    if not (user_likes_target and target_likes_user):
        bot.reply_to(m, "💬 Chat only allowed after mutual match. Like each other first!")
        return
    
    target_profile = db.profiles.find_one({"user_id": target_id, "is_active": True})
    if not target_profile:
        bot.reply_to(m, "❌ Target profile not active.")
        return
    
    target_name = target_profile.get('name', 'User')
    user_temp_data[uid] = {"chat_target": target_id, "chat_target_name": target_name}
    user_temp_data[target_id] = {"chat_target": uid, "chat_target_name": m.from_user.first_name}
    bot.reply_to(m, f"💬 You can now message {target_name}. Send your message (text/photo/video):")
    user_states[uid] = "awaiting_chat_message"

# ---------- Message forwarder ----------
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_chat_message", content_types=['text', 'photo', 'video'])
def receive_chat_message(m):
    uid = m.from_user.id
    if m.text and m.text in ["❤️ LIKE", "💬 CHAT", "⏭️ SKIP", "SKIP", "🛑 STOP VIEWING", "STOP VIEWING", "STOP"]:
        return
    target_info = user_temp_data.get(uid, {})
    target_id = target_info.get("chat_target")
    target_name = target_info.get("chat_target_name")
    if not target_id:
        bot.reply_to(m, "❌ Chat session expired. Use VIEW PROFILES again.")
        user_states.pop(uid, None)
        return
    
    try:
        if m.text:
            bot.send_message(target_id, f"💬 Message from {m.from_user.first_name}:\n{m.text}")
        elif m.photo:
            bot.send_photo(target_id, m.photo[-1].file_id, caption=f"📸 Photo from {m.from_user.first_name}")
        elif m.video:
            bot.send_video(target_id, m.video.file_id, caption=f"🎥 Video from {m.from_user.first_name}")
        bot.reply_to(m, f"✅ Message sent to {target_name}.")
    except:
        pass

# ---------- Helper: Start view profiles for a user ----------
def start_view_profiles_for_user(chat_id, user_id):
    """Start a new swipe session for the user (clears any existing)"""
    if user_id in swipe_sessions:
        del swipe_sessions[user_id]
    my_profile = db.profiles.find_one({"user_id": user_id, "is_active": True})
    if not my_profile:
        bot.send_message(chat_id, "❌ Create profile first using /start.")
