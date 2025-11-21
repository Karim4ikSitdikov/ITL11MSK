from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from database.db import Database
from llm.ollama_client import get_ollama_client
from datetime import datetime
import json

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')


@chat_bp.route('', methods=['POST'])
@jwt_required(optional=True)
def send_message():
    """Send a message to the chatbot (authentication optional)"""
    user_id = get_jwt_identity()  # Will be None if not authenticated
    data = request.get_json()
    
    if not data or not data.get('message'):
        return jsonify({'error': 'Message is required'}), 400
    
    user_message = data['message'].strip()
    
    if not user_message:
        return jsonify({'error': 'Message cannot be empty'}), 400
    
    # Save user message to history if authenticated
    if user_id:
        Database.execute_query(
            """
            INSERT INTO chat_history (user_id, message, is_user_message, created_at)
            VALUES (%s, %s, %s, %s)
            """,
            (user_id, user_message, True, datetime.now()),
            commit=True
        )
    
    # Get user preferences if authenticated
    preferences = None
    chat_history = None
    
    if user_id:
        prefs_result = Database.execute_query(
            """
            SELECT budget, preferred_prize_type, preferred_prize_size,
                   min_acceptable_probability, max_waiting_time, risk_profile
            FROM user_preferences
            WHERE user_id = %s
            """,
            (user_id,)
        )
        if prefs_result:
            preferences = dict(prefs_result[0])
        
        # Get recent chat history for authenticated users
        chat_history = Database.execute_query(
            """
            SELECT message, is_user_message, created_at
            FROM chat_history
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 10
            """,
            (user_id,)
        )
    
    # Get active lotteries (for all users)
    lotteries = Database.execute_query(
        """
        SELECT id, name, lottery_type, ticket_price, draw_frequency, 
               description, max_prize
        FROM lotteries
        WHERE is_active = TRUE
        ORDER BY name
        LIMIT 20
        """
    )
    
    # Get recommendations if authenticated
    recommendations = None
    if user_id:
        recommendations = Database.execute_query(
            """
            SELECT r.score, r.explanation, l.name as lottery_name
            FROM recommendations r
            JOIN lotteries l ON r.lottery_id = l.id
            WHERE r.user_id = %s
            ORDER BY r.created_at DESC, r.score DESC
            LIMIT 5
            """,
            (user_id,)
        )
    
    # Build context data
    context_data = {
        'preferences': preferences or {},
        'lotteries': [dict(l) for l in lotteries] if lotteries else [],
        'recommendations': [dict(r) for r in recommendations] if recommendations else [],
        'statistics': {
            'total_active': len(lotteries) if lotteries else 0
        }
    }
    
    # Generate response using Ollama
    ollama_client = get_ollama_client()
    
    # Reverse chat history for chronological order
    history_formatted = [dict(h) for h in reversed(list(chat_history))] if chat_history else []
    
    try:
        bot_response = ollama_client.generate_response(
            user_message=user_message,
            context_data=context_data,
            chat_history=history_formatted
        )
    except Exception as e:
        print(f"Error generating response: {e}")
        return jsonify({'error': 'Ошибка при генерации ответа'}), 500
    
    # Save bot response to history if authenticated
    if user_id:
        Database.execute_query(
            """
            INSERT INTO chat_history (user_id, message, is_user_message, context_data, created_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, bot_response, False, json.dumps(context_data), datetime.now()),
            commit=True
        )
    
    return jsonify({
        'message': bot_response,
        'timestamp': datetime.now().isoformat()
    }), 200


@chat_bp.route('/history', methods=['GET'])
@jwt_required(optional=True)
def get_chat_history():
    """Get chat history for the current user (if authenticated)"""
    user_id = get_jwt_identity()
    
    if not user_id:
        # Return empty history for non-authenticated users
        return jsonify({
            'history': [],
            'total': 0,
            'limit': 50,
            'offset': 0
        }), 200
    
    # Get pagination parameters
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # Get chat history
    history = Database.execute_query(
        """
        SELECT id, message, is_user_message, created_at
        FROM chat_history
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """,
        (user_id, limit, offset)
    )
    
    # Get total count
    count_result = Database.execute_query(
        "SELECT COUNT(*) as total FROM chat_history WHERE user_id = %s",
        (user_id,)
    )
    
    total = count_result[0]['total'] if count_result else 0
    
    return jsonify({
        'history': [
            {
                'id': h['id'],
                'message': h['message'],
                'is_user_message': h['is_user_message'],
                'timestamp': h['created_at'].isoformat() if h.get('created_at') else None
            }
            for h in reversed(list(history))  # Reverse to show chronologically
        ] if history else [],
        'total': total,
        'limit': limit,
        'offset': offset
    }), 200


@chat_bp.route('/history', methods=['DELETE'])
@jwt_required()
def clear_chat_history():
    """Clear chat history for the current user"""
    user_id = get_jwt_identity()
    
    Database.execute_query(
        "DELETE FROM chat_history WHERE user_id = %s",
        (user_id,),
        commit=True
    )
    
    return jsonify({'message': 'Chat history cleared successfully'}), 200
