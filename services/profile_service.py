from db.mongo import MongoDB

class ProfileService:
    def __init__(self, db: MongoDB):
        self.db = db

    async def get_profile(self, user_id):
        return await self.db.get_profile(user_id)

    async def update_profile(self, user_id, data):
        return await self.db.update_profile(user_id, data)

    async def create_profile(self, user_id, first_name, username=None):
        profile = await self.get_profile(user_id)
        if profile:
            return False
        new_profile = {
            'user_id': user_id,
            'name': first_name or 'Новый пользователь',
            'status': 'active',
            'is_completed': False,
            'preferences': {},
        }
        if username:
            new_profile['username'] = username
        result = await self.db.get_collection('quiz_players').insert_one(new_profile)
        return result.inserted_id is not None 