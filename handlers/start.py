from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from database import Database
from keyboards import get_main_menu
import re
import logging

router = Router()
logger = logging.getLogger(__name__)

# Ленивая инициализация базы данных
_db_instance = None

def get_db():
    global _db_instance
    if _db_instance is None:
        try:
            _db_instance = Database()
        except Exception as e:
            logger.error(f"Ошибка при создании экземпляра базы данных: {e}", exc_info=True)
            raise
    return _db_instance


@router.message(Command("start"))
async def cmd_start(message: Message):
    try:
        db = get_db()
        user_id = message.from_user.id
        username = message.from_user.username or ""
        first_name = message.from_user.first_name or ""
        
        logger.info(f"Обработка /start для пользователя {user_id}")
        
        # Проверяем реферальную ссылку
        referrer_id = None
        if message.text and len(message.text.split()) > 1:
            try:
                ref_code = message.text.split()[1]
                referrer_id = int(ref_code)
                # Проверяем, что реферер существует и это не сам пользователь
                if referrer_id == user_id:
                    referrer_id = None
                else:
                    ref_user = db.get_user(referrer_id)
                    if not ref_user:
                        referrer_id = None
            except (ValueError, IndexError) as e:
                logger.warning(f"Ошибка при обработке реферального кода: {e}")
                referrer_id = None
        
        # Создаем пользователя, если его нет
        try:
            user = db.get_user(user_id)
            if not user:
                logger.info(f"Создание нового пользователя {user_id}")
                db.create_user(user_id, username, first_name, referrer_id)
                user = db.get_user(user_id)
        except Exception as e:
            logger.error(f"Ошибка при работе с пользователем: {e}", exc_info=True)
            # Продолжаем работу даже если есть ошибка
        
        welcome_text = (
            "👋 Добро пожаловать!\n\n"
            "Это бот для заработка Rcoin через выполнение заданий.\n\n"
            "Выберите действие в меню:"
        )
        
        try:
            keyboard = get_main_menu()
            await message.answer(welcome_text, reply_markup=keyboard)
            logger.info(f"Приветственное сообщение отправлено пользователю {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {e}", exc_info=True)
            # Пробуем отправить без клавиатуры
            try:
                await message.answer(welcome_text)
            except Exception as e2:
                logger.error(f"Критическая ошибка при отправке сообщения: {e2}", exc_info=True)
                raise
                
    except Exception as e:
        logger.error(f"Критическая ошибка в cmd_start: {e}", exc_info=True)
        try:
            await message.answer("Произошла ошибка. Попробуйте позже или отправьте /start еще раз.")
        except Exception as e2:
            logger.error(f"Не удалось отправить сообщение об ошибке: {e2}", exc_info=True)


@router.message(F.text == "👤 Личный кабинет")
async def show_profile(message: Message):
    try:
        db = get_db()
        user_id = message.from_user.id
        username = message.from_user.username or ""
        first_name = message.from_user.first_name or ""
        
        user = db.get_user(user_id)
        
        # Создаем пользователя, если его нет
        if not user:
            logger.info(f"Создание пользователя {user_id} из личного кабинета")
            db.create_user(user_id, username, first_name, None)
            user = db.get_user(user_id)
            if not user:
                await message.answer("Ошибка: не удалось создать пользователя.")
                return
        
        referrer_id = user.get('referrer_id')
        referrer_name = "Нет"
        if referrer_id:
            try:
                referrer = db.get_user(referrer_id)
                if referrer:
                    referrer_name = f"@{referrer.get('username', '')}" if referrer.get('username') else f"ID: {referrer_id}"
            except:
                pass
        
        try:
            invited_count = db.get_invited_count(user_id)
        except:
            invited_count = 0
        
        try:
            friends_referrals = db.get_friends_referrals_count(user_id)
        except:
            friends_referrals = 0
    
        # Безопасное получение значений с проверкой на None
        balance = user.get('balance')
        if balance is None:
            balance = 0.0
        else:
            try:
                balance = float(balance)
            except:
                balance = 0.0
        
        withdrawn = user.get('withdrawn')
        if withdrawn is None:
            withdrawn = 0.0
        else:
            try:
                withdrawn = float(withdrawn)
            except:
                withdrawn = 0.0
        
        profile_text = (
            f"👤 Личный кабинет\n\n"
            f"📝 Имя: {user.get('first_name', first_name) or first_name}\n"
            f"🆔 ID: {user_id}\n"
            f"📭 На вывод: {balance:.2f}R\n"
            f"📤 Вывел: {withdrawn:.2f}R\n"
            f"👥 Вас привел: {referrer_name}\n"
            f"💸 Вы пригласили: {invited_count}\n"
        )
        
        from keyboards import get_profile_keyboard
        await message.answer(profile_text, reply_markup=get_profile_keyboard(balance))
    except Exception as e:
        logger.error(f"Ошибка в show_profile: {e}", exc_info=True)
        await message.answer("Произошла ошибка при загрузке профиля.")


@router.message(F.text == "💰 Начать зарабатывать")
async def show_earn_menu(message: Message):
    try:
        db = get_db()
        user_id = message.from_user.id
        username = message.from_user.username or ""
        first_name = message.from_user.first_name or ""
        
        # Создаем пользователя, если его нет
        user = db.get_user(user_id)
        if not user:
            logger.info(f"Создание пользователя {user_id} из меню заработка")
            db.create_user(user_id, username, first_name, None)
        
        from keyboards import get_earn_menu_keyboard
        keyboard = get_earn_menu_keyboard(user_id)
        
        text = "💰 Выберите способ заработка:"
        await message.answer(text, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в show_earn_menu: {e}", exc_info=True)
        await message.answer("Произошла ошибка. Попробуйте позже.")


@router.message(F.text == "🎁 Открыть сундук")
async def show_chest(message: Message):
    try:
        db = get_db()
        user_id = message.from_user.id
        username = message.from_user.username or ""
        first_name = message.from_user.first_name or ""
        
        user = db.get_user(user_id)
        
        # Создаем пользователя, если его нет
        if not user:
            logger.info(f"Создание пользователя {user_id} из сундука")
            db.create_user(user_id, username, first_name, None)
            user = db.get_user(user_id)
            if not user:
                await message.answer("Ошибка: не удалось создать пользователя.")
                return
        
        from keyboards import get_chest_keyboard
        balance = user.get('balance', 0.0)
        text = (
            "🎁 Открыть сундук с подарком\n\n"
            f"Стоимость: 2000R\n"
            f"Ваш баланс: {balance:.2f}R"
        )
        await message.answer(text, reply_markup=get_chest_keyboard(balance))
    except Exception as e:
        logger.error(f"Ошибка в show_chest: {e}", exc_info=True)
        await message.answer("Произошла ошибка.")


@router.message(F.text == "👥 Реферальная программа")
async def show_referral_program(message: Message):
    try:
        db = get_db()
        user_id = message.from_user.id
        user = db.get_user(user_id)
        
        if not user:
            await message.answer("Ошибка: пользователь не найден.")
            return
        
        invited_count = db.get_invited_count(user_id)
        friends_referrals = db.get_friends_referrals_count(user_id)
        
        referral_link = f"https://t.me/{(await message.bot.get_me()).username}?start={user_id}"
        
        # Получаем награды за рефералов из БД
        referral_reward = int(float(db.get_setting('referral_reward', '350')))
        friend_referral_reward = int(float(db.get_setting('friend_referral_reward', '100')))
        
        text = (
            "👥 Реферальная программа\n\n"
            f"🔗 Ваша реферальная ссылка:\n{referral_link}\n\n"
            f"📊 Статистика:\n"
            f"• Приглашено друзей: {invited_count}\n"
            f"• Рефералы друзей: {friends_referrals}\n\n"
            f"💰 Награды:\n"
            f"• 1 реферал = {referral_reward}R\n"
            f"• Рефералы друзей = {friend_referral_reward}R\n\n"
            f"ℹ️ Рефералом считается пользователь, который нажал 'Начать зарабатывать' и выполнил 1 задание."
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_main_menu")]
        ])
        
        await message.answer(text, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в show_referral_program: {e}", exc_info=True)
        await message.answer("Произошла ошибка.")


@router.message(F.text == "📊 Статистика проекта")
async def show_statistics(message: Message):
    try:
        from config import STATS_BASE_USERS, STATS_BOT_CREATED, STATS_BASE_WITHDRAWN
        db = get_db()
        stats = db.get_statistics()
        
        # Прибавляем реальное количество пользователей к базовому
        total_users = STATS_BASE_USERS + stats['total_users']
        
        text = (
            "📊 Статистика проекта\n\n"
            f"💰 Всего пользователей: {total_users}\n"
            f"✅ Бот создан: {STATS_BOT_CREATED}\n"
            f"🔗 Выплачено всего: {STATS_BASE_WITHDRAWN}RUB"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_main_menu")]
        ])
        
        await message.answer(text, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в show_statistics: {e}", exc_info=True)
        await message.answer("Произошла ошибка при загрузке статистики.")


# Обработчик неизвестных сообщений - должен быть последним
# НЕ обрабатывает сообщения в FSM состояниях (они обрабатываются в callbacks.py)
@router.message()
async def handle_unknown(message: Message):
    """Обработчик неизвестных сообщений"""
    # Проверяем только известные команды меню
    # Все остальные сообщения могут быть частью FSM - не обрабатываем их здесь
    known_commands = [
        "👤 Личный кабинет",
        "💰 Начать зарабатывать", 
        "🎁 Открыть сундук",
        "👥 Реферальная программа",
        "📊 Статистика проекта"
    ]
    
    if message.text in known_commands:
        # Это должно было обработаться другими обработчиками
        # Если дошло сюда - значит что-то не так
        await message.answer(
            "Я не понимаю эту команду. Используйте кнопки меню или отправьте /start"
        )
    # Если сообщение не в списке известных команд - это может быть ответ в FSM
    # Пропускаем его, чтобы обработали FSM обработчики в callbacks.py

