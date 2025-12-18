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
        _db_instance = Database()
    return _db_instance


def get_earn_settings_keyboard():
    """Меню настроек раздела 'Начать зарабатывать'"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Настройки ежедневного бонуса", callback_data="admin_daily_bonus_settings")],
        [InlineKeyboardButton(text="📢 Настройки подписки на каналы", callback_data="admin_subscribe_settings")],
        [InlineKeyboardButton(text="💰 Настройки просмотра стримов", callback_data="admin_streams_settings")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ])
    return keyboard


def get_daily_bonus_settings_keyboard():
    """Меню настроек ежедневного бонуса"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить минимальный бонус", callback_data="admin_edit_daily_min")],
        [InlineKeyboardButton(text="✏️ Изменить максимальный бонус", callback_data="admin_edit_daily_max")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_earn_settings")]
    ])
    return keyboard


def get_subscribe_settings_keyboard():
    """Меню настроек подписки на каналы"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить текст кнопки", callback_data="admin_edit_subscribe_button")],
        [InlineKeyboardButton(text="✏️ Изменить текст сообщения", callback_data="admin_edit_subscribe_message")],
        [InlineKeyboardButton(text="➕ Добавить канал", callback_data="admin_add_subscribe_channel")],
        [InlineKeyboardButton(text="📋 Список каналов", callback_data="admin_list_subscribe_channels")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_earn_settings")]
    ])
    return keyboard


@router.callback_query(F.data == "admin_earn_settings")
async def admin_earn_settings(callback: CallbackQuery):
    """Меню настроек раздела 'Начать зарабатывать'"""
    text = (
        "💰 Настройки раздела 'Начать зарабатывать'\n\n"
        "Выберите, что хотите настроить:"
    )
    await callback.message.edit_text(text, reply_markup=get_earn_settings_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_daily_bonus_settings")
async def admin_daily_bonus_settings(callback: CallbackQuery):
    """Меню настроек ежедневного бонуса"""
    db = get_db()
    min_bonus = db.get_setting('daily_bonus_min', '1')
    max_bonus = db.get_setting('daily_bonus_max', '50')
    
    text = (
        "🎁 Настройки ежедневного бонуса\n\n"
        f"Текущие значения:\n"
        f"• Минимум: {min_bonus}R\n"
        f"• Максимум: {max_bonus}R\n\n"
        "Выберите, что хотите изменить:"
    )
    await callback.message.edit_text(text, reply_markup=get_daily_bonus_settings_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_edit_daily_min")
async def admin_edit_daily_min(callback: CallbackQuery, state: FSMContext):
    """Редактирование минимального бонуса"""
    db = get_db()
    current_min = db.get_setting('daily_bonus_min', '1')
    
    await callback.message.edit_text(
        "✏️ Изменение минимального бонуса\n\n"
        f"Текущее значение: {current_min}R\n\n"
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
        if min_value < 1:
            await message.answer("❌ Значение должно быть больше 0")
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
    db = get_db()
    current_max = db.get_setting('daily_bonus_max', '50')
    
    await callback.message.edit_text(
        "✏️ Изменение максимального бонуса\n\n"
        f"Текущее значение: {current_max}R\n\n"
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
        if max_value < 1:
            await message.answer("❌ Значение должно быть больше 0")
            return
        
        db = get_db()
        min_value = int(db.get_setting('daily_bonus_min', '1'))
        if max_value < min_value:
            await message.answer(f"❌ Максимум должен быть больше или равен минимуму ({min_value}R)")
            return
        
        db.set_setting('daily_bonus_max', str(max_value))
        
        await message.answer(
            f"✅ Максимальный бонус установлен: {max_value}R",
            reply_markup=get_daily_bonus_settings_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Пожалуйста, отправьте число")


@router.callback_query(F.data == "admin_subscribe_settings")
async def admin_subscribe_settings(callback: CallbackQuery):
    """Меню настроек подписки на каналы"""
    text = (
        "📢 Настройки подписки на каналы\n\n"
        "Выберите действие:"
    )
    await callback.message.edit_text(text, reply_markup=get_subscribe_settings_keyboard())
    await callback.answer()


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
    db.set_setting('subscribe_button_text', message.text)
    
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
    db.set_setting('subscribe_message_text', message.text)
    
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
    
    # Извлекаем username из ссылки
    username = None
    chat_id = None
    
    # Проверяем, является ли это invite ссылкой (закрытый канал) - пропускаем
    if "+" in link or "joinchat" in link:
        # Это invite ссылка - закрытые каналы не поддерживаются
        await message.answer(
            "❌ Закрытые каналы не поддерживаются. Отправьте ссылку на открытый канал (например: https://t.me/channelname или @channelname):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_subscribe_settings")]
            ])
        )
        return
    
    # Обычная ссылка - извлекаем username
    if True:
        # Обычная ссылка - извлекаем username
        if link.startswith("https://t.me/"):
            parts = link.replace("https://t.me/", "").split("/")
            if parts[0] and not parts[0].startswith("c/") and not parts[0].startswith("joinchat/"):
                username = parts[0].replace("@", "")
        elif link.startswith("@"):
            username = link.replace("@", "")
        elif link.startswith("t.me/"):
            parts = link.replace("t.me/", "").split("/")
            if parts[0] and not parts[0].startswith("c/") and not parts[0].startswith("joinchat/"):
                username = parts[0].replace("@", "")
        else:
            # Пытаемся использовать как username напрямую
            username = link.replace("@", "").replace("https://t.me/", "").replace("t.me/", "").split("/")[0]
    
    if not username:
        await message.answer(
            "❌ Не удалось извлечь username из ссылки. Отправьте ссылку на открытый канал в формате:\n"
            "https://t.me/channelname или @channelname",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_subscribe_settings")]
            ])
        )
        return
    
    await state.update_data(channel_username=username, channel_link=link, channel_chat_id=None)
    
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
    username = data.get('channel_username')
    link = data.get('channel_link')
    chat_id = data.get('channel_chat_id')
    display_name = message.text.strip()
    
    if not link:
        await message.answer("❌ Ошибка: данные канала не найдены")
        await state.clear()
        return
    
    db = get_db()
    channel_id = db.add_subscribe_channel(username, link, display_name, chat_id)
    
    await message.answer(
        f"✅ Канал '{display_name}' добавлен!",
        reply_markup=get_subscribe_settings_keyboard()
    )
    await state.clear()


@router.callback_query(F.data == "admin_list_subscribe_channels")
async def admin_list_subscribe_channels(callback: CallbackQuery):
    """Список каналов для подписки"""
    db = get_db()
    channels = db.get_subscribe_channels()
    
    if not channels:
        await callback.message.edit_text(
            "📋 Список каналов пуст",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_subscribe_settings")]
            ])
        )
        await callback.answer()
        return
    
    text = "📋 Список каналов для подписки:\n\n"
    buttons = []
    
    for channel in channels:
        username = channel.get('channel_username', 'N/A')
        text += f"• {channel['display_name']}\n"
        text += f"  Username: @{username if username else 'N/A'}\n\n"
        buttons.append([InlineKeyboardButton(
            text=f"✏️ Редактировать: {channel['display_name']}",
            callback_data=f"admin_edit_channel_{channel['id']}"
        )])
        buttons.append([InlineKeyboardButton(
            text=f"❌ Удалить: {channel['display_name']}",
            callback_data=f"admin_delete_channel_{channel['id']}"
        )])
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_subscribe_settings")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("admin_delete_channel_"))
async def admin_delete_channel(callback: CallbackQuery):
    """Удаление канала"""
    channel_id = int(callback.data.split("_")[-1])
    
    db = get_db()
    db.delete_subscribe_channel(channel_id)
    
    await callback.answer("✅ Канал удален!", show_alert=True)
    
    # Обновляем список
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
        "Отправьте новое название кнопки:",
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
    db.set_setting('streams_button_text', message.text)
    
    await message.answer(
        "✅ Название кнопки сохранено!",
        reply_markup=get_streams_settings_keyboard()
    )
    await state.clear()


@router.callback_query(F.data == "admin_edit_streams_message")
async def admin_edit_streams_message(callback: CallbackQuery, state: FSMContext):
    """Редактирование текста сообщения стримов"""
    await callback.message.edit_text(
        "✏️ Изменение текста сообщения стримов\n\n"
        "Отправьте новый текст:",
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
    db.set_setting('streams_message_text', message.text)
    
    await message.answer(
        "✅ Текст сообщения сохранен!",
        reply_markup=get_streams_settings_keyboard()
    )
    await state.clear()


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

