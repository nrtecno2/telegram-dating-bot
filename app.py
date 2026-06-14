#!/usr/bin/env python3
import os
import logging
import threading
import time
from datetime import datetime
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

# ---------- User Stores ----------
user_states = {}
user_temp_data = {}

# ---------- Helper: Show Main Menu ----------
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

# ---------- /start Command ----------
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    # For simplicity, we directly start profile creation (no channel verification here, but you can add)
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
    # Gender buttons
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
        bot.reply_to(m, "❌ Invalid age. Send number between 18-100.")
        return
    user_temp_data[uid]['age'] = age
    user_states[uid] = "awaiting_location"
    # Location keyboard with skip option
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("📍 Send Location", request_location=True), types.KeyboardButton("⏭️ Skip Location"))
    bot.reply_to(m, f"✅ Age: {age}\n\nShare your location or type city name (or tap Skip):", reply_markup=markup)

# ---------- Location (live or text) ----------
@bot.message_handler(content_types=['location'])
def process_location_live(m):
    uid = m.from_user.id
    if user_states.get(uid) != "awaiting_location":
        return
    lat = m.location.latitude
    lon = m.location.longitude
    user_temp_data[uid]['location'] = f"{lat},{lon}"
    user_states[uid] = "awaiting_about"
    bot.reply_to(m, "✅ Location saved!\n\nSend your **About** (max 500 chars) or /skip:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_location")
def process_location_text(m):
    uid = m.from_user.id
    text = m.text.strip()
    if text == "⏭️ Skip Location":
        user_temp_data[uid]['location'] = ""
        user_states[uid] = "awaiting_about"
        bot.reply_to(m, "✅ Location skipped.\n\nSend your **About** (max 500 chars) or /skip:", reply_markup=types.ReplyKeyboardRemove())
        return
    if len(text) < 2:
        bot.reply_to(m, "❌ Invalid location. Type city name or tap Skip.")
        return
    user_temp_data[uid]['location'] = text
    user_states[uid] = "awaiting_about"
    bot.reply_to(m, f"✅ Location: {text}\n\nSend your **About** (max 500 chars) or /skip:", reply_markup=types.ReplyKeyboardRemove())

# ---------- About ----------
@bot.message_handler(commands=['skip'])
def skip_about(m):
    uid = m.from_user.id
    if user_states.get(uid) == "awaiting_about":
        user_temp_data[uid]['about'] = ""
        user_states[uid] = "awaiting_media"
        user_temp_data[uid]['media_list'] = []
        bot.reply_to(m, "About skipped. Now send **1-3 photos/videos** (type /done when finished):", reply_markup=types.ReplyKeyboardRemove())

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
    bot.reply_to(m, "About saved. Send **1-3 photos/videos** (type /done when finished):")

# ---------- Media ----------
@bot.message_handler(content_types=['photo', 'video'])
def process_media(m):
    uid = m.from_user.id
    if user_states.get(uid) != "awaiting_media":
        return
    media_list = user_temp_data[uid].get('media_list', [])
    if len(media_list) >= 3:
        bot.reply_to(m, "❌ Max 3 files already. Type /done.")
        return
    if m.photo:
        file_id = m.photo[-1].file_id
        media_list.append(file_id)
    elif m.video:
        media_list.append(m.video.file_id)
    user_temp_data[uid]['media_list'] = media_list
    remaining = 3 - len(media_list)
    bot.reply_to(m, f"✅ Media {len(media_list)}/3 added. {remaining} remaining. Send more or /done.")

@bot.message_handler(commands=['done'])
def done_media(m):
    uid = m.from_user.id
    if user_states.get(uid) != "awaiting_media":
        return
    temp = user_temp_data.get(uid, {})
    media = temp.get('media_list', [])
    if not media:
        bot.reply_to(m, "❌ Please send at least 1 photo or video.")
        return
    # Show profile preview with confirm/cancel buttons
    preview = f"📋 **Profile Preview**\n"
    preview += f"👤 Name: {temp.get('name')}\n"
    preview += f"⚧ Gender: {'Male' if temp.get('gender')=='male' else 'Female'}\n"
    preview += f"🎂 Age: {temp.get('age')}\n"
    preview += f"📍 Location: {temp.get('location', 'Not provided')}\n"
    preview += f"📝 About: {temp.get('about', 'Not provided')[:100]}\n"
    preview += f"📷 Media: {len(media)} file(s)\n\nConfirm to save?"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("✅ CONFIRM"), types.KeyboardButton("❌ CANCEL"))
    user_states[uid] = "awaiting_confirm"
    bot.reply_to(m, preview, reply_markup=markup)

# ---------- Confirm / Cancel ----------
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_confirm" and m.text == "✅ CONFIRM")
def confirm_profile(m):
    uid = m.from_user.id
    temp = user_temp_data.pop(uid, {})
    user_states.pop(uid, None)
    # Here you would save to database. For now, just acknowledge.
    bot.reply_to(m, "🎉 **Profile Created!** 🎉\n\nNow set your preference.", reply_markup=types.ReplyKeyboardRemove())
    # Ask preference
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("👨 Male"), types.KeyboardButton("👩 Female"), types.KeyboardButton("👥 Both"))
    user_states[uid] = "awaiting_preference"
    bot.reply_to(m, "Who do you want to see in your feed?", reply_markup=markup)

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_confirm" and m.text == "❌ CANCEL")
def cancel_profile(m):
    uid = m.from_user.id
    user_states.pop(uid, None)
    user_temp_data.pop(uid, None)
    bot.reply_to(m, "❌ Profile creation cancelled. Use /start to try again.", reply_markup=types.ReplyKeyboardRemove())

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
        bot.reply_to(m, "❌ Please tap Male, Female or Both button.")
        return
    # Save preference (dummy)
    user_states.pop(uid, None)
    bot.reply_to(m, f"✅ Preference set to {text}.", reply_markup=types.ReplyKeyboardRemove())
    show_main_menu(m.chat.id)

# ---------- Main Menu Handlers ----------
@bot.message_handler(func=lambda m: m.text == "👤 MY PROFILE")
def my_profile(m):
    bot.reply_to(m, "👤 Your profile will be shown here (fetch from DB).", reply_markup=types.ReplyKeyboardRemove())
    show_main_menu(m.chat.id)

@bot.message_handler(func=lambda m: m.text == "👀 VIEW PROFILES")
def view_profiles(m):
    bot.reply_to(m, "👀 View profiles feature coming soon.", reply_markup=types.ReplyKeyboardRemove())
    show_main_menu(m.chat.id)

@bot.message_handler(func=lambda m: m.text == "🔔 NOTIFICATIONS")
def notifications(m):
    bot.reply_to(m, "🔔 No new notifications.", reply_markup=types.ReplyKeyboardRemove())
    show_main_menu(m.chat.id)

@bot.message_handler(func=lambda m: m.text == "🎯 CHANGE INTEREST")
def change_interest(m):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("👨 Male"), types.KeyboardButton("👩 Female"), types.KeyboardButton("👥 Both"))
    bot.reply_to(m, "Select your new preference:", reply_markup=markup)
    user_states[m.from_user.id] = "changing_interest"

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "changing_interest")
def update_interest(m):
    uid = m.from_user.id
    text = m.text.strip()
    if text in ["👨 Male", "👩 Female", "👥 Both"]:
        # save new preference
        bot.reply_to(m, f"Preference changed to {text}.", reply_markup=types.ReplyKeyboardRemove())
        user_states.pop(uid, None)
        show_main_menu(m.chat.id)
    else:
        bot.reply_to(m, "Use buttons.")

@bot.message_handler(func=lambda m: m.text == "📊 STATS")
def stats(m):
    bot.reply_to(m, "📊 Stats: No data yet.", reply_markup=types.ReplyKeyboardRemove())
    show_main_menu(m.chat.id)

@bot.message_handler(func=lambda m: m.text == "⚙️ SETTINGS")
def settings(m):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(types.KeyboardButton("🗑 DELETE ACCOUNT"), types.KeyboardButton("🔙 BACK"))
    bot.reply_to(m, "⚙️ Settings", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🗑 DELETE ACCOUNT")
def delete_account(m):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("✅ CONFIRM DELETE"), types.KeyboardButton("❌ CANCEL"))
    bot.reply_to(m, "⚠️ Are you sure? This is permanent.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "✅ CONFIRM DELETE")
def confirm_delete(m):
    uid = m.from_user.id
    # soft delete
    bot.reply_to(m, "Account deleted. Use /start to create new.", reply_markup=types.ReplyKeyboardRemove())
    user_states.pop(uid, None)
    user_temp_data.pop(uid, None)

@bot.message_handler(func=lambda m: m.text == "❌ CANCEL")
def cancel_action(m):
    show_main_menu(m.chat.id)

@bot.message_handler(func=lambda m: m.text == "🔙 BACK")
def back_to_main(m):
    show_main_menu(m.chat.id)

# ---------- Fallback ----------
@bot.message_handler(func=lambda m: True)
def fallback(m):
    bot.reply_to(m, "Use /start or buttons below.", reply_markup=types.ReplyKeyboardRemove())

# ---------- Main ----------
def main():
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(2)
    logger.info("Bot polling started...")
    bot.infinity_polling()

if __name__ == "__main__":
    main()
