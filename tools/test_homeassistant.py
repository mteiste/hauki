#!/usr/bin/env python3
"""
Home Assistant API Testing Tool

This tool runs on the host machine to test Home Assistant API connectivity
and inspect responses. It reads config.json to get the URL and token.

Usage:
    python3 tools/test_homeassistant.py
    python3 tools/test_homeassistant.py --endpoint /api/states
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests library not found")
    print("Install it with: pip install requests")
    sys.exit(1)


def load_config(config_path="config.json"):
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"Error: {config_path} not found")
        print("Please create config.json from config.json.example")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {config_path}")
        print(f"  {e}")
        sys.exit(1)


def test_api_endpoint(url, token, endpoint="/api/", timeout=10):
    """Test a Home Assistant API endpoint.

    Args:
        url: Home Assistant base URL
        token: Long-lived access token
        endpoint: API endpoint to test (default: /api/)
        timeout: Request timeout in seconds

    Returns:
        tuple: (success, response_data, status_code)
    """
    # Ensure URL doesn't have trailing slash
    url = url.rstrip('/')

    # Ensure endpoint starts with /
    if not endpoint.startswith('/'):
        endpoint = '/' + endpoint

    full_url = f"{url}{endpoint}"

    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'

    print(f"\n{'=' * 70}")
    print(f"Testing: {full_url}")
    print(f"{'=' * 70}")

    try:
        response = requests.get(full_url, headers=headers, timeout=timeout)

        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")

        if response.status_code == 200:
            print("✓ Success!")
            try:
                data = response.json()
                print("\nResponse Data:")
                print(json.dumps(data, indent=2))
                return True, data, response.status_code
            except json.JSONDecodeError:
                print("\nResponse Text:")
                print(response.text)
                return True, response.text, response.status_code
        else:
            print(f"✗ Request failed with status {response.status_code}")
            print("\nResponse:")
            print(response.text)
            return False, None, response.status_code

    except requests.exceptions.ConnectionError as e:
        print(f"✗ Connection Error: {e}")
        print("\nPossible issues:")
        print("  - Home Assistant is not running")
        print("  - Wrong URL in config.json")
        print("  - Network connectivity issue")
        return False, None, None
    except requests.exceptions.Timeout:
        print(f"✗ Request timed out after {timeout} seconds")
        return False, None, None
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False, None, None


def main():
    parser = argparse.ArgumentParser(
        description="Test Home Assistant API connectivity from host machine"
    )
    parser.add_argument(
        '--config',
        default='config.json',
        help='Path to config.json (default: config.json)'
    )
    parser.add_argument(
        '--endpoint',
        default='/api/',
        help='API endpoint to test (default: /api/)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=10,
        help='Request timeout in seconds (default: 10)'
    )

    args = parser.parse_args()

    print("Home Assistant API Testing Tool")
    print("=" * 70)

    # Load configuration
    print(f"\nLoading config from: {args.config}")
    config = load_config(args.config)

    # Get Home Assistant settings
    ha_config = config.get('homeassistant', {})
    url = ha_config.get('url')
    token = ha_config.get('token')
    config_timeout = ha_config.get('timeout', 10)

    if not url:
        print("Error: 'homeassistant.url' not found in config.json")
        sys.exit(1)

    if not token or token == "your-long-lived-access-token-here":
        print("Warning: Invalid or placeholder token in config.json")
        print("  Some endpoints may not work without a valid token")

    print(f"Home Assistant URL: {url}")
    print(f"Token configured: {'Yes' if token and token != 'your-long-lived-access-token-here' else 'No'}")

    # Test the endpoint
    timeout = args.timeout if args.timeout else config_timeout
    success, data, status_code = test_api_endpoint(
        url, token, args.endpoint, timeout
    )

    # Additional common endpoints to test
    if args.endpoint == '/api/' and success:
        print("\n" + "=" * 70)
        print("Testing additional endpoints...")
        print("=" * 70)

        # Test /api/config
        print("\n--- Testing /api/config ---")
        success, data, _ = test_api_endpoint(url, token, '/api/config', timeout)

        if success and data:
            print("\nKey Config Info:")
            if isinstance(data, dict):
                print(f"  Version: {data.get('version', 'N/A')}")
                print(f"  Location Name: {data.get('location_name', 'N/A')}")
                print(f"  Time Zone: {data.get('time_zone', 'N/A')}")

    print("\n" + "=" * 70)
    print("Testing complete!")
    print("=" * 70)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
