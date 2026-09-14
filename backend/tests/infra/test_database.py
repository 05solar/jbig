# DB 비활성 시 메모리 폴백 신호를 검증하는 테스트 파일
import unittest

from app.core.config import settings
from app.infra.database import database_available, load_agencies, load_guides


class DatabaseFallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original = settings.database_enabled
        settings.database_enabled = False

    def tearDown(self) -> None:
        settings.database_enabled = self.original

    def test_disabled_database_reports_unavailable(self) -> None:
        self.assertFalse(database_available())

    def test_disabled_database_returns_fallback_signal(self) -> None:
        self.assertIsNone(load_guides())
        self.assertIsNone(load_agencies())


if __name__ == "__main__":
    unittest.main()
