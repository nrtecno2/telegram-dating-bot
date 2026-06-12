from telebot import types
from utils.force_join import check_force_join


def register_start_handler(bot):

    @bot.message_handler(commands=["start"])
    def start(message):

        if not check_force_join(
            bot,
            message.from_user.id
        ):

            markup = types.InlineKeyboardMarkup(
                row_width=1
            )

            join_button = (
                types.InlineKeyboardButton(
                    text="📢 Join Channel",
                    url="https://t.me/nrtecno2"
                )
            )

            verify_button = (
                types.InlineKeyboardButton(
                    text="✅ Verify",
                    callback_data="verify_join"
                )
            )

            markup.add(
                join_button,
                verify_button
            )

            bot.send_message(
                message.chat.id,
                "Bot ka use karne ke liye pahle hamara channel join kare.",
                reply_markup=markup
            )

            return

        bot.send_message(
            message.chat.id,
            "Welcome ❤️\n\nAap channel join kar chuke hain."
        )



    @bot.callback_query_handler(
        func=lambda call: call.data == "verify_join"
    )
    def verify_join(call):

        if check_force_join(
            bot,
            call.from_user.id
        ):

            bot.answer_callback_query(
                call.id,
                "Verification Successful ✅"
            )

            bot.delete_message(
                call.message.chat.id,
                call.message.message_id
            )

            bot.send_message(
                call.message.chat.id,
                "Welcome ❤️\n\nAap channel join kar chuke hain."
            )

        else:

            bot.answer_callback_query(
                call.id,
                "Pahle channel join kare.",
                show_alert=True
            )
