from telebot import types

import database

from utils.states import *
from utils.storage import *


media_counter = {}


def register_profile_handler(bot):


    @bot.message_handler(
        func=lambda message:
        get_state(message.from_user.id) == NAME
    )
    def get_name(message):

        user_id = message.from_user.id

        database.add_user(user_id)

        database.update_field(
            user_id,
            "name",
            message.text
        )

        set_state(
            user_id,
            GENDER
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
            "Gender Select Kare.",
            reply_markup=markup
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
        get_state(message.from_user.id) == AGE
    )
    def get_age(message):

        if not message.text.isdigit():

            bot.send_message(
                message.chat.id,
                "Valid Age Likhe."
            )

            return

        database.update_field(
            message.from_user.id,
            "age",
            int(message.text)
        )

        set_state(
            message.from_user.id,
            LOCATION
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True
        )

        markup.add(

            types.KeyboardButton(
                "📍 Share Location",
                request_location=True
            )

        )

        bot.send_message(
            message.chat.id,
            "Location Share Kare.",
            reply_markup=markup
        )



    @bot.message_handler(
        content_types=["location"]
    )
    def get_location(message):

        if get_state(
            message.from_user.id
        ) != LOCATION:
            return

        location = str(
            message.location.latitude
        ) + "," + str(
            message.location.longitude
        )

        database.update_field(
            message.from_user.id,
            "location",
            location
        )

        set_state(
            message.from_user.id,
            ABOUT
        )

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True
        )

        markup.add(
            "Skip"
        )

        bot.send_message(
            message.chat.id,
            "Apne Bare Me Likhe.\n(Max 500 Characters)",
            reply_markup=markup
        )



    @bot.message_handler(
        func=lambda message:
        get_state(message.from_user.id) == ABOUT
    )
    def get_about(message):

        about = ""

        if message.text != "Skip":

            if len(
                message.text
            ) > 500:

                bot.send_message(
                    message.chat.id,
                    "500 Characters Maximum."
                )

                return

            about = message.text

        database.update_field(
            message.from_user.id,
            "about",
            about
        )

        media_counter[
            message.from_user.id
        ] = 0

        set_state(
            message.from_user.id,
            MEDIA
        )

        bot.send_message(

            message.chat.id,

            "1 Se 3 Photos Ya Videos Upload Kare."

        )



    @bot.message_handler(
        content_types=[
            "photo"
        ]
    )
    def photo(message):

        if get_state(
            message.from_user.id
        ) != MEDIA:
            return

        save_photo(
            bot,
            message
        )

        media_counter[
            message.from_user.id
        ] += 1

        check_media(
            message
        )



    @bot.message_handler(
        content_types=[
            "video"
        ]
    )
    def video(message):

        if get_state(
            message.from_user.id
        ) != MEDIA:
            return

        save_video(
            bot,
            message
        )

        media_counter[
            message.from_user.id
        ] += 1

        check_media(
            message
        )



    def check_media(message):

        count = media_counter[
            message.from_user.id
        ]

        if count >= 3:

            show_confirm(
                message.chat.id
            )

            return

        markup = (
            types.InlineKeyboardMarkup()
        )

        markup.add(

            types.InlineKeyboardButton(

                "✅ Confirm",

                callback_data="confirm_media"

            )

        )

        bot.send_message(

            message.chat.id,

            f"{count}/3 Media Upload Hui.",

            reply_markup=markup

        )



    @bot.callback_query_handler(
        func=lambda call:
        call.data == "confirm_media"
    )
    def confirm(call):

        set_state(
            call.from_user.id,
            PREFERENCE
        )

        markup = (
            types.InlineKeyboardMarkup(
                row_width=1
            )
        )

        markup.add(

            types.InlineKeyboardButton(
                "Male",
                callback_data="pref_male"
            )

        )

        markup.add(

            types.InlineKeyboardButton(
                "Female",
                callback_data="pref_female"
            )

        )

        markup.add(

            types.InlineKeyboardButton(
                "Both",
                callback_data="pref_both"
            )

        )

        bot.send_message(

            call.message.chat.id,

            "Apni Choice Select Kare.",

            reply_markup=markup

        )



    @bot.callback_query_handler(
        func=lambda call:
        call.data.startswith(
            "pref_"
        )
    )
    def preference(call):

        value = call.data.replace(
            "pref_",
            ""
        )

        database.update_field(

            call.from_user.id,

            "preference",

            value

        )

        database.update_field(

            call.from_user.id,

            "completed",

            1

        )

        clear_state(
            call.from_user.id
        )

        markup = (
            types.ReplyKeyboardMarkup(
                resize_keyboard=True
            )
        )

        markup.row(
            "👤 My Profile"
        )

        markup.row(
            "❤️ View Profiles"
        )

        markup.row(
            "🔔 Notifications"
        )

        bot.send_message(

            call.message.chat.id,

            "Profile Complete ✅",

            reply_markup=markup

        )
