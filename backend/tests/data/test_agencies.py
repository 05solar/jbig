# 기관 필터·거리 정렬 API를 검증하는 테스트 파일
import unittest
from unittest.mock import patch

from app.main import list_agencies


class AgencySearchTests(unittest.TestCase):
    @patch("app.main.load_agencies", return_value=None)
    def test_filters_by_service_and_language(self, _load_agencies) -> None:
        labor = list_agencies(region=None, service_type="labor", language=None, latitude=None, longitude=None)
        self.assertEqual({agency.id for agency in labor}, {"labor-office", "workers-comp", "danuri"})

        vietnamese_labor = list_agencies(region=None, service_type="labor", language="vi", latitude=None, longitude=None)
        self.assertEqual([agency.id for agency in vietnamese_labor], ["danuri"])

    @patch("app.main.load_agencies", return_value=None)
    def test_filters_by_region(self, _load_agencies) -> None:
        agencies = list_agencies(region="jeonju", service_type=None, language=None, latitude=None, longitude=None)
        self.assertEqual({agency.id for agency in agencies}, {"immigration", "labor-office"})

    @patch("app.main.load_agencies", return_value=None)
    def test_distance_is_calculated_and_sorted(self, _load_agencies) -> None:
        agencies = list_agencies(region=None, service_type=None, language=None, latitude=35.84, longitude=127.15)
        physical = [agency for agency in agencies if agency.distance_km is not None]
        self.assertEqual(len(physical), 2)
        self.assertLessEqual(physical[0].distance_km, physical[1].distance_km)
        self.assertTrue(all(agency.distance_km is None for agency in agencies[2:]))

    @patch("app.main.load_agencies", return_value=None)
    def test_danuri_current_service_metadata(self, _load_agencies) -> None:
        agencies = list_agencies(region=None, service_type="interpretation", language="vi", latitude=None, longitude=None)
        self.assertEqual(len(agencies), 1)
        self.assertEqual(len(agencies[0].supported_languages), 15)
        self.assertTrue(agencies[0].emergency)
        self.assertIn("24", agencies[0].hours["ko"])


if __name__ == "__main__":
    unittest.main()
