#!/bin/bash
#
# Stress Test
#
# This script runs a stress test to find the breaking point of the system.
# It gradually increases load until the system shows signs of stress.
#
# Usage: ./scripts/run_stress.sh [HOST]
#
# Example:
#   ./scripts/run_stress.sh http://localhost:8000
#   ./scripts/run_stress.sh https://your-production-server.com

set -e

# Configuration
HOST=${1:-"http://localhost:8000"}
USERS=${LOAD_TEST_STRESS_USERS:-100}
SPAWN_RATE=${LOAD_TEST_SPAWN_RATE:-5}
RUN_TIME=${LOAD_TEST_RUN_TIME:-"10m"}

echo "========================================="
echo "Priotag Backend - Stress Test"
echo "========================================="
echo "Host: $HOST"
echo "Users: $USERS"
echo "Spawn Rate: $SPAWN_RATE users/second"
echo "Duration: $RUN_TIME"
echo "========================================="
echo ""
echo "WARNING: This test will put significant load on the server."
echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
sleep 5

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

# Run locust in headless mode with more users
locust \
    -f locustfile.py \
    --host "$HOST" \
    --users "$USERS" \
    --spawn-rate "$SPAWN_RATE" \
    --run-time "$RUN_TIME" \
    --headless \
    --html reports/stress_test_$(date +%Y%m%d_%H%M%S).html \
    --csv reports/stress_test_$(date +%Y%m%d_%H%M%S) \
    --only-summary

echo ""
echo "========================================="
echo "Stress test completed! Check the reports/ directory for results."
echo "========================================="
