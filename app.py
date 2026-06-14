#!/usr/bin/env python3
import os
import logging
import threading
import time
from flask import Flask
import telebot
from telebot import types
from dotenv import load_dotenv

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

# ---------- Bot ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='Markdown')

# ---------- Simple In-Memory Store ----------
user_states = {}
user_temp_data = {}

# ---------- Handlers ----------

@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    user_states[user_id] = "awaiting_name"
    user_temp_data[user_id] = {}
    bot.reply_to(message, "Welcome! Please send your Name (2-50 chars):")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_name")
def process_name(message):
    user_id = message.from_user.id
    name = message.text.strip()
    if len(name) < 2 or len(name) > 50:
        bot.reply_to(message, "❌ Name must be 2-50 chars. Try again.")
        return
    user_temp_data[user_id]['name'] = name
    user_states[user_id] = "awaiting_gender"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("👨 Male"), types.KeyboardButton("👩 Female"))
    bot.reply_to(message, f"✅ Name: {name}\n\nSelect your Gender:", reply_markup=markup)

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_gender")
def process_gender(message):
    user_id = message.from_user.id
    text = message.text.strip()
    if text == "👨 Male":
        gender = "male"
    elif text == "👩 Female":
        gender = "female"
    else:
        bot.reply_to(message, "❌ Please tap Male or Female button.")
        return
    user_temp_data[user_id]['gender'] = gender
    user_states[user_id] = "awaiting_age"
    bot.reply_to(message, f"✅ Gender: {text.replace('👨 ', '').replace('👩 ', '')}\n\nSend your Age (18-100):", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_age")
def process_age(message):
    user_id = message.from_user.id
    try:
        age = int(message.text.strip())
        if age < 18 or age > 100:
            raise ValueError
    except:
        bot.reply_to(message, "❌ Invalid age. Send 18-100.")
        return
    user_temp_data[user_id]['age'] = age
    user_states[user_id] = "awaiting_location"
    bot.reply_to(message, f"✅ Age: {age}\n\nSend your Location (city) or tap /skip to skip:")

@bot.message_handler(commands=['skip'])
def skip_location(message):
    user_id = message.from_user.id
    if user_states.get(user_id) == "awaiting_location":
        user_temp_data[user_id]['location'] = ""
        user_states[user_id] = "awaiting_about"
        bot.reply_to(message, "Location skipped. Send About (max 500 chars) or /skip:")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_location")
def process_location(message):
    user_id = message.from_user.id
    loc = message.text.strip()
    if len(loc) < 2:
        bot.reply_to(message, "❌ Invalid location. Send city name or /skip")
        return
    user_temp_data[user_id]['location'] = loc
    user_states[user_id] = "awaiting_about"
    bot.reply_to(message, f"✅ Location: {loc}\n\nSend About (max 500 chars) or /skip:")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_about")
def process_about(message):
    user_id = message.from_user.id
    if message.text == '/skip':
        about = ""
    else:
        about = message.text.strip()
        if len(about) > 500:
            bot.reply_to(message, "❌ Too long. Max 500 chars.")
            return
    user_temp_data[user_id]['about'] = about
    user_states[user_id] = "awaiting_media"
    user_temp_data[user_id]['media'] = []
    bot.reply_to(message, "Send 1-3 photos/videos. Type /done when finished.")

@bot.message_handler(content_types=['photo', 'video'])
def process_media(message):
    user_id = message.from_user.id
    if user_states.get(user_id) != "awaiting_media":
        return
    media_list = user_temp_data[user_id].get('media', [])
    if len(media_list) >= 3:
        bot.reply_to(message, "Max 3 files already. Type /done")
        return
    if message.photo:
        file_id = message.photo[-1].file_id
        media_list.append(file_id)
    elif message.video:
        media_list.append(message.video.file_id)
    user_temp_data[user_id]['media'] = media_list
    remaining = 3 - len(media_list)
    bot.reply_to(message, f"✅ {len(media_list)}/3 added. {remaining} remaining. Send more or /done")

@bot.message_handler(commands=['done'])
def done_media(message):
    user_id = message.from_user.id
    if user_states.get(user_id) != "awaiting_media":
        return
    temp = user_temp_data[user_id]
    name = temp.get('name')
    gender = temp.get('gender')
    age = temp.get('age')
    location = temp.get('location', '')
    about = temp.get('about', '')
    media = temp.get('media', [])
    if not name or not gender or not age:
        bot.reply_to(message, "❌ Incomplete profile. Use /start again.")
        return

    preview = f"📋 PREVIEW\nName: {name}\nGender: {'Male' if gender=='male' else 'Female'}\nAge: {age}\nLocation: {location}\nAbout: {about[:100]}\nMedia: {len(media)} files"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("✅ CONFIRM"), types.KeyboardButton("❌ CANCEL"))
    user_states[user_id] = "awaiting_confirm"
    bot.reply_to(message, preview + "\n\nConfirm to save?", reply_markup=markup)

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_confirm" and m.text == "✅ CONFIRM")
def confirm_profile(message):
    user_id = message.from_user.id
    temp = user_temp_data.pop(user_id, {})
    user_states.pop(user_id, None)
    # Save to database (dummy for now)
    bot.reply_to(message, "🎉 Profile created! Now set preference.", reply_markup=types.ReplyKeyboardRemove())
    # Ask preference
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("👨 Male"), types.KeyboardButton("👩 Female"), types.KeyboardButton("👥 Both"))
    user_states[user_id] = "awaiting_preference"
    bot.reply_to(message, "Who do you want to see?", reply_markup=markup)

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_preference")
def set_preference(message):
    user_id = message.from_user.id
    text = message.text
    if text == "👨 Male":
        pref = "male"
    elif text == "👩 Female":
        pref = "female"
    elif text == "👥 Both":
        pref = "both"
    else:
        bot.reply_to(message, "Use buttons.")
        return
    # Save preference (dummy)
    user_states.pop(user_id, None)
    bot.reply_to(message, f"Preference set to {text}. Bot is ready!", reply_markup=types.ReplyKeyboardRemove())

# Fallback
@bot.message_handler(func=lambda m: True)
def fallback(m):
    bot.reply_to(m, "Use /start")

# ---------- Main ----------
def main():
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(2)
    logger.info("Starting bot polling...")
    bot.infinity_polling()

if __name__ == "__main__":
    main()
