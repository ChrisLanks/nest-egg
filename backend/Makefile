.PHONY: help install test lint format clean coverage

help:
	@echo "Available commands:"
	@echo "  make install    - Install all dependencies"
	@echo "  make test       - Run all tests"
	@echo "  make test-unit  - Run only unit tests"
	@echo "  make test-api   - Run only API tests"
	@echo "  make lint       - Run all linters"
	@echo "  make format     - Format code with black and isort"
	@echo "  make coverage   - Run tests with coverage report"
	@echo "  make clean      - Remove cache and build files"
	@echo "  make pre-commit - Setup pre-commit hooks"

install:
	pip install -r requirements.txt
	pip install -e .

test:
	pytest -v

test-unit:
	pytest -v -m unit

test-api:
	pytest -v -m api

test-integration:
	pytest -v -m integration

lint:
	@echo "Running Black..."
	black --check app tests
	@echo "Running isort..."
	isort --check-only app tests
	@echo "Running Flake8..."
	flake8 app tests
	@echo "Running Pylint..."
	pylint app --max-line-length=100 --disable=all --enable=E,F || true

format:
	@echo "Formatting with Black..."
	black app tests
	@echo "Sorting imports with isort..."
	isort app tests
	@echo "Done!"

coverage:
	pytest --cov=app --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov/ .coverage coverage.xml

pre-commit:
	pre-commit install
	@echo "Pre-commit hooks installed!"

ci:
	@echo "Running CI checks locally..."
	make lint
	make test
	@echo "All CI checks passed!"
