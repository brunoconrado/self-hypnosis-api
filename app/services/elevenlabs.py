"""
ElevenLabs Service - Text-to-Speech and Voice Cloning
"""

import os
import requests
from typing import Optional, List, BinaryIO
from flask import current_app


class ElevenLabsService:
    """Service for interacting with ElevenLabs API"""

    BASE_URL = "https://api.elevenlabs.io/v1"

    # Default voice settings for calm, hypnotic delivery
    DEFAULT_VOICE_SETTINGS = {
        "stability": 0.75,          # Higher = more consistent
        "similarity_boost": 0.75,   # Higher = more similar to original voice
        "style": 0.35,              # Lower = more neutral/calm
        "use_speaker_boost": True
    }

    # Recommended voices for hypnosis/meditation (from ElevenLabs library)
    RECOMMENDED_VOICES = {
        "male": [
            {"name": "Daniel", "description": "Calm British male, great for meditation"},
            {"name": "Marcus", "description": "Deep, soothing American male"},
            {"name": "Antoni", "description": "Warm, reassuring male voice"},
        ],
        "female": [
            {"name": "Charlotte", "description": "Calm, nurturing female voice"},
            {"name": "Aria", "description": "Soft, gentle female voice"},
            {"name": "Sarah", "description": "Warm American female"},
        ]
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('ELEVENLABS_API_KEY')

    @property
    def headers(self):
        return {
            "Accept": "application/json",
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    def is_configured(self) -> bool:
        """Check if API key is configured"""
        return bool(self.api_key)

    def get_voices(self) -> List[dict]:
        """Get all available voices"""
        if not self.is_configured():
            raise ValueError("ElevenLabs API key not configured")

        response = requests.get(
            f"{self.BASE_URL}/voices",
            headers=self.headers
        )

        if response.status_code != 200:
            raise Exception(f"Failed to get voices: {response.text}")

        data = response.json()
        voices = []

        for voice in data.get("voices", []):
            voices.append({
                "voice_id": voice["voice_id"],
                "name": voice["name"],
                "category": voice.get("category", "unknown"),
                "description": voice.get("description", ""),
                "preview_url": voice.get("preview_url"),
                "labels": voice.get("labels", {})
            })

        return voices

    def get_voice_by_name(self, name: str) -> Optional[dict]:
        """Find a voice by name"""
        voices = self.get_voices()
        for voice in voices:
            if voice["name"].lower() == name.lower():
                return voice
        return None

    def generate_audio(
        self,
        text: str,
        voice_id: str,
        model_id: str = "eleven_multilingual_v2",
        voice_settings: Optional[dict] = None
    ) -> bytes:
        """Generate audio from text using specified voice"""
        if not self.is_configured():
            raise ValueError("ElevenLabs API key not configured")

        settings = voice_settings or self.DEFAULT_VOICE_SETTINGS

        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": settings
        }

        response = requests.post(
            f"{self.BASE_URL}/text-to-speech/{voice_id}",
            json=payload,
            headers={
                "Accept": "audio/mpeg",
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            }
        )

        if response.status_code != 200:
            raise Exception(f"Failed to generate audio: {response.text}")

        return response.content

    def generate_audio_stream(
        self,
        text: str,
        voice_id: str,
        model_id: str = "eleven_multilingual_v2",
        voice_settings: Optional[dict] = None
    ):
        """Generate audio and return as stream (for large texts)"""
        if not self.is_configured():
            raise ValueError("ElevenLabs API key not configured")

        settings = voice_settings or self.DEFAULT_VOICE_SETTINGS

        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": settings
        }

        response = requests.post(
            f"{self.BASE_URL}/text-to-speech/{voice_id}/stream",
            json=payload,
            headers={
                "Accept": "audio/mpeg",
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            },
            stream=True
        )

        if response.status_code != 200:
            raise Exception(f"Failed to generate audio: {response.text}")

        return response.iter_content(chunk_size=1024)

    def get_user_info(self) -> dict:
        """Get user subscription info and remaining characters"""
        if not self.is_configured():
            raise ValueError("ElevenLabs API key not configured")

        response = requests.get(
            f"{self.BASE_URL}/user",
            headers=self.headers
        )

        if response.status_code != 200:
            raise Exception(f"Failed to get user info: {response.text}")

        data = response.json()
        subscription = data.get("subscription", {})

        return {
            "tier": subscription.get("tier", "unknown"),
            "character_count": subscription.get("character_count", 0),
            "character_limit": subscription.get("character_limit", 0),
            "remaining_characters": subscription.get("character_limit", 0) - subscription.get("character_count", 0),
            "voice_limit": subscription.get("voice_limit", 0),
            "can_use_instant_voice_cloning": subscription.get("can_use_instant_voice_cloning", False)
        }

    def clone_voice(
        self,
        name: str,
        description: str,
        files: List[BinaryIO]
    ) -> dict:
        """Clone a voice from audio samples (requires premium)"""
        if not self.is_configured():
            raise ValueError("ElevenLabs API key not configured")

        # Prepare files for upload
        files_data = [
            ("files", (f"sample_{i}.mp3", file, "audio/mpeg"))
            for i, file in enumerate(files)
        ]

        response = requests.post(
            f"{self.BASE_URL}/voices/add",
            headers={"xi-api-key": self.api_key},
            data={
                "name": name,
                "description": description
            },
            files=files_data
        )

        if response.status_code != 200:
            raise Exception(f"Failed to clone voice: {response.text}")

        return response.json()

    def delete_voice(self, voice_id: str) -> bool:
        """Delete a cloned voice"""
        if not self.is_configured():
            raise ValueError("ElevenLabs API key not configured")

        response = requests.delete(
            f"{self.BASE_URL}/voices/{voice_id}",
            headers=self.headers
        )

        return response.status_code == 200


# Singleton instance
_elevenlabs_service: Optional[ElevenLabsService] = None


def get_elevenlabs() -> ElevenLabsService:
    """Get ElevenLabs service instance"""
    global _elevenlabs_service
    if _elevenlabs_service is None:
        _elevenlabs_service = ElevenLabsService()
    return _elevenlabs_service


def init_elevenlabs(api_key: str):
    """Initialize ElevenLabs service with API key"""
    global _elevenlabs_service
    _elevenlabs_service = ElevenLabsService(api_key)
