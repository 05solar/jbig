# 좌표→지역 해석과 지역 API를 검증하는 테스트 파일
import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.data.regions import resolve_region

client = TestClient(app)


class RegionResolveTests(unittest.TestCase):
    def test_jeonju_coordinates_resolve_to_jeonju(self) -> None:
        info = resolve_region(35.8242, 127.1480)
        self.assertEqual(info.region, "jeonju")
        self.assertEqual(info.name["ko"], "전주시")

    def test_nearby_city_resolves_to_nearest_center(self) -> None:
        self.assertEqual(resolve_region(35.96, 126.95).region, "iksan")
        self.assertEqual(resolve_region(35.97, 126.74).region, "gunsan")

    def test_coordinates_outside_jeonbuk_return_empty(self) -> None:
        info = resolve_region(37.5665, 126.9780)  # Seoul
        self.assertIsNone(info.region)
        self.assertIsNone(info.name)

    def test_api_endpoint_returns_region_and_validates_input(self) -> None:
        response = client.get("/api/regions/resolve", params={"latitude": 35.8242, "longitude": 127.1480})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["region"], "jeonju")
        self.assertEqual(body["name"]["ko"], "전주시")
        self.assertEqual(client.get("/api/regions/resolve", params={"latitude": 999, "longitude": 0}).status_code, 422)


if __name__ == "__main__":
    unittest.main()
