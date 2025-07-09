"""
cache.py — простой in-memory кеш для ускорения доступа к часто используемым данным (например, профили пользователей).
"""
import threading
from typing import Any, Dict

class SimpleCache:
    def __init__(self):
        self._cache: Dict[Any, Any] = {}
        self._lock = threading.Lock()

    def get(self, key: Any) -> Any:
        return self._cache.get(key)

    def set(self, key: Any, value: Any):
        with self._lock:
            self._cache[key] = value

    def clear(self, key: Any):
        with self._lock:
            self._cache.pop(key, None)

    def clear_all(self):
        with self._lock:
            self._cache.clear() 