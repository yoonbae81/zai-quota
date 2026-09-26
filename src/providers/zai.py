"""Z.ai (GLM coding plan) quota provider.

Reference: https://github.com/zai-org/zai-coding-plugins/blob/main/plugins/glm-plan-usage/skills/usage-query-skill/scripts/query-usage.mjs
"""

import json
import urllib.error
import urllib.request

from .base import QuotaMetrics, QuotaProvider

USAGE_API_URL = "https://api.z.ai/api/monitor/usage/quota/limit"


class ZaiProvider(QuotaProvider):
    """Queries the Z.ai quota API and normalizes the TOKENS_LIMIT entry."""

    name = "zai"
    display_name = "Z.ai"
    env_key = "ZAI_API_KEY"

    def fetch(self, api_key: str) -> QuotaMetrics:
        data = self._fetch_usage_data(api_key)
        token_limit = self._extract_token_limit(data)
        return QuotaMetrics(
            quota_percentage=token_limit.get("percentage", 0),
            next_reset_ms=token_limit.get("nextResetTime"),
        )

    @staticmethod
    def _fetch_usage_data(api_key: str) -> dict:
        """Send a request to the Z.ai API and return the JSON response."""
        headers = {
            "Authorization": api_key,
            "Accept-Language": "en-US,en",
            "Content-Type": "application/json",
        }
        req = urllib.request.Request(USAGE_API_URL, headers=headers)
        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise Exception(f"HTTP Error: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            raise Exception(f"URL Error: {e.reason}")

        if data.get("code") != 200:
            raise Exception(
                f"API Error: {data.get('msg', 'Unknown error')} (code: {data.get('code')})"
            )
        return data

    @staticmethod
    def _extract_token_limit(data: dict) -> dict:
        """Extract the TOKENS_LIMIT section from the response data."""
        limits = data.get("data", {}).get("limits", [])
        token_limit = next(
            (item for item in limits if item["type"] == "TOKENS_LIMIT"), None
        )
        if not token_limit:
            raise Exception("TOKENS_LIMIT not found in response data")
        return token_limit
