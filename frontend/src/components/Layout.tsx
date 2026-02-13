/**
 * Main layout with top header and accounts sidebar
 */

import {
  Box,
  Flex,
  VStack,
  HStack,
  Text,
  Button,
  Divider,
  Spinner,
  Center,
} from '@chakra-ui/react';
import {
  ViewIcon,
  RepeatIcon,
  SettingsIcon,
  StarIcon,
  ArrowUpDownIcon,
} from '@chakra-ui/icons';
import { FiSettings } from 'react-icons/fi';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../features/auth/stores/authStore';
import { useLogout } from '../features/auth/hooks/useAuth';
import api from '../services/api';

interface Account {
  id: string;
  name: string;
  account_type: string;
  current_balance: number;
  balance_as_of: string | null;
}

interface NavItemProps {
  icon: any;
  label: string;
  path: string;
  isActive: boolean;
  onClick: () => void;
}

const TopNavItem = ({ icon, label, path, isActive, onClick }: NavItemProps) => {
  return (
    <Button
      leftIcon={<icon />}
      variant={isActive ? 'solid' : 'ghost'}
      colorScheme={isActive ? 'brand' : 'gray'}
      size="sm"
      onClick={onClick}
      fontWeight={isActive ? 'semibold' : 'medium'}
    >
      {label}
    </Button>
  );
};

interface AccountItemProps {
  account: Account;
  onAccountClick: (accountId: string) => void;
}

const AccountItem = ({ account, onAccountClick }: AccountItemProps) => {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const formatLastUpdated = (dateStr: string | null) => {
    if (!dateStr) return 'Never';

    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 30) return `${diffDays}d ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const balance = Number(account.current_balance);
  const isNegative = balance < 0;

  return (
    <Box
      px={3}
      py={2}
      _hover={{ bg: 'gray.50' }}
      cursor="pointer"
      borderRadius="md"
      transition="all 0.2s"
      onClick={() => onAccountClick(account.id)}
    >
      <HStack justify="space-between" align="start">
        <VStack align="start" spacing={0} flex={1}>
          <Text fontSize="sm" fontWeight="medium" color="gray.800">
            {account.name}
          </Text>
          <Text fontSize="xs" color="gray.500">
            {formatLastUpdated(account.balance_as_of)}
          </Text>
        </VStack>
        <Text
          fontSize="sm"
          fontWeight="semibold"
          color={isNegative ? 'red.600' : 'brand.600'}
        >
          {formatCurrency(balance)}
        </Text>
      </HStack>
    </Box>
  );
};

const accountTypeConfig: Record<string, { label: string; order: number }> = {
  checking: { label: 'Cash', order: 1 },
  savings: { label: 'Cash', order: 1 },
  credit_card: { label: 'Credit Cards', order: 2 },
  brokerage: { label: 'Investments', order: 3 },
  retirement_401k: { label: 'Retirement', order: 4 },
  retirement_ira: { label: 'Retirement', order: 4 },
  retirement_roth: { label: 'Retirement', order: 4 },
  hsa: { label: 'Retirement', order: 4 },
  loan: { label: 'Loans', order: 5 },
  mortgage: { label: 'Loans', order: 5 },
  property: { label: 'Property', order: 6 },
  crypto: { label: 'Crypto', order: 7 },
  manual: { label: 'Other', order: 8 },
  other: { label: 'Other', order: 8 },
};

export const Layout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuthStore();
  const logoutMutation = useLogout();

  const navItems = [
    { icon: ViewIcon, label: 'Dashboard', path: '/dashboard' },
    { icon: ArrowUpDownIcon, label: 'Cash Flow', path: '/income-expenses' },
    { icon: RepeatIcon, label: 'Transactions', path: '/transactions' },
    { icon: SettingsIcon, label: 'Rules', path: '/rules' },
    { icon: StarIcon, label: 'Categories', path: '/categories' },
    { icon: FiSettings, label: 'Settings', path: '/settings' },
  ];

  // Fetch accounts
  const { data: accounts, isLoading: accountsLoading } = useQuery<Account[]>({
    queryKey: ['accounts'],
    queryFn: async () => {
      const response = await api.get('/accounts');
      return response.data;
    },
  });

  // Group accounts by type
  const groupedAccounts = accounts?.reduce((acc, account) => {
    const typeConfig = accountTypeConfig[account.account_type] || { label: 'Other', order: 7 };
    const label = typeConfig.label;

    if (!acc[label]) {
      acc[label] = [];
    }
    acc[label].push(account);
    return acc;
  }, {} as Record<string, Account[]>);

  // Sort groups by order
  const sortedGroups = groupedAccounts
    ? Object.entries(groupedAccounts).sort((a, b) => {
        const aOrder = accountTypeConfig[accounts?.find(acc =>
          accountTypeConfig[acc.account_type]?.label === a[0]
        )?.account_type || '']?.order || 7;
        const bOrder = accountTypeConfig[accounts?.find(acc =>
          accountTypeConfig[acc.account_type]?.label === b[0]
        )?.account_type || '']?.order || 7;
        return aOrder - bOrder;
      })
    : [];

  const handleLogout = () => {
    logoutMutation.mutate();
  };

  const handleAccountClick = (accountId: string) => {
    navigate(`/accounts/${accountId}`);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  return (
    <Flex h="100vh" flexDirection="column" overflow="hidden">
      {/* Top Header */}
      <Box
        bg="white"
        borderBottomWidth={1}
        borderColor="gray.200"
        px={6}
        py={3}
        position="sticky"
        top={0}
        zIndex={10}
      >
        <HStack justify="space-between">
          {/* Left: Logo + Navigation */}
          <HStack spacing={6}>
            <Text fontSize="xl" fontWeight="bold" color="brand.600">
              Nest Egg
            </Text>
            <HStack spacing={2}>
              {navItems.map((item) => (
                <TopNavItem
                  key={item.path}
                  icon={item.icon}
                  label={item.label}
                  path={item.path}
                  isActive={location.pathname === item.path}
                  onClick={() => navigate(item.path)}
                />
              ))}
            </HStack>
          </HStack>

          {/* Right: User Info + Logout */}
          <HStack spacing={4}>
            <VStack align="end" spacing={0}>
              <Text fontSize="sm" fontWeight="medium">
                {user?.first_name} {user?.last_name}
              </Text>
              <Text fontSize="xs" color="gray.600">
                {user?.email}
              </Text>
            </VStack>
            <Button
              size="sm"
              variant="outline"
              colorScheme="red"
              onClick={handleLogout}
            >
              Logout
            </Button>
          </HStack>
        </HStack>
      </Box>

      <Flex flex={1} overflow="hidden">
        {/* Left Sidebar - Accounts */}
        <Box
          w="280px"
          bg="white"
          borderRightWidth={1}
          borderColor="gray.200"
          overflowY="auto"
          p={4}
        >
          <Text fontSize="xs" fontWeight="bold" color="gray.500" mb={3} textTransform="uppercase">
            Accounts
          </Text>

          {accountsLoading ? (
            <Center py={8}>
              <Spinner size="sm" color="brand.500" />
            </Center>
          ) : (
            <VStack spacing={4} align="stretch">
              {sortedGroups.map(([groupName, groupAccounts]) => {
                const groupTotal = groupAccounts.reduce(
                  (sum, account) => sum + Number(account.current_balance),
                  0
                );

                return (
                  <Box key={groupName}>
                    <HStack justify="space-between" mb={2}>
                      <Text
                        fontSize="xs"
                        fontWeight="semibold"
                        color="gray.600"
                        textTransform="uppercase"
                        letterSpacing="wide"
                      >
                        {groupName}
                      </Text>
                      <Text
                        fontSize="xs"
                        fontWeight="bold"
                        color={groupTotal < 0 ? 'red.600' : 'gray.700'}
                      >
                        {formatCurrency(groupTotal)}
                      </Text>
                    </HStack>
                    <VStack spacing={1} align="stretch">
                      {groupAccounts.map((account) => (
                        <AccountItem
                          key={account.id}
                          account={account}
                          onAccountClick={handleAccountClick}
                        />
                      ))}
                    </VStack>
                    <Divider mt={3} />
                  </Box>
                );
              })}

              {(!sortedGroups || sortedGroups.length === 0) && (
                <Text fontSize="sm" color="gray.500" textAlign="center" py={8}>
                  No accounts yet. Connect an account to get started.
                </Text>
              )}
            </VStack>
          )}
        </Box>

        {/* Main content area */}
        <Box flex={1} overflowY="auto" bg="gray.50">
          <Outlet />
        </Box>
      </Flex>
    </Flex>
  );
};
