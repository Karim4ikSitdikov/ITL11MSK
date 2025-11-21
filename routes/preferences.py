from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.db import Database
from datetime import datetime

preferences_bp = Blueprint('preferences', __name__, url_prefix='/api/preferences')


@preferences_bp.route('', methods=['GET'])
@jwt_required()
def get_preferences():
    """Get user preferences"""
    user_id = get_jwt_identity()
    
    result = Database.execute_query(
        """
        SELECT budget, preferred_prize_type, preferred_prize_size,
               min_acceptable_probability, max_waiting_time, risk_profile,
               created_at, updated_at
        FROM user_preferences
        WHERE user_id = %s
        """,
        (user_id,)
    )
    
    if not result:
        return jsonify({'preferences': None}), 200
    
    prefs = dict(result[0])
    
    return jsonify({
        'preferences': {
            'budget': float(prefs['budget']) if prefs.get('budget') else None,
            'preferred_prize_type': prefs.get('preferred_prize_type'),
            'preferred_prize_size': prefs.get('preferred_prize_size'),
            'min_acceptable_probability': float(prefs['min_acceptable_probability']) if prefs.get('min_acceptable_probability') else None,
            'max_waiting_time': prefs.get('max_waiting_time'),
            'risk_profile': prefs.get('risk_profile'),
            'created_at': prefs['created_at'].isoformat() if prefs.get('created_at') else None,
            'updated_at': prefs['updated_at'].isoformat() if prefs.get('updated_at') else None
        }
    }), 200


@preferences_bp.route('', methods=['PUT'])
@jwt_required()
def update_preferences():
    """Update user preferences"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Check if preferences exist
    existing = Database.execute_query(
        "SELECT id FROM user_preferences WHERE user_id = %s",
        (user_id,)
    )
    
    if existing:
        # Update existing preferences
        Database.execute_query(
            """
            UPDATE user_preferences
            SET budget = %s,
                preferred_prize_type = %s,
                preferred_prize_size = %s,
                min_acceptable_probability = %s,
                max_waiting_time = %s,
                risk_profile = %s,
                updated_at = %s
            WHERE user_id = %s
            """,
            (
                data.get('budget'),
                data.get('preferred_prize_type'),
                data.get('preferred_prize_size'),
                data.get('min_acceptable_probability'),
                data.get('max_waiting_time'),
                data.get('risk_profile'),
                datetime.now(),
                user_id
            ),
            commit=True
        )
    else:
        # Create new preferences
        Database.execute_query(
            """
            INSERT INTO user_preferences (
                user_id, budget, preferred_prize_type, preferred_prize_size,
                min_acceptable_probability, max_waiting_time, risk_profile,
                created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                data.get('budget'),
                data.get('preferred_prize_type'),
                data.get('preferred_prize_size'),
                data.get('min_acceptable_probability'),
                data.get('max_waiting_time'),
                data.get('risk_profile', 'moderate'),
                datetime.now(),
                datetime.now()
            ),
            commit=True
        )
    
    return jsonify({
        'message': 'Preferences updated successfully',
        'preferences': data
    }), 200


@preferences_bp.route('', methods=['DELETE'])
@jwt_required()
def delete_preferences():
    """Delete user preferences (reset to defaults)"""
    user_id = get_jwt_identity()
    
    Database.execute_query(
        "DELETE FROM user_preferences WHERE user_id = %s",
        (user_id,),
        commit=True
    )
    
    return jsonify({'message': 'Preferences deleted successfully'}), 200
