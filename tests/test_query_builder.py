from __future__ import annotations

import unittest

from application.query_builder_service import QueryBuilderService
from domain.models import MaterialItem


class QueryBuilderServiceTests(unittest.TestCase):
    def test_builds_keywords_from_material(self) -> None:
        service = QueryBuilderService()
        material = MaterialItem(row_id=1, serial_no="1", name="电钻", spec="220V 450W", brand="博世")

        query = service.build(material)

        self.assertEqual(query.material_id, 1)
        self.assertIn("电钻 220V 450W", query.keywords)
        self.assertIn("博世 电钻 220V 450W", query.keywords)
        self.assertEqual(query.brand_hint, "博世")


if __name__ == "__main__":
    unittest.main()
