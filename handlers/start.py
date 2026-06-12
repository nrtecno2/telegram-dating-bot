from telebot import types
from utils.force_join import check_force_join


def register_start_handler(bot):

    @bot.message_handler(commands=["start"])
    def start(message):

        if not check_force_join(
            bot,
            message.from_user.id
        ):

            markup = types.InlineKeyboardMarkup()

            join_btn = types.InlineKeyboardButton(
                "📢 Join Channel",
                url="https://t.me/nrtecno2"
            )

            verify_btn = types.InlineKeyboardButton(
                "✅ Verify",
                callback_data="verify_join"
            )

            markup.add(join_btn)
            markup.add(verify_btn)

            bot.send_message(
                message.chat.id,
                "Bot use karne ke liye pahle hamara channel join kare.",
                reply_markup=markup
            )

            return

        bot.send_message(
            message.chat.id,
            "Welcome ❤️\n\nAapne channel join kar liya hai."
        )
