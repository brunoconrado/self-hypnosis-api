"""
Hypnos API Application Factory
"""

import os
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from config import config


def create_app(config_name=None):
    """Application factory"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    JWTManager(app)

    # Initialize services
    from app.services.database import DatabaseService
    from app.services.storage import StorageService

    DatabaseService.init_app(app)
    StorageService.init_app(app)

    # Register blueprints
    from app.routes import (
        auth_bp, config_bp, affirmations_bp, audio_bp,
        categories_bp, voices_bp, generate_bp
    )

    app.register_blueprint(auth_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(affirmations_bp)
    app.register_blueprint(audio_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(voices_bp)
    app.register_blueprint(generate_bp)

    # Seed default data
    with app.app_context():
        seed_defaults()

    # Health check endpoint
    @app.route('/api/health')
    def health():
        return {'status': 'ok'}

    return app


def seed_defaults():
    """Seed default categories and affirmations"""
    from app.models import CategoryModel, AffirmationModel

    # Seed categories first
    CategoryModel.seed_defaults()

    # Get categories for affirmation seeding
    categories = CategoryModel.get_all()

    # Seed affirmations
    AffirmationModel.seed_defaults(categories)
