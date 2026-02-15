# Nest Egg - Feature Implementation Plan

**Date:** February 15, 2026
**Scope:** Complete missing features for production-ready personal finance application

---

## IMPLEMENTATION STRATEGY

**Phase 1:** Backend Infrastructure (All Models, Services, APIs)
**Phase 2:** Frontend Integration (All UI Components, Pages, Hooks)
**Phase 3:** Testing & Integration

---

## FEATURE 1: ACCOUNT SYNC STATUS NOTIFICATIONS

### Status: 50% Complete (Backend in progress)

### Database Schema
```sql
-- notifications table (CREATED)
- id: UUID (PK)
- organization_id: UUID (FK)
- user_id: UUID (FK, nullable for org-wide)
- type: ENUM (sync_failed, reauth_required, sync_stale, account_error, budget_alert, etc.)
- priority: ENUM (low, medium, high, urgent)
- title: VARCHAR(255)
- message: TEXT
- related_entity_type: VARCHAR(50)
- related_entity_id: UUID
- is_read: BOOLEAN
- is_dismissed: BOOLEAN
- read_at: DATETIME
- dismissed_at: DATETIME
- action_url: VARCHAR(500)
- action_label: VARCHAR(100)
- created_at: DATETIME
- expires_at: DATETIME
```

### Backend Components

**Models:** ✅ DONE
- `backend/app/models/notification.py`

**Services:** ✅ DONE
- `backend/app/services/notification_service.py`
  - create_notification()
  - get_user_notifications()
  - mark_as_read()
  - mark_as_dismissed()
  - mark_all_as_read()
  - get_unread_count()
  - create_account_sync_notification()

**API Endpoints:** ⏳ TODO
- `backend/app/api/v1/notifications.py`
  - GET    /notifications          → List notifications
  - GET    /notifications/unread-count → Get count
  - PATCH  /notifications/{id}/read → Mark as read
  - PATCH  /notifications/{id}/dismiss → Dismiss
  - POST   /notifications/mark-all-read → Mark all read

**Webhook Handler:** ⏳ TODO
- `backend/app/api/webhooks.py`
  - POST /webhooks/plaid → Handle Plaid events
  - Verify signature
  - Handle: ITEM_LOGIN_REQUIRED, ERROR, SYNC_UPDATES_AVAILABLE

### Frontend Components

**Types:** ⏳ TODO
- `frontend/src/types/notification.ts`

**API:** ⏳ TODO
- `frontend/src/services/notificationApi.ts`

**Components:** ⏳ TODO
- `frontend/src/components/NotificationBell.tsx` → Header bell icon with badge
- `frontend/src/components/NotificationDropdown.tsx` → Dropdown list
- `frontend/src/components/AccountSyncBadge.tsx` → Status badge for accounts

**Hooks:** ⏳ TODO
- `frontend/src/hooks/useNotifications.ts`

**Integration Points:**
- Add NotificationBell to Layout header
- Add AccountSyncBadge to sidebar accounts
- Add reauth modal/flow when clicking reauth notification

---

## FEATURE 2: TRANSACTION SPLITTING

### Status: Not Started

### Database Schema
```sql
-- transaction_splits table (NEW)
- id: UUID (PK)
- parent_transaction_id: UUID (FK to transactions)
- organization_id: UUID (FK)
- amount: NUMERIC(15,2)
- description: TEXT
- category_id: UUID (FK to categories)
- created_at: DATETIME
- updated_at: DATETIME

-- Add to transactions table:
- is_split: BOOLEAN DEFAULT FALSE
```

### Backend Components

**Models:** ⏳ TODO
- Update `backend/app/models/transaction.py`
  - Add TransactionSplit class
  - Add splits relationship to Transaction
  - Add is_split column

**Schemas:** ⏳ TODO
- `backend/app/schemas/transaction.py`
  - TransactionSplitCreate
  - TransactionSplitResponse
  - TransactionWithSplitsResponse

**Services:** ⏳ TODO
- `backend/app/services/transaction_split_service.py`
  - split_transaction(transaction_id, splits[])
  - validate_split_amounts(splits[])
  - remove_splits(transaction_id)
  - get_transaction_with_splits(transaction_id)

**API Endpoints:** ⏳ TODO
- `backend/app/api/v1/transactions.py` (UPDATE)
  - POST   /transactions/{id}/split → Create splits
  - DELETE /transactions/{id}/splits → Remove splits
  - GET    /transactions/{id} → Include splits in response

**Migration:** ⏳ TODO
- `backend/alembic/versions/[hash]_add_transaction_splits.py`

### Frontend Components

**Types:** ⏳ TODO
- Update `frontend/src/types/transaction.ts`

**API:** ⏳ TODO
- Update `frontend/src/services/transactionApi.ts`

**Components:** ⏳ TODO
- `frontend/src/components/TransactionSplitModal.tsx` → Split UI
- `frontend/src/components/SplitBadge.tsx` → "Split" indicator
- `frontend/src/components/SplitDetails.tsx` → Expandable split view

**Integration Points:**
- Add "Split Transaction" button to transaction detail view
- Show split badge in transaction list
- Expand to show splits inline
- Budget calculations must use split amounts

---

## FEATURE 3: TRANSACTION MERGING

### Status: Not Started

### Database Schema
```sql
-- transaction_merges table (NEW)
- id: UUID (PK)
- organization_id: UUID (FK)
- primary_transaction_id: UUID (FK to transactions)
- merged_transaction_ids: UUID[] (ARRAY)
- merged_by_user_id: UUID (FK to users)
- merged_at: DATETIME
- merge_reason: TEXT
```

### Backend Components

**Models:** ⏳ TODO
- `backend/app/models/transaction_merge.py`

**Services:** ⏳ TODO
- `backend/app/services/transaction_merge_service.py`
  - merge_transactions(primary_id, duplicate_ids[])
  - find_potential_duplicates(org_id, timeframe)
  - undo_merge(merge_id)

**API Endpoints:** ⏳ TODO
- `backend/app/api/v1/transactions.py` (UPDATE)
  - POST /transactions/merge → Merge transactions
  - GET  /transactions/potential-duplicates → Find suggestions
  - POST /transactions/unmerge/{merge_id} → Undo merge

**Migration:** ⏳ TODO
- `backend/alembic/versions/[hash]_add_transaction_merges.py`

### Frontend Components

**Types:** ⏳ TODO
- `frontend/src/types/transaction.ts` (UPDATE)

**API:** ⏳ TODO
- Update `frontend/src/services/transactionApi.ts`

**Components:** ⏳ TODO
- `frontend/src/components/TransactionMergeModal.tsx` → Merge confirmation
- `frontend/src/components/PotentialDuplicates.tsx` → Suggestions panel
- `frontend/src/features/transactions/BulkMergeAction.tsx` → Bulk merge button

**Integration Points:**
- Add "Merge" button to bulk selection mode (already exists)
- Add "Review Duplicates" button to Transactions page
- Show merge history/audit trail

---

## FEATURE 4: BUDGETS (Largest Feature)

### Status: Not Started

### Database Schema
```sql
-- budgets table (NEW)
- id: UUID (PK)
- organization_id: UUID (FK)
- name: VARCHAR(255)
- amount: NUMERIC(15,2)
- period: ENUM (monthly, weekly, yearly, custom)
- start_date: DATE
- end_date: DATE (nullable)
- category_ids: UUID[] (ARRAY)
- label_ids: UUID[] (ARRAY)
- account_ids: UUID[] (ARRAY)
- user_id: UUID (FK, nullable for shared budgets)
- alert_percentage: INTEGER
- is_active: BOOLEAN
- created_at: DATETIME
- updated_at: DATETIME
```

### Backend Components

**Models:** ⏳ TODO
- `backend/app/models/budget.py`

**Schemas:** ⏳ TODO
- `backend/app/schemas/budget.py`
  - BudgetCreate
  - BudgetUpdate
  - BudgetResponse
  - BudgetWithUsage (includes spent, remaining, percentage)
  - BudgetSummary

**Services:** ⏳ TODO
- `backend/app/services/budget_service.py`
  - calculate_budget_usage(budget_id, start_date, end_date)
  - get_budget_status(budget_id)
  - check_budget_alerts(org_id) → Create notifications
  - get_all_budgets_summary(org_id, date_range)

**API Endpoints:** ⏳ TODO
- `backend/app/api/v1/budgets.py` (NEW)
  - POST   /budgets → Create budget
  - GET    /budgets → List all budgets
  - GET    /budgets/{id} → Get budget with usage
  - PATCH  /budgets/{id} → Update budget
  - DELETE /budgets/{id} → Delete budget
  - GET    /budgets/summary → Overview of all budgets

**Migration:** ⏳ TODO
- `backend/alembic/versions/[hash]_add_budgets.py`

### Frontend Components

**Types:** ⏳ TODO
- `frontend/src/types/budget.ts`

**API:** ⏳ TODO
- `frontend/src/services/budgetApi.ts`

**Pages:** ⏳ TODO
- `frontend/src/pages/BudgetsPage.tsx` → Main budgets view

**Components:** ⏳ TODO
- `frontend/src/features/budgets/components/BudgetCard.tsx` → Card with progress
- `frontend/src/features/budgets/components/BudgetForm.tsx` → Create/edit form
- `frontend/src/features/budgets/components/BudgetProgressBar.tsx` → Visual progress
- `frontend/src/features/budgets/components/BudgetAlertBanner.tsx` → Alert when approaching limit

**Hooks:** ⏳ TODO
- `frontend/src/hooks/useBudgets.ts`

**Integration Points:**
- Add "Budgets" to nav menu
- Show budget alerts on dashboard
- Link categories to budgets in Cash Flow page

---

## FEATURE 5: ENHANCED DEDUPLICATION

### Status: Partially Implemented (Needs Enhancement)

### Current State
- Hash-based deduplication exists
- Uses account_id + date + amount + merchant
- Unique constraint on (account_id, deduplication_hash)

### Enhancements Needed

**Backend:** ⏳ TODO
- `backend/app/utils/transaction_utils.py` (NEW)
  - normalize_merchant_name(merchant) → Robust normalization
  - generate_deduplication_hash(txn) → Two-tier system
  - find_matching_pending(txn) → Match pending transactions

**Services:** ⏳ TODO
- Update `backend/app/services/plaid_service.py`
  - Integrate two-tier deduplication
  - Use external_transaction_id first
  - Fall back to content hash
  - Match pending → posted transactions

**Two-Tier System:**
1. Priority 1: Use Plaid `transaction_id` if available
2. Priority 2: Enhanced content hash with normalized merchant

**Merchant Normalization:**
- Remove special characters
- Remove location indicators (#12345, Store #123)
- Remove common suffixes (LLC, INC, CO)
- Standardize spacing
- Convert to lowercase

---

## FEATURE 6: CSV TRANSACTION IMPORT

### Status: Not Started

### Backend Components

**Models:** ⏳ TODO
- No new models (uses existing Transaction)
- May add import_batch_id to transactions for tracking

**Services:** ⏳ TODO
- `backend/app/services/csv_import_service.py`
  - parse_csv(file, column_mapping)
  - validate_transactions(transactions[])
  - import_transactions(transactions[], org_id, dedup=True)
  - get_import_preview(file, mapping)

**API Endpoints:** ⏳ TODO
- `backend/app/api/v1/transactions.py` (UPDATE)
  - POST /transactions/import/preview → Parse CSV, return preview
  - POST /transactions/import → Import transactions
  - GET  /transactions/import-templates → Get CSV templates

### Frontend Components

**Components:** ⏳ TODO
- `frontend/src/components/CsvImportModal.tsx` → Import wizard
- `frontend/src/components/CsvColumnMapper.tsx` → Map CSV columns
- `frontend/src/components/CsvImportPreview.tsx` → Preview before import

**Import Wizard Steps:**
1. Upload CSV file
2. Map columns (Date, Amount, Merchant, Category)
3. Preview transactions
4. Select accounts to import to
5. Import with deduplication
6. Show results/errors

---

## FEATURE 7: RECURRING TRANSACTION DETECTION

### Status: Not Started

### Database Schema
```sql
-- recurring_transactions table (NEW)
- id: UUID (PK)
- organization_id: UUID (FK)
- merchant_name: VARCHAR(255)
- category_id: UUID (FK)
- average_amount: NUMERIC(15,2)
- frequency: ENUM (weekly, biweekly, monthly, quarterly, yearly)
- confidence_score: FLOAT (0-1)
- last_occurrence_date: DATE
- next_expected_date: DATE
- is_active: BOOLEAN
- is_confirmed: BOOLEAN (user confirmed)
- created_at: DATETIME
- updated_at: DATETIME
```

### Backend Components

**Models:** ⏳ TODO
- `backend/app/models/recurring_transaction.py`

**Services:** ⏳ TODO
- `backend/app/services/recurring_detection_service.py`
  - detect_recurring_patterns(org_id, lookback_months=6)
  - calculate_frequency(transactions[])
  - calculate_confidence(transactions[])
  - update_recurring_predictions()

**API Endpoints:** ⏳ TODO
- `backend/app/api/v1/recurring-transactions.py` (NEW)
  - GET    /recurring-transactions → List all recurring
  - POST   /recurring-transactions/detect → Trigger detection
  - PATCH  /recurring-transactions/{id}/confirm → User confirms
  - DELETE /recurring-transactions/{id} → Dismiss

### Frontend Components

**Pages:** ⏳ TODO
- `frontend/src/pages/RecurringTransactionsPage.tsx` → List view

**Components:** ⏳ TODO
- `frontend/src/components/RecurringCard.tsx` → Card for each recurring
- `frontend/src/components/RecurringPrediction.tsx` → Next expected date

---

## FEATURE 8: SAVINGS GOALS

### Status: Not Started

### Database Schema
```sql
-- savings_goals table (NEW)
- id: UUID (PK)
- organization_id: UUID (FK)
- user_id: UUID (FK, nullable)
- name: VARCHAR(255)
- target_amount: NUMERIC(15,2)
- current_amount: NUMERIC(15,2)
- target_date: DATE
- account_ids: UUID[] (ARRAY, accounts contributing)
- is_active: BOOLEAN
- color: VARCHAR(7) (hex color)
- icon: VARCHAR(50)
- created_at: DATETIME
- updated_at: DATETIME

-- goal_contributions table (NEW)
- id: UUID (PK)
- goal_id: UUID (FK)
- amount: NUMERIC(15,2)
- contribution_date: DATE
- notes: TEXT
- created_at: DATETIME
```

### Backend Components

**Models:** ⏳ TODO
- `backend/app/models/savings_goal.py`
- GoalContribution model

**Services:** ⏳ TODO
- `backend/app/services/savings_goal_service.py`
  - calculate_progress(goal_id)
  - calculate_required_monthly_contribution(goal_id)
  - add_contribution(goal_id, amount)
  - get_goals_summary(org_id)

**API Endpoints:** ⏳ TODO
- `backend/app/api/v1/goals.py` (NEW)
  - POST   /goals → Create goal
  - GET    /goals → List goals with progress
  - GET    /goals/{id} → Get goal details
  - PATCH  /goals/{id} → Update goal
  - DELETE /goals/{id} → Delete goal
  - POST   /goals/{id}/contribute → Add contribution

### Frontend Components

**Pages:** ⏳ TODO
- `frontend/src/pages/GoalsPage.tsx`

**Components:** ⏳ TODO
- `frontend/src/features/goals/components/GoalCard.tsx` → Progress visualization
- `frontend/src/features/goals/components/GoalForm.tsx` → Create/edit
- `frontend/src/features/goals/components/GoalChart.tsx` → Progress over time

---

## FEATURE 9: PLAID INTEGRATION FIX

### Status: Partially Implemented (Dummy Data for test@test.com)

### Current Issues
- Most Plaid methods return dummy data or NotImplementedError
- Transaction sync not actually calling Plaid API
- Balance updates not syncing
- Investment holdings returning fake data

### Required Changes

**Service Updates:** ⏳ TODO
- `backend/app/services/plaid_service.py`
  - Implement real Plaid API calls for non-test users
  - Keep dummy data for test@test.com (check user email)
  - sync_transactions(access_token, cursor)
  - sync_balances(access_token)
  - sync_investment_holdings(access_token)

**Conditional Logic:**
```python
async def sync_transactions(org_id, plaid_item_id):
    user = get_user_for_org(org_id)

    if user.email == "test@test.com":
        return get_dummy_transactions()
    else:
        # Real Plaid API call
        return plaid_client.transactions_sync(...)
```

**Real Plaid Integration:** ⏳ TODO
- Use actual Plaid Python SDK
- Implement cursor-based transaction sync
- Handle rate limits
- Store cursor for incremental sync
- Handle pending → posted updates

---

## IMPLEMENTATION ORDER

### Phase 1: Backend (Week 1-2)

**Priority 1: Core Infrastructure**
1. ✅ Notifications (Model, Service) - DONE
2. ⏳ Notifications API
3. ⏳ Webhook handler for Plaid events

**Priority 2: Transaction Features**
4. ⏳ Transaction Splitting (Model, Service, API)
5. ⏳ Transaction Merging (Model, Service, API)
6. ⏳ Enhanced Deduplication utilities

**Priority 3: Budget System**
7. ⏳ Budgets (Model, Service, API)

**Priority 4: Additional Features**
8. ⏳ CSV Import service
9. ⏳ Recurring Detection (Model, Service, API)
10. ⏳ Savings Goals (Model, Service, API)

**Priority 5: Plaid Fix**
11. ⏳ Real Plaid integration with test@test.com bypass

### Phase 2: Frontend (Week 3-4)

**Priority 1: Critical UI**
1. ⏳ Notification Bell + Dropdown
2. ⏳ Account Sync Status Badges
3. ⏳ Budget Page + Components

**Priority 2: Transaction Features**
4. ⏳ Transaction Split Modal
5. ⏳ Transaction Merge Modal
6. ⏳ CSV Import Wizard

**Priority 3: Additional Pages**
7. ⏳ Recurring Transactions Page
8. ⏳ Goals Page

### Phase 3: Integration & Testing (Week 5)
1. ⏳ End-to-end testing
2. ⏳ Bug fixes
3. ⏳ Performance optimization
4. ⏳ Documentation

---

## FILE STRUCTURE

### Backend Files to Create
```
backend/app/
├── models/
│   ├── notification.py ✅
│   ├── budget.py ⏳
│   ├── savings_goal.py ⏳
│   ├── recurring_transaction.py ⏳
│   └── transaction_merge.py ⏳
├── services/
│   ├── notification_service.py ✅
│   ├── budget_service.py ⏳
│   ├── transaction_split_service.py ⏳
│   ├── transaction_merge_service.py ⏳
│   ├── csv_import_service.py ⏳
│   ├── recurring_detection_service.py ⏳
│   └── savings_goal_service.py ⏳
├── api/v1/
│   ├── notifications.py ⏳
│   ├── budgets.py ⏳
│   ├── goals.py ⏳
│   ├── recurring_transactions.py ⏳
│   └── webhooks.py ⏳
├── utils/
│   └── transaction_utils.py ⏳
└── alembic/versions/
    ├── [hash]_add_notifications_table.py ✅
    ├── [hash]_add_transaction_splits.py ⏳
    ├── [hash]_add_transaction_merges.py ⏳
    ├── [hash]_add_budgets.py ⏳
    ├── [hash]_add_recurring_transactions.py ⏳
    └── [hash]_add_savings_goals.py ⏳
```

### Frontend Files to Create
```
frontend/src/
├── pages/
│   ├── BudgetsPage.tsx ⏳
│   ├── GoalsPage.tsx ⏳
│   └── RecurringTransactionsPage.tsx ⏳
├── features/
│   ├── notifications/
│   │   ├── components/NotificationBell.tsx ⏳
│   │   └── components/NotificationDropdown.tsx ⏳
│   ├── budgets/
│   │   ├── components/BudgetCard.tsx ⏳
│   │   ├── components/BudgetForm.tsx ⏳
│   │   └── components/BudgetProgressBar.tsx ⏳
│   ├── goals/
│   │   └── components/ ⏳
│   └── transactions/
│       ├── components/TransactionSplitModal.tsx ⏳
│       ├── components/TransactionMergeModal.tsx ⏳
│       └── components/CsvImportModal.tsx ⏳
├── services/
│   ├── notificationApi.ts ⏳
│   ├── budgetApi.ts ⏳
│   └── goalApi.ts ⏳
├── types/
│   ├── notification.ts ⏳
│   ├── budget.ts ⏳
│   └── goal.ts ⏳
└── hooks/
    ├── useNotifications.ts ⏳
    └── useBudgets.ts ⏳
```

---

## SUCCESS CRITERIA

### Feature Complete When:
- ✅ Database migration runs successfully
- ✅ All CRUD operations work
- ✅ API endpoints return correct data
- ✅ Frontend components render without errors
- ✅ User can complete full workflow
- ✅ Data persists correctly
- ✅ No console errors
- ✅ Responsive on mobile

### Application Complete When:
- ✅ All 9 features implemented
- ✅ test@test.com has dummy data
- ✅ Real users can connect Plaid accounts
- ✅ Transactions sync and deduplicate correctly
- ✅ Budgets track spending accurately
- ✅ Notifications alert for important events
- ✅ CSV import works for historical data
- ✅ No critical bugs

---

## ESTIMATED TIMELINE

**Backend Development:** 2-3 weeks (40-60 hours)
**Frontend Development:** 2-3 weeks (40-60 hours)
**Testing & Polish:** 1 week (10-20 hours)

**Total:** 5-7 weeks (90-140 hours)

---

## NOTES

- Keep dummy data for test@test.com across all features
- Maintain existing functionality while adding new features
- Follow existing code patterns and conventions
- Use TypeScript strict mode
- Add proper error handling
- Include loading states
- Mobile-first responsive design
- Accessible (WCAG AA)

---

**Document Version:** 1.0
**Last Updated:** February 15, 2026
