#!/bin/bash
#
# Run Locust with Web UI
#
# This script starts Locust with its web interface, allowing you to
# control the test parameters in real-time through your browser.
#
# Usage: ./scripts/run_web_ui.sh [HOST] [PORT]
#
# Example:
#   ./scripts/run_web_ui.sh http://localhost:8000
#   ./scripts/run_web_ui.sh http://localhost:8000 8089

set -e

# Configuration
HOST=${LOAD_TEST_BASE_URL:-"http://localhost:8000"}
WEB_PORT=${2:-8089}

echo "========================================="
echo "Priotag Backend - Load Test (Web UI)"
echo "========================================="
echo "Host: $HOST"
echo "Web UI Port: $WEB_PORT"
echo "========================================="
echo ""

# Change to load_tests directory
cd "$(dirname "$0")/.."

# Check if locust is installed
if ! command -v locust &> /dev/null; then
    echo "Error: Locust is not installed."
    echo "Please install it with: pip install -r requirements.txt"
    exit 1
fi

# Create reports directory if it doesn't exist
mkdir -p reports

echo "Starting Locust web UI..."
echo "Open your browser and navigate to: http://0.0.0.0:$WEB_PORT"
echo ""
echo "Press Ctrl+C to stop the test."
echo ""

# Run locust with web UI
locust \
    -f locustfile.py \
    --host "$HOST" \
    --web-port "$WEB_PORT"
