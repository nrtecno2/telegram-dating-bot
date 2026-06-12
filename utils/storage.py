import os

import database


STORAGE_CHANNEL_ID = int(
    os.environ.get(
        "STORAGE_CHANNEL_ID"
    )
)


def save_photo(

    bot,

    message

):

    user_id = (
        message.from_user.id
    )

    file_id = (
        message.photo[-1].file_id
    )

    bot.forward_message(

        STORAGE_CHANNEL_ID,

        message.chat.id,

        message.message_id

    )

    database.add_media(

        user_id,

        file_id,

        "photo"

    )



def save_video(

    bot,

    message

):

    user_id = (
        message.from_user.id
    )

    file_id = (
        message.video.file_id
    )

    bot.forward_message(

        STORAGE_CHANNEL_ID,

        message.chat.id,

        message.message_id

    )

    database.add_media(

        user_id,

        file_id,

        "video"

    )



def media_count(

    user_id

):

    media = database.get_media(
        user_id
    )

    return len(
        media
    )
