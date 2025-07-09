"""
StateService — централизованное хранилище пользовательских состояний для бота.
Позволяет избежать глобальных переменных и облегчает тестирование/расширение.
"""
from typing import Any, Dict, Set
import threading

class StateService:
    def __init__(self):
        # Состояния пользователя (например, шаг регистрации, force-reply и т.д.)
        self.user_data: Dict[int, Dict[str, Any]] = {}
        # Результаты поиска пары для каждого пользователя
        self.current_search_results: Dict[int, Dict[str, Any]] = {}
        # Настройки пропуска (permanent/temporary skip)
        self.user_skip_settings: Dict[int, Dict[str, int]] = {}
        # Ожидание ввода для пропуска
        self.awaiting_skip_input: Set[int] = set()
        self.awaiting_temp_skip_input: Set[int] = set()
        # Потокобезопасность (если потребуется)
        self._lock = threading.Lock()

    # Методы для user_data
    def set_user_state(self, user_id: int, state: Dict[str, Any]):
        with self._lock:
            self.user_data[user_id] = state

    def get_user_state(self, user_id: int) -> Dict[str, Any]:
        return self.user_data.get(user_id, {})

    def clear_user_state(self, user_id: int):
        with self._lock:
            self.user_data.pop(user_id, None)

    # Методы для current_search_results
    def set_search_results(self, user_id: int, results: Dict[str, Any]):
        with self._lock:
            self.current_search_results[user_id] = results

    def get_search_results(self, user_id: int) -> Dict[str, Any]:
        return self.current_search_results.get(user_id, {})

    def clear_search_results(self, user_id: int):
        with self._lock:
            self.current_search_results.pop(user_id, None)

    # Методы для skip settings
    def set_skip_settings(self, user_id: int, settings: Dict[str, int]):
        with self._lock:
            self.user_skip_settings[user_id] = settings

    def get_skip_settings(self, user_id: int) -> Dict[str, int]:
        return self.user_skip_settings.get(user_id, {"permanent": 0, "temporary": 0})

    def clear_skip_settings(self, user_id: int):
        with self._lock:
            self.user_skip_settings.pop(user_id, None)

    # Методы для awaiting input
    def add_awaiting_skip(self, user_id: int):
        with self._lock:
            self.awaiting_skip_input.add(user_id)

    def remove_awaiting_skip(self, user_id: int):
        with self._lock:
            self.awaiting_skip_input.discard(user_id)

    def is_awaiting_skip(self, user_id: int) -> bool:
        return user_id in self.awaiting_skip_input

    def add_awaiting_temp_skip(self, user_id: int):
        with self._lock:
            self.awaiting_temp_skip_input.add(user_id)

    def remove_awaiting_temp_skip(self, user_id: int):
        with self._lock:
            self.awaiting_temp_skip_input.discard(user_id)

    def is_awaiting_temp_skip(self, user_id: int) -> bool:
        return user_id in self.awaiting_temp_skip_input 