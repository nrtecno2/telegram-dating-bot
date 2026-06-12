from telebot import types

import database
from handlers.chat import send_first_message


viewing_users = {}


def register_view_profiles_handler(bot):


    @bot.message_handler(
        func=lambda message:
        message.text == "❤️ View Profiles"
    )
    def start_view(message):

        user_id = message.from_user.id

        user = database.get_user(
            user_id
        )

        if not user:

            bot.send_message(
                message.chat.id,
                "Pahle Profile Banaiye."
            )
            return

        preference = user[6]

        all_users = database.get_all_users()

        profiles = []

        for target in all_users:

            if target[0] == user_id:
                continue

            if target[7] != 1:
                continue

            if preference == "both":

                profiles.append(
                    target[0]
                )

            elif preference.lower() == target[2].lower():

                profiles.append(
                    target[0]
                )

        if len(
            profiles
        ) == 0:

            bot.send_message(

                message.chat.id,

                "Koi Profile Nahi Mili."

            )

            return

        viewing_users[
            user_id
        ] = profiles

        show_next_profile(

            bot,

            message.chat.id,

            user_id

        )


    def show_next_profile(

        bot,

        chat_id,

        viewer

    ):

        if viewer not in viewing_users:

            bot.send_message(

                chat_id,

                "Profiles Band."

            )

            return

        if len(
            viewing_users[
                viewer
            ]
        ) == 0:

            bot.send_message(

                chat_id,

                "Aur Profiles Nahi Hai."

            )

            return

        target = (
            viewing_users[
                viewer
            ][0]
        )

        target_user = (
            database.get_user(
                target
            )
        )

        media = (
            database.get_media(
                target
            )
        )

        text = f"""

👤 Name : {target_user[1]}

🚻 Gender : {target_user[2]}

🎂 Age : {target_user[3]}

📍 Location : {target_user[4]}

📝 About :

{target_user[5]}

"""

        if len(media):

            item = media[0]

            if item[3] == "photo":

                bot.send_photo(

                    chat_id,

                    item[2],

                    caption=text

                )

            else:

                bot.send_video(

                    chat_id,

                    item[2],

                    caption=text

                )

        else:

            bot.send_message(

                chat_id,

                text

            )

        markup = (
            types.InlineKeyboardMarkup(
                row_width=2
            )
        )

        markup.add(

            types.InlineKeyboardButton(

                "❤️ Like",

                callback_data=
                f"like_{target}"

            ),

            types.InlineKeyboardButton(

                "💬 Chat",

                callback_data=
                f"chat_{target}"

            )

        )

        markup.add(

            types.InlineKeyboardButton(

                "⏭ Skip",

                callback_data=
                "skip_profile"

            ),

            types.InlineKeyboardButton(

                "🛑 Stop",

                callback_data=
                "stop_profile"

            )

        )

        bot.send_message(

            chat_id,

            "Action Select Kare.",

            reply_markup=markup

        )


    @bot.callback_query_handler(
        func=lambda call:
        call.data.startswith(
            "like_"
        )
    )
    def like(call):

        target = int(
            call.data.replace(
                "like_",
                ""
            )
        )

        database.add_like(

            call.from_user.id,

            target

        )

        database.add_notification(

            target,

            "like",

            str(
                call.from_user.id
            )

        )

        bot.answer_callback_query(

            call.id,

            "Liked ❤️"

        )


    @bot.callback_query_handler(
        func=lambda call:
        call.data.startswith(
            "chat_"
        )
    )
    def chat(call):

        target = int(
            call.data.replace(
                "chat_",
                ""
            )
        )

        send_first_message(

            bot,

            call.from_user.id,

            target

        )

        bot.answer_callback_query(

            call.id,

            "Chat Started"

        )


    @bot.callback_query_handler(
        func=lambda call:
        call.data ==
        "skip_profile"
    )
    def skip(call):

        user_id = (
            call.from_user.id
        )

        if user_id in viewing_users:

            if len(
                viewing_users[
                    user_id
                ]
            ):

                viewing_users[
                    user_id
                ].pop(
                    0
                )

        show_next_profile(

            bot,

            call.message.chat.id,

            user_id

        )


    @bot.callback_query_handler(
        func=lambda call:
        call.data ==
        "stop_profile"
    )
    def stop(call):

        if call.from_user.id in viewing_users:

            del viewing_users[
                call.from_user.id
            ]

        bot.answer_callback_query(

            call.id,

            "Stopped"

        )

        bot.send_message(

            call.message.chat.id,

            "Profile Viewing Band Kar Di Gayi."

      )
