import logging
import os
from datetime import datetime
from telebot import TeleBot

logger = logging.getLogger(__name__)

# Private channel ID for media storage (must be set in environment variables)
PRIVATE_CHANNEL_ID = os.getenv("PRIVATE_CHANNEL_ID", "-1001234567890")


def upload_media_to_channel(bot: TeleBot, file_id: str, user_id: int, media_type: str) -> str:
    """
    Upload media to private channel and return the message ID or file link
    Returns: file_link for storage
    """
    try:
        caption = f"📸 User: {user_id} | Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Send media based on type
        if media_type == "photo":
            message = bot.send_photo(
                chat_id=PRIVATE_CHANNEL_ID,
                photo=file_id,
                caption=caption
            )
        elif media_type == "video":
            message = bot.send_video(
                chat_id=PRIVATE_CHANNEL_ID,
                video=file_id,
                caption=caption
            )
        else:
            logger.warning(f"Unknown media type: {media_type}")
            return None
        
        # Generate permanent link to the message
        # Format: https://t.me/c/channel_id/message_id
        channel_id_str = str(PRIVATE_CHANNEL_ID)
        if channel_id_str.startswith("-100"):
            channel_id_str = channel_id_str[4:]
        
        file_link = f"https://t.me/c/{channel_id_str}/{message.message_id}"
        
        logger.info(f"Media uploaded for user {user_id}: {file_link}")
        return file_link
        
    except Exception as e:
        logger.error(f"Failed to upload media for user {user_id}: {e}")
        return None


def get_media_from_channel(bot: TeleBot, message_id: int) -> str:
    """
    Get media file_id from private channel by message_id
    Returns file_id or None
    """
    try:
        message = bot.forward_message(
            chat_id=PRIVATE_CHANNEL_ID,
            from_chat_id=PRIVATE_CHANNEL_ID,
            message_id=message_id
        )
        
        if message.photo:
            return message.photo[-1].file_id
        elif message.video:
            return message.video.file_id
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to get media from channel: {e}")
        return None


def delete_media_from_channel(bot: TeleBot, message_id: int) -> bool:
    """
    Delete media message from private channel
    Returns True if successful
    """
    try:
        bot.delete_message(
            chat_id=PRIVATE_CHANNEL_ID,
            message_id=message_id
        )
        logger.info(f"Deleted media message {message_id} from channel")
        return True
    except Exception as e:
        logger.error(f"Failed to delete media from channel: {e}")
        return False


def extract_message_id_from_link(file_link: str) -> int:
    """
    Extract message ID from Telegram media link
    Format: https://t.me/c/channel_id/message_id
    """
    try:
        parts = file_link.split("/")
        return int(parts[-1])
    except Exception as e:
        logger.error(f"Failed to extract message ID from link: {e}")
        return None
