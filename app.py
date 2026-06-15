import os
import time
import threading
from flask import Flask
import telebot
from telebot import types

# ---------- Flask ----------
flask_app = Flask(__name__)
@flask_app.route('/')
def health(): return "OK", 200
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

# ---------- Bot ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# ---------- Simple start ----------
@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "✅ Bot is working! Use /menu")

@bot.message_handler(commands=['menu'])
def menu(m):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("👤 Profile"), types.KeyboardButton("👀 View"))
    bot.reply_to(m, "Choose:", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def echo(m):
    bot.reply_to(m, f"You said: {m.text}")

# ---------- Main ----------
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(2)
    bot.remove_webhook()
    print("Bot polling started...")
    bot.infinity_polling(skip_pending=True)
