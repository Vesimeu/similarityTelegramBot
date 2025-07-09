import logging

logger = logging.getLogger(__name__)

class MatchingService:
    def __init__(self, db):
        self.db = db

    async def find_pairs(self, user_id, user_skip_settings):
        """Поиск подходящих анкет по фильтрам пользователя."""
        user = await self.db.quiz_players.find_one({"user_id": user_id})
        if not user:
            return []
        query = {
            "user_id": {"$ne": user_id},
            "$and": [
                {"age": {"$gte": user.get("preferred_age_range", [18, 99])[0], "$lte": user.get("preferred_age_range", [18, 99])[1]}},
                {"preferred_age_range.0": {"$lte": user.get("age", 25)}},
                {"preferred_age_range.1": {"$gte": user.get("age", 25)}},
                {"$or": [
                    {"preferred_gender": user.get("gender")},
                    {"preferred_gender": "Любой"}
                ]},
                {"gender": user.get("preferred_gender")}
            ]
        }
        user_prefs = user.get("preferences", {})
        if user_prefs.get("preferred_city"):
            query["$and"].append({
                "$or": [
                    {"city": user_prefs["preferred_city"]},
                    {"preferences.preferred_city": user_prefs["preferred_city"]}
                ]
            })
        # Применяем skip (если есть)
        skip_count = user_skip_settings.get(user_id, {}).get('permanent', 0)
        pairs = await self.db.quiz_players.find(query).skip(skip_count).limit(600).to_list(None)
        return pairs

    async def get_partner_profile(self, user_id, current_index):
        """Получить профиль партнёра по индексу из результатов поиска."""
        # TODO: оптимизировать — pairs должны храниться в state/session, а не пересчитываться каждый раз
        pairs = await self.find_pairs(user_id, {})
        if 0 <= current_index < len(pairs):
            return pairs[current_index]
        return None

    async def like_partner(self, user_id, partner_id):
        """Обработка симпатии (like) — можно расширить логику (уведомления, статистика)."""
        logger.info(f"User {user_id} liked {partner_id}")
        # TODO: реализовать запись в БД, уведомления, аналитику
        return True

    async def skip_partner(self, user_id, skip_count):
        """Обработка пропуска анкет (skip) — можно расширить логику."""
        logger.info(f"User {user_id} skipped {skip_count} profiles")
        # TODO: реализовать запись в БД, аналитику
        return True 