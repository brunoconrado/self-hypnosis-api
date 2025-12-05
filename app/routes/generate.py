"""
Audio Generation Routes - Generate affirmation audio with ElevenLabs
"""

import io
from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models import UserModel, AffirmationModel, UserAffirmationModel
from app.services.elevenlabs import get_elevenlabs
from app.services.storage import get_storage

generate_bp = Blueprint('generate', __name__, url_prefix='/api/generate')


@generate_bp.route('/affirmation/<affirmation_id>', methods=['POST'])
@jwt_required()
def generate_affirmation_audio(affirmation_id):
    """Generate audio for a single affirmation using ElevenLabs"""
    user_id = get_jwt_identity()

    # Check premium status
    if not UserModel.is_premium(user_id):
        return jsonify({'error': 'Premium subscription required'}), 403

    # Get voice_id from request
    data = request.json or {}
    voice_id = data.get('voice_id')

    if not voice_id:
        return jsonify({'error': 'voice_id is required'}), 400

    try:
        elevenlabs = get_elevenlabs()

        if not elevenlabs.is_configured():
            return jsonify({'error': 'ElevenLabs not configured'}), 503

        # Get affirmation text
        affirmation = AffirmationModel.find_by_id(affirmation_id)
        if not affirmation:
            return jsonify({'error': 'Affirmation not found'}), 404

        # Generate audio
        audio_bytes = elevenlabs.generate_audio(
            text=affirmation['text'],
            voice_id=voice_id
        )

        # Save to storage
        storage = get_storage()
        audio_file = io.BytesIO(audio_bytes)
        audio_path = storage.save_audio(audio_file, 'affirmation.mp3', 'audio/mpeg')

        # Get duration (approximate: ~150 words per minute for calm speech)
        word_count = len(affirmation['text'].split())
        duration_ms = int((word_count / 150) * 60 * 1000)

        # Update user affirmation
        UserAffirmationModel.set_audio(
            user_id,
            affirmation_id,
            audio_path=audio_path,
            audio_source=UserAffirmationModel.AUDIO_SOURCE_ELEVENLABS,
            audio_duration_ms=duration_ms
        )

        return jsonify({
            'success': True,
            'audio_url': storage.get_audio_url(audio_path),
            'audio_duration_ms': duration_ms
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@generate_bp.route('/preview', methods=['POST'])
@jwt_required()
def preview_generation():
    """Preview text-to-speech without saving (for testing voices)"""
    data = request.json or {}
    text = data.get('text', 'Eu me amo e me aceito completamente.')
    voice_id = data.get('voice_id')

    if not voice_id:
        return jsonify({'error': 'voice_id is required'}), 400

    try:
        elevenlabs = get_elevenlabs()

        if not elevenlabs.is_configured():
            return jsonify({'error': 'ElevenLabs not configured'}), 503

        # Generate audio
        audio_bytes = elevenlabs.generate_audio(
            text=text,
            voice_id=voice_id
        )

        # Return as audio stream
        return Response(
            audio_bytes,
            mimetype='audio/mpeg',
            headers={'Content-Disposition': 'inline; filename=preview.mp3'}
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@generate_bp.route('/batch', methods=['POST'])
@jwt_required()
def batch_generate():
    """Generate audio for multiple affirmations (queued)"""
    user_id = get_jwt_identity()

    # Check premium status
    if not UserModel.is_premium(user_id):
        return jsonify({'error': 'Premium subscription required'}), 403

    data = request.json or {}
    affirmation_ids = data.get('affirmation_ids', [])
    voice_id = data.get('voice_id')

    if not voice_id:
        return jsonify({'error': 'voice_id is required'}), 400

    if not affirmation_ids:
        return jsonify({'error': 'affirmation_ids is required'}), 400

    try:
        elevenlabs = get_elevenlabs()

        if not elevenlabs.is_configured():
            return jsonify({'error': 'ElevenLabs not configured'}), 503

        # Check remaining characters
        user_info = elevenlabs.get_user_info()
        remaining = user_info.get('remaining_characters', 0)

        # Estimate character usage
        total_chars = 0
        affirmations = []
        for aff_id in affirmation_ids:
            aff = AffirmationModel.find_by_id(aff_id)
            if aff:
                total_chars += len(aff['text'])
                affirmations.append(aff)

        if total_chars > remaining:
            return jsonify({
                'error': 'Not enough characters remaining',
                'required': total_chars,
                'remaining': remaining
            }), 400

        # Generate audio for each affirmation
        storage = get_storage()
        results = []
        errors = []

        for aff in affirmations:
            try:
                audio_bytes = elevenlabs.generate_audio(
                    text=aff['text'],
                    voice_id=voice_id
                )

                audio_file = io.BytesIO(audio_bytes)
                audio_path = storage.save_audio(audio_file, 'affirmation.mp3', 'audio/mpeg')

                word_count = len(aff['text'].split())
                duration_ms = int((word_count / 150) * 60 * 1000)

                UserAffirmationModel.set_audio(
                    user_id,
                    aff['id'],
                    audio_path=audio_path,
                    audio_source=UserAffirmationModel.AUDIO_SOURCE_ELEVENLABS,
                    audio_duration_ms=duration_ms
                )

                results.append({
                    'affirmation_id': aff['id'],
                    'success': True,
                    'audio_url': storage.get_audio_url(audio_path)
                })

            except Exception as e:
                errors.append({
                    'affirmation_id': aff['id'],
                    'error': str(e)
                })

        return jsonify({
            'success': len(results),
            'failed': len(errors),
            'results': results,
            'errors': errors
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@generate_bp.route('/estimate', methods=['POST'])
@jwt_required()
def estimate_usage():
    """Estimate character usage for generating affirmations"""
    data = request.json or {}
    affirmation_ids = data.get('affirmation_ids', [])

    if not affirmation_ids:
        # Estimate for all affirmations
        affirmations = AffirmationModel.get_all()
    else:
        affirmations = [AffirmationModel.find_by_id(aid) for aid in affirmation_ids]
        affirmations = [a for a in affirmations if a]

    total_chars = sum(len(a['text']) for a in affirmations)

    try:
        elevenlabs = get_elevenlabs()
        if elevenlabs.is_configured():
            user_info = elevenlabs.get_user_info()
            remaining = user_info.get('remaining_characters', 0)
        else:
            remaining = None
    except:
        remaining = None

    return jsonify({
        'affirmation_count': len(affirmations),
        'total_characters': total_chars,
        'remaining_characters': remaining,
        'can_generate': remaining is not None and remaining >= total_chars
    })
