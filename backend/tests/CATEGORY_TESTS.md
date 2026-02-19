# Category Testing Documentation

This document describes the comprehensive test suite for the category grouping and hierarchical drill-down functionality.

## Overview

The category feature supports:
1. **Hierarchical Categories**: Parent-child relationships (max 2 levels)
2. **Category Grouping**: Automatic grouping of child categories under parents in summaries
3. **Category Drill-Down**: Navigate from parent → children → merchants → transactions
4. **Provider Category Mapping**: Map Plaid/Teller categories to custom categories
5. **Multiple Grouping Modes**: Group by category, label, merchant, or account

## Test Files

### Unit Tests

#### `tests/unit/test_categories_api.py`
Tests for basic category CRUD operations:
- ✅ List categories (custom + provider)
- ✅ Create category with/without parent
- ✅ Update category (including parent changes)
- ✅ Delete category
- ✅ Validation (self-parent, max depth, etc.)

**Key Test Cases:**
- `test_lists_custom_categories` - Lists categories from categories table
- `test_lists_plaid_categories_from_transactions` - Lists provider categories
- `test_combines_custom_and_plaid_categories` - Deduplication logic
- `test_prevents_self_as_parent` - Validation: can't be own parent
- `test_prevents_parent_when_has_children` - Validation: max 2 levels

#### `tests/unit/test_income_expenses_category_grouping.py`
Tests for hierarchical category grouping logic:
- ✅ Groups child categories under parent in summary
- ✅ Shows parent for provider categories with custom mapping
- ✅ Shows root categories without parents as-is
- ✅ Calculates percentages correctly
- ✅ Handles zero total gracefully (no division errors)
- ✅ Drill-down shows children for parent categories
- ✅ Drill-down shows merchants for leaf categories
- ✅ Handles provider categories without custom mappings

**Key Test Cases:**
- `test_groups_child_categories_under_parent` - Core grouping logic
- `test_shows_parent_category_for_provider_categories` - Provider category mapping
- `test_calculates_percentages_correctly` - Percentage math
- `test_handles_zero_total_gracefully` - Division by zero protection
- `test_returns_child_categories_for_parent` - Drill-down to children
- `test_returns_merchants_for_leaf_category` - Drill-down to merchants

### Integration Tests

#### `tests/api/test_categories_endpoints.py`
API endpoint tests for category management:
- ✅ Create category (success/validation)
- ✅ Create with parent (hierarchy)
- ✅ Update category
- ✅ Delete category
- ✅ Input validation (XSS, length, format)

**Key Test Cases:**
- `test_create_category_success` - Happy path
- `test_create_category_with_parent` - Parent-child creation
- `test_create_category_xss_attempt_fails` - Security validation
- `test_create_category_invalid_color_fails` - Format validation

#### `tests/api/test_income_expenses_category_grouping.py`
End-to-end tests for category grouping in income-expenses:
- ✅ Groups child categories under parent (income & expenses)
- ✅ Drill-down shows child categories for parents
- ✅ Drill-down shows merchants for leaf categories
- ✅ Provider category mapping to parent
- ✅ Correct percentage calculations with hierarchy
- ✅ Excludes transfers from summaries
- ✅ Group by label mode
- ✅ Group by merchant mode

**Key Test Cases:**
- `test_groups_child_categories_under_parent_income` - E2E income grouping
- `test_groups_child_categories_under_parent_expenses` - E2E expense grouping
- `test_drill_down_shows_child_categories` - E2E drill-down to children
- `test_drill_down_shows_merchants_for_leaf_category` - E2E drill-down to merchants
- `test_provider_category_with_custom_mapping_groups_under_parent` - Provider mapping
- `test_excludes_transfers_from_category_summary` - Transfer exclusion

## Running Tests

### Run All Category Tests
```bash
./tests/run_category_tests.sh
```

### Run Specific Test Files
```bash
# Unit tests only
pytest tests/unit/test_categories_api.py -v
pytest tests/unit/test_income_expenses_category_grouping.py -v

# Integration tests only
pytest tests/api/test_categories_endpoints.py -v
pytest tests/api/test_income_expenses_category_grouping.py -v
```

### Run Specific Test Classes
```bash
pytest tests/unit/test_income_expenses_category_grouping.py::TestCategoryHierarchicalGrouping -v
pytest tests/api/test_income_expenses_category_grouping.py::TestIncomeExpenseCategoryGrouping -v
```

### Run Specific Test Methods
```bash
pytest tests/unit/test_income_expenses_category_grouping.py::TestCategoryHierarchicalGrouping::test_groups_child_categories_under_parent -v
```

### Run with Coverage
```bash
pytest tests/unit/test_categories_api.py --cov=app.api.v1.categories --cov-report=html
pytest tests/unit/test_income_expenses_category_grouping.py --cov=app.api.v1.income_expenses --cov-report=html
```

## Test Coverage

### Backend API Endpoints Covered

1. **`GET /api/v1/categories`**
   - Lists all categories (custom + provider)
   - Deduplicates provider categories
   - Sorts alphabetically

2. **`POST /api/v1/categories`**
   - Creates custom category
   - Validates parent hierarchy
   - Prevents > 2 levels

3. **`PATCH /api/v1/categories/{id}`**
   - Updates category fields
   - Validates parent changes
   - Prevents self-parent

4. **`DELETE /api/v1/categories/{id}`**
   - Deletes category
   - Cascade deletes via DB constraint

5. **`GET /api/v1/income-expenses/summary`**
   - Groups transactions by category
   - Shows parent for child categories
   - Maps provider categories to custom
   - Supports `group_by` parameter

6. **`GET /api/v1/income-expenses/category-drill-down`**
   - Drills into parent → shows children
   - Drills into leaf → shows merchants
   - Handles provider categories

### Frontend Components Covered

The test suite focuses on backend logic. For frontend testing:

**Components to Test:**
- `IncomeExpensesPage.tsx` - Category grouping UI
- Category drill-down navigation
- Empty state handling
- localStorage persistence for groupBy

**Recommended Frontend Tests:**
```typescript
// Example with React Testing Library
describe('IncomeExpensesPage', () => {
  test('groups child categories under parent', () => {
    // Mock API response with hierarchical data
    // Verify parent category appears, children don't
  });

  test('persists groupBy selection in localStorage', () => {
    // Change groupBy mode
    // Verify localStorage.setItem called
    // Reload page
    // Verify groupBy restored
  });

  test('shows empty state when no data', () => {
    // Mock empty API response
    // Verify empty state card with icon displayed
  });
});
```

## Test Data Setup

### Example Hierarchy
```
Food (parent)
  ├── Restaurants (child)
  └── Groceries (child)

Transportation (parent)
  ├── Gas (child)
  └── Public Transit (child)
```

### Sample Transactions
```python
# Transaction with custom category (child)
{
  "amount": -50.00,
  "category_id": restaurants_id,  # Child category
  # Should be grouped under "Food" parent
}

# Transaction with provider category
{
  "amount": -30.00,
  "category_primary": "Food and Drink",  # Plaid category
  # If mapped to "Restaurants" → grouped under "Food"
}
```

## Key Edge Cases Tested

1. **Empty Data**: Zero income/expenses doesn't cause division errors
2. **No Mapping**: Provider categories without custom mappings show as-is
3. **Transfers**: Transfer transactions excluded from category summaries
4. **Circular References**: Prevented by validation (can't be own parent)
5. **Max Depth**: Enforced at 2 levels (parent → child only)
6. **Deduplication**: Custom categories override provider categories with same name
7. **Percentages**: Calculated correctly across hierarchy levels

## Common Test Patterns

### Setting Up Hierarchy
```python
# Create parent
food_response = client.post("/api/v1/categories", json={"name": "Food"})
food_id = food_response.json()["id"]

# Create child
restaurants_response = client.post(
    "/api/v1/categories",
    json={"name": "Restaurants", "parent_category_id": food_id}
)
```

### Verifying Grouping
```python
# Get summary
summary = client.get("/api/v1/income-expenses/summary").json()

# Verify parent shown, not children
assert "Food" in [cat["category"] for cat in summary["expense_categories"]]
assert "Restaurants" not in [cat["category"] for cat in summary["expense_categories"]]
```

### Testing Drill-Down
```python
# Drill into parent
drill_down = client.get(
    "/api/v1/income-expenses/category-drill-down",
    params={"category": "Food"}
).json()

# Verify children shown
assert "Restaurants" in [cat["category"] for cat in drill_down["expense_categories"]]
assert "Groceries" in [cat["category"] for cat in drill_down["expense_categories"]]
```

## Continuous Integration

Add to CI pipeline (`.github/workflows/test.yml`):
```yaml
- name: Run category tests
  run: |
    pytest tests/unit/test_categories_api.py -v
    pytest tests/unit/test_income_expenses_category_grouping.py -v
    pytest tests/api/test_categories_endpoints.py -v
    pytest tests/api/test_income_expenses_category_grouping.py -v
```

## Future Test Additions

### Phase 2 (Smart Analytics)
- Budget alert tests with categories
- Subscription detection with categories
- Cash flow forecast with category-based projections

### Phase 3 (Advanced Analytics)
- Tax-deductible tagging with categories
- Custom reports filtered by category
- Multi-year trend analysis by category

## Debugging Failed Tests

### Common Issues

1. **Database State**: Integration tests require clean database
   ```bash
   # Reset test database
   pytest --create-db
   ```

2. **Async Mock Setup**: Ensure `AsyncMock` used for async functions
   ```python
   mock_db.execute.side_effect = [...]  # Multiple calls
   ```

3. **Test Isolation**: Each test should be independent
   ```python
   @pytest.fixture(autouse=True)
   def cleanup(db_session):
       yield
       # Clean up test data
   ```

## Contact

For questions about category tests:
- Backend logic: Review `app/api/v1/income_expenses.py`
- Frontend UI: Review `frontend/src/features/income-expenses/pages/IncomeExpensesPage.tsx`
- Database schema: Review `backend/alembic/versions/*_add_categories_and_update_transactions.py`
