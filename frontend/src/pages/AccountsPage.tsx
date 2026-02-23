/**
 * Accounts admin page with institution grouping and bulk operations
 */

import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Spinner,
  Center,
  Button,
  IconButton,
  useToast,
  Card,
  CardHeader,
  CardBody,
  Checkbox,
  Badge,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
  useDisclosure,
  Tooltip,
  Icon,
  Alert,
  AlertIcon,
  AlertDescription,
} from '@chakra-ui/react';
import { useState, useMemo, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ViewIcon, ViewOffIcon, EditIcon, DeleteIcon, ChevronDownIcon, RepeatIcon } from '@chakra-ui/icons';
import { useNavigate } from 'react-router-dom';
import { FiCreditCard, FiTrendingUp, FiTrendingDown, FiAlertTriangle } from 'react-icons/fi';
import api from '../services/api';
import { formatAssetType } from '../utils/formatAssetType';
import { EmptyState } from '../components/EmptyState';
import { useUserView } from '../contexts/UserViewContext';
import { AccountsSkeleton } from '../components/LoadingSkeleton';

interface Account {
  id: string;
  user_id: string;
  name: string;
  account_type: string;
  institution_name: string | null;
  mask: string | null;
  current_balance: number;
  available_balance: number | null;
  limit: number | null;
  is_active: boolean;
  exclude_from_cash_flow: boolean;
  balance_as_of: string | null;
  plaid_item_id: string | null;
  last_synced_at: string | null;
  last_error_code: string | null;
  last_error_message: string | null;
  needs_reauth: boolean | null;
}

interface User {
  id: string;
  email: string;
  full_name: string | null;
  display_name: string | null;
  first_name: string | null;
  last_name: string | null;
}

export const AccountsPage = () => {
  const [selectedAccounts, setSelectedAccounts] = useState<Set<string>>(new Set());
  const [deleteTarget, setDeleteTarget] = useState<'selected' | string | null>(null);
  const [syncingItemId, setSyncingItemId] = useState<string | null>(null);
  const toast = useToast();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { isOpen: isDeleteOpen, onOpen: onDeleteOpen, onClose: onDeleteClose } = useDisclosure();
  const cancelRef = useRef<HTMLButtonElement>(null);
  const { canWriteResource, isOtherUserView, selectedUserId } = useUserView();
  const canEdit = canWriteResource('account');

  // Fetch current user for permission checks
  const { data: currentUser } = useQuery({
    queryKey: ['current-user'],
    queryFn: async () => {
      const response = await api.get<User>('/auth/me');
      return response.data;
    },
  });

  // Fetch all accounts (ALWAYS include hidden - this is the admin page)
  // Filter by selected user when not in combined view
  const { data: accounts, isLoading } = useQuery({
    queryKey: ['accounts-admin', 'include-hidden', selectedUserId],
    queryFn: async () => {
      const params: { include_hidden: boolean; user_id?: string } = {
        include_hidden: true
      };

      // Filter by user_id when a specific user is selected (not combined view)
      if (selectedUserId) {
        params.user_id = selectedUserId;
      }

      const response = await api.get<Account[]>('/accounts', { params });
      return response.data;
    },
  });

  // Fetch household users for ownership display
  const { data: users } = useQuery({
    queryKey: ['household-users'],
    queryFn: async () => {
      const response = await api.get<User[]>('/household/members');
      return response.data;
    },
  });

  // Refresh data when user view selection changes
  useEffect(() => {
    // Invalidate queries to refresh the page when view changes
    queryClient.invalidateQueries({ queryKey: ['accounts-admin'] });
    queryClient.invalidateQueries({ queryKey: ['current-user'] });
    queryClient.invalidateQueries({ queryKey: ['household-users'] });
  }, [selectedUserId, queryClient]);

  // Create user map for quick lookups
  const userMap = useMemo(() => {
    if (!users) return new Map<string, User>();
    return new Map(users.map(user => [user.id, user]));
  }, [users]);

  // Same color palette as Layout.tsx household member colors
  const userColorSchemes = ['blue', 'green', 'purple', 'orange', 'pink'];

  const getUserColorScheme = (userId: string): string => {
    if (!users) return 'blue';
    const index = users.findIndex(u => u.id === userId);
    return userColorSchemes[(index >= 0 ? index : 0) % userColorSchemes.length];
  };

  const getUserDisplayName = (user: User): string => {
    if (user.display_name?.trim()) return user.display_name.trim();
    if (user.first_name?.trim()) {
      return user.last_name?.trim()
        ? `${user.first_name.trim()} ${user.last_name.trim()}`
        : user.first_name.trim();
    }
    return user.email.split('@')[0];
  };

  // Check if current user can modify an account
  const canModifyAccount = (account: Account): boolean => {
    if (!currentUser) return false;
    // Combined view: can edit all household accounts
    if (selectedUserId === null) return true;
    // Self view: only own accounts
    if (selectedUserId === currentUser.id) return account.user_id === currentUser.id;
    // Other-user view: canEdit already evaluated grants in UserViewContext
    return canEdit;
  };

  // Bulk delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (accountIds: string[]) => {
      await api.post('/accounts/bulk-delete', { account_ids: accountIds });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts-admin'] });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      queryClient.invalidateQueries({ queryKey: ['infinite-transactions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      toast({
        title: 'Accounts deleted',
        status: 'success',
        duration: 3000,
      });
      setSelectedAccounts(new Set());
      onDeleteClose();
    },
    onError: () => {
      toast({
        title: 'Failed to delete accounts',
        status: 'error',
        duration: 3000,
      });
    },
  });

  // Bulk visibility mutation
  const visibilityMutation = useMutation({
    mutationFn: async ({ accountIds, isActive }: { accountIds: string[]; isActive: boolean }) => {
      const response = await api.patch<{ updated_count: number }>('/accounts/bulk-visibility', {
        account_ids: accountIds,
        is_active: isActive,
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['accounts-admin'] });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      queryClient.invalidateQueries({ queryKey: ['infinite-transactions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      if (data.updated_count === 0) {
        toast({
          title: 'No accounts updated',
          description: 'No accounts were changed — you may not have permission to modify these accounts.',
          status: 'warning',
          duration: 5000,
        });
      } else {
        toast({
          title: `${data.updated_count} account${data.updated_count !== 1 ? 's' : ''} updated`,
          status: 'success',
          duration: 3000,
        });
      }
      setSelectedAccounts(new Set());
    },
    onError: (error: any) => {
      console.error('[AccountsPage] Bulk visibility error:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || 'Unknown error';
      toast({
        title: 'Failed to update visibility',
        description: errorMessage,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    },
  });

  // Single account visibility toggle
  const toggleAccountMutation = useMutation({
    mutationFn: async ({ accountId, isActive }: { accountId: string; isActive: boolean }) => {
      await api.patch(`/accounts/${accountId}`, { is_active: isActive });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts-admin'] });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      queryClient.invalidateQueries({ queryKey: ['infinite-transactions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      toast({
        title: 'Account updated',
        status: 'success',
        duration: 3000,
      });
    },
    onError: () => {
      toast({
        title: 'Failed to update account',
        status: 'error',
        duration: 3000,
      });
    },
  });

  // Toggle exclude from cash flow
  const toggleCashFlowMutation = useMutation({
    mutationFn: async ({ accountId, excludeFromCashFlow }: { accountId: string; excludeFromCashFlow: boolean }) => {
      await api.patch(`/accounts/${accountId}`, { exclude_from_cash_flow: excludeFromCashFlow });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts-admin'] });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      queryClient.invalidateQueries({ queryKey: ['infinite-transactions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      toast({
        title: 'Account cash flow setting updated',
        status: 'success',
        duration: 3000,
      });
    },
    onError: () => {
      toast({
        title: 'Failed to update account',
        status: 'error',
        duration: 3000,
      });
    },
  });

  // Sync transactions mutation
  const syncTransactionsMutation = useMutation({
    mutationFn: async (plaidItemId: string) => {
      setSyncingItemId(plaidItemId);
      const response = await api.post(`/plaid/sync-transactions/${plaidItemId}`);
      return response.data;
    },
    onSuccess: (data, plaidItemId) => {
      queryClient.invalidateQueries({ queryKey: ['accounts-admin'] });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      queryClient.invalidateQueries({ queryKey: ['infinite-transactions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });

      const stats = data.stats;
      const message = stats
        ? `Synced: ${stats.added} added, ${stats.updated} updated, ${stats.skipped} skipped`
        : 'Transactions synced successfully';

      toast({
        title: 'Sync Complete',
        description: message,
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
      setSyncingItemId(null);
    },
    onError: (error: any, plaidItemId) => {
      const errorMessage = error?.response?.data?.detail || 'Failed to sync transactions';
      toast({
        title: 'Sync Failed',
        description: errorMessage,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
      setSyncingItemId(null);
    },
  });

  // Group accounts by institution
  const accountsByInstitution = useMemo(() => {
    if (!accounts) return {};

    return accounts.reduce((acc, account) => {
      const institution = account.institution_name || 'Other';
      if (!acc[institution]) {
        acc[institution] = [];
      }
      acc[institution].push(account);
      return acc;
    }, {} as Record<string, Account[]>);
  }, [accounts]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const formatLastSynced = (lastSyncedAt: string | null) => {
    if (!lastSyncedAt) return 'Never synced';

    const date = new Date(lastSyncedAt);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
    });
  };

  const handleSelectAccount = (accountId: string, checked: boolean) => {
    setSelectedAccounts((prev) => {
      const next = new Set(prev);
      if (checked) {
        next.add(accountId);
      } else {
        next.delete(accountId);
      }
      return next;
    });
  };

  const handleSelectAll = (accounts: Account[], checked: boolean) => {
    setSelectedAccounts((prev) => {
      const next = new Set(prev);
      accounts.forEach((account) => {
        if (checked) {
          next.add(account.id);
        } else {
          next.delete(account.id);
        }
      });
      return next;
    });
  };

  const allVisible = (accounts: Account[]) => {
    return accounts.every((a) => a.is_active);
  };

  const toggleInstitutionVisibility = (accounts: Account[]) => {
    const modifiableAccounts = accounts.filter(account => canModifyAccount(account));

    if (modifiableAccounts.length === 0) {
      toast({
        title: 'No accounts to modify',
        description: 'You do not have permission to modify these accounts',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    const shouldHide = allVisible(modifiableAccounts);
    visibilityMutation.mutate({
      accountIds: modifiableAccounts.map((a) => a.id),
      isActive: !shouldHide,
    });
  };

  const handleBulkHide = () => {
    const ownedAccountIds = Array.from(selectedAccounts).filter(accountId => {
      const account = accounts?.find(a => a.id === accountId);
      return account && canModifyAccount(account);
    });

    if (ownedAccountIds.length === 0) {
      toast({
        title: 'No accounts to modify',
        description: 'You do not have permission to modify these accounts',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    visibilityMutation.mutate({
      accountIds: ownedAccountIds,
      isActive: false,
    });
  };

  const handleBulkShow = () => {
    const ownedAccountIds = Array.from(selectedAccounts).filter(accountId => {
      const account = accounts?.find(a => a.id === accountId);
      return account && canModifyAccount(account);
    });

    if (ownedAccountIds.length === 0) {
      toast({
        title: 'No accounts to modify',
        description: 'You do not have permission to modify these accounts',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    visibilityMutation.mutate({
      accountIds: ownedAccountIds,
      isActive: true,
    });
  };

  const handleDeleteClick = (target: 'selected' | string) => {
    if (target !== 'selected') {
      // Single account deletion - check ownership
      const account = accounts?.find(a => a.id === target);
      if (account && !canModifyAccount(account)) {
        toast({
          title: 'Cannot delete account',
          description: 'You can only delete your own accounts',
          status: 'error',
          duration: 3000,
        });
        return;
      }
    }
    setDeleteTarget(target);
    onDeleteOpen();
  };

  const handleDeleteConfirm = () => {
    if (deleteTarget === 'selected') {
      // Filter to only accounts the user owns
      const ownedAccountIds = Array.from(selectedAccounts).filter(accountId => {
        const account = accounts?.find(a => a.id === accountId);
        return account && canModifyAccount(account);
      });

      if (ownedAccountIds.length === 0) {
        toast({
          title: 'No accounts to delete',
          description: 'You can only delete your own accounts',
          status: 'warning',
          duration: 3000,
        });
        onDeleteClose();
        return;
      }

      deleteMutation.mutate(ownedAccountIds);
    } else if (deleteTarget) {
      deleteMutation.mutate([deleteTarget]);
    }
  };

  if (isLoading) {
    return <AccountsSkeleton />;
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <HStack justify="space-between">
          <Box>
            <Heading size="lg">Accounts</Heading>
            <Text color="gray.600" fontSize="sm" mt={1}>
              Manage your accounts, visibility, and bulk operations
            </Text>
          </Box>
          {selectedAccounts.size > 0 && (
            <Menu>
              <MenuButton
                as={Button}
                rightIcon={<ChevronDownIcon />}
                colorScheme="brand"
                size="sm"
              >
                Bulk Actions ({selectedAccounts.size})
              </MenuButton>
              <MenuList>
                <MenuItem onClick={handleBulkHide}>Hide Selected</MenuItem>
                <MenuItem onClick={handleBulkShow}>Show Selected</MenuItem>
                <MenuItem color="red.600" onClick={() => handleDeleteClick('selected')}>
                  Delete Selected
                </MenuItem>
              </MenuList>
            </Menu>
          )}
        </HStack>

        {/* Accounts by Institution */}
        {Object.entries(accountsByInstitution).map(([institution, institutionAccounts]) => {
          // Get plaid_item_id if all accounts share the same one (Plaid-linked institution)
          const plaidItemId = institutionAccounts[0]?.plaid_item_id;
          const isPlaidLinked = plaidItemId && institutionAccounts.every(a => a.plaid_item_id === plaidItemId);
          const lastSynced = institutionAccounts[0]?.last_synced_at;
          const isSyncing = syncingItemId === plaidItemId;

          // Check if any accounts have errors
          const hasError = institutionAccounts.some(a => a.last_error_code || a.needs_reauth);
          const errorAccount = institutionAccounts.find(a => a.last_error_code || a.needs_reauth);

          return (
            <Card key={institution}>
              <CardHeader>
                <HStack justify="space-between" align="center">
                  <Box flex={1}>
                    <HStack spacing={2} align="center">
                      <Heading size="md">{institution}</Heading>
                      {hasError && (
                        <Tooltip label={errorAccount?.last_error_message || 'Connection issue - check account status'}>
                          <Badge colorScheme="red" fontSize="xs">
                            <HStack spacing={1}>
                              <Icon as={FiAlertTriangle} />
                              <Text>Issue</Text>
                            </HStack>
                          </Badge>
                        </Tooltip>
                      )}
                    </HStack>
                    {isPlaidLinked && lastSynced && (
                      <Text fontSize="xs" color="gray.500" mt={1}>
                        Last synced: {formatLastSynced(lastSynced)}
                      </Text>
                    )}
                  </Box>
                  <HStack spacing={2}>
                    {isPlaidLinked && (
                      <IconButton
                        icon={<RepeatIcon />}
                        size="sm"
                        variant="ghost"
                        aria-label="Sync transactions"
                        onClick={() => syncTransactionsMutation.mutate(plaidItemId)}
                        isLoading={isSyncing}
                        isDisabled={isSyncing}
                      />
                    )}
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => toggleInstitutionVisibility(institutionAccounts)}
                    >
                      {allVisible(institutionAccounts.filter(canModifyAccount)) ? 'Hide All' : 'Show All'}
                    </Button>
                  </HStack>
                </HStack>
              </CardHeader>
            <CardBody pt={0}>
              <Table size="sm">
                <Thead>
                  <Tr>
                    <Th>
                      <Checkbox
                        isChecked={institutionAccounts.every((a) =>
                          selectedAccounts.has(a.id)
                        )}
                        isIndeterminate={
                          institutionAccounts.some((a) => selectedAccounts.has(a.id)) &&
                          !institutionAccounts.every((a) => selectedAccounts.has(a.id))
                        }
                        onChange={(e) =>
                          handleSelectAll(institutionAccounts, e.target.checked)
                        }
                      />
                    </Th>
                    <Th>Account Name</Th>
                    <Th>Type</Th>
                    <Th isNumeric>Balance</Th>
                    <Th>Status</Th>
                    <Th>Actions</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {institutionAccounts.map((account) => (
                    <Tr
                      key={account.id}
                      opacity={account.is_active ? 1 : 0.5}
                      bg={account.is_active ? 'white' : 'gray.50'}
                    >
                      <Td>
                        <Tooltip label={!canModifyAccount(account) ? 'No permission to modify this account' : ''}>
                          <Checkbox
                            isChecked={selectedAccounts.has(account.id)}
                            isDisabled={!canModifyAccount(account)}
                            onChange={(e) =>
                              handleSelectAccount(account.id, e.target.checked)
                            }
                          />
                        </Tooltip>
                      </Td>
                      <Td>
                        <VStack align="start" spacing={1}>
                          <HStack>
                            <Text fontWeight="medium">{account.name}</Text>
                            {(users?.length ?? 0) > 1 && userMap.get(account.user_id) && (
                              <Badge colorScheme={getUserColorScheme(account.user_id)} fontSize="xs">
                                {getUserDisplayName(userMap.get(account.user_id)!)}
                              </Badge>
                            )}
                          </HStack>
                          {account.mask && (
                            <Text fontSize="xs" color="gray.500">
                              •••• {account.mask}
                            </Text>
                          )}
                        </VStack>
                      </Td>
                      <Td>
                        <Text fontSize="sm">{formatAssetType(account.account_type)}</Text>
                      </Td>
                      <Td isNumeric>
                        <Text
                          fontWeight="semibold"
                          color={account.current_balance < 0 ? 'red.600' : 'inherit'}
                        >
                          {formatCurrency(account.current_balance)}
                        </Text>
                      </Td>
                      <Td>
                        <VStack align="start" spacing={1}>
                          <Badge colorScheme={account.is_active ? 'green' : 'gray'}>
                            {account.is_active ? 'Visible' : 'Hidden'}
                          </Badge>
                          {account.exclude_from_cash_flow && (
                            <Badge colorScheme="orange" fontSize="xs">
                              Excluded from Cash Flow
                            </Badge>
                          )}
                          {account.needs_reauth && (
                            <Tooltip label="Reconnect your account to resume syncing">
                              <Badge colorScheme="red" fontSize="xs">
                                <HStack spacing={1}>
                                  <Icon as={FiAlertTriangle} />
                                  <Text>Needs Reauth</Text>
                                </HStack>
                              </Badge>
                            </Tooltip>
                          )}
                          {account.last_error_code && (
                            <Tooltip label={account.last_error_message || 'Unknown error'}>
                              <Badge colorScheme="red" fontSize="xs" maxW="150px">
                                <HStack spacing={1}>
                                  <Icon as={FiAlertTriangle} />
                                  <Text isTruncated>Error: {account.last_error_code}</Text>
                                </HStack>
                              </Badge>
                            </Tooltip>
                          )}
                        </VStack>
                      </Td>
                      <Td>
                        <HStack spacing={2}>
                          <Tooltip label={!canModifyAccount(account) ? 'No permission to modify this account' : (account.is_active ? 'Hide account from everywhere' : 'Show account everywhere')}>
                            <IconButton
                              icon={account.is_active ? <ViewOffIcon /> : <ViewIcon />}
                              size="sm"
                              variant="ghost"
                              aria-label={account.is_active ? 'Hide account' : 'Show account'}
                              isDisabled={!canModifyAccount(account)}
                              onClick={() =>
                                toggleAccountMutation.mutate({
                                  accountId: account.id,
                                  isActive: !account.is_active,
                                })
                              }
                            />
                          </Tooltip>
                          <Tooltip label={!canModifyAccount(account) ? 'No permission to modify this account' : (account.exclude_from_cash_flow ? 'Include in budgets & cash flow' : 'Exclude from budgets & cash flow')}>
                            <IconButton
                              icon={<Icon as={account.exclude_from_cash_flow ? FiTrendingDown : FiTrendingUp} />}
                              size="sm"
                              variant="ghost"
                              colorScheme={account.exclude_from_cash_flow ? 'orange' : 'green'}
                              aria-label={account.exclude_from_cash_flow ? 'Include in cash flow' : 'Exclude from cash flow'}
                              isDisabled={!canModifyAccount(account)}
                              onClick={() =>
                                toggleCashFlowMutation.mutate({
                                  accountId: account.id,
                                  excludeFromCashFlow: !account.exclude_from_cash_flow,
                                })
                              }
                            />
                          </Tooltip>
                          <Tooltip label={!canModifyAccount(account) ? 'No permission to modify this account' : 'Edit account details'}>
                            <IconButton
                              icon={<EditIcon />}
                              size="sm"
                              variant="ghost"
                              aria-label="Edit account"
                              isDisabled={!canModifyAccount(account)}
                              onClick={() => navigate(`/accounts/${account.id}${selectedUserId ? `?user=${selectedUserId}` : ''}`)}
                            />
                          </Tooltip>
                          <Tooltip label={!canModifyAccount(account) ? 'No permission to modify this account' : 'Delete account permanently'}>
                            <IconButton
                              icon={<DeleteIcon />}
                              size="sm"
                              variant="ghost"
                              colorScheme="red"
                              aria-label="Delete account"
                              isDisabled={!canModifyAccount(account)}
                              onClick={() => handleDeleteClick(account.id)}
                            />
                          </Tooltip>
                        </HStack>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </CardBody>
          </Card>
          );
        })}

        {(!accounts || accounts.length === 0) && (
          <EmptyState
            icon={FiCreditCard}
            title="No accounts yet"
            description="Connect your bank accounts or add manual accounts to start tracking your finances."
            actionLabel="Add Account"
            onAction={() => {/* TODO: Open add account modal */}}
            showAction={false}
          />
        )}
      </VStack>

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        isOpen={isDeleteOpen}
        leastDestructiveRef={cancelRef}
        onClose={onDeleteClose}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              Delete Account{deleteTarget === 'selected' && selectedAccounts.size > 1 ? 's' : ''}
            </AlertDialogHeader>

            <AlertDialogBody>
              Are you sure? This will permanently delete{' '}
              {deleteTarget === 'selected'
                ? `${selectedAccounts.size} account${selectedAccounts.size > 1 ? 's' : ''}`
                : 'this account'}{' '}
              and all associated data. This action cannot be undone.
            </AlertDialogBody>

            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={onDeleteClose}>
                Cancel
              </Button>
              <Button colorScheme="red" onClick={handleDeleteConfirm} ml={3}>
                Delete
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </Container>
  );
};

export default AccountsPage;
