import os, logging, threading, time
from flask import Flask
import telebot
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)
@flask_app.route('/')
def health(): return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "Bot is working!")

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(2)
    logger.info("Bot polling...")
    bot.infinity_polling()

if __name__ == "__main__":
    main()
