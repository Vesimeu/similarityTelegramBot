import logging

logger = logging.getLogger(__name__)

class SoulService:
    def __init__(self, soul_oracle):
        self.soul_oracle = soul_oracle

    async def generate_prophecy(self, user_id: int):
        try:
            return await self.soul_oracle.generate_prophecy(user_id)
        except Exception as e:
            logger.error(f"Ошибка генерации пророчества: {e}")
            return "Ошибка генерации пророчества" 