"""
Categories Routes
"""

from flask import Blueprint, jsonify

from app.models import CategoryModel

categories_bp = Blueprint('categories', __name__, url_prefix='/api/categories')


@categories_bp.route('', methods=['GET'])
def get_categories():
    """Get all categories (public endpoint)"""
    categories = CategoryModel.get_all()
    return jsonify(categories)
