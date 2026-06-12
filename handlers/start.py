from telebot import types

from utils.force_join import check_force_join

from utils.states import set_state
from utils.states import NAME


def register_start_handler(bot):


    @bot.message_handler(
        commands=["start"]
    )
    def start(message):

        if not check_force_join(

            bot,

            message.from_user.id

        ):

            markup = (
                types.InlineKeyboardMarkup(
                    row_width=1
                )
            )

            markup.add(

                types.InlineKeyboardButton(

                    text="📢 Join Channel",

                    url="https://t.me/nrtecno2"

                )

            )

            markup.add(

                types.InlineKeyboardButton(

                    text="✅ Verify",

                    callback_data="verify_join"

                )

            )

            bot.send_message(

                message.chat.id,

                "Bot use karne ke liye pahle hamara channel join kare.",

                reply_markup=markup

            )

            return


        set_state(

            message.from_user.id,

            NAME

        )

        bot.send_message(

            message.chat.id,

            "Apna Name Likhe."

        )



    @bot.callback_query_handler(

        func=lambda call:

        call.data == "verify_join"

    )

    def verify(call):

        if check_force_join(

            bot,

            call.from_user.id

        ):

            bot.answer_callback_query(

                call.id,

                "Verification Successful"

            )

            bot.delete_message(

                call.message.chat.id,

                call.message.message_id

            )

            set_state(

                call.from_user.id,

                NAME

            )

            bot.send_message(

                call.message.chat.id,

                "Apna Name Likhe."

            )

        else:

            bot.answer_callback_query(

                call.id,

                "Pahle Channel Join Kare.",

                show_alert=True

            )
