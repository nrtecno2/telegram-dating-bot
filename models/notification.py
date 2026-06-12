from datetime import datetime
from typing import List, Dict, Optional
from database import get_db

db = get_db()

class NotificationModel:
    """Model for handling user notifications (likes, messages, matches)"""
    
    COLLECTION = "notifications"
    
    NOTIFICATION_TYPES = {
        "like": "❤️",
        "message": "💬",
        "mutual_match": "🎉",
        "view": "👁️",
        "system": "📢"
    }
    
    @classmethod
    def get_collection(cls):
        return db.get_collection(cls.COLLECTION)
    
    @classmethod
    def create_notification(cls, user_id: int, notif_type: str, from_user_id: int = None, 
                           from_name: str = None, message: str = None, data: dict = None) -> dict:
        """Create a new notification"""
        collection = cls.get_collection()
        
        icon = cls.NOTIFICATION_TYPES.get(notif_type, "🔔")
        
        if not message:
            if notif_type == "like":
                message = f"{icon} {from_name} liked your profile!"
            elif notif_type == "message":
                message = f"{icon} {from_name} sent you a message!"
            elif notif_type == "mutual_match":
                message = f"{icon} It's a match! You and {from_name} liked each other!"
            else:
                message = f"{icon} You have a new notification"
        
        notification_data = {
            "user_id": user_id,
            "type": notif_type,
            "from_user_id": from_user_id,
            "from_name": from_name,
            "message": message,
            "data": data or {},
            "is_read": False,
            "created_at": datetime.utcnow()
        }
        
        result = collection.insert_one(notification_data)
        notification_data["_id"] = result.inserted_id
        
        return notification_data
    
    @classmethod
    def get_user_notifications(cls, user_id: int, unread_only: bool = False, limit: int = 50) -> List[Dict]:
        """Get notifications for a user"""
        collection = cls.get_collection()
        
        query = {"user_id": user_id}
        if unread_only:
            query["is_read"] = False
        
        return list(collection.find(query).sort("created_at", -1).limit(limit))
    
    @classmethod
    def get_unread_count(cls, user_id: int) -> int:
        """Get count of unread notifications for a user"""
        collection = cls.get_collection()
        return collection.count_documents({"user_id": user_id, "is_read": False})
    
    @classmethod
    def mark_as_read(cls, notification_id: str) -> bool:
        """Mark a single notification as read"""
        collection = cls.get_collection()
        from bson import ObjectId
        result = collection.update_one(
            {"_id": ObjectId(notification_id)},
            {"$set": {"is_read": True}}
        )
        return result.modified_count > 0
    
    @classmethod
    def mark_all_as_read(cls, user_id: int) -> int:
        """Mark all notifications as read for a user"""
        collection = cls.get_collection()
        result = collection.update_many(
            {"user_id": user_id, "is_read": False},
            {"$set": {"is_read": True}}
        )
        return result.modified_count
    
    @classmethod
    def delete_notification(cls, notification_id: str) -> bool:
        """Delete a notification"""
        collection = cls.get_collection()
        from bson import ObjectId
        result = collection.delete_one({"_id": ObjectId(notification_id)})
        return result.deleted_count > 0
    
    @classmethod
    def delete_user_notifications(cls, user_id: int) -> int:
        """Delete all notifications for a user (for account deletion)"""
        collection = cls.get_collection()
        result = collection.delete_many({"user_id": user_id})
        return result.deleted_count
    
    @classmethod
    def get_notification_by_type(cls, user_id: int, notif_type: str, limit: int = 20) -> List[Dict]:
        """Get notifications of specific type for a user"""
        collection = cls.get_collection()
        return list(collection.find({
            "user_id": user_id,
            "type": notif_type
        }).sort("created_at", -1).limit(limit))
    
    @classmethod
    def has_unread_likes(cls, user_id: int) -> bool:
        """Check if user has unread like notifications"""
        collection = cls.get_collection()
        count = collection.count_documents({
            "user_id": user_id,
            "type": "like",
            "is_read": False
        })
        return count > 0
    
    @classmethod
    def has_unread_messages(cls, user_id: int) -> bool:
        """Check if user has unread message notifications"""
        collection = cls.get_collection()
        count = collection.count_documents({
            "user_id": user_id,
            "type": "message",
            "is_read": False
        })
        return count > 0
    
    @classmethod
    def get_recent_notifications(cls, user_id: int, hours: int = 24) -> List[Dict]:
        """Get notifications from last X hours"""
        collection = cls.get_collection()
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        return list(collection.find({
            "user_id": user_id,
            "created_at": {"$gte": cutoff}
        }).sort("created_at", -1))
    
    @classmethod
    def cleanup_old_notifications(cls, days: int = 30) -> int:
        """Delete notifications older than X days"""
        collection = cls.get_collection()
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        result = collection.delete_many({"created_at": {"$lt": cutoff}})
        return result.deleted_count
    
    @classmethod
    def format_notification_text(cls, notification: Dict) -> str:
        """Format notification for display in Telegram"""
        icon = cls.NOTIFICATION_TYPES.get(notification.get("type"), "🔔")
        message = notification.get("message", "New notification")
        
        text = f"{icon} {message}\n"
        text += f"🕐 {notification['created_at'].strftime('%d/%m/%Y %H:%M')}"
        
        if not notification.get("is_read"):
            text = "🆕 " + text
        
        return text
    
    @classmethod
    def create_like_notification(cls, to_user_id: int, from_user_id: int, from_name: str) -> dict:
        """Create a like notification"""
        return cls.create_notification(
            user_id=to_user_id,
            notif_type="like",
            from_user_id=from_user_id,
            from_name=from_name,
            message=f"❤️ {from_name} liked your profile!"
        )
    
    @classmethod
    def create_message_notification(cls, to_user_id: int, from_user_id: int, 
                                   from_name: str, message_preview: str) -> dict:
        """Create a message notification"""
        return cls.create_notification(
            user_id=to_user_id,
            notif_type="message",
            from_user_id=from_user_id,
            from_name=from_name,
            message=f"💬 {from_name} sent: \"{message_preview[:50]}\""
        )
    
    @classmethod
    def create_match_notification(cls, user_id: int, matched_user_id: int, matched_user_name: str) -> dict:
        """Create a mutual match notification"""
        return cls.create_notification(
            user_id=user_id,
            notif_type="mutual_match",
            from_user_id=matched_user_id,
            from_name=matched_user_name,
            message=f"🎉 It's a match! You and {matched_user_name} liked each other!"
        )
    
    @classmethod
    def create_system_notification(cls, user_id: int, message: str, data: dict = None) -> dict:
        """Create a system notification"""
        return cls.create_notification(
            user_id=user_id,
            notif_type="system",
            from_user_id=None,
            from_name="System",
            message=message,
            data=data
        )


class NotificationManager:
    """Helper class for managing notifications with user context"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
    
    def get_all(self, unread_only: bool = False) -> List[Dict]:
        """Get all notifications for the user"""
        return NotificationModel.get_user_notifications(self.user_id, unread_only)
    
    def get_unread_count(self) -> int:
        """Get unread notification count"""
        return NotificationModel.get_unread_count(self.user_id)
    
    def mark_all_read(self) -> int:
        """Mark all notifications as read"""
        return NotificationModel.mark_all_as_read(self.user_id)
    
    def has_notifications(self) -> bool:
        """Check if user has any notifications"""
        return self.get_unread_count() > 0
    
    def get_display_text(self) -> str:
        """Get formatted display text for all notifications"""
        notifications = self.get_all(unread_only=True)
        
        if not notifications:
            return "🔔 **No new notifications**\n\nYou're all caught up!"
        
        text = f"🔔 **{len(notifications)} New Notification(s)**\n\n"
        
        for notif in notifications[:20]:  # Limit to 20
            text += NotificationModel.format_notification_text(notif)
            text += "\n\n"
            text += "─" * 30 + "\n\n"
        
        if len(notifications) > 20:
            text += f"\nAnd {len(notifications) - 20} more notifications..."
        
        return text
    
    def get_notifications_with_actions(self) -> List[Dict]:
        """Get notifications with action buttons data"""
        notifications = self.get_all(unread_only=True)
        result = []
        
        for notif in notifications:
            action = None
            
            if notif.get("type") in ["like", "mutual_match"]:
                action = {
                    "type": "view_profile",
                    "user_id": notif.get("from_user_id"),
                    "button_text": "👤 View Profile"
                }
            elif notif.get("type") == "message":
                action = {
                    "type": "reply",
                    "user_id": notif.get("from_user_id"),
                    "button_text": "💬 Reply"
                }
            
            result.append({
                "notification": notif,
                "action": action,
                "text": NotificationModel.format_notification_text(notif)
            })
        
        return result
