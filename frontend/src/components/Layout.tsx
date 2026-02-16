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
  Badge,
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
  Tooltip,
} from '@chakra-ui/react';
import {
  AddIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  WarningIcon,
} from '@chakra-ui/icons';
import { FiSettings, FiLogOut, FiUsers } from 'react-icons/fi';
import { Outlet, useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useAuthStore } from '../features/auth/stores/authStore';
import { useLogout } from '../features/auth/hooks/useAuth';
import api from '../services/api';
import { AddAccountModal } from '../features/accounts/components/AddAccountModal';
import NotificationBell from '../features/notifications/components/NotificationBell';
import { UserViewToggle } from './UserViewToggle';
import { useUserView } from '../contexts/UserViewContext';

interface Account {
  id: string;
  name: string;
  account_type: string;
  current_balance: number;
  balance_as_of: string | null;
  user_id: string;
  plaid_item_hash: string | null;
  plaid_item_id: string | null;
  exclude_from_cash_flow: boolean;
  // Sync status
  last_synced_at: string | null;
  last_error_code: string | null;
  last_error_message: string | null;
  needs_reauth: boolean | null;
}

interface DedupedAccount extends Account {
  owner_ids: string[];  // Array of user IDs who own this account
  is_shared: boolean;   // True if owned by multiple users
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
  account: DedupedAccount;
  onAccountClick: (accountId: string) => void;
  currentUserId?: string;
  getUserColor: (userId: string) => string;
  getUserBgColor: (userId: string) => string | undefined;
  getUserInitials: (userId: string) => string;
  getUserName: (userId: string) => string;
  isCombinedView: boolean;
  membersLoaded: boolean;
}

const AccountItem = ({
  account,
  onAccountClick,
  currentUserId,
  getUserColor,
  getUserBgColor,
  getUserInitials,
  getUserName,
  isCombinedView,
  membersLoaded,
}: AccountItemProps) => {
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
  const isOwnedByCurrentUser = account.owner_ids.includes(currentUserId || '');

  // Get background color from primary owner (first in list)
  const primaryOwnerId = account.owner_ids[0];
  const bgColor = isCombinedView ? getUserBgColor(primaryOwnerId) : undefined;

  // Check for sync errors
  const hasSyncError = account.last_error_code || account.needs_reauth;
  const errorTooltip = account.needs_reauth
    ? 'Reauthentication required - click to reconnect account'
    : account.last_error_message || 'Sync error - check account settings';

  return (
    <Box
      px={3}
      py={1.5}
      ml={5}
      bg={bgColor}
      _hover={{ bg: bgColor ? bgColor : 'gray.50', opacity: 0.8 }}
      cursor="pointer"
      borderRadius="md"
      transition="all 0.2s"
      onClick={() => onAccountClick(account.id)}
      borderLeftWidth={isOwnedByCurrentUser ? 3 : 0}
      borderLeftColor="brand.500"
    >
      <VStack align="stretch" spacing={1}>
        <HStack justify="space-between" align="center" spacing={2}>
          <HStack flex={1} minW={0} spacing={1.5}>
            <Text fontSize="xs" fontWeight="medium" color="gray.700" noOfLines={1} flex={1}>
              {account.name}
            </Text>
            {hasSyncError && (
              <Tooltip label={errorTooltip} placement="right" hasArrow>
                <WarningIcon
                  boxSize={3}
                  color={account.needs_reauth ? 'orange.500' : 'red.500'}
                  flexShrink={0}
                />
              </Tooltip>
            )}
          </HStack>
          <Text
            fontSize="xs"
            fontWeight="semibold"
            color={isNegative ? 'red.600' : 'brand.600'}
            flexShrink={0}
          >
            {formatCurrency(balance)}
          </Text>
        </HStack>
        <HStack justify="space-between" align="center">
          <Text fontSize="2xs" color="gray.500">
            {formatLastUpdated(account.balance_as_of)}
          </Text>
          {isCombinedView && membersLoaded && (
            <HStack spacing={1}>
              {account.owner_ids.map((ownerId) => (
                <Tooltip key={ownerId} label={getUserName(ownerId)} placement="top">
                  <Badge
                    size="sm"
                    fontSize="2xs"
                    px={1.5}
                    py={0.5}
                    borderRadius="md"
                    bg={getUserColor(ownerId)}
                    color="white"
                    fontWeight="bold"
                  >
                    {getUserInitials(ownerId)}
                  </Badge>
                </Tooltip>
              ))}
            </HStack>
          )}
        </HStack>
      </VStack>
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
  const [searchParams] = useSearchParams();
  const { user } = useAuthStore();
  const { selectedUserId, isCombinedView, isOtherUserView, canEdit } = useUserView();
  const logoutMutation = useLogout();
  const { isOpen: isAddAccountOpen, onOpen: onAddAccountOpen, onClose: onAddAccountClose } = useDisclosure();
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({});

  // Navigation helper that preserves query params
  const navigateWithParams = (path: string) => {
    const currentUser = searchParams.get('user');
    if (currentUser) {
      navigate(`${path}?user=${currentUser}`);
    } else {
      navigate(path);
    }
  };

  const cashFlowMenuItems = [
    { label: 'Cash Flow', path: '/income-expenses' },
    { label: 'Budgets', path: '/budgets' },
    { label: 'Goals', path: '/goals' },
  ];

  const transactionsMenuItems = [
    { label: 'Transactions', path: '/transactions' },
    { label: 'Categories', path: '/categories' },
    { label: 'Rules', path: '/rules' },
    { label: 'Recurring', path: '/recurring' },
    { label: 'Bills', path: '/bills' },
    { label: 'Subscriptions', path: '/subscriptions' },
    { label: 'Tax Deductible', path: '/tax-deductible' },
  ];

  // Fetch accounts with user filtering
  const { data: accounts, isLoading: accountsLoading } = useQuery<Account[]>({
    queryKey: ['accounts', selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const response = await api.get('/accounts', { params });
      return response.data;
    },
  });

  // Fetch dashboard summary for net worth (filtered by user)
  const { data: dashboardSummary } = useQuery({
    queryKey: ['dashboard-summary', selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const response = await api.get('/dashboard/summary', { params });
      return response.data;
    },
  });

  // Fetch household members for color coding
  const { data: members } = useQuery({
    queryKey: ['household-members'],
    queryFn: async () => {
      const response = await api.get('/household/members');
      return response.data;
    },
  });

  // Assign colors to users for visual distinction in combined view
  const userColors = ['blue.500', 'green.500', 'purple.500', 'orange.500', 'pink.500'];
  const userBgColors = ['blue.50', 'green.50', 'purple.50', 'orange.50', 'pink.50'];

  const getUserColorIndex = (userId: string): number => {
    if (!members) return 0;
    const memberIndex = members.findIndex((m: any) => m.id === userId);
    return memberIndex >= 0 ? memberIndex : 0;
  };

  const getUserColor = (userId: string): string => {
    const index = getUserColorIndex(userId);
    return userColors[index % userColors.length];
  };

  const getUserBgColor = (userId: string): string | undefined => {
    if (!isCombinedView) return undefined;
    const index = getUserColorIndex(userId);
    return userBgColors[index % userBgColors.length];
  };

  const getUserName = (userId: string): string => {
    if (!members || !userId) {
      return '';
    }

    const member = members.find((m: any) => m.id === userId);
    if (!member) {
      return '';
    }

    // Try display_name first
    if (member.display_name && member.display_name.trim()) {
      return member.display_name.trim();
    }

    // Try first_name + last_name
    if (member.first_name && member.first_name.trim()) {
      if (member.last_name && member.last_name.trim()) {
        return `${member.first_name.trim()} ${member.last_name.trim()}`;
      }
      return member.first_name.trim();
    }

    // Fallback to email username
    if (member.email && member.email.includes('@')) {
      return member.email.split('@')[0];
    }

    return '';
  };

  const getUserInitials = (userId: string): string => {
    const name = getUserName(userId);
    if (!name || name.length === 0) return '?';

    // Split by space to get first and last name
    const parts = name.split(' ').filter(p => p.length > 0);

    if (parts.length >= 2) {
      // Use first letter of first word and first letter of last word
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }

    // Single word name - use first two characters
    if (name.length >= 2) {
      return name.substring(0, 2).toUpperCase();
    }

    // Very short name - use first character twice
    return (name[0] + name[0]).toUpperCase();
  };

  // Deduplicate accounts in combined view
  const dedupedAccounts: DedupedAccount[] = isCombinedView && accounts
    ? (() => {
        const hashMap = new Map<string, DedupedAccount>();

        accounts.forEach((account) => {
          const hash = account.plaid_item_hash || account.id; // Use account ID if no hash

          if (hashMap.has(hash)) {
            // Account already exists, add this user as an owner
            const existing = hashMap.get(hash)!;
            if (!existing.owner_ids.includes(account.user_id)) {
              existing.owner_ids.push(account.user_id);
              existing.is_shared = true;
            }
          } else {
            // First time seeing this account
            hashMap.set(hash, {
              ...account,
              owner_ids: [account.user_id],
              is_shared: false,
            });
          }
        });

        return Array.from(hashMap.values());
      })()
    : accounts?.map(account => ({
        ...account,
        owner_ids: [account.user_id],
        is_shared: false,
      })) || [];

  // Group accounts by type (using deduplicated accounts)
  const groupedAccounts = dedupedAccounts?.reduce((acc, account) => {
    const typeConfig = accountTypeConfig[account.account_type] || { label: 'Other', order: 7 };
    const label = typeConfig.label;

    if (!acc[label]) {
      acc[label] = [];
    }
    acc[label].push(account);
    return acc;
  }, {} as Record<string, DedupedAccount[]>);

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
    navigateWithParams(`/accounts/${accountId}`);
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
          <HStack spacing={8}>
            <Text fontSize="xl" fontWeight="bold" color="brand.600" whiteSpace="nowrap">
              Nest Egg
            </Text>
            <HStack spacing={1}>
              {/* Overview */}
              <TopNavItem
                label="Overview"
                isActive={location.pathname === '/overview'}
                onClick={() => navigateWithParams('/overview')}
              />

              {/* Cash Flow Dropdown */}
              <Menu>
                <MenuButton
                  as={Button}
                  rightIcon={<ChevronDownIcon />}
                  variant={cashFlowMenuItems.some(item => location.pathname === item.path) ? 'solid' : 'ghost'}
                  colorScheme={cashFlowMenuItems.some(item => location.pathname === item.path) ? 'brand' : 'gray'}
                  size="sm"
                  fontWeight={cashFlowMenuItems.some(item => location.pathname === item.path) ? 'semibold' : 'medium'}
                >
                  Cash Flow
                </MenuButton>
                <MenuList>
                  {cashFlowMenuItems.map((item) => (
                    <MenuItem
                      key={item.path}
                      onClick={() => navigateWithParams(item.path)}
                      fontWeight={location.pathname === item.path ? 'semibold' : 'normal'}
                      bg={location.pathname === item.path ? 'brand.50' : 'transparent'}
                    >
                      {item.label}
                    </MenuItem>
                  ))}
                </MenuList>
              </Menu>

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
                      onClick={() => navigateWithParams(item.path)}
                      fontWeight={location.pathname === item.path ? 'semibold' : 'normal'}
                      bg={location.pathname === item.path ? 'brand.50' : 'transparent'}
                    >
                      {item.label}
                    </MenuItem>
                  ))}
                </MenuList>
              </Menu>

              {/* Investments */}
              <TopNavItem
                label="Investments"
                isActive={location.pathname === '/investments'}
                onClick={() => navigateWithParams('/investments')}
              />

              {/* Accounts */}
              <TopNavItem
                label="Accounts"
                isActive={location.pathname === '/accounts'}
                onClick={() => navigateWithParams('/accounts')}
              />
            </HStack>
          </HStack>

          {/* Right: User View Toggle, Notification Bell and User Menu */}
          <HStack spacing={4}>
            <UserViewToggle />
            <NotificationBell />

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
              <MenuItem icon={<FiUsers />} onClick={() => navigateWithParams('/household')}>
                Household Settings
              </MenuItem>
              <MenuItem icon={<FiSettings />} onClick={() => navigateWithParams('/preferences')}>
                Preferences
              </MenuItem>
              <MenuItem icon={<FiLogOut />} onClick={handleLogout} color="red.600">
                Logout
              </MenuItem>
            </MenuList>
          </Menu>
          </HStack>
        </HStack>
      </Box>

      {/* View Indicator Banner */}
      {!isCombinedView && members && (
        <Box
          bg={isOtherUserView ? 'orange.50' : 'blue.50'}
          borderBottomWidth={1}
          borderColor={isOtherUserView ? 'orange.200' : 'blue.200'}
          px={8}
          py={2}
        >
          <HStack spacing={3}>
            <Text fontSize="sm" fontWeight="semibold" color={isOtherUserView ? 'orange.800' : 'blue.800'}>
              {isOtherUserView ? '👁️ Viewing:' : '📊 Your View:'}
            </Text>
            <Badge
              size="sm"
              fontSize="xs"
              px={2}
              py={1}
              borderRadius="md"
              bg={getUserColor(selectedUserId || user?.id || '')}
              color="white"
              fontWeight="bold"
            >
              {getUserInitials(selectedUserId || user?.id || '')}
            </Badge>
            <Text fontSize="sm" fontWeight="medium" color={isOtherUserView ? 'orange.700' : 'blue.700'}>
              {getUserName(selectedUserId || user?.id || '')}
              {isOtherUserView ? "'s Accounts (Read-only)" : "'s Accounts"}
            </Text>
          </HStack>
        </Box>
      )}

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
          <VStack align="stretch" spacing={2} mb={3}>
            <HStack justify="space-between">
              <VStack align="start" spacing={0}>
                <Text fontSize="sm" fontWeight="bold" textTransform="uppercase" color="gray.700" letterSpacing="wide">
                  Accounts
                </Text>
                {!isCombinedView && members && (
                  <HStack spacing={1} mt={1}>
                    <Badge
                      size="sm"
                      fontSize="2xs"
                      px={1.5}
                      py={0.5}
                      borderRadius="md"
                      bg={getUserColor(selectedUserId || user?.id || '')}
                      color="white"
                      fontWeight="bold"
                    >
                      {getUserInitials(selectedUserId || user?.id || '')}
                    </Badge>
                    <Text fontSize="2xs" color="gray.600">
                      {getUserName(selectedUserId || user?.id || '')}
                    </Text>
                  </HStack>
                )}
              </VStack>
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
          </VStack>

          {/* User color legend in combined view */}
          {isCombinedView && members && members.length > 1 && (
            <Box mb={3} p={2} bg="gray.50" borderRadius="md">
              <Text fontSize="2xs" fontWeight="semibold" color="gray.600" mb={1.5}>
                HOUSEHOLD MEMBERS
              </Text>
              <VStack spacing={1} align="stretch">
                {members.map((member: any, index: number) => (
                  <HStack key={member.id} spacing={2}>
                    <Badge
                      size="sm"
                      fontSize="2xs"
                      px={1.5}
                      py={0.5}
                      borderRadius="md"
                      bg={userColors[index % userColors.length]}
                      color="white"
                      fontWeight="bold"
                    >
                      {getUserInitials(member.id)}
                    </Badge>
                    <Text fontSize="2xs" color="gray.700">
                      {getUserName(member.id)}
                    </Text>
                  </HStack>
                ))}
              </VStack>
            </Box>
          )}

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
                            currentUserId={user?.id}
                            getUserColor={getUserColor}
                            getUserBgColor={getUserBgColor}
                            getUserInitials={getUserInitials}
                            getUserName={getUserName}
                            isCombinedView={isCombinedView}
                            membersLoaded={!!members}
                          />
                        ))}
                      </VStack>
                    </Collapse>
                  </Box>
                );
              })}

              {(!sortedGroups || sortedGroups.length === 0) && (
                <Text fontSize="sm" color="gray.500" textAlign="center" py={8}>
                  {isOtherUserView
                    ? "This user has no accounts yet."
                    : "No accounts yet. Connect an account to get started."}
                </Text>
              )}

              {!isOtherUserView && (
                <Tooltip
                  label={!canEdit ? "You can only add accounts for yourself or in combined view" : ""}
                  placement="top"
                  isDisabled={canEdit}
                >
                  <Button
                    leftIcon={<AddIcon />}
                    colorScheme="brand"
                    size="sm"
                    onClick={onAddAccountOpen}
                    mt={2}
                    w="full"
                    isDisabled={!canEdit}
                  >
                    Add Account
                  </Button>
                </Tooltip>
              )}
            </VStack>
          )}
        </Box>

        {/* Main content area */}
        <Box flex={1} overflowY="auto" bg="gray.50" pl={8}>
          <Outlet />
        </Box>
      </Flex>

      {/* Add Account Modal */}
      <AddAccountModal isOpen={isAddAccountOpen} onClose={onAddAccountClose} />
    </Flex>
  );
};
