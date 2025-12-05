"""
Voice Routes - ElevenLabs voice management
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.elevenlabs import get_elevenlabs
from app.models import VoiceModel, UserModel

voices_bp = Blueprint('voices', __name__, url_prefix='/api/voices')


@voices_bp.route('/configured', methods=['GET'])
@jwt_required()
def list_configured_voices():
    """List configured voices available in the system (voices with generated audio)"""
    user_id = get_jwt_identity()
    user = UserModel.find_by_id(user_id)

    voices = VoiceModel.get_all(active_only=True)

    # For free users, only show default voice
    if not user or user.get('plan') != 'premium':
        voices = [v for v in voices if v.get('is_default')]

    return jsonify({
        'voices': voices,
        'default_voice_id': VoiceModel.get_default_voice_id()
    })


@voices_bp.route('', methods=['GET'])
@jwt_required()
def list_voices():
    """List all available voices from ElevenLabs"""
    try:
        elevenlabs = get_elevenlabs()

        if not elevenlabs.is_configured():
            return jsonify({'error': 'ElevenLabs not configured'}), 503

        voices = elevenlabs.get_voices()

        # Group by category
        grouped = {
            'premade': [],
            'cloned': [],
            'generated': [],
            'other': []
        }

        for voice in voices:
            category = voice.get('category', 'other')
            if category in grouped:
                grouped[category].append(voice)
            else:
                grouped['other'].append(voice)

        return jsonify({
            'voices': voices,
            'grouped': grouped,
            'total': len(voices)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@voices_bp.route('/recommended', methods=['GET'])
@jwt_required()
def recommended_voices():
    """Get recommended voices for hypnosis/meditation"""
    try:
        elevenlabs = get_elevenlabs()

        if not elevenlabs.is_configured():
            return jsonify({'error': 'ElevenLabs not configured'}), 503

        all_voices = elevenlabs.get_voices()

        # Find recommended voices by name
        recommended = {
            'male': [],
            'female': []
        }

        recommended_names = {
            'male': ['Daniel', 'Marcus', 'Antoni', 'Adam', 'Arnold'],
            'female': ['Charlotte', 'Aria', 'Sarah', 'Rachel', 'Domi']
        }

        for voice in all_voices:
            name = voice['name']
            for gender, names in recommended_names.items():
                if name in names:
                    recommended[gender].append(voice)

        return jsonify(recommended)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@voices_bp.route('/user-info', methods=['GET'])
@jwt_required()
def user_info():
    """Get ElevenLabs user subscription info"""
    try:
        elevenlabs = get_elevenlabs()

        if not elevenlabs.is_configured():
            return jsonify({'error': 'ElevenLabs not configured'}), 503

        info = elevenlabs.get_user_info()
        return jsonify(info)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@voices_bp.route('/preview/<voice_id>', methods=['GET'])
@jwt_required()
def preview_voice(voice_id):
    """Get preview URL for a voice"""
    try:
        elevenlabs = get_elevenlabs()

        if not elevenlabs.is_configured():
            return jsonify({'error': 'ElevenLabs not configured'}), 503

        voices = elevenlabs.get_voices()
        voice = next((v for v in voices if v['voice_id'] == voice_id), None)

        if not voice:
            return jsonify({'error': 'Voice not found'}), 404

        return jsonify({
            'voice_id': voice_id,
            'name': voice['name'],
            'preview_url': voice.get('preview_url')
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
