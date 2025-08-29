"""
Модуль для интеграции с DeepSeek LLM API
Генерация персонализированных планов питания и вопросов для интервью
"""

import logging
import json
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from config import config

logger = logging.getLogger(__name__)

class LLMIntegration:
    """Класс для работы с DeepSeek LLM API"""
    
    def __init__(self):
        self.base_url = config.DEEPSEEK_BASE_URL
        self.api_key = config.DEEPSEEK_API_KEY
        self.model = config.DEEPSEEK_MODEL
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    async def generate_chat_completion(self, messages: List[Dict], max_tokens: int = None) -> Optional[Dict]:
        """Генерация ответа через chat completion API"""
        if not self.api_key:
            logger.error("❌ DEEPSEEK_API_KEY не установлен")
            return None
        
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": config.DEEPSEEK_TEMPERATURE,
            "max_tokens": max_tokens or config.DEEPSEEK_MAX_TOKENS,
            "stream": False
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=self.headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Ошибка API DeepSeek: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к DeepSeek API: {e}")
            return None
    
    async def generate_interview_questions(self, user_data: Dict, interview_type: str) -> List[str]:
        """Генерация вопросов для интервью"""
        prompt = self._build_interview_prompt(user_data, interview_type)
        
        messages = [
            {"role": "system", "content": "Ты опытный спортивный диетолог. Генерируй конкретные, четкие вопросы для сбора информации о питании и тренировках спортсменов."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.generate_chat_completion(messages, max_tokens=1000)
        if response and 'choices' in response:
            content = response['choices'][0]['message']['content']
            return self._parse_questions(content)
        
        # Fallback вопросы
        return self._get_fallback_questions(interview_type)
    
    async def generate_meal_plan(self, user_data: Dict, interview_answers: Dict) -> Optional[Dict]:
        """Генерация персонализированного плана питания"""
        prompt = self._build_meal_plan_prompt(user_data, interview_answers)
        
        messages = [
            {"role": "system", "content": "Ты эксперт по спортивному питанию. Создавай детальные, персонализированные планы питания для спортсменов с учетом их целей, вида спорта и индивидуальных особенностей."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.generate_chat_completion(messages)
        if response and 'choices' in response:
            content = response['choices'][0]['message']['content']
            return self._parse_meal_plan(content, user_data)
        
        return None
    
    def _build_interview_prompt(self, user_data: Dict, interview_type: str) -> str:
        """Построение промпта для интервью"""
        base_info = f"""
        Спортсмен: {user_data.get('first_name', 'Пользователь')}
        Пол: {user_data.get('gender', 'не указан')}
        Возраст: {user_data.get('age', 'не указан')}
        Вес: {user_data.get('weight', 'не указан')} кг
        Рост: {user_data.get('height', 'не указан')} см
        Вид спорта: {user_data.get('sport_type', 'не указан')}
        Цель: {user_data.get('goal', 'не указана')}
        """
        
        if interview_type == 'training':
            return f"""
            {base_info}
            Сгенерируй 5-7 конкретных вопросов о тренировочном процессе этого спортсмена.
            Вопросы должны касаться: частоты тренировок, продолжительности, интенсивности, 
            типа тренировок, времени суток для тренировок, восстановления.
            Верни только вопросы, пронумерованные через точку, без дополнительного текста.
            """
        else:  # activity
            return f"""
            {base_info}
            Сгенерируй 5-7 конкретных вопросов о повседневной активности и образе жизни.
            Вопросы должны касаться: уровня daily activity, работы, хобби, сна, стресса, 
            пищевых привычек, аллергий и предпочтений в еде.
            Верни только вопросы, пронумерованные через точку, без дополнительного текста.
            """
    
    def _build_meal_plan_prompt(self, user_data: Dict, interview_answers: Dict) -> str:
        """Построение промпта для генерации плана питания"""
        return f"""
        Создай детальный 7-дневный план питания для спортсмена:
        
        Основная информация:
        - Имя: {user_data.get('first_name', 'Спортсмен')}
        - Пол: {user_data.get('gender')}
        - Возраст: {user_data.get('age')} лет
        - Вес: {user_data.get('weight')} кг
        - Рост: {user_data.get('height')} см
        - Вид спорта: {user_data.get('sport_type')}
        - Цель: {user_data.get('goal')}
        - Дата соревнований: {user_data.get('competition_date')}
        
        Тренировочные данные:
        {json.dumps(interview_answers.get('training', {}), ensure_ascii=False, indent=2)}
        
        Данные об активности:
        {json.dumps(interview_answers.get('activity', {}), ensure_ascii=False, indent=2)}
        
        Требования к плану:
        1. 7 дней питания с завтраком, обедом, ужином и 2 перекусами
        2. Указать точные порции в граммах/мл
        3. Рассчитать БЖУ и калории для каждого приема пищи
        4. Учесть время тренировок и соревнований
        5. Предложить варианты замены для аллергиков
        6. Учесть пищевые предпочтения из интервью
        7. Добавить рекомендации по гидратации
        8. Указать timing питания вокруг тренировок
        
        Верни ответ в формате JSON с структурой:
        {{
            "plan_type": "7_day_meal_plan",
            "total_calories": number,
            "protein_grams": number,
            "carbs_grams": number,
            "fat_grams": number,
            "days": [
                {{
                    "day_number": 1,
                    "date": "YYYY-MM-DD",
                    "meals": [
                        {{
                            "meal_type": "breakfast|lunch|dinner|snack",
                            "time": "HH:MM",
                            "food_items": [
                                {{
                                    "name": "Название продукта",
                                    "portion": "100г",
                                    "calories": number,
                                    "protein": number,
                                    "carbs": number,
                                    "fat": number
                                }}
                            ],
                            "total_calories": number,
                            "total_protein": number,
                            "total_carbs": number,
                            "total_fat": number,
                            "recommendations": "Текст рекомендаций"
                        }}
                    ],
                    "training_schedule": "Описание тренировки",
                    "hydration": "Рекомендации по воде"
                }}
            ],
            "general_recommendations": "Общие рекомендации",
            "shopping_list": ["список продуктов"]
        }}
        """
    
    def _parse_questions(self, content: str) -> List[str]:
        """Парсинг сгенерированных вопросов"""
        questions = []
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line and any(line.startswith(f"{i}.") for i in range(1, 10)):
                # Убираем нумерацию "1.", "2." и т.д.
                question = line.split('.', 1)[1].strip()
                if question:
                    questions.append(question)
        
        return questions or self._get_fallback_questions('general')
    
    def _parse_meal_plan(self, content: str, user_data: Dict) -> Optional[Dict]:
        """Парсинг сгенерированного плана питания"""
        try:
            # Пытаемся найти JSON в ответе
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start != -1 and json_end != 0:
                json_str = content[json_start:json_end]
                plan_data = json.loads(json_str)
                
                # Добавляем базовую информацию
                plan_data['generated_for'] = {
                    'user_id': user_data.get('telegram_id'),
                    'generated_at': str(datetime.now())
                }
                
                return plan_data
        except json.JSONDecodeError as e:
            logger.error(f"❌ Ошибка парсинга JSON плана питания: {e}")
        
        return None
    
    def _get_fallback_questions(self, interview_type: str) -> List[str]:
        """Резервные вопросы на случай ошибки API"""
        if interview_type == 'training':
            return [
                "Сколько раз в неделю вы тренируетесь?",
                "Какова продолжительность одной тренировки?",
                "Какова интенсивность ваших тренировок (низкая/средняя/высокая)?",
                "В какое время суток вы обычно тренируетесь?",
                "Какие типы тренировок преобладают (силовые/кардио/смешанные)?"
            ]
        else:
            return [
                "Опишите ваш обычный уровень daily activity (сидячий/умеренный/активный)?",
                "Есть ли у вас пищевые аллергии или непереносимости?",
                "Какие продукты вы предпочитаете избегать в питании?",
                "Сколько часов в сутки вы обычно спите?",
                "Испытываете ли вы регулярный стресс?"
            ]

# Глобальный экземпляр LLM интеграции
llm = LLMIntegration()