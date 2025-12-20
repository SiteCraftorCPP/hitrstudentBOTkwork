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
    waiting_subscribe_reward = State()
    waiting_chest_message_text = State()
    waiting_chest_project_link = State()
    waiting_welcome_text = State()
    waiting_stats_base_users = State()
    waiting_stats_bot_created = State()
    waiting_stats_base_withdrawn = State()


def get_admin_keyboard():
    """Главное меню админ-панели"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Рассылка сообщений", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="⚙️ Настройки вывода на баланс сайта", callback_data="admin_withdraw_settings")],
        [InlineKeyboardButton(text="💰 Настройки раздела 'Начать зарабатывать'", callback_data="admin_earn_settings")],
        [InlineKeyboardButton(text="👥 Настройки реферальной программы", callback_data="admin_referral_settings")],
        [InlineKeyboardButton(text="📝 Настройки приветствия и статистики", callback_data="admin_welcome_stats_settings")],
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
    try:
        user_id = message.from_user.id
        
        if user_id not in ADMINS:
            await message.answer("❌ У вас нет доступа к админ-панели.")
            return
        
        # Очищаем состояние, если есть
        await state.clear()
        
        # Проверяем доступность БД, но не блокируем загрузку меню
        try:
            db = get_db()
            # Простая проверка - пытаемся выполнить простой запрос
            db.conn.execute("SELECT 1")
        except Exception as db_error:
            logger.error(f"Проблема с БД при загрузке админ-панели: {db_error}", exc_info=True)
            # Продолжаем работу, но предупреждаем админа
            text = "🔧 Админ-панель\n\n⚠️ Внимание: обнаружены проблемы с базой данных. Некоторые функции могут не работать.\n\nВыберите действие:"
        else:
            text = "🔧 Админ-панель\n\nВыберите действие:"
        
        keyboard = get_admin_keyboard()
        await message.answer(text, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в admin_panel: {e}", exc_info=True)
        # Даже при ошибке показываем меню
        try:
            keyboard = get_admin_keyboard()
            await message.answer("🔧 Админ-панель\n\n⚠️ Ошибка при инициализации. Попробуйте позже.", reply_markup=keyboard)
        except:
            await message.answer("❌ Критическая ошибка при загрузке админ-панели.")


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню админ-панели"""
    try:
        await state.clear()
        keyboard = get_admin_keyboard()
        await callback.message.edit_text(
            "🔧 Админ-панель\n\nВыберите действие:",
            reply_markup=keyboard
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в admin_back: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при загрузке меню", show_alert=True)


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
    try:
        # Проверяем БД, но не блокируем загрузку меню
        try:
            db = get_db()
            db.conn.execute("SELECT 1")
        except Exception as db_error:
            logger.error(f"Проблема с БД в admin_withdraw_settings: {db_error}")
        
        text = (
            "⚙️ Настройки вывода на баланс сайта\n\n"
            "Выберите, что хотите изменить:"
        )
        keyboard = get_withdraw_settings_keyboard()
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в admin_withdraw_settings: {e}", exc_info=True)
        # Пытаемся показать меню даже при ошибке
        try:
            keyboard = get_withdraw_settings_keyboard()
            await callback.message.edit_text("⚙️ Настройки вывода на баланс сайта\n\n⚠️ Ошибка при загрузке данных.", reply_markup=keyboard)
            await callback.answer()
        except:
            await callback.answer("❌ Ошибка при загрузке меню", show_alert=True)


@router.callback_query(F.data == "admin_edit_confirmation")
async def admin_edit_confirmation(callback: CallbackQuery, state: FSMContext):
    """Редактирование текста подтверждения"""
    try:
        logger.info(f"Начало редактирования текста подтверждения от {callback.from_user.id}")
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
        logger.info(f"Состояние установлено: waiting_withdraw_confirmation_text для {callback.from_user.id}")
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в admin_edit_confirmation: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при загрузке. Попробуйте позже.", show_alert=True)


@router.message(AdminStates.waiting_withdraw_confirmation_text)
async def admin_save_confirmation_text(message: Message, state: FSMContext):
    """Сохранение текста подтверждения"""
    try:
        logger.info(f"Получено сообщение для сохранения текста подтверждения от {message.from_user.id}")
        if message.from_user.id not in ADMINS:
            logger.warning(f"Попытка сохранения от не-админа {message.from_user.id}")
            await state.clear()
            return
        
        db = get_db()
        new_text = message.text
        logger.info(f"Новый текст подтверждения: {new_text[:50]}...")
        
        # Автоматически добавляем "Сумма: {amount:.0f} Rcoin" если его нет в тексте
        if 'Сумма:' not in new_text and '{amount}' not in new_text:
            new_text = f"{new_text}\n\nСумма: {{amount:.0f}} Rcoin"
        
        db.set_setting('withdraw_site_confirmation_text', new_text)
        logger.info("Текст подтверждения успешно сохранен в БД")
        
        await message.answer(
            "✅ Текст подтверждения сохранен!",
            reply_markup=get_withdraw_settings_keyboard()
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при сохранении текста подтверждения: {e}", exc_info=True)
        await message.answer(
            f"❌ Ошибка при сохранении: {str(e)}\n\nПопробуйте еще раз или обратитесь к разработчику.",
            reply_markup=get_withdraw_settings_keyboard()
        )
        await state.clear()


@router.callback_query(F.data == "admin_edit_success")
async def admin_edit_success(callback: CallbackQuery, state: FSMContext):
    """Редактирование текста успешного вывода"""
    try:
        logger.info(f"Начало редактирования текста успешного вывода от {callback.from_user.id}")
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
        logger.info(f"Состояние установлено: waiting_withdraw_success_text для {callback.from_user.id}")
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в admin_edit_success: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при загрузке. Попробуйте позже.", show_alert=True)


@router.message(AdminStates.waiting_withdraw_success_text)
async def admin_save_success_text(message: Message, state: FSMContext):
    """Сохранение текста успешного вывода"""
    try:
        logger.info(f"Получено сообщение для сохранения текста успешного вывода от {message.from_user.id}")
        if message.from_user.id not in ADMINS:
            logger.warning(f"Попытка сохранения от не-админа {message.from_user.id}")
            await state.clear()
            return
        
        db = get_db()
        new_text = message.text
        logger.info(f"Новый текст успешного вывода: {new_text[:50]}...")
        
        db.set_setting('withdraw_site_success_text', new_text)
        logger.info("Текст успешного вывода успешно сохранен в БД")
        
        await message.answer(
            "✅ Текст успешного вывода сохранен!",
            reply_markup=get_withdraw_settings_keyboard()
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при сохранении текста успешного вывода: {e}", exc_info=True)
        await message.answer(
            f"❌ Ошибка при сохранении: {str(e)}\n\nПопробуйте еще раз или обратитесь к разработчику.",
            reply_markup=get_withdraw_settings_keyboard()
        )
        await state.clear()


@router.callback_query(F.data == "admin_edit_site_link")
async def admin_edit_site_link(callback: CallbackQuery, state: FSMContext):
    """Редактирование ссылки на сайт"""
    try:
        logger.info(f"Начало редактирования ссылки на сайт от {callback.from_user.id}")
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
        logger.info(f"Состояние установлено: waiting_withdraw_site_link для {callback.from_user.id}")
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в admin_edit_site_link: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при загрузке. Попробуйте позже.", show_alert=True)


@router.message(AdminStates.waiting_withdraw_site_link)
async def admin_save_site_link(message: Message, state: FSMContext):
    """Сохранение ссылки на сайт"""
    try:
        logger.info(f"Получено сообщение для сохранения ссылки на сайт от {message.from_user.id}")
        if message.from_user.id not in ADMINS:
            logger.warning(f"Попытка сохранения от не-админа {message.from_user.id}")
            await state.clear()
            return
        
        db = get_db()
        new_link = message.text.strip()
        logger.info(f"Новая ссылка: {new_link}")
        
        # Простая проверка формата ссылки
        if not new_link.startswith('http://') and not new_link.startswith('https://'):
            await message.answer("❌ Ссылка должна начинаться с http:// или https://")
            return
        
        db.set_setting('withdraw_site_link', new_link)
        logger.info("Ссылка на сайт успешно сохранена в БД")
        
        await message.answer(
            "✅ Ссылка на сайт сохранена!",
            reply_markup=get_withdraw_settings_keyboard()
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при сохранении ссылки на сайт: {e}", exc_info=True)
        await message.answer(
            f"❌ Ошибка при сохранении: {str(e)}\n\nПопробуйте еще раз или обратитесь к разработчику.",
            reply_markup=get_withdraw_settings_keyboard()
        )
        await state.clear()


def get_welcome_stats_settings_keyboard():
    """Меню настроек приветствия и статистики"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить приветственное сообщение", callback_data="admin_edit_welcome_text")],
        [InlineKeyboardButton(text="📊 Редактировать статистику проекта", callback_data="admin_stats_settings")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ])
    return keyboard


@router.callback_query(F.data == "admin_welcome_stats_settings")
async def admin_welcome_stats_settings(callback: CallbackQuery):
    """Меню настроек приветствия и статистики"""
    try:
        # Проверяем БД, но не блокируем загрузку меню
        try:
            db = get_db()
            db.conn.execute("SELECT 1")
        except Exception as db_error:
            logger.error(f"Проблема с БД в admin_welcome_stats_settings: {db_error}")
        
        text = (
            "📝 Настройки приветствия и статистики\n\n"
            "Выберите, что хотите изменить:"
        )
        keyboard = get_welcome_stats_settings_keyboard()
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в admin_welcome_stats_settings: {e}", exc_info=True)
        # Пытаемся показать меню даже при ошибке
        try:
            keyboard = get_welcome_stats_settings_keyboard()
            await callback.message.edit_text("📝 Настройки приветствия и статистики\n\n⚠️ Ошибка при загрузке данных.", reply_markup=keyboard)
            await callback.answer()
        except:
            await callback.answer("❌ Ошибка при загрузке меню", show_alert=True)


@router.callback_query(F.data == "admin_edit_welcome_text")
async def admin_edit_welcome_text(callback: CallbackQuery, state: FSMContext):
    """Редактирование приветственного сообщения"""
    db = get_db()
    current_text = db.get_setting('welcome_text', '👋 Добро пожаловать!\n\nЭто бот для заработка Rcoin через выполнение заданий.\n\nВыберите действие в меню:')
    
    await callback.message.edit_text(
        "✏️ Изменение приветственного сообщения\n\n"
        "Отправьте новый текст:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_welcome_stats_settings")]
        ])
    )
    await state.set_state(AdminStates.waiting_welcome_text)
    await callback.answer()


@router.message(AdminStates.waiting_welcome_text)
async def admin_save_welcome_text(message: Message, state: FSMContext):
    """Сохранение приветственного сообщения"""
    if message.from_user.id not in ADMINS:
        await state.clear()
        return
    
    db = get_db()
    new_text = message.text
    
    db.set_setting('welcome_text', new_text)
    
    await message.answer(
        "✅ Приветственное сообщение сохранено!",
        reply_markup=get_welcome_stats_settings_keyboard()
    )
    await state.clear()


def get_stats_settings_keyboard():
    """Меню редактирования статистики проекта"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить базовое количество пользователей", callback_data="admin_edit_stats_base_users")],
        [InlineKeyboardButton(text="✏️ Изменить дату создания бота", callback_data="admin_edit_stats_bot_created")],
        [InlineKeyboardButton(text="✏️ Изменить базовое количество выплаченных рублей", callback_data="admin_edit_stats_base_withdrawn")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_welcome_stats_settings")]
    ])
    return keyboard


@router.callback_query(F.data == "admin_stats_settings")
async def admin_stats_settings(callback: CallbackQuery):
    """Меню редактирования статистики проекта"""
    db = get_db()
    base_users = db.get_setting('stats_base_users', '29201')
    bot_created = db.get_setting('stats_bot_created', '12.06.2024г')
    base_withdrawn = db.get_setting('stats_base_withdrawn', '169768')
    
    text = (
        "📊 Редактирование статистики проекта\n\n"
        f"💰 Базовое количество пользователей: {base_users}\n"
        f"✅ Дата создания бота: {bot_created}\n"
        f"🔗 Базовое количество выплаченных рублей: {base_withdrawn}\n\n"
        "Выберите, что хотите изменить:"
    )
    await callback.message.edit_text(text, reply_markup=get_stats_settings_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_edit_stats_base_users")
async def admin_edit_stats_base_users(callback: CallbackQuery, state: FSMContext):
    """Редактирование базового количества пользователей"""
    await callback.message.edit_text(
        "✏️ Изменение базового количества пользователей\n\n"
        "Отправьте новое значение (только число):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_stats_settings")]
        ])
    )
    await state.set_state(AdminStates.waiting_stats_base_users)
    await callback.answer()


@router.message(AdminStates.waiting_stats_base_users)
async def admin_save_stats_base_users(message: Message, state: FSMContext):
    """Сохранение базового количества пользователей"""
    if message.from_user.id not in ADMINS:
        await state.clear()
        return
    
    try:
        value = int(message.text.strip())
        if value < 0:
            await message.answer("❌ Значение должно быть больше или равно 0")
            return
        
        db = get_db()
        db.set_setting('stats_base_users', str(value))
        
        await message.answer(
            f"✅ Базовое количество пользователей установлено: {value}",
            reply_markup=get_stats_settings_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Пожалуйста, отправьте число")


@router.callback_query(F.data == "admin_edit_stats_bot_created")
async def admin_edit_stats_bot_created(callback: CallbackQuery, state: FSMContext):
    """Редактирование даты создания бота"""
    await callback.message.edit_text(
        "✏️ Изменение даты создания бота\n\n"
        "Отправьте новую дату (например: 12.06.2024г):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_stats_settings")]
        ])
    )
    await state.set_state(AdminStates.waiting_stats_bot_created)
    await callback.answer()


@router.message(AdminStates.waiting_stats_bot_created)
async def admin_save_stats_bot_created(message: Message, state: FSMContext):
    """Сохранение даты создания бота"""
    if message.from_user.id not in ADMINS:
        await state.clear()
        return
    
    db = get_db()
    new_date = message.text.strip()
    
    db.set_setting('stats_bot_created', new_date)
    
    await message.answer(
        f"✅ Дата создания бота установлена: {new_date}",
        reply_markup=get_stats_settings_keyboard()
    )
    await state.clear()


@router.callback_query(F.data == "admin_edit_stats_base_withdrawn")
async def admin_edit_stats_base_withdrawn(callback: CallbackQuery, state: FSMContext):
    """Редактирование базового количества выплаченных рублей"""
    await callback.message.edit_text(
        "✏️ Изменение базового количества выплаченных рублей\n\n"
        "Отправьте новое значение (только число):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_stats_settings")]
        ])
    )
    await state.set_state(AdminStates.waiting_stats_base_withdrawn)
    await callback.answer()


@router.message(AdminStates.waiting_stats_base_withdrawn)
async def admin_save_stats_base_withdrawn(message: Message, state: FSMContext):
    """Сохранение базового количества выплаченных рублей"""
    if message.from_user.id not in ADMINS:
        await state.clear()
        return
    
    try:
        value = int(message.text.strip())
        if value < 0:
            await message.answer("❌ Значение должно быть больше или равно 0")
            return
        
        db = get_db()
        db.set_setting('stats_base_withdrawn', str(value))
        
        await message.answer(
            f"✅ Базовое количество выплаченных рублей установлено: {value}",
            reply_markup=get_stats_settings_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Пожалуйста, отправьте число")

