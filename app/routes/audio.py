"""
Audio Routes
"""

import os
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename

from app.models import UserModel, UserAffirmationModel
from app.services.storage import get_storage, LocalStorageBackend

audio_bp = Blueprint('audio', __name__, url_prefix='/api/audio')

ALLOWED_EXTENSIONS = {'webm', 'mp3', 'mp4', 'm4a', 'wav', 'ogg'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@audio_bp.route('/upload/<affirmation_id>', methods=['POST'])
@jwt_required()
def upload_audio(affirmation_id):
    """Upload audio for an affirmation"""
    user_id = get_jwt_identity()

    # Check premium status for recording
    if not UserModel.is_premium(user_id):
        return jsonify({'error': 'Premium subscription required for audio recording'}), 403

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    # Check file size
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)

    if size > MAX_FILE_SIZE:
        return jsonify({'error': 'File too large (max 10MB)'}), 400

    # Get content type
    content_type = file.content_type or 'audio/webm'

    # Get duration from request (calculated on frontend)
    duration_ms = request.form.get('duration_ms', type=int)

    # Remove old audio if exists
    UserAffirmationModel.remove_audio(user_id, affirmation_id)

    # Save new audio
    storage = get_storage()
    audio_path = storage.save_audio(file, file.filename, content_type)

    # Update affirmation with audio
    result = UserAffirmationModel.set_audio(
        user_id,
        affirmation_id,
        audio_path=audio_path,
        audio_source=UserAffirmationModel.AUDIO_SOURCE_RECORDED,
        audio_duration_ms=duration_ms
    )

    return jsonify({
        'success': True,
        'audio_url': storage.get_audio_url(audio_path),
        'audio_duration_ms': duration_ms
    })


@audio_bp.route('/<affirmation_id>', methods=['DELETE'])
@jwt_required()
def delete_audio(affirmation_id):
    """Delete audio from an affirmation"""
    user_id = get_jwt_identity()

    success = UserAffirmationModel.remove_audio(user_id, affirmation_id)

    return jsonify({'success': success})


@audio_bp.route('/file/<path:file_path>', methods=['GET'])
def serve_audio(file_path):
    """Serve audio file with caching (for local storage only)"""
    storage = get_storage()

    # Only serve local files
    if not isinstance(storage.backend, LocalStorageBackend):
        return jsonify({'error': 'Direct file access not available'}), 404

    full_path = storage.backend.get_full_path(file_path)

    if not full_path.exists():
        return jsonify({'error': 'File not found'}), 404

    # Determine mimetype from extension
    ext = full_path.suffix.lower()
    mimetypes = {
        '.mp3': 'audio/mpeg',
        '.webm': 'audio/webm',
        '.m4a': 'audio/mp4',
        '.wav': 'audio/wav',
        '.ogg': 'audio/ogg',
    }
    mimetype = mimetypes.get(ext, 'audio/mpeg')

    # Send file with caching headers (cache for 1 year)
    response = send_file(
        full_path,
        mimetype=mimetype,
        as_attachment=False
    )

    # Cache for 1 year (31536000 seconds) - audio files are immutable
    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'

    return response
