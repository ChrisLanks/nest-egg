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
  useDisclosure,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Avatar,
  Collapse,
  IconButton,
} from '@chakra-ui/react';
import {
  AddIcon,
  ChevronDownIcon,
  ChevronRightIcon,
} from '@chakra-ui/icons';
import { FiSettings, FiLogOut } from 'react-icons/fi';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useAuthStore } from '../features/auth/stores/authStore';
import { useLogout } from '../features/auth/hooks/useAuth';
import api from '../services/api';
import { AddAccountModal } from '../features/accounts/components/AddAccountModal';

interface Account {
  id: string;
  name: string;
  account_type: string;
  current_balance: number;
  balance_as_of: string | null;
}

interface NavItemProps {
  label: string;
  path: string;
  isActive: boolean;
  onClick: () => void;
}

const TopNavItem = ({ label, isActive, onClick }: Omit<NavItemProps, 'icon' | 'path'>) => {
  return (
    <Button
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
      py={1}
      ml={5}
      _hover={{ bg: 'gray.50' }}
      cursor="pointer"
      borderRadius="md"
      transition="all 0.2s"
      onClick={() => onAccountClick(account.id)}
    >
      <HStack justify="space-between" align="center" spacing={2}>
        <VStack align="start" spacing={0} flex={1} minW={0}>
          <Text fontSize="xs" fontWeight="medium" color="gray.700" noOfLines={1}>
            {account.name}
          </Text>
          <Text fontSize="2xs" color="gray.500">
            {formatLastUpdated(account.balance_as_of)}
          </Text>
        </VStack>
        <Text
          fontSize="xs"
          fontWeight="semibold"
          color={isNegative ? 'red.600' : 'brand.600'}
          flexShrink={0}
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
  private_equity: { label: 'Investments', order: 3 },
  retirement_401k: { label: 'Retirement', order: 4 },
  retirement_ira: { label: 'Retirement', order: 4 },
  retirement_roth: { label: 'Retirement', order: 4 },
  retirement_529: { label: 'Retirement', order: 4 },
  hsa: { label: 'Retirement', order: 4 },
  loan: { label: 'Loans', order: 5 },
  mortgage: { label: 'Loans', order: 5 },
  property: { label: 'Property', order: 6 },
  vehicle: { label: 'Property', order: 6 },
  crypto: { label: 'Crypto', order: 7 },
  manual: { label: 'Other', order: 8 },
  other: { label: 'Other', order: 8 },
};

export const Layout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuthStore();
  const logoutMutation = useLogout();
  const { isOpen: isAddAccountOpen, onOpen: onAddAccountOpen, onClose: onAddAccountClose } = useDisclosure();
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({});

  const navItems = [
    { label: 'Overview', path: '/dashboard' },
    { label: 'Cash Flow', path: '/income-expenses' },
    { label: 'Investments', path: '/investments' },
    { label: 'Accounts', path: '/accounts' },
  ];

  const transactionsMenuItems = [
    { label: 'Transactions', path: '/transactions' },
    { label: 'Categories', path: '/categories' },
    { label: 'Rules', path: '/rules' },
  ];

  // Fetch accounts
  const { data: accounts, isLoading: accountsLoading } = useQuery<Account[]>({
    queryKey: ['accounts'],
    queryFn: async () => {
      const response = await api.get('/accounts');
      return response.data;
    },
  });

  // Fetch dashboard summary for net worth (all accounts)
  const { data: dashboardSummary } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: async () => {
      const response = await api.get('/dashboard/summary');
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

  const toggleSection = (sectionName: string) => {
    setCollapsedSections(prev => ({
      ...prev,
      [sectionName]: !prev[sectionName]
    }));
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
                  label={item.label}
                  isActive={location.pathname === item.path}
                  onClick={() => navigate(item.path)}
                />
              ))}

              {/* Transactions Dropdown */}
              <Menu>
                <MenuButton
                  as={Button}
                  rightIcon={<ChevronDownIcon />}
                  variant={transactionsMenuItems.some(item => location.pathname === item.path) ? 'solid' : 'ghost'}
                  colorScheme={transactionsMenuItems.some(item => location.pathname === item.path) ? 'brand' : 'gray'}
                  size="sm"
                  fontWeight={transactionsMenuItems.some(item => location.pathname === item.path) ? 'semibold' : 'medium'}
                >
                  Transactions
                </MenuButton>
                <MenuList>
                  {transactionsMenuItems.map((item) => (
                    <MenuItem
                      key={item.path}
                      onClick={() => navigate(item.path)}
                      fontWeight={location.pathname === item.path ? 'semibold' : 'normal'}
                      bg={location.pathname === item.path ? 'brand.50' : 'transparent'}
                    >
                      {item.label}
                    </MenuItem>
                  ))}
                </MenuList>
              </Menu>
            </HStack>
          </HStack>

          {/* Right: User Menu Dropdown */}
          <Menu>
            <MenuButton
              as={Button}
              rightIcon={<ChevronDownIcon />}
              variant="ghost"
              size="sm"
            >
              <HStack spacing={2}>
                <Avatar
                  size="sm"
                  name={`${user?.first_name} ${user?.last_name}`}
                  bg="brand.500"
                />
                <VStack align="start" spacing={0}>
                  <Text fontSize="sm" fontWeight="medium">
                    {user?.first_name} {user?.last_name}
                  </Text>
                  <Text fontSize="xs" color="gray.600">
                    {user?.email}
                  </Text>
                </VStack>
              </HStack>
            </MenuButton>
            <MenuList>
              <MenuItem icon={<FiSettings />} onClick={() => navigate('/preferences')}>
                Preferences
              </MenuItem>
              <MenuItem icon={<FiLogOut />} onClick={handleLogout} color="red.600">
                Logout
              </MenuItem>
            </MenuList>
          </Menu>
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
          p={3}
        >
          <HStack justify="space-between" mb={3}>
            <Text fontSize="sm" fontWeight="bold" textTransform="uppercase" color="gray.700" letterSpacing="wide">
              Accounts
            </Text>
            {dashboardSummary?.net_worth !== undefined && (
              <Text
                fontSize="md"
                fontWeight="bold"
                color={dashboardSummary.net_worth >= 0 ? 'green.600' : 'red.600'}
              >
                {formatCurrency(Number(dashboardSummary.net_worth))}
              </Text>
            )}
          </HStack>

          {accountsLoading ? (
            <Center py={8}>
              <Spinner size="sm" color="brand.500" />
            </Center>
          ) : (
            <VStack spacing={2} align="stretch">
              {sortedGroups.map(([groupName, groupAccounts]) => {
                const groupTotal = groupAccounts.reduce(
                  (sum, account) => sum + Number(account.current_balance),
                  0
                );
                const isCollapsed = collapsedSections[groupName];

                return (
                  <Box key={groupName}>
                    <HStack
                      justify="space-between"
                      mb={1}
                      px={2}
                      py={1.5}
                      cursor="pointer"
                      _hover={{ bg: 'gray.50' }}
                      borderRadius="md"
                      onClick={() => toggleSection(groupName)}
                    >
                      <HStack spacing={2}>
                        {isCollapsed ? (
                          <ChevronRightIcon boxSize={3.5} color="gray.600" />
                        ) : (
                          <ChevronDownIcon boxSize={3.5} color="gray.600" />
                        )}
                        <Text
                          fontSize="sm"
                          fontWeight="bold"
                          color="gray.700"
                          textTransform="uppercase"
                          letterSpacing="wide"
                        >
                          {groupName}
                        </Text>
                      </HStack>
                      <Text
                        fontSize="sm"
                        fontWeight="bold"
                        color={groupTotal < 0 ? 'red.600' : 'gray.800'}
                      >
                        {formatCurrency(groupTotal)}
                      </Text>
                    </HStack>
                    <Collapse in={!isCollapsed} animateOpacity>
                      <VStack spacing={0.5} align="stretch" mb={2}>
                        {groupAccounts.map((account) => (
                          <AccountItem
                            key={account.id}
                            account={account}
                            onAccountClick={handleAccountClick}
                          />
                        ))}
                      </VStack>
                    </Collapse>
                  </Box>
                );
              })}

              {(!sortedGroups || sortedGroups.length === 0) && (
                <Text fontSize="sm" color="gray.500" textAlign="center" py={8}>
                  No accounts yet. Connect an account to get started.
                </Text>
              )}

              <Button
                leftIcon={<AddIcon />}
                colorScheme="brand"
                size="sm"
                onClick={onAddAccountOpen}
                mt={2}
                w="full"
              >
                Add Account
              </Button>
            </VStack>
          )}
        </Box>

        {/* Main content area */}
        <Box flex={1} overflowY="auto" bg="gray.50">
          <Outlet />
        </Box>
      </Flex>

      {/* Add Account Modal */}
      <AddAccountModal isOpen={isAddAccountOpen} onClose={onAddAccountClose} />
    </Flex>
  );
};
