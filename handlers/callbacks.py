import random
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import Database
from config import *
from keyboards import (
    get_main_menu, get_profile_keyboard, get_withdraw_keyboard,
    get_withdraw_methods_keyboard, get_earn_menu_keyboard,
    get_chest_keyboard, get_cancel_keyboard
)
import asyncio

router = Router()
db = Database()
logger = logging.getLogger(__name__)


class WithdrawStates(StatesGroup):
    waiting_amount = State()
    waiting_wallet = State()
    confirming_site_withdraw = State()
    confirming_site_withdraw = State()


@router.callback_query(F.data == "daily_bonus")
async def daily_bonus(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    can_get, next_time = db.can_get_daily_bonus(user_id)
    
    if not can_get:
        # Показываем информацию о следующем бонусе
        from datetime import datetime, timedelta
        
        if next_time:
            # Вычисляем оставшееся время до следующего бонуса
            now = datetime.now()
            next_datetime = datetime.combine(next_time, datetime.min.time())
            
            if next_datetime <= now:
                # Уже наступил новый день, можно получить бонус
                can_get = True
            else:
                # Показываем информацию о следующем бонусе
                time_left = next_datetime - now
                hours = int(time_left.total_seconds() // 3600)
                minutes = int((time_left.total_seconds() % 3600) // 60)
                
                # Форматируем дату
                next_date_str = next_time.strftime("%d.%m.%Y")
                
                text = (
                    f"🎁 Ежедневный бонус\n\n"
                    f"❌ Бонус уже получен сегодня!\n\n"
                    f"⏰ Следующий бонус доступен:\n"
                    f"📅 Дата: {next_date_str}\n"
                )
                
                if hours > 0:
                    text += f"⏳ Осталось: {hours} ч. {minutes} мин."
                elif minutes > 0:
                    text += f"⏳ Осталось: {minutes} мин."
                else:
                    text += f"⏳ Осталось: менее минуты"
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_earn_menu")]
                ])
                await callback.answer("Бонус уже получен сегодня", show_alert=True)
                await callback.message.edit_text(text, reply_markup=keyboard)
                return
        
        if not can_get:
            await callback.answer("Вы уже получили ежедневный бонус сегодня!", show_alert=True)
            return
    
    # Выдаем бонус (получаем значения из настроек)
    min_bonus = int(db.get_setting('daily_bonus_min', str(DAILY_BONUS_MIN)))
    max_bonus = int(db.get_setting('daily_bonus_max', str(DAILY_BONUS_MAX)))
    amount = random.randint(min_bonus, max_bonus)
    db.set_daily_bonus(user_id, amount)
    
    user = db.get_user(user_id)
    
    # Вычисляем время следующего бонуса для отображения
    from datetime import datetime, timedelta
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    tomorrow_str = tomorrow.strftime("%d.%m.%Y")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_earn_menu")]
    ])
    await callback.answer(f"Вы получили {amount}R!", show_alert=True)
    await callback.message.edit_text(
        f"🎁 Ежедневный бонус\n\n"
        f"✅ Вы получили: {amount}R\n"
        f"💰 Ваш баланс: {user.get('balance', 0.0):.2f}R\n\n"
        f"⏰ Следующий бонус доступен:\n"
        f"📅 Дата: {tomorrow_str}\n"
        f"🔄 Обновляется каждый день",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("task_"))
async def handle_task(callback: CallbackQuery):
    user_id = callback.from_user.id
    task_id = int(callback.data.split("_")[1])
    
    task = None
    tasks = db.get_tasks()
    for t in tasks:
        if t['task_id'] == task_id:
            task = t
            break
    
    if not task:
        await callback.answer("Задание не найдено!", show_alert=True)
        return
    
    # Для заданий типа 'subscribe' и 'info' не проверяем выполнение - кнопки всегда доступны
    if task['task_type'] not in ['subscribe', 'info']:
        if db.is_task_completed(user_id, task_id):
            await callback.answer("Вы уже выполнили это задание!", show_alert=True)
            return
    
    if task['task_type'] == 'subscribe':
        # Проверяем, есть ли каналы в настройках
        channels = db.get_subscribe_channels()
        
        if not channels:
            # Нет каналов в настройках - задание недоступно
            await callback.answer("Каналы для подписки не настроены. Обратитесь к администратору.", show_alert=True)
            return
        
        # Используем каналы из настроек
        message_text = db.get_setting('subscribe_message_text', '📢 Подпишитесь на каналы для получения награды!')
        
        # Создаем кнопки для каждого канала
        buttons = []
        for channel in channels:
            channel_link = channel.get('channel_link') or f"https://t.me/{channel.get('channel_username', '')}"
            buttons.append([InlineKeyboardButton(
                text=f"📢 {channel.get('display_name', channel.get('channel_username', 'Канал'))}",
                url=channel_link
            )])
        
        buttons.append([InlineKeyboardButton(
            text="✅ Я подписался, проверить",
            callback_data=f"check_subscribe_channels_{task_id}"
        )])
        buttons.append([InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back_to_earn_menu"
        )])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            message_text,
            reply_markup=keyboard
        )
        await callback.answer()
        return
    
    elif task['task_type'] == 'info':
        # Задание всегда доступно, но награда начисляется только один раз
        # Проверяем подписку на канал @akatsik
        channel_username = "akatsik"
        channel_url = f"https://t.me/{channel_username}"
        is_subscribed = False
        
        logger.info(f"Проверка подписки на канал @{channel_username} для пользователя {user_id}")
        
        try:
            member = await callback.bot.get_chat_member(f"@{channel_username}", user_id)
            logger.info(f"Статус пользователя {user_id} в канале @{channel_username}: {member.status}")
            if member.status in ['member', 'administrator', 'creator']:
                is_subscribed = True
                logger.info(f"Пользователь {user_id} подписан на канал @{channel_username}")
            else:
                logger.info(f"Пользователь {user_id} НЕ подписан на канал @{channel_username} (статус: {member.status})")
        except Exception as e:
            logger.error(f"Ошибка при проверке подписки на канал @{channel_username}: {e}", exc_info=True)
            # Если бот не может проверить подписку, показываем сообщение с кнопкой
            text = db.get_setting('streams_message_text', task.get('description', task.get('title', '📖 Узнать, как зарабатывать на просмотре трансляций/стримов')))
            
            buttons = [
                [InlineKeyboardButton(
                    text="📢 Подписаться на канал",
                    url=channel_url
                )],
                [InlineKeyboardButton(
                    text="✅ Я подписался, проверить",
                    callback_data=f"check_streams_subscribe_{task_id}"
                )],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_earn_menu")]
            ]
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            await callback.message.edit_text(
                text,
                reply_markup=keyboard
            )
            await callback.answer()
            return
        
        if not is_subscribed:
            # Пользователь не подписан - показываем сообщение с кнопкой подписки
            logger.info(f"Пользователь {user_id} не подписан на канал @{channel_username}, показываем кнопки подписки")
            text = db.get_setting('streams_message_text', task.get('description', task.get('title', '📖 Узнать, как зарабатывать на просмотре трансляций/стримов')))
            
            buttons = [
                [InlineKeyboardButton(
                    text="📢 Подписаться на канал",
                    url=channel_url
                )],
                [InlineKeyboardButton(
                    text="✅ Я подписался, проверить",
                    callback_data=f"check_streams_subscribe_{task_id}"
                )],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_earn_menu")]
            ]
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            await callback.message.edit_text(
                text,
                reply_markup=keyboard
            )
            # Убираем навязчивое предупреждение — просто обновляем текст и кнопки
            await callback.answer()
            return
        
        # Пользователь подписан - проверяем, получал ли он уже награду
        if db.is_task_completed(user_id, task_id):
            # Уже получил награду - показываем текст с кнопками, но без начисления
            text = db.get_setting('streams_message_text', task.get('description', task.get('title', '📖 Узнать, как зарабатывать на просмотре трансляций/стримов')))
            
            buttons = [
                [InlineKeyboardButton(
                    text="📢 Подписаться на канал",
                    url=channel_url
                )],
                [InlineKeyboardButton(
                    text="✅ Я подписался, проверить",
                    callback_data=f"check_streams_subscribe_{task_id}"
                )],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_earn_menu")]
            ]
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
            return
        
        # Пользователь подписан и еще не получал награду - начисляем награду ОДИН РАЗ
        # Используем награду из задания, если есть, иначе из конфига
        reward_amount = float(task.get('reward', STREAM_INFO_REWARD))
        
        # Проверяем реферала перед выполнением задания
        # Получаем награды за рефералов из БД
        referral_reward = float(db.get_setting('referral_reward', '350'))
        friend_referral_reward = float(db.get_setting('friend_referral_reward', '100'))
        
        user = db.get_user(user_id)
        if user and user.get('referrer_id'):
            cursor = db.conn.cursor()
            # Проверяем, есть ли уже выполненные задания (кроме текущего)
            cursor.execute(
                "SELECT COUNT(*) as count FROM completed_tasks WHERE user_id = ? AND task_id != ?",
                (user_id, task_id)
            )
            completed_before = cursor.fetchone()['count']
            
            # Начисляем за реферала только если это первое выполненное задание
            if completed_before == 0:
                db.update_user_balance(user['referrer_id'], referral_reward)
                referrer = db.get_user(user['referrer_id'])
                if referrer and referrer.get('referrer_id'):
                    db.update_user_balance(referrer['referrer_id'], friend_referral_reward)
        
        db.update_user_balance(user_id, reward_amount)
        db.complete_task(user_id, task_id)  # Помечаем задание как выполненное
        
        # Получаем обновленный баланс
        user = db.get_user(user_id)
        
        # Используем настройку из БД для текста сообщения
        text = db.get_setting('streams_message_text', task.get('description', task.get('title', '📖 Узнать, как зарабатывать на просмотре трансляций/стримов')))
        
        # Добавляем информацию о начислении
        text_with_reward = f"{text}\n\n✅ Начислено: {int(reward_amount)}R\n💰 Ваш баланс: {user['balance']:.2f}R"
        
        buttons = [
            [InlineKeyboardButton(
                text="📢 Подписаться на канал",
                url=channel_url
            )],
            [InlineKeyboardButton(
                text="✅ Я подписался, проверить",
                callback_data=f"check_streams_subscribe_{task_id}"
            )],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_earn_menu")]
        ]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.answer(f"✅ Начислено {int(reward_amount)}R!", show_alert=True)
        await callback.message.edit_text(text_with_reward, reply_markup=keyboard)
    
    elif task['task_type'] == 'custom':
        # Для кастомных заданий
        # Проверяем реферала перед выполнением
        # Получаем награды за рефералов из БД
        referral_reward = float(db.get_setting('referral_reward', '350'))
        friend_referral_reward = float(db.get_setting('friend_referral_reward', '100'))
        
        user = db.get_user(user_id)
        if user and user.get('referrer_id'):
            cursor = db.conn.cursor()
            # Проверяем, есть ли уже выполненные задания (кроме текущего)
            cursor.execute(
                "SELECT COUNT(*) as count FROM completed_tasks WHERE user_id = ? AND task_id != ?",
                (user_id, task_id)
            )
            completed_before = cursor.fetchone()['count']
            
            # Начисляем за реферала только если это первое выполненное задание
            if completed_before == 0:
                db.update_user_balance(user['referrer_id'], referral_reward)
                referrer = db.get_user(user['referrer_id'])
                if referrer and referrer.get('referrer_id'):
                    db.update_user_balance(referrer['referrer_id'], friend_referral_reward)
        
        db.complete_task(user_id, task_id)
        user = db.get_user(user_id)
        
        await callback.answer(f"Задание выполнено! Начислено {task['reward']}R", show_alert=True)
        await callback.message.edit_text(
            f"✅ {task['title']}\n\n"
            f"{task['description'] or ''}\n\n"
            f"Начислено: {task['reward']}R\n"
            f"Ваш баланс: {user['balance']:.2f}R"
        )


@router.callback_query(F.data.startswith("check_subscribe_") & ~F.data.startswith("check_subscribe_channels_"))
async def check_subscription(callback: CallbackQuery):
    """Проверка подписки - перенаправляет на функцию с каналами из БД"""
    task_id = int(callback.data.split("_")[-1])
    
    # Меняем data и вызываем функцию напрямую
    original_data = callback.data
    callback.data = f"check_subscribe_channels_{task_id}"
    
    try:
        # Вызываем функцию check_subscribe_channels напрямую
        await check_subscribe_channels(callback)
    finally:
        # Восстанавливаем оригинальный data
        callback.data = original_data


@router.callback_query(F.data == "referral_link")
async def show_referral_link(callback: CallbackQuery):
    user_id = callback.from_user.id
    bot_username = (await callback.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    
    # Получаем награды за рефералов из БД
    referral_reward = int(float(db.get_setting('referral_reward', '350')))
    friend_referral_reward = int(float(db.get_setting('friend_referral_reward', '100')))
    
    text = (
        f"👥 Пригласите друга и получите {referral_reward}R!\n\n"
        f"🔗 Ваша реферальная ссылка:\n{referral_link}\n\n"
        f"💰 За каждого реферала вы получите {referral_reward}R\n"
        f"💰 За реферала вашего реферала - {friend_referral_reward}R"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_earn_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == "open_chest")
async def open_chest(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    # Получаем стоимость сундука из БД
    chest_cost = float(db.get_setting('chest_cost', '2000'))
    
    if not user:
        await callback.answer("Ошибка: пользователь не найден", show_alert=True)
        return
    
    balance = user.get('balance', 0.0)
    if balance < chest_cost:
        await callback.answer(f"Недостаточно средств! Нужно {chest_cost:.0f}R", show_alert=True)
        return
    
    # Списываем стоимость
    db.update_user_balance(user_id, -chest_cost)
    
    # Генерируем промокод
    promo_code = f"CHEST{random.randint(1000, 9999)}"
    
    # Получаем текст и ссылку из настроек
    chest_text = db.get_setting('chest_message_text', '🎁 Поздравляем!\n\nДарим тебе 200FS БЕЗ ДЕПОЗИТА на проекте ... по промокоду {promo_code}')
    chest_link = db.get_setting('chest_project_link', 'https://example.com')
    
    # Заменяем {promo_code} на реальный промокод
    text = chest_text.replace('{promo_code}', promo_code)
    
    # Создаем клавиатуру со ссылкой
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Перейти на проект", url=chest_link)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_earn_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer(f"✅ Сундук открыт! Промокод: {promo_code}", show_alert=True)


@router.callback_query(F.data == "withdraw")
async def start_withdraw(callback: CallbackQuery):
    from config import ADMINS
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    balance = user.get('balance', 0.0)
    is_admin = user_id in ADMINS
    
    text = (
        "💸 Вывод средств\n\n"
        f"Курс: 10 Rcoin = 1 рубль\n"
    )
    
    if is_admin:
        text += f"👑 Режим администратора: можно вывести любую сумму\n"
    else:
        text += f"Минимальный вывод: 5000 Rcoin\n"
    
    text += f"Ваш баланс: {balance:.2f}R"
    
    if not is_admin and balance < 5000:
        text += f"\n\n❌ Недостаточно средств для вывода. Минимум: 5000R"
    
    # Для админов всегда показываем кнопку "Далее", для обычных пользователей - только если баланс >= 5000
    display_balance = balance if not is_admin else max(balance, 5000)  # Для админов всегда >= 5000 для показа кнопки
    await callback.message.edit_text(text, reply_markup=get_withdraw_keyboard(display_balance))


@router.callback_query(F.data == "withdraw_amount")
async def ask_withdraw_amount(callback: CallbackQuery, state: FSMContext):
    from config import ADMINS
    user_id = callback.from_user.id
    is_admin = user_id in ADMINS
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_withdraw_start")]
    ])
    
    text = "💸 Введите сумму для вывода (в Rcoin):"
    if is_admin:
        text += "\n👑 Режим администратора: можно вывести любую сумму"
    else:
        text += f"\nМинимум: 5000R"
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await state.set_state(WithdrawStates.waiting_amount)


@router.message(WithdrawStates.waiting_amount)
async def process_withdraw_amount(message: Message, state: FSMContext):
    from config import ADMINS
    user_id = message.from_user.id
    user = db.get_user(user_id)
    is_admin = user_id in ADMINS
    
    try:
        amount = float(message.text)
        
        # Для админов нет ограничений по минимальной сумме
        if not is_admin and amount < MIN_WITHDRAW:
            await message.answer(f"Минимальная сумма вывода: {MIN_WITHDRAW}R")
            return
        
        # Для админов нет ограничений по балансу
        if not is_admin and amount > user['balance']:
            await message.answer("Недостаточно средств на балансе!")
            return
        
        await state.update_data(amount=amount)
        await message.answer(
            "💸 Выберите способ вывода:",
            reply_markup=get_withdraw_methods_keyboard()
        )
    except ValueError:
        await message.answer("Пожалуйста, введите число!")


@router.callback_query(F.data == "withdraw_site")
async def withdraw_to_site(callback: CallbackQuery, state: FSMContext):
    from config import ADMINS, COIN_TO_RUB
    data = await state.get_data()
    amount = data.get('amount')
    
    if not amount:
        await callback.answer("Ошибка: сумма не указана", show_alert=True)
        return
    
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    is_admin = user_id in ADMINS
    
    # Для админов нет ограничений по балансу
    if not is_admin and amount > user['balance']:
        await callback.answer("Недостаточно средств!", show_alert=True)
        return
    
    # Вычисляем сумму в рублях
    rub_amount = amount / COIN_TO_RUB
    
    # Получаем текст подтверждения из настроек
    confirmation_text = db.get_setting('withdraw_site_confirmation_text', 
        '💸 Подтвердите вывод\n\nСумма: {amount:.0f} Rcoin\n\n📌 Пример: 5000 Rcoin = 1000 рублей на балансе\n\nПодтверждаете вывод?')
    
    # Подставляем сумму в текст
    try:
        text = confirmation_text.format(amount=amount)
    except:
        # Если ошибка форматирования, используем базовый текст
        text = f"💸 Подтвердите вывод\n\nСумма: {amount:.0f} Rcoin\n\n📌 Пример: 5000 Rcoin = 1000 рублей на балансе\n\nПодтверждаете вывод?"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_site_withdraw")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_withdraw_methods")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await state.set_state(WithdrawStates.confirming_site_withdraw)
    await callback.answer()


@router.callback_query(F.data == "confirm_site_withdraw")
async def confirm_site_withdraw(callback: CallbackQuery, state: FSMContext):
    from config import ADMINS, COIN_TO_RUB
    import logging
    logger = logging.getLogger(__name__)
    
    data = await state.get_data()
    amount = data.get('amount')
    
    if not amount:
        await callback.answer("Ошибка: сумма не указана", show_alert=True)
        return
    
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    is_admin = user_id in ADMINS
    
    # Для админов нет ограничений по балансу
    if not is_admin and amount > user['balance']:
        await callback.answer("Недостаточно средств!", show_alert=True)
        return
    
    # Генерируем промокод
    promo_code = f"WITHDRAW{random.randint(10000, 99999)}"
    
    # Создаем заявку на вывод (баланс списывается внутри create_withdrawal)
    withdrawal_id = db.create_withdrawal(user_id, amount, "site", promo_code)
    
    # Отправляем в канал
    from config import WITHDRAWAL_CHANNEL_ID
    try:
        username = user.get('username', 'N/A')
        if username == 'N/A':
            username_text = f"ID: {user_id}"
        else:
            username_text = f"@{username}"
        
        message_text = (
            f"💸 Новая заявка на вывод\n\n"
            f"Пользователь: {username_text}\n"
            f"Сумма: {amount:.0f}R\n"
            f"Способ: Другой способ"
        )
        
        logger.info(f"Попытка отправить уведомление в канал {WITHDRAWAL_CHANNEL_ID}")
        await callback.bot.send_message(
            chat_id=WITHDRAWAL_CHANNEL_ID,
            text=message_text
        )
        logger.info(f"Уведомление успешно отправлено в канал")
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Ошибка при отправке уведомления в канал {WITHDRAWAL_CHANNEL_ID}: {error_msg}", exc_info=True)
        # Также отправляем админу для отладки
        try:
            await callback.bot.send_message(
                ADMINS[0],
                f"⚠️ Ошибка отправки в канал:\n{error_msg}\n\nПроверьте, что бот добавлен в канал как администратор."
            )
        except:
            pass
    
    # Получаем обновленный баланс
    user = db.get_user(user_id)
    
    # Получаем текст успешного вывода из настроек
    success_text = db.get_setting('withdraw_site_success_text', 
        '✅ Заявка на вывод создана!\n\n⏳ Ожидайте исполнения заявки.')
    
    # Получаем ссылку на сайт из настроек
    site_link = db.get_setting('withdraw_site_link', 'https://example.com')
    
    await callback.message.edit_text(
        success_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Ссылка на сайт", url=site_link)]
        ])
    )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "withdraw_usdt")
async def ask_usdt_wallet(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_withdraw_methods")]
    ])
    await callback.message.edit_text(
        "💎 Вывод на USDT (BEP20)\n\n"
        "Комиссия: 3$\n\n"
        "Укажите свой кошелек в формате:\n"
        "0x29E5413420cd856aD2409484BfB600e65c96F777",
        reply_markup=keyboard
    )
    await state.set_state(WithdrawStates.waiting_wallet)


@router.message(WithdrawStates.waiting_wallet)
async def process_usdt_withdraw(message: Message, state: FSMContext):
    from config import ADMINS
    user_id = message.from_user.id
    wallet = message.text.strip()
    is_admin = user_id in ADMINS
    
    # Простая проверка формата кошелька
    if not wallet.startswith("0x") or len(wallet) != 42:
        await message.answer("Неверный формат кошелька! Используйте формат BEP20 (0x...)")
        return
    
    data = await state.get_data()
    amount = data.get('amount')
    
    if not amount:
        await message.answer("Ошибка: сумма не указана")
        return
    
    user = db.get_user(user_id)
    
    # Для админов нет ограничений по балансу
    if not is_admin and amount > user['balance']:
        await message.answer("Недостаточно средств на балансе!")
        return
    
    # Создаем заявку на вывод (баланс списывается внутри create_withdrawal)
    withdrawal_id = db.create_withdrawal(user_id, amount, "usdt", wallet)
    
    # Отправляем в канал
    from config import WITHDRAWAL_CHANNEL_ID, ADMINS
    import logging
    logger = logging.getLogger(__name__)
    try:
        username = user.get('username', 'N/A')
        if username == 'N/A':
            username_text = f"ID: {user_id}"
        else:
            username_text = f"@{username}"
        
        message_text = (
            f"💸 Новая заявка на вывод\n\n"
            f"Пользователь: {username_text}\n"
            f"Сумма: {amount:.0f}R\n"
            f"Способ: USDT (BEP20)\n"
            f"Кошелек: {wallet}"
        )
        
        logger.info(f"Попытка отправить уведомление в канал {WITHDRAWAL_CHANNEL_ID}")
        await message.bot.send_message(
            chat_id=WITHDRAWAL_CHANNEL_ID,
            text=message_text
        )
        logger.info(f"Уведомление успешно отправлено в канал")
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Ошибка при отправке уведомления в канал {WITHDRAWAL_CHANNEL_ID}: {error_msg}", exc_info=True)
        # Также отправляем админу для отладки
        try:
            await message.bot.send_message(
                ADMINS[0],
                f"⚠️ Ошибка отправки в канал:\n{error_msg}\n\nПроверьте, что бот добавлен в канал как администратор."
            )
        except:
            pass
    
    # Получаем текст успешного вывода USDT из настроек
    success_text = db.get_setting('withdraw_usdt_success_text', 
        '✅ Заявка на вывод создана! Проверка качества приглашенных Вами рефералов займет от 1 до 7 рабочих дней. Также вы можете воспользоваться другим способом вывода. Он сразу поступит Вам на баланс.')
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в профиль", callback_data="back_to_profile")]
    ])
    
    await message.answer(
        success_text,
        reply_markup=keyboard
    )
    
    await state.clear()


@router.callback_query(F.data == "back_to_profile")
async def back_to_profile(callback: CallbackQuery, state: FSMContext):
    """Возврат к профилю из процесса вывода"""
    await state.clear()
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    referrer_id = user.get('referrer_id')
    referrer_name = "Нет"
    if referrer_id:
        referrer = db.get_user(referrer_id)
        if referrer:
            referrer_name = f"@{referrer.get('username', '')}" if referrer.get('username') else f"ID: {referrer_id}"
    
    invited_count = db.get_invited_count(user_id)
    
    profile_text = (
        f"👤 Личный кабинет\n\n"
        f"📝 Имя: {user.get('first_name', '')}\n"
        f"🆔 ID: {user_id}\n"
        f"📭 На вывод: {user.get('balance', 0.0):.2f}R\n"
        f"📤 Вывел: {user.get('withdrawn', 0.0):.2f}R\n"
        f"👥 Вас привел: {referrer_name}\n"
        f"💸 Вы пригласили: {invited_count}\n"
    )
    
    from keyboards import get_profile_keyboard
    balance = user.get('balance', 0.0)
    await callback.message.edit_text(profile_text, reply_markup=get_profile_keyboard(balance))
    await callback.answer()


@router.callback_query(F.data == "back_to_withdraw_start")
async def back_to_withdraw_start(callback: CallbackQuery, state: FSMContext):
    """Возврат к началу процесса вывода"""
    from config import ADMINS
    await state.clear()
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    balance = user.get('balance', 0.0)
    is_admin = user_id in ADMINS
    
    text = (
        "💸 Вывод средств\n\n"
        f"Курс: 10 Rcoin = 1 рубль\n"
    )
    
    if is_admin:
        text += f"👑 Режим администратора: можно вывести любую сумму\n"
    else:
        text += f"Минимальный вывод: 5000 Rcoin\n"
    
    text += f"Ваш баланс: {balance:.2f}R"
    
    if not is_admin and balance < 5000:
        text += f"\n\n❌ Недостаточно средств для вывода. Минимум: 5000R"
    
    # Для админов всегда показываем кнопку "Далее"
    display_balance = balance if not is_admin else max(balance, 5000)
    await callback.message.edit_text(text, reply_markup=get_withdraw_keyboard(display_balance))
    await callback.answer()


@router.callback_query(F.data == "back_to_withdraw_methods")
async def back_to_withdraw_methods(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору способа вывода"""
    data = await state.get_data()
    amount = data.get('amount')
    
    if not amount:
        await callback.answer("Ошибка: сумма не указана", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💸 Выберите способ вывода:",
        reply_markup=get_withdraw_methods_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_earn_menu")
async def back_to_earn_menu(callback: CallbackQuery):
    """Возврат в меню заработка"""
    user_id = callback.from_user.id
    keyboard = get_earn_menu_keyboard(user_id)
    
    await callback.message.edit_text(
        "💰 Выберите способ заработка:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("check_subscribe_channels_"))
async def check_subscribe_channels(callback: CallbackQuery):
    """Проверка подписки на все каналы из настроек"""
    user_id = callback.from_user.id
    task_id = int(callback.data.split("_")[-1])
    
    logger.info("=" * 80)
    logger.info(f"🚀 НАЧАЛО ПРОВЕРКИ ПОДПИСКИ: user_id={user_id}, task_id={task_id}")
    logger.info("=" * 80)
    
    # Проверяем и создаем пользователя, если его нет
    user = db.get_user(user_id)
    if not user:
        username = callback.from_user.username or ""
        first_name = callback.from_user.first_name or ""
        db.create_user(user_id, username, first_name, None)
        user = db.get_user(user_id)
        if not user:
            await callback.answer("Ошибка: не удалось создать пользователя", show_alert=True)
            return
    
    channels = db.get_subscribe_channels()
    
    if not channels:
        await callback.answer("Каналы не настроены", show_alert=True)
        return
    
    # Получаем задание для награды
    task = None
    tasks = db.get_tasks()
    for t in tasks:
        if t['task_id'] == task_id:
            task = t
            break
    
    if not task:
        await callback.answer("Задание не найдено!", show_alert=True)
        return
    
    total_channels = len(channels)
    
    if total_channels == 0:
        await callback.answer("Каналы не настроены", show_alert=True)
        return
    
    logger.info(f"🔍 Начинаем проверку {total_channels} каналов для пользователя {user_id}")
    
    # НОВАЯ ЛОГИКА: начисляем за каждый подписанный канал отдельно
    from config import SUBSCRIBE_REWARD
    
    # Получаем награду за один канал (из настроек или из config)
    reward_per_channel = float(db.get_setting('subscribe_reward', str(SUBSCRIBE_REWARD)))
    
    cursor = db.conn.cursor()
    
    # Создаем пользователя если нет
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, username, first_name, balance)
        VALUES (?, ?, ?, 0.0)
    """, (user_id, callback.from_user.username or "", callback.from_user.first_name or ""))
    
    # Проверяем каждый канал отдельно и начисляем за те, за которые еще не начисляли
    total_reward = 0.0
    new_channels_count = 0
    already_rewarded_channels = []
    error_channels = []
    
    for channel in channels:
        channel_id = channel.get('id')
        channel_username = channel.get('channel_username')
        channel_link = channel.get('channel_link', '')
        display_name = channel.get('display_name', channel_username or 'Канал')
        
        if not channel_id:
            continue
        
        # Проверяем подписку на этот канал
        is_subscribed = False
        if channel_username:
            try:
                member = await callback.bot.get_chat_member(f"@{channel_username}", user_id)
                if member.status in ['member', 'administrator', 'creator']:
                    is_subscribed = True
            except Exception as e:
                error_msg = str(e).lower()
                logger.error(f"Ошибка при проверке подписки на канал @{channel_username}: {e}")
                
                # Если критическая ошибка - останавливаем проверку
                if "member list is inaccessible" in error_msg:
                    await callback.answer(
                        f"Ошибка: Бот не может проверить подписку на канал @{channel_username}.\n"
                        f"Убедитесь, что бот добавлен в канал как администратор с правами на просмотр участников.",
                        show_alert=True
                    )
                    return
                elif "chat not found" in error_msg or "bot is not a member" in error_msg:
                    await callback.answer(
                        f"Ошибка: Бот не добавлен в канал @{channel_username} как администратор!",
                        show_alert=True
                    )
                    return
                else:
                    # Другие ошибки - пропускаем этот канал
                    error_channels.append(display_name)
                    continue
        
        # Если подписан и еще не получал награду за этот канал - начисляем
        if is_subscribed:
            if not db.has_received_reward_for_channel(user_id, channel_id):
                # Начисляем за этот канал
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (reward_per_channel, user_id))
                total_reward += reward_per_channel
                new_channels_count += 1
                
                # Отмечаем, что награда получена за этот канал
                db.mark_reward_received_for_channel(user_id, channel_id)
                
                # Сохраняем подписку
                if not channel_link:
                    if channel_username:
                        channel_link = f"https://t.me/{channel_username.replace('@', '')}"
                
                if channel_link:
                    db.add_subscription(user_id, channel_link)
            else:
                already_rewarded_channels.append(display_name)
    
    # Коммитим все изменения
    db.conn.commit()
    
    # Рефералы - начисляем только если это первое задание пользователя
    user = db.get_user(user_id)
    if user and user.get('referrer_id') and new_channels_count > 0:
        referral_reward = float(db.get_setting('referral_reward', '350'))
        friend_referral_reward = float(db.get_setting('friend_referral_reward', '100'))
        
        cursor.execute("SELECT COUNT(*) as count FROM completed_tasks WHERE user_id = ? AND task_id != ?", (user_id, task_id))
        if cursor.fetchone()['count'] == 0:
            db.update_user_balance(user['referrer_id'], referral_reward)
            referrer = db.get_user(user['referrer_id'])
            if referrer and referrer.get('referrer_id'):
                db.update_user_balance(referrer['referrer_id'], friend_referral_reward)
    
    # Формируем ответ
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_earn_menu")]
    ])
    
    if new_channels_count > 0:
        message_text = f"✅ Начислено: {total_reward:.0f}R за {new_channels_count} канал(ов)"
        if already_rewarded_channels:
            message_text += f"\n\nВы уже получили награду за:\n" + "\n".join([f"• {name}" for name in already_rewarded_channels])
        await callback.answer(f"✅ Начислено {total_reward:.0f}R за {new_channels_count} канал(ов)!", show_alert=True)
    else:
        if already_rewarded_channels:
            message_text = f"Вы уже получили награду за все подписанные каналы.\n\nУже награждены:\n" + "\n".join([f"• {name}" for name in already_rewarded_channels])
            await callback.answer("Вы уже получили награду за все каналы", show_alert=True)
        else:
            message_text = "❌ Вы не подписаны ни на один канал.\n\nПодпишитесь на каналы и нажмите 'Проверить' снова."
            if error_channels:
                message_text += f"\n\nНе удалось проверить:\n" + "\n".join([f"• {name}" for name in error_channels])
            await callback.answer("Подпишитесь на каналы для получения награды", show_alert=True)
    
    await callback.message.edit_text(message_text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("check_streams_subscribe_"))
async def check_streams_subscribe(callback: CallbackQuery):
    """Проверка подписки на канал @akatsik для задания 'просмотр стрима'"""
    user_id = callback.from_user.id
    task_id = int(callback.data.split("_")[-1])
    
    # Получаем задание
    task = None
    tasks = db.get_tasks()
    for t in tasks:
        if t['task_id'] == task_id:
            task = t
            break
    
    if not task:
        await callback.answer("Задание не найдено!", show_alert=True)
        return
    
    # Кнопки всегда доступны, но награда начисляется только один раз
    
    # Проверяем подписку на канал @akatsik
    channel_username = "akatsik"
    channel_url = f"https://t.me/{channel_username}"
    is_subscribed = False
    
    logger.info(f"Проверка подписки на канал @{channel_username} для пользователя {user_id} (обработчик check_streams_subscribe)")
    
    try:
        member = await callback.bot.get_chat_member(f"@{channel_username}", user_id)
        logger.info(f"Статус пользователя {user_id} в канале @{channel_username}: {member.status}")
        if member.status in ['member', 'administrator', 'creator']:
            is_subscribed = True
            logger.info(f"Пользователь {user_id} подписан на канал @{channel_username}")
        else:
            logger.info(f"Пользователь {user_id} НЕ подписан на канал @{channel_username} (статус: {member.status})")
    except Exception as e:
        logger.error(f"Ошибка при проверке подписки на канал @{channel_username}: {e}", exc_info=True)
        error_msg = str(e).lower()
        
        if "member list is inaccessible" in error_msg:
            await callback.answer(
                f"Ошибка: Бот не может проверить подписку на канал @{channel_username}.\n"
                f"Убедитесь, что бот добавлен в канал как администратор с правами на просмотр участников.",
                show_alert=True
            )
        elif "chat not found" in error_msg or "bot is not a member" in error_msg:
            await callback.answer(
                f"Ошибка: Бот не добавлен в канал @{channel_username} как администратор!",
                show_alert=True
            )
        else:
            await callback.answer("Ошибка при проверке подписки. Попробуйте позже.", show_alert=True)
        
        # Показываем сообщение с кнопкой подписки
        text = db.get_setting('streams_message_text', task.get('description', task.get('title', '📖 Узнать, как зарабатывать на просмотре трансляций/стримов')))
        
        buttons = [
            [InlineKeyboardButton(
                text="📢 Подписаться на канал",
                url=channel_url
            )],
            [InlineKeyboardButton(
                text="✅ Я подписался, проверить",
                callback_data=f"check_streams_subscribe_{task_id}"
            )],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_earn_menu")]
        ]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
        return
    
    if not is_subscribed:
        # Пользователь не подписан
        logger.info(f"Пользователь {user_id} не подписан на канал @{channel_username}, показываем кнопки подписки")
        base_text = db.get_setting('streams_message_text', task.get('description', task.get('title', '📖 Узнать, как зарабатывать на просмотре трансляций/стримов')))
        # Добавляем явное упоминание, что подписки нет
        text = f"{base_text}\n\n❌ Вы не подписаны на канал.\nПодпишитесь и нажмите «✅ Я подписался, проверить»."
        
        buttons = [
            [InlineKeyboardButton(
                text="📢 Подписаться на канал",
                url=channel_url
            )],
            [InlineKeyboardButton(
                text="✅ Я подписался, проверить",
                callback_data=f"check_streams_subscribe_{task_id}"
            )],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_earn_menu")]
        ]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
        # Здесь показываем алерт, т.к. это явная проверка по кнопке
        await callback.answer("❌ Сначала подпишитесь на канал!", show_alert=True)
        return
    
    # Пользователь подписан - проверяем, получал ли он уже награду
    if db.is_task_completed(user_id, task_id):
        # Уже получил награду - показываем текст с кнопками, но без начисления
        text = db.get_setting('streams_message_text', task.get('description', task.get('title', '📖 Узнать, как зарабатывать на просмотре трансляций/стримов')))
        
        buttons = [
            [InlineKeyboardButton(
                text="📢 Подписаться на канал",
                url=channel_url
            )],
            [InlineKeyboardButton(
                text="✅ Я подписался, проверить",
                callback_data=f"check_streams_subscribe_{task_id}"
            )],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_earn_menu")]
        ]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        return
    
    # Пользователь подписан и еще не получал награду - начисляем награду ОДИН РАЗ
    reward_amount = float(task.get('reward', STREAM_INFO_REWARD))
    
    # Проверяем реферала перед выполнением задания
    referral_reward = float(db.get_setting('referral_reward', '350'))
    friend_referral_reward = float(db.get_setting('friend_referral_reward', '100'))
    
    user = db.get_user(user_id)
    if user and user.get('referrer_id'):
        cursor = db.conn.cursor()
        # Проверяем, есть ли уже выполненные задания (кроме текущего)
        cursor.execute(
            "SELECT COUNT(*) as count FROM completed_tasks WHERE user_id = ? AND task_id != ?",
            (user_id, task_id)
        )
        completed_before = cursor.fetchone()['count']
        
        # Начисляем за реферала только если это первое выполненное задание
        if completed_before == 0:
            db.update_user_balance(user['referrer_id'], referral_reward)
            referrer = db.get_user(user['referrer_id'])
            if referrer and referrer.get('referrer_id'):
                db.update_user_balance(referrer['referrer_id'], friend_referral_reward)
    
    db.update_user_balance(user_id, reward_amount)
    db.complete_task(user_id, task_id)  # Помечаем задание как выполненное - награда только один раз
    
    # Получаем обновленный баланс
    user = db.get_user(user_id)
    
    # Используем настройку из БД для текста сообщения
    text = db.get_setting('streams_message_text', task.get('description', task.get('title', '📖 Узнать, как зарабатывать на просмотре трансляций/стримов')))
    
    # Добавляем информацию о начислении
    text_with_reward = f"{text}\n\n✅ Начислено: {int(reward_amount)}R\n💰 Ваш баланс: {user['balance']:.2f}R"
    
    buttons = [
        [InlineKeyboardButton(
            text="📢 Подписаться на канал",
            url=channel_url
        )],
        [InlineKeyboardButton(
            text="✅ Я подписался, проверить",
            callback_data=f"check_streams_subscribe_{task_id}"
        )],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_earn_menu")]
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.answer(f"✅ Начислено {int(reward_amount)}R!", show_alert=True)
    await callback.message.edit_text(text_with_reward, reply_markup=keyboard)


@router.callback_query(F.data == "back_to_main_menu")
async def back_to_main_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    from keyboards import get_main_menu
    
    # Используем глобальный экземпляр БД, а не создаем новый
    text = db.get_setting(
        'welcome_text',
        "👋 Добро пожаловать!\n\nЭто бот для заработка Rcoin через выполнение заданий.\n\nВыберите действие в меню:"
    )
    
    # Удаляем старое сообщение и отправляем новое с главным меню
    try:
        await callback.message.delete()
    except:
        pass
    
    await callback.message.answer(text, reply_markup=get_main_menu())
    await callback.answer()



