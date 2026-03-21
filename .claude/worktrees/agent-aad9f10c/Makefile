.PHONY: help install dev test lint format clean docker-up docker-down docker-logs

help:
	@echo "╔═══════════════════════════════════════════════════════════╗"
	@echo "║           Nest Egg - Development Commands                ║"
	@echo "╚═══════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install        - Run full setup (one-shot installation)"
	@echo "  make clean          - Clean all build artifacts and caches"
	@echo ""
	@echo "Development:"
	@echo "  make dev            - Start all services (backend + frontend + celery)"
	@echo "  make dev-backend    - Start backend API only"
	@echo "  make dev-frontend   - Start frontend only"
	@echo "  make dev-celery     - Start Celery worker + beat"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up      - Start Docker services (postgres, redis)"
	@echo "  make docker-down    - Stop Docker services"
	@echo "  make docker-logs    - View Docker service logs"
	@echo "  make docker-reset   - Reset Docker (remove volumes)"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run all tests (backend + frontend)"
	@echo "  make test-backend   - Run backend tests only"
	@echo "  make test-frontend  - Run frontend tests only"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           - Run all linters"
	@echo "  make lint-backend   - Run backend linters"
	@echo "  make lint-frontend  - Run frontend linters"
	@echo "  make format         - Format all code"
	@echo "  make format-backend - Format backend code"
	@echo "  make format-frontend- Format frontend code"
	@echo ""
	@echo "Database:"
	@echo "  make db-migrate     - Run database migrations"
	@echo "  make db-revision    - Create new migration"
	@echo "  make db-reset       - Reset database (⚠️  destroys data)"
	@echo "  make db-shell       - Open PostgreSQL shell"
	@echo ""
	@echo "Utilities:"
	@echo "  make health         - Check health of all services"
	@echo "  make logs           - Tail all logs"
	@echo "  make shell-backend  - Open backend Python shell"
	@echo "  make pre-commit     - Install git pre-commit hooks"
	@echo ""

###############################################################################
# Setup & Installation
###############################################################################

install:
	@echo "🚀 Running one-shot installation..."
	./scripts/dev-setup.sh

clean:
	@echo "🧹 Cleaning build artifacts..."
	cd backend && make clean
	cd frontend && rm -rf node_modules dist .vite
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✓ Cleaned!"

###############################################################################
# Development
###############################################################################

dev:
	@echo "🚀 Starting all development services..."
	./scripts/dev-run.sh

dev-backend:
	@echo "🚀 Starting backend API..."
	cd backend && source venv/bin/activate && uvicorn app.main:app --reload

dev-frontend:
	@echo "🚀 Starting frontend..."
	cd frontend && npm run dev

dev-celery:
	@echo "🚀 Starting Celery services..."
	@trap 'kill 0' SIGINT; \
	(cd backend && source venv/bin/activate && celery -A app.workers.celery_app worker --loglevel=info) & \
	(cd backend && source venv/bin/activate && celery -A app.workers.celery_app beat --loglevel=info) & \
	wait

###############################################################################
# Docker
###############################################################################

docker-up:
	@echo "🐳 Starting Docker services..."
	docker compose up -d db redis
	@echo "✓ PostgreSQL and Redis started"

docker-down:
	@echo "🐳 Stopping Docker services..."
	docker compose down
	@echo "✓ Services stopped"

docker-logs:
	docker compose logs -f

docker-reset:
	@echo "⚠️  Resetting Docker (this will delete all data)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose down -v; \
		docker compose up -d db redis; \
		sleep 5; \
		cd backend && source venv/bin/activate && alembic upgrade head; \
	fi

###############################################################################
# Testing
###############################################################################

test:
	@echo "🧪 Running all tests..."
	@$(MAKE) test-backend
	@$(MAKE) test-frontend

test-backend:
	@echo "🧪 Running backend tests..."
	cd backend && source venv/bin/activate && pytest -v

test-frontend:
	@echo "🧪 Running frontend tests..."
	cd frontend && npm test -- --run

test-coverage:
	@echo "🧪 Running tests with coverage..."
	cd backend && source venv/bin/activate && pytest --cov=app --cov-report=html --cov-report=term
	cd frontend && npm test -- --coverage --run
	@echo "📊 Backend coverage: backend/htmlcov/index.html"
	@echo "📊 Frontend coverage: frontend/coverage/index.html"

###############################################################################
# Code Quality
###############################################################################

lint:
	@echo "🔍 Running all linters..."
	@$(MAKE) lint-backend
	@$(MAKE) lint-frontend

lint-backend:
	@echo "🔍 Linting backend..."
	cd backend && make lint

lint-frontend:
	@echo "🔍 Linting frontend..."
	cd frontend && npm run lint

format:
	@echo "✨ Formatting all code..."
	@$(MAKE) format-backend
	@$(MAKE) format-frontend

format-backend:
	@echo "✨ Formatting backend..."
	cd backend && make format

format-frontend:
	@echo "✨ Formatting frontend..."
	cd frontend && npm run format || npx prettier --write 'src/**/*.{ts,tsx,js,jsx,json,css}'

###############################################################################
# Database
###############################################################################

db-migrate:
	@echo "📊 Running database migrations..."
	cd backend && source venv/bin/activate && alembic upgrade head

db-revision:
	@read -p "Enter migration message: " msg; \
	cd backend && source venv/bin/activate && alembic revision --autogenerate -m "$$msg"

db-reset:
	@echo "⚠️  Resetting database (this will delete all data)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose exec db psql -U nestegg -c "DROP DATABASE IF EXISTS nestegg;"; \
		docker compose exec db psql -U nestegg -c "CREATE DATABASE nestegg;"; \
		cd backend && source venv/bin/activate && alembic upgrade head; \
		echo "✓ Database reset complete"; \
	fi

db-shell:
	@echo "🐘 Opening PostgreSQL shell..."
	docker compose exec db psql -U nestegg nestegg

###############################################################################
# Utilities
###############################################################################

health:
	@echo "🏥 Checking service health..."
	@echo ""
	@echo "Docker Services:"
	@docker compose ps || echo "  ❌ Docker not running"
	@echo ""
	@echo "Backend API:"
	@curl -s http://localhost:8000/health > /dev/null && echo "  ✓ API responding" || echo "  ❌ API not responding"
	@echo ""
	@echo "Frontend:"
	@curl -s http://localhost:5173 > /dev/null && echo "  ✓ Frontend responding" || echo "  ❌ Frontend not responding"
	@echo ""
	@echo "Flower:"
	@curl -s http://localhost:5555 > /dev/null && echo "  ✓ Flower responding" || echo "  ❌ Flower not responding"

logs:
	@trap 'kill 0' SIGINT; \
	docker compose logs -f & \
	tail -f backend/logs/*.log 2>/dev/null & \
	wait || true

shell-backend:
	@echo "🐍 Opening backend Python shell..."
	cd backend && source venv/bin/activate && python

pre-commit:
	@echo "🪝 Installing pre-commit hooks..."
	pre-commit install
	@echo "✓ Pre-commit hooks installed"
	@echo ""
	@echo "Run 'pre-commit run --all-files' to check all files"

###############################################################################
# CI Emulation
###############################################################################

ci:
	@echo "🔄 Running CI checks locally..."
	@echo ""
	@$(MAKE) lint
	@$(MAKE) test
	@echo ""
	@echo "✓ All CI checks passed!"
