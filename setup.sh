#!/bin/bash
###############################################################################
# Nest Egg - One-Shot Local Development Setup Script
#
# This script automates the complete setup of Nest Egg on a local machine.
# It handles all dependencies, services, and configuration in one command.
#
# Usage: ./setup.sh [options]
#
# Options:
#   --skip-docker      Skip Docker Compose services (use local Postgres/Redis)
#   --skip-frontend    Skip frontend setup
#   --skip-backend     Skip backend setup
#   --help             Show this help message
###############################################################################

set -e  # Exit on error

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
        --help)
            head -n 13 "$0" | tail -n 11
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

generate_secret_key() {
    if command_exists openssl; then
        openssl rand -hex 32
    else
        # Fallback to Python if openssl not available
        python3 -c "import secrets; print(secrets.token_hex(32))"
    fi
}

###############################################################################
# Prerequisite Checks
###############################################################################

check_prerequisites() {
    print_header "Checking Prerequisites"

    local missing_deps=()

    # Check Docker
    if ! $SKIP_DOCKER; then
        if ! command_exists docker; then
            missing_deps+=("Docker")
            print_warning "Docker not found - will not be able to run services"
        else
            print_success "Docker found: $(docker --version)"
        fi

        if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
            missing_deps+=("Docker Compose")
            print_warning "Docker Compose not found"
        else
            print_success "Docker Compose found"
        fi
    fi

    # Check Python
    if ! $SKIP_BACKEND; then
        if ! command_exists python3; then
            missing_deps+=("Python 3.11+")
            print_error "Python 3 not found"
        else
            PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
            print_success "Python found: $PYTHON_VERSION"
        fi
    fi

    # Check Node.js
    if ! $SKIP_FRONTEND; then
        if ! command_exists node; then
            missing_deps+=("Node.js 18+")
            print_error "Node.js not found"
        else
            NODE_VERSION=$(node --version)
            print_success "Node.js found: $NODE_VERSION"
        fi

        if ! command_exists npm; then
            missing_deps+=("npm")
            print_error "npm not found"
        else
            NPM_VERSION=$(npm --version)
            print_success "npm found: v$NPM_VERSION"
        fi
    fi

    # Check git
    if ! command_exists git; then
        missing_deps+=("git")
        print_error "git not found"
    else
        print_success "git found: $(git --version)"
    fi

    # Report missing dependencies
    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_error "Missing required dependencies: ${missing_deps[*]}"
        echo ""
        echo "Please install missing dependencies:"
        echo "  - Docker: https://docs.docker.com/get-docker/"
        echo "  - Python 3.11+: https://www.python.org/downloads/"
        echo "  - Node.js 18+: https://nodejs.org/"
        echo "  - Git: https://git-scm.com/downloads"
        exit 1
    fi

    print_success "All prerequisites satisfied"
}

###############################################################################
# Environment Configuration
###############################################################################

setup_environment() {
    print_header "Setting Up Environment Variables"

    # Backend .env
    if [ ! -f ".env" ]; then
        print_info "Creating .env file from template..."
        cp .env.example .env

        # Generate secure keys
        SECRET_KEY=$(generate_secret_key)
        MASTER_ENCRYPTION_KEY=$(generate_secret_key | cut -c1-32)  # Exactly 32 chars

        # Update .env with generated keys
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
            sed -i '' "s/MASTER_ENCRYPTION_KEY=.*/MASTER_ENCRYPTION_KEY=$MASTER_ENCRYPTION_KEY/" .env
        else
            # Linux
            sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
            sed -i "s/MASTER_ENCRYPTION_KEY=.*/MASTER_ENCRYPTION_KEY=$MASTER_ENCRYPTION_KEY/" .env
        fi

        print_success "Generated .env with secure keys"
    else
        print_warning ".env already exists - skipping generation"
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
# Docker Services Setup
###############################################################################

setup_docker() {
    if $SKIP_DOCKER; then
        print_warning "Skipping Docker setup (--skip-docker flag)"
        return
    fi

    print_header "Setting Up Docker Services"

    # Check if services are already running
    if docker compose ps | grep -q "Up"; then
        print_warning "Some services already running"
        read -p "Stop and restart services? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Stopping existing services..."
            docker compose down
        else
            print_info "Keeping existing services running"
            return
        fi
    fi

    # Pull latest images
    print_info "Pulling Docker images..."
    docker compose pull

    # Start services
    print_info "Starting Docker services (PostgreSQL, Redis, Celery, Flower)..."
    docker compose up -d db redis

    print_success "Docker services started"

    # Wait for health checks
    print_info "Waiting for services to be healthy..."
    sleep 5

    local max_wait=60
    local waited=0
    while [ $waited -lt $max_wait ]; do
        if docker compose ps | grep -q "healthy"; then
            print_success "Services are healthy"
            break
        fi
        sleep 2
        waited=$((waited + 2))
        echo -n "."
    done
    echo ""

    if [ $waited -ge $max_wait ]; then
        print_warning "Services may not be fully ready - check with: docker compose ps"
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

    cd backend

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
    pip install --quiet pytest pytest-asyncio pytest-cov httpx black isort flake8 pylint

    print_success "Backend dependencies installed"

    # Run database migrations
    print_info "Running database migrations..."
    if alembic upgrade head; then
        print_success "Database migrations completed"
    else
        print_error "Database migration failed - check connection settings"
        cd ..
        return 1
    fi

    cd ..
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

    cd frontend

    # Install dependencies
    print_info "Installing Node.js dependencies (this may take a few minutes)..."
    npm install

    print_success "Frontend dependencies installed"

    cd ..
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

    # Install pre-commit hooks
    if command_exists pre-commit; then
        print_info "Installing pre-commit hooks..."
        pre-commit install
        print_success "Pre-commit hooks installed"
    else
        print_warning "pre-commit not installed - run: pip install pre-commit"
        print_info "Then run: pre-commit install"
    fi
}

###############################################################################
# Verification & Health Checks
###############################################################################

verify_setup() {
    print_header "Verifying Installation"

    local all_good=true

    # Check Docker services
    if ! $SKIP_DOCKER; then
        if docker compose ps | grep -q "db.*healthy"; then
            print_success "PostgreSQL is running"
        else
            print_error "PostgreSQL is not healthy"
            all_good=false
        fi

        if docker compose ps | grep -q "redis.*healthy"; then
            print_success "Redis is running"
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
    if [ -f ".env" ]; then
        print_success "Backend .env configured"
    else
        print_error "Backend .env missing"
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
    print_header "Setup Complete! 🎉"

    echo -e "${GREEN}Your Nest Egg development environment is ready!${NC}\n"

    echo -e "${BLUE}Next Steps:${NC}\n"

    if ! $SKIP_DOCKER; then
        echo "1. Start backend API:"
        echo "   ${YELLOW}cd backend${NC}"
        echo "   ${YELLOW}source venv/bin/activate${NC}"
        echo "   ${YELLOW}uvicorn app.main:app --reload${NC}"
        echo ""

        echo "2. Start Celery worker (in new terminal):"
        echo "   ${YELLOW}cd backend${NC}"
        echo "   ${YELLOW}source venv/bin/activate${NC}"
        echo "   ${YELLOW}celery -A app.workers.celery_app worker --loglevel=info${NC}"
        echo ""

        echo "3. Start Celery beat scheduler (in new terminal):"
        echo "   ${YELLOW}cd backend${NC}"
        echo "   ${YELLOW}source venv/bin/activate${NC}"
        echo "   ${YELLOW}celery -A app.workers.celery_app beat --loglevel=info${NC}"
        echo ""
    fi

    if ! $SKIP_FRONTEND; then
        echo "4. Start frontend dev server (in new terminal):"
        echo "   ${YELLOW}cd frontend${NC}"
        echo "   ${YELLOW}npm run dev${NC}"
        echo ""
    fi

    echo -e "${BLUE}Or use the convenient Makefile commands:${NC}"
    echo "   ${YELLOW}make dev${NC}         # Start backend + frontend + celery"
    echo "   ${YELLOW}make test${NC}        # Run all tests"
    echo "   ${YELLOW}make lint${NC}        # Run all linters"
    echo ""

    echo -e "${BLUE}Access Points:${NC}"
    echo "   Frontend:      ${GREEN}http://localhost:5173${NC}"
    echo "   API Docs:      ${GREEN}http://localhost:8000/docs${NC}"
    echo "   Flower:        ${GREEN}http://localhost:5555${NC} (Celery monitoring)"
    echo ""

    echo -e "${BLUE}Useful Commands:${NC}"
    echo "   ${YELLOW}make help${NC}                  # Show all available commands"
    echo "   ${YELLOW}docker compose ps${NC}          # Check service status"
    echo "   ${YELLOW}docker compose logs -f${NC}     # View Docker logs"
    echo ""

    echo -e "${YELLOW}⚠ Important:${NC} Update your Plaid credentials in ${YELLOW}.env${NC}:"
    echo "   PLAID_CLIENT_ID=your_client_id"
    echo "   PLAID_SECRET=your_secret"
    echo ""

    echo -e "${GREEN}Happy coding! 🚀${NC}"
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
    verify_setup
    print_next_steps
}

# Run main function
main
