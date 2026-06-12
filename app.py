import os
import telebot

from flask import Flask
from flask import request

import database

from handlers.start import register_start_handler
from handlers.profile import register_profile_handler


BOT_TOKEN = os.environ.get(
    "BOT_TOKEN"
)

bot = telebot.TeleBot(
    BOT_TOKEN
)

app = Flask(__name__)


# ==========================
# REGISTER HANDLERS
# ==========================

register_start_handler(
    bot
)

register_profile_handler(
    bot
)


# ==========================
# HOME PAGE
# ==========================

@app.route(
    "/"
)

def home():

    return "Telegram Dating Bot Running Successfully"


# ==========================
# WEBHOOK
# ==========================

@app.route(

    f"/{BOT_TOKEN}",

    methods=[
        "POST"
    ]

)

def webhook():

    json_string = request.get_data().decode(
        "utf-8"
    )

    update = telebot.types.Update.de_json(
        json_string
    )

    bot.process_new_updates(
        [
            update
        ]
    )

    return "OK", 200


# ==========================
# MAIN
# ==========================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=5000

    )
