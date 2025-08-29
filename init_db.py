#!/usr/bin/env python3
"""
Скрипт инициализации базы данных для AI диетолога 3.0
Создает необходимые таблицы и индексы
"""

import logging
import sys
from database import db
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_tables():
    """Создание всех необходимых таблиц"""
    
    tables = [
        """
        CREATE TABLE IF NOT EXISTS athletes (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE NOT NULL,
            username VARCHAR(100),
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            gender VARCHAR(10),
            age INTEGER,
            weight DECIMAL(5,2),
            height DECIMAL(5,2),
            sport_type VARCHAR(100),
            training_frequency VARCHAR(50),
            training_duration VARCHAR(50),
            training_intensity VARCHAR(50),
            goal TEXT,
            competition_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS meal_plans (
            id SERIAL PRIMARY KEY,
            athlete_id INTEGER REFERENCES athletes(id) ON DELETE CASCADE,
            plan_type VARCHAR(50) DEFAULT 'custom',
            duration_days INTEGER DEFAULT 7,
            total_calories DECIMAL(8,2),
            protein_grams DECIMAL(8,2),
            carbs_grams DECIMAL(8,2),
            fat_grams DECIMAL(8,2),
            plan_data JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS meals (
            id SERIAL PRIMARY KEY,
            athlete_id INTEGER REFERENCES athletes(id) ON DELETE CASCADE,
            meal_type VARCHAR(50) NOT NULL,
            food_items JSONB NOT NULL,
            calories DECIMAL(8,2),
            protein_grams DECIMAL(8,2),
            carbs_grams DECIMAL(8,2),
            fat_grams DECIMAL(8,2),
            meal_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS activities (
            id SERIAL PRIMARY KEY,
            athlete_id INTEGER REFERENCES athletes(id) ON DELETE CASCADE,
            activity_type VARCHAR(50) NOT NULL,
            activity_data JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS workouts (
            id SERIAL PRIMARY KEY,
            athlete_id INTEGER REFERENCES athletes(id) ON DELETE CASCADE,
            workout_type VARCHAR(100) NOT NULL,
            duration_minutes INTEGER,
            intensity VARCHAR(50),
            calories_burned DECIMAL(8,2),
            workout_data JSONB NOT NULL,
            workout_date DATE DEFAULT CURRENT_DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    ]
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_athletes_telegram_id ON athletes(telegram_id)",
        "CREATE INDEX IF NOT EXISTS idx_meal_plans_athlete_id ON meal_plans(athlete_id)",
        "CREATE INDEX IF NOT EXISTS idx_meal_plans_created_at ON meal_plans(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_meals_athlete_id ON meals(athlete_id)",
        "CREATE INDEX IF NOT EXISTS idx_meals_meal_time ON meals(meal_time)",
        "CREATE INDEX IF NOT EXISTS idx_activities_athlete_id ON activities(athlete_id)",
        "CREATE INDEX IF NOT EXISTS idx_activities_created_at ON activities(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_workouts_athlete_id ON workouts(athlete_id)",
        "CREATE INDEX IF NOT EXISTS idx_workouts_workout_date ON workouts(workout_date)"
    ]
    
    try:
        # Создаем таблицы
        for table_sql in tables:
            db.execute_query(table_sql)
            logger.info("✅ Таблица создана/проверена")
        
        # Создаем индексы
        for index_sql in indexes:
            db.execute_query(index_sql)
            logger.info("✅ Индекс создан/проверен")
            
        logger.info("🎉 Все таблицы и индексы успешно созданы!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при создании таблиц: {e}")
        return False

def create_test_data():
    """Создание тестовых данных (опционально)"""
    if not config.DEBUG:
        logger.info("⚠️  Тестовые данные создаются только в режиме DEBUG")
        return
    
    try:
        # Тестовый пользователь
        test_user = {
            'telegram_id': 123456789,
            'username': 'test_user',
            'first_name': 'Тестовый',
            'last_name': 'Пользователь',
            'gender': 'male',
            'age': 25,
            'weight': 75.5,
            'height': 180.0,
            'sport_type': 'бег',
            'goal': 'Подготовка к марафону'
        }
        
        # Проверяем, существует ли уже тестовый пользователь
        existing_user = db.get_user(test_user['telegram_id'])
        if not existing_user:
            user_id = db.create_user(test_user)
            logger.info(f"✅ Тестовый пользователь создан с ID: {user_id}")
        else:
            logger.info("⚠️  Тестовый пользователь уже существует")
            
    except Exception as e:
        logger.error(f"❌ Ошибка при создании тестовых данных: {e}")

def main():
    """Основная функция инициализации"""
    logger.info("🚀 Запуск инициализации базы данных...")
    
    try:
        # Подключаемся к базе данных
        db.connect()
        logger.info("✅ Подключение к базе данных установлено")
        
        # Создаем таблицы
        if create_tables():
            # Создаем тестовые данные (только в DEBUG режиме)
            if config.DEBUG:
                create_test_data()
            
            logger.info("🎉 Инициализация базы данных завершена успешно!")
        else:
            logger.error("❌ Инициализация базы данных завершена с ошибками")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при инициализации: {e}")
        sys.exit(1)
        
    finally:
        # Закрываем соединение с базой данных
        db.close()
        logger.info("✅ Соединение с базой данных закрыто")

if __name__ == "__main__":
    main()