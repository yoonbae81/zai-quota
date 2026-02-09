import unittest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import calculate_metrics, extract_token_limit


class TestCalculateMetrics(unittest.TestCase):
    """Test cases for calculate_metrics function"""

    def test_calculate_metrics_basic(self):
        """Test basic metrics calculation"""
        token_limit = {
            "currentValue": 50000,
            "usage": 100000,
            "nextResetTime": 1700000000000  # Mock timestamp
        }
        result = calculate_metrics(token_limit)
        
        self.assertIn("quotaUsed", result)
        self.assertIn("nextReset", result)
        self.assertIn("remainingTime", result)
        self.assertEqual(result["quotaUsed"], 50.0)

    def test_calculate_metrics_full_quota(self):
        """Test metrics when quota is fully used"""
        token_limit = {
            "currentValue": 100000,
            "usage": 100000,
            "nextResetTime": 1700000000000
        }
        result = calculate_metrics(token_limit)
        self.assertEqual(result["quotaUsed"], 100.0)

    def test_calculate_metrics_zero_quota(self):
        """Test metrics when quota is not used"""
        token_limit = {
            "currentValue": 0,
            "usage": 100000,
            "nextResetTime": 1700000000000
        }
        result = calculate_metrics(token_limit)
        self.assertEqual(result["quotaUsed"], 0.0)


class TestExtractTokenLimit(unittest.TestCase):
    """Test cases for extract_token_limit function"""

    def test_extract_token_limit_valid(self):
        """Test extracting TOKENS_LIMIT from valid data"""
        data = {
            "data": {
                "limits": [
                    {"type": "OTHER_LIMIT", "usage": 100},
                    {"type": "TOKENS_LIMIT", "usage": 100000, "currentValue": 50000}
                ]
            }
        }
        result = extract_token_limit(data)
        self.assertEqual(result["type"], "TOKENS_LIMIT")
        self.assertEqual(result["usage"], 100000)

    def test_extract_token_limit_not_found(self):
        """Test when TOKENS_LIMIT is not found"""
        data = {
            "data": {
                "limits": [
                    {"type": "OTHER_LIMIT", "usage": 100}
                ]
            }
        }
        with self.assertRaises(Exception) as context:
            extract_token_limit(data)
        self.assertIn("TOKENS_LIMIT not found", str(context.exception))


if __name__ == '__main__':
    unittest.main()
