mod frontend
mod backend
mod monitoring

# List available commands
default:
    @just --list

# Start development environment
dev:
    docker compose -f docker-compose.dev.yml up

# Build dev images
dev-build:
    docker compose -f docker-compose.dev.yml build

# Start development environment in detached mode
dev-detached:
    docker compose -f docker-compose.dev.yml up -d

# Start production environment
prod:
    docker compose up -d

# Build production images
build:
    docker compose build

# Build production images without cache
build-no-cache:
    docker compose build --no-cache

# Stop all containers
down service="": 
    #!/usr/bin/env bash
    if [ -z "{{service}}" ]; then
        docker compose down
        docker compose -f docker-compose.dev.yml down
    else
        docker compose down {{service}}
        docker compose -f docker-compose.dev.yml down {{service}}
    fi

# Stop all containers and remove volumes
down-volumes:
    docker compose down -v
    docker compose -f docker-compose.dev.yml down -v

# View container logs
logs service="":
    #!/usr/bin/env bash
    if [ -z "{{service}}" ]; then
        docker compose logs -f
    else
        docker compose logs -f {{service}}
    fi

# View development container logs
logs-dev service="":
    #!/usr/bin/env bash
    if [ -z "{{service}}" ]; then
        docker compose -f docker-compose.dev.yml logs -f
    else
        docker compose -f docker-compose.dev.yml logs -f {{service}}
    fi

# Use act to test github action locally
github-action job:
    act --rm -j {{job}} --secret-file "./.github/.secrets"

# Run all tests
test: backend::test frontend::test

test-cli-locally:
    ./scripts/test-ci-locally.sh

# Format admin ui code
format-admin:
    docker compose -f docker-compose.dev.yml run --rm admin npm run format
    
# Format all code
format: backend::format frontend::format format-admin

# Lint admin ui code  
lint-admin:
    docker compose -f docker-compose.dev.yml run --rm admin npm run lint
    
# Lint all code
lint: backend::lint frontend::lint lint-admin

# Clean up Docker system
clean:
    docker compose down -v
    docker compose -f docker-compose.dev.yml down -v

# Check Docker stats
stats:
    docker stats

# Show running containers
ps:
    docker compose ps
    docker compose -f docker-compose.dev.yml ps

# Pull latest images
pull:
    docker compose pull
    docker compose -f docker-compose.dev.yml pull

# Restart a specific service
restart service:
    docker compose restart {{service}}

# Restart a specific service (development)
restart-dev service:
    docker compose -f docker-compose.dev.yml restart {{service}}

# View environment variables
env:
    docker compose -f docker-compose.dev.yml exec backend env | sort

# Copy built frontend files to backend (for testing static serving)
copy-static-to-backend:
    #!/usr/bin/env bash
    echo "Building frontend..."
    docker compose -f docker-compose.dev.yml exec frontend npm run build
    echo "Copying static files to backend..."
    docker cp priotag-frontend-dev:/app/build/. priotag-backend-dev:/app/static/
    echo "Static files copied! Access at http://localhost:8000"

# Run development with static file building
dev-with-static:
    docker compose -f docker-compose.dev-with-static.yml up

# Initialize secrets needed for running containers
init-secrets:
    ./scripts/init-secrets.sh

# Initialize the admin public / private key, where public key is needed for the server to run
init-admin-key:
    #!/usr/bin/env bash
    docker run --rm -it -v ./backend:/app priotag-backend:dev uv run src/priotag/scripts/initialize_admin_keypair.py
    mv ./backend/admin_public_key.pem ./.secrets/
    mv ./backend/admin_private_key.pem ./

# Initialize pocketbase directories for storage
pocketbase-init: init-secrets
    ./pocketbase/init.sh
    docker compose -f docker-compose.dev.yml run --rm backend uv run src/priotag/scripts/initialize_pocketbase.py

services-init:
    #!/usr/bin/env bash
    echo "Initializing Redis persistence..."
    mkdir -p redis_data
    sudo chmod 700 redis_data
    echo "Creating user for redis"
    sudo groupadd --gid 10001 redis-priotag
    sudo useradd --system \
      --uid 10001 --gid 10001 \
      --no-create-home \
      --shell /usr/sbin/nologin \
      redis-priotag
    echo "Setting ownership (requires sudo)..."
    sudo chown -R 10001:10001 redis_data || echo "⚠️  Could not set ownership for redis"
    echo "Redis persistence initialized"

    mkdir -p monitoring/prometheus/data
    sudo chmod 700 monitoring/prometheus/data
    sudo groupadd --gid 10002 prometheus-priotag
    sudo useradd --system \
      --uid 10002 --gid 10002 \
      --no-create-home \
      --shell /usr/sbin/nologin \
      prometheus-priotag
    echo "Setting ownership (requires sudo)..."
    sudo chown -R 10002:10002 monitoring/prometheus || echo "⚠️  Could not set ownership for prometheus"
    echo "Prometheus initialized"

    mkdir -p monitoring/grafana/data
    sudo chmod 700 monitoring/grafana/data
    sudo groupadd --gid 10003 grafana-priotag
    sudo useradd --system \
      --uid 10003 --gid 10003 \
      --no-create-home \
      --shell /usr/sbin/nologin \
      grafana-priotag
    echo "Setting ownership (requires sudo)..."
    sudo chown -R 10003:10003 monitoring/grafana || echo "⚠️  Could not set ownership for prometheus"
    echo "grafana initialized"

    mkdir -p monitoring/alertmanager/data
    sudo chmod 700 monitoring/alertmanager/data
    sudo groupadd --gid 10004 alertmanager-priotag
    sudo useradd --system \
      --uid 10004 --gid 10004 \
      --no-create-home \
      --shell /usr/sbin/nologin \
      alertmanager-priotag
    echo "Setting ownership (requires sudo)..."
    sudo chown -R 10004:10004 monitoring/alertmanager || echo "⚠️  Could not set ownership for prometheus"
    echo "alertmanager initialized"

# Reset redis cache
redis-clear:
    docker compose -f ./docker-compose.dev.yml exec redis redis-cli FLUSHALL

