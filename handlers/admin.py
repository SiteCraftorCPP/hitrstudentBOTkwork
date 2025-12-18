from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMINS
from database import Database
import logging

router = Router()
logger = logging.getLogger(__name__)

_db_instance = None

def get_db():
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


class AdminStates(StatesGroup):
    waiting_broadcast_message = State()
    waiting_withdraw_confirmation_text = State()
    waiting_withdraw_success_text = State()
    waiting_withdraw_site_link = State()
    waiting_daily_bonus_min = State()
    waiting_daily_bonus_max = State()
    waiting_subscribe_button_text = State()
    waiting_subscribe_message_text = State()
    waiting_subscribe_channel_username = State()
    waiting_subscribe_channel_link = State()
    waiting_subscribe_channel_name = State()
    waiting_streams_button_text = State()
    waiting_streams_message_text = State()
    waiting_referral_reward = State()
    waiting_friend_referral_reward = State()


def get_admin_keyboard():
    """Главное меню админ-панели"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Рассылка сообщений", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="⚙️ Настройки вывода на баланс сайта", callback_data="admin_withdraw_settings")],
        [InlineKeyboardButton(text="💰 Настройки раздела 'Начать зарабатывать'", callback_data="admin_earn_settings")],
        [InlineKeyboardButton(text="👥 Настройки реферальной программы", callback_data="admin_referral_settings")],
        [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_main_menu")]
    ])
    return keyboard


def get_withdraw_settings_keyboard():
    """Меню настроек вывода"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить текст подтверждения", callback_data="admin_edit_confirmation")],
        [InlineKeyboardButton(text="✏️ Изменить текст успешного вывода", callback_data="admin_edit_success")],
        [InlineKeyboardButton(text="🔗 Изменить ссылку на сайт", callback_data="admin_edit_site_link")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ])
    return keyboard


@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    """Главная команда админ-панели"""
    user_id = message.from_user.id
    
    if user_id not in ADMINS:
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    # Очищаем состояние, если есть
    await state.clear()
    
    text = "🔧 Админ-панель\n\nВыберите действие:"
    await message.answer(text, reply_markup=get_admin_keyboard())


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню админ-панели"""
    await state.clear()
    await callback.message.edit_text(
        "🔧 Админ-панель\n\nВыберите действие:",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    """Начало рассылки"""
    await callback.message.edit_text(
        "📢 Рассылка сообщений\n\n"
        "Отправьте сообщение, которое нужно разослать всем пользователям:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
        ])
    )
    await state.set_state(AdminStates.waiting_broadcast_message)
    await callback.answer()


@router.message(AdminStates.waiting_broadcast_message)
async def admin_broadcast_process(message: Message, state: FSMContext):
    """Обработка рассылки"""
    if message.from_user.id not in ADMINS:
        await state.clear()
        return
    
    db = get_db()
    users = db.get_all_users()
    
    if not users:
        await message.answer("❌ Пользователи не найдены.")
        await state.clear()
        return
    
    # Отправляем сообщение всем пользователям
    sent = 0
    failed = 0
    
    await message.answer(f"📤 Начинаю рассылку для {len(users)} пользователей...")
    
    for user_id in users:
        try:
            await message.bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            sent += 1
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
            failed += 1
    
    await message.answer(
        f"✅ Рассылка завершена!\n\n"
        f"📊 Статистика:\n"
        f"• Отправлено: {sent}\n"
        f"• Ошибок: {failed}\n"
        f"• Всего: {len(users)}",
        reply_markup=get_admin_keyboard()
    )
    
    await state.clear()


@router.callback_query(F.data == "admin_withdraw_settings")
async def admin_withdraw_settings(callback: CallbackQuery):
    """Меню настроек вывода"""
    text = (
        "⚙️ Настройки вывода на баланс сайта\n\n"
        "Выберите, что хотите изменить:"
    )
    
    await callback.message.edit_text(text, reply_markup=get_withdraw_settings_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_edit_confirmation")
async def admin_edit_confirmation(callback: CallbackQuery, state: FSMContext):
    """Редактирование текста подтверждения"""
    db = get_db()
    current_text = db.get_setting('withdraw_site_confirmation_text', '')
    
    # Убираем "Сумма: {amount:.0f} Rcoin" из текущего текста для отображения
    display_text = current_text.replace('Сумма: {amount:.0f} Rcoin', '').replace('\n\n\n', '\n\n').strip()
    
    await callback.message.edit_text(
        "✏️ Изменение текста подтверждения вывода\n\n"
        f"Текущий текст:\n{display_text}\n\n"
        "Отправьте новый текст:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_withdraw_settings")]
        ])
    )
    await state.set_state(AdminStates.waiting_withdraw_confirmation_text)
    await callback.answer()


@router.message(AdminStates.waiting_withdraw_confirmation_text)
async def admin_save_confirmation_text(message: Message, state: FSMContext):
    """Сохранение текста подтверждения"""
    if message.from_user.id not in ADMINS:
        await state.clear()
        return
    
    db = get_db()
    new_text = message.text
    
    # Автоматически добавляем "Сумма: {amount:.0f} Rcoin" если его нет в тексте
    if 'Сумма:' not in new_text and '{amount}' not in new_text:
        new_text = f"{new_text}\n\nСумма: {{amount:.0f}} Rcoin"
    
    db.set_setting('withdraw_site_confirmation_text', new_text)
    
    await message.answer(
        "✅ Текст подтверждения сохранен!",
        reply_markup=get_withdraw_settings_keyboard()
    )
    await state.clear()


@router.callback_query(F.data == "admin_edit_success")
async def admin_edit_success(callback: CallbackQuery, state: FSMContext):
    """Редактирование текста успешного вывода"""
    db = get_db()
    current_text = db.get_setting('withdraw_site_success_text', '')
    
    await callback.message.edit_text(
        "✏️ Изменение текста успешного вывода\n\n"
        f"Текущий текст:\n{current_text}\n\n"
        "Отправьте новый текст:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_withdraw_settings")]
        ])
    )
    await state.set_state(AdminStates.waiting_withdraw_success_text)
    await callback.answer()


@router.message(AdminStates.waiting_withdraw_success_text)
async def admin_save_success_text(message: Message, state: FSMContext):
    """Сохранение текста успешного вывода"""
    if message.from_user.id not in ADMINS:
        await state.clear()
        return
    
    db = get_db()
    new_text = message.text
    
    db.set_setting('withdraw_site_success_text', new_text)
    
    await message.answer(
        "✅ Текст успешного вывода сохранен!",
        reply_markup=get_withdraw_settings_keyboard()
    )
    await state.clear()


@router.callback_query(F.data == "admin_edit_site_link")
async def admin_edit_site_link(callback: CallbackQuery, state: FSMContext):
    """Редактирование ссылки на сайт"""
    db = get_db()
    current_link = db.get_setting('withdraw_site_link', 'https://example.com')
    
    await callback.message.edit_text(
        "🔗 Изменение ссылки на сайт\n\n"
        f"Текущая ссылка:\n{current_link}\n\n"
        "Отправьте новую ссылку:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_withdraw_settings")]
        ])
    )
    await state.set_state(AdminStates.waiting_withdraw_site_link)
    await callback.answer()


@router.message(AdminStates.waiting_withdraw_site_link)
async def admin_save_site_link(message: Message, state: FSMContext):
    """Сохранение ссылки на сайт"""
    if message.from_user.id not in ADMINS:
        await state.clear()
        return
    
    db = get_db()
    new_link = message.text.strip()
    
    # Простая проверка формата ссылки
    if not new_link.startswith('http://') and not new_link.startswith('https://'):
        await message.answer("❌ Ссылка должна начинаться с http:// или https://")
        return
    
    db.set_setting('withdraw_site_link', new_link)
    
    await message.answer(
        "✅ Ссылка на сайт сохранена!",
        reply_markup=get_withdraw_settings_keyboard()
    )
    await state.clear()

