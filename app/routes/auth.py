"""
Authentication Routes
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity
)
from marshmallow import Schema, fields, validate, ValidationError

from app.models import UserModel

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


class RegisterSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=6))


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True)


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    schema = RegisterSchema()

    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({'error': 'Validation error', 'details': err.messages}), 400

    # Check if user already exists
    existing = UserModel.find_by_email(data['email'])
    if existing:
        return jsonify({'error': 'Email already registered'}), 409

    # Create user
    user = UserModel.create(data['email'], data['password'])

    # Generate tokens
    access_token = create_access_token(identity=user['id'])
    refresh_token = create_refresh_token(identity=user['id'])

    return jsonify({
        'user': user,
        'access_token': access_token,
        'refresh_token': refresh_token
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    schema = LoginSchema()

    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({'error': 'Validation error', 'details': err.messages}), 400

    # Verify credentials
    user = UserModel.verify_password(data['email'], data['password'])
    if not user:
        return jsonify({'error': 'Invalid email or password'}), 401

    # Generate tokens
    access_token = create_access_token(identity=user['id'])
    refresh_token = create_refresh_token(identity=user['id'])

    return jsonify({
        'user': user,
        'access_token': access_token,
        'refresh_token': refresh_token
    })


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    user_id = get_jwt_identity()
    access_token = create_access_token(identity=user_id)

    return jsonify({'access_token': access_token})


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    """Get current user"""
    user_id = get_jwt_identity()
    user = UserModel.find_by_id(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify(user)
