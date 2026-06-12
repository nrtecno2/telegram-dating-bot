from telebot import types

import database


# ==========================
# CHAT MEMORY
# ==========================

chat_users = {}


# ==========================
# OPEN CHAT
# ==========================

def open_chat(

    bot,

    from_user,

    to_user

):

    chat_users[
        from_user
    ] = to_user

    bot.send_message(

        from_user,

        "Ab aap message bhej sakte hain."

    )


# ==========================
# CLOSE CHAT
# ==========================

def close_chat(

    user_id

):

    if user_id in chat_users:

        del chat_users[
            user_id
        ]


# ==========================
# REGISTER
# ==========================

def register_chat_handler(

    bot

):


    @bot.message_handler(

        func=lambda message:

        message.from_user.id
        in
        chat_users

    )

    def chat(message):

        sender = (
            message.from_user.id
        )

        receiver = (
            chat_users[
                sender
            ]
        )

        sender_user = (
            database.get_user(
                sender
            )
        )

        sender_name = (
            sender_user[1]
        )

        text = (
            message.text
        )


        database.add_notification(

            receiver,

            "text",

            str(
                sender
            )

        )


        try:

            markup = (
                types.InlineKeyboardMarkup()
            )

            markup.add(

                types.InlineKeyboardButton(

                    "View User",

                    callback_data=
                    f"view_{sender}"

                )

            )

            bot.send_message(

                receiver,

                f"{sender_name} texted you.\n\n{text}",

                reply_markup=markup

            )

        except:

            pass


# ==========================
# SEND FIRST MESSAGE
# ==========================

def send_first_message(

    bot,

    from_user,

    to_user

):

    open_chat(

        bot,

        from_user,

        to_user

  )
