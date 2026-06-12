import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
from telegram import Bot
from database import get_db

logger = logging.getLogger(__name__)

db = get_db()

class MediaModel:
    """Model for handling user media files (photos/videos)"""
    
    COLLECTION = "media"
    
    # Private channel ID where media will be stored
    PRIVATE_CHANNEL_ID = os.getenv("PRIVATE_CHANNEL_ID", "-1001234567890")
    
    @classmethod
    def get_collection(cls):
        return db.get_collection(cls.COLLECTION)
    
    @classmethod
    async def upload_media(cls, bot: Bot, file_id: str, user_id: int, media_type: str) -> Optional[str]:
        """
        Upload media to private channel and return the message ID or file URL
        Returns: file_id or message_link for storage
        """
        try:
            # Forward or copy media to private channel
            if media_type == "photo":
                # Get the largest photo
                message = await bot.send_photo(
                    chat_id=cls.PRIVATE_CHANNEL_ID,
                    photo=file_id,
                    caption=f"📸 User: {user_id} | Time: {datetime.utcnow()}"
                )
            elif media_type == "video":
                message = await bot.send_video(
                    chat_id=cls.PRIVATE_CHANNEL_ID,
                    video=file_id,
                    caption=f"🎥 User: {user_id} | Time: {datetime.utcnow()}"
                )
            else:
                return None
            
            # Generate permanent link
            file_link = f"https://t.me/c/{str(cls.PRIVATE_CHANNEL_ID)[4:]}/{message.message_id}"
            
            # Save to database
            media_record = {
                "user_id": user_id,
                "file_id": file_id,
                "message_id": message.message_id,
                "channel_id": cls.PRIVATE_CHANNEL_ID,
                "file_link": file_link,
                "media_type": media_type,
                "created_at": datetime.utcnow()
            }
            cls.get_collection().insert_one(media_record)
            
            return file_link
            
        except Exception as e:
            logger.error(f"Media upload failed for user {user_id}: {e}")
            return None
    
    @classmethod
    def save_media_reference(cls, user_id: int, file_link: str, media_type: str, file_id: str = None) -> Dict:
        """Save media reference to database without uploading to channel"""
        media_record = {
            "user_id": user_id,
            "file_id": file_id,
            "file_link": file_link,
            "media_type": media_type,
            "created_at": datetime.utcnow()
        }
        
        result = cls.get_collection().insert_one(media_record)
        media_record["_id"] = result.inserted_id
        
        return media_record
    
    @classmethod
    def get_user_media(cls, user_id: int) -> List[Dict]:
        """Get all media files for a user"""
        collection = cls.get_collection()
        return list(collection.find({"user_id": user_id}).sort("created_at", 1))
    
    @classmethod
    def get_first_media(cls, user_id: int) -> Optional[Dict]:
        """Get first media file for a user (for profile display)"""
        collection = cls.get_collection()
        return collection.find_one({"user_id": user_id})
    
    @classmethod
    def get_media_count(cls, user_id: int) -> int:
        """Get count of media files for a user"""
        collection = cls.get_collection()
        return collection.count_documents({"user_id": user_id})
    
    @classmethod
    def delete_user_media(cls, user_id: int) -> int:
        """Delete all media references for a user"""
        collection = cls.get_collection()
        result = collection.delete_many({"user_id": user_id})
        return result.deleted_count
    
    @classmethod
    def update_media(cls, user_id: int, media_list: List[str], media_types: List[str]) -> bool:
        """Replace all media for a user (used during profile edit)"""
        # First delete existing
        cls.delete_user_media(user_id)
        
        # Add new media
        for idx, media_link in enumerate(media_list):
            media_type = media_types[idx] if idx < len(media_types) else "photo"
            cls.save_media_reference(user_id, media_link, media_type)
        
        return True
    
    @classmethod
    def get_media_links(cls, user_id: int) -> List[str]:
        """Get list of media links for a user"""
        media_files = cls.get_user_media(user_id)
        return [m.get("file_link", m.get("file_id", "")) for m in media_files]
    
    @classmethod
    def validate_media_type(cls, file_type: str) -> bool:
        """Validate if file type is allowed"""
        allowed_types = ["photo", "video", "animation", "document"]
        return file_type in allowed_types
    
    @classmethod
    def get_media_size_limit(cls, media_type: str) -> int:
        """Get size limit for media type (in bytes)"""
        limits = {
            "photo": 10 * 1024 * 1024,  # 10 MB
            "video": 50 * 1024 * 1024,   # 50 MB
            "animation": 50 * 1024 * 1024,
            "document": 50 * 1024 * 1024
        }
        return limits.get(media_type, 50 * 1024 * 1024)


class ProfileMediaManager:
    """Helper class for managing profile media specifically"""
    
    @staticmethod
    async def process_profile_media(bot: Bot, media_list: List[Dict], user_id: int) -> List[str]:
        """
        Process and upload multiple media files for a profile
        media_list: list of dicts with 'file_id' and 'type' keys
        Returns: list of uploaded URLs
        """
        uploaded_urls = []
        
        for media in media_list:
            file_id = media.get("file_id")
            media_type = media.get("type", "photo")
            
            if file_id:
                url = await MediaModel.upload_media(bot, file_id, user_id, media_type)
                if url:
                    uploaded_urls.append(url)
        
        return uploaded_urls
    
    @staticmethod
    def get_profile_display_media(user_id: int, max_count: int = 3) -> List[str]:
        """Get media for profile display (limited to max_count)"""
        media_links = MediaModel.get_media_links(user_id)
        return media_links[:max_count]
    
    @staticmethod
    def has_media(user_id: int) -> bool:
        """Check if user has uploaded any media"""
        return MediaModel.get_media_count(user_id) > 0
    
    @staticmethod
    def get_media_summary(user_id: int) -> str:
        """Get summary of user's media for display"""
        media_count = MediaModel.get_media_count(user_id)
        
        if media_count == 0:
            return "📷 No photos/videos"
        elif media_count == 1:
            return "📷 1 photo/video"
        else:
            return f"📷 {media_count} photos/videos"


class TempMediaStorage:
    """Temporary storage for media during profile creation"""
    
    def __init__(self, context):
        self.context = context
    
    def add_media(self, file_id: str, media_type: str):
        """Add media to temporary storage"""
        if "temp_media" not in self.context.user_data:
            self.context.user_data["temp_media"] = []
        
        self.context.user_data["temp_media"].append({
            "file_id": file_id,
            "type": media_type,
            "timestamp": datetime.utcnow()
        })
    
    def get_media(self) -> List[Dict]:
        """Get all temporary media"""
        return self.context.user_data.get("temp_media", [])
    
    def get_media_count(self) -> int:
        """Get count of temporary media"""
        return len(self.get_media())
    
    def clear_media(self):
        """Clear temporary media"""
        self.context.user_data["temp_media"] = []
    
    def is_max_reached(self, max_limit: int = 3) -> bool:
        """Check if max media limit reached"""
        return self.get_media_count() >= max_limit
    
    def get_remaining_slots(self, max_limit: int = 3) -> int:
        """Get remaining media slots"""
        return max_limit - self.get_media_count()
