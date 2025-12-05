"""
Database Service - MongoDB connection and operations
"""

from pymongo import MongoClient
from pymongo.database import Database
from typing import Optional


class DatabaseService:
    """MongoDB database service"""

    _client: Optional[MongoClient] = None
    _db: Optional[Database] = None

    @classmethod
    def init_app(cls, app):
        """Initialize MongoDB connection with Flask app config"""
        uri = app.config.get('MONGODB_URI', 'mongodb://localhost:27017')
        db_name = app.config.get('MONGODB_DATABASE', 'hypnos')

        cls._client = MongoClient(uri)
        cls._db = cls._client[db_name]

        # Create indexes
        cls._create_indexes()

    @classmethod
    def _create_indexes(cls):
        """Create database indexes for performance"""
        # Users collection
        cls._db.users.create_index('email', unique=True)

        # User configs collection
        cls._db.user_configs.create_index('user_id', unique=True)

        # User affirmations collection
        cls._db.user_affirmations.create_index([('user_id', 1), ('affirmation_id', 1)])
        cls._db.user_affirmations.create_index([('user_id', 1), ('category_id', 1)])

        # Affirmations (system)
        cls._db.affirmations.create_index('category_id')

    @classmethod
    def get_db(cls) -> Database:
        """Get database instance"""
        if cls._db is None:
            raise RuntimeError("Database not initialized. Call init_app first.")
        return cls._db

    @classmethod
    def close(cls):
        """Close database connection"""
        if cls._client:
            cls._client.close()


def get_db() -> Database:
    """Convenience function to get database"""
    return DatabaseService.get_db()
