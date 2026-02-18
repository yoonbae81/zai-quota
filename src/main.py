#!/usr/bin/env python3

"""
Purpose: Query Z.ai usage quota limits and output calculated metrics in JSON format.
Reference: https://github.com/zai-org/zai-coding-plugins/blob/main/plugins/glm-plan-usage/skills/usage-query-skill/scripts/query-usage.mjs
"""

import warnings
# Suppress urllib3's NotOpenSSLWarning (must be set before importing requests)
warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")
warnings.filterwarnings("ignore", message=".*OpenSSL 1.1.1+.*")

import urllib.request
import urllib.error
import json
import time
import sys
import os
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone

# Global Constants
USAGE_API_URL = "https://api.z.ai/api/monitor/usage/quota/limit"

def fetch_usage_data(api_key):
    """Sends a request to the API and returns JSON data."""
    headers = {
        "Authorization": api_key,
        "Accept-Language": "en-US,en",
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(USAGE_API_URL, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        raise Exception(f"HTTP Error: {e.code} {e.reason}")
    except urllib.error.URLError as e:
        raise Exception(f"URL Error: {e.reason}")
    
    if data.get("code") != 200:
        raise Exception(f"API Error: {data.get('msg', 'Unknown error')} (code: {data.get('code')})")
    
    return data

def extract_token_limit(data):
    """Extracts the TOKENS_LIMIT section from the response data."""
    limits = data.get("data", {}).get("limits", [])
    token_limit = next((item for item in limits if item["type"] == "TOKENS_LIMIT"), None)
    
    if not token_limit:
        raise Exception("TOKENS_LIMIT not found in response data")
        
    return token_limit

def calculate_metrics(token_limit):
    """Calculates the necessary metrics based on the extracted data."""
    quota_percentage = token_limit.get("percentage", 0)
    next_reset_ms = token_limit.get("nextResetTime", 0)
    
    # 1. Calculate nextReset (Local time, HH:mm)
    next_reset_dt = datetime.fromtimestamp(next_reset_ms / 1000)
    next_reset_str = next_reset_dt.strftime("%H:%M")
    
    # 2. Calculate remainingTime (HH:mm)
    now_ts = time.time()
    diff_sec = max(0, (next_reset_ms / 1000) - now_ts)
    hours = int(diff_sec // 3600)
    minutes = int((diff_sec % 3600) // 60)
    remaining_str = f"{hours:02d}:{minutes:02d}"
    
    return {
        "quotaPercentage": quota_percentage,
        "nextReset": next_reset_str,
        "remainingTime": remaining_str
    }

class UsageRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for usage query endpoint."""
    
    
    def do_GET(self):
        """Handle GET requests."""
        api_key = os.environ.get("ZAI_API_KEY")
        base_url = os.environ.get("BASE_URL", "").rstrip("/")
        
        # Validate path (allow base_url, base_url/, or / if base_url is empty)
        current_path = self.path.split('?')[0].rstrip("/")
        if current_path != base_url:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"error": f"Not Found. Use {base_url or '/'}"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            return

        if not api_key:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"error": "API Key is missing. Set ZAI_API_KEY environment variable."}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            return
        
        try:
            data = fetch_usage_data(api_key)
            token_limit = extract_token_limit(data)
            result = calculate_metrics(token_limit)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, indent=2, ensure_ascii=False).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"error": str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass






def main():
    parser = argparse.ArgumentParser(description='Query Z.ai quota usage')
    parser.add_argument('--server', '-s', action='store_true', help='Run as web server')
    parser.add_argument('--port', '-p', type=int, default=9999, help='Port number for web server (default: 9999)')
    parser.add_argument('api_key', nargs='?', help='API key (optional, can use ZAI_API_KEY env var)')
    
    args = parser.parse_args()
    

    
    if args.server:
        # Web server mode
        api_key = args.api_key or os.environ.get("ZAI_API_KEY")
        if api_key:
            os.environ["ZAI_API_KEY"] = api_key
            print(f"Using API Key: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}")
        else:
            print("Warning: No API Key found.")
        
        print(f"Starting web server on port {args.port}...")
        server = HTTPServer(('0.0.0.0', args.port), UsageRequestHandler)
        print(f"Server running at http://0.0.0.0:{args.port}/")
        print("Press Ctrl+C to stop the server")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
            server.shutdown()
    else:
        # CLI mode
        api_key = args.api_key or os.environ.get("ZAI_API_KEY")
        
        if not api_key:
            print("Error: API Key is missing.", file=sys.stderr)
            print("\nUsage:", file=sys.stderr)
            print(f"  {sys.argv[0]} <your_api_key>", file=sys.stderr)
            print(f"  {sys.argv[0]} --server [--port PORT]", file=sys.stderr)
            print("  or set environment variable: export ZAI_API_KEY='your_api_key'", file=sys.stderr)
            sys.exit(1)

        try:
            data = fetch_usage_data(api_key)
            token_limit = extract_token_limit(data)
            result = calculate_metrics(token_limit)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
