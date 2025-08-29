#!/usr/bin/env python3
"""
Telegram Bot для AI диетолога 3.0
Генерирует персонализированные планы питания для спортсменов
Оптимизирован для развертывания на Amvera
"""

import logging
import os
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from handlers import (
    start, handle_main_menu, collect_parameters, 
    handle_training_interview, handle_activity_interview,
    view_plan_day, cancel, back_to_menu, error_handler,
    MAIN_MENU, COLLECTING_PARAMS, TRAINING_INTERVIEW, 
    ACTIVITY_INTERVIEW, VIEWING_PLAN, VIEWING_SAVED_PLANS
)
from config import config
from database import db

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def setup_application():
    """Настройка и конфигурация приложения Telegram"""
    
    # Создаем приложение Telegram
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # Создаем ConversationHandler для управления состояниями
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(handle_main_menu),
                CallbackQueryHandler(back_to_menu, pattern='^back_to_menu$')
            ],
            COLLECTING_PARAMS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, collect_parameters)
            ],
            TRAINING_INTERVIEW: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_training_interview)
            ],
            ACTIVITY_INTERVIEW: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_activity_interview)
            ],
            VIEWING_PLAN: [
                CallbackQueryHandler(view_plan_day, pattern='^day_'),
                CallbackQueryHandler(back_to_menu, pattern='^back_to_menu$')
            ],
            VIEWING_SAVED_PLANS: [
                CallbackQueryHandler(back_to_menu, pattern='^back_to_menu$')
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )
    
    # Добавляем обработчики
    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)
    
    return application

async def initialize_database():
    """Инициализация базы данных при запуске"""
    try:
        # Проверяем соединение с базой данных
        db.connect()
        logger.info("✅ База данных успешно подключена")
        
        # Можно добавить здесь автоматическое создание таблиц при необходимости
        # db.execute_query("CREATE TABLE IF NOT EXISTS ...")
        
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к базе данных: {e}")
        raise

def main():
    """Основная функция запуска бота"""
    
    # Проверка обязательных переменных окружения
    required_vars = ['BOT_TOKEN']
    missing_vars = [var for var in required_vars if not getattr(config, var)]
    
    if missing_vars:
        logger.error(f"Отсутствуют обязательные переменные окружения: {missing_vars}")
        logger.error("Установите переменные в панели управления Amvera:")
        logger.error("BOT_TOKEN - токен Telegram бота")
        logger.error("DEEPSEEK_API_KEY - ключ API DeepSeek")
        exit(1)
    
    try:
        # Инициализация базы данных
        initialize_database()
        
        # Настройка приложения
        application = setup_application()
        
        # Запуск бота в зависимости от режима
        if config.IS_PRODUCTION:
            # Режим webhook для Amvera
            logger.info("🚀 Запуск в режиме webhook на Amvera")
            
            # Amvera автоматически предоставляет порт через переменную PORT
            port = int(os.getenv('PORT', 8080))
            
            application.run_webhook(
                listen="0.0.0.0",
                port=port,
                url_path=config.BOT_TOKEN,
                webhook_url=config.WEBHOOK_URL,
                drop_pending_updates=True
            )
        else:
            # Режим polling для локальной разработки
            logger.info("🔧 Запуск в режиме polling для разработки")
            application.run_polling(
                drop_pending_updates=True,
                allowed_updates=['message', 'callback_query']
            )
            
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")
        # Закрываем соединение с базой данных при ошибке
        try:
            db.close()
        except:
            pass
        exit(1)

if __name__ == '__main__':
    main()