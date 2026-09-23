import os
import sys
import unittest
from importlib.util import module_from_spec, spec_from_file_location

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

MAIN_MODULE_PATH = os.path.join(os.path.dirname(__file__), '..', 'src', 'main.py')
main_spec = spec_from_file_location("zai_quota_main", MAIN_MODULE_PATH)
if main_spec is None or main_spec.loader is None:
    raise ImportError(f"Unable to load main module from {MAIN_MODULE_PATH}")

main_module = module_from_spec(main_spec)
main_spec.loader.exec_module(main_module)

format_allowed_paths = main_module.format_allowed_paths
get_allowed_base_paths = main_module.get_allowed_base_paths
is_allowed_request_path = main_module.is_allowed_request_path


class TestServerRouting(unittest.TestCase):
    """Test route matching for reverse-proxy deployments."""

    def test_primary_base_url_is_allowed(self):
        self.assertTrue(is_allowed_request_path("/zai-quota", "/zai-quota"))
        self.assertTrue(is_allowed_request_path("/zai-quota/", "/zai-quota"))

    def test_alias_base_url_is_allowed(self):
        self.assertTrue(
            is_allowed_request_path(
                "/zai-proxy",
                "/zai-quota",
                "/zai-proxy",
            )
        )
        self.assertTrue(
            is_allowed_request_path(
                "/zai-proxy/?via=haproxy",
                "/zai-quota",
                "/zai-proxy",
            )
        )

    def test_unconfigured_path_is_rejected(self):
        self.assertFalse(
            is_allowed_request_path(
                "/unknown-path",
                "/zai-quota",
                "/zai-proxy",
            )
        )

    def test_allowed_paths_are_normalized(self):
        self.assertEqual(
            get_allowed_base_paths("zai-quota/", " /zai-proxy/, zai-proxy "),
            ["/zai-quota", "/zai-proxy"],
        )

    def test_root_path_remains_supported(self):
        self.assertTrue(is_allowed_request_path("/", ""))
        self.assertEqual(format_allowed_paths("", ""), ["/"])


if __name__ == '__main__':
    unittest.main()
