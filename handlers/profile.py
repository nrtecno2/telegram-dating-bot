from telebot import types

import database

from utils.states import *


def register_profile_handler(bot):


    @bot.message_handler(
        func=lambda message:
        get_state(
            message.from_user.id
        ) == NAME
    )
    def get_name(message):

        user_id = message.from_user.id

        database.add_user(
            user_id
        )

        database.update_field(

            user_id,

            "name",

            message.text

        )

        set_state(

            user_id,

            GENDER

        )

        markup = (
            types.InlineKeyboardMarkup(
                row_width=2
            )
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



    @bot.callback_query_handler(

        func=lambda call:

        call.data.startswith(

            "gender_"

        )

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

        set_state(

            user_id,

            AGE

        )

        bot.answer_callback_query(

            call.id,

            "Saved"

        )

        bot.send_message(

            call.message.chat.id,

            "Apni Age Likhe."

        )



    @bot.message_handler(

        func=lambda message:

        get_state(

            message.from_user.id

        ) == AGE

    )

    def get_age(message):

        if not message.text.isdigit():

            bot.send_message(

                message.chat.id,

                "Valid Age Likhe."

            )

            return

        user_id = message.from_user.id

        database.update_field(

            user_id,

            "age",

            int(

                message.text

            )

        )

        set_state(

            user_id,

            LOCATION

        )

        markup = (

            types.ReplyKeyboardMarkup(

                resize_keyboard=True,

                one_time_keyboard=True

            )

        )

        button = (

            types.KeyboardButton(

                "📍 Share Location",

                request_location=True

            )

        )

        markup.add(

            button

        )

        bot.send_message(

            message.chat.id,

            "Apni Location Share Kare.",

            reply_markup=markup

        )



    @bot.message_handler(

        content_types=[

            "location"

        ]

    )

    def get_location(message):

        if get_state(

            message.from_user.id

        ) != LOCATION:

            return

        user_id = message.from_user.id

        location = (

            str(

                message.location.latitude

            )

            +

            ","

            +

            str(

                message.location.longitude

            )

        )

        database.update_field(

            user_id,

            "location",

            location

        )

        set_state(

            user_id,

            ABOUT

        )

        markup = (

            types.ReplyKeyboardMarkup(

                resize_keyboard=True,

                one_time_keyboard=True

            )

        )

        markup.add(

            "Skip"

        )

        bot.send_message(

            message.chat.id,

            "Apne Bare Me Likhe.\n\n(Max 500 Characters)",

            reply_markup=markup

        )



    @bot.message_handler(

        func=lambda message:

        get_state(

            message.from_user.id

        ) == ABOUT

    )

    def get_about(message):

        user_id = message.from_user.id

        about = ""

        if message.text != "Skip":

            if len(

                message.text

            ) > 500:

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

        clear_state(

            user_id

        )

        bot.send_message(

            message.chat.id,

            "Basic Profile Complete ✅"

        )
