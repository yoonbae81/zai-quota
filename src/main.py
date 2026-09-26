#!/usr/bin/env python3

"""
Purpose: Query LLM usage quota limits across providers and output calculated
metrics in JSON format.

Web routes (base path defaults to /quota, configurable via BASE_URL):
  <base>            -> comprehensive view of all registered providers
  <base>/<provider> -> single provider metrics (e.g. /quota/zai)
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from providers import PROVIDERS, PROVIDER_MAP, get_provider  # noqa: E402

DEFAULT_BASE_URL = "/quota"


# ---------------------------------------------------------------------------
# Base path routing helpers (reverse-proxy friendly)
# ---------------------------------------------------------------------------

def normalize_base_path(path):
    """Normalize a configured base path for route matching."""
    normalized = (path or "").strip()
    if not normalized or normalized == "/":
        return ""

    normalized = normalized.strip("/")
    return f"/{normalized}" if normalized else ""


def get_allowed_base_paths(base_url, base_url_aliases=""):
    """Return normalized base paths accepted by the web server."""
    paths = []
    seen = set()

    raw_paths = [base_url]
    if base_url_aliases:
        raw_paths.extend(alias for alias in base_url_aliases.split(",") if alias.strip())

    for raw_path in raw_paths:
        normalized = normalize_base_path(raw_path)
        if normalized in seen:
            continue
        seen.add(normalized)
        paths.append(normalized)

    if not paths:
        return [""]

    return paths


def format_allowed_paths(base_url, base_url_aliases=""):
    """Return human-readable allowed paths for error messages."""
    return [path or "/" for path in get_allowed_base_paths(base_url, base_url_aliases)]


def resolve_route(request_path, base_url, base_url_aliases=""):
    """Resolve a request path against the configured base paths.

    Returns ``(sub_path, matched_base)`` where ``sub_path`` is ``""`` for the
    base (comprehensive) route or a provider slug for a per-provider route.
    Returns ``None`` when the request does not match any configured base path
    (or points deeper than ``<base>/<provider>``).
    """
    path = request_path.split("?")[0].rstrip("/")

    for base in get_allowed_base_paths(base_url, base_url_aliases):
        if base == "":
            if path == "":
                return "", base
            rest = path.lstrip("/")
            if rest and "/" not in rest:
                return rest, base
            continue

        if path == base:
            return "", base
        if path.startswith(base + "/"):
            rest = path[len(base) + 1:].strip("/")
            if rest and "/" not in rest:
                return rest, base

    return None


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def build_comprehensive_view(now_ts=None):
    """Build the comprehensive view across all registered providers.

    A provider that fails or is not configured never fails the whole view;
    its status is reported per provider instead.
    """
    providers = {}
    for provider in PROVIDERS:
        if not provider.is_configured():
            providers[provider.name] = {
                "configured": False,
                "status": "not_configured",
            }
            continue
        try:
            metrics = provider.fetch(os.environ[provider.env_key])
            entry = {"configured": True, "status": "ok"}
            entry.update(metrics.to_dict(now_ts))
            providers[provider.name] = entry
        except Exception as e:
            providers[provider.name] = {
                "configured": True,
                "status": "error",
                "error": str(e),
            }

    if now_ts is None:
        now_ts = time.time()
    return {
        "generatedAt": datetime.fromtimestamp(now_ts).isoformat(timespec="seconds"),
        "providers": providers,
    }


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------

class QuotaRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the quota endpoints."""

    def _send_json(self, status, payload):
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        base_url = os.environ.get("BASE_URL", DEFAULT_BASE_URL)
        base_url_aliases = os.environ.get("BASE_URL_ALIASES", "")

        route = resolve_route(self.path, base_url, base_url_aliases)
        if route is None:
            allowed = ", ".join(format_allowed_paths(base_url, base_url_aliases))
            provider_paths = ", ".join(
                f"{base}/{name}".replace("//", "/")
                for base in format_allowed_paths(base_url, base_url_aliases)
                for name in PROVIDER_MAP
            )
            self._send_json(404, {"error": f"Not Found. Use {allowed} or {provider_paths}"})
            return

        sub_path, _matched_base = route

        if sub_path == "":
            self._send_json(200, build_comprehensive_view())
            return

        provider = get_provider(sub_path)
        if provider is None:
            available = ", ".join(p.name for p in PROVIDERS)
            self._send_json(404, {"error": f"Unknown provider '{sub_path}'. Available: {available}"})
            return

        if not provider.is_configured():
            self._send_json(
                500,
                {"error": f"API Key is missing. Set {provider.env_key} environment variable."},
            )
            return

        try:
            metrics = provider.fetch(os.environ[provider.env_key])
            self._send_json(200, metrics.to_dict())
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def run_server(port):
    print(f"Starting web server on port {port}...")
    base_url = os.environ.get("BASE_URL", DEFAULT_BASE_URL) or "/"
    server = ThreadingHTTPServer(("0.0.0.0", port), QuotaRequestHandler)
    print(f"Server running at http://0.0.0.0:{port}{base_url}")
    print("Press Ctrl+C to stop the server")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.shutdown()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def print_provider_list():
    for provider in PROVIDERS:
        status = "configured" if provider.is_configured() else "not configured"
        print(f"{provider.name:<12} {provider.display_name} [{status}] ({provider.env_key})")


def main():
    parser = argparse.ArgumentParser(description="Query LLM quota usage across providers")
    parser.add_argument("provider", nargs="?", help="Provider slug (e.g. zai). Omit for comprehensive view")
    parser.add_argument("--list", action="store_true", help="List registered providers")
    parser.add_argument("--server", "-s", action="store_true", help="Run as web server")
    parser.add_argument("--port", "-p", type=int, default=9999, help="Port number for web server (default: 9999)")

    args = parser.parse_args()

    if args.list:
        print_provider_list()
        return

    if args.server:
        run_server(args.port)
        return

    if args.provider:
        provider = get_provider(args.provider)
        if provider is None:
            available = ", ".join(p.name for p in PROVIDERS)
            print(f"Error: Unknown provider '{args.provider}'. Available: {available}", file=sys.stderr)
            sys.exit(1)
        if not provider.is_configured():
            print(f"Error: API Key is missing. Set {provider.env_key} environment variable.", file=sys.stderr)
            sys.exit(1)
        try:
            metrics = provider.fetch(os.environ[provider.env_key])
            print(json.dumps(metrics.to_dict(), indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    print(json.dumps(build_comprehensive_view(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
