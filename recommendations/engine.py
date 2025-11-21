from typing import List, Dict, Optional
from database.db import Database
from llm.ollama_client import get_ollama_client
from datetime import datetime
import json


class RecommendationEngine:
    """Engine for generating personalized lottery recommendations"""
    
    def __init__(self):
        self.ollama_client = get_ollama_client()
    
    def generate_recommendations(self, user_id: int, top_n: int = 10) -> List[Dict]:
        """
        Generate personalized lottery recommendations for a user
        
        Args:
            user_id: User ID
            top_n: Number of top recommendations to return
            
        Returns:
            List of recommendations with scores and explanations
        """
        # Get user preferences
        preferences = self._get_user_preferences(user_id)
        
        if not preferences:
            # No preferences, return popular lotteries
            return self._get_popular_lotteries(top_n)
        
        # Get all active lotteries
        lotteries = self._get_active_lotteries()
        
        if not lotteries:
            return []
        
        # Calculate scores for each lottery
        recommendations = []
        for lottery in lotteries:
            score = self._calculate_lottery_score(lottery, preferences)
            recommendations.append({
                'lottery_id': lottery['id'],
                'lottery': lottery,
                'score': score,
                'preferences': preferences
            })
        
        # Sort by score descending
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        # Get top N
        top_recommendations = recommendations[:top_n]
        
        # Generate explanations for top recommendations
        for rec in top_recommendations:
            explanation = self._generate_explanation(
                rec['lottery']['name'],
                rec['lottery'],
                rec['preferences'],
                rec['score']
            )
            rec['explanation'] = explanation
        
        # Save recommendations to database
        self._save_recommendations(user_id, top_recommendations)
        
        return top_recommendations
    
    def _get_user_preferences(self, user_id: int) -> Optional[Dict]:
        """Get user preferences from database"""
        result = Database.execute_query(
            """
            SELECT budget, preferred_prize_type, preferred_prize_size,
                   min_acceptable_probability, max_waiting_time, risk_profile
            FROM user_preferences
            WHERE user_id = %s
            """,
            (user_id,)
        )
        
        return dict(result[0]) if result else None
    
    def _get_active_lotteries(self) -> List[Dict]:
        """Get all active lotteries"""
        result = Database.execute_query(
            """
            SELECT l.*,
                   AVG(pc.probability) as avg_win_probability,
                   COUNT(DISTINCT d.id) as total_draws
            FROM lotteries l
            LEFT JOIN prize_categories pc ON l.id = pc.lottery_id
            LEFT JOIN draws d ON l.id = d.lottery_id
            WHERE l.is_active = TRUE
            GROUP BY l.id
            """
        )
        
        return [dict(r) for r in result] if result else []
    
    def _get_popular_lotteries(self, limit: int) -> List[Dict]:
        """Get popular lotteries when no preferences available"""
        result = Database.execute_query(
            """
            SELECT l.*, COUNT(r.id) as recommendation_count
            FROM lotteries l
            LEFT JOIN recommendations r ON l.id = r.lottery_id
            WHERE l.is_active = TRUE
            GROUP BY l.id
            ORDER BY recommendation_count DESC, l.name
            LIMIT %s
            """,
            (limit,)
        )
        
        return [
            {
                'lottery_id': r['id'],
                'lottery': dict(r),
                'score': 75.0,
                'explanation': 'Популярная лотерея'
            }
            for r in result
        ] if result else []
    
    def _calculate_lottery_score(self, lottery: Dict, preferences: Dict) -> float:
        """
        Calculate a score for how well a lottery matches user preferences
        
        Score is 0-100, with 100 being a perfect match
        """
        score = 0.0
        max_score = 0.0
        
        # Budget match (weight: 30)
        if preferences.get('budget') and lottery.get('ticket_price'):
            budget = float(preferences['budget'])
            price = float(lottery['ticket_price'])
            
            if price <= budget:
                # Within budget - higher score if closer to budget
                score += 30 * (price / budget)
            else:
                # Over budget - penalize
                score += max(0, 30 * (1 - (price - budget) / budget))
            max_score += 30
        
        # Lottery type match (weight: 25)
        if preferences.get('preferred_prize_type'):
            pref_type = preferences['preferred_prize_type']
            lottery_type = lottery.get('lottery_type')
            
            if pref_type == 'both' or pref_type == lottery_type:
                score += 25
            elif pref_type in ['instant', 'draw'] and lottery_type:
                # Partial match for opposite type
                score += 10
            max_score += 25
        
        # Prize size match (weight: 20)
        if preferences.get('preferred_prize_size') and lottery.get('max_prize'):
            pref_size = preferences['preferred_prize_size']
            max_prize = float(lottery['max_prize']) if lottery.get('max_prize') else 0
            
            size_ranges = {
                'small': (0, 10000),
                'medium': (10000, 100000),
                'large': (100000, 1000000),
                'jackpot': (1000000, float('inf'))
            }
            
            if pref_size in size_ranges:
                min_range, max_range = size_ranges[pref_size]
                if min_range <= max_prize <= max_range:
                    score += 20
                else:
                    # Partial score if close to range
                    if max_prize < min_range:
                        score += 10 * (max_prize / min_range)
                    else:
                        score += 10
            max_score += 20
        
        # Win probability match (weight: 15)
        if preferences.get('min_acceptable_probability') and lottery.get('avg_win_probability'):
            min_prob = float(preferences['min_acceptable_probability'])
            avg_prob = float(lottery['avg_win_probability'])
            
            if avg_prob >= min_prob:
                score += 15
            else:
                # Partial score
                score += 15 * (avg_prob / min_prob)
            max_score += 15
        
        # Risk profile match (weight: 10)
        if preferences.get('risk_profile') and lottery.get('lottery_type'):
            risk_profile = preferences['risk_profile']
            lottery_type = lottery['lottery_type']
            
            # Conservative prefers instant with higher win probability
            # Aggressive prefers draw with bigger jackpots
            if risk_profile == 'conservative' and lottery_type == 'instant':
                score += 10
            elif risk_profile == 'aggressive' and lottery_type == 'draw':
                score += 10
            elif risk_profile == 'moderate':
                score += 7
            max_score += 10
        
        # Normalize score to 0-100
        if max_score > 0:
            return (score / max_score) * 100
        return 50.0  # Default score if no matching criteria
    
    def _generate_explanation(
        self,
        lottery_name: str,
        lottery_params: Dict,
        user_preferences: Dict,
        score: float
    ) -> str:
        """Generate human-readable explanation using LLM"""
        try:
            return self.ollama_client.generate_recommendation_explanation(
                lottery_name,
                lottery_params,
                user_preferences,
                score
            )
        except Exception as e:
            print(f"Error generating explanation: {e}")
            return f"Рейтинг соответствия ваш{'' if score >= 70 else 'им'} предпочтениям: {score:.1f}/100"
    
    def _save_recommendations(self, user_id: int, recommendations: List[Dict]):
        """Save recommendations to database"""
        timestamp = datetime.now()
        
        data_to_insert = [
            (
                user_id,
                rec['lottery_id'],
                rec['score'],
                rec.get('explanation', ''),
                timestamp
            )
            for rec in recommendations
        ]
        
        if data_to_insert:
            Database.execute_many(
                """
                INSERT INTO recommendations (user_id, lottery_id, score, explanation, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                data_to_insert
            )


def generate_recommendations_for_user(user_id: int, top_n: int = 10) -> List[Dict]:
    """
    Convenience function to generate recommendations
    
    Args:
        user_id: User ID
        top_n: Number of recommendations to generate
        
    Returns:
        List of recommendations
    """
    engine = RecommendationEngine()
    return engine.generate_recommendations(user_id, top_n)


if __name__ == '__main__':
    # Test recommendation engine
    print("Testing recommendation engine...")
    
    # This would need a valid user_id from the database
    # recommendations = generate_recommendations_for_user(1, top_n=5)
    # print(f"Generated {len(recommendations)} recommendations")
    # for rec in recommendations:
    #     print(f"- {rec['lottery']['name']}: {rec['score']:.1f}/100")
    #     print(f"  {rec['explanation']}")
    
    print("Recommendation engine module created successfully!")
