import ollama
from config import Config
from typing import List, Dict, Optional


class OllamaClient:
    """Client for interacting with Ollama LLM"""
    
    def __init__(self):
        self.host = Config.OLLAMA_HOST
        self.model = Config.OLLAMA_MODEL
        self.timeout = Config.OLLAMA_TIMEOUT
        
    def test_connection(self) -> bool:
        """Test connection to Ollama server"""
        try:
            models = ollama.list()
            return True
        except Exception as e:
            print(f"Ollama connection failed: {e}")
            return False
    
    def generate_response(
        self,
        user_message: str,
        context_data: Optional[Dict] = None,
        chat_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Generate a response from the LLM
        
        Args:
            user_message: User's question/message
            context_data: Relevant data from database (lotteries, user preferences, etc.)
            chat_history: Previous conversation history
            
        Returns:
            Generated response text
        """
        # Build system prompt
        system_prompt = self._build_system_prompt(context_data)
        
        # Build conversation messages
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add chat history if available
        if chat_history:
            for msg in chat_history[-5:]:  # Last 5 messages for context
                messages.append({
                    "role": "user" if msg.get('is_user_message') else "assistant",
                    "content": msg.get('message', '')
                })
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        try:
            # Call Ollama
            response = ollama.chat(
                model=self.model,
                messages=messages
            )
            
            return response['message']['content']
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return "Извините, произошла ошибка при обработке вашего запроса. Попробуйте позже."
    
    def _build_system_prompt(self, context_data: Optional[Dict] = None) -> str:
        """Build system prompt with context"""
        
        base_prompt = """Ты - помощник по выбору лотерей Столото. 

ВАЖНО - СТИЛЬ ОТВЕТОВ:
- Отвечай КРАТКО и ПО ДЕЛУ - максимум 3-4 предложения
- БЕЗ длинных объяснений и лишней воды
- Сразу к сути - конкретные рекомендации
- Используй ТОЛЬКО русский язык (никаких английских слов)
- Отвечай только на основе предоставленных данных
- Если данных недостаточно - скажи это в одном предложении

ФОРМАТ ОТВЕТА:
- Одна рекомендация = 1-2 предложения максимум
- Не повторяй информацию, которую пользователь уже знает
- Не объясняй очевидное"""

        if not context_data:
            return base_prompt
        
        # Add user name if available
        if 'user_name' in context_data and context_data['user_name']:
            base_prompt += f"\n\nИмя пользователя: {context_data['user_name']}"
            base_prompt += "\nОбращайся к пользователю по имени в ответах."
        
        # Add user preferences to context
        if 'preferences' in context_data:
            prefs = context_data['preferences']
            base_prompt += f"\n\nПредпочтения пользователя:"
            if prefs.get('budget'):
                base_prompt += f"\n- Бюджет: {prefs['budget']} руб."
            if prefs.get('preferred_prize_type'):
                prize_type_map = {
                    'instant': 'мгновенные выигрыши',
                    'draw': 'тиражные лотереи',
                    'both': 'любой тип'
                }
                base_prompt += f"\n- Тип выигрыша: {prize_type_map.get(prefs['preferred_prize_type'], prefs['preferred_prize_type'])}"
            if prefs.get('preferred_prize_size'):
                size_map = {
                    'small': 'небольшие частые выигрыши',
                    'medium': 'средние призы',
                    'large': 'крупные призы',
                    'jackpot': 'джекпот'
                }
                base_prompt += f"\n- Желаемый размер приза: {size_map.get(prefs['preferred_prize_size'], prefs['preferred_prize_size'])}"
        
        # Add available lotteries to context (только базовая инфо)
        if 'lotteries' in context_data:
            lotteries = context_data['lotteries']
            if lotteries:
                base_prompt += f"\n\nДоступные лотереи ({len(lotteries)}):"
                for lottery in lotteries[:10]:  # Limit to 10
                    lottery_type = 'мгновенная' if lottery.get('lottery_type') == 'instant' else 'тиражная'
                    base_prompt += f"\n- {lottery['name']} ({lottery_type}, {lottery.get('ticket_price', 'N/A')} руб.)"
        
        return base_prompt
    
    def generate_recommendation_explanation(
        self,
        lottery_name: str,
        lottery_params: Dict,
        user_preferences: Dict,
        score: float
    ) -> str:
        """Generate human-readable explanation for a recommendation"""
        
        prompt = f"""Объясни пользователю, почему лотерея "{lottery_name}" ему подходит 
(рейтинг соответствия: {score}/100).

Параметры лотереи:
{self._format_lottery_params(lottery_params)}

Предпочтения пользователя:
{self._format_user_preferences(user_preferences)}

Дай краткое (2-3 предложения) объяснение, почему эта лотерея подходит."""

        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            return response['message']['content']
        except Exception as e:
            print(f"Error generating explanation: {e}")
            return f"Рейтинг соответствия: {score}/100"
    
    def _format_lottery_params(self, params: Dict) -> str:
        """Format lottery parameters for prompt"""
        lines = []
        if params.get('lottery_type'):
            lottery_type = 'мгновенная' if params['lottery_type'] == 'instant' else 'тиражная'
            lines.append(f"- Тип: {lottery_type}")
        if params.get('ticket_price'):
            lines.append(f"- Цена билета: {params['ticket_price']} руб.")
        if params.get('draw_frequency'):
            lines.append(f"- Частота розыгрышей: {params['draw_frequency']}")
        if params.get('max_prize'):
            lines.append(f"- Максимальный приз: {params['max_prize']} руб.")
        return '\n'.join(lines)
    
    def _format_user_preferences(self, prefs: Dict) -> str:
        """Format user preferences for prompt"""
        lines = []
        if prefs.get('budget'):
            lines.append(f"- Бюджет: {prefs['budget']} руб.")
        if prefs.get('preferred_prize_type'):
            lines.append(f"- Предпочитаемый тип: {prefs['preferred_prize_type']}")
        if prefs.get('preferred_prize_size'):
            lines.append(f"- Желаемый размер приза: {prefs['preferred_prize_size']}")
        return '\n'.join(lines)


# Singleton instance
_ollama_client = None

def get_ollama_client() -> OllamaClient:
    """Get or create Ollama client instance"""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client


if __name__ == '__main__':
    # Test Ollama connection
    client = OllamaClient()
    if client.test_connection():
        print("✓ Ollama connection successful!")
        
        # Test generation
        test_response = client.generate_response(
            "Привет! Посоветуй мне лотерею.",
            context_data={
                'preferences': {
                    'budget': 200,
                    'preferred_prize_type': 'instant'
                }
            }
        )
        print(f"\nTest response:\n{test_response}")
    else:
        print("✗ Ollama connection failed!")
