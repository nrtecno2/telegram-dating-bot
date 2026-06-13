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
            logger.info(f"✅ MongoDB connected: {self.db_name}")
            self._create_indexes()
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise
    
    def _create_indexes(self):
        try:
            self.db.users.create_index("user_id", unique=True)
            self.db.profiles.create_index("user_id", unique=True)
            self.db.likes.create_index([("from_user", 1), ("to_user", 1)], unique=True)
            self.db.notifications.create_index("user_id")
            self.db.messages.create_index([("from_user", 1), ("to_user", 1)])
            logger.info("✅ Indexes created")
        except Exception as e:
            logger.warning(f"Index warning: {e}")
    
    def get_collection(self, name):
        # YAHAN FIX KIYA - "is None" use karo, "not" mat use karo
        if self.db is None:
            self._connect()
        return self.db[name]

_db_instance = None

def get_db():
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
