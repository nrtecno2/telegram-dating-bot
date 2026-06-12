import os

from telebot import types


# ==========================
# CHANNEL
# ==========================

REQUIRED_CHANNEL = os.environ.get(
    "CHANNEL_USERNAME"
)


# ==========================
# CHECK JOIN
# ==========================

def check_force_join(

    bot,

    user_id

):

    try:

        member = bot.get_chat_member(

            REQUIRED_CHANNEL,

            user_id

        )

        if member.status in [

            "creator",

            "administrator",

            "member"

        ]:

            return True

    except:

        pass

    return False


# ==========================
# JOIN KEYBOARD
# ==========================

def join_keyboard():

    markup = (
        types.InlineKeyboardMarkup(
            row_width=1
        )
    )

    join_button = (
        types.InlineKeyboardButton(

            text="📢 Join Channel",

            url=f"https://t.me/{REQUIRED_CHANNEL.replace('@','')}"

        )
    )

    verify_button = (
        types.InlineKeyboardButton(

            text="✅ Verify",

            callback_data="verify_join"

        )
    )

    markup.add(
        join_button
    )

    markup.add(
        verify_button
    )

    return markup


# ==========================
# SEND FORCE JOIN
# ==========================

def send_force_join(

    bot,

    chat_id

):

    bot.send_message(

        chat_id,

        "Bot use karne ke liye pahle hamara channel join kare.",

        reply_markup=join_keyboard()

    )
