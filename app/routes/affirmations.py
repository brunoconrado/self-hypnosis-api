"""
Affirmations Routes
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import Schema, fields, validate, ValidationError

from app.models import UserModel, UserAffirmationModel, AffirmationModel, CategoryModel

affirmations_bp = Blueprint('affirmations', __name__, url_prefix='/api/affirmations')


class AffirmationUpdateSchema(Schema):
    enabled = fields.Bool()
    order = fields.Int(validate=validate.Range(min=0))


class CustomAffirmationSchema(Schema):
    category_id = fields.Str(required=True)
    text = fields.Str(required=True, validate=validate.Length(min=1, max=500))
    order = fields.Int(validate=validate.Range(min=0))


@affirmations_bp.route('/default', methods=['GET'])
def get_default_affirmations():
    """Get default system affirmations (public, no auth required)"""
    affirmations = AffirmationModel.get_all()
    return jsonify([{
        'id': a['id'],
        'category_id': a['category_id'],
        'text': a['text'],
        'order': a['order'],
        'enabled': True,
        'audio_url': a.get('default_audio_url'),
        'is_custom': False
    } for a in affirmations])


@affirmations_bp.route('', methods=['GET'])
@jwt_required()
def get_affirmations():
    """Get all affirmations for user (merged with defaults)"""
    user_id = get_jwt_identity()
    affirmations = UserAffirmationModel.get_user_affirmations(user_id)
    return jsonify(affirmations)


@affirmations_bp.route('/<affirmation_id>', methods=['PUT'])
@jwt_required()
def update_affirmation(affirmation_id):
    """Update affirmation settings (enable/disable, reorder)"""
    user_id = get_jwt_identity()
    schema = AffirmationUpdateSchema()

    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({'error': 'Validation error', 'details': err.messages}), 400

    result = UserAffirmationModel.update_affirmation(user_id, affirmation_id, **data)

    if not result:
        return jsonify({'error': 'No valid fields to update'}), 400

    return jsonify(result)


@affirmations_bp.route('', methods=['POST'])
@jwt_required()
def create_custom_affirmation():
    """Create a custom affirmation (premium only)"""
    user_id = get_jwt_identity()

    # Check premium status
    if not UserModel.is_premium(user_id):
        return jsonify({'error': 'Premium subscription required'}), 403

    schema = CustomAffirmationSchema()

    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({'error': 'Validation error', 'details': err.messages}), 400

    result = UserAffirmationModel.create_custom(
        user_id,
        data['category_id'],
        data['text'],
        data.get('order', 999)
    )

    return jsonify(result), 201


@affirmations_bp.route('/<user_affirmation_id>', methods=['DELETE'])
@jwt_required()
def delete_custom_affirmation(user_affirmation_id):
    """Delete a custom affirmation (premium only)"""
    user_id = get_jwt_identity()

    # Check premium status
    if not UserModel.is_premium(user_id):
        return jsonify({'error': 'Premium subscription required'}), 403

    success = UserAffirmationModel.delete_custom(user_id, user_affirmation_id)

    if not success:
        return jsonify({'error': 'Affirmation not found or not a custom affirmation'}), 404

    return jsonify({'success': True})


@affirmations_bp.route('/batch', methods=['PUT'])
@jwt_required()
def batch_update_affirmations():
    """Batch update multiple affirmations (for reordering)"""
    user_id = get_jwt_identity()

    updates = request.json
    if not isinstance(updates, list):
        return jsonify({'error': 'Expected array of updates'}), 400

    results = []
    for update in updates:
        affirmation_id = update.get('id')
        if not affirmation_id:
            continue

        data = {}
        if 'enabled' in update:
            data['enabled'] = update['enabled']
        if 'order' in update:
            data['order'] = update['order']

        if data:
            result = UserAffirmationModel.update_affirmation(user_id, affirmation_id, **data)
            if result:
                results.append(result)

    return jsonify({'updated': len(results)})
