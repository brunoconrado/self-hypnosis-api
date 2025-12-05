"""
Voice Model - Configured voices for audio generation
"""

from datetime import datetime
from typing import Optional, List
from bson import ObjectId

from app.services.database import get_db


class VoiceModel:
    """Model for configured TTS voices"""

    collection_name = 'voices'

    @classmethod
    def collection(cls):
        return get_db()[cls.collection_name]

    @classmethod
    def get_all(cls, active_only: bool = True) -> List[dict]:
        """Get all voices"""
        query = {'is_active': True} if active_only else {}
        voices = cls.collection().find(query).sort('order', 1)
        return [cls._serialize(v) for v in voices]

    @classmethod
    def get_default(cls) -> Optional[dict]:
        """Get default voice (for free users)"""
        voice = cls.collection().find_one({'is_default': True, 'is_active': True})
        return cls._serialize(voice) if voice else None

    @classmethod
    def get_default_voice_id(cls) -> Optional[str]:
        """Get default voice ElevenLabs ID"""
        voice = cls.get_default()
        return voice['elevenlabs_id'] if voice else None

    @classmethod
    def find_by_id(cls, voice_id: str) -> Optional[dict]:
        """Find voice by MongoDB ID"""
        try:
            voice = cls.collection().find_one({'_id': ObjectId(voice_id)})
            return cls._serialize(voice) if voice else None
        except Exception:
            return None

    @classmethod
    def find_by_elevenlabs_id(cls, elevenlabs_id: str) -> Optional[dict]:
        """Find voice by ElevenLabs voice ID"""
        voice = cls.collection().find_one({'elevenlabs_id': elevenlabs_id})
        return cls._serialize(voice) if voice else None

    @classmethod
    def create(cls, elevenlabs_id: str, slug: str, name: str,
               display_name: str = None, gender: str = 'male',
               is_default: bool = False, preview_url: str = None) -> dict:
        """Create a new voice"""
        # If setting as default, unset other defaults
        if is_default:
            cls.collection().update_many({}, {'$set': {'is_default': False}})

        voice = {
            'elevenlabs_id': elevenlabs_id,
            'slug': slug,
            'name': name,
            'display_name': display_name or name,
            'gender': gender,
            'is_default': is_default,
            'is_active': True,
            'order': cls.collection().count_documents({}) + 1,
            'preview_url': preview_url,
            'created_at': datetime.utcnow()
        }

        result = cls.collection().insert_one(voice)
        voice['_id'] = result.inserted_id
        return cls._serialize(voice)

    @classmethod
    def seed_defaults(cls):
        """Seed default voices if not exist"""
        existing = cls.collection().count_documents({})
        if existing > 0:
            return

        # Primary voice: Harrison Gale
        cls.create(
            elevenlabs_id='fCxG8OHm4STbIsWe4aT9',
            slug='harrison',
            name='Harrison Gale',
            display_name='Voz Masculina Suave',
            gender='male',
            is_default=True
        )

    @classmethod
    def _serialize(cls, voice: dict) -> dict:
        if not voice:
            return None
        return {
            'id': str(voice['_id']),
            'elevenlabs_id': voice['elevenlabs_id'],
            'slug': voice['slug'],
            'name': voice['name'],
            'display_name': voice.get('display_name', voice['name']),
            'gender': voice.get('gender', 'male'),
            'is_default': voice.get('is_default', False),
            'is_active': voice.get('is_active', True),
            'order': voice.get('order', 0),
            'preview_url': voice.get('preview_url')
        }
