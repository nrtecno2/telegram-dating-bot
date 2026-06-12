"""
Utils package for DEMON Dating Bot
Contains utility functions
"""

from .location import (
    calculate_distance,
    get_nearby_profiles,
    get_location_based_matches,
    format_distance,
    is_within_radius
)

from .force_join import (
    check_channel_membership,
    get_join_button,
    get_force_join_message,
    get_verification_success_message,
    get_verification_failed_message
)

from .storage import (
    upload_media_to_channel,
    get_media_from_channel,
    delete_media_from_channel,
    extract_message_id_from_link
)

from .states import (
    AWAITING_NAME,
    AWAITING_GENDER,
    AWAITING_AGE,
    AWAITING_LOCATION,
    AWAITING_LOCATION_COORDS,
    AWAITING_LOCATION_TEXT,
    AWAITING_ABOUT,
    AWAITING_MEDIA,
    AWAITING_CONFIRM,
    AWAITING_PREFERENCE,
    AWAITING_CHAT_MESSAGE,
    VIEWING_PROFILES,
    get_state,
    set_state,
    clear_state,
    get_temp_data,
    set_temp_data,
    clear_temp_data
)

__all__ = [
    # Location
    'calculate_distance',
    'get_nearby_profiles',
    'get_location_based_matches',
    'format_distance',
    'is_within_radius',
    
    # Force Join
    'check_channel_membership',
    'get_join_button',
    'get_force_join_message',
    'get_verification_success_message',
    'get_verification_failed_message',
    
    # Storage
    'upload_media_to_channel',
    'get_media_from_channel',
    'delete_media_from_channel',
    'extract_message_id_from_link',
    
    # States
    'AWAITING_NAME',
    'AWAITING_GENDER',
    'AWAITING_AGE',
    'AWAITING_LOCATION',
    'AWAITING_LOCATION_COORDS',
    'AWAITING_LOCATION_TEXT',
    'AWAITING_ABOUT',
    'AWAITING_MEDIA',
    'AWAITING_CONFIRM',
    'AWAITING_PREFERENCE',
    'AWAITING_CHAT_MESSAGE',
    'VIEWING_PROFILES',
    'get_state',
    'set_state',
    'clear_state',
    'get_temp_data',
    'set_temp_data',
    'clear_temp_data',
]
