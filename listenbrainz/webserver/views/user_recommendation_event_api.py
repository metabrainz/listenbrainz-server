from flask import Blueprint, jsonify, request

user_recommendation_event_bp = Blueprint('user_recommendation_event_bp', __name__)


@user_recommendation_event_bp.route('/create')
def create_user_recommendation_event():
    pass
