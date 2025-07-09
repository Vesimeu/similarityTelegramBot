from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_HOST, MONGODB_PORT
import logging

logger = logging.getLogger(__name__)

class MongoDB:
    def __init__(self):
        self.client = None
        self.db = None

    async def connect(self):
        try:
            self.client = AsyncIOMotorClient(
                host=MONGODB_HOST,
                port=MONGODB_PORT,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=30000
            )
            await self.client.admin.command('ping')
            self.db = self.client.poll_notify
            logger.info('MongoDB: Успешное подключение')
        except Exception as e:
            logger.critical(f'MongoDB: Ошибка подключения - {str(e)}')
            raise

    def get_collection(self, name):
        if not self.db:
            raise RuntimeError('MongoDB не инициализирован')
        return self.db[name]

    # Пример универсальных функций
    async def get_profile(self, user_id):
        return await self.get_collection('quiz_players').find_one({'user_id': user_id})

    async def update_profile(self, user_id, data):
        return await self.get_collection('quiz_players').update_one(
            {'user_id': user_id},
            {'$set': data},
            upsert=True
        )

    async def get_poll(self, poll_id):
        return await self.get_collection('polls').find_one({'_id': poll_id})

    async def get_admin_settings(self):
        return await self.get_collection('admin_settings').find_one({'_id': 'pairs_display'}) 