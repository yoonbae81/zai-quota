import os
import sys
import unittest
from unittest import mock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import main  # noqa: E402
from providers import PROVIDERS, PROVIDER_MAP  # noqa: E402
from providers.base import QuotaMetrics, QuotaProvider, format_reset_info  # noqa: E402
from providers.zai import ZaiProvider  # noqa: E402


class TestFormatResetInfo(unittest.TestCase):
    """Test cases for the shared reset-time formatter."""

    def test_formats_next_reset_and_remaining(self):
        info = format_reset_info(1700000000000, now_ts=1700000000)
        self.assertIn("nextReset", info)
        self.assertIn("remainingTime", info)
        self.assertEqual(info["remainingTime"], "00:00")

    def test_remaining_time_hours_and_minutes(self):
        # 2 hours from now
        info = format_reset_info(1700007200000, now_ts=1700000000)
        self.assertEqual(info["remainingTime"], "02:00")

    def test_remaining_time_clamped_at_zero(self):
        # Reset time in the past
        info = format_reset_info(1699999000000, now_ts=1700000000)
        self.assertEqual(info["remainingTime"], "00:00")


class TestQuotaMetrics(unittest.TestCase):
    """Test cases for QuotaMetrics.to_dict."""

    def test_to_dict_includes_percentage_and_reset_fields(self):
        metrics = QuotaMetrics(quota_percentage=42.0, next_reset_ms=1700000000000)
        result = metrics.to_dict(now_ts=1700000000)
        self.assertEqual(result["quotaPercentage"], 42.0)
        self.assertIn("nextReset", result)
        self.assertIn("remainingTime", result)

    def test_to_dict_without_reset_time(self):
        metrics = QuotaMetrics(quota_percentage=7.5)
        self.assertEqual(metrics.to_dict(), {"quotaPercentage": 7.5})


class TestZaiProvider(unittest.TestCase):
    """Test cases for the Z.ai provider."""

    def test_provider_metadata(self):
        provider = ZaiProvider()
        self.assertEqual(provider.name, "zai")
        self.assertEqual(provider.env_key, "ZAI_API_KEY")

    def test_extract_token_limit_valid(self):
        data = {
            "data": {
                "limits": [
                    {"type": "OTHER_LIMIT", "usage": 100},
                    {"type": "TOKENS_LIMIT", "percentage": 100, "nextResetTime": 1700000000000},
                ]
            }
        }
        result = ZaiProvider._extract_token_limit(data)
        self.assertEqual(result["type"], "TOKENS_LIMIT")
        self.assertEqual(result["percentage"], 100)

    def test_extract_token_limit_not_found(self):
        data = {"data": {"limits": [{"type": "OTHER_LIMIT", "usage": 100}]}}
        with self.assertRaises(Exception) as context:
            ZaiProvider._extract_token_limit(data)
        self.assertIn("TOKENS_LIMIT not found", str(context.exception))

    def test_fetch_returns_normalized_metrics(self):
        provider = ZaiProvider()
        payload = {
            "code": 200,
            "data": {
                "limits": [
                    {"type": "TOKENS_LIMIT", "percentage": 33, "nextResetTime": 1700000000000},
                ]
            },
        }
        with mock.patch.object(ZaiProvider, "_fetch_usage_data", return_value=payload):
            metrics = provider.fetch("dummy-key")
        self.assertEqual(metrics.quota_percentage, 33)
        self.assertEqual(metrics.next_reset_ms, 1700000000000)


class _StubProvider(QuotaProvider):
    """Configured test provider returning fixed metrics."""

    name = "stub"
    display_name = "Stub"
    env_key = "STUB_API_KEY"

    def __init__(self):
        self.calls = 0

    def fetch(self, api_key):
        self.calls += 1
        return QuotaMetrics(quota_percentage=55.0, next_reset_ms=1700000000000)


class _BrokenProvider(QuotaProvider):
    """Configured test provider that always fails."""

    name = "broken"
    display_name = "Broken"
    env_key = "BROKEN_API_KEY"

    def fetch(self, api_key):
        raise Exception("boom")


class TestComprehensiveView(unittest.TestCase):
    """Test cases for the comprehensive (all-provider) view."""

    def setUp(self):
        self.stub = _StubProvider()
        self.broken = _BrokenProvider()
        PROVIDERS.append(self.stub)
        PROVIDERS.append(self.broken)
        PROVIDER_MAP[self.stub.name] = self.stub
        PROVIDER_MAP[self.broken.name] = self.broken
        self._environ = dict(os.environ)
        os.environ["STUB_API_KEY"] = "stub-key"
        os.environ["BROKEN_API_KEY"] = "broken-key"
        os.environ.pop("ZAI_API_KEY", None)

    def tearDown(self):
        PROVIDERS.remove(self.stub)
        PROVIDERS.remove(self.broken)
        del PROVIDER_MAP[self.stub.name]
        del PROVIDER_MAP[self.broken.name]
        os.environ.clear()
        os.environ.update(self._environ)

    def test_reports_all_provider_statuses(self):
        view = main.build_comprehensive_view(now_ts=1700000000)
        self.assertIn("generatedAt", view)
        providers = view["providers"]
        self.assertEqual(providers["zai"], {"configured": False, "status": "not_configured"})
        self.assertEqual(providers["stub"]["status"], "ok")
        self.assertEqual(providers["stub"]["quotaPercentage"], 55.0)
        self.assertIn("nextReset", providers["stub"])
        self.assertIn("remainingTime", providers["stub"])
        self.assertEqual(providers["broken"]["status"], "error")
        self.assertEqual(providers["broken"]["error"], "boom")

    def test_unconfigured_provider_is_not_fetched(self):
        os.environ.pop("STUB_API_KEY")
        main.build_comprehensive_view()
        self.assertEqual(self.stub.calls, 0)


if __name__ == '__main__':
    unittest.main()
