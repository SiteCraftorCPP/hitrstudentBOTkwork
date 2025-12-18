import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from handlers import start, callbacks, admin, admin_earn

# Настройка логирования в файл и консоль
import logging.handlers
import os

# Создаем директорию для логов, если её нет
os.makedirs('logs', exist_ok=True)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler()  # Также выводим в консоль
    ]
)
logger = logging.getLogger(__name__)
logger.info("=" * 50)
logger.info("БОТ ЗАПУЩЕН - ЛОГИРОВАНИЕ АКТИВНО")
logger.info("=" * 50)


async def main():
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрация роутеров
    # Важно: callbacks.router должен быть ПЕРВЫМ, чтобы FSM состояния обрабатывались раньше
    dp.include_router(callbacks.router)
    dp.include_router(admin.router)  # Админ-панель
    dp.include_router(admin_earn.router)  # Настройки раздела "Начать зарабатывать"
    dp.include_router(start.router)
    
    logger.info("Бот запущен и готов к работе")
    
    try:
        # Запуск бота
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")

