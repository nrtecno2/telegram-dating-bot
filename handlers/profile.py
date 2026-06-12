from telebot import types
import database


def register_profile_handler(bot):

    @bot.message_handler(func=lambda message: True)
    def profile_steps(message):

        user_id = message.from_user.id

        user = database.get_user(user_id)

        if user is None:
            database.add_user(user_id)
            user = database.get_user(user_id)

        # Name

        if user[1] is None:

            database.update_field(
                user_id,
                "name",
                message.text
            )

            markup = types.InlineKeyboardMarkup(
                row_width=2
            )

            markup.add(

                types.InlineKeyboardButton(
                    "Male",
                    callback_data="gender_male"
                ),

                types.InlineKeyboardButton(
                    "Female",
                    callback_data="gender_female"
                )

            )

            bot.send_message(
                message.chat.id,
                "Apna Gender Select Kare.",
                reply_markup=markup
            )

            return

        # Age

        if user[2] is not None and user[3] is None:

            if not message.text.isdigit():

                bot.send_message(
                    message.chat.id,
                    "Valid Age Enter Kare."
                )

                return

            database.update_field(
                user_id,
                "age",
                int(message.text)
            )

            bot.send_message(
                message.chat.id,
                "Apni Location Likhe."
            )

            return

        # Location

        if user[4] is None:

            database.update_field(
                user_id,
                "location",
                message.text
            )

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True
            )

            markup.add("Skip")

            bot.send_message(

                message.chat.id,

                "Apne Bare Me Likhe (500 Characters Max)",

                reply_markup=markup

            )

            return

        # About

        if user[5] is None:

            about = ""

            if message.text != "Skip":

                if len(message.text) > 500:

                    bot.send_message(

                        message.chat.id,

                        "500 Characters Se Kam Likhe."

                    )

                    return

                about = message.text

            database.update_field(
                user_id,
                "about",
                about
            )

            bot.send_message(

                message.chat.id,

                "Profile Ka Pehla Bhag Complete Hua ✅"

            )



    @bot.callback_query_handler(
        func=lambda call:
        call.data.startswith("gender_")
    )
    def gender(call):

        user_id = call.from_user.id

        if call.data == "gender_male":

            database.update_field(
                user_id,
                "gender",
                "Male"
            )

        else:

            database.update_field(
                user_id,
                "gender",
                "Female"
            )

        bot.answer_callback_query(
            call.id,
            "Gender Saved"
        )

        bot.send_message(
            call.message.chat.id,
            "Apni Age Likhe."
          )
