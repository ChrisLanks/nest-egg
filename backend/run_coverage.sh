#!/bin/bash

# Simple coverage runner script
cd "$(dirname "$0")"

# Try to find and use pytest
if command -v pytest &> /dev/null; then
    PYTEST_CMD="pytest"
elif [ -f ".venv/bin/pytest" ]; then
    PYTEST_CMD=".venv/bin/pytest"
elif [ -f "venv/bin/pytest" ]; then
    PYTEST_CMD="venv/bin/pytest"
else
    echo "pytest not found. Install with: pip install pytest pytest-cov pytest-asyncio"
    exit 1
fi

# Run coverage for specific files
echo "Running coverage for target files..."
$PYTEST_CMD tests/unit/ \
    --cov=app/api/v1/budgets \
    --cov=app/api/v1/labels \
    --cov=app/api/v1/rules \
    --cov=app/api/v1/household \
    --cov=app/api/v1/savings_goals \
    --cov=app/api/v1/holdings \
    --cov-report=term-missing \
    --cov-report=html \
    -v

echo ""
echo "Detailed HTML report available at: htmlcov/index.html"
