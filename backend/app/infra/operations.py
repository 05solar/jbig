# 인메모리 운영 기능(레이트리밋·상담 캐시·일일 AI 예산·지표 집계)을 담당하는 파일
import hashlib
import re
import threading
import time
from collections import Counter, defaultdict, deque
from datetime import date

from ..core.config import settings
from ..core.schemas import ConsultationResponse, FeedbackRequest, OperationsStatus

_lock = threading.Lock()
_requests: dict[str, deque[float]] = defaultdict(deque)
_cache: dict[str, tuple[float, ConsultationResponse]] = {}
_metrics: Counter[str] = Counter()
_feedback_ids: set[str] = set()
_budget_date = date.today()
_daily_ai_calls = 0


def hash_identifier(value: str) -> str:
    return hashlib.sha256(f"{settings.identifier_salt}:{value}".encode()).hexdigest()


def cache_key(question: str, language: str, user_type: str | None = None, region: str | None = None, index_version: str | None = None, conversation_context: str | None = None) -> str:
    normalized = re.sub(r"\s+", " ", question.strip().casefold())
    context = re.sub(r"\s+", " ", (conversation_context or "").strip().casefold())
    return hash_identifier(f"{language}:{user_type or ''}:{region or ''}:{index_version or '1'}:{context}:{normalized}")


def allow_request(client_id: str, now: float | None = None) -> bool:
    current = now if now is not None else time.time()
    with _lock:
        window = _requests[client_id]
        while window and current - window[0] >= 60:
            window.popleft()
        if len(window) >= settings.consultation_rate_limit:
            return False
        window.append(current)
        _metrics["consultations"] += 1
        return True


def get_cached(key: str, now: float | None = None) -> ConsultationResponse | None:
    current = now if now is not None else time.time()
    with _lock:
        item = _cache.get(key)
        if not item or current - item[0] >= settings.consultation_cache_seconds:
            _cache.pop(key, None)
            return None
        _metrics["cache_hits"] += 1
        return item[1].model_copy(update={"cached": True})


def set_cached(key: str, response: ConsultationResponse) -> None:
    with _lock:
        if len(_cache) >= 500:
            oldest = min(_cache, key=lambda item: _cache[item][0])
            _cache.pop(oldest, None)
        _cache[key] = (time.time(), response.model_copy(update={"cached": False}))


def acquire_ai_budget() -> bool:
    global _budget_date, _daily_ai_calls
    from .database import acquire_daily_ai_budget
    database_result = acquire_daily_ai_budget(settings.daily_ai_call_limit)
    if database_result is not None:
        if database_result:
            with _lock:
                _metrics["ai_calls"] += 1
        return database_result
    with _lock:
        today = date.today()
        if today != _budget_date:
            _budget_date, _daily_ai_calls = today, 0
        if _daily_ai_calls >= settings.daily_ai_call_limit:
            return False
        _daily_ai_calls += 1
        _metrics["ai_calls"] += 1
        return True


def record_ai_fallback() -> None:
    with _lock:
        _metrics["ai_fallbacks"] += 1


def record_feedback(feedback: FeedbackRequest) -> bool:
    from .database import save_feedback
    database_result = save_feedback(feedback)
    if database_result is not None:
        return database_result
    with _lock:
        if feedback.consultation_id in _feedback_ids:
            return False
        _feedback_ids.add(feedback.consultation_id)
        _metrics[feedback.rating] += 1
        if feedback.reason:
            _metrics[f"reason:{feedback.reason}"] += 1
        return True


def status() -> OperationsStatus:
    from .database import database_status
    persisted = database_status()
    with _lock:
        return OperationsStatus(consultations=persisted.consultations if persisted else _metrics["consultations"], cache_hits=_metrics["cache_hits"], ai_calls=persisted.ai_calls if persisted else _metrics["ai_calls"], ai_fallbacks=_metrics["ai_fallbacks"], helpful=persisted.helpful if persisted else _metrics["helpful"], not_helpful=persisted.not_helpful if persisted else _metrics["not_helpful"])


def reset_for_tests() -> None:
    global _budget_date, _daily_ai_calls
    with _lock:
        _requests.clear()
        _cache.clear()
        _metrics.clear()
        _feedback_ids.clear()
        _budget_date = date.today()
        _daily_ai_calls = 0
