"""
Конфигурация приложения для AI диетолога 3.0
Поддержка как локальной разработки, так и развертывания на Amvera
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    """Конфигурация приложения"""
    
    # Основные настройки
    BOT_TOKEN: str = os.getenv('BOT_TOKEN', '')
    DEEPSEEK_API_KEY: str = os.getenv('DEEPSEEK_API_KEY', '')
    
    # Настройки базы данных
    DB_HOST: str = os.getenv('DB_HOST', 'localhost')
    DB_PORT: int = int(os.getenv('DB_PORT', '5432'))
    DB_NAME: str = os.getenv('DB_NAME', 'ai_diet_bot')
    DB_USER: str = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD: str = os.getenv('DB_PASSWORD', '')
    
    # Настройки вебхука для Amvera
    WEBHOOK_URL: str = os.getenv('WEBHOOK_URL', '')
    WEBHOOK_PATH: str = f"/webhook/{BOT_TOKEN}" if BOT_TOKEN else "/webhook"
    
    # Флаги окружения
    IS_PRODUCTION: bool = os.getenv('ENVIRONMENT', 'development').lower() == 'production'
    DEBUG: bool = os.getenv('DEBUG', 'false').lower() == 'true'
    
    # Настройки LLM
    DEEPSEEK_MODEL: str = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
    DEEPSEEK_BASE_URL: str = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
    DEEPSEEK_TEMPERATURE: float = float(os.getenv('DEEPSEEK_TEMPERATURE', '0.7'))
    DEEPSEEK_MAX_TOKENS: int = int(os.getenv('DEEPSEEK_MAX_TOKENS', '4000'))
    
    # Настройки бота
    ADMIN_USER_ID: int = int(os.getenv('ADMIN_USER_ID', '0'))
    SUPPORT_CHAT_ID: str = os.getenv('SUPPORT_CHAT_ID', '')
    
    # Настройки логирования
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    @property
    def database_url(self) -> str:
        """Получить URL подключения к базе данных"""
        if self.IS_PRODUCTION and os.getenv('DATABASE_URL'):
            # Используем предоставленный Amvera DATABASE_URL
            return os.getenv('DATABASE_URL')
        
        # Локальное подключение
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def is_valid(self) -> bool:
        """Проверить валидность конфигурации"""
        return bool(self.BOT_TOKEN and self.DEEPSEEK_API_KEY)
    
    def validate(self) -> None:
        """Валидация конфигурации"""
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не установлен")
        if not self.DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY не установлен")
        
        # Предупреждения для разработки
        if not self.IS_PRODUCTION:
            if not self.DB_PASSWORD:
                print("⚠️  DB_PASSWORD не установлен (разработка)")
            if self.DB_HOST == 'localhost':
                print("⚠️  Используется локальная база данных (разработка)")

# Глобальный экземпляр конфигурации
config = Config()

# Автоматическая валидация при импорте
try:
    config.validate()
except ValueError as e:
    if config.IS_PRODUCTION:
        raise
    else:
        print(f"⚠️  Конфигурационное предупреждение: {e}")