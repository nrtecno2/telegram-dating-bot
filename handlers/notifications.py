from telebot import types

import database


# ==========================
# SHOW NOTIFICATIONS
# ==========================

def show_notifications(

    bot,

    message

):

    user_id = (
        message.from_user.id
    )

    notifications = (
        database.get_notifications(
            user_id
        )
    )

    if len(
        notifications
    ) == 0:

        bot.send_message(

            message.chat.id,

            "Koi Notification Nahi Hai."

        )

        return

    for item in notifications:

        notification_id = item[0]

        notification_type = item[2]

        data = item[3]

        sender = int(
            data
        )

        sender_user = (
            database.get_user(
                sender
            )
        )

        if sender_user:

            sender_name = (
                sender_user[1]
            )

        else:

            sender_name = (
                "Unknown"
            )

        if notification_type == "like":

            text = (

                f"{sender_name} liked you ❤️"

            )

        elif notification_type == "text":

            text = (

                f"{sender_name} texted you 💬"

            )

        else:

            text = (

                "New Notification"

            )

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

            message.chat.id,

            text,

            reply_markup=markup

        )


# ==========================
# REGISTER
# ==========================

def register_notification_handler(

    bot

):


    @bot.message_handler(

        func=lambda message:

        message.text
        ==
        "🔔 Notifications"

    )

    def notification_button(

        message

    ):

        show_notifications(

            bot,

            message

      )
