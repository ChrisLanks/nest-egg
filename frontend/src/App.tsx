/**
 * Main App component with routing
 * Uses React.lazy for code splitting to improve initial load performance
 */

import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ChakraProvider, Spinner, Center } from '@chakra-ui/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { theme } from './styles/theme';
import { queryClient } from './services/queryClient';
import { UserViewProvider } from './contexts/UserViewContext';

// Eager-loaded components (critical for initial render)
import { LoginPage } from './features/auth/pages/LoginPage';
import { RegisterPage } from './features/auth/pages/RegisterPage';
import { ProtectedRoute } from './features/auth/components/ProtectedRoute';
import { Layout } from './components/Layout';
import { ErrorBoundary } from './components/ErrorBoundary';

// Lazy-loaded pages (code-split for performance)
const DashboardPage = lazy(() => import('./pages/DashboardPage').then(m => ({ default: m.DashboardPage })));
const TransactionsPage = lazy(() => import('./pages/TransactionsPage').then(m => ({ default: m.TransactionsPage })));
const RulesPage = lazy(() => import('./pages/RulesPage').then(m => ({ default: m.RulesPage })));
const CategoriesPage = lazy(() => import('./pages/CategoriesPage').then(m => ({ default: m.CategoriesPage })));
const PreferencesPage = lazy(() => import('./pages/PreferencesPage'));
const IncomeExpensesPage = lazy(() => import('./features/income-expenses/pages/IncomeExpensesPage').then(m => ({ default: m.IncomeExpensesPage })));
const AccountDetailPage = lazy(() => import('./pages/AccountDetailPage').then(m => ({ default: m.AccountDetailPage })));
const InvestmentsPage = lazy(() => import('./pages/InvestmentsPage').then(m => ({ default: m.InvestmentsPage })));
const AccountsPage = lazy(() => import('./pages/AccountsPage').then(m => ({ default: m.AccountsPage })));
const BudgetsPage = lazy(() => import('./pages/BudgetsPage'));
const SavingsGoalsPage = lazy(() => import('./pages/SavingsGoalsPage'));
const RecurringTransactionsPage = lazy(() => import('./pages/RecurringTransactionsPage'));
const BillsPage = lazy(() => import('./pages/BillsPage'));
const TaxDeductiblePage = lazy(() => import('./pages/TaxDeductiblePage'));
const TrendsPage = lazy(() => import('./pages/TrendsPage'));
const ReportsPage = lazy(() => import('./pages/ReportsPage'));
const DebtPayoffPage = lazy(() => import('./pages/DebtPayoffPage'));
const HouseholdSettingsPage = lazy(() => import('./pages/HouseholdSettingsPage').then(m => ({ default: m.HouseholdSettingsPage })));
const AcceptInvitationPage = lazy(() => import('./pages/AcceptInvitationPage').then(m => ({ default: m.AcceptInvitationPage })));

// Loading fallback component
const PageLoader = () => (
  <Center h="100vh">
    <Spinner size="xl" color="brand.500" thickness="4px" />
  </Center>
);

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ChakraProvider theme={theme}>
        <BrowserRouter>
          <UserViewProvider>
            <ErrorBoundary>
            <Suspense fallback={<PageLoader />}>
              <Routes>
            {/* Public routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/accept-invite" element={<AcceptInvitationPage />} />

            {/* Protected routes with layout */}
            <Route element={<ProtectedRoute />}>
              <Route element={<Layout />}>
                <Route path="/overview" element={<DashboardPage />} />
                <Route path="/transactions" element={<TransactionsPage />} />
                <Route path="/investments" element={<InvestmentsPage />} />
                <Route path="/rules" element={<RulesPage />} />
                <Route path="/income-expenses" element={<IncomeExpensesPage />} />
                <Route path="/categories" element={<CategoriesPage />} />
                <Route path="/tax-deductible" element={<TaxDeductiblePage />} />
                <Route path="/trends" element={<TrendsPage />} />
                <Route path="/reports" element={<ReportsPage />} />
                <Route path="/accounts" element={<AccountsPage />} />
                <Route path="/accounts/:accountId" element={<AccountDetailPage />} />
                <Route path="/budgets" element={<BudgetsPage />} />
                <Route path="/goals" element={<SavingsGoalsPage />} />
                <Route path="/recurring" element={<RecurringTransactionsPage />} />
                <Route path="/bills" element={<BillsPage />} />
                {/* Redirect old subscriptions route to recurring page */}
                <Route path="/subscriptions" element={<Navigate to="/recurring" replace />} />
                <Route path="/debt-payoff" element={<DebtPayoffPage />} />
                <Route path="/preferences" element={<PreferencesPage />} />
                <Route path="/household" element={<HouseholdSettingsPage />} />
              </Route>
            </Route>

            {/* Redirect root to overview */}
            <Route path="/" element={<Navigate to="/overview" replace />} />

            {/* Catch all - redirect to overview */}
            <Route path="*" element={<Navigate to="/overview" replace />} />
              </Routes>
            </Suspense>
            </ErrorBoundary>
          </UserViewProvider>
        </BrowserRouter>
      </ChakraProvider>
    </QueryClientProvider>
  );
}

export default App;
