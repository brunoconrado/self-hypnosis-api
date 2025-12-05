"""
User Model
"""

from datetime import datetime
from typing import Optional
from bson import ObjectId
import bcrypt

from app.services.database import get_db


class UserModel:
    """User model for authentication and profile"""

    PLAN_FREE = 'free'
    PLAN_PREMIUM = 'premium'

    collection_name = 'users'

    @classmethod
    def collection(cls):
        return get_db()[cls.collection_name]

    @classmethod
    def create(cls, email: str, password: str) -> dict:
        """Create a new user"""
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        user = {
            'email': email.lower().strip(),
            'password_hash': password_hash,
            'plan': cls.PLAN_FREE,
            'elevenlabs_voice_id': None,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        result = cls.collection().insert_one(user)
        user['_id'] = result.inserted_id

        return cls._serialize(user)

    @classmethod
    def find_by_email(cls, email: str) -> Optional[dict]:
        """Find user by email"""
        user = cls.collection().find_one({'email': email.lower().strip()})
        return cls._serialize(user) if user else None

    @classmethod
    def find_by_id(cls, user_id: str) -> Optional[dict]:
        """Find user by ID"""
        try:
            user = cls.collection().find_one({'_id': ObjectId(user_id)})
            return cls._serialize(user) if user else None
        except Exception:
            return None

    @classmethod
    def verify_password(cls, email: str, password: str) -> Optional[dict]:
        """Verify user password and return user if valid"""
        user = cls.collection().find_one({'email': email.lower().strip()})

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
            return cls._serialize(user)

        return None

    @classmethod
    def update(cls, user_id: str, **kwargs) -> Optional[dict]:
        """Update user fields"""
        allowed_fields = ['plan', 'elevenlabs_voice_id']
        update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not update_data:
            return None

        update_data['updated_at'] = datetime.utcnow()

        result = cls.collection().find_one_and_update(
            {'_id': ObjectId(user_id)},
            {'$set': update_data},
            return_document=True
        )

        return cls._serialize(result) if result else None

    @classmethod
    def is_premium(cls, user_id: str) -> bool:
        """Check if user has premium plan"""
        user = cls.find_by_id(user_id)
        return user and user.get('plan') == cls.PLAN_PREMIUM

    @classmethod
    def _serialize(cls, user: dict) -> dict:
        """Serialize user document (remove sensitive data)"""
        if not user:
            return None

        return {
            'id': str(user['_id']),
            'email': user['email'],
            'plan': user.get('plan', cls.PLAN_FREE),
            'elevenlabs_voice_id': user.get('elevenlabs_voice_id'),
            'created_at': user.get('created_at'),
            'updated_at': user.get('updated_at')
        }
