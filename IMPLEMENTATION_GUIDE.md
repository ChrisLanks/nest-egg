# Nest Egg - Production Readiness Implementation Guide

## ✅ **COMPLETED**

### 1. Shift-Click Multi-Select on Transactions ✅
- Hold Shift and click to select ranges
- Works on both desktop and mobile views
- Tooltip added for discoverability

### 2. JWT Token Auto-Refresh Fixed ✅
- Datetime import added to user.py
- Tokens refresh 5 minutes before expiration
- Automatic retry on 401 errors

### 3. Debt Payoff Improvements ✅
- Clickable strategy cards with detailed modals
- Account selection with localStorage persistence
- Manual debt editing (interest rate, minimum payment)
- All debt types supported (credit cards, loans, mortgages)

### 4. Trends Page Fixed ✅
- Array serialization fixed for FastAPI
- Year-over-year comparisons working
- Quarterly summaries displaying correctly

### 5. Debug Endpoints Protected ✅
- Already checks for DEBUG mode
- Returns 404 in production

### 6. Database Indexes Created ✅
- Migration file: `alembic/versions/1e002a673565_add_performance_indexes.py`
- **Run migration**: `cd backend && source venv/bin/activate && alembic upgrade head`
- Indexes cover:
  - Transactions (org_id + date, amount, merchant, category)
  - Labels (transaction_id, label_id)
  - Budgets (org_id + is_active)
  - Accounts (org_id + type + is_active)
  - Categories (org_id + name)

---

## 🚧 **IN PROGRESS / TODO**

### Priority 1: Loading Skeletons (2 hours)

**File to create**: `/frontend/src/components/LoadingSkeleton.tsx`

```typescript
import { Box, Skeleton, Stack, Card, CardBody, SimpleGrid } from '@chakra-ui/react';

export const DashboardSkeleton = () => (
  <Stack spacing={6}>
    <SimpleGrid columns={{ base: 1, md: 4 }} spacing={6}>
      {[1, 2, 3, 4].map((i) => (
        <Card key={i}>
          <CardBody>
            <Skeleton height="20px" mb={2} />
            <Skeleton height="40px" />
          </CardBody>
        </Card>
      ))}
    </SimpleGrid>
    <Card>
      <CardBody>
        <Skeleton height="300px" />
      </CardBody>
    </Card>
  </Stack>
);

export const TransactionsSkeleton = () => (
  <Stack spacing={4}>
    {[1, 2, 3, 4, 5].map((i) => (
      <Skeleton key={i} height="60px" borderRadius="md" />
    ))}
  </Stack>
);

export const TableSkeleton = ({ rows = 5, columns = 6 }) => (
  <Stack spacing={2}>
    <Skeleton height="40px" /> {/* Header */}
    {Array.from({ length: rows }).map((_, i) => (
      <Skeleton key={i} height="50px" />
    ))}
  </Stack>
);
```

**Usage in pages**:
```typescript
// DashboardPage.tsx
if (isLoading) {
  return <DashboardSkeleton />;
}

// TransactionsPage.tsx
if (isLoading) {
  return <TransactionsSkeleton />;
}
```

**Pages to update**:
- `/frontend/src/pages/DashboardPage.tsx`
- `/frontend/src/pages/TransactionsPage.tsx`
- `/frontend/src/pages/IncomeExpensesPage.tsx`
- `/frontend/src/pages/BudgetsPage.tsx`
- `/frontend/src/pages/AccountsPage.tsx`

---

### Priority 2: Empty States with CTAs (3 hours)

**File to create**: `/frontend/src/components/EmptyState.tsx`

```typescript
import { Box, VStack, Heading, Text, Button, Icon } from '@chakra-ui/react';

interface EmptyStateProps {
  icon?: React.ReactElement;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  actionLabel,
  onAction,
}) => (
  <Box textAlign="center" py={12} px={6}>
    <VStack spacing={4}>
      {icon && (
        <Box fontSize="4xl" color="gray.400">
          {icon}
        </Box>
      )}
      <Heading size="md" color="gray.700">
        {title}
      </Heading>
      <Text color="gray.600" maxW="md">
        {description}
      </Text>
      {actionLabel && onAction && (
        <Button colorScheme="blue" onClick={onAction} mt={4}>
          {actionLabel}
        </Button>
      )}
    </VStack>
  </Box>
);
```

**Usage examples**:

```typescript
// TransactionsPage.tsx
{transactions.length === 0 && !isLoading && (
  <EmptyState
    icon={<Text>💳</Text>}
    title="No transactions yet"
    description="Connect your first account to start tracking transactions automatically, or add them manually."
    actionLabel="Connect Account"
    onAction={() => navigate('/accounts')}
  />
)}

// BudgetsPage.tsx
{budgets.length === 0 && !isLoading && (
  <EmptyState
    icon={<Text>🎯</Text>}
    title="No budgets created"
    description="Create your first budget to start tracking spending and get alerts when you're approaching limits."
    actionLabel="Create Budget"
    onAction={() => setIsCreateModalOpen(true)}
  />
)}
```

---

### Priority 3: Transaction CSV Export (1 hour)

**Already partially exists** - just needs export button.

**File to update**: `/frontend/src/pages/TransactionsPage.tsx`

Add export function:
```typescript
const exportToCSV = () => {
  const headers = ['Date', 'Merchant', 'Amount', 'Category', 'Account', 'Labels'];
  const rows = processedTransactions.map(txn => [
    txn.date,
    txn.merchant_name,
    txn.amount,
    txn.category_primary || '',
    txn.account_name || '',
    txn.labels?.map(l => l.name).join('; ') || ''
  ]);

  const csv = [
    headers.join(','),
    ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
  ].join('\n');

  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `transactions-${dateRange.start}-${dateRange.end}.csv`;
  a.click();
  URL.revokeObjectURL(url);
};
```

Add button near existing filters:
```typescript
<Button
  leftIcon={<DownloadIcon />}
  variant="outline"
  onClick={exportToCSV}
>
  Export CSV
</Button>
```

---

### Priority 4: Budget Progress Bars (1 hour)

**File to update**: `/frontend/src/pages/BudgetsPage.tsx`

Add to each budget card:
```typescript
import { Progress } from '@chakra-ui/react';

const percentUsed = (spent / budget.amount) * 100;
const colorScheme = percentUsed >= 100 ? 'red' : percentUsed >= 80 ? 'yellow' : 'green';

<Progress
  value={percentUsed}
  colorScheme={colorScheme}
  size="sm"
  borderRadius="full"
  mb={2}
/>
<Text fontSize="xs" color="gray.600">
  {formatCurrency(spent)} of {formatCurrency(budget.amount)} ({percentUsed.toFixed(0)}%)
</Text>
```

---

### Priority 5: CSV Import Functionality (8 hours - COMPLEX)

**Backend**: Create new endpoint `/api/v1/transactions/import`

**File to create**: `/backend/app/api/v1/transaction_import.py`

```python
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import csv
import io
from datetime import datetime
from decimal import Decimal

router = APIRouter()

@router.post("/import")
async def import_transactions(
    file: UploadFile = File(...),
    account_id: UUID = None,  # Optional - for assigning to account
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Import transactions from CSV.

    Expected format:
    Date,Merchant,Amount,Category,Description
    2024-01-15,Starbucks,-4.50,Food & Dining,Coffee

    Or Mint format:
    Date,Description,Original Description,Amount,Transaction Type,Category,Account Name,Labels,Notes
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(400, "File must be CSV")

    content = await file.read()
    csv_file = io.StringIO(content.decode('utf-8'))
    reader = csv.DictReader(csv_file)

    # Detect format (standard vs Mint)
    fieldnames = reader.fieldnames
    is_mint_format = 'Original Description' in fieldnames

    transactions = []
    errors = []

    for i, row in enumerate(reader):
        try:
            if is_mint_format:
                txn_data = parse_mint_format(row)
            else:
                txn_data = parse_standard_format(row)

            # Validate and create transaction
            # Check for duplicates
            # Add to batch
            transactions.append(txn_data)

        except Exception as e:
            errors.append({'row': i + 2, 'error': str(e), 'data': row})

    # Bulk insert transactions
    # Return summary with errors for review

    return {
        'imported': len(transactions),
        'errors': errors,
        'needs_review': [...]  # Questionable transactions
    }
```

**Frontend**: Create import modal with drag-drop

**File to create**: `/frontend/src/components/TransactionImportModal.tsx`

```typescript
import { Modal, ModalOverlay, ModalContent, useToast } from '@chakra-ui/react';
import { useDropzone } from 'react-dropzone';

export const TransactionImportModal = ({ isOpen, onClose }) => {
  const toast = useToast();

  const { getRootProps, getInputProps } = useDropzone({
    accept: { 'text/csv': ['.csv'] },
    onDrop: async (files) => {
      const formData = new FormData();
      formData.append('file', files[0]);

      const response = await api.post('/transactions/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      toast({
        title: `Imported ${response.data.imported} transactions`,
        status: 'success'
      });

      if (response.data.errors.length > 0) {
        // Show error review modal
      }
    }
  });

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      {/* Dropzone UI */}
    </Modal>
  );
};
```

---

### Priority 6: Bug Fixes

**Bug 1: Date Range Picker Doesn't Update Chart**
File: `/frontend/src/pages/DashboardPage.tsx`

Add refetch on date change:
```typescript
useEffect(() => {
  refetch();  // Add refetch from useQuery
}, [dateRange]);
```

**Bug 2: Bulk Edit Loses Selection**
File: `/frontend/src/pages/TransactionsPage.tsx`

Remove selection clear:
```typescript
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['transactions'] });
  // Don't clear: setSelectedTransactions(new Set());
}
```

**Bug 3: Mobile Menu Doesn't Close**
File: `/frontend/src/components/Layout.tsx`

Add onClose to nav links:
```typescript
<Link to="/dashboard" onClick={onClose}>Dashboard</Link>
```

---

### Priority 7: Security Fixes (CRITICAL)

**Fix 1: Remove unsafe-eval from CSP**
File: `/backend/app/middleware/security_headers.py`

Change line 18:
```python
# Before:
"script-src 'self' 'unsafe-inline' 'unsafe-eval'; "

# After (production):
"script-src 'self' 'nonce-{NONCE}'; "

# Use environment variable to switch:
if settings.DEBUG:
    script_src = "'self' 'unsafe-inline' 'unsafe-eval'"
else:
    script_src = "'self' 'nonce-{NONCE}'"
```

**Fix 2: Move Refresh Tokens to HttpOnly Cookies** (8 hours - requires backend + frontend changes)

This is complex and should be a separate task. Document the approach:
1. Backend: Set refresh token as httpOnly cookie
2. Frontend: Access token in memory only
3. Update all token refresh logic

---

### Priority 8: Logging & Monitoring (4 hours)

**Add Sentry for Frontend Errors**

File: `/frontend/src/main.tsx`

```typescript
import * as Sentry from "@sentry/react";

if (import.meta.env.PROD) {
  Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN,
    integrations: [
      new Sentry.BrowserTracing(),
      new Sentry.Replay(),
    ],
    tracesSampleRate: 0.1,
    replaysSessionSampleRate: 0.1,
  });
}
```

**Add Request Logging Middleware**

File to create: `/backend/app/middleware/logging_middleware.py`

```python
import time
import logging
from fastapi import Request

logger = logging.getLogger(__name__)

async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    logger.info(
        f"{request.method} {request.url.path} "
        f"status={response.status_code} duration={duration:.3f}s"
    )

    if duration > 1.0:  # Log slow queries
        logger.warning(f"Slow request: {request.url.path} took {duration:.3f}s")

    return response
```

Add to `main.py`:
```python
from app.middleware.logging_middleware import log_requests
app.middleware("http")(log_requests)
```

---

### Priority 9: Performance Optimizations (6 hours)

**1. React.lazy for Route Splitting**

File: `/frontend/src/App.tsx`

```typescript
import { lazy, Suspense } from 'react';

const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const TransactionsPage = lazy(() => import('./pages/TransactionsPage'));
// ... other pages

<Suspense fallback={<DashboardSkeleton />}>
  <Route path="/dashboard" element={<DashboardPage />} />
</Suspense>
```

**2. Redis Caching for Dashboard**

File: `/backend/app/services/cache_service.py`

```python
import json
from typing import Optional
import redis

class CacheService:
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

    def get(self, key: str) -> Optional[dict]:
        data = self.redis.get(key)
        return json.loads(data) if data else None

    def set(self, key: str, value: dict, ttl: int = 300):  # 5 min default
        self.redis.setex(key, ttl, json.dumps(value))

    def invalidate(self, pattern: str):
        for key in self.redis.scan_iter(pattern):
            self.redis.delete(key)
```

Usage:
```python
cache_key = f"dashboard:{user.organization_id}:{date_range}"
cached = cache_service.get(cache_key)
if cached:
    return cached

# ... fetch from DB ...
cache_service.set(cache_key, data)
```

**3. React.memo for Expensive Components**

```typescript
export const TransactionRow = React.memo(({ transaction, onSelect }) => {
  // ... render logic
}, (prev, next) => {
  // Custom comparison
  return prev.transaction.id === next.transaction.id &&
         prev.isSelected === next.isSelected;
});
```

---

## 📊 **CHARTS TO REVIEW**

### Net Worth Tracker
**Status**: Exists on Overview page
**Action**: Consider adding to Dashboard as well
**Location**: `/frontend/src/pages/OverviewPage.tsx`

### Spending by Day of Week
**Status**: Doesn't exist
**Action**: Add to Cash Flow page
**File**: `/frontend/src/pages/IncomeExpensesPage.tsx`

```typescript
// Add heatmap using recharts
const dayOfWeekData = transactions.reduce((acc, txn) => {
  const day = new Date(txn.date).getDay();
  acc[day] = (acc[day] || 0) + Math.abs(txn.amount);
  return acc;
}, {});
```

### Category Pie Chart
**Status**: Exists as bar chart
**Action**: Add pie chart option
**File**: `/frontend/src/pages/DashboardPage.tsx`

### Budget vs Actual
**Status**: Needs improvement
**Action**: Add side-by-side comparison chart
**File**: `/frontend/src/pages/BudgetsPage.tsx`

### Income vs Expenses on Dashboard
**Status**: Exists in Cash Flow
**Action**: Add smaller version to Dashboard
**File**: Copy from IncomeExpensesPage to DashboardPage

---

## 🎯 **NEXT STEPS - RECOMMENDED ORDER**

1. **Run database migration** (1 min)
2. **Add loading skeletons** (2 hours) - Immediate UX improvement
3. **Add empty states** (3 hours) - Better first-time experience
4. **Add CSV export** (1 hour) - Quick win
5. **Add budget progress bars** (1 hour) - Visual improvement
6. **Fix bugs** (2 hours) - Quality improvements
7. **Add logging** (2 hours) - Production monitoring
8. **Security fixes** (4 hours) - Critical for production
9. **CSV import** (8 hours) - Major feature
10. **Performance optimizations** (6 hours) - Scale improvements

**Total: ~30 hours of work**

---

## 🚀 **READY TO DEPLOY CHECKLIST**

Before deploying to production:

- [x] Git commit current state
- [x] Database indexes migration created
- [ ] Run migration: `alembic upgrade head`
- [ ] Loading skeletons on major pages
- [ ] Empty states with CTAs
- [ ] CSV export working
- [ ] Budget progress bars
- [ ] Critical bugs fixed
- [ ] CSP policy updated for production
- [ ] Sentry integrated
- [ ] Request logging enabled
- [ ] Redis caching configured
- [ ] Run `npm audit` and `pip-audit`
- [ ] Load testing with realistic data
- [ ] Backup procedures tested
- [ ] Deployment documentation written

---

## 📚 **ADDITIONAL RESOURCES**

- **Chakra UI Skeleton**: https://chakra-ui.com/docs/components/skeleton
- **React Dropzone**: https://react-dropzone.js.org/
- **Sentry React**: https://docs.sentry.io/platforms/javascript/guides/react/
- **Alembic Migrations**: https://alembic.sqlalchemy.org/
- **Redis Caching**: https://redis.io/docs/manual/client-side-caching/

---

**Questions? Check the security audit in the agent output above for detailed findings and recommendations.**
