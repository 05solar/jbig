# 가이드 시드 데이터 무결성과 조회 API를 검증하는 테스트 파일
import unittest

from fastapi import HTTPException

from app.data.seed import AGENCIES, GUIDES
from app.main import get_agency, get_guide, list_guides


class GuideDataTests(unittest.TestCase):
    def test_expected_data_counts(self) -> None:
        self.assertEqual(len(GUIDES), 13)
        self.assertEqual(len(AGENCIES), 5)
        self.assertEqual(len(list_guides("residency")), 5)
        self.assertEqual(len(list_guides("labor")), 8)

    def test_guides_are_enriched_with_details(self) -> None:
        for guide in GUIDES:
            self.assertTrue(guide.target.get("ko"), guide.id)
            self.assertTrue(guide.common_mistakes.get("ko"), guide.id)
        unpaid = next(guide for guide in GUIDES if guide.id == "unpaid-wages")
        self.assertTrue(unpaid.related_documents)
        self.assertTrue(all(reference.url.startswith("https://") for reference in unpaid.related_documents))

    def test_guides_reference_existing_agencies(self) -> None:
        agency_ids = {agency.id for agency in AGENCIES}
        for guide in GUIDES:
            self.assertTrue(set(guide.agency_ids) <= agency_ids)
            for field in (guide.title, guide.summary, guide.steps, guide.required_documents, guide.cautions, guide.source_name):
                self.assertEqual(set(field), {"ko", "en", "vi"})
                self.assertTrue(all(field.values()))
            self.assertTrue(guide.source_url.startswith("https://"))

    def test_detail_lookup_and_not_found(self) -> None:
        self.assertEqual(get_guide("alien-registration").category, "residency")
        self.assertEqual(get_agency("labor-office").phone, "1350")
        with self.assertRaises(HTTPException) as context:
            get_guide("missing")
        self.assertEqual(context.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
