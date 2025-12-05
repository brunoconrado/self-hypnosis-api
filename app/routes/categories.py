"""
Categories Routes
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from app.models import CategoryModel

categories_bp = Blueprint('categories', __name__, url_prefix='/api/categories')


@categories_bp.route('', methods=['GET'])
@jwt_required()
def get_categories():
    """Get all categories"""
    categories = CategoryModel.get_all()
    return jsonify(categories)
