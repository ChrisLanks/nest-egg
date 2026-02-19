#!/bin/bash
# Run all category-related tests

set -e

echo "=========================================="
echo "Running Category Tests"
echo "=========================================="
echo ""

# Change to backend directory
cd "$(dirname "$0")/.."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "1. Running unit tests for categories API..."
pytest tests/unit/test_categories_api.py -v

echo ""
echo "2. Running unit tests for income-expenses category grouping..."
pytest tests/unit/test_income_expenses_category_grouping.py -v

echo ""
echo "3. Running integration tests for category endpoints..."
pytest tests/api/test_categories_endpoints.py -v

echo ""
echo "4. Running integration tests for income-expenses category grouping..."
pytest tests/api/test_income_expenses_category_grouping.py -v

echo ""
echo "=========================================="
echo "All category tests completed!"
echo "=========================================="
