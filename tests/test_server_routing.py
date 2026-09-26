import os
import sys
import unittest
from importlib.util import module_from_spec, spec_from_file_location

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

MAIN_MODULE_PATH = os.path.join(os.path.dirname(__file__), '..', 'src', 'main.py')
main_spec = spec_from_file_location("quota_main", MAIN_MODULE_PATH)
if main_spec is None or main_spec.loader is None:
    raise ImportError(f"Unable to load main module from {MAIN_MODULE_PATH}")

main_module = module_from_spec(main_spec)
main_spec.loader.exec_module(main_module)

format_allowed_paths = main_module.format_allowed_paths
get_allowed_base_paths = main_module.get_allowed_base_paths
normalize_base_path = main_module.normalize_base_path
resolve_route = main_module.resolve_route


class TestBasePathNormalization(unittest.TestCase):
    """Test base path normalization helpers."""

    def test_root_and_empty_normalize_to_blank(self):
        self.assertEqual(normalize_base_path(""), "")
        self.assertEqual(normalize_base_path("/"), "")

    def test_allowed_paths_are_normalized(self):
        self.assertEqual(
            get_allowed_base_paths("quota/", " /zai-proxy/, quota "),
            ["/quota", "/zai-proxy"],
        )

    def test_allowed_paths_default_to_root(self):
        self.assertEqual(get_allowed_base_paths("", ""), [""])
        self.assertEqual(format_allowed_paths("", ""), ["/"])

    def test_empty_aliases_do_not_enable_root(self):
        # Regression: BASE_URL_ALIASES="" must not inject the root base ""
        self.assertEqual(get_allowed_base_paths("/quota", ""), ["/quota"])
        self.assertIsNone(resolve_route("/other", "/quota"))
        self.assertIsNone(resolve_route("/", "/quota"))

    def test_explicit_root_alias_is_respected(self):
        self.assertEqual(get_allowed_base_paths("/quota", "/"), ["/quota", ""])
        self.assertEqual(resolve_route("/other", "/quota", "/"), ("other", ""))


class TestResolveRoute(unittest.TestCase):
    """Test route resolution for reverse-proxy deployments."""

    def test_base_route_resolves_to_empty_sub_path(self):
        self.assertEqual(resolve_route("/quota", "/quota"), ("", "/quota"))
        self.assertEqual(resolve_route("/quota/", "/quota"), ("", "/quota"))

    def test_alias_base_route_is_allowed(self):
        self.assertEqual(resolve_route("/zai-proxy", "/quota", "/zai-proxy"), ("", "/zai-proxy"))
        self.assertEqual(
            resolve_route("/zai-proxy/?via=haproxy", "/quota", "/zai-proxy"),
            ("", "/zai-proxy"),
        )

    def test_provider_sub_path_resolves_to_slug(self):
        self.assertEqual(resolve_route("/quota/zai", "/quota"), ("zai", "/quota"))
        self.assertEqual(resolve_route("/quota/zai/", "/quota"), ("zai", "/quota"))
        self.assertEqual(
            resolve_route("/quota/zai?refresh=1", "/quota", "/zai-proxy"),
            ("zai", "/quota"),
        )
        self.assertEqual(resolve_route("/zai-proxy/zai", "/quota", "/zai-proxy"), ("zai", "/zai-proxy"))

    def test_root_base_routes(self):
        self.assertEqual(resolve_route("/", ""), ("", ""))
        self.assertEqual(resolve_route("/zai", ""), ("zai", ""))

    def test_unconfigured_path_is_rejected(self):
        self.assertIsNone(resolve_route("/unknown-path", "/quota", "/zai-proxy"))
        self.assertIsNone(resolve_route("/quota/unknown/deeper", "/quota"))
        self.assertIsNone(resolve_route("/zai/deeper", ""))


if __name__ == '__main__':
    unittest.main()
