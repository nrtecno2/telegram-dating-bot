import os
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, OperationFailure
from pymongo.database import Database as MongoDatabase
from pymongo.collection import Collection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    """MongoDB Database Manager for DEMON Dating Bot"""
    
    def __init__(self):
        """Initialize database connection"""
        self.mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.db_name = os.getenv("DB_NAME", "dating_bot")
        self.client: Optional[MongoClient] = None
        self.db: Optional[MongoDatabase] = None
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(
                self.mongo_uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=30000,
                retryWrites=True,
                w='majority'
            )
            
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            
            logger.info(f"✅ MongoDB connected successfully to: {self.db_name}")
            
            # Create indexes
            self._create_indexes()
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected database error: {e}")
            raise
    
    def _create_indexes(self) -> None:
        """Create all necessary database indexes for performance"""
        
        # ========== USERS COLLECTION ==========
        users_col = self.db["users"]
        users_col.create_index("user_id", unique=True)
        users_col.create_index("username")
        users_col.create_index("preference")
        users_col.create_index("is_active")
        users_col.create_index("created_at")
        users_col.create_index([("latitude", 1), ("longitude", 1)])
        logger.info("✅ Users collection indexes created")
        
        # ========== PROFILES COLLECTION ==========
        profiles_col = self.db["profiles"]
        profiles_col.create_index("user_id", unique=True)
        profiles_col.create_index("gender")
        profiles_col.create_index("age")
        profiles_col.create_index("location_text")
        profiles_col.create_index([("latitude", 1), ("longitude", 1)])
        profiles_col.create_index("is_active")
        profiles_col.create_index("created_at")
        
        # 2dsphere index for geospatial queries
        try:
            profiles_col.create_index([("location", "2dsphere")])
        except Exception as e:
            logger.warning(f"2dsphere index creation skipped: {e}")
        logger.info("✅ Profiles collection indexes created")
        
        # ========== LIKES COLLECTION ==========
        likes_col = self.db["likes"]
        likes_col.create_index([("from_user", 1), ("to_user", 1)], unique=True)
        likes_col.create_index("to_user")
        likes_col.create_index("from_user")
        likes_col.create_index("is_mutual")
        likes_col.create_index("is_read")
        likes_col.create_index("created_at")
        logger.info("✅ Likes collection indexes created")
        
        # ========== NOTIFICATIONS COLLECTION ==========
        notif_col = self.db["notifications"]
        notif_col.create_index("user_id")
        notif_col.create_index("type")
        notif_col.create_index("is_read")
        notif_col.create_index("created_at")
        notif_col.create_index([("user_id", 1), ("is_read", 1)])
        logger.info("✅ Notifications collection indexes created")
        
        # ========== MESSAGES COLLECTION ==========
        msg_col = self.db["messages"]
        msg_col.create_index([("from_user", 1), ("to_user", 1)])
        msg_col.create_index("to_user")
        msg_col.create_index("is_read")
        msg_col.create_index("created_at")
        msg_col.create_index([("conversation_id", 1)])
        logger.info("✅ Messages collection indexes created")
        
        # ========== MEDIA COLLECTION ==========
        media_col = self.db["media"]
        media_col.create_index("user_id")
        media_col.create_index("file_id")
        media_col.create_index("media_type")
        media_col.create_index("created_at")
        logger.info("✅ Media collection indexes created")
        
        # ========== SESSIONS COLLECTION ==========
        sessions_col = self.db["sessions"]
        sessions_col.create_index("token", unique=True)
        sessions_col.create_index("user_id")
        sessions_col.create_index("expires_at")
        sessions_col.create_index([("user_id", 1), ("is_active", 1)])
        logger.info("✅ Sessions collection indexes created")
        
        # ========== REPORTS COLLECTION ==========
        reports_col = self.db["reports"]
        reports_col.create_index("reported_user")
        reports_col.create_index("reporter_user")
        reports_col.create_index("status")
        reports_col.create_index("created_at")
        logger.info("✅ Reports collection indexes created")
        
        # ========== FEEDBACK COLLECTION ==========
        feedback_col = self.db["feedback"]
        feedback_col.create_index("user_id")
        feedback_col.create_index("created_at")
        logger.info("✅ Feedback collection indexes created")
        
        logger.info("✅ All database indexes created successfully")
    
    def get_collection(self, name: str) -> Collection:
        """Get a collection by name"""
        if not self.db:
            self._connect()
        return self.db[name]
    
    def get_db(self) -> MongoDatabase:
        """Get database instance"""
        if not self.db:
            self._connect()
        return self.db
    
    def health_check(self) -> Dict[str, Any]:
        """Check database health status"""
        try:
            self.client.admin.command('ping')
            stats = {
                "status": "healthy",
                "connected": True,
                "database": self.db_name,
                "collections": self.db.list_collection_names(),
                "timestamp": datetime.utcnow()
            }
            return stats
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
                "timestamp": datetime.utcnow()
            }
    
    def close(self) -> None:
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("🔌 MongoDB connection closed")
    
    def drop_collection(self, collection_name: str) -> bool:
        """Drop a collection (use with caution)"""
        try:
            self.db[collection_name].drop()
            logger.warning(f"Collection dropped: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to drop collection {collection_name}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        stats = {}
        try:
            for collection_name in self.db.list_collection_names():
                stats[collection_name] = self.db[collection_name].count_documents({})
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
        return stats
    
    def backup(self, backup_name: str = None) -> str:
        """Create a backup reference (actual backup needs external tool)"""
        if not backup_name:
            backup_name = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # This is a metadata backup reference
        backup_info = {
            "name": backup_name,
            "timestamp": datetime.utcnow(),
            "collections": self.db.list_collection_names(),
            "stats": self.get_stats()
        }
        
        backup_col = self.db["backups"]
        backup_col.insert_one(backup_info)
        
        logger.info(f"📦 Backup metadata created: {backup_name}")
        return backup_name


# ========== SINGLETON INSTANCE ==========
_db_instance: Optional[Database] = None

def get_db() -> Database:
    """Get singleton database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance

def get_collection(name: str) -> Collection:
    """Get collection from database"""
    return get_db().get_collection(name)

def close_db() -> None:
    """Close database connection"""
    global _db_instance
    if _db_instance:
        _db_instance.close()
        _db_instance = None


# ========== DECORATORS ==========
def db_operation(retry_count: int = 3):
    """Decorator for database operations with retry logic"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(retry_count):
                try:
                    return await func(*args, **kwargs)
                except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                    last_error = e
                    logger.warning(f"DB operation failed (attempt {attempt + 1}/{retry_count}): {e}")
                    if attempt < retry_count - 1:
                        import asyncio
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        raise
                except Exception as e:
                    raise
            raise last_error
        return wrapper
    return decorator
