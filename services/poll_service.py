import logging
from geopy.distance import geodesic
from collections import defaultdict
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)

class PollService:
    def __init__(self, db, target_chat_id):
        self.db = db
        self.target_chat_id = target_chat_id
        self.min_participation = 2

    async def check_eligible(self, user_id: int) -> Tuple[bool, str]:
        try:
            total_polls = await self.db.polls.count_documents({"chat_id": self.target_chat_id})
            if total_polls < self.min_participation:
                return False, f"Нужно минимум {self.min_participation} опроса"
            user_answers = await self.db.polls.count_documents({"chat_id": self.target_chat_id, "answers.uid": user_id})
            if user_answers < self.min_participation:
                return False, f"Участвуйте min. еще в {self.min_participation-user_answers} @apbaabpa опросах"
            return True, f"Доступно ({user_answers}/{total_polls})"
        except Exception as e:
            logger.error(f"Error in check_eligible: {str(e)}")
            return False, "Ошибка проверки"

    async def get_user_distance(self, user1_id: int, user2_id: int) -> str:
        # TODO: реализовать через _get_user_preferences и _parse_coords
        return "Not implemented"

    async def find_nearby_users(self, user_id: int, radius_km: float = 50) -> List[Dict]:
        # TODO: реализовать через _get_user_preferences и _parse_coords
        return []

    async def generate_report(self, user_id: int, limit: int = 25, sort_by_distance: bool = False) -> str:
        # TODO: реализовать основную логику анализа совпадений
        return "Not implemented"

    # TODO: перенести остальные методы из PollAnalyzer по мере необходимости 