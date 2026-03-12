#!/bin/bash
###############################################################################
# Nest Egg - Production Runner
#
# Builds and starts the full production stack via Docker Compose.
# Expects .env.docker to exist (create with ./scripts/prod/setup.sh).
#
# Usage: ./scripts/prod/run.sh [command]
#
# Commands:
#   start      Build (if needed) and start all services (default)
#   stop       Stop all services
#   restart    Restart all services
#   status     Show service status and health
#   logs       Tail logs from all services
#   migrate    Run database migrations
#   rebuild    Force-rebuild images and restart
#   help       Show this help message
###############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

ENV_FILE=".env.docker"
COMPOSE_FILE="docker-compose.yml"

CMD="${1:-start}"

###############################################################################
# Helpers
###############################################################################

print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"
}

print_success() { echo -e "  ${GREEN}✓${NC} $1"; }
print_error()   { echo -e "  ${RED}✗${NC} $1"; }
print_info()    { echo -e "  ${BLUE}ℹ${NC} $1"; }

# Detect compose command
compose_cmd() {
    if docker compose version >/dev/null 2>&1; then
        echo "docker compose"
    elif command -v docker-compose >/dev/null 2>&1; then
        echo "docker-compose"
    else
        echo ""
    fi
}

COMPOSE=$(compose_cmd)

preflight() {
    if [ -z "$COMPOSE" ]; then
        print_error "Docker Compose not found"
        exit 1
    fi

    if ! docker info >/dev/null 2>&1; then
        print_error "Docker daemon is not running"
        exit 1
    fi

    if [ ! -f "$ENV_FILE" ]; then
        print_error "$ENV_FILE not found"
        echo -e "  Run ${YELLOW}./scripts/prod/setup.sh${NC} to create it"
        exit 1
    fi

    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "$COMPOSE_FILE not found"
        exit 1
    fi
}

compose() {
    $COMPOSE --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

###############################################################################
# Commands
###############################################################################

cmd_start() {
    print_header "Starting Nest Egg (Production)"

    preflight

    # Validate env before starting
    "$SCRIPT_DIR/setup.sh" --check
    echo ""

    print_info "Building and starting services..."
    compose up -d --build

    # Wait for backend health
    print_info "Waiting for backend to become healthy..."
    local max_wait=90
    local waited=0
    while [ $waited -lt $max_wait ]; do
        if compose ps 2>/dev/null | grep -q "nestegg-backend.*healthy"; then
            break
        fi
        sleep 3
        waited=$((waited + 3))
        echo -n "."
    done
    echo ""

    if [ $waited -ge $max_wait ]; then
        print_error "Backend did not become healthy within ${max_wait}s"
        echo -e "  Check logs: ${YELLOW}./scripts/prod/run.sh logs${NC}"
        exit 1
    fi

    # Run migrations
    print_info "Running database migrations..."
    compose exec -T backend alembic upgrade head
    print_success "Migrations complete"

    cmd_status
}

cmd_stop() {
    print_header "Stopping Nest Egg"
    preflight
    compose down
    print_success "All services stopped"
}

cmd_restart() {
    print_header "Restarting Nest Egg"
    preflight
    compose restart
    print_success "All services restarted"
}

cmd_status() {
    print_header "Service Status"
    preflight

    compose ps

    echo ""

    # Health checks
    local backend_url="http://localhost:8000/health"
    local frontend_url="http://localhost:${FRONTEND_PORT:-80}"

    if curl -sf "$backend_url" >/dev/null 2>&1; then
        print_success "Backend API: healthy"
    else
        print_error "Backend API: not responding"
    fi

    if curl -sf "$frontend_url" >/dev/null 2>&1; then
        print_success "Frontend: responding"
    else
        print_error "Frontend: not responding"
    fi

    if curl -sf "http://localhost:5555" >/dev/null 2>&1; then
        print_success "Flower: responding"
    else
        print_info "Flower: not responding (optional)"
    fi

    echo ""
    echo -e "  ${BOLD}Access:${NC}"
    echo -e "    Frontend:  ${GREEN}http://localhost:${FRONTEND_PORT:-80}${NC}"
    echo -e "    API:       ${GREEN}http://localhost:8000${NC}"
    echo -e "    API Docs:  ${GREEN}http://localhost:8000/docs${NC}"
    echo -e "    Flower:    ${GREEN}http://localhost:5555${NC}"
    echo ""
}

cmd_logs() {
    preflight
    compose logs -f "$@"
}

cmd_migrate() {
    print_header "Running Database Migrations"
    preflight
    compose exec -T backend alembic upgrade head
    print_success "Migrations complete"
}

cmd_rebuild() {
    print_header "Rebuilding and Restarting"
    preflight
    compose down
    compose build --no-cache
    cmd_start
}

cmd_help() {
    head -n 18 "$0" | tail -n 16
}

###############################################################################
# Main
###############################################################################

case "$CMD" in
    start)   cmd_start ;;
    stop)    cmd_stop ;;
    restart) cmd_restart ;;
    status)  cmd_status ;;
    logs)    shift; cmd_logs "$@" ;;
    migrate) cmd_migrate ;;
    rebuild) cmd_rebuild ;;
    help|--help|-h) cmd_help ;;
    *)
        echo -e "${RED}Unknown command: $CMD${NC}"
        cmd_help
        exit 1
        ;;
esac
