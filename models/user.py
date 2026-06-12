import hashlib
import secrets
from datetime import datetime
from typing import Dict, List, Optional, Any
from bson import ObjectId
from database import get_db

db = get_db()

class UserModel:
    """Model for handling user data and profiles"""
    
    USERS_COLLECTION = "users"
    PROFILES_COLLECTION = "profiles"
    SESSIONS_COLLECTION = "sessions"
    
    @classmethod
    def get_users_collection(cls):
        return db.get_collection(cls.USERS_COLLECTION)
    
    @classmethod
    def get_profiles_collection(cls):
        return db.get_collection(cls.PROFILES_COLLECTION)
    
    @classmethod
    def get_sessions_collection(cls):
        return db.get_collection(cls.SESSIONS_COLLECTION)
    
    # ========== USER MANAGEMENT ==========
    
    @classmethod
    def create_user(cls, user_id: int, username: str = None, first_name: str = None, 
                   last_name: str = None) -> Dict:
        """Create a new user entry"""
        collection = cls.get_users_collection()
        
        # Check if user exists
        existing = collection.find_one({"user_id": user_id})
        if existing:
            return existing
        
        user_data = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": f"{first_name or ''} {last_name or ''}".strip(),
            "preference": None,  # male, female, both
            "setup_complete": False,
            "is_active": True,
            "is_banned": False,
            "created_at": datetime.utcnow(),
            "last_active": datetime.utcnow(),
            "language": "hi",
            "total_likes_given": 0,
            "total_likes_received": 0,
            "total_matches": 0
        }
        
        result = collection.insert_one(user_data)
        user_data["_id"] = result.inserted_id
        
        return user_data
    
    @classmethod
    def get_user(cls, user_id: int) -> Optional[Dict]:
        """Get user by Telegram ID"""
        collection = cls.get_users_collection()
        return collection.find_one({"user_id": user_id})
    
    @classmethod
    def update_user(cls, user_id: int, update_data: Dict) -> bool:
        """Update user data"""
        collection = cls.get_users_collection()
        update_data["updated_at"] = datetime.utcnow()
        
        result = collection.update_one(
            {"user_id": user_id},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    @classmethod
    def update_last_active(cls, user_id: int) -> bool:
        """Update user's last active timestamp"""
        return cls.update_user(user_id, {"last_active": datetime.utcnow()})
    
    @classmethod
    def set_preference(cls, user_id: int, preference: str) -> bool:
        """Set user's viewing preference"""
        valid_preferences = ["male", "female", "both"]
        if preference not in valid_preferences:
            return False
        
        return cls.update_user(user_id, {"preference": preference})
    
    @classmethod
    def complete_setup(cls, user_id: int) -> bool:
        """Mark user setup as complete"""
        return cls.update_user(user_id, {"setup_complete": True})
    
    @classmethod
    def delete_user(cls, user_id: int) -> bool:
        """Soft delete user (deactivate)"""
        return cls.update_user(user_id, {"is_active": False})
    
    @classmethod
    def hard_delete_user(cls, user_id: int) -> Dict:
        """Permanently delete user and all associated data"""
        result = {
            "users": 0,
            "profiles": 0,
            "likes": 0,
            "notifications": 0,
            "messages": 0,
            "media": 0,
            "sessions": 0
        }
        
        # Delete from users collection
        users_col = cls.get_users_collection()
        user_result = users_col.delete_one({"user_id": user_id})
        result["users"] = user_result.deleted_count
        
        # Delete profile
        profiles_col = cls.get_profiles_collection()
        profile_result = profiles_col.delete_one({"user_id": user_id})
        result["profiles"] = profile_result.deleted_count
        
        # Delete likes
        likes_col = db.get_collection("likes")
        likes_from = likes_col.delete_many({"from_user": user_id})
        likes_to = likes_col.delete_many({"to_user": user_id})
        result["likes"] = likes_from.deleted_count + likes_to.deleted_count
        
        # Delete notifications
        notif_col = db.get_collection("notifications")
        notif_result = notif_col.delete_many({"user_id": user_id})
        result["notifications"] = notif_result.deleted_count
        
        # Delete messages
        msg_col = db.get_collection("messages")
        msg_from = msg_col.delete_many({"from_user": user_id})
        msg_to = msg_col.delete_many({"to_user": user_id})
        result["messages"] = msg_from.deleted_count + msg_to.deleted_count
        
        # Delete media
        media_col = db.get_collection("media")
        media_result = media_col.delete_many({"user_id": user_id})
        result["media"] = media_result.deleted_count
        
        # Delete sessions
        sessions_col = cls.get_sessions_collection()
        sessions_result = sessions_col.delete_many({"user_id": user_id})
        result["sessions"] = sessions_result.deleted_count
        
        return result
    
    # ========== PROFILE MANAGEMENT ==========
    
    @classmethod
    def create_profile(cls, user_id: int, profile_data: Dict) -> Dict:
        """Create user profile"""
        collection = cls.get_profiles_collection()
        
        # Check if profile exists
        existing = collection.find_one({"user_id": user_id})
        if existing:
            return cls.update_profile(user_id, profile_data)
        
        profile = {
            "user_id": user_id,
            "name": profile_data.get("name"),
            "gender": profile_data.get("gender"),
            "age": profile_data.get("age"),
            "location_text": profile_data.get("location_text"),
            "latitude": profile_data.get("latitude"),
            "longitude": profile_data.get("longitude"),
            "about": profile_data.get("about", ""),
            "media": profile_data.get("media", []),
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "profile_views": 0,
            "last_activity": datetime.utcnow()
        }
        
        result = collection.insert_one(profile)
        profile["_id"] = result.inserted_id
        
        return profile
    
    @classmethod
    def get_profile(cls, user_id: int) -> Optional[Dict]:
        """Get user profile"""
        collection = cls.get_profiles_collection()
        return collection.find_one({"user_id": user_id})
    
    @classmethod
    def update_profile(cls, user_id: int, update_data: Dict) -> bool:
        """Update user profile"""
        collection = cls.get_profiles_collection()
        update_data["updated_at"] = datetime.utcnow()
        
        result = collection.update_one(
            {"user_id": user_id},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    @classmethod
    def increment_profile_views(cls, user_id: int) -> bool:
        """Increment profile view count"""
        collection = cls.get_profiles_collection()
        result = collection.update_one(
            {"user_id": user_id},
            {"$inc": {"profile_views": 1}}
        )
        return result.modified_count > 0
    
    @classmethod
    def get_all_profiles(cls, filters: Dict = None, limit: int = 100) -> List[Dict]:
        """Get all profiles with optional filters"""
        collection = cls.get_profiles_collection()
        
        query = {"is_active": True}
        if filters:
            query.update(filters)
        
        return list(collection.find(query).limit(limit))
    
    @classmethod
    def search_profiles(cls, user_id: int, preference: str, latitude: float = None, 
                       longitude: float = None, max_distance_km: int = 50) -> List[Dict]:
        """Search profiles based on user preference and location"""
        collection = cls.get_profiles_collection()
        
        # Base query - exclude self and inactive
        query = {
            "user_id": {"$ne": user_id},
            "is_active": True
        }
        
        # Apply gender preference
        if preference == "male":
            query["gender"] = "male"
        elif preference == "female":
            query["gender"] = "female"
        
        # Get profiles
        profiles = list(collection.find(query))
        
        # Filter out already liked profiles
        likes_col = db.get_collection("likes")
        liked_users = likes_col.distinct("to_user", {"from_user": user_id})
        profiles = [p for p in profiles if p["user_id"] not in liked_users]
        
        # If location available, sort by distance
        if latitude and longitude:
            from utils.location import calculate_distance
            for profile in profiles:
                if profile.get("latitude") and profile.get("longitude"):
                    profile["distance"] = calculate_distance(
                        latitude, longitude,
                        profile["latitude"], profile["longitude"]
                    )
                else:
                    profile["distance"] = float("inf")
            
            # Filter by max distance and sort
            profiles = [p for p in profiles if p.get("distance", float("inf")) <= max_distance_km]
            profiles.sort(key=lambda x: x.get("distance", float("inf")))
        
        return profiles
    
    # ========== SESSION MANAGEMENT ==========
    
    @classmethod
    def create_session(cls, user_id: int) -> str:
        """Create a new session token for user"""
        collection = cls.get_sessions_collection()
        
        # Generate secure token
        token = secrets.token_urlsafe(32)
        
        session_data = {
            "user_id": user_id,
            "token": token,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow().replace(year=datetime.utcnow().year + 1),
            "is_active": True
        }
        
        collection.insert_one(session_data)
        return token
    
    @classmethod
    def validate_session(cls, token: str) -> Optional[Dict]:
        """Validate session token and return user"""
        collection = cls.get_sessions_collection()
        
        session = collection.find_one({
            "token": token,
            "is_active": True,
            "expires_at": {"$gt": datetime.utcnow()}
        })
        
        if not session:
            return None
        
        return cls.get_user(session["user_id"])
    
    @classmethod
    def invalidate_session(cls, token: str) -> bool:
        """Invalidate a session token"""
        collection = cls.get_sessions_collection()
        result = collection.update_one(
            {"token": token},
            {"$set": {"is_active": False}}
        )
        return result.modified_count > 0
    
    @classmethod
    def invalidate_all_sessions(cls, user_id: int) -> int:
        """Invalidate all sessions for a user"""
        collection = cls.get_sessions_collection()
        result = collection.update_many(
            {"user_id": user_id, "is_active": True},
            {"$set": {"is_active": False}}
        )
        return result.modified_count
    
    # ========== STATISTICS ==========
    
    @classmethod
    def update_stats(cls, user_id: int, stat_type: str) -> bool:
        """Update user statistics"""
        stat_fields = {
            "like_given": "total_likes_given",
            "like_received": "total_likes_received",
            "match": "total_matches"
        }
        
        field = stat_fields.get(stat_type)
        if not field:
            return False
        
        collection = cls.get_users_collection()
        result = collection.update_one(
            {"user_id": user_id},
            {"$inc": {field: 1}}
        )
        return result.modified_count > 0
    
    @classmethod
    def get_stats(cls, user_id: int) -> Dict:
        """Get user statistics"""
        user = cls.get_user(user_id)
        profile = cls.get_profile(user_id)
        
        if not user:
            return {}
        
        return {
            "likes_given": user.get("total_likes_given", 0),
            "likes_received": user.get("total_likes_received", 0),
            "matches": user.get("total_matches", 0),
            "profile_views": profile.get("profile_views", 0) if profile else 0,
            "member_since": user.get("created_at"),
            "last_active": user.get("last_active")
        }
    
    # ========== UTILITY ==========
    
    @classmethod
    def is_profile_complete(cls, user_id: int) -> bool:
        """Check if user profile is complete"""
        profile = cls.get_profile(user_id)
        if not profile:
            return False
        
        required_fields = ["name", "gender", "age", "location_text"]
        for field in required_fields:
            if not profile.get(field):
                return False
        
        return True
