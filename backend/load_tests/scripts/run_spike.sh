#!/bin/bash
#
# Spike Test
#
# This script runs a spike test to see how the system handles sudden traffic spikes.
# It rapidly spawns many users to simulate a sudden surge in traffic.
#
# Usage: ./scripts/run_spike.sh [HOST]
#
# Example:
#   ./scripts/run_spike.sh http://localhost:8000
#   ./scripts/run_spike.sh https://your-production-server.com

set -e

# Configuration
HOST=${LOAD_TEST_BASE_URL:-"http://localhost:8000"}
USERS=${LOAD_TEST_SPIKE_USERS:-50}
SPAWN_RATE=${LOAD_TEST_SPIKE_SPAWN_RATE:-25}  # Spawn users very quickly
RUN_TIME=${LOAD_TEST_RUN_TIME:-"3m"}

echo "========================================="
echo "Priotag Backend - Spike Test"
echo "========================================="
echo "Host: $HOST"
echo "Users: $USERS"
echo "Spawn Rate: $SPAWN_RATE users/second (RAPID)"
echo "Duration: $RUN_TIME"
echo "========================================="
echo ""
echo "WARNING: This test will rapidly spike load on the server."
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

# Run locust in headless mode with rapid spawn rate
locust \
    -f locustfile.py \
    --host "$HOST" \
    --users "$USERS" \
    --spawn-rate "$SPAWN_RATE" \
    --run-time "$RUN_TIME" \
    --headless \
    --html reports/spike_test_$(date +%Y%m%d_%H%M%S).html \
    --csv reports/spike_test_$(date +%Y%m%d_%H%M%S) \
    --only-summary

echo ""
echo "========================================="
echo "Spike test completed! Check the reports/ directory for results."
echo "========================================="
