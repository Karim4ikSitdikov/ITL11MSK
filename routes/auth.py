from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import Database
from datetime import datetime

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user with preferences"""
    data = request.get_json()
    
    # Validate input
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400
    
    email = data['email'].lower().strip()
    password = data['password']
    full_name = data.get('full_name', '').strip() or None
    preferences = data.get('preferences', {})
    
    # Check if user already exists
    existing_user = Database.execute_query(
        "SELECT id FROM users WHERE email = %s",
        (email,)
    )
    
    if existing_user:
        return jsonify({'error': 'User with this email already exists'}), 409
    
    # Hash password
    password_hash = generate_password_hash(password)
    
    # Create user
    user_result = Database.execute_query(
        """
        INSERT INTO users (email, password_hash, full_name, created_at, last_login)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, email, full_name
        """,
        (email, password_hash, full_name, datetime.now(), datetime.now()),
        commit=True
    )
    
    if not user_result:
        return jsonify({'error': 'Failed to create user'}), 500
    
    user = user_result[0]
    user_id = user['id']
    
    # Create user preferences if provided
    if preferences:
        Database.execute_query(
            """
            INSERT INTO user_preferences (
                user_id, budget, preferred_prize_type, 
                preferred_prize_size, min_acceptable_probability,
                max_waiting_time, risk_profile, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                preferences.get('budget'),
                preferences.get('preferred_prize_type'),
                preferences.get('preferred_prize_size'),
                preferences.get('min_acceptable_probability'),
                preferences.get('max_waiting_time'),
                preferences.get('risk_profile', 'moderate'),
                datetime.now(),
                datetime.now()
            ),
            commit=True
        )
    
    # Create user stats entry
    Database.execute_query(
        """
        INSERT INTO user_stats (user_id, created_at, updated_at)
        VALUES (%s, %s, %s)
        """,
        (user_id, datetime.now(), datetime.now()),
        commit=True
    )
    
    # Generate access token
    access_token = create_access_token(identity=user_id)
    
    return jsonify({
        'message': 'User registered successfully',
        'user': {
            'id': user_id,
            'email': email,
            'full_name': user.get('full_name')
        },
        'access_token': access_token
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400
    
    email = data['email'].lower().strip()
    password = data['password']
    
    # Find user
    user_result = Database.execute_query(
        "SELECT id, email, password_hash FROM users WHERE email = %s",
        (email,)
    )
    
    if not user_result:
        return jsonify({'error': 'Invalid email or password'}), 401
    
    user = user_result[0]
    
    # Check password
    if not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    # Update last login
    Database.execute_query(
        "UPDATE users SET last_login = %s WHERE id = %s",
        (datetime.now(), user['id']),
        commit=True
    )
    
    # Generate access token
    access_token = create_access_token(identity=user['id'])
    
    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user['id'],
            'email': user['email']
        },
        'access_token': access_token
    }), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user information"""
    user_id = get_jwt_identity()
    
    # Get user data
    user = Database.execute_query(
        "SELECT id, email, full_name, created_at FROM users WHERE id = %s",
        (user_id,)
    )
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user_data = dict(user[0])
    
    return jsonify({
        'id': user_data['id'],
        'email': user_data['email'],
        'full_name': user_data.get('full_name'),
        'created_at': user_data['created_at'].isoformat() if user_data.get('created_at') else None
    }), 200   
    return jsonify(response), 200
