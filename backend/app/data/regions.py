# 좌표를 전북 시·군 지역명으로 해석하는 결정적 역지오코딩을 담당하는 파일
"""Deterministic reverse geocoding for Jeonbuk cities and counties.

Coordinates are matched to the nearest administrative center without any
external geocoding API, so consultations never trigger network calls.
"""
from math import asin, cos, radians, sin, sqrt

from ..core.schemas import RegionInfo

# (region id, ko, en, vi, latitude, longitude) — approximate city/county centers.
REGION_CENTERS = (
    ("jeonju", "전주시", "Jeonju-si", "Jeonju", 35.8242, 127.1480),
    ("gunsan", "군산시", "Gunsan-si", "Gunsan", 35.9676, 126.7366),
    ("iksan", "익산시", "Iksan-si", "Iksan", 35.9483, 126.9578),
    ("jeongeup", "정읍시", "Jeongeup-si", "Jeongeup", 35.5699, 126.8558),
    ("namwon", "남원시", "Namwon-si", "Namwon", 35.4164, 127.3906),
    ("gimje", "김제시", "Gimje-si", "Gimje", 35.8037, 126.8809),
    ("wanju", "완주군", "Wanju-gun", "Wanju", 35.9047, 127.1622),
    ("jinan", "진안군", "Jinan-gun", "Jinan", 35.7917, 127.4249),
    ("muju", "무주군", "Muju-gun", "Muju", 36.0069, 127.6608),
    ("jangsu", "장수군", "Jangsu-gun", "Jangsu", 35.6473, 127.5213),
    ("imsil", "임실군", "Imsil-gun", "Imsil", 35.6178, 127.2891),
    ("sunchang", "순창군", "Sunchang-gun", "Sunchang", 35.3744, 127.1376),
    ("gochang", "고창군", "Gochang-gun", "Gochang", 35.4358, 126.7020),
    ("buan", "부안군", "Buan-gun", "Buan", 35.7318, 126.7331),
)

# Beyond this distance from every center the point is outside Jeonbuk.
MAX_REGION_DISTANCE_KM = 45.0


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    a, b, c, d = map(radians, (lat1, lon1, lat2, lon2))
    return 6371 * 2 * asin(sqrt(sin((c - a) / 2) ** 2 + cos(a) * cos(c) * sin((d - b) / 2) ** 2))


def resolve_region(latitude: float, longitude: float) -> RegionInfo:
    """Nearest Jeonbuk region for the coordinates, or an empty result outside the province."""
    best = min(REGION_CENTERS, key=lambda center: _distance_km(latitude, longitude, center[4], center[5]))
    if _distance_km(latitude, longitude, best[4], best[5]) > MAX_REGION_DISTANCE_KM:
        return RegionInfo()
    return RegionInfo(region=best[0], name={"ko": best[1], "en": best[2], "vi": best[3]})
