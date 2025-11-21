from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.db import Database

lotteries_bp = Blueprint('lotteries', __name__, url_prefix='/api/lotteries')


@lotteries_bp.route('', methods=['GET'])
def get_lotteries():
    """Get all lotteries with optional filters"""
    # Get query parameters
    lottery_type = request.args.get('type')  # instant or draw
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    
    # Build query
    query = """
        SELECT l.*, 
               COUNT(DISTINCT d.id) as total_draws,
               AVG(d.total_prize_fund) as avg_prize_fund
        FROM lotteries l
        LEFT JOIN draws d ON l.id = d.lottery_id
        WHERE 1=1
    """
    params = []
    
    if active_only:
        query += " AND l.is_active = TRUE"
    
    if lottery_type:
        query += " AND l.lottery_type = %s"
        params.append(lottery_type)
    
    if min_price is not None:
        query += " AND l.ticket_price >= %s"
        params.append(min_price)
    
    if max_price is not None:
        query += " AND l.ticket_price <= %s"
        params.append(max_price)
    
    query += " GROUP BY l.id ORDER BY l.name"
    
    lotteries = Database.execute_query(query, tuple(params) if params else None)
    
    return jsonify({
        'lotteries': [
            {
                'id': l['id'],
                'name': l['name'],
                'slug': l['slug'],
                'lottery_type': l['lottery_type'],
                'ticket_price': float(l['ticket_price']) if l.get('ticket_price') else None,
                'draw_frequency': l.get('draw_frequency'),
                'description': l.get('description'),
                'max_prize': float(l['max_prize']) if l.get('max_prize') else None,
                'url': l.get('url'),
                'is_active': l.get('is_active'),
                'statistics': {
                    'total_draws': l.get('total_draws', 0),
                    'avg_prize_fund': float(l['avg_prize_fund']) if l.get('avg_prize_fund') else None
                }
            }
            for l in lotteries
        ] if lotteries else [],
        'total': len(lotteries) if lotteries else 0
    }), 200


@lotteries_bp.route('/<int:lottery_id>', methods=['GET'])
def get_lottery_details(lottery_id):
    """Get detailed information about a specific lottery"""
    # Get lottery info
    lottery = Database.execute_query(
        "SELECT * FROM lotteries WHERE id = %s",
        (lottery_id,)
    )
    
    if not lottery:
        return jsonify({'error': 'Lottery not found'}), 404
    
    lottery_data = dict(lottery[0])
    
    # Get recent draws
    draws = Database.execute_query(
        """
        SELECT id, draw_number, draw_date, winning_numbers, 
               total_prize_fund, winners_count
        FROM draws
        WHERE lottery_id = %s
        ORDER BY draw_date DESC
        LIMIT 10
        """,
        (lottery_id,)
    )
    
    # Get prize categories statistics
    prize_stats = Database.execute_query(
        """
        SELECT category_name, 
               AVG(prize_amount) as avg_prize,
               AVG(probability) as avg_probability,
               SUM(winners_count) as total_winners
        FROM prize_categories
        WHERE lottery_id = %s
        GROUP BY category_name
        ORDER BY avg_prize DESC
        """,
        (lottery_id,)
    )
    
    return jsonify({
        'lottery': {
            'id': lottery_data['id'],
            'name': lottery_data['name'],
            'slug': lottery_data['slug'],
            'lottery_type': lottery_data['lottery_type'],
            'ticket_price': float(lottery_data['ticket_price']) if lottery_data.get('ticket_price') else None,
            'draw_frequency': lottery_data.get('draw_frequency'),
            'description': lottery_data.get('description'),
            'rules': lottery_data.get('rules'),
            'max_prize': float(lottery_data['max_prize']) if lottery_data.get('max_prize') else None,
            'url': lottery_data.get('url'),
            'is_active': lottery_data.get('is_active')
        },
        'recent_draws': [
            {
                'id': d['id'],
                'draw_number': d['draw_number'],
                'draw_date': d['draw_date'].isoformat() if d.get('draw_date') else None,
                'winning_numbers': d.get('winning_numbers'),
                'total_prize_fund': float(d['total_prize_fund']) if d.get('total_prize_fund') else None,
                'winners_count': d.get('winners_count', 0)
            }
            for d in draws
        ] if draws else [],
        'prize_statistics': [
            {
                'category': p['category_name'],
                'avg_prize': float(p['avg_prize']) if p.get('avg_prize') else None,
                'avg_probability': float(p['avg_probability']) if p.get('avg_probability') else None,
                'total_winners': p.get('total_winners', 0)
            }
            for p in prize_stats
        ] if prize_stats else []
    }), 200


@lotteries_bp.route('/recommended', methods=['GET'])
@jwt_required()
def get_recommended_lotteries():
    """Get recommended lotteries for the current user"""
    user_id = get_jwt_identity()
    
    # Get user's latest recommendations
    recommendations = Database.execute_query(
        """
        SELECT DISTINCT ON (r.lottery_id)
               r.lottery_id, r.score, r.explanation, r.created_at,
               l.name, l.slug, l.lottery_type, l.ticket_price, 
               l.draw_frequency, l.description, l.max_prize
        FROM recommendations r
        JOIN lotteries l ON r.lottery_id = l.id
        WHERE r.user_id = %s AND l.is_active = TRUE
        ORDER BY r.lottery_id, r.created_at DESC
        LIMIT 10
        """,
        (user_id,)
    )
    
    if not recommendations:
        # No recommendations yet, return popular lotteries
        popular = Database.execute_query(
            """
            SELECT l.*, COUNT(r.id) as recommendation_count
            FROM lotteries l
            LEFT JOIN recommendations r ON l.id = r.lottery_id
            WHERE l.is_active = TRUE
            GROUP BY l.id
            ORDER BY recommendation_count DESC, l.name
            LIMIT 5
            """
        )
        
        return jsonify({
            'recommendations': [
                {
                    'lottery_id': p['id'],
                    'score': 75.0,  # Default score
                    'explanation': 'Популярная лотерея среди пользователей',
                    'lottery': {
                        'id': p['id'],
                        'name': p['name'],
                        'slug': p['slug'],
                        'lottery_type': p['lottery_type'],
                        'ticket_price': float(p['ticket_price']) if p.get('ticket_price') else None,
                        'draw_frequency': p.get('draw_frequency'),
                        'description': p.get('description'),
                        'max_prize': float(p['max_prize']) if p.get('max_prize') else None
                    }
                }
                for p in popular
            ] if popular else [],
            'message': 'Showing popular lotteries. Complete your preferences to get personalized recommendations.'
        }), 200
    
    return jsonify({
        'recommendations': [
            {
                'lottery_id': r['lottery_id'],
                'score': float(r['score']) if r.get('score') else 0,
                'explanation': r.get('explanation'),
                'created_at': r['created_at'].isoformat() if r.get('created_at') else None,
                'lottery': {
                    'id': r['lottery_id'],
                    'name': r['name'],
                    'slug': r['slug'],
                    'lottery_type': r['lottery_type'],
                    'ticket_price': float(r['ticket_price']) if r.get('ticket_price') else None,
                    'draw_frequency': r.get('draw_frequency'),
                    'description': r.get('description'),
                    'max_prize': float(r['max_prize']) if r.get('max_prize') else None
                }
            }
            for r in recommendations
        ]
    }), 200
