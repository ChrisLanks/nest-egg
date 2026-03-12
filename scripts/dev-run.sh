#!/bin/bash
###############################################################################
# Nest Egg - Development Runner
#
# Starts all services needed for local development:
#   - Docker services (PostgreSQL, Redis)
#   - Backend API (uvicorn with hot-reload)
#   - Celery worker + beat scheduler
#   - Frontend dev server (Vite)
#
# Usage: ./scripts/dev-run.sh [options]
#
# Options:
#   --skip-docker      Don't start Docker services (already running)
#   --skip-celery      Don't start Celery worker/beat
#   --skip-frontend    Don't start frontend dev server
#   --skip-backend     Don't start backend API server
#   --help             Show this help message
###############################################################################

set -e

# Resolve project root (parent of scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Flags
SKIP_DOCKER=false
SKIP_CELERY=false
SKIP_FRONTEND=false
SKIP_BACKEND=false

# Track background PIDs for cleanup
PIDS=()

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-docker)
            SKIP_DOCKER=true
            shift
            ;;
        --skip-celery)
            SKIP_CELERY=true
            shift
            ;;
        --skip-frontend)
            SKIP_FRONTEND=true
            shift
            ;;
        --skip-backend)
            SKIP_BACKEND=true
            shift
            ;;
        --help)
            head -n 20 "$0" | tail -n 18
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

###############################################################################
# Helpers
###############################################################################

print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"
}

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
print_error()   { echo -e "${RED}✗ $1${NC}"; }
print_info()    { echo -e "${BLUE}ℹ $1${NC}"; }

cleanup() {
    echo ""
    print_info "Shutting down services..."
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            wait "$pid" 2>/dev/null
        fi
    done
    print_success "All services stopped"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Detect docker compose command
detect_compose_cmd() {
    if docker compose version >/dev/null 2>&1; then
        echo "docker compose"
    elif command -v docker-compose >/dev/null 2>&1; then
        echo "docker-compose"
    else
        echo ""
    fi
}

# Try to start the Docker daemon if it isn't running.
ensure_docker_running() {
    if docker info >/dev/null 2>&1; then
        return 0
    fi

    print_warning "Docker daemon is not running"

    if grep -qi microsoft /proc/version 2>/dev/null; then
        print_info "Starting Docker daemon (may ask for your password once)..."
        if sudo service docker start >/dev/null 2>&1; then
            sleep 2
            if docker info >/dev/null 2>&1; then
                print_success "Docker daemon started"
                return 0
            fi
        fi
    fi

    if command -v systemctl >/dev/null 2>&1; then
        print_info "Starting Docker daemon via systemctl..."
        if sudo systemctl start docker >/dev/null 2>&1; then
            sleep 2
            if docker info >/dev/null 2>&1; then
                print_success "Docker daemon started"
                return 0
            fi
        fi
    fi

    print_error "Could not start Docker daemon. Start it manually and retry."
    return 1
}

###############################################################################
# Preflight Checks
###############################################################################

preflight() {
    local ok=true

    if ! $SKIP_BACKEND; then
        if [ ! -d "backend/venv" ]; then
            print_error "Backend venv not found. Run ./scripts/dev-setup.sh first."
            ok=false
        fi
    fi

    if ! $SKIP_FRONTEND; then
        if [ ! -d "frontend/node_modules" ]; then
            print_error "Frontend node_modules not found. Run ./scripts/dev-setup.sh first."
            ok=false
        fi
    fi

    if ! $ok; then
        exit 1
    fi
}

###############################################################################
# Start Services
###############################################################################

start_docker() {
    if $SKIP_DOCKER; then
        print_warning "Skipping Docker services (--skip-docker)"
        return
    fi

    print_info "Starting Docker services (PostgreSQL, Redis)..."

    if ! ensure_docker_running; then
        print_error "Docker is required. Use --skip-docker if services are already running."
        exit 1
    fi

    local compose_cmd
    compose_cmd=$(detect_compose_cmd)
    if [ -z "$compose_cmd" ]; then
        print_error "Docker Compose not found"
        exit 1
    fi

    $compose_cmd -f docker-compose.dev.yml up -d postgres redis

    # Wait for healthy
    local max_wait=30
    local waited=0
    while [ $waited -lt $max_wait ]; do
        local ps_output
        ps_output=$($compose_cmd -f docker-compose.dev.yml ps 2>/dev/null)
        local pg_ok=false redis_ok=false
        echo "$ps_output" | grep -q "postgres.*healthy\|nestegg-dev-postgres.*healthy" && pg_ok=true
        echo "$ps_output" | grep -q "redis.*healthy\|nestegg-dev-redis.*healthy" && redis_ok=true
        if $pg_ok && $redis_ok; then
            print_success "PostgreSQL and Redis are healthy"
            return
        fi
        sleep 2
        waited=$((waited + 2))
        echo -n "."
    done
    echo ""
    print_warning "Services may not be fully ready yet"
}

start_backend() {
    if $SKIP_BACKEND; then
        print_warning "Skipping backend (--skip-backend)"
        return
    fi

    print_info "Starting backend API (uvicorn)..."
    (
        cd backend
        source venv/bin/activate
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload 2>&1 | \
            sed "s/^/[backend] /"
    ) &
    PIDS+=($!)
    print_success "Backend starting on http://localhost:8000"
}

start_celery() {
    if $SKIP_CELERY; then
        print_warning "Skipping Celery (--skip-celery)"
        return
    fi

    if $SKIP_BACKEND; then
        print_warning "Skipping Celery (backend skipped)"
        return
    fi

    print_info "Starting Celery worker..."
    (
        cd backend
        source venv/bin/activate
        celery -A app.workers.celery_app worker --loglevel=info 2>&1 | \
            sed "s/^/[celery-worker] /"
    ) &
    PIDS+=($!)

    print_info "Starting Celery beat scheduler..."
    (
        cd backend
        source venv/bin/activate
        celery -A app.workers.celery_app beat --loglevel=info 2>&1 | \
            sed "s/^/[celery-beat] /"
    ) &
    PIDS+=($!)

    print_success "Celery worker and beat started"
}

start_frontend() {
    if $SKIP_FRONTEND; then
        print_warning "Skipping frontend (--skip-frontend)"
        return
    fi

    print_info "Starting frontend dev server (Vite)..."
    (
        cd frontend
        npx vite --host 0.0.0.0 --port 5173 2>&1 | \
            sed "s/^/[frontend] /"
    ) &
    PIDS+=($!)
    print_success "Frontend starting on http://localhost:5173"
}

###############################################################################
# Main
###############################################################################

main() {
    echo -e "${BLUE}"
    cat << "EOF"
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║                Nest Egg Dev Server                        ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"

    preflight
    start_docker
    start_backend
    start_celery
    start_frontend

    print_header "All Services Running"

    echo -e "   Frontend:      ${GREEN}http://localhost:5173${NC}"
    echo -e "   Backend API:   ${GREEN}http://localhost:8000${NC}"
    echo -e "   API Docs:      ${GREEN}http://localhost:8000/docs${NC}"
    echo ""
    echo -e "   Press ${YELLOW}Ctrl+C${NC} to stop all services"
    echo ""

    # Wait for any background process to exit
    wait
}

main
