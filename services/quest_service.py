import logging

logger = logging.getLogger(__name__)

class QuestService:
    def __init__(self, quest_engine):
        self.quest_engine = quest_engine

    async def start_quest(self, message):
        # QuestEngine может быть синхронным, обернем в executor если нужно
        try:
            result = self.quest_engine.start_quest(message)
            return result
        except Exception as e:
            logger.error(f"Ошибка запуска квеста: {e}")
            return None 