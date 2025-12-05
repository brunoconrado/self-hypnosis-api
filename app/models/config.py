"""
User Config Model
"""

from datetime import datetime
from typing import Optional
from bson import ObjectId

from app.services.database import get_db


class ConfigModel:
    """User configuration model"""

    collection_name = 'user_configs'

    # Default values
    DEFAULTS = {
        'binaural_base_freq': 200,
        'binaural_beat_freq': 10,
        'binaural_volume': 0.5,
        'voice_volume': 0.8,
        'gap_between_sec': 2
    }

    @classmethod
    def collection(cls):
        return get_db()[cls.collection_name]

    @classmethod
    def get_or_create(cls, user_id: str) -> dict:
        """Get user config or create with defaults"""
        config = cls.collection().find_one({'user_id': ObjectId(user_id)})

        if not config:
            config = cls._create_default(user_id)

        return cls._serialize(config)

    @classmethod
    def _create_default(cls, user_id: str) -> dict:
        """Create default config for user"""
        config = {
            'user_id': ObjectId(user_id),
            **cls.DEFAULTS,
            'updated_at': datetime.utcnow()
        }

        result = cls.collection().insert_one(config)
        config['_id'] = result.inserted_id

        return config

    @classmethod
    def update(cls, user_id: str, **kwargs) -> dict:
        """Update user config"""
        allowed_fields = [
            'binaural_base_freq',
            'binaural_beat_freq',
            'binaural_volume',
            'voice_volume',
            'gap_between_sec'
        ]

        update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not update_data:
            return cls.get_or_create(user_id)

        # Validate ranges
        if 'binaural_base_freq' in update_data:
            update_data['binaural_base_freq'] = max(100, min(500, update_data['binaural_base_freq']))

        if 'binaural_beat_freq' in update_data:
            update_data['binaural_beat_freq'] = max(1, min(30, update_data['binaural_beat_freq']))

        if 'binaural_volume' in update_data:
            update_data['binaural_volume'] = max(0, min(1, update_data['binaural_volume']))

        if 'voice_volume' in update_data:
            update_data['voice_volume'] = max(0, min(1, update_data['voice_volume']))

        if 'gap_between_sec' in update_data:
            update_data['gap_between_sec'] = max(0, min(10, update_data['gap_between_sec']))

        update_data['updated_at'] = datetime.utcnow()

        result = cls.collection().find_one_and_update(
            {'user_id': ObjectId(user_id)},
            {'$set': update_data},
            upsert=True,
            return_document=True
        )

        return cls._serialize(result)

    @classmethod
    def _serialize(cls, config: dict) -> dict:
        """Serialize config document"""
        if not config:
            return None

        return {
            'id': str(config['_id']),
            'user_id': str(config['user_id']),
            'binaural_base_freq': config.get('binaural_base_freq', cls.DEFAULTS['binaural_base_freq']),
            'binaural_beat_freq': config.get('binaural_beat_freq', cls.DEFAULTS['binaural_beat_freq']),
            'binaural_volume': config.get('binaural_volume', cls.DEFAULTS['binaural_volume']),
            'voice_volume': config.get('voice_volume', cls.DEFAULTS['voice_volume']),
            'gap_between_sec': config.get('gap_between_sec', cls.DEFAULTS['gap_between_sec']),
            'updated_at': config.get('updated_at')
        }
