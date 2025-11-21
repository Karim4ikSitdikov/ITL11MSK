from flask import Blueprint, request, jsonify
from llm.ollama_client import get_ollama_client

test_bp = Blueprint('test', __name__, url_prefix='/api/test')


@test_bp.route('/chat', methods=['POST'])
def test_chat():
    """Test chat endpoint without authentication - for demo purposes"""
    data = request.get_json()
    
    if not data or not data.get('message'):
        return jsonify({'error': 'Message is required'}), 400
    
    user_message = data['message'].strip()
    
    if not user_message:
        return jsonify({'error': 'Message cannot be empty'}), 400
    
    # Try to get user info if token provided
    user_name = None
    try:
        from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        
        if user_id:
            from database.db import Database
            user_result = Database.execute_query(
                "SELECT full_name FROM users WHERE id = %s",
                (user_id,)
            )
            if user_result:
                user_name = user_result[0].get('full_name')
    except:
        pass  # If no token or error, just continue without user name
    
    # Generate response using Ollama
    ollama_client = get_ollama_client()
    
    # Simple context for demo
    context_data = {
        'user_name': user_name,
        'lotteries': [
            {
                'name': 'Русское лото',
                'lottery_type': 'draw',
                'ticket_price': 100,
                'description': 'Классическая тиражная лотерея с высокими шансами на выигрыш'
            },
            {
                'name': '4 из 20',
                'lottery_type': 'instant',
                'ticket_price': 50,
                'description': 'Мгновенная лотерея с частыми выигрышами'
            },
            {
                'name': '6 из 45',
                'lottery_type': 'draw',
                'ticket_price': 150,
                'description': 'Тиражная лотерея с большими джекпотами'
            }
        ],
        'preferences': {
            'budget': 500,
            'preferred_prize_type': 'both',
            'preferred_prize_size': 'medium'
        }
    }
    
    try:
        bot_response = ollama_client.generate_response(
            user_message=user_message,
            context_data=context_data
        )
        
        return jsonify({
            'message': bot_response
        }), 200
    except Exception as e:
        print(f"Error in test chat: {e}")
        return jsonify({'error': str(e)}), 500
