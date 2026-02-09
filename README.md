# ZAI Quota

A Python script to query Z.ai usage quota limits and output calculated metrics in JSON format.

## Features

- Query Z.ai API for current usage quota limits
- Calculate usage percentage
- Display next reset time and remaining time
- Run as CLI tool or web server
- Support for systemd service automation (web server mode)
- Configurable port via environment variable

## Installation

### Prerequisites

- Python 3.7 or higher
- pip

### Setup

```bash
# Clone repository
git clone <repository-url>
cd zai-quota

# Run setup script
./scripts/setup-env.sh

# Configure environment variables
nano .env
```

Set your Z.ai API key and optional port in `.env`:
```
ZAI_API_KEY=your_api_key_here
PORT=9999
```

## Usage

### Manual Execution (CLI)

```bash
# Run with API key from .env
./scripts/run.sh

# Or specify API key directly
./scripts/run.sh <your_api_key>
```

### Web Server Mode

```bash
# Start web server on port from .env (default: 9999)
./scripts/run.sh --server

# Or specify custom port (overrides .env)
./scripts/run.sh --server --port 8080
```

Then access the endpoint:
```bash
curl http://0.0.0.0:9999/
```

### Systemd Service (Linux)

```bash
# Install systemd service (runs web server)
./scripts/install-systemd.sh

# Check service status
systemctl --user status zai-quota.service

# View logs
journalctl --user -u zai-quota.service -f

# Stop service
systemctl --user stop zai-quota.service

# Restart service
systemctl --user restart zai-quota.service
```

The systemd service runs the web server continuously with auto-restart on failure. Port is configured via the `PORT` environment variable in `.env` (default: 9999).

## Output Format

```json
{
  "quotaUsed": 45.67,
  "nextReset": "00:00",
  "remainingTime": "05:23"
}
```

- `quotaUsed`: Percentage of quota used (0-100)
- `nextReset`: Local time when quota resets (HH:MM)
- `remainingTime`: Time remaining until reset (HH:MM)

## Project Structure

```
zai-quota/
├── src/                    # Source code
│   └── main.py            # Main script
├── tests/                  # Test suite
│   ├── __init__.py
│   ├── test_main.py
│   └── README.md
├── scripts/                # Setup and deployment scripts
│   ├── setup-env.sh        # Environment setup
│   ├── install-systemd.sh  # Systemd service installation
│   ├── run.sh              # Main execution script
│   └── systemd/           # Systemd configuration files
│       └── zai-quota.service
├── .venv/                  # Python virtual environment
├── .env                    # Environment variables (private)
├── .env.example            # Environment variable template
├── requirements.txt        # Python dependencies
├── .gitignore             # Git ignore file
└── README.md              # This file
```

## Running Tests

```bash
# Run all tests
python3 -m unittest discover tests

# Run specific test file
python3 -m unittest tests.test_main

# Verbose output
python3 -m unittest discover tests -v
```

## License

MIT License
