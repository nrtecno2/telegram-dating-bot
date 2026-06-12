"""
Handlers package for DEMON Dating Bot
Contains all callback and message handlers
"""

from .start import (
    handle_start,
    handle_verify_callback,
    handle_continue_bot,
    handle_create_profile,
    show_main_menu
)

from .profile import (
    handle_name,
    handle_gender_callback,
    handle_age,
    handle_location,
    handle_location_text,
    handle_about,
    handle_media,
    confirm_profile,
    handle_confirm_callback,
    handle_preference_callback,
    handle_edit_profile
)

from .view_profiles import (
    handle_view_profiles,
    handle_like_callback,
    handle_skip_callback,
    handle_stop_callback,
    handle_my_profile
)

from .notifications import (
    handle_notifications,
    send_like_notification,
    send_message_notification,
    get_unread_count
)

from .chat import (
    handle_chat_callback,
    handle_chat_message,
    handle_cancel_chat,
    get_conversation
)

__all__ = [
    # Start handlers
    'handle_start',
    'handle_verify_callback',
    'handle_continue_bot',
    'handle_create_profile',
    'show_main_menu',
    
    # Profile handlers
    'handle_name',
    'handle_gender_callback',
    'handle_age',
    'handle_location',
    'handle_location_text',
    'handle_about',
    'handle_media',
    'confirm_profile',
    'handle_confirm_callback',
    'handle_preference_callback',
    'handle_edit_profile',
    
    # View profiles handlers
    'handle_view_profiles',
    'handle_like_callback',
    'handle_skip_callback',
    'handle_stop_callback',
    'handle_my_profile',
    
    # Notifications
    'handle_notifications',
    'send_like_notification',
    'send_message_notification',
    'get_unread_count',
    
    # Chat handlers
    'handle_chat_callback',
    'handle_chat_message',
    'handle_cancel_chat',
    'get_conversation',
]
