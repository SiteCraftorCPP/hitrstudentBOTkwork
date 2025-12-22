from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from config import ADMINS
from database import Database
from handlers.admin import AdminStates, get_admin_keyboard
import logging

router = Router()
logger = logging.getLogger(__name__)

_db_instance = None

def get_db():
    global _db_instance
    if _db_instance is None:
        try:
            _db_instance = Database()
        except Exception as e:
            logger.error(f"Ошибка при создании экземпляра базы данных: {e}", exc_info=True)
            # Пытаемся пересоздать соединение
            try:
                _db_instance = Database()
            except Exception as e2:
                logger.error(f"Критическая ошибка БД: {e2}", exc_info=True)
                raise
    return _db_instance


def get_earn_settings_keyboard():
    """Меню настроек раздела 'Начать зарабатывать'"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Настройки ежедневного бонуса", callback_data="admin_daily_bonus_settings")],
        [InlineKeyboardButton(text="📢 Настройки подписки на каналы", callback_data="admin_subscribe_settings")],
        [InlineKeyboardButton(text="💰 Настройки просмотра стримов", callback_data="admin_streams_settings")],
        [InlineKeyboardButton(text="🎁 Настройки сундука с подарком", callback_data="admin_chest_settings")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ])
    return keyboard


@router.callback_query(F.data == "admin_earn_settings")
async def admin_earn_settings(callback: CallbackQuery):
    """Меню настроек раздела 'Начать зарабатывать'"""
    try:
        # Проверяем БД, но не блокируем загрузку меню
        try:
            db = get_db()
            db.conn.execute("SELECT 1")
        except Exception as db_error:
            logger.error(f"Проблема с БД в admin_earn_settings: {db_error}")
        
        text = (
            "💰 Настройки раздела 'Начать зарабатывать'\n\n"
            "Выберите, что хотите настроить:"
        )
        keyboard = get_earn_settings_keyboard()
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в admin_earn_settings: {e}", exc_info=True)
        # Пытаемся показать меню даже при ошибке
        try:
            keyboard = get_earn_settings_keyboard()
            await callback.message.edit_text("💰 Настройки раздела 'Начать зарабатывать'\n\n⚠️ Ошибка при загрузке данных.", reply_markup=keyboard)
            await callback.answer()
        except:
            await callback.answer("❌ Ошибка при загрузке меню", show_alert=True)


def get_daily_bonus_settings_keyboard():
    """Меню настроек ежедневного бонуса"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить минимальный бонус", callback_data="admin_edit_daily_min")],
        [InlineKeyboardButton(text="✏️ Изменить максимальный бонус", callback_data="admin_edit_daily_max")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_earn_settings")]
    ])
    return keyboard


@router.callback_query(F.data == "admin_daily_bonus_settings")
async def admin_daily_bonus_settings(callback: CallbackQuery):
    """Меню настроек ежедневного бонуса"""
    db = get_db()
    min_bonus = db.get_setting('daily_bonus_min', '1')
    max_bonus = db.get_setting('daily_bonus_max', '50')
    
    text = (
        "🎁 Настройки ежедневного бонуса\n\n"
        f"Минимальный бонус: {min_bonus}R\n"
        f"Максимальный бонус: {max_bonus}R\n\n"
        "Выберите, что хотите изменить:"
    )
    await callback.message.edit_text(text, reply_markup=get_daily_bonus_settings_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_edit_daily_min")
async def admin_edit_daily_min(callback: CallbackQuery, state: FSMContext):
    """Редактирование минимального бонуса"""
    await callback.message.edit_text(
        "✏️ Изменение минимального ежедневного бонуса\n\n"
        "Отправьте новое значение (только число):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_daily_bonus_settings")]
        ])
    )
    await state.set_state(AdminStates.waiting_daily_bonus_min)
    await callback.answer()


@router.message(AdminStates.waiting_daily_bonus_min)
async def admin_save_daily_min(message: Message, state: FSMContext):
    """Сохранение минимального бонуса"""
    if message.from_user.id not in ADMINS:
        await state.clear()
        return
    
    try:
        min_value = int(message.text.strip())
        if min_value < 0:
            await message.answer("❌ Значение должно быть больше или равно 0")
            return
        
        db = get_db()
        db.set_setting('daily_bonus_min', str(min_value))
        
        await message.answer(
            f"✅ Минимальный бонус установлен: {min_value}R",
            reply_markup=get_daily_bonus_settings_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Пожалуйста, отправьте число")


@router.callback_query(F.data == "admin_edit_daily_max")
async def admin_edit_daily_max(callback: CallbackQuery, state: FSMContext):
    """Редактирование максимального бонуса"""
    await callback.message.edit_text(
        "✏️ Изменение максимального ежедневного бонуса\n\n"
        "Отправьте новое значение (только число):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_daily_bonus_settings")]
        ])
    )
    await state.set_state(AdminStates.waiting_daily_bonus_max)
    await callback.answer()


@router.message(AdminStates.waiting_daily_bonus_max)
async def admin_save_daily_max(message: Message, state: FSMContext):
    """Сохранение максимального бонуса"""
    if message.from_user.id not in ADMINS:
        await state.clear()
        return
    
    try:
        max_value = int(message.text.strip())
        if max_value < 0:
            await message.answer("❌ Значение должно быть больше или равно 0")
            return
        
        db = get_db()
        db.set_setting('daily_bonus_max', str(max_value))
        
        await message.answer(
            f"✅ Максимальный бонус установлен: {max_value}R",
            reply_markup=get_daily_bonus_settings_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Пожалуйста, отправьте число")


def get_subscribe_settings_keyboard():
    """Меню настроек подписки на каналы"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Изменить награду за канал", callback_data="admin_edit_subscribe_reward")],
        [InlineKeyboardButton(text="✏️ Изменить текст кнопки", callback_data="admin_edit_subscribe_button")],
        [InlineKeyboardButton(text="✏️ Изменить текст сообщения", callback_data="admin_edit_subscribe_message")],
        [InlineKeyboardButton(text="➕ Добавить канал", callback_data="admin_add_subscribe_channel")],
        [InlineKeyboardButton(text="📋 Список каналов", callback_data="admin_list_subscribe_channels")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_earn_settings")]
    ])
    return keyboard


@router.callback_query(F.data == "admin_subscribe_settings")
async def admin_subscribe_settings(callback: CallbackQuery):
    """Меню настроек подписки на каналы"""
    try:
        # Проверяем БД, но не блокируем загрузку меню
        try:
            db = get_db()
            db.conn.execute("SELECT 1")
        except Exception as db_error:
            logger.error(f"Проблема с БД в admin_subscribe_settings: {db_error}")
        
        text = (
            "📢 Настройки подписки на каналы\n\n"
            "Выберите действие:"
        )
        keyboard = get_subscribe_settings_keyboard()
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в admin_subscribe_settings: {e}", exc_info=True)
        # Пытаемся показать меню даже при ошибке
        try:
            keyboard = get_subscribe_settings_keyboard()
            await callback.message.edit_text("📢 Настройки подписки на каналы\n\n⚠️ Ошибка при загрузке данных.", reply_markup=keyboard)
            await callback.answer()
        except:
            await callback.answer("❌ Ошибка при загрузке меню", show_alert=True)


@router.callback_query(F.data == "admin_edit_subscribe_button")
async def admin_edit_subscribe_button(callback: CallbackQuery, state: FSMContext):
    """Редактирование текста кнопки подписки"""
    await callback.message.edit_text(
        "✏️ Изменение текста кнопки подписки\n\n"
        "Отправьте новый текст:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_subscribe_settings")]
        ])
    )
    await state.set_state(AdminStates.waiting_subscribe_button_text)
    await callback.answer()


@router.message(AdminStates.waiting_subscribe_button_text)
async def admin_save_subscribe_button(message: Message, state: FSMContext):
    """Сохранение текста кнопки подписки"""
    if message.from_user.id not in ADMINS:
        await state.clear()
        return
    
    db = get_db()
    new_text = message.text
    
    db.set_setting('subscribe_button_text', new_text)
    
    await message.answer(
        "✅ Текст кнопки сохранен!",
        reply_markup=get_subscribe_settings_keyboard()
    )
    await state.clear()


@router.callback_query(F.data == "admin_edit_subscribe_message")
async def admin_edit_subscribe_message(callback: CallbackQuery, state: FSMContext):
    """Редактирование текста сообщения подписки"""
    await callback.message.edit_text(
        "✏️ Изменение текста сообщения подписки\n\n"
        "Отправьте новый текст:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_subscribe_settings")]
        ])
    )
    await state.set_state(AdminStates.waiting_subscribe_message_text)
    await callback.answer()


@router.message(AdminStates.waiting_subscribe_message_text)
async def admin_save_subscribe_message(message: Message, state: FSMContext):
    """Сохранение текста сообщения подписки"""
    if message.from_user.id not in ADMINS:
        await state.clear()
        return
    
    db = get_db()
    new_text = message.text
    
    db.set_setting('subscribe_message_text', new_text)
    
    await message.answer(
        "✅ Текст сообщения сохранен!",
        reply_markup=get_subscribe_settings_keyboard()
    )
    await state.clear()


@router.callback_query(F.data == "admin_add_subscribe_channel")
async def admin_add_subscribe_channel_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления канала"""
    await callback.message.edit_text(
        "➕ Добавление канала для подписки\n\n"
        "Отправьте ссылку на канал:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_subscribe_settings")]
        ])
    )
    await state.set_state(AdminStates.waiting_subscribe_channel_link)
    await callback.answer()


@router.message(AdminStates.waiting_subscribe_channel_link)
async def admin_add_subscribe_channel_link(message: Message, state: FSMContext):
    """Получение ссылки на канал и извлечение username/chat_id"""
    if message.from_user.id not in ADMINS:
        await state.clear()
        return
    
    link = message.text.strip()
    
    # Извлекаем username или chat_id из ссылки
    channel_username = None
    channel_chat_id = None
    
    if link.startswith('https://t.me/'):
        # Извлекаем username
        parts = link.replace('https://t.me/', '').split('/')
        if parts:
            channel_username = parts[0].replace('@', '')
    elif link.startswith('@'):
        channel_username = link.replace('@', '')
    elif link.startswith('-100'):
        # Это chat_id
        try:
            channel_chat_id = link
        except:
            pass
    
    if not channel_username and not channel_chat_id:
        await message.answer(
            "❌ Не удалось определить канал из ссылки.\n\n"
            "Отправьте ссылку в формате:\n"
            "• https://t.me/channel_name\n"
            "• @channel_name\n"
            "• -1001234567890 (chat_id)",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_subscribe_settings")]
            ])
        )
        return
    
    # Сохраняем данные во временное хранилище
    await state.update_data(
        channel_link=link,
        channel_username=channel_username,
        channel_chat_id=channel_chat_id
    )
    
    await message.answer(
        "Отправьте название канала для отображения:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_subscribe_settings")]
        ])
    )
    await state.set_state(AdminStates.waiting_subscribe_channel_name)


@router.message(AdminStates.waiting_subscribe_channel_name)
async def admin_add_subscribe_channel_name(message: Message, state: FSMContext):
    """Сохранение канала"""
    if message.from_user.id not in ADMINS:
        await state.clear()
        return
    
    data = await state.get_data()
    channel_link = data.get('channel_link')
    channel_username = data.get('channel_username')
    channel_chat_id = data.get('channel_chat_id')
    display_name = message.text.strip()
    
    db = get_db()
    
    try:
        channel_id = db.add_subscribe_channel(
            channel_username=channel_username or '',
            channel_link=channel_link,
            display_name=display_name,
            channel_chat_id=channel_chat_id
        )
        
        await message.answer(
            f"✅ Канал '{display_name}' добавлен!",
            reply_markup=get_subscribe_settings_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при добавлении канала: {e}", exc_info=True)
        await message.answer(
            f"❌ Ошибка при добавлении канала: {e}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_subscribe_settings")]
            ])
        )
    
    await state.clear()


@router.callback_query(F.data == "admin_list_subscribe_channels")
async def admin_list_subscribe_channels(callback: CallbackQuery):
    """Список каналов для подписки"""
    db = get_db()
    channels = db.get_subscribe_channels()
    
    if not channels:
        await callback.message.edit_text(
            "📋 Список каналов пуст.\n\nДобавьте каналы через меню настроек.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_subscribe_settings")]
            ])
        )
        await callback.answer()
        return
    
    text = "📋 Список каналов для подписки:\n\n"
    buttons = []
    
    for channel in channels:
        display_name = channel.get('display_name', channel.get('channel_username', 'Без названия'))
        channel_id = channel.get('id')
        text += f"• {display_name}\n"
        
        buttons.append([
            InlineKeyboardButton(
                text=f"✏️ {display_name}",
                callback_data=f"admin_edit_channel_{channel_id}"
            ),
            InlineKeyboardButton(
                text="🗑️",
                callback_data=f"admin_delete_channel_{channel_id}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_subscribe_settings")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_delete_channel_"))
async def admin_delete_channel(callback: CallbackQuery):
    """Удаление канала"""
    channel_id = int(callback.data.split("_")[-1])
    
    db = get_db()
    db.delete_subscribe_channel(channel_id)
    
    await callback.answer("✅ Канал удален!", show_alert=True)
    await admin_list_subscribe_channels(callback)


def get_streams_settings_keyboard():
    """Меню настроек просмотра стримов"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить название кнопки", callback_data="admin_edit_streams_button")],
        [InlineKeyboardButton(text="✏️ Изменить текст сообщения", callback_data="admin_edit_streams_message")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_earn_settings")]
    ])
    return keyboard


@router.callback_query(F.data == "admin_streams_settings")
async def admin_streams_settings(callback: CallbackQuery):
    """Меню настроек просмотра стримов"""
    text = (
        "💰 Настройки просмотра стримов\n\n"
        "Выберите, что хотите изменить:"
    )
    await callback.message.edit_text(text, reply_markup=get_streams_settings_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_edit_streams_button")
async def admin_edit_streams_button(callback: CallbackQuery, state: FSMContext):
    """Редактирование названия кнопки стримов"""
    await callback.message.edit_text(
        "✏️ Изменение названия кнопки стримов\n\n"
        "Отправьте новое название:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_streams_settings")]
        ])
    )
    await state.set_state(AdminStates.waiting_streams_button_text)
    await callback.answer()


@router.message(AdminStates.waiting_streams_button_text)
async def admin_save_streams_button(message: Message, state: FSMContext):
    """Сохранение названия кнопки стримов"""
    if message.from_user.id not in ADMINS:
        await state.clear()
        return
    
    db = get_db()
    new_text = message.text
    
    db.set_setting('streams_button_text', new_text)
    
    await message.answer(
        "✅ Название кнопки сохранено!",
        reply_markup=get_streams_settings_keyboard()
    )
    await state.clear()


@router.callback_query(F.data == "admin_edit_streams_message")
async def admin_edit_streams_message(callback: CallbackQuery, state: FSMContext):
    """Редактирование текста сообщения стримов"""
    db = get_db()
    current_text = db.get_setting('streams_message_text', '📖 Узнать, как зарабатывать на просмотре трансляций/стримов')
    
    await callback.message.edit_text(
        "✏️ Изменение текста сообщения стримов\n\n"
        f"Текущий текст:\n{current_text}\n\n"
        "Отправьте новый текст (можете включить информацию о подписке на канал @akatsik):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_streams_settings")]
        ])
    )
    await state.set_state(AdminStates.waiting_streams_message_text)
    await callback.answer()


@router.message(AdminStates.waiting_streams_message_text)
async def admin_save_streams_message(message: Message, state: FSMContext):
    """Сохранение текста сообщения стримов"""
    if message.from_user.id not in ADMINS:
        await state.clear()
        return
    
    db = get_db()
    new_text = message.text
    
    db.set_setting('streams_message_text', new_text)
    
    await message.answer(
        "✅ Текст сообщения сохранен!",
        reply_markup=get_streams_settings_keyboard()
    )
    await state.clear()


@router.callback_query(F.data == "admin_edit_subscribe_reward")
async def admin_edit_subscribe_reward(callback: CallbackQuery, state: FSMContext):
    """Редактирование награды за подписку на один канал"""
    db = get_db()
    current_reward = db.get_setting('subscribe_reward', '100')
    
    await callback.message.edit_text(
        "💰 Изменение награды за подписку на один канал\n\n"
        f"Текущая награда: {current_reward}R за один канал\n\n"
        "Отправьте новое значение (только число):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_subscribe_settings")]
        ])
    )
    await state.set_state(AdminStates.waiting_subscribe_reward)
    await callback.answer()


@router.message(AdminStates.waiting_subscribe_reward)
async def admin_save_subscribe_reward(message: Message, state: FSMContext):
    """Сохранение награды за подписку на один канал"""
    if message.from_user.id not in ADMINS:
        await state.clear()
        return
    
    try:
        reward_value = int(message.text.strip())
        if reward_value < 0:
            await message.answer("❌ Значение должно быть больше или равно 0")
            return
        
        db = get_db()
        db.set_setting('subscribe_reward', str(reward_value))
        
        await message.answer(
            f"✅ Награда за подписку на один канал установлена: {reward_value}R\n\n"
            f"Пример: если пользователь подпишется на 2 канала, он получит {reward_value * 2}R",
            reply_markup=get_subscribe_settings_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Пожалуйста, отправьте число")


def get_referral_settings_keyboard():
    """Меню настроек реферальной программы"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить награду за реферала", callback_data="admin_edit_referral_reward")],
        [InlineKeyboardButton(text="✏️ Изменить награду за реферала друга", callback_data="admin_edit_friend_referral_reward")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ])
    return keyboard


@router.callback_query(F.data == "admin_referral_settings")
async def admin_referral_settings(callback: CallbackQuery):
    """Меню настроек реферальной программы"""
    text = (
        "👥 Настройки реферальной программы\n\n"
        "Выберите, что хотите изменить:"
    )
    await callback.message.edit_text(text, reply_markup=get_referral_settings_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_edit_referral_reward")
async def admin_edit_referral_reward(callback: CallbackQuery, state: FSMContext):
    """Редактирование награды за реферала"""
    await callback.message.edit_text(
        "✏️ Изменение награды за реферала\n\n"
        "Отправьте новое значение (только число):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_referral_settings")]
        ])
    )
    await state.set_state(AdminStates.waiting_referral_reward)
    await callback.answer()


@router.message(AdminStates.waiting_referral_reward)
async def admin_save_referral_reward(message: Message, state: FSMContext):
    """Сохранение награды за реферала"""
    if message.from_user.id not in ADMINS:
        await state.clear()
        return
    
    try:
        reward_value = int(message.text.strip())
        if reward_value < 0:
            await message.answer("❌ Значение должно быть больше или равно 0")
            return
        
        db = get_db()
        db.set_setting('referral_reward', str(reward_value))
        
        await message.answer(
            f"✅ Награда за реферала установлена: {reward_value}R",
            reply_markup=get_referral_settings_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Пожалуйста, отправьте число")


@router.callback_query(F.data == "admin_edit_friend_referral_reward")
async def admin_edit_friend_referral_reward(callback: CallbackQuery, state: FSMContext):
    """Редактирование награды за реферала друга"""
    await callback.message.edit_text(
        "✏️ Изменение награды за реферала друга\n\n"
        "Отправьте новое значение (только число):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_referral_settings")]
        ])
    )
    await state.set_state(AdminStates.waiting_friend_referral_reward)
    await callback.answer()


@router.message(AdminStates.waiting_friend_referral_reward)
async def admin_save_friend_referral_reward(message: Message, state: FSMContext):
    """Сохранение награды за реферала друга"""
    if message.from_user.id not in ADMINS:
        await state.clear()
        return
    
    try:
        reward_value = int(message.text.strip())
        if reward_value < 0:
            await message.answer("❌ Значение должно быть больше или равно 0")
            return
        
        db = get_db()
        db.set_setting('friend_referral_reward', str(reward_value))
        
        await message.answer(
            f"✅ Награда за реферала друга установлена: {reward_value}R",
            reply_markup=get_referral_settings_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Пожалуйста, отправьте число")


def get_chest_settings_keyboard():
    """Меню настроек сундука с подарком"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить текст сообщения", callback_data="admin_edit_chest_message")],
        [InlineKeyboardButton(text="🔗 Изменить ссылку на проект", callback_data="admin_edit_chest_link")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_earn_settings")]
    ])
    return keyboard


@router.callback_query(F.data == "admin_chest_settings")
async def admin_chest_settings(callback: CallbackQuery):
    """Меню настроек сундука с подарком"""
    try:
        text = (
            "🎁 Настройки сундука с подарком\n\n"
            "Выберите, что хотите изменить:"
        )
        keyboard = get_chest_settings_keyboard()
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в admin_chest_settings: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при загрузке меню", show_alert=True)


@router.callback_query(F.data == "admin_edit_chest_message")
async def admin_edit_chest_message(callback: CallbackQuery, state: FSMContext):
    """Редактирование текста сообщения сундука"""
    await callback.message.edit_text(
        "✏️ Изменение текста сообщения сундука\n\n"
        "Отправьте новый текст:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_chest_settings")]
        ])
    )
    await state.set_state(AdminStates.waiting_chest_message_text)
    await callback.answer()


@router.message(AdminStates.waiting_chest_message_text)
async def admin_save_chest_message(message: Message, state: FSMContext):
    """Сохранение текста сообщения сундука"""
    if message.from_user.id not in ADMINS:
        await state.clear()
        return
    
    db = get_db()
    new_text = message.text
    
    db.set_setting('chest_message_text', new_text)
    
    await message.answer(
        "✅ Текст сообщения сундука сохранен!",
        reply_markup=get_chest_settings_keyboard()
    )
    await state.clear()


@router.callback_query(F.data == "admin_edit_chest_link")
async def admin_edit_chest_link(callback: CallbackQuery, state: FSMContext):
    """Редактирование ссылки на проект"""
    await callback.message.edit_text(
        "🔗 Изменение ссылки на проект\n\n"
        "Отправьте новую ссылку:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_chest_settings")]
        ])
    )
    await state.set_state(AdminStates.waiting_chest_project_link)
    await callback.answer()


@router.message(AdminStates.waiting_chest_project_link)
async def admin_save_chest_link(message: Message, state: FSMContext):
    """Сохранение ссылки на проект"""
    if message.from_user.id not in ADMINS:
        await state.clear()
        return
    
    db = get_db()
    new_link = message.text.strip()
    
    # Простая проверка формата ссылки
    if not new_link.startswith('http://') and not new_link.startswith('https://'):
        await message.answer("❌ Ссылка должна начинаться с http:// или https://")
        return
    
    db.set_setting('chest_project_link', new_link)
    
    await message.answer(
        "✅ Ссылка на проект сохранена!",
        reply_markup=get_chest_settings_keyboard()
    )
    await state.clear()


