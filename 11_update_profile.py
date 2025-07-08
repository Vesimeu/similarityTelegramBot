import logging
import random
from telebot import types
from telebot.async_telebot import AsyncTeleBot
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import json
import re
import traceback
import colorama
import math
import aiohttp
from typing import Dict, Any
#import datetime
from pymongo import errors as pymongo_errors
#from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from pymongo import ReturnDocument
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
import sys
import io
from quest_engine import QuestEngine
from bson import Binary
from typing import List, Dict, Tuple
from collections import defaultdict
from typing import Dict, List, Union
from soul_connection import SoulOracle
from datetime import datetime 
from typing import Dict, List
from geopy.distance import geodesic 

from config import BOT_TOKEN, ADMIN_ID, MONGODB_HOST, MONGODB_PORT, TARGET_CHAT_ID
CONTACT_BUTTON_ENABLED = True  # Можно отключать все кнопки контактов

# Настройка кодировки для корректного вывода emoji
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Глобальный словарь для хранения текущих результатов поиска
current_search_results = {}
cache = {}  # Глобальный кеш для хранения профилей
user_data = {}
current_search_settings = {}  # Храним настройки поиска для каждого пользователя
ser_skip_settings = {}      # Новый словарь для хранения настроек пропуска
poll_analyzer = None  # Будет инициализирована в main()

# Глобальные переменные
quiz_players_collection = None
admin_settings_collection = None
awaiting_temp_skip_input = set()

awaiting_skip_input = set()  # Для отслеживания ожидающих ввода 
user_skip_settings = {}  # {'user_id': {'permanent': 1, 'temporary': 5}}
user_skip_settings = {}  # {'user_id': {'permanent': X, 'temporary': Y}}

async def is_contact_available(user_id: int, partner_id: int) -> bool:
    """Проверяет, можно ли связаться с пользователем"""
    try:
        chat = await bot.get_chat(partner_id)
        return True
    except Exception as e:
        logger.debug(f"Контакты пользователя {partner_id} недоступны: {str(e)}")
        return False



# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] - %(levelname)s - %(funcName)s :  %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log")
    ]
)
logger = logging.getLogger(__name__)

logger.info("Бот запускается...")



# Где-то в начале (после импортов):
client = None  # Для AsyncIOMotorClient
db = None      # Для poll_notify

#Функция которая выводит опроы и ответы в них при поиске пар
def get_random_user_answer(user_id,db):
    """Возвращает случайный ответ пользователя с флагом совпадения"""
    try:
        # 1. Найти все опросы, где user_id участвовал
        user_answers = list(db.polls.aggregate([
            {"$match": {"answers.uid": user_id}},
            {"$unwind": "$answers"},
            {"$match": {"answers.uid": user_id}},
            {"$sample": {"size": 1}}  # Случайный ответ
        ]))

        if not user_answers:
            return None

        answer = user_answers[0]['answers']
        question = user_answers[0]['question']
        
        # 2. Проверить, совпадает ли с вашим ответом (заглушка)
        # Здесь нужно будет доработать сравнение с текущим пользователем
        matched = False  # Заглушка - всегда false для первого шага

        return {
            "question": question,
            "option": answer['option'],
            "matched": matched
        }
    except Exception as e:
        logging.error(f"Ошибка поиска ответов: {e}")
        return None



from typing import Dict, Tuple, Optional, List

import logging
from collections import defaultdict
from typing import Dict, Tuple, Optional, List, Any
from pymongo import MongoClient

from geopy.distance import geodesic
from typing import Dict, List, Optional, Tuple, Any
from pymongo import MongoClient
from collections import defaultdict
import logging

class PollAnalyzer:
    def __init__(self, client: MongoClient):
        self.db = client.poll_notify
        self.target_chat_id = TARGET_CHAT_ID
        self.logger = logging.getLogger(__name__)
        self.min_participation = 2

    async def _execute_async(self, coro):
        """Универсальный обработчик асинхронных операций"""
        try:
            return await coro
        except Exception as e:
            self.logger.error(f"Async operation failed: {str(e)}")
            return None

    async def check_answer_match(self, target_user_id: int, seeker_user_id: int) -> bool:
        """Асинхронная проверка совпадений ответов"""
        try:
            polls = await self._execute_async(
                self.db.polls.find({
                    "answers.uid": target_user_id,
                    "chat_id": self.target_chat_id
                }).to_list(None)
            )
            
            if not polls:
                return False

            for poll in polls:
                target_answer = next(
                    (a for a in poll.get('answers', []) 
                     if isinstance(a, dict) and a.get('uid') == target_user_id),
                    None
                )
                seeker_answer = next(
                    (a for a in poll.get('answers', []) 
                     if isinstance(a, dict) and a.get('uid') == seeker_user_id),
                    None
                )

                if all([target_answer, seeker_answer]):
                    if target_answer.get('option') == seeker_answer.get('option'):
                        return True
            return False

        except Exception as e:
            self.logger.error(f"Error in check_answer_match: {str(e)}")
            return False

    def _format_gender(self, gender: Optional[str]) -> str:
        """Форматирование пола с защитой от None"""
        if not isinstance(gender, str):
            return ""
        gender = gender.lower()
        return '♀️' if 'жен' in gender or 'female' in gender else '♂️' if 'муж' in gender or 'male' in gender else ''

    async def check_eligible(self, user_id: int) -> Tuple[bool, str]:
        """Проверка возможности анализа с обработкой ошибок"""
        try:
            total_polls = await self._execute_async(
                self.db.polls.count_documents({"chat_id": self.target_chat_id})
            )
            
            if total_polls < self.min_participation:
                return False, f"Нужно минимум {self.min_participation} опроса"

            user_answers = await self._execute_async(
                self.db.polls.count_documents({
                    "chat_id": self.target_chat_id,
                    "answers.uid": user_id
                })
            )

            if user_answers < self.min_participation:
                return False, f"Участвуйте min. еще в {self.min_participation-user_answers} @apbaabpa опросах"
                
            return True, f"Доступно ({user_answers}/{total_polls})"

        except Exception as e:
            self.logger.error(f"Error in check_eligible: {str(e)}")
            return False, "Ошибка проверки"

    async def _get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """Безопасное получение предпочтений с координатами"""
        try:
            user_data = await self._execute_async(
                self.db.quiz_players.find_one({"user_id": user_id})
            )
            if not user_data:
                return None
                
            # Обработка возраста
            age = user_data.get('age')
            if age is None:
                age = 25
            else:
                try:
                    age = int(age)
                    age = max(18, min(age, 99))
                except (TypeError, ValueError):
                    age = 25
                    
            return {
                'gender': str(user_data.get('gender', '')).lower(),
                'preferred_gender': str(user_data.get('preferred_gender', 'любой')).lower(),
                'preferred_age_range': self._validate_age_range(
                    user_data.get('preferred_age_range', [18, 99])
                ),
                'age': age,
                'name': self._get_best_username(user_data, user_id),
                'username': str(user_data.get('username', '')),
                'user_id': user_id,
                'location': user_data.get('location', '')  # Координаты как строка
            }
        except Exception as e:
            self.logger.error(f"Error in _get_user_preferences: {str(e)}")
            return None


    def _get_best_username(self, user_data: Dict, user_id: int) -> str:
        """Выбирает лучшее доступное имя пользователя"""
        for field in ['name', 'username', 'nick']:
            if user_data.get(field):
                name = str(user_data[field]).strip()
                if name:
                    return name
        return f"Участник {user_id}"

    def _validate_age_range(self, age_range) -> List[int]:
        """Валидация возрастного диапазона"""
        if not isinstance(age_range, list) or len(age_range) != 2:
            return [18, 99]
        return [
            max(18, min(age_range[0], 99)),
            min(99, max(age_range[1], 18))
        ]
    def _parse_coords(self, coord_str: str) -> Optional[Tuple[float, float]]:
        """Парсинг координат из строки 'долгота, широта'"""
        if not coord_str or not isinstance(coord_str, str):
            return None
            
        try:
            # Удаляем возможные скобки и пробелы
            clean_str = coord_str.strip('[] ')
            parts = [p.strip() for p in clean_str.split(',')]
            if len(parts) == 2:
                lon, lat = map(float, parts)
                if -180 <= lon <= 180 and -90 <= lat <= 90:
                    return (lat, lon)  # Для geopy: (широта, долгота)
        except (ValueError, TypeError, AttributeError):
            pass
        return None

    async def get_user_distance(self, user1_id: int, user2_id: int) -> str:
        """Получить расстояние между двумя пользователями"""
        user1 = await self._get_user_preferences(user1_id)
        user2 = await self._get_user_preferences(user2_id)
        
        if not user1 or not user2:
            return "❌ Один из пользователей не найден"
            
        coords1 = self._parse_coords(user1.get('location', ''))
        coords2 = self._parse_coords(user2.get('location', ''))
        
        if not coords1:
            return f"❌ У пользователя {user1_id} нет координат"
        if not coords2:
            return f"❌ У пользователя {user2_id} нет координат"
            
        try:
            distance = geodesic(coords1, coords2).km
            return f"📍 Расстояние: {distance:.1f} км"
        except Exception as e:
            self.logger.error(f"Ошибка расчета расстояния: {str(e)}")
            return "⚠️ Ошибка расчета"
    async def find_nearby_users(self, user_id: int, radius_km: float = 50) -> List[Dict]:
        """Найти пользователей в радиусе"""
        user = await self._get_user_preferences(user_id)
        if not user:
            return []
            
        user_coords = self._parse_coords(user.get('location', ''))
        if not user_coords:
            return []
            
        all_users = await self._execute_async(
            self.db.quiz_players.find({
                "user_id": {"$ne": user_id},
                "location": {"$ne": "", "$exists": True}
            }).to_list(None)
        )
        
        nearby = []
        for u in all_users:
            coords = self._parse_coords(u.get('location', ''))
            if coords:
                distance = geodesic(user_coords, coords).km
                if distance <= radius_km:
                    nearby.append({
                        'user_id': u['user_id'],
                        'name': self._get_best_username(u, u['user_id']),
                        'distance': distance,
                        'age': u.get('age', '?')
                    })
        
        return sorted(nearby, key=lambda x: x['distance'])[:10]  # Топ-10 ближайших    

    async def _get_polls_for_analysis(self) -> List[Dict]:
        """Получение опросов для анализа"""
        try:
            return await self._execute_async(
                self.db.polls.find(
                    {"chat_id": self.target_chat_id},
                    {"answers": 1, "_id": 1}
                ).to_list(None)
            ) or []
        except Exception as e:
            self.logger.error(f"Failed to get polls: {str(e)}")
            return []

    def _extract_user_answers(self, polls: List[Dict], user_id: int) -> Dict:
        """Извлечение ответов пользователя"""
        answers = {}
        for poll in polls:
            for answer in poll.get('answers', []):
                if isinstance(answer, dict) and answer.get('uid') == user_id:
                    answers[poll['_id']] = answer.get('option')
                    break
        return answers

    async def _find_matches(self, polls: List[Dict], user_answers: Dict, seeker_prefs: Dict) -> Dict:
        """Поиск совпадений с другими пользователями с учетом радиуса поиска"""
        matches = defaultdict(int)
        distances = {}  # Будем хранить расстояния до кандидатов
        
        # Получаем координаты и радиус поиска текущего пользователя
        seeker_coords = self._parse_coords(seeker_prefs.get('location', ''))
        if not seeker_coords:
            # Если нет координат - работаем в старом режиме
            return await self._find_matches_without_distance(polls, user_answers, seeker_prefs)
        
        # Получаем радиус поиска (в метрах)
        seeker_radius = await self._get_seeker_radius(seeker_prefs['user_id'])
        if seeker_radius is None:
            # Если радиус не указан - работаем в старом режиме
            return await self._find_matches_without_distance(polls, user_answers, seeker_prefs)
        
        for poll in polls:
            if poll['_id'] not in user_answers:
                continue
                
            for answer in poll.get('answers', []):
                if not isinstance(answer, dict):
                    continue
                    
                candidate_id = answer.get('uid')
                if not candidate_id or candidate_id == seeker_prefs['user_id']:
                    continue
                    
                # Проверяем расстояние до кандидата
                distance = await self._get_candidate_distance(
                    seeker_coords, 
                    candidate_id,
                    seeker_radius
                )
                
                if distance is None:
                    continue  # Пропускаем если нет координат или вне радиуса
                    
                # Сохраняем расстояние для последующей сортировки
                distances[candidate_id] = distance
                    
                candidate_data = await self._get_user_preferences(candidate_id)
                if not candidate_data:
                    continue
                    
                if (self._check_compatibility(seeker_prefs, candidate_data) and
                    answer.get('option') == user_answers[poll['_id']]):
                    matches[candidate_id] += 1
                    
        # Сортируем результаты по расстоянию (от ближних к дальним)
        sorted_matches = dict(sorted(
            matches.items(),
            key=lambda item: distances.get(item[0], float('inf'))
        ))
        
        return sorted_matches

    async def _find_matches_without_distance(self, polls: List[Dict], user_answers: Dict, seeker_prefs: Dict) -> Dict:
        """Оригинальный метод поиска без учета расстояния"""
        matches = defaultdict(int)
        for poll in polls:
            if poll['_id'] not in user_answers:
                continue
                
            for answer in poll.get('answers', []):
                if not isinstance(answer, dict):
                    continue
                    
                candidate_id = answer.get('uid')
                if not candidate_id or candidate_id == seeker_prefs['user_id']:
                    continue
                    
                candidate_data = await self._get_user_preferences(candidate_id)
                if not candidate_data:
                    continue
                    
                if (self._check_compatibility(seeker_prefs, candidate_data) and
                    answer.get('option') == user_answers[poll['_id']]):
                    matches[candidate_id] += 1
                    
        return matches

    async def _get_seeker_radius(self, user_id: int) -> Optional[float]:
        """Получаем радиус поиска пользователя в метрах"""
        try:
            user_data = await self.db.quiz_players.find_one({"user_id": user_id})
            if not user_data or 'km' not in user_data or not user_data['km']:
                return None
                
            # Преобразуем км в метры (для точности)
            return float(user_data['km']) * 1000
        except (ValueError, TypeError):
            return None

    async def _get_candidate_distance(self, seeker_coords: Tuple[float, float], 
                                    candidate_id: int, max_distance: float) -> Optional[float]:
        """Получаем расстояние до кандидата, если оно в пределах max_distance"""
        try:
            candidate_data = await self._get_user_preferences(candidate_id)
            if not candidate_data:
                return None
                
            candidate_coords = self._parse_coords(candidate_data.get('location', ''))
            if not candidate_coords:
                return None
                
            distance_meters = geodesic(seeker_coords, candidate_coords).meters
            return distance_meters if distance_meters <= max_distance else None
        except Exception as e:
            self.logger.error(f"Distance calculation error: {str(e)}")
            return None

    def _check_compatibility(self, seeker_prefs: Dict, candidate_data: Dict) -> bool:
        """Проверка совместимости с защитой от ошибок"""
        try:
            # Проверка пола
            pref_gender = seeker_prefs.get('preferred_gender', 'любой').lower()
            candidate_gender = candidate_data.get('gender', '').lower()
            
            gender_ok = (pref_gender in ['любой', 'any'] or 
                        not candidate_gender or
                        pref_gender == candidate_gender)
            if not gender_ok:
                return False

            # Проверка возраста
            age_range = seeker_prefs.get('preferred_age_range', [18, 99])
            candidate_age = int(candidate_data.get('age', 0))
            return age_range[0] <= candidate_age <= age_range[1]
            
        except Exception:
            return False

    def _format_user_link(self, user_data: Dict) -> str:
        """Генерация безопасной ссылки на пользователя"""
        name = self._sanitize_name(user_data.get('name', f"user_{user_data.get('user_id', '')}"))
        return f'<a href="tg://user?id={user_data.get("user_id")}">{name[:50]}</a>'

    def _sanitize_name(self, name: str) -> str:
        """Очистка имени от лишних пробелов"""
        if not isinstance(name, str):
            return ""
        name = name.strip()
        return name if name and name.lower() != "не указано" else ""

    def _get_match_emoji(self, similarity: float) -> str:
        """Подбор эмодзи для оценки совпадения"""
        if similarity >= 80: return "🟢"
        if similarity >= 60: return "🟡"
        return "🔴"

    async def generate_report(self, user_id: int, limit: int = 25, sort_by_distance: bool = False) -> str:
        """Основной метод генерации отчета"""
        try:
            # Проверка eligibility
            eligible, msg = await self.check_eligible(user_id)
            if not eligible:
                return f"❌ {msg}"

            # Получение данных
            seeker_prefs = await self._get_user_preferences(user_id)
            if sort_by_distance and not seeker_prefs.get('location'):
                return "📍 Для сортировки по расстоянию укажите свою геопозицию в📍 @apbabpa_bot."

            polls = await self._get_polls_for_analysis()
            if not polls:
                return "ℹ️ Нет данных опросов"

            user_answers = self._extract_user_answers(polls, user_id)
            if not user_answers:
                return "ℹ️ Вы не участвовали"

            # Поиск совпадений
            match_stats = await self._find_matches(polls, user_answers, seeker_prefs)
            if not match_stats:
                return "💔 Совпадений нет, проверьте настройки, геопозциию в📍 @apbabpa_bot"

            # Формирование отчета
            return await self._format_match_report(
                user_id, 
                seeker_prefs, 
                user_answers, 
                match_stats, 
                limit, 
                len(polls),
                sort_by_distance
            )
        except Exception as e:
            self.logger.error(f"Report generation failed: {str(e)}")
            return "⚠️ Ошибка генерации отчета"

    

    async def _format_match_report(self, user_id: int, seeker_prefs: Dict, 
                             user_answers: Dict, matches: Dict, limit: int,
                             total_polls: int, sort_by_distance: bool = False) -> str:
        """Улучшенная версия форматирования отчета"""
        try:
            candidates = []
            seeker_coords = self._parse_coords(seeker_prefs.get('location', ''))
            
            for candidate_id, count in matches.items():
                candidate = await self._get_user_preferences(candidate_id)
                if not candidate:
                    continue

                # Получаем координаты кандидата
                candidate_coords = self._parse_coords(candidate.get('location', ''))
                
                # Рассчитываем расстояние
                distance = None
                if seeker_coords and candidate_coords:
                    try:
                        distance = round(geodesic(seeker_coords, candidate_coords).km, 1)
                    except Exception as e:
                        self.logger.error(f"Distance calc error: {str(e)}")
                        distance = None

                # Вычисляем общее количество ответов кандидата
                candidate_answers = await self._execute_async(
                    self.db.polls.count_documents({
                        "chat_id": self.target_chat_id,
                        "answers.uid": candidate_id
                    })
                )
                
                similarity = (count / len(user_answers)) * 100
                candidates.append({
                    'candidate': candidate,
                    'match_count': count,  # Совпавшие ответы
                    'total_answers': len(user_answers),  # Всего ответов пользователя
                    'candidate_total': candidate_answers,  # Всего ответов кандидата
                    'similarity': similarity,
                    'distance': distance
                })

            # Сортировка
            if sort_by_distance:
                candidates.sort(key=lambda x: (
                    x['distance'] if x['distance'] is not None else float('inf'),
                    -x['similarity']
                ))
                title = "🏆 Ближайшие совпадения (по расстоянию)"
            else:
                candidates.sort(key=lambda x: -x['similarity'])
                title = "🏆 Лучшие совпадения (по сходству)"

            # Получаем предпочтения по полу
            preferred_gender = seeker_prefs.get('preferred_gender', 'любой').capitalize()
            if preferred_gender == 'Любой':
                preferred_gender = 'любой пол'

            # Получаем радиус поиска из базы данных
            try:
                user_data = await self.db.quiz_players.find_one({"user_id": seeker_prefs['user_id']})
                search_radius = user_data.get('km', '').strip() if user_data else ''
                radius_text = f"{search_radius} км" if search_radius else "Любой"
            except Exception as e:
                self.logger.error(f"Ошибка получения радиуса поиска: {str(e)}")
                radius_text = "Любой"

            # Формирование отчета
            report_lines = [
                f"{title}",
                f"├ Ищу: {preferred_gender}",
                f"├ Радиус поиска: {radius_text}",
                f"├ Ваши ответы: {len(user_answers)}/{total_polls}",
                f"└ Найдено совпадений: {len(candidates)}\n"
            ]

            for idx, data in enumerate(candidates[:limit], 1):
                candidate = data['candidate']
                # Форматируем расстояние с точностью до 100 метров
                if data['distance'] is not None:
                    if data['distance'] < 1:  # Менее 1 км показываем в метрах
                        distance_text = f"{int(data['distance']*1000)} м"
                    else:
                        distance_text = f"{data['distance']:.1f} км"
                else:
                    distance_text = "—"
                
                report_lines.append(
                    f"{self._get_match_emoji(data['similarity'])} {idx}. "
                    f"{self._format_user_link(candidate)} • "
                    f"{candidate.get('age', '?')} лет {self._format_gender(candidate.get('gender'))} • "
                    f"{data['similarity']:.0f}% ({data['match_count']}/{data['total_answers']}) • "
                    f"{distance_text}"
                )

            report_lines.extend([
                "\nℹ️ Как улучшить результаты:",
                "1. Дабы видеть удаленность вставьте свои координаты 📍@apbabpa_bot",
                "2. Участвуйте в опросах @apbaabpa",
                "3. Вам пророчество /soul_connection",
                "4. Заблокированы? Встречайтесь в @dveoo"
                #"🔹 /report - по сходству",
                #"🔹 /report_distance - по расстоянию"
            ])

            return "\n".join(report_lines)
        except Exception as e:
            self.logger.error(f"Formatting failed: {str(e)}")
            return "⚠️ Ошибка формирования отчета"

# Инициализация бота        
# Инициализация бота        
# Инициализация бота

bot = AsyncTeleBot(BOT_TOKEN)  # Используем токен из config



# Подключение к MongoDB
# Новый блок (line 560) подключения к MongoDB (заменяет старый try-except блок)
async def init_db():
    """Улучшенное подключение к MongoDB с обработкой ошибок"""
    try:
        client = AsyncIOMotorClient(
            host=MONGODB_HOST,
            port=MONGODB_PORT,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=30000
        )
        
        # Проверка подключения
        await client.admin.command('ping')
        db = client.poll_notify
        
        # Проверка доступности коллекции quiz_players
        if 'quiz_players' not in (await db.list_collection_names()):
            logger.warning("Коллекция quiz_players не найдена, будет создана автоматически")
        
        logger.info("MongoDB: Успешное подключение и проверка")
        return client, db  # Возвращаем и клиент, и базу
        
    except ServerSelectionTimeoutError:
        logger.critical("MongoDB: Сервер недоступен (таймаут подключения)")
        raise
    except ConnectionFailure as e:
        logger.critical(f"MongoDB: Ошибка подключения - {str(e)}")
        raise
    except Exception as e:
        logger.critical(f"MongoDB: Неожиданная ошибка - {str(e)}")
        raise

# После инициализации бота Line 592:
quest_engine = QuestEngine(bot)  # Автоподключение к MongoDB
    
# ВСТАВЬТЕ ФУНКЦИЮ ОЧИСТКИ ЗДЕСЬ
async def create_new_profile(user_id: int, first_name: str, username: str = None) -> bool:
    """Создает новый профиль с обязательными полями"""
    if await quiz_players_collection.find_one({"user_id": user_id}):
        return False
    
    # Минимальный валидный профиль
    new_profile = {
        "user_id": user_id,
        "name": first_name or "Новый пользователь",  # Гарантированно не пустое
        
        
        "status": "active",
        "is_completed": False,  # Явно помечаем как незавершенный
        # Все остальные обязательные поля
        "preferences": {
            
            
        }
    }

    try:
        result = await quiz_players_collection.insert_one(new_profile)
        logger.info(f"Создан новый профиль для {user_id}")
        return result.inserted_id is not None
    except Exception as e:
        logger.error(f"Ошибка создания профиля: {e}")
        return False
#ссылка mangu    
@bot.message_handler(commands=['mangu'])  
async def handle_mangu_royal(message: types.Message):  
    # Создаем свиток, окутанный сиянием фей  
    royal_scroll = (  
        "📜 *Волшебный Указ Добросердечных Встреч*\n"  
        "✨ **Запечатано лунным светом и лепестками хрустальных роз** ✨\n\n"  
        "🦋 *Драгоценный гость, свет очей наших!*  \n"  
        "В башне @apbaabpa, где феи плетут нити судеб, а мудрые волшебники бережно хранят каждое слово,  \n"  
        "сегодня открываются врата *Турнира Ласковых Мнений*:\n\n"  
        "🌹 Ваши мысли — как алмазы в короне королевства, и мы ждём их с трепетом  \n"  
        "🕊️ Голубки-посланницы разнесут ваши слова по свету  \n"  
        "🍃 Эльфы-хранители аккуратно сложат каждую идею в шкатулку мудрости  \n\n"  
        "💎 *О, прекрасный странник, как присоединиться к этому дивному действу?*  \n"  
        "1. Проследуйте в хрустальные чертоги: @apbaabpa  \n"  
        "2. Шепните пароль «Лунный свет» стражам-гномам  \n"  
        "3. Окунитесь в море тёплых бесед, где каждому рады!"  
    )  

    # Кнопка с волшебным артефактом  
    markup = types.InlineKeyboardMarkup()  
    castle_button = types.InlineKeyboardButton(  
        text="🔮 Коснуться волшебного зеркала 🔮",  
        url="https://t.me/apbaabpa"  
    )  
    markup.add(castle_button)  

    # Анимация: фея пишет письмо  
    await bot.send_chat_action(message.chat.id, 'typing')  
    await asyncio.sleep(1.2)  
      
    # Появление сказочного герольда  
    herald_msg = await bot.send_message(  
        message.chat.id,  
        "🧚 *Фея-невидимка рассыпает звёздную пыль...*",  
        parse_mode="Markdown"  
    )  
    await asyncio.sleep(0.8)  
      
    # Основное послание  
    await bot.edit_message_text(  
        royal_scroll,  
        chat_id=message.chat.id,  
        message_id=herald_msg.message_id,  
        parse_mode="Markdown",  
        reply_markup=markup,  
        disable_web_page_preview=True  
    )  

    # Исчезающая печать из лепестков  
    seal_msg = await bot.send_message(  
        message.chat.id,  
        "🌺 *Печать Королевы Фей тает в воздухе, оставляя аромат жасмина...*",  
        parse_mode="Markdown"  
    )  
    await asyncio.sleep(1.5)  
    await bot.delete_message(message.chat.id, seal_msg.message_id)

# Обработчик кнопки:
@bot.message_handler(func=lambda m: m.text == "🌺@apbaabpa")
def handle_tournament(message):
    quest_engine.start_quest(message)
# Обработчик команды:
@bot.message_handler(commands=['quest'])
def handle_quest(message):
    quest_engine.start_quest(message)    
    
# КОНЕЦ ВСТАВКИ    
#Универсальный обработчик возраста (добавьте в код)
async def update_age_handler(user_id: int, age_range: str, source: str):
    """Общая функция для обновления возраста из любого источника"""
    try:
        min_age, max_age = map(int, age_range.split('-'))
        
        # Валидация
        if min_age >= max_age:
            raise ValueError("Минимальный возраст должен быть меньше максимального")
        if min_age < 18 or max_age > 100:
            raise ValueError("Допустимый диапазон: 18-100 лет")

        # Обновление в базе
        result = await quiz_players_collection.update_one(
            {"user_id": user_id},
            {"$set": {"preferred_age_range": [min_age, max_age]}},
            upsert=True
        )
        
        logger.info(f"Age updated: user={user_id} range={min_age}-{max_age} source={source}")

        return True
    except Exception as e:
        logger.error(f"Age update failed: {str(e)}")
        return False    
    
#"""Гарантированное обновление возраста в базе"""
async def update_age_in_db(user_id: int, min_age: int, max_age: int) -> bool:
    """Гарантированное обновление возраста в базе"""
    try:
        result = await quiz_players_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "preferred_age_range": [min_age, max_age],
                    "last_modified": datetime.datetime.now()
                },
                "$setOnInsert": {
                    "user_id": user_id,
                    "created_at": datetime.datetime.now()
                }
            },
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id
    except Exception as e:
        logger.error(f"Ошибка обновления возраста, повторите нажатие кнопки: {str(e)}")
        return False
    
# Инициализация настроек по умолчанию, если их нет
async def init_default_settings(db):
    """Инициализирует настройки по умолчанию"""
    try:
        admin_settings_collection = db.admin_settings
        if not await admin_settings_collection.find_one({"_id": "pairs_display"}):
            await admin_settings_collection.insert_one({
                "_id": "pairs_display",
                "show_full_profiles": True,
                "visible_fields": ["name", "age", "city", "gender"],
                "allow_contact": False,
                "last_modified": datetime.datetime.now()
            })
            logger.info("Инициализированы настройки отображения по умолчанию")
    except Exception as e:
        logger.error(f"Ошибка при инициализации настроек MongoDB: {e}")
        raise

# Состояния пользователя
user_data: Dict[int, Dict[str, Any]] = {}  # Хранение состояния пользователя

# Клавиатуры
gender_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
gender_keyboard.add(
    types.KeyboardButton("Мужской"),
    types.KeyboardButton("Женский"),
    #types.KeyboardButton("Любой")
)

preferred_gender_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
preferred_gender_keyboard.add(
    types.KeyboardButton("Мужской"),
    types.KeyboardButton("Женский"),
    #types.KeyboardButton("Любой")
   
)

main_menu_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
main_menu_keyboard.add(
    types.KeyboardButton("Мой профиль"),
    types.KeyboardButton("Найти пару"),
    types.KeyboardButton("Настройки"),
    types.KeyboardButton("📍Где Вы @apbabpa_bot"),
    types.KeyboardButton("Анализ опросов")  # Новая кнопка
)

async def get_display_settings() -> Dict[str, Any]:
    """
    Возвращает настройки отображения профилей.
    Гарантирует наличие всех обязательных полей с fallback-значениями.
    """
    # Стандартные значения (если документ отсутствует или поврежден)
    DEFAULT_SETTINGS = {
        "show_full_profiles": True,
        "visible_fields": ["name", "age", "city", "gender"],
        "allow_contact": False
    }
    
    try:
        # Получаем текущие настройки
        settings = await admin_settings_collection.find_one({"_id": "pairs_display"})
        
        # Если документ не существует, создаем с дефолтными значениями
        if not settings:
            await admin_settings_collection.insert_one({
                "_id": "pairs_display",
                **DEFAULT_SETTINGS
            })
            return DEFAULT_SETTINGS
        
        # Проверяем и дополняем недостающие поля
        validated_settings = {**DEFAULT_SETTINGS, **settings}
        
        # Особые проверки для массивов
        if not isinstance(validated_settings["visible_fields"], list):
            validated_settings["visible_fields"] = DEFAULT_SETTINGS["visible_fields"]
            
        # Логируем несоответствия
        if settings != validated_settings:
            logger.warning(f"Настройки были дополнены: {validated_settings}")
            await admin_settings_collection.update_one(
                {"_id": "pairs_display"},
                {"$set": validated_settings}
            )
            
        return validated_settings
        
    except Exception as e:
        logger.error(f"Критическая ошибка получения настроек: {e}", exc_info=True)
        return DEFAULT_SETTINGS


    
#Функция Всегда сохраняет данные и возвращает статус изменений"""
from pymongo import ReturnDocument

async def update_profile(user_id: int, **kwargs) -> dict:
    """Обновление профиля с гарантированным сохранением и кешированием"""
    try:
        # Нормализация данных
        if 'preferred_keyword' in kwargs:
            kwargs['preferred_keyword'] = kwargs['preferred_keyword'].strip()[:3].lower()

        # Принудительное обновление с возвратом нового документа
        result = await quiz_players_collection.find_one_and_update(
            {"user_id": user_id},
            {
                "$set": kwargs,
                "$setOnInsert": {
                    "created_at": datetime.now(),
                    "is_completed": False,
                    "matches": 0
                },
                "$currentDate": {"last_modified": True}
            },
            upsert=True,
            return_document=ReturnDocument.AFTER
        )

        # Кеширование в памяти
        cache[user_id] = result

        return {
            "success": True,
            "data": result,
            "message": "Данные обновлены"
        }

    except Exception as e:
        logger.error(f"Update failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Ошибка сохранения, повторите процедуру сначала"
        }
    
# ======================================================
# УПРАВЛЕНИЕ РЕЖИМОМ ОТОБРАЖЕНИЯ ПРОФИЛЕЙ
# 
# Команда: /toggle_profile_links_mode
# 
# Функционал:
# - Переключает между режимами отображения результатов поиска:
#   1. 🔗 Режим активных ссылок (кликабельные имена)
#   2. 📄 Текстовый режим (простой текст)
# 
# Требования:
# - Доступ только для администратора (ID: 6865318896)
# - Рабочее подключение к MongoDB
# - Коллекция admin_settings с документом pairs_display
# 
# Логирование:
# - Все изменения фиксируются в bot.log
# - Оповещение администратора о попытках доступа
# ======================================================
@bot.message_handler(commands=['toggle_profile_links_mode'])
async def toggle_profile_links_mode(message: types.Message):
    """
    Переключает режим отображения профилей между:
    - Кликабельными ссылками (режим ВКЛ)
    - Простым текстом (режим ВЫКЛ)
    """
    try:
        # Конфигурация администратора
        # Проверка прав доступа
        if message.from_user.id != ADMIN_ID:
            # Логирование попытки доступа
            logger.warning(
                f"Unauthorized access attempt by {message.from_user.id} "
                f"(@{message.from_user.username})"
            )
            return await bot.reply_to(message, "⛔ Доступ запрещен")
        
        # Получаем текущие настройки
        current_settings = await admin_settings_collection.find_one(
            {"_id": "pairs_display"}
        ) or {"show_full_profiles": True}  # Значение по умолчанию
        
        # Определяем новый режим
        new_mode = not current_settings.get("show_full_profiles", True)
        
        # Обновление базы данных
        update_result = await admin_settings_collection.update_one(
            {"_id": "pairs_display"},
            {"$set": {
                "show_full_profiles": new_mode,
                "last_modified": datetime.datetime.now(),
                "modified_by": message.from_user.id
            }},
            upsert=True
        )
        
        # Формируем ответ пользователю
        response_message = (
            f"🔘 Режим профилей: {'🔗 ССЫЛКИ' if new_mode else '📝 ТЕКСТ'}\n"
            f"🆔 Изменил: {message.from_user.id}\n"
            f"🕒 Время: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"📊 Документов обновлено: {update_result.modified_count}"
        )
        
        await bot.reply_to(message, response_message)
        
        # Дополнительная проверка
        if update_result.modified_count == 0:
            logger.warning("No documents were modified during update")
            
    except pymongo.errors.PyMongoError as db_error:
        logger.critical(f"MongoDB error: {str(db_error)}")
        await bot.reply_to(
            message,
            "💾 Ошибка базы данных! Проверьте:\n"
            "1. Подключение к MongoDB\n"
            "2. Наличие коллекции admin_settings"
        )
        
    except Exception as unexpected_error:
        logger.error(
            f"Unexpected error in toggle_profile_links_mode: {str(unexpected_error)}",
            exc_info=True
        )
        await bot.reply_to(
            message,
            "⚠️ Непредвиденная ошибка! Подробности в логах бота"
        )
        
# Обработчик новых анкет
async def create_new_profile(user_id: int, first_name: str) -> bool:
    """
    Создает новый профиль пользователя с правильной структурой
    Возвращает True если профиль создан, False если уже существовал
    """
    try:
        # Проверяем существование профиля
        if await quiz_players_collection.find_one({"user_id": user_id}):
            return False
            
        new_profile = {
            "user_id": user_id,
            "name": first_name,
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "age": None,
            "username": username,
            "gender": None,
            "city": "",
            "photo_url": None,
            "social_links": {},
            "interests": [],
            "phone": None,
            "email": None,
            "preferred_age_range": [18, 45],
            "preferences": {
                "gender": "Любой",
                "preferred_city": "",
                "preferred_keyword": ""
            },
            "visibility": {
                "name": True,
                "age": True,
                "gender": True,
                "city": True,
                "email": False,
                "photo_url": False,
                "social_links": False,
                "interests": False,
                "phone": False
            },
            "is_completed": False,
            "matches": 0,
            "photos": []
        }

        result = await quiz_players_collection.insert_one(new_profile)
        logger.info(f"Создан новый профиль для {user_id} (имя: {first_name})")
        return result.inserted_id is not None
        
    except Exception as e:
        logger.error(f"Ошибка создания профиля для {user_id}: {str(e)}")
        return False
# ====================== СВИТОК ======================
async def show_welcome_scroll(user_id: int):
    try:
        scroll = """
✨ *Хрустальный Эдикт Светлейшего Совета* ✨

┏━━━━━━━❀•°•⚜•°•❀━━━━━━━┓
   🌌 Драгоценнейшему из ангелов земных,
   бриллианту в оправе нашего сообщества,
   истинному вельможе добрых намерений!

   🌟 *Мудрейшие Духи Радужных Башен повелевают:*
   
   1. Каждое ваше слово — жемчужина в ларце мудрости
   2. Тени невежества пусть растворяются в вашем свете
   3. Анкеты — как крылья ангелов-хранителей

   🕊️ Пусть феи удачи осыпают вас лепестками!
┗━━━━━━━━━━•☽•━━━━━━━━━━┛

🌙 *Примите этот дар сердец, о лучезарный!* 🌙
"""
        await bot.send_message(
            user_id, 
            scroll, 
            parse_mode="Markdown",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton(
                    "🌹 Клянусь перьями феникса!", 
                    callback_data="scroll_accept"
                )
            )
        )
    except Exception as e:
        logger.error(f"Феи-писарки уронили свиток: {e}")
        await bot.send_message(
            user_id, 
            "🦋 Добро пожаловать в сады вечного цветения, светлейший!",
            parse_mode="Markdown"
        )

# ====================== /start ======================
@bot.message_handler(commands=['start'])
async def handle_start(message: types.Message):
    user_id = message.from_user.id
    
    try:
        # Анимация с волшебным свитком, сотканным из лунного света
        scroll_steps = [
            "🌙 *Серебристый свиток судеб нежно разворачивается...* [░░░░░░░░░░]",
            "✨ *Чернила из слез феникса проявляют узоры...* [▓▓░░░░░░░░]",
            "🦢 *Перо ангела выводит ваше имя золотом...* [▓▓▓▓▓░░░░░]",
            "🔮 *Хрустальная печать застывает в воздухе...* [▓▓▓▓▓▓▓▓░░]",
            "💎 *Готово, о драгоценнейший!* [▓▓▓▓▓▓▓▓▓▓]"
        ]
        
        scroll_msg = await bot.send_message(
            user_id, 
            scroll_steps[0],
            parse_mode="Markdown"
        )
        for step in scroll_steps[1:]:
            await asyncio.sleep(0.5)
            await bot.edit_message_text(
                step,
                chat_id=user_id, 
                message_id=scroll_msg.message_id,
                parse_mode="Markdown"
            )
        
        # Проверка в Хрустальных Архивах Эльфийских Мудрецов
        profile = await quiz_players_collection.find_one({"user_id": user_id})
        
        if not profile or not profile.get("is_completed", False):
            await bot.delete_message(user_id, scroll_msg.message_id)
            
            # Для новых светлейших гостей - Церемония Лунного Посвящения
            if not profile or not profile.get("seen_welcome_scroll", False):
                await show_welcome_scroll(user_id)
                await quiz_players_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"seen_welcome_scroll": True}},
                    upsert=True
                )
                return

            # Волшебные эффекты для возвратившихся принцев и принцесс
            for _ in range(3):
                candle = await bot.send_message(user_id, random.choice(["🕯️", "🌟", "🌠"]))
                await asyncio.sleep(0.3)
                await bot.delete_message(user_id, candle.message_id)
            
            # Торжественное приветствие, достойное королей
            welcome_text = (
                "🏰 *Добро пожаловать в Хрустальный Замок Вечной Гармонии, о лучезарный (ая)!*\n\n"
                "💫 *О бриллиант среди вечноживущих,*\n"
                "Ваше присутствие заставляет солнце светить ярче.\n\n"
                "🦚 *Почему наш дворец создан для вас:*\n"
                "🔹 Персональные пророчества от Архимага-Оракула\n"
                "🔹 Покои, защищенные крыльями ангелов-хранителей\n"
                "🔹 Только избранные, чище горного хрусталя\n\n"
                "🌹 *Пусть ваше путешествие будет слаще меда фей!*"
            )
            
            # Королевский указ с печатью единорога
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(
                    "🦄 Создать фамильную реликвию", 
                    callback_data="create_profile"
                )
            )
            
            sent_msg = await bot.send_message(
                user_id,
                "🕊️ Белоснежный пегас доставляет ваше приглашение...",
                parse_mode="Markdown"
            )
            await asyncio.sleep(0.7)
            
            await bot.edit_message_text(
                welcome_text,
                chat_id=user_id,
                message_id=sent_msg.message_id,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Эффект королевского благословения
            for _ in range(3):
                seal = await bot.send_message(user_id, random.choice(["⚜️", "🦄", "👑", "🌹"]))
                await asyncio.sleep(0.4)
                await bot.delete_message(user_id, seal.message_id)
            
        else:
            # Для посвящённых рыцарей и фей двора
            await bot.delete_message(user_id, scroll_msg.message_id)
            
            # Анимация признания высочайшей знати
            for symbol in ["💎", "👑", "🦢", "🌌"]:
                msg = await bot.send_message(user_id, f"{symbol} *Ваш герб сияет ярче звезд!*", parse_mode="Markdown")
                await asyncio.sleep(0.4)
                await bot.delete_message(user_id, msg.message_id)
            
            await bot.send_message(
                user_id,
                "🎭 *О светлейший владыка сердец!*\n"
                "Бальный зал ждет вашего появления.\n\n"
                "Выберите действие из меню, достойное вашего статуса. "
                "Если в Вашем фамильном древе закралась ошибка - я вашим услугам, перепишу ваши свитки /update_profile :",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard
            )
            
    except Exception as e:
        logger.error(f"Волшебные скрипты дали сбой: {e}")
        try:
            await bot.delete_message(user_id, scroll_msg.message_id)
        except:
            pass
        
        # Изысканные сообщения об ошибке
        error_messages = [
            "⚡ *О драгоценный!*\nМагический барьер из крыльев фей преградил путь.",
            "💫 *Ваше сиятельство!*\nДревние руны восстали против правил этикета.",
            "🌪️ *О жемчужина среди вечножителей!*\nВихрь из лепестков роз помешал церемонии."
        ]
        
        for msg_text in error_messages:
            msg = await bot.send_message(
                user_id,
                f"{msg_text}\n\n"
                "🛠️ *Как восстановить гармонию:*\n"
                "1. Посетите Алтарь Обновлений\n"
                "2. Выберите *«Освятить герб заново»*\n"
                "3. Или произнесите заклинание: /update_profile",
                parse_mode="Markdown"
            )
            await asyncio.sleep(0.5)
            await bot.delete_message(user_id, msg.message_id)
        
        await bot.send_message(
            user_id,
            "🏰 *О светлейший из светлейших!*\n"
            "Наши эльфийские писцы уже склонились над исправлением.\n"
            "Пока же, почтительно просим посетить Алтарь (/update_profile)\n"
            "для возобновления магических связей.",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard
        )


async def show_welcome_scroll(user_id: int):
    """Драгоценный Свиток Вежливости для Избранных"""
    try:
        scroll_text = """
✨ *Хрустальный Манускрипт Благородного Общества* ✨

   🦚 *О, сияющий алмаз в оправе нашего собрания!*  🦚

🌸 *Бот специализирован на том , что на основе ваших ответов,*  
🌸 *подбирает близкого по духу, человека:*
🌸 *Для этого нужно ответить на несколько вопросов в @apbaabpa,*
🌸 *Очень важно отметить свою геопозицию 📍@apbabpa_bot,*
🌸 *Чтобы посмотреть результаты нужно пройти регистрацию ниже:*

༺ *Священные Заповеди для Благородных Душ* ༻

▸ Зарегистрируйтесь здесь , введите пол,возраст
▸ далее отвечайте на вопросы в группе @apbaabpa
▸ далее по команде /analyze  смотрите результат

💎 *Привилегии для столь блистательной особы:*
- Персональные рекомендации от придворного оракула
- Только достойнейшие из достойных
- Защита крыльями ангелов-хранителей

🌹 *Как удостоиться чести беседы:*
1. Создать фамильный герб (анкету)
2. Обменяться драгоценными речами в @dveoo
3. Посетить Бальный Зал @apbaabpa


🦢 *Пусть феи удачи осыпают вас лепестками сакуры!* 🦢
"""

        # Анимация с поклоном и поцелуем руки
        scroll_parts = [
            "💌 *Письмо с золотой каймой медленно парит в воздухе...*",
            "🕊️ *Голубь преклоняется перед вашим величием...*",
            "🌹 *Невидимые пажи целуют край свитка...*",
            "👑 *Ваше имя выгравировано на хрустальной пластине...*",
            scroll_text
        ]
        
        # Первый поклон
        msg = await bot.send_message(
            user_id, 
            "*С почтением склоняясь перед вашей красотой...*",
            parse_mode="Markdown"
        )
        await asyncio.sleep(0.7)
        
        # Церемония разворачивания
        for part in scroll_parts:
            await bot.edit_message_text(
                part,
                chat_id=user_id,
                message_id=msg.message_id,
                parse_mode="Markdown"
            )
            await asyncio.sleep(0.8)
        
        # Финальный реверанс с кнопкой
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "💃 С Любовью примем Ваc, далее 🕺", 
                callback_data="create_profile"
            )
        )
        
        await bot.edit_message_reply_markup(
            chat_id=user_id,
            message_id=msg.message_id,
            reply_markup=keyboard
        )
        
        # Эффект рассыпающихся роз
        for _ in range(3):
            flower = await bot.send_message(user_id, random.choice(["🌹", "🌸", "💮"]))
            await asyncio.sleep(0.3)
            await bot.delete_message(user_id, flower.message_id)
        
    except Exception as e:
        logger.error(f"Придворные писцы допустили оплошность: {e}")
        await bot.send_message(
            user_id,
            "🕊️ *О, драгоценнейший!*\n"
            "Наши пажи уронили хрустальное перо...\n"
            "Позвольте начать церемонию заново (/start)",
            parse_mode="Markdown"
        )
        
@bot.callback_query_handler(func=lambda call: call.data == "create_profile")
async def handle_create_profile(call: types.CallbackQuery):
    """Священный Ритуал Внесения в Анналы Вечности"""
    try:
        user_id = call.from_user.id
        
        # 1. Церемониальный ответ с поклоном
        await bot.answer_callback_query(
            call.id,
            text="Вашему великолепию почтительно кланяемся...",
            show_alert=False
        )
        
        # 2. Торжественное удаление свитка
        try:
            await bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение: {e}")
        
        # 3. Анимация с лепестками роз
        for _ in range(2):
            flower_msg = await bot.send_message(call.message.chat.id, "🌹")
            await asyncio.sleep(0.3)
            try:
                await bot.delete_message(call.message.chat.id, flower_msg.message_id)
            except:
                pass
        
        # 4. Установление Священного Этапа
        prophecies = [
            "Вижу в хрустальном шаре - вас ждёт встреча с родственной душой",
            "Феи шепчут, что ваше имя будет сиять золотыми буквами",
            "Оракул предрёк - ваша анкета станет образцом для подражания"
        ]
        
        user_data[user_id] = {
            "step": "waiting_for_name",
            "prophecy": random.choice(prophecies)
        }
        
        # 5. Благословенный запрос имени (без форматирования, вызывающего ошибку)
        request_text = (
            "✨ О, драгоценнейший из вечносчасливейших!\n\n"
            "🦢 Позвольте преклонить колено и попросить:\n"
            " Введите Ваше ИМЯ !\n\n"
            f"📜 Пророчество для вас:\n"
            f"{user_data[user_id]['prophecy']}\n\n"
            "💫 Правила именования:\n"
            "- От 2 до 20 символов\n"
            "- Достойное королевской крови\n"
            "- Введите же Ваше ИМЯ, Ваше наипрекраснейшее ИМЯ"
        )
        
        await bot.send_message(
            call.message.chat.id,
            request_text,
            reply_markup=types.ForceReply()
        )
        
        # 6. Анимация с падающими звёздами
        for _ in range(2):
            star = await bot.send_message(call.message.chat.id, random.choice(["🌠", "🌟"]))
            await asyncio.sleep(0.3)
            try:
                await bot.delete_message(call.message.chat.id, star.message_id)
            except:
                pass
        
    except Exception as e:
        logger.error(f"Ошибка в ритуале: {e}")
        error_msg = await bot.send_message(
            call.message.chat.id,
            "💔 О, светлейший!\n"
            "Хрустальный пергамент разорвался от волнения...\n\n"
            "✨ Но не печальтесь!\n"
            "Наши лучшие каллиграфы уже готовят новый свиток.\n"
            "Произнесите: /update_profile"
        )
        
        # Анимация разбитого сердца
        for symbol in ["💔", "❤️"]:
            try:
                heart = await bot.send_message(call.message.chat.id, symbol)
                await asyncio.sleep(0.5)
                await bot.delete_message(call.message.chat.id, heart.message_id)
            except:
                pass

@bot.message_handler(commands=['test_search'])
async def cmd_test_search(message: types.Message):
    """Ручной тест поиска с выводом сырых данных"""
    user_id = message.from_user.id
    
    # 1. Проверяем, что пользователь — администратор или тестер
    ADMIN_IDS = [ADMIN_ID]  # Замените на ваш ID и тестовые
    if message.from_user.id not in ADMIN_IDS:
        return await bot.reply_to(message, "❌ Команда только для тестирования")
    
    # 2. Получаем и логируем профиль
    profile = await quiz_players_collection.find_one({"user_id": user_id})
    if not profile:
        return await bot.reply_to(message, "❌ Профиль не найден. Сначала заполните /start")
    
    # 3. Формируем отчёт
    report = [
        "🔧 <b>ТЕСТ ПОИСКА</b>",
        f"👤 <b>Ваш профиль</b>:",
        f"- Возраст: {profile.get('age')}",
        f"- Пол: {profile.get('gender')}",
        f"- Диапазон поиска возраста: {profile.get('preferred_age_range', [18, 99])}",
        f"- Город: {profile.get('preferences', {}).get('preferred_city', 'не указан')}",
        f"- Ключ. слово: {profile.get('preferences', {}).get('preferred_keyword', 'не указано')}"
    ]
    
    # 4. Запускаем поиск и добавляем результаты
    await bot.send_message(user_id, "\n".join(report), parse_mode="HTML")
    await find_pair(user_id)  # Ваша основная функция поиска

    # 5. Логируем в консоль (для дебага)
    logger.debug(f"Тестовый поиск для {user_id}:\n{json.dumps(profile, indent=2, default=str)}")
#Кнопки команды ввода координат
    
    
#обновление профиля 
@bot.message_handler(commands=['update_profile'])
async def cmd_update_profile(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    try:
        logger.info(f"Пользователь {user_id} начал обновление профиля.")
        
        # Легкая анимация появления свитка
        scroll_msg = await bot.send_message(
            chat_id,
            "📜 *Свиток анкеты разворачивается...*",
            parse_mode="Markdown"
        )
        await asyncio.sleep(1)
        
        # Анимация подготовки пера
        await bot.edit_message_text(
            "✍️ *Перо окунается в чернила...*",
            chat_id=chat_id,
            message_id=scroll_msg.message_id,
            parse_mode="Markdown"
        )
        await asyncio.sleep(1)
        
        # Удаляем анимацию и запрашиваем имя
        await bot.delete_message(chat_id, scroll_msg.message_id)
        
        # Основной запрос (сохраняем оригинальный текст)
        await bot.send_message(
            user_id,
            "🖋️ Пожалуйста, введите ваше имя:",
            reply_markup=types.ForceReply()
        )
        
        # Сохраняем состояние (как в оригинале)
        user_data[user_id] = {"step": "waiting_for_name", "registration": True}
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_update_profile: {e}")
        # Сохраняем оригинальное поведение при ошибке
        await bot.send_message(user_id, "Пожалуйста, введите ваше имя:")
#регистрация пола 
@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get("step") == "waiting_for_name")
async def handle_name_input(message: types.Message):
    user_id = message.from_user.id
    name = message.text.strip()
    
    try:
        # Волшебная анимация записи имени
        writing_steps = [
            f"🕊️ *Драгоценный(ая) {name}, феи уже шепчут ваше имя на утреннем ветерке...*",
            f"📜 *Мудрые эльф-писцы выводят «{name}» серебряными чернилами...*",
            f"✨ *Хрустальный свиток трепещет от счастья, принимая ваше имя...*"
        ]
        
        writing_msg = await bot.send_message(
            user_id, 
            writing_steps[0],
            parse_mode="Markdown"
        )
        
        for step in writing_steps[1:]:
            await asyncio.sleep(1.2)
            await bot.edit_message_text(
                step,
                chat_id=user_id,
                message_id=writing_msg.message_id,
                parse_mode="Markdown"
            )
        
        # Пророчество о будущем
        prophecies = [
            f"🔮 *Предрекаю:* имя «{name}» принесёт вам встречу с удивительной душой",
            f"🌠 *Оракул шепчет:* под именем «{name}» вас ждёт великая симпатия",
            f"🌸 *Феи нашептали:* «{name}» станет магнитом для добрых сердец"
        ]
        
        if await update_profile(user_id, name=name):
            # Торжественное завершение
            await bot.edit_message_text(
                f"💎 *«{name}» - имя достойное королевской крови!*\n"
                f"{random.choice(prophecies)}\n\n"
                "🦢 *Теперь перо судьбы замерло в ожидании...*",
                chat_id=user_id,
                message_id=writing_msg.message_id,
                parse_mode="Markdown"
            )
            await asyncio.sleep(2)
            
            # Изящный запрос гендера
            gender_request = await bot.send_message(
                user_id,
                "🌹 *О, прекраснейший(ая) из вечноблаженствующих!*\n"
                "Ваш пол Мужской или Женский, каков ваш гендер?\n\n"
                "*Выберите вариант ниже , драгоценный (ая):*",
                parse_mode="Markdown",
                reply_markup=gender_keyboard
            )
            
            # Анимация с падающими лепестками
            for _ in range(2):
                petal = await bot.send_message(user_id, random.choice(["🌸", "🌺"]))
                await asyncio.sleep(0.4)
                await bot.delete_message(user_id, petal.message_id)
            
            user_data[user_id]["step"] = "waiting_for_gender"
            
        else:
            # Поэтичное сообщение об ошибке
            await bot.edit_message_text(
                f"💔 *О, светлейший(ая) {name}!*\n"
                "Чернильные феи уронили хрустальный флакон...\n\n"
                "✨ *Не тревожьтесь!* Просто впишите своё имя ещё раз:",
                parse_mode="Markdown"
            )
            await asyncio.sleep(2)
            await bot.send_message(
                user_id,
                "🖋️ *Попробуйте снова, драгоценный(ая):*",
                parse_mode="Markdown",
                reply_markup=types.ForceReply()
            )
            
    except Exception as e:
        logger.error(f"Ошибка в ритуале именования: {e}")
        await bot.send_message(
            user_id,
            "🌪️ *О, бриллиант среди людей!*\n"
            "Волшебный вихрь помешал нам сохранить ваше имя...\n\n"
            "🕊️ *Позвольте попросить вас написать его ещё раз:*",
            parse_mode="Markdown",
            reply_markup=types.ForceReply()
        )
        
        # Анимация с рассеивающимся туманом
        for symbol in ["🌫️", "✨"]:
            effect = await bot.send_message(user_id, symbol)
            await asyncio.sleep(0.5)
            await bot.delete_message(user_id, effect.message_id)

@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get("step") == "waiting_for_gender")
async def handle_gender_input(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    gender = message.text
    
    try:
        if gender not in ["Мужской", "Женский"]:
            # Анимация для неверного выбора
            wrong_msg = await bot.send_message(
                chat_id,
                "⚔️ *Рыцарь-хранитель хмурится:*\n"
                "🚫 Такого варианта нет в древних свитках!",
                parse_mode="Markdown"
            )
            await asyncio.sleep(1.5)
            await bot.edit_message_text(
                "❌ Пожалуйста, выберите пол из предложенных вариантов:",
                chat_id=chat_id,
                message_id=wrong_msg.message_id
            )
            return

        # Анимация проверки
        check_msg = await bot.send_message(
            chat_id,
            f"🔮 *Магический кристалл проверяет выбранный пол: {gender}...*",
            parse_mode="Markdown"
        )
        await asyncio.sleep(1.5)

        if await update_profile(user_id, gender=gender):
            # Успешная анимация
            await bot.edit_message_text(
                f"✅ *{gender} пол запечатан королевской печатью!*\n"
                "🌙 Теперь он навеки сохранен в архивах Гильдии",
                chat_id=chat_id,
                message_id=check_msg.message_id,
                parse_mode="Markdown"
            )
            await asyncio.sleep(1.5)
            
            # Запрос возраста с оформлением
            await bot.delete_message(chat_id, check_msg.message_id)
            age_msg = await bot.send_message(
                chat_id,
                "🧙 *Мудрец-хронолог вопрошает:*\n"
                "⌛ **Сколько зим вы видели, благородный искатель?**\n\n"
                "_Укажите ваш возраст цифрами (от 18 до 99)_\n"
                "✨ Вы увидите только тех, кто ищет ваш возраст",
                parse_mode="Markdown"
            )
            
            user_data[user_id]["step"] = "waiting_for_age"
            user_data[user_id]["age_msg_id"] = age_msg.message_id
            
        else:
            # Анимация ошибки
            await bot.edit_message_text(
                "💥 *Чернила внезапно воспламенились!*\n"
                "❌ Не удалось сохранить пол",
                chat_id=chat_id,
                message_id=check_msg.message_id,
                parse_mode="Markdown"
            )
            await asyncio.sleep(1.5)
            await bot.send_message(
                chat_id,
                "Попробуйте выбрать пол снова:",
                reply_markup=gender_keyboard
            )
            
    except Exception as e:
        logger.error(f"Ошибка сохранения пола: {e}")
        await bot.send_message(
            chat_id,
            "⚡ *Древние руны сопротивляются!*\n"
            "Попробуйте выбрать пол еще раз:",
            parse_mode="Markdown",
            reply_markup=gender_keyboard
        )

@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get("step") == "waiting_for_age")
async def handle_age_input(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text
    
    try:
        if not text.isdigit():
            # Анимация для неверного формата
            wrong_msg = await bot.send_message(
                chat_id,
                "📜 *Мудрец-каллиграф разглядывает ваши символы:*\n"
                "✖️ Это не похоже на цифры из королевских архивов!",
                parse_mode="Markdown"
            )
            await asyncio.sleep(1.5)
            await bot.edit_message_text(
                "❌ Возраст должен быть числом, благородный странник.",
                chat_id=chat_id,
                message_id=wrong_msg.message_id
            )
            return

        age = int(text)
        
        if not (18 <= age <= 99):
            # Анимация для недопустимого возраста
            scroll_msg = await bot.send_message(
                chat_id,
                f"🧙 *Хранитель времени разворачивает древний свиток:*\n"
                f"⏳ Ваши {age} зим выходят за пределы дозволенного...",
                parse_mode="Markdown"
            )
            await asyncio.sleep(1.5)
            await bot.edit_message_text(
                "❌ Возраст должен быть от 18 до 99 лет, согласно уставу Гильдии.",
                chat_id=chat_id,
                message_id=scroll_msg.message_id
            )
            return

        # Анимация записи в книгу судеб
        record_msg = await bot.send_message(
            chat_id,
            f"📖 *Писарь короля записывает в книгу судеб:*\n"
            f"✍️ Возраст {age} зим заносится в анналы...",
            parse_mode="Markdown"
        )
        await asyncio.sleep(1.5)

        if await update_profile(user_id, age=age):
            # Успешное сохранение
            await bot.edit_message_text(
                f"✅ *{age} зим запечатлено золотыми чернилами!*\n"
                "🔒 Теперь он хранится в королевской библиотеке",
                chat_id=chat_id,
                message_id=record_msg.message_id,
                parse_mode="Markdown"
            )
            await asyncio.sleep(1.5)
            
            # Запрос предпочитаемого возраста
            await bot.delete_message(chat_id, record_msg.message_id)
            pref_msg = await bot.send_message(
                chat_id,
                "🎯 *Лучник-картограф вопрошает ....:*\n"
                "🏹 **В каком диапазоне искать Вам достойных спутников?**\n\n"
                "_О вы само благородство! Укажите предпочитаемый возраст партнера формате 'min-max' (например: 25-35)_\n"
                "✨ Ваше сиятельство вы увидите только тех, чьи предпочтения совпадают с вашим возрастом",
                parse_mode="Markdown"
            )
            
            user_data[user_id]["step"] = "waiting_for_preferred_age"
            user_data[user_id]["pref_msg_id"] = pref_msg.message_id
            
        else:
            # Анимация ошибки записи
            await bot.edit_message_text(
                "💥 *Чернильное пятно испортило пергамент!*\n"
                "❌ Не удалось сохранить возраст в архивах",
                chat_id=chat_id,
                message_id=record_msg.message_id,
                parse_mode="Markdown"
            )
            await asyncio.sleep(1.5)
            await bot.send_message(
                chat_id,
                "Попробуйте ввести возраст снова:"
            )
            
    except Exception as e:
        logger.error(f"Ошибка сохранения возраста: {e}")
        await bot.send_message(
            chat_id,
            "⚡ *Магический барьер преградил путь!*\n"
            "Попробуйте ввести возраст еще раз:",
            parse_mode="Markdown"
        )

@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get("step") == "waiting_for_preferred_age")
async def handle_preferred_age_input(message: types.Message):
    user_id = message.from_user.id
    text = message.text
    chat_id = message.chat.id
    
    try:
        # Проверка формата
        if "-" not in text:
            scroll = await bot.send_message(
                chat_id,
                "📜 *Мудрец-хронолог разворачивает древний свиток:*\n"
                "✖️ *Запись нарушает устав Гильдии!*\n\n"
                "🔮 Используйте формат «min-max» (пример: 25-35)",
                parse_mode="Markdown"
            )
            await asyncio.sleep(2)
            await bot.edit_message_text(
                "📛 Введите диапазон в формате «min-max»:",
                chat_id=chat_id,
                message_id=scroll.message_id
            )
            return

        min_age, max_age = map(int, text.split("-"))
        
        # Проверка корректности диапазона
        if min_age >= max_age:
            raise ValueError("⚔️ *Рыцарь-хранитель качает головой:*\n"
                           "Минимальный возраст должен быть меньше максимального!")
        
        if min_age < 18 or max_age > 100:
            raise ValueError("🧙 *Магический кристалл темнеет:*\n"
                           "Допустимый диапазон: от 18 до 100 зим!")

        # Анимация записи в книгу судеб
        record_msg = await bot.send_message(
            chat_id,
            f"📖 *Писарь короля записывает в книгу судеб:*\n"
            f"✍️ Диапазон {min_age}-{max_age} зим заносится в анналы...",
            parse_mode="Markdown"
        )
        await asyncio.sleep(1.5)

        if await update_profile(user_id, preferred_age_range=[min_age, max_age]):
            # Успешное сохранение
            await bot.edit_message_text(
                f"✅ *Диапазон {min_age}-{max_age} зим скреплен печатью!*\n"
                "🔒 Теперь он хранится в королевской библиотеке",
                chat_id=chat_id,
                message_id=record_msg.message_id,
                parse_mode="Markdown"
            )
            await asyncio.sleep(1)
            
            # Запрос предпочитаемого пола
            await bot.delete_message(chat_id, record_msg.message_id)
            await bot.send_message(
                chat_id,
                "🔮 *Оракул Гильдии вопрошает:*\n"
                "✨ **Кого ищет ваше сердце?**\n\n"
                "_Выберите предпочитаемый пол из свитка_",
                parse_mode="Markdown",
                reply_markup=preferred_gender_keyboard
            )
            
            user_data[user_id]["step"] = "waiting_for_preferred_gender"
            
        else:
            # Анимация ошибки
            await bot.edit_message_text(
                "💥 *Чернильное пятно испортило пергамент!*\n"
                "❌ Не удалось сохранить диапазон в архивах",
                chat_id=chat_id,
                message_id=record_msg.message_id,
                parse_mode="Markdown"
            )
            await asyncio.sleep(1.5)
            await bot.send_message(
                chat_id,
                "Попробуйте ввести диапазон снова:",
                reply_markup=types.ForceReply()
            )
            
    except ValueError as e:
        await bot.send_message(
            chat_id,
            f"⚔️ *Рыцарь-хранитель указывает на ошибку:*\n{str(e)}\n\n"
            "Пример правильного ввода: 25-35",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка сохранения возраста: {str(e)}")
        await bot.send_message(
            chat_id,
            "💥 *Магический барьер разрушен!*\n"
            "🔮 Попробуйте позже, когда магия восстановится",
            parse_mode="Markdown"
        )

@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get("step") == "waiting_for_preferred_gender")
async def handle_preferred_gender_input(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    gender = message.text
    
    try:
        # Проверка выбора
        if gender not in ["Мужской", "Женский", "Любой"]:
            scroll = await bot.send_message(
                chat_id,
                "📜 *Герольд разворачивает устав:*\n"
                "⚔️ Такого варианта нет в королевских хартиях!\n\n"
                "Выберите рыцаря, даму или любой из вариантов:",
                parse_mode="Markdown"
            )
            await asyncio.sleep(2)
            await bot.edit_message_text(
                "🛡️ Пожалуйста, выберите вариант из древнего свитка:",
                chat_id=chat_id,
                message_id=scroll.message_id,
                reply_markup=preferred_gender_keyboard
            )
            return

        # Анимация запечатывания печатью
        seal_msg = await bot.send_message(
            chat_id,
            f"🔮 *Магический кристалл проверяет выбор:*\n"
            f"⚜️ «{gender}»...",
            parse_mode="Markdown"
        )
        await asyncio.sleep(1.5)

        # Обновление в королевских архивах
        result = await quiz_players_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "preferred_gender": gender,
                    "preferences.gender": gender,
                    "last_modified": datetime.now(),
                    "is_completed": True
                }
            }
        )
        
        if result.modified_count > 0:
            # Успешное завершение
            await bot.edit_message_text(
                f"✅ *Королевская печать скрепляет ваш выбор!*\n"
                f"⚜️ Предпочитаемый пол: «{gender}»\n\n"
                "📜 Отныне это записано в анналах Гильдии",
                chat_id=chat_id,
                message_id=seal_msg.message_id,
                parse_mode="Markdown"
            )
            await asyncio.sleep(1)
            
            # Завершение регистрации
            if user_data.get(user_id, {}).get("registration"):
                await bot.send_message(
                    chat_id,
                    "🏰 *Трубы возвещают о завершении регистрации!*\n\n"
                    "🔓 Теперь вам доступны👇:\n"
                    "⚔️ Рыцарский зал знакомств👇\n"
                    "📜 Чат собеседований, @dveoo👇\n"
                    "📜 Локация *@apbabpa_bot*👇\n"
                    "📜 НАСТРОЙКИ 👇\n"
                    "📜 Анализ сходства /analyze 👇\n"
                    "🎭 Турниры сердец @apbaabpa👇",
                    parse_mode="Markdown",
                    reply_markup=main_menu_keyboard
                )
            else:
                await bot.send_message(
                    chat_id,
                    "🛡️ *Сохранено! Воспользуйтесь возможностями королевского замка. Если что то пошло не так меняйте настройки /update_profile*",
                    parse_mode="Markdown",
                    reply_markup=main_menu_keyboard
                )
            
            # Очищаем данные
            if user_id in user_data:
                del user_data[user_id]
                
        else:
            # Если изменения не потребовались
            await bot.edit_message_text(
                "🔹 *Ваш щит уже украшен этим гербом*",
                chat_id=chat_id,
                message_id=seal_msg.message_id,
                parse_mode="Markdown"
            )
            await bot.send_message(
                chat_id,
                "🛡️ Настройки остались прежними",
                reply_markup=main_menu_keyboard
            )
            
    except Exception as e:
        logger.error(f"Ошибка сохранения пола: {e}")
        await bot.send_message(
            chat_id,
            "💥 *Дракон повредил королевские архивы!*\n"
            "🔧 Попробуйте позже, когда маги восстановят порядок",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard
        )
            
# Обработчик сохранения города поиска (адаптированный под ваш стиль)
@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get("step") == "waiting_for_preferred_city")
async def handle_preferred_city_input(message: types.Message):
    user_id = message.from_user.id
    city = message.text.strip()
    
    try:
        # Получаем текущие настройки
        profile = await quiz_players_collection.find_one({"user_id": user_id})
        current_prefs = profile.get("preferences", {}) if profile else {}
        current_city = current_prefs.get("preferred_city", "не указан")

        # Подготовка обновления
        new_prefs = {**current_prefs, "preferred_city": city if city else None}
        
        # Сохраняем в любом случае (даже если город пустой)
        result = await quiz_players_collection.update_one(
            {"user_id": user_id},
            {"$set": {"preferences": new_prefs}},
            upsert=True
        )
        
        # Формируем сообщение
        if not city:
            msg = "✅ Поле 'город поиска' очищено.\nТеперь будут показаны анкеты из всех городов."
            logger.info(f"User {user_id} reset preferred_city (was: {current_city})")
        elif current_city == city:
            msg = f"🔁 Город поиска остался прежним: {city}"
            logger.debug(f"User {user_id} kept same city: {city}")
        else:
            msg = f"✅ Город поиска изменён: {current_city} → {city}"
            logger.info(f"User {user_id} changed city: {current_city} → {city}")

        await bot.send_message(
            user_id,
            msg,
            reply_markup=main_menu_keyboard
        )
        
    except Exception as e:
        error_msg = "❌ Ошибка при сохранении. Попробуйте позже."
        logger.error(f"City save failed for {user_id}: {str(e)}")
        await bot.send_message(user_id, error_msg)
    
    # Всегда сбрасываем состояние
    user_data.pop(user_id, None)
# Где-то в основном файле бота (обычно там где @bot.message_handler)

@bot.message_handler(commands=['distance'])
async def cmd_distance(message: types.Message):
    """Расчет расстояния до другого пользователя"""
    try:
        if len(message.text.split()) < 2:
            await bot.reply_to(message, "Используйте: /distance user_id")
            return
            
        target_id = int(message.text.split()[1])
        response = await analyzer.get_user_distance(
            message.from_user.id,
            target_id
        )
        await bot.reply_to(message, response)
    except Exception as e:
        await bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['nearby'])
async def cmd_nearby(message: types.Message):
    """Поиск пользователей рядом"""
    try:
        # Можно указать радиус: /nearby 100 (по умолчанию 50 км)
        radius = float(message.text.split()[1]) if len(message.text.split()) > 1 else 50.0
        
        nearby_users = await analyzer.find_nearby_users(
            message.from_user.id,
            radius
        )
        
        if not nearby_users:
            await bot.reply_to(message, f"🚷 Никого не найдено в радиусе {radius} км")
            return
            
        response = [f"🏘 Ближайшие пользователи (радиус {radius} км):"]
        for idx, user in enumerate(nearby_users, 1):
            response.append(
                f"{idx}. {user['name']} ({user['age']} лет) - {user['distance']:.1f} км"
            )
            
        await bot.reply_to(message, "\n".join(response))
    except Exception as e:
        await bot.reply_to(message, f"❌ Ошибка: {str(e)}")    
    
#soul_connection    
@bot.message_handler(commands=['soul_connection'])
async def handle_soul_connection(message):
    oracle = SoulOracle(poll_analyzer)
    prophecy = await oracle.generate_prophecy(message.from_user.id)
    await bot.reply_to(message, f"🔮 *Пророчество духов:*\n{prophecy}", parse_mode='Markdown')    

        
#Обработчик ввода-сохранеия ключевого слова
@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get("step") == "waiting_for_preferred_keyword")
async def handle_preferred_keyword_input(message: types.Message):
    user_id = message.from_user.id
    raw_keyword = message.text.strip()
    
    # Нормализация ключевого слова
    keyword = raw_keyword[:3].lower()  # Берём первые 3 символа в нижнем регистре
    
    try:
        # 1. Получаем текущее значение для информативного сообщения
        current_data = await quiz_players_collection.find_one(
            {"user_id": user_id},
            {"preferences.preferred_keyword": 1}
        )
        current_keyword = current_data.get("preferences", {}).get("preferred_keyword", "не установлено") if current_data else "не установлено"
        
        # 2. Всегда сохраняем (даже если слово совпадает)
        result = await quiz_players_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {"preferences.preferred_keyword": keyword},
                "$currentDate": {"last_modified": True}  # Добавляем метку времени
            },
            upsert=True
        )
        
        # 3. Формируем информативное сообщение
        if current_keyword == keyword:
            msg = f"🔁 Ключевое слово осталось прежним: '{keyword}'"
        else:
            msg = f"✅ Изменено: '{current_keyword}' → '{keyword}'"
            
        # 4. Добавляем подсказку
        msg += "\n\nℹ️ Теперь бот будет искать анкеты, содержащие эти буквы"
        
        await bot.send_message(
            user_id,
            msg,
            reply_markup=main_menu_keyboard
        )
        
        logger.info(f"User {user_id} keyword update: {current_keyword} → {keyword}")

    except Exception as e:
        error_msg = f"❌ Ошибка при сохранении ключевого слова: {str(e)}"
        logger.error(f"Keyword save failed for {user_id}: {e}\nInput: '{raw_keyword}'")
        await bot.send_message(
            user_id,
            error_msg,
            reply_markup=main_menu_keyboard
        )
    
    # 5. Всегда сбрасываем состояние
    user_data.pop(user_id, None)
        
# Обработчик выбора предпочитаемого гендера
@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get("step") == "waiting_for_preferred_gender")
async def handle_preferred_gender_input(message: types.Message):
    user_id = message.from_user.id
    gender = message.text
    
    if gender not in ["Мужской", "Женский", "Любой"]:
        await bot.send_message(user_id, "❌ Пожалуйста, выберите пол из предложенных вариантов.")
        return

    try:
        # Обновляем оба поля одновременно
        result = await quiz_players_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "preferred_gender": gender,
                    "preferences.gender": gender,
                    "last_modified": datetime.now()
                }
            }
        )
        
        if result.modified_count > 0:
            await bot.send_message(
                user_id,
                f"✅ Предпочитаемый пол сохранён: {gender}",
                reply_markup=main_menu_keyboard
            )
        else:
            await bot.send_message(
                user_id,
                "⚠️ Настройки не изменились (возможно, вы выбрали тот же пол)",
                reply_markup=main_menu_keyboard
            )
            
    except Exception as e:
        logger.error(f"Ошибка сохранения пола для {user_id}: {str(e)}")
        await bot.send_message(
            user_id,
            "❌ Произошла ошибка при сохранении. Попробуйте позже.",
            reply_markup=main_menu_keyboard
        )
    finally:
        user_data[user_id]["step"] = None

# Обработчик кнопки "Мой профиль"
@bot.message_handler(func=lambda message: message.text == "Мой профиль")
async def handle_my_profile(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} запросил свой профиль.")
    await show_profile(user_id, is_owner=True)

# Функция для отображения профиля с учетом видимости
async def show_profile(user_id, is_owner=False):
    """Отображает профиль пользователя с учетом видимости полей."""
    try:
        profile = await quiz_players_collection.find_one({"user_id": user_id})
        if profile:
            visibility = profile.get("visibility", {
                "name": True,
                "age": True,
                "gender": True,
                "city": True,
                "email": True,
                "photo_url": True,
                "social_links": True,
                "interests": True,
                "phone": True
            })
            profile_message = "👤 Ваш изумительно прекрасный профиль:\n" if is_owner else "👤 Профиль пользователя:\n"

            # Добавляем поля в сообщение только если они видимы или это владелец
            if is_owner or visibility.get("name", True):
                profile_message += f"🔁Имя: {profile.get('name', 'Не указано')}\n"
            if is_owner or visibility.get("age", True):
                profile_message += f"🔁Возраст: {profile.get('age', 'Не указан')}\n"
            if is_owner or visibility.get("gender", True):
                profile_message += f"🔁Гендер: {profile.get('gender', 'Не указан')}\n"
            if is_owner or visibility.get("city", True):
                profile_message += f"Город: {profile.get('city', 'Не указан')}\n"
            if is_owner or visibility.get("preferred_age_range", True):
                profile_message += f"Предпочитаемый возраст: {profile.get('preferred_age_range', 'Не указан')}\n"
            if is_owner or visibility.get("preferences", True):
                profile_message += f"Предпочитаемый гендер: {profile.get('preferences', {}).get('gender', 'Не указан')}\n"
            if is_owner or visibility.get("email", True):
                profile_message += f"Email: {profile.get('email', 'Не указан')}\n"
            if is_owner or visibility.get("photo_url", True):
                profile_message += f"URL: {profile.get('photo_url', 'Не указан')}\n"
            if is_owner or visibility.get("social_links", True):
                profile_message += f"Соцсети: {profile.get('social_links', 'Не указаны')}\n"
            if is_owner or visibility.get("interests", True):
                profile_message += f"Интересы: {profile.get('interests', 'Не указаны')}\n"
            if is_owner or visibility.get("phone", True):
                profile_message += f"Телефон: {profile.get('phone', 'Не указан')}\n"

            await bot.send_message(user_id, profile_message)
        else:
            await bot.send_message(user_id, "❌ Профиль не найден. Сначала заполните профиль.")
    except Exception as e:
        logger.error(f"Ошибка при отображении профиля: {e}", exc_info=True)
        await bot.send_message(user_id, "❌ Произошла ошибка при загрузке профиля.")
        
@bot.message_handler(func=lambda message: message.text == "Найти пару")
async def handle_find_pair(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"Дитя Солнца {user_id} начало священный поиск родственной души.")
    
    # Очищаем временные пути для нового путешествия
    if user_id in user_skip_settings:
        user_skip_settings[user_id]['temporary'] = 0
    
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("🌄 Поиск анкет", callback_data="skip_default"),
        types.InlineKeyboardButton("🦋 Поиск с пропуcком", callback_data="skip_temp")
    )
    
    await bot.send_message(
        user_id,
        f"✨ *О, прекрасный цветок в садах Великого Духа!* ✨\n\n"
        f"🦅 Кондор судьбы принес весть о вашей готовности найти родное сердце.\n\n"
        f"☀️ *Если стеснительность мешает, то встретимся здесь https://parmesan-perm.ru/ :*\n"
        f"• *Путь Мудрого Искателя* - ступайте уверенно, пропуская N анкет навсегда\n"
        f"• *Миг Судьбы* - лишь однажды сверните с тропы, чтобы потом вернуться\n\n"
        f"🌕 *Священное предсказание:*\n"
        f"Вижу в дыме священной травы - ваша судьба уже плетет золотые нити встречи!\n\n"
        f"🌾 *Мудрость предков гласит:*\n"
        f"Чтобы очистить свой путь, сожгите старую анкету в священном огне настроек",
        reply_markup=markup,
        parse_mode="Markdown"
    )
#Обновите обработчик кнопки "Анализ опросов
@bot.message_handler(func=lambda message: message.text == "Анализ опросов")
async def handle_poll_analysis(message: types.Message):
    await handle_analyze(message)
    
# Обработчик выбора режима
@bot.callback_query_handler(func=lambda call: call.data in ["skip_default", "skip_temp"])
async def handle_skip_mode(call: types.CallbackQuery):
    user_id = call.from_user.id
    
    if call.data == "skip_default":
        awaiting_skip_input.add(user_id)
        await bot.send_message(
            user_id,
            "🔢 Введите ПОСТОЯННЫЙ шаг пропуска цифрой (от 0 до 10):\n"
            "Это значение будет использоваться при каждом нажатии 'Далее'.Частые мелькание это  анкеты, котрые не соответсвуют вашему выбору",
            parse_mode="Markdown"
        )
    else:
        awaiting_temp_skip_input.add(user_id)
        await bot.send_message(
            user_id,
            "⏩ Введите количество анкет для РАЗОВОГО пропуска:\n"
            "Например: цифра 20 - это пропустит 20 анкет и продолжит с обычным шагом",
            parse_mode="Markdown"
        )
    
    await bot.answer_callback_query(call.id)
    
#Обработчик постоянного шага (ваш существующий handle_skip_input)
# Обработчик постоянного шага пропуска
@bot.message_handler(func=lambda message: message.from_user.id in awaiting_skip_input)
async def handle_skip_input(message: types.Message):
    user_id = message.from_user.id
    try:
        skip_count = int(message.text)
        if 0 <= skip_count <= 10:
            user_skip_settings[user_id] = {'permanent': skip_count, 'temporary': 0}
            awaiting_skip_input.remove(user_id)
            
            await bot.send_message(
                user_id,
                f"⚙️ Установлен постоянный шаг: {skip_count} анкет\n"
                "🔮 Начинаю поиск...",
                parse_mode="Markdown"
            )
            await find_pair(user_id)
        else:
            await bot.send_message(
                user_id,
                "⚠️ Введите число от 0 до 10",
                parse_mode="Markdown"
            )
    except ValueError:
        await bot.send_message(
            user_id,
            "⚠️ Пожалуйста, введите число",
            parse_mode="Markdown"
        )

# Новый обработчик разового пропуска
@bot.message_handler(func=lambda message: message.from_user.id in awaiting_temp_skip_input)
async def handle_temp_skip_input(message: types.Message):
    user_id = message.from_user.id
    try:
        skip_count = int(message.text)
        if skip_count >= 0:
            # Сохраняем временный пропуск, сохраняя постоянный
            perm = user_skip_settings.get(user_id, {}).get('permanent', 0)
            user_skip_settings[user_id] = {'permanent': perm, 'temporary': skip_count}
            awaiting_temp_skip_input.remove(user_id)
            
            await bot.send_message(
                user_id,
                f"⏩ Будет пропущено {skip_count} анкет (разово)\n"
                f"⚙️ Постоянный шаг: {perm} анкет\n"
                "🔮 Начинаю поиск...",
                parse_mode="Markdown"
            )
            await find_pair(user_id)
        else:
            await bot.send_message(
                user_id,
                "⚠️ Введите положительное число",
                parse_mode="Markdown"
            )
    except ValueError:
        await bot.send_message(
            user_id,
            "⚠️ Пожалуйста, введите число",
            parse_mode="Markdown"
        )
    
    
#Новая функция process_skip_input обрабатывает ввод числа  # Новая функция обработки ввода числа (добавляем ПЕРЕД find_pair)  
# Обработчик ввода числа для пропуска
@bot.message_handler(func=lambda message: message.from_user.id in awaiting_skip_input)
async def handle_skip_input(message: types.Message):
    user_id = message.from_user.id
    
    try:
        skip_count = int(message.text)
        if 0 <= skip_count <= 10:
            user_skip_settings[user_id] = skip_count
            awaiting_skip_input.remove(user_id)
            await bot.send_message(
                user_id,
                f"⚙️ Установлен пропуск: {skip_count} анкет\n"
                "🔮 Начинаю поиск...",
                parse_mode="Markdown"
            )
            await find_pair(user_id)
        else:
            await bot.send_message(
                user_id,
                "⚠️ Введите число от 0 до 10",
                parse_mode="Markdown"
            )
    except ValueError:
        await bot.send_message(
            user_id,
            "⚠️ Пожалуйста, введите число",
            parse_mode="Markdown"
        )    



async def find_pair(user_id: int):
    try:
        user = await quiz_players_collection.find_one({"user_id": user_id})
        if not user:
            await bot.send_message(
                user_id,
                "📜 *О достопочтенный искатель!*\n"
                "Ваша анкета не найдена в королевских архивах.\n"
                "Пожалуйста, завершите обряд посвящения через /start",
                parse_mode="Markdown"
            )
            return

        # Запрос к древним скрижалям
        query = {
            "user_id": {"$ne": user_id},
            "$and": [
                {"age": {
                    "$gte": user.get("preferred_age_range", [18, 99])[0],
                    "$lte": user.get("preferred_age_range", [18, 99])[1]
                }},
                {"preferred_age_range.0": {"$lte": user.get("age", 25)}},
                {"preferred_age_range.1": {"$gte": user.get("age", 25)}},
                {"$or": [
                    {"preferred_gender": user.get("gender")},
                    {"preferred_gender": "Любой"}
                ]},
                {"gender": user.get("preferred_gender")}
            ]
        }

        # Дополнительные пророчества
        user_prefs = user.get("preferences", {})
        if user_prefs.get("preferred_city"):
            query["$and"].append({
                "$or": [
                    {"city": user_prefs["preferred_city"]},
                    {"preferences.preferred_city": user_prefs["preferred_city"]}
                ]
            })

        await bot.send_chat_action(user_id, 'typing')
        
        # Ограничиваем поиск 50 свитками
        pairs = await quiz_players_collection.find(query).limit(600).to_list(None)

        if not pairs:
            await bot.send_message(
                user_id,
                "🌌 *О светлейший!*\n"
                "Нынешние звёзды не благоволят вашим поискам.\n"
                "Возможно, стоит пересмотреть условия гадания в настройках?",
                parse_mode="Markdown"
            )
            return

        current_search_results[user_id] = {
            "pairs": pairs,
            "current_index": 0
        }

        await show_partner_profile(user_id)

    except Exception as e:
        logger.error(f"Ошибка в пророчествах: {str(e)}")
        await bot.send_message(
            user_id,
            "⚡ *О досточтимый!*\n"
            "Древние руны сопротивляются гаданию.\n"
            "Пожалуйста, повторите попытку при следующем восходе луны.",
            parse_mode="Markdown"
        )


async def show_partner_profile(user_id: int):
    if user_id not in current_search_results:
        return await find_pair(user_id)

    data = current_search_results[user_id]
    
    try:
        # Анимация с магическими артефактами
        loading_items = ["🕯️ Свеча зажигается...", "📖 Открывается фолиант...", "⚗️ Алхимик готовит зелье..."]
        loading_msg = await bot.send_message(
            user_id, 
            f"*{random.choice(loading_items)}*\n"
            "🔮 Подготовка к прорицанию...",
            parse_mode="Markdown"
        )
        await asyncio.sleep(0.8)
        
        while data["current_index"] < len(data["pairs"]):
            partner = data["pairs"][data["current_index"]]
            if isinstance(partner, dict) and all(key in partner for key in ['user_id', 'name', 'age', 'gender']):
                break
            data["current_index"] += 1
        else:
            await bot.delete_message(user_id, loading_msg.message_id)
            
            # Торжественное завершение
            await bot.send_message(
                user_id,
                "🏰 *О благороднейший!*\n"
                "Вы изволили просмотреть все доступные свитки.\n\n"
                "🕊️ Возвращайтесь при следующем полнолунии,\n"
                "когда новые искатели явятся в наш замок.",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard
            )
            del current_search_results[user_id]
            return

        partner = data["pairs"][data["current_index"]]
        await bot.delete_message(user_id, loading_msg.message_id)

        # Анимация открытия свитка
        for step in ["📜", "🔓", "✨"]:
            anim_msg = await bot.send_message(user_id, f"*{step} Раскрываем древний свиток...*", parse_mode="Markdown")
            await asyncio.sleep(0.3)
            await bot.delete_message(user_id, anim_msg.message_id)

        # Магические характеристики
        match_percent = random.randint(75, 98)
        days_active = random.randint(1, 365)
        response_rate = random.randint(50, 100)

        # Оформление в стиле рыцарского герба
        # Оформление в стиле рыцарского герба
        # Оформление в стиле рыцарского герба
        profile_text = (
            f"⚜️ *Герб {data['current_index']+1}/{len(data['pairs'])}*\n"
            
            f"┏━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"┃ 🏰 <b>{partner.get('name', 'Таинственный незнакомец')}</b>\n"
            f"┃ 🕰️ Лет: {partner.get('age', '?')}\n"
            f"┃ {'⚔️' if partner.get('gender') == 'Мужской' else '👑'} Род: {partner.get('gender')}\n"
            f"┃ 💞 Ищет: {partner.get('preferred_gender', 'любого')}\n"
            f"┃ 🎯 Желанный возраст: {partner.get('preferred_age_range', ['?', '?'])[0]}-{partner.get('preferred_age_range', ['?', '?'])[1]} зим\n"
            #f"┃ 🏙️ Град: {partner.get('city', 'неизвестен')}\n"
            f"┣━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"┃ 📜 Ответ на свитки: {response_rate}%\n"
            f"┃ 📅 В ордене: {days_active} дней\n"
            f"┃ 💫 Совместимость: {match_percent}%\n"
            f"┗━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"*\"{partner.get('bio', ' я бываю в  чате @dveoo')}\"*\n\n"
            
        )

        # Добавляем случайный ответ отдельным блоком
        async def get_random_user_answer(user_id: int, db):  # ← db как параметр
            try:                
                logger.debug(f"Поиск ответов для user_id: {user_id}")  # <-- Добавить
                poll = await db.polls.find_one({"answers.uid": user_id})
                if poll:
                    logger.info(f"Найден ответ: {poll['answers'][0]['option']}")  # <-- Добавить
                    return {
                        "question": poll.get("question", "Неизвестный вопрос"),
                        "option": poll["answers"][0]["option"],
                        "matched": False
                    }
                return None
            except Exception as e:
                logger.error(f"Ошибка поиска ответов: {e}")
                return None
        profile_text += "🛡️ <i>Ищите📍 @apbabpa_bot друг-друга, в чате @dveoo  и турнире @apbaabpa </i>"


        keyboard = types.InlineKeyboardMarkup()
        
        # Безопасная проверка доступности контакта
        partner_id = partner.get('user_id')
        contact_available = False
        if partner_id and CONTACT_BUTTON_ENABLED:
            try:
                chat = await bot.get_chat(partner_id)
                contact_available = True
            except Exception as e:
                logger.debug(f"Контакт пользователя {partner_id} недоступен: {str(e)}")

        # Рыцарские кнопки
        btn_options = {
            'like': ["⚔️ Послать вызов в чат", "💌 Отправить герб для чата ", "🏆 Пригласить на турнир в чат"],
            'next': ["➡️ Следующий свиток", "📜 Дальше", "⚜️ Продолжить"],
            'prev': ["⬅️ Предыдущий", "↩️ Назад"]
        }

        if contact_available:
            keyboard.add(
                types.InlineKeyboardButton(
                    "✉️ Послать голубя", 
                    url=f"tg://user?id={partner_id}"
                )
            )

        buttons = []
        if data["current_index"] > 0:
            buttons.append(types.InlineKeyboardButton(
                random.choice(btn_options['prev']), 
                callback_data="prev_profile"
            ))
        if data["current_index"] < len(data["pairs"]) - 1:
            buttons.append(types.InlineKeyboardButton(
                random.choice(btn_options['next']), 
                callback_data="next_profile"
            ))
        
        if buttons:
            keyboard.row(*buttons)

        keyboard.add(types.InlineKeyboardButton(
            random.choice(btn_options['like']),
            callback_data=f"like_{partner['user_id']}"
        ))

        try:
            profile_photos = await bot.get_user_profile_photos(partner['user_id'], limit=1)
            if profile_photos and profile_photos.photos:
                await bot.send_photo(
                    user_id,
                    photo=profile_photos.photos[0][0].file_id,
                    caption=profile_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    user_id,
                    "🖼️ *Увы, портрет отсутствует...*\n\n" + profile_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            
            # Финальный магический эффект
            await asyncio.sleep(0.5)
            effect = await bot.send_message(user_id, random.choice(["✨", "🌟", "⚡"]))
            await asyncio.sleep(0.5)
            await bot.delete_message(user_id, effect.message_id)
            
        except Exception as e:
            logger.error(f"Ошибка в магическом ритуале: {e}")
            data["current_index"] += 1
            await show_partner_profile(user_id)
            
    except Exception as e:
        logger.error(f"Проклятие на свитках: {e}")
        await bot.send_message(
            user_id,
            "💢 *О достопочтенный!*\n"
            "Древние духи помешали прорицанию.\n"
            "Пожалуйста, повторите попытку позже.\n\n"
            "🏹 Не забывайте о турнире в @apbaabpa",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard
        )
        
# Модифицированный обработчик навигации
@bot.callback_query_handler(func=lambda call: call.data in ["next_profile", "prev_profile"])
async def handle_navigation(call: types.CallbackQuery):
    user_id = call.from_user.id
    
    if user_id not in current_search_results:
        await bot.answer_callback_query(call.id, "❌ Сессия поиска устарела")
        return

    data = current_search_results[user_id]
    settings = user_skip_settings.get(user_id, {'permanent': 0, 'temporary': 0})
    
    if call.data == "next_profile":
        if data["current_index"] < len(data["pairs"]) - 1:
            # Применяем временный или постоянный пропуск
            skip = settings['temporary'] or settings['permanent']
            new_index = min(data["current_index"] + 1 + skip, len(data["pairs"]) - 1)
            actual_skipped = new_index - data["current_index"] - 1
            
            if actual_skipped > 0:
                await bot.answer_callback_query(
                    call.id, 
                    f"Пропущено {actual_skipped} анкет"
                )
            
            data["current_index"] = new_index
            # Сбрасываем временный пропуск после использования
            if settings['temporary'] > 0:
                user_skip_settings[user_id]['temporary'] = 0
        else:
            await bot.answer_callback_query(call.id, "Это последняя анкета")
            return
            
    elif call.data == "prev_profile":
        if data["current_index"] > 0:
            data["current_index"] -= 1
        else:
            await bot.answer_callback_query(call.id, "Это первая анкета")
            return

    try:
        await bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    
    await show_partner_profile(user_id)
    await bot.answer_callback_query(call.id)
    
@bot.message_handler(func=lambda message: message.text == "Настройки")
async def handle_settings(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"Рыцарь {user_id} вступил в зал королевских указов.")

    try:
        # Получаем текущий профиль из королевских архивов
        profile = await quiz_players_collection.find_one({"user_id": user_id})
        if not profile:
            await bot.send_message(
                user_id,
                "⚔️ *Ваш герб не найден в архивах!*\n"
                "Пройдите обряд посвящения через /start",
                parse_mode="Markdown"
            )
            return

        # Формируем королевский указ с текущими настройками
        prefs = profile.get("preferences", {})
        status_text = (
            "📜 *Королевский Указ о Ваших Предпочтениях*\n\n"
            #f"🏰 *Замок:* `{prefs.get('preferred_city', 'не указан')}`\n"
            #f"🗝️ *Ключ к сердцу:* `{prefs.get('preferred_keyword', 'не указан')}`\n"
            f"🕰️ *Годы поиска:* `{'-'.join(map(str, profile.get('preferred_age_range', ['18', '99'])))} зим`\n"
            f"💘 *Искомый род:* `{profile.get('preferred_gender', 'не указан')}`\n"
            #f"⚔️ *Сходство с другими рыцарями:* `{profile.get('match_percentage', 'еще не рассчитано')}%`"
        )

        # Создаем рыцарский свиток с печатями (кнопками)
        settings_keyboard = types.InlineKeyboardMarkup()
        
        # 1. Блок личных печатей
        settings_keyboard.row(
            types.InlineKeyboardButton("🖋️ Изменить имя", callback_data="change_name"),
            types.InlineKeyboardButton("🕰️ Возраст", callback_data="change_age")
        )
        settings_keyboard.row(
            types.InlineKeyboardButton("⚔️ Мой пол", callback_data="change_gender"),
            #types.InlineKeyboardButton("🏰 Мой замок", callback_data="change_city")
        )
        
        # 2. Блок поиска спутника
        settings_keyboard.row(
            #types.InlineKeyboardButton("🌍 Град поиска", callback_data="change_preferred_city"),
            #types.InlineKeyboardButton("🗝️ Ключевое слово", callback_data="change_preferred_keyword")
        )
        settings_keyboard.row(
            types.InlineKeyboardButton("🕰 Годы партнера(ши)", callback_data="change_preferred_age"),
            types.InlineKeyboardButton("💘 Искомый пол", callback_data="change_preferences_gender")
        )
        
        # 3. Новые кнопки (заготовки)
        settings_keyboard.row(
            #types.InlineKeyboardButton("🛡️ Результат о сходстве", callback_data="show_similarity"),
            #types.InlineKeyboardButton("📜 Интересы", callback_data="show_interests")
        )
        
        # 4. Блок королевских указов
        settings_keyboard.row(
            types.InlineKeyboardButton("✉️ Ваш Email:", callback_data="change_email"),
            types.InlineKeyboardButton("📯 Ваш телефон:", callback_data="change_phone")
        )
        settings_keyboard.row(
            types.InlineKeyboardButton("👁 Видимость в королевстве", callback_data="change_visibility"),
            types.InlineKeyboardButton("♻️ Очистить свою анкету", callback_data="reset_preferences")
        )

        # Анимация разворачивания свитка
        await bot.send_chat_action(message.chat.id, 'typing')
        scroll_msg = await bot.send_message(
            message.chat.id,
            "📜 *Королевский герольд разворачивает свиток...*",
            parse_mode="Markdown"
        )
        await asyncio.sleep(1)
        
        # Отправляем основное сообщение
        await bot.edit_message_text(
            "⚔️ *Зал Королевских Указов*\n\n"
            f"{status_text}\n\n"
            "Выберите печати для поиска:\n"
            "▫️ *Личные настройки* - о радиусе поиска *@apbabpa_bot* \n"
            "▫️ *Исправляйте свой профиль* - */update_profile*\n"
            #"▫️ *Новые пророчества* - ваши интересы\n\n"
            "ℹ️ Выбирая годы спутника, помните:\n"
            "Вам будут доступны лишь те, чьи желания\n"
            "совпадают с вашими годами.\n"
            "*Приглашайте к нам в группу своих знакомых.*",
            chat_id=message.chat.id,
            message_id=scroll_msg.message_id,
            parse_mode="Markdown",
            reply_markup=settings_keyboard
        )

        # Совет мудреца о настройках
        if not prefs.get('preferred_keyword'):
            await bot.send_message(
                message.chat.id,
                "🧙 *Совет королевского мудреца:*\n"
                "Установите *геопозицию в📍 @apbabpa_bot* ,\n"
                "чтобы найти достойных рыцарей и дам.\n"
                "Проголосуйте в: *'@apbaabpa'* → *'далее'*, *'/analyze'*→*'!!!'*\n\n"
                "Приглашайте знакомых в наши знакомства!",
                parse_mode="Markdown"
            )

    except Exception as e:
        logger.error(f"Ошибка в королевских архивах: {e}")
        await bot.send_message(
            message.chat.id,
            "💢 *Проклятие дракона!*\n"
            "Свитки временно недоступны. Попробуйте позже.",
            parse_mode="Markdown"
        )
    
    # Возвращаем рыцаря в главный зал
    try:
        await bot.send_message(
            user_id,
            "🏰 Если геопозиция не указана, установите в📍 @apbabpa_bot или пропустите:",
            reply_markup=main_menu_keyboard
        )
    except:
        pass
# Примерно здесь (после других callback-обработчиков, но до message-обработчиков)
# ==============================================
# Обработчики настроек поиска
# ==============================================
#кнопка выбора предпочитаемого города
@bot.callback_query_handler(func=lambda call: call.data == "change_preferred_city")
async def handle_pref_city(call: types.CallbackQuery):
    """Обработчик изменения города поиска"""
    user_data[call.from_user.id] = {"step": "waiting_for_preferred_city"}
    await bot.send_message(
        call.message.chat.id,
        "🏙 Введите город для поиска партнеров, также Вы можете создать свой виртуальный город для общения:",
        reply_markup=types.ForceReply(selective=True)
    )
#кнопка выбора предпочитаемого слова
@bot.callback_query_handler(func=lambda call: call.data == "change_preferred_keyword")
async def handle_pref_keyword(call: types.CallbackQuery):
    """Обработчик изменения ключевого слова"""
    user_data[call.from_user.id] = {"step": "waiting_for_preferred_keyword"}
    await bot.send_message(
        call.message.chat.id,
        "🔍 Введите ключевое слово (первые 3 буквы):\n"
        "Пример: 'путешествия' → поиск по 'пут'",
        parse_mode="HTML",
        reply_markup=types.ForceReply(selective=True)
    )
# ========== ОБРАБОТЧИК ВОЗРАСТНОГО ДИАПАЗОНА ==========
@bot.callback_query_handler(func=lambda call: call.data == "change_preferred_age")
async def handle_age_button_click(call: types.CallbackQuery):
    """Обработчик кнопки изменения возраста"""
    try:
        user_id = call.from_user.id
        
        # Сохраняем ID оригинального сообщения для возврата
        user_data[user_id] = {
            "step": "waiting_age_range",
            "original_msg_id": call.message.message_id
        }
        
        # Отправляем инструкции с ForceReply
        await bot.send_message(
            call.message.chat.id,
            "🔞 Введите возрастной диапазон (например: 25-35):\n\n"
            "• Минимальный возраст: 18\n"
            "• Максимальный возраст: 100",
            reply_markup=types.ForceReply(selective=True)
        )
        
        await bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике кнопки возраста: {str(e)}")
        await bot.answer_callback_query(call.id, "❌ Ошибка при запросе возраста")
        await bot.send_message(
            call.from_user.id,
            "Что-то пошло не так. Попробуйте снова:",
            reply_markup=main_menu_keyboard
        )

@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get("step") == "waiting_age_range")
async def handle_age_range_input(message: types.Message):
    """Обработчик ввода возрастного диапазона"""
    user_id = message.from_user.id
    state = user_data.get(user_id, {})
    
    try:
        # Удаляем ForceReply сообщение
        try:
            await bot.delete_message(message.chat.id, message.message_id - 1)
        except:
            pass
        
        # Проверка формата
        if "-" not in message.text:
            raise ValueError("Используйте формат 'min-max' (например: 25-35)")
        
        min_age, max_age = map(int, message.text.split("-"))
        
        # Валидация
        if min_age >= max_age:
            raise ValueError("Минимальный возраст должен быть меньше максимального")
        if min_age < 18 or max_age > 100:
            raise ValueError("Допустимый диапазон: 18-100 лет")

        # Анимация сохранения
        saving_msg = await bot.send_message(user_id, "💾 Сохраняем...")
        
        # Сохранение в базу
        await quiz_players_collection.update_one(
            {"user_id": user_id},
            {"$set": {"preferred_age_range": [min_age, max_age]}},
            upsert=True
        )
        
        # Удаляем анимацию
        await bot.delete_message(user_id, saving_msg.message_id)
        
        # Успешное сообщение
        await bot.send_message(
            user_id,
            f"✅ Диапазон сохранён: {min_age}-{max_age} лет",
            reply_markup=main_menu_keyboard
        )
        
        # Восстанавливаем оригинальное сообщение
        try:
            await bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=state["original_msg_id"],
                reply_markup=create_settings_keyboard()
            )
        except:
            pass
            
    except ValueError as e:
        await bot.send_message(
            message.chat.id,
            f"❌ {str(e)}",
            reply_markup=main_menu_keyboard
        )
    except Exception as e:
        logger.error(f"Ошибка сохранения возраста: {str(e)}")
        await bot.send_message(
            message.chat.id,
            "⚠️ Ошибка сервера. Попробуйте позже.",
            reply_markup=main_menu_keyboard
        )
    finally:
        # Гарантированно возвращаем меню и очищаем состояние
        if user_id in user_data:
            del user_data[user_id]
        
        try:
            await bot.send_message(
                message.chat.id,
                "Укажите свою геопозицию📍 @apbabpa_bot или пропустите:",
                reply_markup=main_menu_keyboard
            )
        except:
            pass
            
# ========== ОБРАБОТЧИК ПОЛА ПАРТНЕРА ==========
@bot.callback_query_handler(func=lambda call: call.data == "change_preferences_gender")
async def gender_button_handler(call: types.CallbackQuery):
    """Обработчик кнопки изменения пола"""
    try:
        user_id = call.from_user.id
        user_data[user_id] = {"step": "waiting_gender"}
        await bot.send_message(
            user_id, 
            "Выберите предпочитаемый пол:",
            reply_markup=preferred_gender_keyboard
        )
        await bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"Ошибка в gender_button_handler: {e}")
        await bot.answer_callback_query(call.id, "❌ Ошибка")

@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get("step") == "waiting_gender")
async def gender_selection_handler(message: types.Message):
    """Обработчик выбора пола"""
    user_id = message.from_user.id
    
    try:
        gender = message.text
        if gender not in ["Мужской", "Женский", "Любой"]:
            await bot.send_message(
                user_id,
                "❌ Выберите из предложенных вариантов",
                reply_markup=preferred_gender_keyboard
            )
            return

        # Обновление в базе
        result = await quiz_players_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "preferred_gender": gender,
                    "preferences.gender": gender,
                    "last_modified": datetime.now()
                }
            }
        )
        
        # Удаление клавиатуры
        await bot.send_message(
            user_id,
            "⌛",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await asyncio.sleep(0.3)

        # Результат
        if result.modified_count > 0:
            await bot.send_message(
                user_id,
                f"✅ Пол сохранен: {gender}",
                reply_markup=main_menu_keyboard
            )
        else:
            await bot.send_message(
                user_id,
                "🔹 Настройки не изменились",
                reply_markup=main_menu_keyboard
            )
            
    except Exception as e:
        logger.error(f"Ошибка в gender_selection_handler: {e}")
        await bot.send_message(
            user_id,
            "❌ Ошибка сохранения",
            reply_markup=main_menu_keyboard
        )
    finally:
        # Гарантированная очистка
        if user_id in user_data:
            del user_data[user_id]

# Обработчик для управления видимостью полей
async def handle_visibility_settings(user_id):
    """Управление видимостью полей профиля."""
    try:
        # Получаем профиль пользователя из базы данных
        profile = await quiz_players_collection.find_one({"user_id": user_id})
        if not profile:
            await bot.send_message(user_id, "❌ Профиль не найден.")
            return

        # Получаем текущие настройки видимости
        visibility = profile.get("visibility", {
            "name": True,
            "age": True,
            "gender": True,
            "city": True,
            "email": True,
            "photo_url": True,
            "social_links": True,
            "interests": True,
            "phone": True
        })

        # Создаем сообщение с текущим состоянием видимости
        visibility_status = "👀 Текущая видимость полей:\n"
        for field, is_visible in visibility.items():
            status = "🟢 Видимо" if is_visible else "🔴 Скрыто"
            visibility_status += f"{field.capitalize()}: {status}\n"

        # Создаем клавиатуру для изменения видимости
        visibility_keyboard = types.InlineKeyboardMarkup()
        visibility_keyboard.row(
            types.InlineKeyboardButton("👤 Имя", callback_data="toggle_visibility_name"),
            types.InlineKeyboardButton("🎂 Возраст", callback_data="toggle_visibility_age"),
            types.InlineKeyboardButton("🚻 Гендер", callback_data="toggle_visibility_gender")
        )
        visibility_keyboard.row(
            types.InlineKeyboardButton("🏙️ Город", callback_data="toggle_visibility_city"),
            types.InlineKeyboardButton("📧 Email", callback_data="toggle_visibility_email"),
            types.InlineKeyboardButton("🌐 URL", callback_data="toggle_visibility_url")
        )
        visibility_keyboard.row(
            types.InlineKeyboardButton("🔗 Соцсети", callback_data="toggle_visibility_social_links"),
            types.InlineKeyboardButton("🎨 Интересы", callback_data="toggle_visibility_interests"),
            types.InlineKeyboardButton("📞 Телефон", callback_data="toggle_visibility_phone")
        )

        # Отправляем сообщение с текущими настройками видимости
        await bot.send_message(user_id, visibility_status, reply_markup=visibility_keyboard)
    except Exception as e:
        logger.error(f"Ошибка при отображении настроек видимости: {e}", exc_info=True)
        await bot.send_message(user_id, "❌ Произошла ошибка при загрузке настроек видимости.")

# Обработчик для переключения видимости полей
@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_visibility_"))
async def handle_toggle_visibility(call: types.CallbackQuery):
    user_id = call.from_user.id
    field = call.data.replace("toggle_visibility_", "")
    logger.info(f"Пользователь {user_id} изменил видимость поля: {field}")

    try:
        # Получаем текущее состояние видимости
        profile = await quiz_players_collection.find_one({"user_id": user_id})
        if not profile:
            await bot.answer_callback_query(call.id, "❌ Профиль не найден.")
            return

        # Инициализируем поле visibility, если его нет
        visibility = profile.get("visibility", {
            "name": True,
            "age": True,
            "gender": True,
            "city": True,
            "email": True,
            "photo_url": True,
            "social_links": True,
            "interests": True,
            "phone": True
        })

        # Переключаем видимость
        visibility[field] = not visibility.get(field, True)

        # Обновляем профиль в MongoDB
        result = await quiz_players_collection.update_one(
            {"user_id": user_id},
            {"$set": {"visibility": visibility}}
        )

        # Логируем результат обновления
        if result.modified_count > 0:
            logger.info(f"Видимость поля '{field}' успешно обновлена для пользователя {user_id}.")
        else:
            logger.warning(f"Не удалось обновить видимость поля '{field}' для пользователя {user_id}.")

        # Отправляем уведомление пользователю
        status = "видимо" if visibility[field] else "скрыто"
        await bot.answer_callback_query(call.id, f"✅ Поле '{field}' теперь {status}.")

        # Обновляем меню настроек видимости
        await handle_visibility_settings(user_id)
    except Exception as e:
        logger.error(f"Ошибка при обновлении видимости: {e}", exc_info=True)
        await bot.answer_callback_query(call.id, "❌ Произошла ошибка при обновлении видимости.")
 # ▼▼▼ ВСТАВЛЯЕМ ПОСЛЕ ДРУГИХ CALLBACK-ОБРАБОТЧИКОВ НАСТРОЕК ▼▼▼
@bot.callback_query_handler(func=lambda call: call.data == "reset_preferences")
async def handle_reset_preferences(call: types.CallbackQuery):
    user_id = call.from_user.id
    try:
        current_profile = await quiz_players_collection.find_one({"user_id": user_id})
        current_name = current_profile.get("name", "")
        
        await quiz_players_collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "name": current_name,
                "age": None,
                "gender": None,
                "city": None,
                "photo_url": None,
                "preferences": {
                    "gender": "Любой",
                    "preferred_city": "",
                    "preferred_keyword": ""
                },
                "visibility": {
                    "name": True,
                    "age": True,
                    "gender": True,
                    "city": True,
                    "email": False,
                    "photo_url": False,
                    "social_links": False,
                    "interests": False,
                    "phone": False
                }
            }}
        )

        
        await bot.answer_callback_query(call.id, "✅ Все настройки сброшены")
        await show_profile(call.from_user.id, is_owner=True)
        
    except Exception as e:
        logger.error(f"Reset error: {str(e)}")
        await bot.answer_callback_query(call.id, "❌ Ошибка сброса", show_alert=True)
# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲       

# Обработчик callback-запросов
@bot.callback_query_handler(func=lambda call: True)
async def handle_callback(call: types.CallbackQuery):
    user_id = call.from_user.id
    data = call.data
    logger.info(f"Пользователь {user_id} нажал на кнопку: {data}")

    if data == "change_name":
        user_data[user_id] = {"step": "waiting_for_new_name"}
        await bot.send_message(user_id, "Введите ваше новое имя:")
    elif data == "change_age":
        user_data[user_id] = {"step": "waiting_for_new_age"}
        await bot.send_message(user_id, "Введите ваш новый возраст:")
    elif data == "change_gender":
        user_data[user_id] = {"step": "waiting_for_new_gender"}
        await bot.send_message(user_id, "Выберите ваш новый пол:", reply_markup=gender_keyboard)
    elif data == "change_city":
        user_data[user_id] = {"step": "waiting_for_new_city"}
        await bot.send_message(user_id, "Введите ваш новый город:")
    elif data == "change_preferred_age":
        user_data[user_id] = {"step": "waiting_for_new_preferens_age"}
        await bot.send_message(user_id, "Введите новый предпочитаемый возраст в формате 'min-max':")
    elif data == "change_preferred_gender":
        user_data[user_id] = {"step": "waiting_for_new_preferred_gender"}
        await bot.send_message(user_id, "Выберите новый предпочитаемый гендер:", reply_markup=preferred_gender_keyboard)
    elif data == "change_email":
        user_data[user_id] = {"step": "waiting_for_new_email"}
        await bot.send_message(user_id, "Введите ваш новый email:")
    elif data == "change_url":
        user_data[user_id] = {"step": "waiting_for_new_url"}
        await bot.send_message(user_id, "Введите новый URL (например, ссылка на фото):")
    elif data == "change_social_links":
        user_data[user_id] = {"step": "waiting_for_new_social_links"}
        await bot.send_message(user_id, "Введите новые ссылки на социальные сети в формате JSON (например, {'vk': 'https://vk.com/id123', 'instagram': 'https://instagram.com/user123'}):")
    elif data == "change_interests":
        user_data[user_id] = {"step": "waiting_for_new_interests"}
        await bot.send_message(user_id, "Введите ваши новые интересы (например, 'программирование, музыка, спорт'):")
    elif data == "change_phone":
        user_data[user_id] = {"step": "waiting_for_new_phone"}
        await bot.send_message(user_id, "Введите ваш новый номер телефона (например, +71234567890):")
    elif data == "change_visibility":
        await handle_visibility_settings(user_id)
    elif data.startswith("toggle_visibility_"):
        await handle_toggle_visibility(call)

    await bot.answer_callback_query(call.id)
    try:
        await bot.send_message(
        user_id,
        #"Меню:",
        reply_markup=main_menu_keyboard
    )
    except:
        pass

# Обработчик для изменения имени
@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get("step") == "waiting_for_new_name")
async def handle_new_name_input(message: types.Message):
    user_id = message.from_user.id
    new_name = message.text
    if await update_profile(user_id, name=new_name):
        await bot.send_message(user_id, "✅ Имя успешно обновлено!", reply_markup=main_menu_keyboard)
    else:
        await bot.send_message(user_id, "❌ Не удалось обновить имя. Попробуйте снова.")
    user_data[user_id]["step"] = None

# Обработчик для изменения возраста
@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get("step") == "waiting_for_new_age")
async def handle_new_age_input(message: types.Message):
    user_id = message.from_user.id
    text = message.text
    if text.isdigit():
        new_age = int(text)
        if 18 <= new_age <= 99:
            if await update_profile(user_id, age=new_age):
                await bot.send_message(user_id, "✅ Возраст успешно обновлён!", reply_markup=main_menu_keyboard)
            else:
                await bot.send_message(user_id, "❌ Не удалось обновить возраст. Попробуйте снова.")
        else:
            await bot.send_message(user_id, "❌ Возраст должен быть от 18 до 99 лет.")
    else:
        await bot.send_message(user_id, "❌ Возраст должен быть числом.")
    user_data[user_id]["step"] = None

# Обработчик для изменения пола
@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get("step") == "waiting_for_new_gender")
async def handle_new_gender_input(message: types.Message):
    user_id = message.from_user.id
    new_gender = message.text
    if new_gender in ["Мужской", "Женский", "Другой"]:
        if await update_profile(user_id, gender=new_gender):
            await bot.send_message(user_id, "✅ Пол успешно обновлён!", reply_markup=main_menu_keyboard)
        else:
            await bot.send_message(user_id, "❌ Не удалось обновить пол. Попробуйте снова.")
    else:
        await bot.send_message(user_id, "❌ Пожалуйста, выберите пол из предложенных вариантов.")
    user_data[user_id]["step"] = None

# Обработчик для изменения города
@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get("step") == "waiting_for_new_city")
async def handle_new_city_input(message: types.Message):
    user_id = message.from_user.id
    new_city = message.text
    if await update_profile(user_id, city=new_city):
        await bot.send_message(user_id, "✅ Город успешно обновлён!", reply_markup=main_menu_keyboard)
    else:
        await bot.send_message(user_id, "❌ Не удалось обновить город. Попробуйте снова.")
    user_data[user_id]["step"] = None



# Обработчик для изменения предпочитаемого гендера
@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get("step") == "waiting_for_new_preferred_gender")
async def handle_new_preferred_gender_input(message: types.Message):
    user_id = message.from_user.id
    new_preferred_gender = message.text
    if new_preferred_gender in ["Мужской", "Женский", "Любой"]:
        if await update_profile(user_id, preferred_gender=new_preferred_gender):
            await bot.send_message(user_id, "✅ Предпочитаемый гендер успешно обновлён!", reply_markup=main_menu_keyboard)
        else:
            await bot.send_message(user_id, "❌ Не удалось обновить предпочитаемый гендер. Попробуйте снова.")
    else:
        await bot.send_message(user_id, "❌ Пожалуйста, выберите гендер из предложенных вариантов.")
    user_data[user_id]["step"] = None

# Обработчик для изменения email
@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get("step") == "waiting_for_new_email")
async def handle_new_email_input(message: types.Message):
    user_id = message.from_user.id
    new_email = message.text
    if await update_profile(user_id, email=new_email):
        await bot.send_message(user_id, "✅ Email успешно обновлён!", reply_markup=main_menu_keyboard)
    else:
        await bot.send_message(user_id, "❌ Не удалось обновить email. Попробуйте снова.")
    user_data[user_id]["step"] = None

# Обработчик для изменения URL
@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get("step") == "waiting_for_new_url")
async def handle_new_url_input(message: types.Message):
    user_id = message.from_user.id
    new_url = message.text
    if await update_profile(user_id, photo_url=new_url):
        await bot.send_message(user_id, "✅ URL успешно обновлён!", reply_markup=main_menu_keyboard)
    else:
        await bot.send_message(user_id, "❌ Не удалось обновить URL. Попробуйте снова.")
    user_data[user_id]["step"] = None

# Обработчик для изменения социальных ссылок
@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get("step") == "waiting_for_new_social_links")
async def handle_new_social_links_input(message: types.Message):
    user_id = message.from_user.id
    try:
        new_social_links = json.loads(message.text)
        if await update_profile(user_id, social_links=new_social_links):
            await bot.send_message(user_id, "✅ Социальные ссылки успешно обновлены!", reply_markup=main_menu_keyboard)
        else:
            await bot.send_message(user_id, "❌ Не удалось обновить социальные ссылки. Попробуйте снова.")
    except json.JSONDecodeError:
        await bot.send_message(user_id, "❌ Некорректный формат JSON. Попробуйте снова.")
    user_data[user_id]["step"] = None

# Обработчик для изменения интересов
@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get("step") == "waiting_for_new_interests")
async def handle_new_interests_input(message: types.Message):
    user_id = message.from_user.id
    new_interests = message.text
    if await update_profile(user_id, interests=new_interests):
        await bot.send_message(user_id, "✅ Интересы успешно обновлены!", reply_markup=main_menu_keyboard)
    else:
        await bot.send_message(user_id, "❌ Не удалось обновить интересы. Попробуйте снова.")
    user_data[user_id]["step"] = None

# Обработчик для изменения телефона
@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get("step") == "waiting_for_new_phone")
async def handle_new_phone_input(message: types.Message):
    user_id = message.from_user.id
    new_phone = message.text
    if await update_profile(user_id, phone=new_phone):
        await bot.send_message(user_id, "✅ Телефон успешно обновлён!", reply_markup=main_menu_keyboard)
    else:
        await bot.send_message(user_id, "❌ Не удалось обновить телефон. Попробуйте снова.")
    user_data[user_id]["step"] = None

@bot.callback_query_handler(func=lambda call: call.data == "contact_unavailable")
async def handle_unavailable(call: types.CallbackQuery):
    await bot.answer_callback_query(call.id, "Этот пользователь ограничил контакты", show_alert=False)
    
#Обновите обработчик команды /analyze:
@bot.message_handler(commands=['analyze'])
async def handle_analyze(message):
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        logger.info(f"Начало обработки анализа для пользователя {user_id}")
        
        if poll_analyzer is None:
            logger.error("Анализатор голосований не инициализирован")
            await bot.reply_to(message, "⚠️ Сервис временно недоступен. Попробуйте позже.")
            return

        # 1. Отправляем сообщение о начале обработки
        try:
            progress_msg = await bot.reply_to(message, "⏳ Анализируем ваши совпадения...")
            logger.debug(f"Сообщение о начале отправлено, ID: {progress_msg.message_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки начального сообщения: {str(e)}")
            return

        # 2. Проверяем возможность анализа с таймаутом
        try:
            logger.debug("Проверка eligibility...")
            eligible, msg = await asyncio.wait_for(
                poll_analyzer.check_eligible(user_id),
                timeout=10.0
            )
            logger.debug(f"Результат проверки: eligible={eligible}, msg={msg[:500]}...")
            
            if not eligible:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=progress_msg.message_id,
                    text=msg
                )
                logger.info("Пользователь не прошел проверку eligibility")
                return
        except asyncio.TimeoutError:
            logger.error("Таймаут при проверке eligibility")
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=progress_msg.message_id,
                text="⚠️ Сервис перегружен. Попробуйте позже."
            )
            return
        except Exception as e:
            logger.error(f"Ошибка проверки eligibility: {str(e)}", exc_info=True)
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=progress_msg.message_id,
                text="⚠️ Ошибка проверки данных. Попробуйте позже."
            )
            return

        # 3. Генерация отчета с таймаутом
        try:
            logger.debug("Начало генерации отчета...")
            report = await asyncio.wait_for(
                poll_analyzer.generate_report(user_id),
                timeout=30.0
            )
            logger.debug(f"Отчет сгенерирован, длина: {len(report)} символов")
            
            if not report.strip():
                logger.error("Получен пустой отчет")
                raise ValueError("Пустой отчет")

            # 4. Отправка результата
            if len(report) > 4000:
                logger.debug("Отчет слишком длинный, разбиваем на части...")
                await bot.delete_message(chat_id=chat_id, message_id=progress_msg.message_id)
                
                parts = [report[i:i+4000] for i in range(0, len(report), 4000)]
                for i, part in enumerate(parts, 1):
                    await bot.send_message(chat_id, part, parse_mode='HTML')
                    logger.debug(f"Отправлена часть {i}/{len(parts)}")
            else:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=progress_msg.message_id,
                    text=report,
                    parse_mode='HTML'
                )
                logger.debug("Отчет успешно отправлен")
                
            logger.info(f"Анализ для {user_id} успешно завершен")

        except asyncio.TimeoutError:
            logger.error("Таймаут при генерации отчета")
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=progress_msg.message_id,
                text="⚠️ Анализ занял слишком много времени. Попробуйте позже."
            )
        except Exception as e:
            logger.error(f"Ошибка генерации/отправки отчета: {str(e)}", exc_info=True)
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=progress_msg.message_id,
                text="⚠️ Произошла ошибка при формировании отчета"
            )

    except Exception as e:
        logger.error(f"Критическая ошибка в обработчике analyze: {str(e)}", exc_info=True)
        try:
            await bot.reply_to(message, "⚠️ Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")
        except:
            pass   

# Инициализация при старте
async def main():
    global poll_analyzer, quiz_players_collection, polls_collection, admin_settings_collection
    
    try:
        # 1. Подключаемся к MongoDB
        client, db = await init_db()
        logger.info("Успешное подключение к MongoDB")
        
        # 2. Инициализируем анализатор голосований
        poll_analyzer = PollAnalyzer(client)
        logger.info("Анализатор голосований инициализирован")
        
        # 3. Получаем коллекции
        quiz_players_collection = db.quiz_players
        admin_settings_collection = db.admin_settings
        logger.info("Коллекции MongoDB получены")
        
        # 4. Запускаем бота
        logger.info("Запуск бота...")
        await bot.polling(non_stop=True)
        
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())

print("Доступные команды бота:")
print(bot.get_my_commands())  # Проверка зарегистрированных обработчиков
