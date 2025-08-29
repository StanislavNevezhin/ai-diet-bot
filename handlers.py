"""
Обработчики команд и состояний для Telegram бота AI диетолога
Реализует всю логику согласно Sequence Diagram
"""

import logging
import json
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from typing import Dict, List, Optional, Tuple

from config import config
from database import db
from llm_integration import llm

logger = logging.getLogger(__name__)

# Состояния ConversationHandler
MAIN_MENU, COLLECTING_PARAMS, TRAINING_INTERVIEW, ACTIVITY_INTERVIEW, VIEWING_PLAN, VIEWING_SAVED_PLANS = range(6)

# Глобальные переменные для хранения данных интервью
user_interview_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /start"""
    user = update.effective_user
    logger.info(f"👤 Пользователь {user.id} начал работу с ботом")
    
    # Проверяем, есть ли пользователь в базе
    existing_user = db.get_user(user.id)
    
    if existing_user:
        # Пользователь уже существует - показываем главное меню
        welcome_text = f"С возвращением, {user.first_name}! 🏋️‍♂️\n\nГотовы продолжить работу над вашим питанием?"
        await update.message.reply_text(welcome_text, reply_markup=main_menu_keyboard())
        return MAIN_MENU
    else:
        # Новый пользователь - начинаем сбор параметров
        welcome_text = (
            f"Привет, {user.first_name}! 👋\n\n"
            "Я - AI диетолог 3.0, твой персональный помощник в создании "
            "идеального плана питания для спортивных достижений! 🥇\n\n"
            "Для начала, давай познакомимся поближе. Ответь на несколько вопросов о себе:"
        )
        await update.message.reply_text(welcome_text)
        
        # Запрашиваем первый параметр
        await update.message.reply_text("🚀 Какой у тебя вид спорта? (например: бег, плавание, футбол)")
        return COLLECTING_PARAMS

async def collect_parameters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сбор основных параметров пользователя"""
    user = update.effective_user
    user_data = context.user_data.setdefault('user_data', {})
    
    # Определяем, какой параметр собираем
    current_step = user_data.get('current_step', 'sport_type')
    
    if current_step == 'sport_type':
        user_data['sport_type'] = update.message.text
        user_data['current_step'] = 'gender'
        await update.message.reply_text("👫 Укажи свой пол (мужской/женский):")
        
    elif current_step == 'gender':
        gender = update.message.text.lower()
        if gender in ['мужской', 'муж', 'm']:
            user_data['gender'] = 'male'
        elif gender in ['женский', 'жен', 'f']:
            user_data['gender'] = 'female'
        else:
            await update.message.reply_text("Пожалуйста, укажи 'мужской' или 'женский':")
            return COLLECTING_PARAMS
        
        user_data['current_step'] = 'age'
        await update.message.reply_text("🎂 Сколько тебе лет?")
        
    elif current_step == 'age':
        try:
            age = int(update.message.text)
            if 10 <= age <= 100:
                user_data['age'] = age
                user_data['current_step'] = 'weight'
                await update.message.reply_text("⚖️ Какой у тебя текущий вес (в кг)?")
            else:
                await update.message.reply_text("Пожалуйста, укажи возраст от 10 до 100 лет:")
        except ValueError:
            await update.message.reply_text("Пожалуйста, укажи возраст числом:")
            
    elif current_step == 'weight':
        try:
            weight = float(update.message.text.replace(',', '.'))
            if 30 <= weight <= 200:
                user_data['weight'] = weight
                user_data['current_step'] = 'height'
                await update.message.reply_text("📏 Какой у тебя рост (в см)?")
            else:
                await update.message.reply_text("Пожалуйста, укажи вес от 30 до 200 кг:")
        except ValueError:
            await update.message.reply_text("Пожалуйста, укажи вес числом (например: 75.5):")
            
    elif current_step == 'height':
        try:
            height = float(update.message.text)
            if 100 <= height <= 250:
                user_data['height'] = height
                user_data['current_step'] = 'goal'
                await update.message.reply_text(
                    "🎯 Какая у тебя цель?\n"
                    "• Набор мышечной массы 💪\n"
                    "• Снижение веса 🏃‍♂️\n"
                    "• Поддержание формы ⚖️\n"
                    "• Подготовка к соревнованиям 🏆"
                )
            else:
                await update.message.reply_text("Пожалуйста, укажи рост от 100 до 250 см:")
        except ValueError:
            await update.message.reply_text("Пожалуйста, укажи рост числом:")
            
    elif current_step == 'goal':
        user_data['goal'] = update.message.text
        user_data['current_step'] = 'competition_date'
        await update.message.reply_text(
            "📅 Есть ли у тебя важные соревнования? Если да, укажи дату (в формате ДД.ММ.ГГГГ), "
            "или напиши 'нет' если соревнований нет:"
        )
        
    elif current_step == 'competition_date':
        text = update.message.text.lower()
        if text == 'нет':
            user_data['competition_date'] = None
            # Завершаем сбор параметров
            return await finish_parameter_collection(update, context, user_data)
        else:
            try:
                comp_date = datetime.strptime(text, '%d.%m.%Y').date()
                if db.validate_competition_date(comp_date):
                    user_data['competition_date'] = comp_date
                    return await finish_parameter_collection(update, context, user_data)
                else:
                    await update.message.reply_text("Дата соревнований должна быть в будущем. Укажи корректную дату:")
            except ValueError:
                await update.message.reply_text("Пожалуйста, укажи дату в формате ДД.ММ.ГГГГ или 'нет':")
    
    return COLLECTING_PARAMS

async def finish_parameter_collection(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: Dict) -> int:
    """Завершение сбора параметров и сохранение пользователя"""
    user = update.effective_user
    
    # Сохраняем пользователя в базу
    user_data['telegram_id'] = user.id
    user_data['username'] = user.username
    user_data['first_name'] = user.first_name
    user_data['last_name'] = user.last_name
    
    try:
        user_id = db.create_user(user_data)
        logger.info(f"✅ Пользователь {user.id} сохранен в базу с ID {user_id}")
        
        # Очищаем временные данные
        context.user_data.pop('user_data', None)
        
        await update.message.reply_text(
            "🎉 Отлично! Основная информация сохранена.\n\n"
            "Теперь давай создадим твой персональный план питания!",
            reply_markup=main_menu_keyboard()
        )
        
        return MAIN_MENU
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения пользователя: {e}")
        await update.message.reply_text(
            "😕 Произошла ошибка при сохранении данных. Попробуй начать заново с /start"
        )
        return ConversationHandler.END

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик главного меню"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    choice = query.data
    
    if choice == 'generate_plan':
        # Начинаем процесс генерации плана
        await query.edit_message_text(
            "🔍 Для создания идеального плана питания мне нужно узнать немного больше о твоих тренировках и образе жизни.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Начать интервью 🏋️‍♂️", callback_data="start_interview")]
            ])
        )
        
    elif choice == 'start_interview':
        # Запускаем интервью о тренировках
        user_data = db.get_user(user.id)
        if not user_data:
            await query.edit_message_text("Сначала нужно заполнить основную информацию. Напиши /start")
            return ConversationHandler.END
        
        # Генерируем вопросы для интервью
        questions = await llm.generate_interview_questions(user_data, 'training')
        if questions:
            user_interview_data[user.id] = {
                'training': {'questions': questions, 'current_question': 0, 'answers': {}},
                'activity': {'questions': [], 'current_question': 0, 'answers': {}}
            }
            
            await ask_next_question(query, user.id, 'training')
            return TRAINING_INTERVIEW
        else:
            await query.edit_message_text("😕 Не удалось сгенерировать вопросы. Попробуй позже.")
            return MAIN_MENU
            
    elif choice == 'view_saved_plans':
        # Показываем сохраненные планы
        plans = db.get_user_plans(user.id)
        if plans:
            keyboard = []
            for plan in plans[:5]:  # Показываем последние 5 планов
                plan_date = plan['created_at'].strftime('%d.%m.%Y')
                keyboard.append([
                    InlineKeyboardButton(
                        f"План от {plan_date} ({plan['plan_type']})", 
                        callback_data=f"view_plan_{plan['id']}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("← Назад", callback_data="back_to_menu")])
            
            await query.edit_message_text(
                "📋 Твои сохраненные планы питания:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return VIEWING_SAVED_PLANS
        else:
            await query.edit_message_text(
                "У тебя пока нет сохраненных планов питания. Создай первый план!",
                reply_markup=main_menu_keyboard()
            )
            return MAIN_MENU
            
    elif choice == 'cancel':
        return await cancel(update, context)
    
    return MAIN_MENU

async def handle_training_interview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик интервью о тренировках"""
    user = update.effective_user
    answer = update.message.text
    
    if user.id not in user_interview_data:
        await update.message.reply_text("Интервью прервано. Начни заново с /start")
        return ConversationHandler.END
    
    # Сохраняем ответ
    interview_data = user_interview_data[user.id]['training']
    current_q = interview_data['current_question']
    interview_data['answers'][f"q{current_q + 1}"] = answer
    
    # Переходим к следующему вопросу или завершаем
    interview_data['current_question'] += 1
    
    if interview_data['current_question'] < len(interview_data['questions']):
        await ask_next_question_from_message(update, user.id, 'training')
        return TRAINING_INTERVIEW
    else:
        # Завершаем тренировочное интервью и начинаем интервью об активности
        await update.message.reply_text(
            "✅ Отлично! Теперь давай поговорим о твоем образе жизни и повседневной активности.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Продолжить интервью 🚶‍♂️", callback_data="continue_activity_interview")]
            ])
        )
        return MAIN_MENU

async def handle_activity_interview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик интервью об активности"""
    user = update.effective_user
    answer = update.message.text
    
    if user.id not in user_interview_data:
        await update.message.reply_text("Интервью прервано. Начни заново с /start")
        return ConversationHandler.END
    
    # Сохраняем ответ
    interview_data = user_interview_data[user.id]['activity']
    current_q = interview_data['current_question']
    interview_data['answers'][f"q{current_q + 1}"] = answer
    
    # Переходим к следующему вопросу или завершаем
    interview_data['current_question'] += 1
    
    if interview_data['current_question'] < len(interview_data['questions']):
        await ask_next_question_from_message(update, user.id, 'activity')
        return ACTIVITY_INTERVIEW
    else:
        # Завершаем оба интервью и генерируем план
        return await generate_meal_plan(update, context, user.id)

async def generate_meal_plan(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> int:
    """Генерация плана питания после завершения интервью"""
    try:
        user_data = db.get_user(user_id)
        interview_data = user_interview_data.get(user_id, {})
        
        # Генерируем план питания
        meal_plan = await llm.generate_meal_plan(user_data, interview_data)
        
        if meal_plan:
            # Сохраняем план в базу
            plan_id = db.save_meal_plan(user_id, meal_plan)
            
            # Сохраняем интервью как активность
            db.save_activity(user_id, 'interview_completed', interview_data)
            
            # Очищаем временные данные
            user_interview_data.pop(user_id, None)
            
            # Показываем успех и первый день плана
            if isinstance(update, Update) and update.message:
                await update.message.reply_text(
                    "🎉 Твой персональный план питания готов!\n\n"
                    "Теперь ты можешь просматривать его по дням и сохранять для будущего использования.",
                    reply_markup=view_plan_keyboard(plan_id, 1)
                )
            else:
                # Если это callback query
                query = update.callback_query
                await query.edit_message_text(
                    "🎉 Твой персональный план питания готов!\n\n"
                    "Теперь ты можешь просматривать его по дням и сохранять для будущего использования.",
                    reply_markup=view_plan_keyboard(plan_id, 1)
                )
            
            return VIEWING_PLAN
            
        else:
            error_msg = "😕 Не удалось сгенерировать план питания. Попробуй позже."
            if isinstance(update, Update) and update.message:
                await update.message.reply_text(error_msg, reply_markup=main_menu_keyboard())
            else:
                query = update.callback_query
                await query.edit_message_text(error_msg, reply_markup=main_menu_keyboard())
            return MAIN_MENU
            
    except Exception as e:
        logger.error(f"❌ Ошибка генерации плана питания: {e}")
        error_msg = "😕 Произошла ошибка при генерации плана. Попробуй позже."
        if isinstance(update, Update) and update.message:
            await update.message.reply_text(error_msg, reply_markup=main_menu_keyboard())
        else:
            query = update.callback_query
            await query.edit_message_text(error_msg, reply_markup=main_menu_keyboard())
        return MAIN_MENU

async def view_plan_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Просмотр конкретного дня плана питания"""
    query = update.callback_query
    await query.answer()
    
    # Извлекаем ID плана и номер дня из callback_data
    callback_data = query.data
    if callback_data.startswith('day_'):
        parts = callback_data.split('_')
        if len(parts) >= 3:
            plan_id = int(parts[1])
            day_number = int(parts[2])
            
            # Здесь будет логика отображения конкретного дня плана
            # Для простоты просто показываем номер дня
            await query.edit_message_text(
                f"📋 День {day_number} твоего плана питания\n\n"
                "Здесь будет детальная информация о питании на этот день...",
                reply_markup=view_plan_keyboard(plan_id, day_number)
            )
    
    return VIEWING_PLAN

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /cancel"""
    user = update.effective_user
    logger.info(f"❌ Пользователь {user.id} отменил операцию")
    
    # Очищаем временные данные
    context.user_data.clear()
    user_interview_data.pop(user.id, None)
    
    await update.message.reply_text(
        "Операция отменена. Если захочешь начать заново - напиши /start",
        reply_markup=main_menu_keyboard()
    )
    return ConversationHandler