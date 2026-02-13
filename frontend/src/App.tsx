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
import { IncomeExpensesPage } from './features/income-expenses/pages/IncomeExpensesPage';

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ChakraProvider theme={theme}>
        <BrowserRouter>
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Protected routes with layout */}
            <Route element={<ProtectedRoute />}>
              <Route element={<Layout />}>
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/transactions" element={<TransactionsPage />} />
                <Route path="/rules" element={<RulesPage />} />
                <Route path="/income-expenses" element={<IncomeExpensesPage />} />
                <Route path="/categories" element={<CategoriesPage />} />
              </Route>
            </Route>

            {/* Redirect root to dashboard or login */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />

            {/* Catch all - redirect to dashboard */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </ChakraProvider>
    </QueryClientProvider>
  );
}

export default App;
