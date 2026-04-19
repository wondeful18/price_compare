from __future__ import annotations

import unittest

from domain.enums import PlatformType
from infra.http_client import build_mock_http_client
from providers.jd_provider import JDOfficialProvider


class JDProviderTests(unittest.TestCase):
    def test_parses_mock_payload(self) -> None:
        provider = JDOfficialProvider(build_mock_http_client())
        offers = provider.parse_response(
            {
                "offers": [
                    {
                        "skuName": "博世 电钻 220V 450W",
                        "brandName": "博世",
                        "specification": "220V 450W",
                        "price": 99.8,
                        "shopName": "京东自营",
                        "skuUrl": "https://example.com/1",
                    }
                ]
            }
        )

        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].platform, PlatformType.JD)
        self.assertEqual(offers[0].brand, "博世")
        self.assertEqual(offers[0].price, 99.8)


if __name__ == "__main__":
    unittest.main()
