from flask import Blueprint, request, jsonify
from database.db import Database

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')


@analytics_bp.route('/summary', methods=['GET'])
def get_summary_statistics():
    """Get summary statistics for all lotteries"""
    
    # Get total active lotteries
    stats = Database.execute_query(
        """
        SELECT 
            COUNT(*) as total_lotteries,
            COUNT(*) FILTER (WHERE lottery_type = 'instant') as instant_count,
            COUNT(*) FILTER (WHERE lottery_type = 'draw') as draw_count,
            AVG(ticket_price) as avg_ticket_price,
            MIN(ticket_price) as min_ticket_price,
            MAX(ticket_price) as max_ticket_price,
            AVG(max_prize) as avg_max_prize,
            MAX(max_prize) as biggest_jackpot
        FROM lotteries
        WHERE is_active = TRUE
        """
    )
    
    # Get total draws
    draws_stats = Database.execute_query(
        """
        SELECT 
            COUNT(*) as total_draws,
            SUM(total_prize_fund) as total_prize_fund_distributed,
            SUM(winners_count) as total_winners
        FROM draws
        """
    )
    
    # Get recent activity
    recent_draws = Database.execute_query(
        """
        SELECT d.draw_date, l.name as lottery_name, d.total_prize_fund, d.winners_count
        FROM draws d
        JOIN lotteries l ON d.lottery_id = l.id
        ORDER BY d.draw_date DESC
        LIMIT 5
        """
    )
    
    stats_data = dict(stats[0]) if stats else {}
    draws_data = dict(draws_stats[0]) if draws_stats else {}
    
    return jsonify({
        'summary': {
            'total_active_lotteries': stats_data.get('total_lotteries', 0),
            'instant_lotteries': stats_data.get('instant_count', 0),
            'draw_lotteries': stats_data.get('draw_count', 0),
            'avg_ticket_price': float(stats_data['avg_ticket_price']) if stats_data.get('avg_ticket_price') else None,
            'min_ticket_price': float(stats_data['min_ticket_price']) if stats_data.get('min_ticket_price') else None,
            'max_ticket_price': float(stats_data['max_ticket_price']) if stats_data.get('max_ticket_price') else None,
            'avg_max_prize': float(stats_data['avg_max_prize']) if stats_data.get('avg_max_prize') else None,
            'biggest_jackpot': float(stats_data['biggest_jackpot']) if stats_data.get('biggest_jackpot') else None
        },
        'total_statistics': {
            'total_draws': draws_data.get('total_draws', 0),
            'total_prize_fund_distributed': float(draws_data['total_prize_fund_distributed']) if draws_data.get('total_prize_fund_distributed') else 0,
            'total_winners': draws_data.get('total_winners', 0)
        },
        'recent_activity': [
            {
                'date': d['draw_date'].isoformat() if d.get('draw_date') else None,
                'lottery_name': d['lottery_name'],
                'prize_fund': float(d['total_prize_fund']) if d.get('total_prize_fund') else None,
                'winners': d.get('winners_count', 0)
            }
            for d in recent_draws
        ] if recent_draws else []
    }), 200


@analytics_bp.route('/lottery/<int:lottery_id>', methods=['GET'])
def get_lottery_analytics(lottery_id):
    """Get detailed analytics for a specific lottery"""
    
    # Check if lottery exists
    lottery = Database.execute_query(
        "SELECT name FROM lotteries WHERE id = %s",
        (lottery_id,)
    )
    
    if not lottery:
        return jsonify({'error': 'Lottery not found'}), 404
    
    # Get draw statistics
    draw_stats = Database.execute_query(
        """
        SELECT 
            COUNT(*) as total_draws,
            AVG(total_prize_fund) as avg_prize_fund,
            MAX(total_prize_fund) as max_prize_fund,
            MIN(total_prize_fund) as min_prize_fund,
            SUM(winners_count) as total_winners,
            AVG(winners_count) as avg_winners_per_draw
        FROM draws
        WHERE lottery_id = %s
        """,
        (lottery_id,)
    )
    
    # Get prize category statistics
    prize_categories = Database.execute_query(
        """
        SELECT 
            category_name,
            COUNT(*) as occurrences,
            AVG(prize_amount) as avg_prize,
            MAX(prize_amount) as max_prize,
            AVG(probability) as avg_probability,
            SUM(winners_count) as total_winners
        FROM prize_categories
        WHERE lottery_id = %s
        GROUP BY category_name
        ORDER BY avg_prize DESC
        """,
        (lottery_id,)
    )
    
    # Get monthly trends (last 12 months)
    monthly_trends = Database.execute_query(
        """
        SELECT 
            DATE_TRUNC('month', draw_date) as month,
            COUNT(*) as draws_count,
            AVG(total_prize_fund) as avg_prize_fund,
            SUM(winners_count) as total_winners
        FROM draws
        WHERE lottery_id = %s 
              AND draw_date >= CURRENT_DATE - INTERVAL '12 months'
        GROUP BY DATE_TRUNC('month', draw_date)
        ORDER BY month DESC
        """,
        (lottery_id,)
    )
    
    draw_stats_data = dict(draw_stats[0]) if draw_stats else {}
    
    return jsonify({
        'lottery_id': lottery_id,
        'lottery_name': lottery[0]['name'],
        'draw_statistics': {
            'total_draws': draw_stats_data.get('total_draws', 0),
            'avg_prize_fund': float(draw_stats_data['avg_prize_fund']) if draw_stats_data.get('avg_prize_fund') else None,
            'max_prize_fund': float(draw_stats_data['max_prize_fund']) if draw_stats_data.get('max_prize_fund') else None,
            'min_prize_fund': float(draw_stats_data['min_prize_fund']) if draw_stats_data.get('min_prize_fund') else None,
            'total_winners': draw_stats_data.get('total_winners', 0),
            'avg_winners_per_draw': float(draw_stats_data['avg_winners_per_draw']) if draw_stats_data.get('avg_winners_per_draw') else None
        },
        'prize_categories': [
            {
                'category': p['category_name'],
                'occurrences': p['occurrences'],
                'avg_prize': float(p['avg_prize']) if p.get('avg_prize') else None,
                'max_prize': float(p['max_prize']) if p.get('max_prize') else None,
                'avg_probability': float(p['avg_probability']) if p.get('avg_probability') else None,
                'total_winners': p.get('total_winners', 0)
            }
            for p in prize_categories
        ] if prize_categories else [],
        'monthly_trends': [
            {
                'month': t['month'].isoformat() if t.get('month') else None,
                'draws_count': t['draws_count'],
                'avg_prize_fund': float(t['avg_prize_fund']) if t.get('avg_prize_fund') else None,
                'total_winners': t.get('total_winners', 0)
            }
            for t in monthly_trends
        ] if monthly_trends else []
    }), 200


@analytics_bp.route('/win-probability/<int:lottery_id>', methods=['GET'])
def get_win_probability(lottery_id):
    """Calculate win probability for a lottery"""
    
    # Get prize categories with probabilities
    probabilities = Database.execute_query(
        """
        SELECT 
            category_name,
            AVG(probability) as probability,
            AVG(prize_amount) as avg_prize
        FROM prize_categories
        WHERE lottery_id = %s AND probability IS NOT NULL
        GROUP BY category_name
        ORDER BY probability DESC
        """,
        (lottery_id,)
    )
    
    if not probabilities:
        return jsonify({
            'lottery_id': lottery_id,
            'message': 'Insufficient data to calculate probabilities',
            'probabilities': []
        }), 200
    
    # Calculate overall win probability (any prize)
    total_win_probability = sum(float(p['probability']) for p in probabilities if p.get('probability'))
    
    return jsonify({
        'lottery_id': lottery_id,
        'overall_win_probability': total_win_probability,
        'probabilities_by_category': [
            {
                'category': p['category_name'],
                'probability': float(p['probability']) if p.get('probability') else None,
                'probability_percentage': float(p['probability']) * 100 if p.get('probability') else None,
                'avg_prize': float(p['avg_prize']) if p.get('avg_prize') else None
            }
            for p in probabilities
        ]
    }), 200
