# Конфигурация бота
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN", "8579046645:AAH3YLjnLxUrYNfMy3-xfYJ8qn_mFIpVHxM")

# ID администраторов
ADMINS_STR = os.getenv("ADMINS", "6933111964")
ADMINS = [int(admin_id.strip()) for admin_id in ADMINS_STR.split(",") if admin_id.strip()]

# ID канала для уведомлений о заявках на вывод
WITHDRAWAL_CHANNEL_ID = int(os.getenv("WITHDRAWAL_CHANNEL_ID", "-1003417484899"))

# Настройки валюты
COIN_TO_RUB = int(os.getenv("COIN_TO_RUB", "10"))  # 10 Rcoin = 1 рубль
MIN_WITHDRAW = int(os.getenv("MIN_WITHDRAW", "5000"))  # Минимальный вывод в Rcoin
WITHDRAW_FEE_USDT = int(os.getenv("WITHDRAW_FEE_USDT", "3"))  # Комиссия на вывод USDT в долларах

# Награды
DAILY_BONUS_MIN = int(os.getenv("DAILY_BONUS_MIN", "1"))
DAILY_BONUS_MAX = int(os.getenv("DAILY_BONUS_MAX", "50"))
REFERRAL_REWARD = int(os.getenv("REFERRAL_REWARD", "350"))  # За реферала
FRIEND_REFERRAL_REWARD = int(os.getenv("FRIEND_REFERRAL_REWARD", "100"))  # За реферала друга
SUBSCRIBE_REWARD = int(os.getenv("SUBSCRIBE_REWARD", "100"))  # За подписку
STREAM_INFO_REWARD = int(os.getenv("STREAM_INFO_REWARD", "100"))  # За просмотр информации о стримах
CHEST_COST = int(os.getenv("CHEST_COST", "2000"))  # Стоимость сундука

# База данных
DB_NAME = os.getenv("DB_NAME", "bot_database.db")

# Статистика проекта (для отображения пользователям)
STATS_BASE_USERS = int(os.getenv("STATS_BASE_USERS", "29201"))  # Базовое количество пользователей
STATS_BOT_CREATED = os.getenv("STATS_BOT_CREATED", "12.06.2024г")  # Дата создания бота
STATS_BASE_WITHDRAWN = int(os.getenv("STATS_BASE_WITHDRAWN", "169768"))  # Базовое количество выплаченных рублей

