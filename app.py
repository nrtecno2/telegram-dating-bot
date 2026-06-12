from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Telegram Dating Bot is Running Successfully!"
