"""
geo.py — утилиты для работы с координатами пользователей.
Используется для поиска по радиусу, расчета расстояний и парсинга координат.
"""
from typing import Optional, Tuple
from geopy.distance import geodesic

def parse_coords(coord_str: str) -> Optional[Tuple[float, float]]:
    """Парсит строку 'долгота, широта' в кортеж (lat, lon)."""
    if not coord_str or not isinstance(coord_str, str):
        return None
    try:
        clean_str = coord_str.strip('[] ')
        parts = [p.strip() for p in clean_str.split(',')]
        if len(parts) == 2:
            lon, lat = map(float, parts)
            if -180 <= lon <= 180 and -90 <= lat <= 90:
                return (lat, lon)
    except (ValueError, TypeError, AttributeError):
        pass
    return None

def calc_distance_km(coords1: Tuple[float, float], coords2: Tuple[float, float]) -> float:
    """Вычисляет расстояние между двумя точками в км."""
    return geodesic(coords1, coords2).km 