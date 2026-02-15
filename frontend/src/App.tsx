/**
 * Main App component with routing
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ChakraProvider } from '@chakra-ui/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { theme } from './styles/theme';
import { queryClient } from './services/queryClient';
import { LoginPage } from './features/auth/pages/LoginPage';
import { RegisterPage } from './features/auth/pages/RegisterPage';
import { ProtectedRoute } from './features/auth/components/ProtectedRoute';
import { Layout } from './components/Layout';
import { DashboardPage } from './pages/DashboardPage';
import { TransactionsPage } from './pages/TransactionsPage';
import { RulesPage } from './pages/RulesPage';
import { CategoriesPage } from './pages/CategoriesPage';
import PreferencesPage from './pages/PreferencesPage';
import { IncomeExpensesPage } from './features/income-expenses/pages/IncomeExpensesPage';
import { AccountDetailPage } from './pages/AccountDetailPage';
import { InvestmentsPage } from './pages/InvestmentsPage';
import { AccountsPage } from './pages/AccountsPage';
import BudgetsPage from './pages/BudgetsPage';
import SavingsGoalsPage from './pages/SavingsGoalsPage';
import RecurringTransactionsPage from './pages/RecurringTransactionsPage';
import { HouseholdSettingsPage } from './pages/HouseholdSettingsPage';
import { AcceptInvitationPage } from './pages/AcceptInvitationPage';
import { UserViewProvider } from './contexts/UserViewContext';

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ChakraProvider theme={theme}>
        <BrowserRouter>
          <UserViewProvider>
            <Routes>
            {/* Public routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/accept-invite" element={<AcceptInvitationPage />} />

            {/* Protected routes with layout */}
            <Route element={<ProtectedRoute />}>
              <Route element={<Layout />}>
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/transactions" element={<TransactionsPage />} />
                <Route path="/investments" element={<InvestmentsPage />} />
                <Route path="/rules" element={<RulesPage />} />
                <Route path="/income-expenses" element={<IncomeExpensesPage />} />
                <Route path="/categories" element={<CategoriesPage />} />
                <Route path="/accounts" element={<AccountsPage />} />
                <Route path="/accounts/:accountId" element={<AccountDetailPage />} />
                <Route path="/budgets" element={<BudgetsPage />} />
                <Route path="/goals" element={<SavingsGoalsPage />} />
                <Route path="/recurring" element={<RecurringTransactionsPage />} />
                <Route path="/preferences" element={<PreferencesPage />} />
                <Route path="/household" element={<HouseholdSettingsPage />} />
              </Route>
            </Route>

            {/* Redirect root to dashboard or login */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />

            {/* Catch all - redirect to dashboard */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
          </UserViewProvider>
        </BrowserRouter>
      </ChakraProvider>
    </QueryClientProvider>
  );
}

export default App;
