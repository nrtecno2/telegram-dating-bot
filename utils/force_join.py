import os

CHANNEL_USERNAME = os.environ.get(
    "CHANNEL_USERNAME"
)


def check_force_join(bot, user_id):

    try:

        member = bot.get_chat_member(
            CHANNEL_USERNAME,
            user_id
        )

        if member.status in [
            "member",
            "administrator",
            "creator"
        ]:
            return True

    except:
        pass

    return False
