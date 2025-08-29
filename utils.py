"""
Вспомогательные функции для Telegram бота AI диетолога
Утилиты для клавиатур, форматирования и валидации
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict, Optional
from datetime import datetime, date
import re

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура главного меню"""
    keyboard = [
        [InlineKeyboardButton("🍽 Создать план питания", callback_data="generate_plan")],
        [InlineKeyboardButton("📋 Мои планы", callback_data="view_saved_plans")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def view_plan_keyboard(plan_id: int, current_day: int, total_days: int = 7) -> InlineKeyboardMarkup:
    """Клавиатура для навигации по дням плана питания"""
    keyboard = []
    
    # Кнопки навигации по дням
    nav_buttons = []
    if current_day > 1:
        nav_buttons.append(InlineKeyboardButton("◀️ Предыдущий", callback_data=f"day_{plan_id}_{current_day-1}"))
    
    nav_buttons.append(InlineKeyboardButton(f"День {current_day}", callback_data=f"day_info_{current_day}"))
    
    if current_day < total_days:
        nav_buttons.append(InlineKeyboardButton("Следующий ▶️", callback_data=f"day_{plan_id}_{current_day+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Дополнительные кнопки
    keyboard.extend([
        [InlineKeyboardButton("💾 Сохранить план", callback_data=f"save_plan_{plan_id}")],
        [InlineKeyboardButton("📊 Общая статистика", callback_data=f"stats_{plan_id}")],
        [InlineKeyboardButton("← Назад в меню", callback_data="back_to_menu")]
    ])
    
    return InlineKeyboardMarkup(keyboard)

def format_meal_plan_day(plan_data: Dict, day_number: int) -> str:
    """Форматирование дня плана питания для отображения"""
    if 'days' not in plan_data or day_number < 1 or day_number > len(plan_data['days']):
        return "❌ Информация о дне плана не найдена"
    
    day_info = plan_data['days'][day_number - 1]
    response = f"📋 *День {day_number}* • {day_info.get('date', '')}\n\n"
    
    # Тренировочное расписание
    if day_info.get('training_schedule'):
        response += f"🏋️ *Тренировка:* {day_info['training_schedule']}\n\n"
    
    # Приемы пищи
    response += "🍽 *Питание:*\n"
    for meal in day_info.get('meals', []):
        response += f"\n*{meal['meal_type'].capitalize()}* ({meal['time']})\n"
        
        for item in meal.get('food_items', []):
            response += f"• {item['name']} - {item['portion']}\n"
            
            # Пищевая ценность
            nutrients = []
            if item.get('calories'):
                nutrients.append(f"{item['calories']} ккал")
            if item.get('protein'):
                nutrients.append(f"Б: {item['protein']}г")
            if item.get('carbs'):
                nutrients.append(f"У: {item['carbs']}г")
            if item.get('fat'):
                nutrients.append(f"Ж: {item['fat']}г")
                
            if nutrients:
                response += f"  ({', '.join(nutrients)})\n"
        
        # Итоги по приему пищи
        if meal.get('total_calories'):
            response += f"\n*Итого:* {meal['total_calories']} ккал"
            if meal.get('total_protein'):
                response += f" (Б: {meal['total_protein']}г"
            if meal.get('total_carbs'):
                response += f", У: {meal['total_carbs']}г"
            if meal.get('total_fat'):
                response += f", Ж: {meal['total_fat']}г"
            response += ")\n"
        
        # Рекомендации
        if meal.get('recommendations'):
            response += f"💡 *Рекомендации:* {meal['recommendations']}\n"
    
    # Гидратация
    if day_info.get('hydration'):
        response += f"\n💧 *Гидратация:* {day_info['hydration']}\n"
    
    # Общие рекомендации дня
    if day_info.get('general_recommendations'):
        response += f"\n🌟 *Рекомендации на день:* {day_info['general_recommendations']}\n"
    
    return response

def format_plan_stats(plan_data: Dict) -> str:
    """Форматирование статистики плана питания"""
    response = "📊 *Общая статистика плана:*\n\n"
    
    if plan_data.get('total_calories'):
        response += f"• *Калории:* {plan_data['total_calories']} ккал/день\n"
    if plan_data.get('protein_grams'):
        response += f"• *Белки:* {plan_data['protein_grams']} г/день\n"
    if plan_data.get('carbs_grams'):
        response += f"• *Углеводы:* {plan_data['carbs_grams']} г/день\n"
    if plan_data.get('fat_grams'):
        response += f"• *Жиры:* {plan_data['fat_grams']} г/день\n"
    
    # Расчет макросов в процентах
    if all([plan_data.get('protein_grams'), plan_data.get('carbs_grams'), plan_data.get('fat_grams')]):
        total_grams = plan_data['protein_grams'] + plan_data['carbs_grams'] + plan_data['fat_grams']
        if total_grams > 0:
            protein_pct = (plan_data['protein_grams'] * 4 / (plan_data['protein_grams'] * 4 + plan_data['carbs_grams'] * 4 + plan_data['fat_grams'] * 9)) * 100
            carbs_pct = (plan_data['carbs_grams'] * 4 / (plan_data['protein_grams'] * 4 + plan_data['carbs_grams'] * 4 + plan_data['fat_grams'] * 9)) * 100
            fat_pct = (plan_data['fat_grams'] * 9 / (plan_data['protein_grams'] * 4 + plan_data['carbs_grams'] * 4 + plan_data['fat_grams'] * 9)) * 100
            
            response += f"\n*Распределение макросов:*\n"
            response += f"• Белки: {protein_pct:.1f}%\n"
            response += f"• Углеводы: {carbs_pct:.1f}%\n"
            response += f"• Жиры: {fat_pct:.1f}%\n"
    
    # Общие рекомендации
    if plan_data.get('general_recommendations'):
        response += f"\n🌟 *Общие рекомендации:*\n{plan_data['general_recommendations']}\n"
    
    # Список покупок
    if plan_data.get('shopping_list'):
        response += f"\n🛒 *Список покупок:*\n"
        for i, item in enumerate(plan_data['shopping_list'][:10], 1):  # Первые 10 items
            response += f"{i}. {item}\n"
        if len(plan_data['shopping_list']) > 10:
            response += f"... и еще {len(plan_data['shopping_list']) - 10} позиций\n"
    
    return response

def validate_date(date_str: str) -> Optional[date]:
    """Валидация даты в формате ДД.ММ.ГГГГ"""
    try:
        return datetime.strptime(date_str, '%d.%m.%Y').date()
    except ValueError:
        return None

def validate_number(input_str: str, min_val: float = None, max_val: float = None) -> Optional[float]:
    """Валидация числового ввода"""
    try:
        num = float(input_str.replace(',', '.'))
        if min_val is not None and num < min_val:
            return None
        if max_val is not None and num > max_val:
            return None
        return num
    except ValueError:
        return None

def validate_gender(gender_str: str) -> Optional[str]:
    """Валидация ввода пола"""
    gender = gender_str.lower()
    if gender in ['мужской', 'муж', 'm', 'male']:
        return 'male'
    elif gender in ['женский', 'жен', 'f', 'female']:
        return 'female'
    return None

def escape_markdown(text: str) -> str:
    """Экранирование символов Markdown для Telegram"""
    if not text:
        return text
        
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def format_user_profile(user_data: Dict) -> str:
    """Форматирование профиля пользователя"""
    profile = "👤 *Твой профиль:*\n\n"
    
    if user_data.get('first_name'):
        profile += f"• *Имя:* {escape_markdown(user_data['first_name'])}\n"
    if user_data.get('age'):
        profile += f"• *Возраст:* {user_data['age']} лет\n"
    if user_data.get('gender'):
        gender = "Мужской" if user_data['gender'] == 'male' else "Женский"
        profile += f"• *Пол:* {gender}\n"
    if user_data.get('weight'):
        profile += f"• *Вес:* {user_data['weight']} кг\n"
    if user_data.get('height'):
        profile += f"• *Рост:* {user_data['height']} см\n"
    if user_data.get('sport_type'):
        profile += f"• *Вид спорта:* {escape_markdown(user_data['sport_type'])}\n"
    if user_data.get('goal'):
        profile += f"• *Цель:* {escape_markdown(user_data['goal'])}\n"
    if user_data.get('competition_date'):
        profile += f"• *Соревнования:* {user_data['competition_date'].strftime('%d.%m.%Y')}\n"
    
    profile += f"\n📅 *Зарегистрирован:* {user_data.get('created_at', datetime.now()).strftime('%d.%m.%Y')}"
    
    return profile