"""
Affirmation Models
"""

from datetime import datetime
from typing import Optional, List
from bson import ObjectId

from app.services.database import get_db
from app.services.storage import get_storage


class CategoryModel:
    """Category model for affirmation categories"""

    collection_name = 'categories'

    @classmethod
    def collection(cls):
        return get_db()[cls.collection_name]

    @classmethod
    def get_all(cls) -> List[dict]:
        """Get all categories"""
        categories = cls.collection().find().sort('order', 1)
        return [cls._serialize(c) for c in categories]

    @classmethod
    def find_by_id(cls, category_id: str) -> Optional[dict]:
        """Find category by ID"""
        try:
            category = cls.collection().find_one({'_id': ObjectId(category_id)})
            return cls._serialize(category) if category else None
        except Exception:
            return None

    @classmethod
    def seed_defaults(cls):
        """Seed default categories if not exist"""
        existing = cls.collection().count_documents({})
        if existing > 0:
            return

        default_categories = [
            {'name': 'Financeiro', 'order': 0, 'is_system': True},
            {'name': 'Saúde', 'order': 1, 'is_system': True},
            {'name': 'Sono', 'order': 2, 'is_system': True},
            {'name': 'Autoestima', 'order': 3, 'is_system': True},
            {'name': 'Produtividade', 'order': 4, 'is_system': True},
        ]

        cls.collection().insert_many(default_categories)

    @classmethod
    def _serialize(cls, category: dict) -> dict:
        if not category:
            return None
        return {
            'id': str(category['_id']),
            'name': category['name'],
            'order': category.get('order', 0),
            'is_system': category.get('is_system', True)
        }


class AffirmationModel:
    """System affirmation model (default affirmations)"""

    collection_name = 'affirmations'

    @classmethod
    def collection(cls):
        return get_db()[cls.collection_name]

    @classmethod
    def get_all(cls, voice_id: str = None) -> List[dict]:
        """Get all system affirmations, optionally with audio for specific voice"""
        affirmations = cls.collection().find().sort([('category_id', 1), ('order', 1)])
        return [cls._serialize(a, voice_id) for a in affirmations]

    @classmethod
    def get_by_category(cls, category_id: str, voice_id: str = None) -> List[dict]:
        """Get affirmations by category"""
        affirmations = cls.collection().find(
            {'category_id': ObjectId(category_id)}
        ).sort('order', 1)
        return [cls._serialize(a, voice_id) for a in affirmations]

    @classmethod
    def find_by_id(cls, affirmation_id: str, voice_id: str = None) -> Optional[dict]:
        """Find affirmation by ID"""
        try:
            affirmation = cls.collection().find_one({'_id': ObjectId(affirmation_id)})
            return cls._serialize(affirmation, voice_id) if affirmation else None
        except Exception:
            return None

    @classmethod
    def get_audio_for_voice(cls, affirmation_id: str, voice_id: str) -> Optional[dict]:
        """Get audio data for a specific voice"""
        try:
            affirmation = cls.collection().find_one({'_id': ObjectId(affirmation_id)})
            if not affirmation:
                return None
            audio_map = affirmation.get('audio', {})
            return audio_map.get(voice_id)
        except Exception:
            return None

    @classmethod
    def set_audio_for_voice(cls, affirmation_id: str, voice_id: str,
                            path: str, url: str, duration_ms: int = None) -> bool:
        """Set audio for a specific voice on an affirmation"""
        try:
            audio_data = {
                'path': path,
                'url': url,
                'generated_at': datetime.utcnow()
            }
            if duration_ms:
                audio_data['duration_ms'] = duration_ms

            result = cls.collection().update_one(
                {'_id': ObjectId(affirmation_id)},
                {'$set': {f'audio.{voice_id}': audio_data}}
            )
            return result.modified_count > 0
        except Exception:
            return False

    @classmethod
    def has_audio_for_voice(cls, affirmation_id: str, voice_id: str) -> bool:
        """Check if affirmation has audio for a specific voice"""
        audio = cls.get_audio_for_voice(affirmation_id, voice_id)
        return audio is not None and audio.get('path') is not None

    @classmethod
    def seed_defaults(cls, categories: List[dict]):
        """Seed default affirmations if not exist"""
        existing = cls.collection().count_documents({})
        if existing > 0:
            return

        # Import affirmations data
        from app.data.affirmations import AFFIRMATIONS

        category_map = {c['name']: c['id'] for c in categories}

        for category_name, texts in AFFIRMATIONS.items():
            category_id = category_map.get(category_name)
            if not category_id:
                continue

            affirmations = [
                {
                    'category_id': ObjectId(category_id),
                    'text': text,
                    'order': idx,
                    'audio': {},  # Multi-voice audio map
                    'default_audio_url': None  # Deprecated, kept for backward compat
                }
                for idx, text in enumerate(texts)
            ]

            if affirmations:
                cls.collection().insert_many(affirmations)

    @classmethod
    def _serialize(cls, affirmation: dict, voice_id: str = None) -> dict:
        if not affirmation:
            return None

        # Get audio for requested voice (or None)
        audio_map = affirmation.get('audio', {})
        voice_audio = audio_map.get(voice_id) if voice_id else None

        # Determine audio URL: prefer voice-specific, fallback to legacy default_audio_url
        if voice_audio and voice_audio.get('url'):
            audio_url = voice_audio['url']
            audio_duration_ms = voice_audio.get('duration_ms')
        else:
            audio_url = affirmation.get('default_audio_url')
            audio_duration_ms = None

        return {
            'id': str(affirmation['_id']),
            'category_id': str(affirmation['category_id']),
            'text': affirmation['text'],
            'order': affirmation.get('order', 0),
            'audio_url': audio_url,
            'audio_duration_ms': audio_duration_ms,
            'audio': audio_map,  # Full audio map for reference
            # Deprecated fields (backward compat)
            'default_audio_url': affirmation.get('default_audio_url')
        }


class UserAffirmationModel:
    """User-specific affirmation settings and custom affirmations"""

    collection_name = 'user_affirmations'

    AUDIO_SOURCE_SYSTEM = 'system'
    AUDIO_SOURCE_ELEVENLABS = 'elevenlabs'
    AUDIO_SOURCE_RECORDED = 'recorded'

    @classmethod
    def collection(cls):
        return get_db()[cls.collection_name]

    @classmethod
    def get_user_affirmations(cls, user_id: str, voice_id: str = None) -> List[dict]:
        """Get all affirmations for a user (merged with system defaults)

        Args:
            user_id: User's MongoDB ID
            voice_id: ElevenLabs voice ID for system audio. If None, uses legacy default_audio_url
        """
        # Get user's customizations
        user_affs = list(cls.collection().find({'user_id': ObjectId(user_id)}))
        user_aff_map = {str(ua.get('affirmation_id')): ua for ua in user_affs if ua.get('affirmation_id')}

        # Get system affirmations with voice-specific audio
        system_affs = AffirmationModel.get_all(voice_id=voice_id)

        result = []
        for sys_aff in system_affs:
            user_aff = user_aff_map.get(sys_aff['id'])

            if user_aff:
                # Merge user customization with system affirmation
                # Priority: user's custom audio > system voice audio > legacy default
                user_audio_url = cls._get_audio_url(user_aff)
                if user_audio_url:
                    audio_url = user_audio_url
                    audio_source = user_aff.get('audio_source', cls.AUDIO_SOURCE_SYSTEM)
                    audio_duration_ms = user_aff.get('audio_duration_ms')
                else:
                    audio_url = sys_aff.get('audio_url')
                    audio_source = cls.AUDIO_SOURCE_SYSTEM
                    audio_duration_ms = sys_aff.get('audio_duration_ms')

                result.append({
                    'id': sys_aff['id'],
                    'user_affirmation_id': str(user_aff['_id']),
                    'category_id': sys_aff['category_id'],
                    'text': sys_aff['text'],
                    'enabled': user_aff.get('enabled', True),
                    'order': user_aff.get('order', sys_aff['order']),
                    'audio_url': audio_url,
                    'audio_source': audio_source,
                    'audio_duration_ms': audio_duration_ms,
                    'is_custom': False
                })
            else:
                # System affirmation without user customization
                result.append({
                    'id': sys_aff['id'],
                    'user_affirmation_id': None,
                    'category_id': sys_aff['category_id'],
                    'text': sys_aff['text'],
                    'enabled': True,
                    'order': sys_aff['order'],
                    'audio_url': sys_aff.get('audio_url'),
                    'audio_source': cls.AUDIO_SOURCE_SYSTEM,
                    'audio_duration_ms': sys_aff.get('audio_duration_ms'),
                    'is_custom': False
                })

        # Add custom affirmations (premium feature)
        custom_affs = [ua for ua in user_affs if not ua.get('affirmation_id')]
        for custom in custom_affs:
            result.append({
                'id': str(custom['_id']),
                'user_affirmation_id': str(custom['_id']),
                'category_id': str(custom.get('category_id')),
                'text': custom.get('custom_text', ''),
                'enabled': custom.get('enabled', True),
                'order': custom.get('order', 999),
                'audio_url': cls._get_audio_url(custom),
                'audio_source': custom.get('audio_source', cls.AUDIO_SOURCE_SYSTEM),
                'audio_duration_ms': custom.get('audio_duration_ms'),
                'is_custom': True
            })

        return sorted(result, key=lambda x: (x['category_id'], x['order']))

    @classmethod
    def update_affirmation(cls, user_id: str, affirmation_id: str, **kwargs) -> dict:
        """Update user's affirmation settings"""
        allowed_fields = ['enabled', 'order', 'audio_path', 'audio_source', 'audio_duration_ms']
        update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not update_data:
            return None

        update_data['updated_at'] = datetime.utcnow()

        # Upsert user affirmation
        result = cls.collection().find_one_and_update(
            {
                'user_id': ObjectId(user_id),
                'affirmation_id': ObjectId(affirmation_id)
            },
            {
                '$set': update_data,
                '$setOnInsert': {
                    'user_id': ObjectId(user_id),
                    'affirmation_id': ObjectId(affirmation_id),
                    'created_at': datetime.utcnow()
                }
            },
            upsert=True,
            return_document=True
        )

        return cls._serialize(result)

    @classmethod
    def create_custom(cls, user_id: str, category_id: str, text: str, order: int = 999) -> dict:
        """Create a custom affirmation (premium feature)"""
        custom = {
            'user_id': ObjectId(user_id),
            'affirmation_id': None,  # null indicates custom
            'category_id': ObjectId(category_id),
            'custom_text': text,
            'enabled': True,
            'order': order,
            'audio_path': None,
            'audio_source': cls.AUDIO_SOURCE_SYSTEM,
            'audio_duration_ms': None,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        result = cls.collection().insert_one(custom)
        custom['_id'] = result.inserted_id

        return cls._serialize(custom)

    @classmethod
    def delete_custom(cls, user_id: str, user_affirmation_id: str) -> bool:
        """Delete a custom affirmation"""
        # First get the affirmation to delete audio if exists
        user_aff = cls.collection().find_one({
            '_id': ObjectId(user_affirmation_id),
            'user_id': ObjectId(user_id),
            'affirmation_id': None  # Only custom affirmations
        })

        if not user_aff:
            return False

        # Delete audio file if exists
        if user_aff.get('audio_path'):
            get_storage().delete_audio(user_aff['audio_path'])

        result = cls.collection().delete_one({'_id': ObjectId(user_affirmation_id)})
        return result.deleted_count > 0

    @classmethod
    def set_audio(cls, user_id: str, affirmation_id: str, audio_path: str,
                  audio_source: str, audio_duration_ms: int) -> dict:
        """Set audio for an affirmation"""
        return cls.update_affirmation(
            user_id, affirmation_id,
            audio_path=audio_path,
            audio_source=audio_source,
            audio_duration_ms=audio_duration_ms
        )

    @classmethod
    def remove_audio(cls, user_id: str, affirmation_id: str) -> bool:
        """Remove audio from an affirmation"""
        # Get current audio path
        user_aff = cls.collection().find_one({
            'user_id': ObjectId(user_id),
            'affirmation_id': ObjectId(affirmation_id)
        })

        if user_aff and user_aff.get('audio_path'):
            # Delete audio file
            get_storage().delete_audio(user_aff['audio_path'])

        # Update document
        cls.collection().update_one(
            {
                'user_id': ObjectId(user_id),
                'affirmation_id': ObjectId(affirmation_id)
            },
            {
                '$set': {
                    'audio_path': None,
                    'audio_source': cls.AUDIO_SOURCE_SYSTEM,
                    'audio_duration_ms': None,
                    'updated_at': datetime.utcnow()
                }
            }
        )

        return True

    @classmethod
    def _get_audio_url(cls, user_aff: dict) -> Optional[str]:
        """Get audio URL from user affirmation"""
        audio_path = user_aff.get('audio_path')
        if audio_path:
            return get_storage().get_audio_url(audio_path)
        return None

    @classmethod
    def _serialize(cls, user_aff: dict) -> dict:
        if not user_aff:
            return None
        return {
            'id': str(user_aff['_id']),
            'user_id': str(user_aff['user_id']),
            'affirmation_id': str(user_aff['affirmation_id']) if user_aff.get('affirmation_id') else None,
            'category_id': str(user_aff['category_id']) if user_aff.get('category_id') else None,
            'custom_text': user_aff.get('custom_text'),
            'enabled': user_aff.get('enabled', True),
            'order': user_aff.get('order', 0),
            'audio_path': user_aff.get('audio_path'),
            'audio_source': user_aff.get('audio_source'),
            'audio_duration_ms': user_aff.get('audio_duration_ms')
        }
