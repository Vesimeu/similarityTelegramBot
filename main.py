import asyncio
import logging
from telebot.async_telebot import AsyncTeleBot
from config import BOT_TOKEN, MONGODB_HOST, MONGODB_PORT
from motor.motor_asyncio import AsyncIOMotorClient

# Импорт обработчиков (ВАЖНО: чтобы декораторы сработали)
import handlers.profile
import handlers.matching
import handlers.analyze
import handlers.settings
import handlers.soul
import handlers.admin
import handlers.quest
import handlers.geo

# Импорт сервисов и утилит
from services.profile_service import ProfileService
from services.matching_service import MatchingService
from services.poll_service import PollService
from services.soul_service import SoulService
from services.quest_service import QuestService
from utils.state_service import StateService

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("main")

bot = AsyncTeleBot(BOT_TOKEN)

async def init_db():
    try:
        client = AsyncIOMotorClient(
            host=MONGODB_HOST,
            port=MONGODB_PORT,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=30000
        )
        await client.admin.command('ping')
        db = client.poll_notify
        logger.info("MongoDB: Успешное подключение и проверка")
        return client, db
    except Exception as e:
        logger.critical(f"MongoDB: Ошибка подключения - {str(e)}")
        raise

async def main():
    logger.info("Запуск Telegram-бота...")
    # 1. Подключение к базе данных
    client, db = await init_db()
    logger.info("База данных инициализирована.")

    # 2. Инициализация сервисов (пример)
    profile_service = ProfileService(db)
    matching_service = MatchingService(db)
    poll_service = PollService(db)
    soul_service = SoulService(db)
    quest_service = QuestService(db)
    state_service = StateService()

    logger.info("Сервисы инициализированы.")

    # 3. Вывод списка зарегистрированных хендлеров (по декораторам telebot)
    logger.info("Список зарегистрированных message handlers:")
    for handler in bot.message_handlers:
        logger.info(f"  {handler['filters']} -> {handler['function'].__name__}")
    logger.info("Список зарегистрированных callback_query handlers:")
    for handler in bot.callback_query_handlers:
        logger.info(f"  {handler['filters']} -> {handler['function'].__name__}")

    logger.info("Бот запущен. Ожидание событий...")
    await bot.polling(non_stop=True)

if __name__ == "__main__":
    asyncio.run(main()) 