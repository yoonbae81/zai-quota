#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
SERVICE_NAME="zai-quota"

echo "ZAI Quota - Systemd Service Installation"
echo "=============================================="
echo "Project directory: $PROJECT_DIR"
echo ""

# Load environment variables from .env
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(cat "$PROJECT_DIR/.env" | grep -v '^#' | xargs)
    echo "Environment variables loaded from .env"
    if [ -n "$PORT" ]; then
        echo "  Port: $PORT"
    else
        echo "  Port: 9999 (default)"
    fi
else
    echo "Warning: .env file not found, using default port 9999"
fi

# Create systemd directory
echo "Setting up systemd service..."
mkdir -p "$SYSTEMD_USER_DIR"

# Create service file with environment variables
echo "Creating $SERVICE_NAME.service..."
cat > "$SYSTEMD_USER_DIR/$SERVICE_NAME.service" << EOF
[Unit]
Description=ZAI Usage Quota Monitor Web Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=$PROJECT_DIR/.env

ExecStart=$PROJECT_DIR/.venv/bin/python3 $PROJECT_DIR/src/main.py --server --port \${PORT:-9999}

StandardOutput=journal
StandardError=journal
SyslogIdentifier=zai-quota

Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF

echo "Service file installed"
echo ""

# Reload systemd daemon
echo "Reloading systemd daemon..."
systemctl --user daemon-reload

# Enable and start service
echo "Enabling and starting service..."
systemctl --user enable "$SERVICE_NAME.service"
systemctl --user start "$SERVICE_NAME.service"

echo ""
echo "Service installation completed!"
echo ""
echo "Useful commands:"
echo "  • Check service status:  systemctl --user status $SERVICE_NAME.service"
echo "  • View logs:            journalctl --user -u $SERVICE_NAME.service"
echo "  • Follow logs:           journalctl --user -u $SERVICE_NAME.service -f"
echo "  • Stop service:          systemctl --user stop $SERVICE_NAME.service"
echo "  • Restart service:       systemctl --user restart $SERVICE_NAME.service"
echo ""
PORT_DISPLAY=${PORT:-9999}
echo "Web server will be available at: http://localhost:$PORT_DISPLAY/"
