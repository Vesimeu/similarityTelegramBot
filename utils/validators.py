"""
validators.py — набор функций для валидации пользовательских данных.
Используется в хендлерах и сервисах для проверки корректности ввода.
"""
import re
from typing import Tuple

def validate_age(age: int) -> bool:
    """Проверяет, что возраст в допустимом диапазоне."""
    return 18 <= age <= 99

def validate_age_range(min_age: int, max_age: int) -> bool:
    """Проверяет, что диапазон возраста корректен."""
    return 18 <= min_age < max_age <= 100

def parse_age_range(text: str) -> Tuple[int, int]:
    """Парсит строку вида '25-35' в кортеж (25, 35)."""
    parts = text.replace(' ', '').split('-')
    if len(parts) != 2:
        raise ValueError("Формат должен быть 'min-max'")
    min_age, max_age = map(int, parts)
    if not validate_age_range(min_age, max_age):
        raise ValueError("Возраст вне диапазона 18-100 или min >= max")
    return min_age, max_age

def validate_email(email: str) -> bool:
    """Простая валидация email."""
    return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email)) 