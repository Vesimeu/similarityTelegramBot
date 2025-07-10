import logging
from aiogram import Bot, Dispatcher, executor, types
from config import BOT_TOKEN
from handlers.start import register_start_handlers

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Регистрируем хендлеры
register_start_handlers(dp)

if __name__ == "__main__":
    logger.info("Запуск Telegram-бота на aiogram 2...")
    executor.start_polling(dp, skip_updates=True)