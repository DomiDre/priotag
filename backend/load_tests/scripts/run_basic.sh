#!/bin/bash
#
# Basic Load Test
#
# This script runs a basic load test to establish baseline performance.
# It simulates a moderate number of concurrent users performing typical operations.
#
# Usage: ./scripts/run_basic.sh [HOST]
#
# Example:
#   ./scripts/run_basic.sh http://localhost:8000
#   ./scripts/run_basic.sh https://your-production-server.com

set -e

# Configuration
HOST=${1:-"http://localhost:8000"}
USERS=${LOAD_TEST_USERS:-20}
SPAWN_RATE=${LOAD_TEST_SPAWN_RATE:-2}
RUN_TIME=${LOAD_TEST_RUN_TIME:-"5m"}

echo "========================================="
echo "Priotag Backend - Basic Load Test"
echo "========================================="
echo "Host: $HOST"
echo "Users: $USERS"
echo "Spawn Rate: $SPAWN_RATE users/second"
echo "Duration: $RUN_TIME"
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

# Run locust in headless mode
locust \
    -f locustfile.py \
    --host "$HOST" \
    --users "$USERS" \
    --spawn-rate "$SPAWN_RATE" \
    --run-time "$RUN_TIME" \
    --headless \
    --html reports/basic_load_test_$(date +%Y%m%d_%H%M%S).html \
    --csv reports/basic_load_test_$(date +%Y%m%d_%H%M%S) \
    --only-summary

echo ""
echo "========================================="
echo "Test completed! Check the reports/ directory for results."
echo "========================================="
