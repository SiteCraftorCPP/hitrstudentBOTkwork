from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from database import Database

_db_instance = None

def get_db():
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


def get_main_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Личный кабинет")],
            [KeyboardButton(text="💰 Начать зарабатывать")],
            [KeyboardButton(text="👥 Реферальная программа")],
            [KeyboardButton(text="📊 Статистика проекта")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_profile_keyboard(balance: float):
    buttons = []
    # Кнопка "Вывод" всегда показывается
    buttons.append([InlineKeyboardButton(text="💸 Вывод", callback_data="withdraw")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_main_menu")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_withdraw_keyboard(balance: float = 0.0):
    buttons = []
    # Кнопка "Далее" показывается только если баланс >= 5000
    if balance >= 5000:
        buttons.append([InlineKeyboardButton(text="✅ Далее", callback_data="withdraw_amount")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_profile")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_withdraw_methods_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Другой способ", callback_data="withdraw_site")],
        [InlineKeyboardButton(text="💎 USDT (BEP20)", callback_data="withdraw_usdt")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_withdraw_start")]
    ])
    return keyboard


def get_earn_menu_keyboard(user_id: int):
    import logging
    logger = logging.getLogger(__name__)
    
    buttons = []
    
    try:
        db = get_db()
        # Ежедневный бонус - всегда показываем кнопку
        buttons.append([InlineKeyboardButton(text="🎁 Ежедневный бонус до 1000R", callback_data="daily_bonus")])
        
        # Задания из базы данных
        tasks = db.get_tasks()
        for task in tasks:
            try:
                if task['task_type'] == 'subscribe':
                    # Кнопка подписки ВСЕГДА показывается, независимо от выполнения
                    # Убираем "Подписаться на" из названия, если оно уже есть
                    title = task['title']
                    if title.startswith('Подписаться на '):
                        title = title.replace('Подписаться на ', '')
                    buttons.append([InlineKeyboardButton(
                        text=f"📢 Подписаться на {title} + {int(task['reward'])} R",
                        callback_data=f"task_{task['task_id']}"
                    )])
                elif task['task_type'] == 'info':
                    # Кнопка для заданий типа 'info' ВСЕГДА показывается, независимо от выполнения
                    # Используем настройку из БД для названия кнопки
                    button_text = db.get_setting('streams_button_text', f"💰 Зарабатывай на просмотре стримов... + {int(task['reward'])}R")
                    # Если в настройке нет награды, добавляем её
                    if f"+ {int(task['reward'])}R" not in button_text:
                        button_text = f"{button_text} + {int(task['reward'])}R"
                    buttons.append([InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"task_{task['task_id']}"
                    )])
                elif task['task_type'] == 'custom':
                    # Кнопка кастомного задания ВСЕГДА показывается, независимо от выполнения
                    buttons.append([InlineKeyboardButton(
                        text=task['title'],
                        callback_data=f"task_{task['task_id']}"
                    )])
            except Exception as e:
                logger.error(f"Ошибка при обработке задания {task.get('task_id', 'unknown')}: {e}")
                continue
    except Exception as e:
        logger.error(f"Ошибка в get_earn_menu_keyboard: {e}", exc_info=True)
    
    # Пригласить друга - используем награду из БД
    referral_reward = int(float(db.get_setting('referral_reward', '350')))
    buttons.append([InlineKeyboardButton(text=f"👥 Пригласить друга + {referral_reward}R", callback_data="referral_link")])
    
    # Сундук с подарком - используем стоимость из БД
    chest_cost = int(float(db.get_setting('chest_cost', '2000')))
    buttons.append([InlineKeyboardButton(text=f"🎁 Открыть сундук с подарком ({chest_cost}R)", callback_data="open_chest")])
    
    # Кнопка "Назад в меню"
    buttons.append([InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_main_menu")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_chest_keyboard(balance: float):
    buttons = []
    if balance >= 2000:
        buttons.append([InlineKeyboardButton(text="🎁 Открыть сундук (2000R)", callback_data="open_chest")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_earn_menu")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_cancel_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="cancel")]
    ])
    return keyboard

