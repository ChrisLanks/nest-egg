#!/bin/bash
###############################################################################
# Nest Egg - One-Shot Local Development Setup Script
#
# This script automates the complete setup of Nest Egg on a local machine.
# It uses Docker Compose for PostgreSQL and Redis so no root access is needed
# beyond starting the Docker daemon (if it isn't already running).
#
# Prerequisites (install once before running):
#   - Docker (user must be in the 'docker' group)
#   - Python 3.11+
#   - Node.js 18+
#   - Git
#
# Usage: ./scripts/dev-setup.sh [options]
#
# Options:
#   --skip-docker      Skip Docker Compose services
#   --skip-frontend    Skip frontend setup
#   --skip-backend     Skip backend setup
#   --seed-user        Create test@test.com with mock data (password: test1234)
#   --seed-user2       Create test2@test.com with mock data (password: test1234)
#   --yes              Answer yes to all prompts (non-interactive)
#   --help             Show this help message
###############################################################################

set -e  # Exit on error

# Resolve project root (parent of scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Flags
SKIP_DOCKER=false
SKIP_FRONTEND=false
SKIP_BACKEND=false
SEED_USER=false
SEED_USER2=false
AUTO_YES=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-docker)
            SKIP_DOCKER=true
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
        --seed-user)
            SEED_USER=true
            shift
            ;;
        --seed-user2)
            SEED_USER2=true
            shift
            ;;
        --yes|-y)
            AUTO_YES=true
            shift
            ;;
        --help)
            head -n 27 "$0" | tail -n 25
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

###############################################################################
# Utility Functions
###############################################################################

print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

confirm() {
    if $AUTO_YES; then
        return 0
    fi
    local prompt="$1 (y/N): "
    read -p "$prompt" -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# Detect docker compose command — verify daemon connectivity (no sudo)
detect_compose_cmd() {
    if docker compose version >/dev/null 2>&1; then
        echo "docker compose"
        return
    elif command_exists docker-compose; then
        echo "docker-compose"
        return
    fi
    echo ""
}

COMPOSE_CMD=""

generate_secret_key() {
    if command_exists openssl; then
        openssl rand -hex 32
    else
        python3 -c "import secrets; print(secrets.token_hex(32))"
    fi
}

generate_fernet_key() {
    # Fernet key = URL-safe base64-encoded 32 random bytes (stdlib only, no pip deps)
    python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
}

###############################################################################
# Docker Daemon Helper
###############################################################################

# Try to start the Docker daemon if it isn't running.
# This is the ONLY step that may require sudo (WSL2 needs it to start the
# service). Once the daemon is up, everything else runs as the current user
# via docker-group membership.
ensure_docker_running() {
    if docker info >/dev/null 2>&1; then
        return 0
    fi

    print_warning "Docker daemon is not running"

    # WSL2: try 'sudo service docker start' (lightweight, no systemd needed)
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

    # systemd systems
    if command_exists systemctl; then
        print_info "Starting Docker daemon via systemctl (may ask for your password once)..."
        if sudo systemctl start docker >/dev/null 2>&1; then
            sleep 2
            if docker info >/dev/null 2>&1; then
                print_success "Docker daemon started"
                return 0
            fi
        fi
    fi

    print_error "Could not start Docker daemon."
    print_info "Start it manually and re-run this script:"
    print_info "  sudo service docker start   # WSL2 / sysvinit"
    print_info "  sudo systemctl start docker  # systemd"
    return 1
}

###############################################################################
# Prerequisite Checks
###############################################################################

check_prerequisites() {
    print_header "Checking Prerequisites"

    local missing_deps=()

    # -- Docker --
    if ! $SKIP_DOCKER; then
        if ! command_exists docker; then
            missing_deps+=("Docker")
            print_error "Docker not found — install: https://docs.docker.com/get-docker/"
        else
            print_success "Docker found: $(docker --version 2>&1 | head -1)"

            # Ensure the daemon is running (may prompt for sudo once)
            if ensure_docker_running; then
                COMPOSE_CMD=$(detect_compose_cmd)
                if [ -n "$COMPOSE_CMD" ]; then
                    print_success "Docker Compose found ($COMPOSE_CMD)"
                else
                    missing_deps+=("Docker Compose")
                    print_error "Docker Compose not found"
                fi
            else
                missing_deps+=("Docker daemon (not running)")
            fi
        fi
    fi

    # -- Python --
    if ! $SKIP_BACKEND; then
        if ! command_exists python3; then
            missing_deps+=("Python 3.11+")
            print_error "Python 3 not found"
        else
            PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
            print_success "Python found: $PYTHON_VERSION"

            # Verify python3-venv is usable
            if ! python3 -m venv --help >/dev/null 2>&1; then
                missing_deps+=("python3-venv")
                print_error "python3-venv not available — install: sudo apt-get install python3-venv"
            fi
        fi
    fi

    # -- Node.js (must be a real Linux binary, not a Windows .cmd on WSL PATH) --
    if ! $SKIP_FRONTEND; then
        local node_ok=false
        if command_exists node; then
            if node --version >/dev/null 2>&1; then
                NODE_VERSION=$(node --version)
                print_success "Node.js found: $NODE_VERSION"
                node_ok=true
            fi
        fi

        if ! $node_ok; then
            missing_deps+=("Node.js 18+")
            print_error "Node.js not found (or not functional)"
        fi

        if $node_ok; then
            if command_exists npm && npm --version >/dev/null 2>&1; then
                NPM_VERSION=$(npm --version)
                print_success "npm found: v$NPM_VERSION"
            else
                missing_deps+=("npm")
                print_error "npm not found"
            fi
        fi
    fi

    # -- Git --
    if ! command_exists git; then
        missing_deps+=("git")
        print_error "git not found"
    else
        print_success "git found: $(git --version)"
    fi

    # Report missing dependencies
    if [ ${#missing_deps[@]} -gt 0 ]; then
        echo ""
        print_error "Missing required dependencies: ${missing_deps[*]}"
        echo ""
        echo "  Install the missing tools and re-run this script."
        echo "  On Ubuntu/Debian:"
        echo "    sudo apt-get install docker.io python3 python3-venv nodejs npm git"
        echo "    sudo usermod -aG docker \$USER   # then log out & back in"
        exit 1
    fi

    print_success "All prerequisites satisfied"
}

###############################################################################
# Environment Configuration
###############################################################################

setup_environment() {
    print_header "Setting Up Environment Variables"

    # Generate secure keys once (shared between root .env and backend/.env)
    SECRET_KEY=$(generate_secret_key)
    MASTER_ENCRYPTION_KEY=$(generate_fernet_key)

    # Root .env — used by Docker Compose for variable substitution (Plaid, Teller keys)
    if [ ! -f ".env" ]; then
        print_info "Creating .env file from template..."
        cp .env.example .env

        # Update .env with generated keys (use | delimiter — Fernet keys are URL-safe base64)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
            sed -i '' "s|MASTER_ENCRYPTION_KEY=.*|MASTER_ENCRYPTION_KEY=$MASTER_ENCRYPTION_KEY|" .env
        else
            sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
            sed -i "s|MASTER_ENCRYPTION_KEY=.*|MASTER_ENCRYPTION_KEY=$MASTER_ENCRYPTION_KEY|" .env
        fi

        print_success "Generated .env with secure keys"
    else
        print_warning ".env already exists - skipping generation"
        # Re-read existing keys so backend/.env gets the same values
        SECRET_KEY=$(grep '^SECRET_KEY=' .env | cut -d'=' -f2-)
        MASTER_ENCRYPTION_KEY=$(grep '^MASTER_ENCRYPTION_KEY=' .env | cut -d'=' -f2-)
    fi

    # Backend .env — used by local uvicorn/alembic (pydantic-settings reads from CWD)
    if [ ! -f "backend/.env" ] && [ -f "backend/.env.example" ]; then
        print_info "Creating backend/.env from template..."
        cp backend/.env.example backend/.env

        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" backend/.env
            sed -i '' "s|MASTER_ENCRYPTION_KEY=.*|MASTER_ENCRYPTION_KEY=$MASTER_ENCRYPTION_KEY|" backend/.env
        else
            sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" backend/.env
            sed -i "s|MASTER_ENCRYPTION_KEY=.*|MASTER_ENCRYPTION_KEY=$MASTER_ENCRYPTION_KEY|" backend/.env
        fi

        print_success "Generated backend/.env with secure keys"
    else
        print_warning "backend/.env already exists - skipping"
    fi

    # Frontend .env
    if [ ! -f "frontend/.env" ] && [ -f "frontend/.env.example" ]; then
        print_info "Creating frontend/.env..."
        cp frontend/.env.example frontend/.env
        print_success "Created frontend/.env"
    else
        print_warning "frontend/.env already exists - skipping"
    fi
}

###############################################################################
# Docker Services Setup (PostgreSQL + Redis via Docker Compose — no root)
###############################################################################

setup_docker() {
    if $SKIP_DOCKER; then
        print_warning "Skipping Docker setup (--skip-docker flag)"
        return
    fi

    if [ -z "$COMPOSE_CMD" ]; then
        print_error "Docker Compose not available - skipping Docker services"
        return 1
    fi

    print_header "Setting Up Docker Services (PostgreSQL, Redis)"

    # Check if services are already running
    if $COMPOSE_CMD -f docker-compose.dev.yml ps 2>/dev/null | grep -q "Up\|running"; then
        print_warning "Some services already running"
        if confirm "Stop and restart services?"; then
            print_info "Stopping existing services..."
            $COMPOSE_CMD -f docker-compose.dev.yml down
        else
            print_info "Keeping existing services running"
            return
        fi
    fi

    # Pull latest images
    print_info "Pulling Docker images..."
    $COMPOSE_CMD -f docker-compose.dev.yml pull postgres redis

    # Start only postgres and redis (no root needed — docker group handles it)
    print_info "Starting PostgreSQL and Redis containers..."
    $COMPOSE_CMD -f docker-compose.dev.yml up -d postgres redis

    print_success "Docker services started"

    # Wait for health checks
    print_info "Waiting for services to be healthy..."
    sleep 3

    local max_wait=60
    local waited=0
    while [ $waited -lt $max_wait ]; do
        local pg_healthy=false
        local redis_healthy=false
        local ps_output
        ps_output=$($COMPOSE_CMD -f docker-compose.dev.yml ps 2>/dev/null)
        echo "$ps_output" | grep -q "postgres.*healthy\|nestegg-dev-postgres.*healthy" && pg_healthy=true
        echo "$ps_output" | grep -q "redis.*healthy\|nestegg-dev-redis.*healthy" && redis_healthy=true

        if $pg_healthy && $redis_healthy; then
            print_success "PostgreSQL and Redis are healthy"
            return
        fi
        sleep 2
        waited=$((waited + 2))
        echo -n "."
    done
    echo ""

    if [ $waited -ge $max_wait ]; then
        print_warning "Services may not be fully ready - check with: $COMPOSE_CMD -f docker-compose.dev.yml ps"
    fi
}

###############################################################################
# Backend Setup
###############################################################################

setup_backend() {
    if $SKIP_BACKEND; then
        print_warning "Skipping backend setup (--skip-backend flag)"
        return
    fi

    print_header "Setting Up Backend (Python/FastAPI)"

    pushd backend > /dev/null

    # Create virtual environment
    if [ ! -d "venv" ]; then
        print_info "Creating Python virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_warning "Virtual environment already exists"
    fi

    # Activate virtual environment
    print_info "Activating virtual environment..."
    source venv/bin/activate

    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --quiet --upgrade pip

    # Install dependencies
    print_info "Installing Python dependencies (this may take a few minutes)..."
    pip install --quiet -r requirements.txt

    # Install development dependencies
    print_info "Installing development dependencies..."
    pip install --quiet pytest pytest-asyncio pytest-cov httpx ruff

    print_success "Backend dependencies installed"

    # Set up database schema (if Docker services are running)
    if ! $SKIP_DOCKER && [ -n "$COMPOSE_CMD" ]; then
        print_info "Setting up database schema..."
        # Try alembic upgrade first (works for existing DBs with migration history)
        if alembic upgrade head 2>&1; then
            print_success "Database migrations completed"
        else
            # Fresh DB: create all tables from models and stamp alembic to head
            print_info "Running fresh schema creation from models..."
            if python3 -c "
import asyncio
from app.core.database import engine, Base
from app.models import *  # noqa
async def create():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
asyncio.run(create())
" 2>&1; then
                alembic stamp head 2>&1
                print_success "Database schema created and stamped to head"
            else
                print_warning "Database setup failed - you can retry manually:"
                print_info "  cd backend && source venv/bin/activate && alembic upgrade head"
            fi
        fi
    else
        print_warning "Skipping database setup (no database services running)"
        print_info "Start services first, then run: cd backend && source venv/bin/activate && alembic upgrade head"
    fi

    popd > /dev/null
}

###############################################################################
# Frontend Setup
###############################################################################

setup_frontend() {
    if $SKIP_FRONTEND; then
        print_warning "Skipping frontend setup (--skip-frontend flag)"
        return
    fi

    print_header "Setting Up Frontend (React/TypeScript)"

    pushd frontend > /dev/null

    # Install dependencies
    print_info "Installing Node.js dependencies (this may take a few minutes)..."
    npm install

    print_success "Frontend dependencies installed"

    popd > /dev/null
}

###############################################################################
# Git Hooks Setup
###############################################################################

setup_git_hooks() {
    print_header "Setting Up Git Hooks"

    # Create .secrets.baseline if it doesn't exist
    if [ ! -f ".secrets.baseline" ]; then
        print_info "Creating .secrets.baseline for detect-secrets..."
        echo '{}' > .secrets.baseline
        print_success "Created .secrets.baseline"
    fi

    # Install pre-commit hooks (it was just installed via pip in setup_backend)
    if command_exists pre-commit; then
        print_info "Installing pre-commit hooks..."
        pre-commit install
        print_success "Pre-commit hooks installed"
    else
        print_warning "pre-commit not installed - run: pip install pre-commit && pre-commit install"
    fi
}

###############################################################################
# Seed Test Data
###############################################################################

seed_test_data() {
    if ! $SEED_USER && ! $SEED_USER2; then
        return
    fi

    print_header "Seeding Test Data"

    pushd backend > /dev/null
    source venv/bin/activate

    if $SEED_USER; then
        print_info "Creating test@test.com user with mock data..."

        python3 -c "
import asyncio, sys
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User, Organization
from sqlalchemy import select
from uuid import uuid4
from datetime import datetime

async def seed():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == 'test@test.com'))
        if result.scalar_one_or_none():
            print('  User test@test.com already exists')
            return

        org = Organization(id=uuid4(), name=\"Test Household\", created_at=datetime.utcnow())
        db.add(org)
        await db.flush()

        user = User(
            id=uuid4(), email='test@test.com',
            password_hash=hash_password('test1234'),
            first_name='Test', last_name='User',
            organization_id=org.id, is_org_admin=True,
            is_primary_household_member=True, is_active=True,
            created_at=datetime.utcnow(),
        )
        db.add(user)
        await db.commit()
        print('  Created test@test.com (password: test1234)')

asyncio.run(seed())
" 2>&1

        # Seed mock transaction data (|| true = don't abort on error)
        print_info "Seeding mock accounts and transactions..."
        python3 scripts/seed_mock_data.py 2>&1 || print_warning "seed_mock_data.py had issues (see above)"
        # Seed categories
        print_info "Seeding categories..."
        python3 scripts/seed_categories.py 2>&1 || print_warning "seed_categories.py had issues (see above)"
        # Seed investment holdings
        print_info "Seeding investment portfolio..."
        python3 scripts/create_comprehensive_test_data.py 2>&1 || print_warning "create_comprehensive_test_data.py had issues (see above)"
        print_success "test@test.com seeding complete"
    fi

    if $SEED_USER2; then
        print_info "Creating test2@test.com user with mock data..."
        python3 app/scripts/seed_multi_user_test_data.py 2>&1 || true
        if [ $? -eq 0 ]; then
            print_success "test2@test.com seeded with mock data"
        else
            print_warning "test2@test.com seeding had issues (see output above)"
        fi
    fi

    popd > /dev/null
}

###############################################################################
# Verification & Health Checks
###############################################################################

verify_setup() {
    print_header "Verifying Installation"

    local all_good=true

    # Check Docker services
    if ! $SKIP_DOCKER && [ -n "$COMPOSE_CMD" ]; then
        if $COMPOSE_CMD -f docker-compose.dev.yml ps 2>/dev/null | grep -q "postgres.*healthy"; then
            print_success "PostgreSQL is running (Docker)"
        else
            print_error "PostgreSQL is not healthy"
            all_good=false
        fi
        if $COMPOSE_CMD -f docker-compose.dev.yml ps 2>/dev/null | grep -q "redis.*healthy"; then
            print_success "Redis is running (Docker)"
        else
            print_error "Redis is not healthy"
            all_good=false
        fi
    fi

    # Check backend venv
    if ! $SKIP_BACKEND && [ -d "backend/venv" ]; then
        print_success "Backend virtual environment exists"
    elif ! $SKIP_BACKEND; then
        print_error "Backend virtual environment missing"
        all_good=false
    fi

    # Check frontend node_modules
    if ! $SKIP_FRONTEND && [ -d "frontend/node_modules" ]; then
        print_success "Frontend dependencies installed"
    elif ! $SKIP_FRONTEND; then
        print_error "Frontend node_modules missing"
        all_good=false
    fi

    # Check .env files
    if [ -f "backend/.env" ]; then
        print_success "Backend .env configured"
    else
        print_error "Backend .env missing (expected at backend/.env)"
        all_good=false
    fi

    if $all_good; then
        print_success "All checks passed!"
    else
        print_warning "Some checks failed - see errors above"
    fi
}

###############################################################################
# Post-Setup Instructions
###############################################################################

print_next_steps() {
    print_header "Setup Complete!"

    echo -e "${GREEN}Your Nest Egg development environment is ready!${NC}\n"

    echo -e "${BLUE}Start the app:${NC}"
    echo -e "   ${YELLOW}./scripts/dev-run.sh${NC}"
    echo ""

    if $SEED_USER || $SEED_USER2; then
        echo -e "${BLUE}Test Accounts:${NC}"
        if $SEED_USER; then
            echo -e "   ${GREEN}test@test.com${NC}  / test1234"
        fi
        if $SEED_USER2; then
            echo -e "   ${GREEN}test2@test.com${NC} / test1234"
        fi
        echo ""
    fi

    echo -e "${BLUE}Access Points:${NC}"
    echo -e "   Frontend:      ${GREEN}http://localhost:5173${NC}"
    echo -e "   Backend API:   ${GREEN}http://localhost:8000${NC}"
    echo -e "   API Docs:      ${GREEN}http://localhost:8000/docs${NC}"
    echo ""

    echo -e "${YELLOW}Optional:${NC} Configure bank account providers in ${YELLOW}backend/.env${NC}:"
    echo ""
    echo -e "   ${YELLOW}Plaid${NC} (11,000+ institutions, ~\$0.50-\$2/account/month):"
    echo "   PLAID_CLIENT_ID=your_client_id"
    echo "   PLAID_SECRET=your_secret"
    echo ""
    echo -e "   ${YELLOW}Teller${NC} (Recommended - 100 FREE accounts/month!):"
    echo "   TELLER_APP_ID=your_teller_app_id"
    echo "   TELLER_API_KEY=your_teller_api_key"
    echo ""
    echo -e "   ${GREEN}Sign up:${NC} Plaid: https://dashboard.plaid.com/signup"
    echo "            Teller: https://teller.io"
    echo ""

    echo -e "${GREEN}Happy coding!${NC}"
}

###############################################################################
# Main Execution
###############################################################################

main() {
    echo -e "${BLUE}"
    cat << "EOF"
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║               Nest Egg Development Setup                 ║
    ║          Personal Finance Tracking Application           ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"

    check_prerequisites
    setup_environment
    setup_docker
    setup_backend
    setup_frontend
    setup_git_hooks
    seed_test_data
    verify_setup
    print_next_steps
}

# Run main function
main
