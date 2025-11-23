#!/bin/bash
# Script to test CI workflow locally before pushing
# Run from project root: ./scripts/test-ci-locally.sh
#
# Options:
#   --no-build, --skip-build    Skip rebuilding Docker images

set -e

# Parse arguments
SKIP_BUILD=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-build|--skip-build)
            SKIP_BUILD=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-build, --skip-build    Skip rebuilding Docker images"
            echo "  -h, --help                  Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Change to project root directory (parent of scripts/)
cd "$(dirname "$0")/.."

echo "🧪 Testing CI workflow locally..."
echo ""

if [ -d ".secrets" ]; then
    echo "ℹ️  Your .secrets/ folder will remain untouched"
    echo ""
fi

# Create temporary test secrets directory with unique name
TEST_SECRETS_DIR="$(pwd)/.secrets.ci.test.$$"
echo "📝 Creating test secrets in ${TEST_SECRETS_DIR}/..."
mkdir -p "${TEST_SECRETS_DIR}"
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
  | openssl pkey -pubout -out "${TEST_SECRETS_DIR}/admin_public_key.pem"
echo "admin@example.com" > "${TEST_SECRETS_DIR}/pb_admin_email"
echo "admintest" > "${TEST_SECRETS_DIR}/pb_admin_password"
echo "service-id-$(openssl rand -hex 8)" > "${TEST_SECRETS_DIR}/pb_service_id"
echo "ServicePass$(openssl rand -hex 8)" > "${TEST_SECRETS_DIR}/pb_service_password"
echo "$(openssl rand -hex 32)" > "${TEST_SECRETS_DIR}/redis_pass"
echo "$(openssl rand -hex 32)" > "${TEST_SECRETS_DIR}/server_cache_key"
echo "$(openssl rand -hex 16)" > "${TEST_SECRETS_DIR}/metrics_token"
echo "✅ Test secrets created"
echo ""

# Export SECRETS_DIR for docker-compose.ci.yml to use
export SECRETS_DIR="${TEST_SECRETS_DIR}"

# Cleanup function
cleanup() {
    local exit_code=$?
    echo ""
    echo "🧹 Cleaning up..."

    # Remove test runner container if it exists
    if docker ps -a --format '{{.Names}}' | grep -q '^priotag-test-runner$'; then
        echo "🗑️  Removing test runner container"
        docker rm -f priotag-test-runner >/dev/null 2>&1 || true
    fi

    # Shutdown docker services
    docker compose -f docker-compose.dev.yml -f docker-compose.ci.yml down -v 2>/dev/null || true

    # Remove test secrets directory
    if [ -d "${TEST_SECRETS_DIR}" ]; then
        echo "🗑️  Removing test secrets"
        rm -rf "${TEST_SECRETS_DIR}"
    fi

    if [ $exit_code -ne 0 ]; then
        echo "❌ Script failed with exit code $exit_code"
    fi

    exit $exit_code
}

# Set trap to ensure cleanup happens even on error
trap cleanup EXIT INT TERM

# Build images (unless --no-build was specified)
if [ "$SKIP_BUILD" = false ]; then
    echo "🏗️  Building Docker images..."
    docker compose -f docker-compose.dev.yml -f docker-compose.ci.yml build --no-cache backend pocketbase
    echo "✅ Images built"
    echo ""
else
    echo "⏭️  Skipping Docker image build (using existing images)"
    echo ""
fi

# Start dependencies
echo "🚀 Starting PocketBase and Redis..."
docker compose -f docker-compose.dev.yml -f docker-compose.ci.yml up -d pocketbase redis
echo "⏳ Waiting for services to be healthy..."
timeout 120 sh -c 'until docker compose -f docker-compose.dev.yml -f docker-compose.ci.yml ps pocketbase | grep -q "healthy" && docker compose -f docker-compose.dev.yml -f docker-compose.ci.yml ps redis | grep -q "healthy"; do sleep 2; done'
echo "✅ Services are ready!"
echo ""

# Initialize PocketBase admin using exec (operates on running container)
echo "👤 Creating PocketBase superuser..."
docker compose -f docker-compose.dev.yml -f docker-compose.ci.yml exec pocketbase \
  ./pocketbase superuser upsert admin@example.com admintest
echo "✅ Superuser created"
echo ""

# Setup PocketBase data (magic word, service account)
# Use 'run --no-deps' to avoid recreating pocketbase/redis containers
echo "🔧 Setting up PocketBase test data..."
docker compose -f docker-compose.dev.yml -f docker-compose.ci.yml run --rm --no-deps backend \
  uv run python tests/integration/setup_pocketbase.py
echo "✅ PocketBase data setup complete"
echo ""

# Run tests
echo "🧪 Running tests with coverage..."
# Note: Don't use --rm so we can copy the coverage file afterward
docker compose -f docker-compose.dev.yml -f docker-compose.ci.yml run --name priotag-test-runner --no-deps \
  backend \
  uv run pytest --cov=priotag --cov-report=xml --cov-report=term-missing

# Copy coverage report from the test container
echo ""
echo "📊 Copying coverage report..."
docker cp priotag-test-runner:/app/coverage.xml ./coverage.xml 2>/dev/null || echo "⚠️  No coverage file found"

echo ""
echo "✅ CI test completed successfully!"
echo "📊 Coverage report saved to: coverage.xml"
