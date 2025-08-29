"""
Модуль для работы с базой данных PostgreSQL
Реализует все CRUD операции для AI диетолога 3.0
"""

import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
from config import config

logger = logging.getLogger(__name__)

class Database:
    """Класс для работы с базой данных PostgreSQL"""
    
    def __init__(self):
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """Установить соединение с базой данных"""
        try:
            self.connection = psycopg2.connect(
                config.database_url,
                cursor_factory=RealDictCursor
            )
            self.cursor = self.connection.cursor()
            logger.info("✅ Успешное подключение к базе данных")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к базе данных: {e}")
            raise
    
    def close(self):
        """Закрыть соединение с базой данных"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.info("✅ Соединение с базой данных закрыто")
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Выполнить запрос и вернуть результаты"""
        try:
            self.cursor.execute(query, params)
            if query.strip().upper().startswith('SELECT'):
                return self.cursor.fetchall()
            self.connection.commit()
            return []
        except Exception as e:
            self.connection.rollback()
            logger.error(f"❌ Ошибка выполнения запроса: {e}")
            raise
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получить пользователя по ID"""
        query = "SELECT * FROM athletes WHERE telegram_id = %s"
        result = self.execute_query(query, (user_id,))
        return result[0] if result else None
    
    def create_user(self, user_data: Dict) -> int:
        """Создать нового пользователя"""
        query = """
        INSERT INTO athletes (
            telegram_id, username, first_name, last_name, 
            gender, age, weight, height, sport_type, 
            training_frequency, training_duration, training_intensity,
            goal, competition_date, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """
        params = (
            user_data['telegram_id'], user_data.get('username'), 
            user_data.get('first_name'), user_data.get('last_name'),
            user_data.get('gender'), user_data.get('age'), 
            user_data.get('weight'), user_data.get('height'),
            user_data.get('sport_type'), user_data.get('training_frequency'),
            user_data.get('training_duration'), user_data.get('training_intensity'),
            user_data.get('goal'), user_data.get('competition_date'),
            datetime.now()
        )
        result = self.execute_query(query, params)
        return result[0]['id'] if result else None
    
    def update_user(self, user_id: int, update_data: Dict) -> bool:
        """Обновить данные пользователя"""
        set_clause = ", ".join([f"{key} = %s" for key in update_data.keys()])
        values = list(update_data.values())
        values.append(user_id)
        
        query = f"UPDATE athletes SET {set_clause}, updated_at = %s WHERE telegram_id = %s"
        values.append(datetime.now())
        
        self.execute_query(query, values)
        return True
    
    def save_meal_plan(self, user_id: int, plan_data: Dict, days: int = 7) -> int:
        """Сохранить план питания"""
        query = """
        INSERT INTO meal_plans (
            athlete_id, plan_type, duration_days, total_calories, 
            protein_grams, carbs_grams, fat_grams, plan_data, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """
        params = (
            user_id, plan_data.get('plan_type', 'custom'), days,
            plan_data.get('total_calories', 0), plan_data.get('protein_grams', 0),
            plan_data.get('carbs_grams', 0), plan_data.get('fat_grams', 0),
            plan_data, datetime.now()
        )
        result = self.execute_query(query, params)
        return result[0]['id'] if result else None
    
    def get_user_plans(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Получить планы питания пользователя"""
        query = """
        SELECT mp.* FROM meal_plans mp
        JOIN athletes a ON mp.athlete_id = a.id
        WHERE a.telegram_id = %s
        ORDER BY mp.created_at DESC
        LIMIT %s
        """
        return self.execute_query(query, (user_id, limit))
    
    def get_plan_by_id(self, plan_id: int) -> Optional[Dict]:
        """Получить план питания по ID"""
        query = "SELECT * FROM meal_plans WHERE id = %s"
        result = self.execute_query(query, (plan_id,))
        return result[0] if result else None
    
    def save_activity(self, user_id: int, activity_type: str, data: Dict) -> int:
        """Сохранить активность пользователя"""
        query = """
        INSERT INTO activities (
            athlete_id, activity_type, activity_data, created_at
        ) VALUES (%s, %s, %s, %s)
        RETURNING id
        """
        params = (user_id, activity_type, data, datetime.now())
        result = self.execute_query(query, params)
        return result[0]['id'] if result else None
    
    def get_user_activities(self, user_id: int, activity_type: str = None, limit: int = 50) -> List[Dict]:
        """Получить активности пользователя"""
        query = """
        SELECT a.* FROM activities a
        JOIN athletes ath ON a.athlete_id = ath.id
        WHERE ath.telegram_id = %s
        """
        params = [user_id]
        
        if activity_type:
            query += " AND a.activity_type = %s"
            params.append(activity_type)
        
        query += " ORDER BY a.created_at DESC LIMIT %s"
        params.append(limit)
        
        return self.execute_query(query, tuple(params))
    
    def log_meal(self, user_id: int, meal_data: Dict) -> int:
        """Записать прием пищи"""
        query = """
        INSERT INTO meals (
            athlete_id, meal_type, food_items, calories, 
            protein_grams, carbs_grams, fat_grams, meal_time, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """
        params = (
            user_id, meal_data.get('meal_type'), meal_data.get('food_items'),
            meal_data.get('calories', 0), meal_data.get('protein_grams', 0),
            meal_data.get('carbs_grams', 0), meal_data.get('fat_grams', 0),
            meal_data.get('meal_time', datetime.now()), datetime.now()
        )
        result = self.execute_query(query, params)
        return result[0]['id'] if result else None
    
    def get_today_meals(self, user_id: int) -> List[Dict]:
        """Получить приемы пищи за сегодня"""
        query = """
        SELECT * FROM meals 
        WHERE athlete_id = %s AND DATE(meal_time) = CURRENT_DATE
        ORDER BY meal_time
        """
        return self.execute_query(query, (user_id,))
    
    def validate_competition_date(self, competition_date: date) -> bool:
        """Проверить валидность даты соревнований"""
        if competition_date <= date.today():
            return False
        return True
    
    def validate_weight_difference(self, current_weight: float, target_weight: float) -> bool:
        """Проверить разницу весов (не более 30%)"""
        if current_weight <= 0 or target_weight <= 0:
            return False
        
        difference = abs(current_weight - target_weight) / current_weight
        return difference <= 0.3  # 30% максимальная разница

# Глобальный экземпляр базы данных
db = Database()