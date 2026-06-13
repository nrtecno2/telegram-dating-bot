import os
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.db_name = os.getenv("DB_NAME", "dating_bot")
        self.client = None
        self.db = None
        self._connect()
    
    def _connect(self):
        try:
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            logger.info(f"✅ MongoDB connected successfully to: {self.db_name}")
            self._create_indexes()
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise
    
    def _create_indexes(self):
        try:
            # Users collection
            self.db.users.create_index("user_id", unique=True)
            self.db.users.create_index("preference")
            self.db.users.create_index("created_at")
            
            # Profiles collection
            self.db.profiles.create_index("user_id", unique=True)
            self.db.profiles.create_index("gender")
            self.db.profiles.create_index("age")
            self.db.profiles.create_index("is_active")
            
            # Likes collection
            self.db.likes.create_index([("from_user", 1), ("to_user", 1)], unique=True)
            self.db.likes.create_index("to_user")
            self.db.likes.create_index("is_mutual")
            
            # Notifications collection
            self.db.notifications.create_index("user_id")
            self.db.notifications.create_index("is_read")
            self.db.notifications.create_index("created_at")
            
            # Messages collection
            self.db.messages.create_index([("from_user", 1), ("to_user", 1)])
            self.db.messages.create_index("to_user")
            self.db.messages.create_index("is_read")
            
            # Media collection
            self.db.media.create_index("user_id")
            
            # Sessions collection
            self.db.sessions.create_index("token", unique=True)
            self.db.sessions.create_index("user_id")
            
            logger.info("✅ All database indexes created successfully")
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")
    
    def get_collection(self, name):
        # Fixed: using 'is None' instead of 'not' for database truth value testing
        if self.db is None:
            self._connect()
        return self.db[name]
    
    def get_db(self):
        if self.db is None:
            self._connect()
        return self.db
    
    def health_check(self):
        try:
            self.client.admin.command('ping')
            return {"status": "healthy", "connected": True}
        except Exception as e:
            return {"status": "unhealthy", "connected": False, "error": str(e)}
    
    def close(self):
        if self.client:
            self.client.close()
            logger.info("🔌 MongoDB connection closed")

_db_instance = None

def get_db():
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance

def get_collection(name):
    return get_db().get_collection(name)

def close_db():
    global _db_instance
    if _db_instance:
        _db_instance.close()
        _db_instance = None
