import os
import telebot

from flask import Flask, request

BOT_TOKEN = os.environ.get("BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)


@app.route("/")
def home():
    return "Dating Bot Working Successfully"


@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():

    json_string = request.get_data().decode("utf-8")

    update = telebot.types.Update.de_json(
        json_string
    )

    bot.process_new_updates(
        [update]
    )

    return "OK", 200


@bot.message_handler(commands=["start"])
def start(message):

    bot.reply_to(
        message,
        "Bot Successfully Connected ✅"
    )


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000
    )
