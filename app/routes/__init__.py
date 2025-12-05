"""
API Routes
"""

from .auth import auth_bp
from .config import config_bp
from .affirmations import affirmations_bp
from .audio import audio_bp
from .categories import categories_bp
from .voices import voices_bp
from .generate import generate_bp

__all__ = [
    'auth_bp',
    'config_bp',
    'affirmations_bp',
    'audio_bp',
    'categories_bp',
    'voices_bp',
    'generate_bp'
]
