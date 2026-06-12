from datetime import datetime
from database import get_db

db = get_db()

class LikeModel:
    """Model for handling like operations between users"""
    
    COLLECTION = "likes"
    
    @classmethod
    def get_collection(cls):
        return db.get_collection(cls.COLLECTION)
    
    @classmethod
    def create_like(cls, from_user_id: int, to_user_id: int, from_name: str, to_name: str) -> dict:
        """Create a new like record"""
        collection = cls.get_collection()
        
        # Check if already exists
        existing = collection.find_one({
            "from_user": from_user_id,
            "to_user": to_user_id
        })
        
        if existing:
            return existing
        
        like_data = {
            "from_user": from_user_id,
            "to_user": to_user_id,
            "from_name": from_name,
            "to_name": to_name,
            "is_mutual": False,
            "is_read": False,
            "created_at": datetime.utcnow()
        }
        
        result = collection.insert_one(like_data)
        like_data["_id"] = result.inserted_id
        
        # Check for mutual like
        cls.check_mutual_like(from_user_id, to_user_id)
        
        return like_data
    
    @classmethod
    def check_mutual_like(cls, user1_id: int, user2_id: int) -> bool:
        """Check if two users have liked each other"""
        collection = cls.get_collection()
        
        user1_likes_user2 = collection.find_one({
            "from_user": user1_id,
            "to_user": user2_id
        })
        
        user2_likes_user1 = collection.find_one({
            "from_user": user2_id,
            "to_user": user1_id
        })
        
        if user1_likes_user2 and user2_likes_user1:
            # Update both as mutual
            collection.update_many(
                {"$or": [
                    {"from_user": user1_id, "to_user": user2_id},
                    {"from_user": user2_id, "to_user": user1_id}
                ]},
                {"$set": {"is_mutual": True}}
            )
            return True
        
        return False
    
    @classmethod
    def get_user_likes(cls, user_id: int, include_mutual_only: bool = False) -> list:
        """Get all likes received by a user"""
        collection = cls.get_collection()
        
        query = {"to_user": user_id}
        if include_mutual_only:
            query["is_mutual"] = True
        
        return list(collection.find(query).sort("created_at", -1))
    
    @classmethod
    def get_likes_given(cls, user_id: int) -> list:
        """Get all likes given by a user"""
        collection = cls.get_collection()
        return list(collection.find({"from_user": user_id}).sort("created_at", -1))
    
    @classmethod
    def get_mutual_matches(cls, user_id: int) -> list:
        """Get all mutual matches for a user"""
        collection = cls.get_collection()
        return list(collection.find({
            "$or": [
                {"from_user": user_id, "is_mutual": True},
                {"to_user": user_id, "is_mutual": True}
            ]
        }).sort("created_at", -1))
    
    @classmethod
    def unlike(cls, from_user_id: int, to_user_id: int) -> bool:
        """Remove a like"""
        collection = cls.get_collection()
        result = collection.delete_one({
            "from_user": from_user_id,
            "to_user": to_user_id
        })
        return result.deleted_count > 0
    
    @classmethod
    def has_liked(cls, from_user_id: int, to_user_id: int) -> bool:
        """Check if a user has liked another user"""
        collection = cls.get_collection()
        return collection.find_one({
            "from_user": from_user_id,
            "to_user": to_user_id
        }) is not None
    
    @classmethod
    def get_like_count(cls, user_id: int, received: bool = True) -> int:
        """Get like count for a user"""
        collection = cls.get_collection()
        if received:
            return collection.count_documents({"to_user": user_id})
        else:
            return collection.count_documents({"from_user": user_id})
    
    @classmethod
    def get_mutual_count(cls, user_id: int) -> int:
        """Get mutual matches count for a user"""
        collection = cls.get_collection()
        return collection.count_documents({
            "$or": [
                {"from_user": user_id, "is_mutual": True},
                {"to_user": user_id, "is_mutual": True}
            ]
        })
    
    @classmethod
    def mark_as_read(cls, user_id: int) -> int:
        """Mark all likes as read for a user"""
        collection = cls.get_collection()
        result = collection.update_many(
            {"to_user": user_id, "is_read": False},
            {"$set": {"is_read": True}}
        )
        return result.modified_count
    
    @classmethod
    def get_unread_count(cls, user_id: int) -> int:
        """Get count of unread likes for a user"""
        collection = cls.get_collection()
        return collection.count_documents({"to_user": user_id, "is_read": False})
    
    @classmethod
    def delete_user_likes(cls, user_id: int) -> dict:
        """Delete all likes associated with a user (for account deletion)"""
        collection = cls.get_collection()
        result_from = collection.delete_many({"from_user": user_id})
        result_to = collection.delete_many({"to_user": user_id})
        return {
            "deleted_from": result_from.deleted_count,
            "deleted_to": result_to.deleted_count,
            "total": result_from.deleted_count + result_to.deleted_count
        }
    
    @classmethod
    def get_liked_by_users(cls, user_id: int, limit: int = 50) -> list:
        """Get list of users who liked this user"""
        collection = cls.get_collection()
        likes = collection.find({"to_user": user_id}).limit(limit)
        
        user_ids = [like["from_user"] for like in likes]
        
        # Get full profile data
        from models.user import UserModel
        profiles = []
        for uid in user_ids:
            profile = UserModel.get_profile(uid)
            if profile:
                profiles.append(profile)
        
        return profiles
    
    @classmethod
    def get_mutual_partners(cls, user_id: int) -> list:
        """Get list of mutual match user IDs"""
        collection = cls.get_collection()
        
        mutuals = collection.find({
            "$or": [
                {"from_user": user_id, "is_mutual": True},
                {"to_user": user_id, "is_mutual": True}
            ]
        })
        
        partners = []
        for mutual in mutuals:
            if mutual["from_user"] == user_id:
                partners.append(mutual["to_user"])
            else:
                partners.append(mutual["from_user"])
        
        return list(set(partners))
