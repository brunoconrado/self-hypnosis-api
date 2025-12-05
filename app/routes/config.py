"""
User Config Routes
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import Schema, fields, validate, ValidationError

from app.models import ConfigModel

config_bp = Blueprint('config', __name__, url_prefix='/api/config')


class ConfigUpdateSchema(Schema):
    binaural_base_freq = fields.Int(validate=validate.Range(min=100, max=500))
    binaural_beat_freq = fields.Int(validate=validate.Range(min=1, max=30))
    binaural_volume = fields.Float(validate=validate.Range(min=0, max=1))
    voice_volume = fields.Float(validate=validate.Range(min=0, max=1))
    gap_between_sec = fields.Int(validate=validate.Range(min=0, max=10))


@config_bp.route('', methods=['GET'])
@jwt_required()
def get_config():
    """Get user configuration"""
    user_id = get_jwt_identity()
    config = ConfigModel.get_or_create(user_id)
    return jsonify(config)


@config_bp.route('', methods=['PUT'])
@jwt_required()
def update_config():
    """Update user configuration"""
    user_id = get_jwt_identity()
    schema = ConfigUpdateSchema()

    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({'error': 'Validation error', 'details': err.messages}), 400

    config = ConfigModel.update(user_id, **data)
    return jsonify(config)
