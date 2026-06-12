from enum import Enum, auto


class UserState(Enum):
    """
    Main user flow states for the bot
    """

    # Initial
    START = auto()
    IDLE = auto()

    # Registration flow
    REGISTER_NAME = auto()
    REGISTER_AGE = auto()
    REGISTER_GENDER = auto()
    REGISTER_BIO = auto()
    REGISTER_LOCATION = auto()
    REGISTER_PHOTOS = auto()

    # Profile
    PROFILE_VIEW = auto()
    PROFILE_EDIT = auto()

    # Discovery / Matching
    BROWSING = auto()
    LIKING = auto()
    PASSING = auto()

    # Chat system
    CHAT_ACTIVE = auto()
    CHAT_TYPING = auto()

    # Media handling
    UPLOADING_MEDIA = auto()

    # Notifications
    NOTIFICATION_VIEW = auto()

    # Settings
    SETTINGS = auto()

    # Safety / system
    FORCE_JOIN = auto()
    BLOCKED = auto()


class ChatState(Enum):
    """
    Chat-specific states between two users
    """

    NONE = auto()
    ACTIVE = auto()
    TYPING = auto()
    ENDED = auto()
    BLOCKED = auto()
