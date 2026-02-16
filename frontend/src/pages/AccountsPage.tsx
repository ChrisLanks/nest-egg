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
} from '@chakra-ui/react';
import { useState, useMemo, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ViewIcon, ViewOffIcon, EditIcon, DeleteIcon, ChevronDownIcon, RepeatIcon } from '@chakra-ui/icons';
import { useNavigate } from 'react-router-dom';
import { FiCreditCard } from 'react-icons/fi';
import api from '../services/api';
import { formatAssetType } from '../utils/formatAssetType';
import { EmptyState } from '../components/EmptyState';

interface Account {
  id: string;
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

  // Fetch all accounts (ALWAYS include hidden - this is the admin page)
  const { data: accounts, isLoading } = useQuery({
    queryKey: ['accounts-admin', 'include-hidden'],
    queryFn: async () => {
      const response = await api.get<Account[]>('/accounts', {
        params: { include_hidden: true }
      });
      return response.data;
    },
  });

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
      await api.patch('/accounts/bulk-visibility', {
        account_ids: accountIds,
        is_active: isActive,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts-admin'] });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      queryClient.invalidateQueries({ queryKey: ['infinite-transactions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      toast({
        title: 'Account visibility updated',
        status: 'success',
        duration: 3000,
      });
      setSelectedAccounts(new Set());
    },
    onError: () => {
      toast({
        title: 'Failed to update visibility',
        status: 'error',
        duration: 3000,
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
    const shouldHide = allVisible(accounts);
    const accountIds = accounts.map((a) => a.id);
    visibilityMutation.mutate({ accountIds, isActive: !shouldHide });
  };

  const handleBulkHide = () => {
    visibilityMutation.mutate({
      accountIds: Array.from(selectedAccounts),
      isActive: false,
    });
  };

  const handleBulkShow = () => {
    visibilityMutation.mutate({
      accountIds: Array.from(selectedAccounts),
      isActive: true,
    });
  };

  const handleDeleteClick = (target: 'selected' | string) => {
    setDeleteTarget(target);
    onDeleteOpen();
  };

  const handleDeleteConfirm = () => {
    if (deleteTarget === 'selected') {
      deleteMutation.mutate(Array.from(selectedAccounts));
    } else if (deleteTarget) {
      deleteMutation.mutate([deleteTarget]);
    }
  };

  if (isLoading) {
    return (
      <Center h="50vh">
        <Spinner size="xl" color="brand.500" />
      </Center>
    );
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

          return (
            <Card key={institution}>
              <CardHeader>
                <HStack justify="space-between" align="center">
                  <Box>
                    <Heading size="md">{institution}</Heading>
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
                      {allVisible(institutionAccounts) ? 'Hide All' : 'Show All'}
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
                        <Checkbox
                          isChecked={selectedAccounts.has(account.id)}
                          onChange={(e) =>
                            handleSelectAccount(account.id, e.target.checked)
                          }
                        />
                      </Td>
                      <Td>
                        <VStack align="start" spacing={0}>
                          <Text fontWeight="medium">{account.name}</Text>
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
                        </VStack>
                      </Td>
                      <Td>
                        <HStack spacing={2}>
                          <IconButton
                            icon={account.is_active ? <ViewOffIcon /> : <ViewIcon />}
                            size="sm"
                            variant="ghost"
                            aria-label={account.is_active ? 'Hide account' : 'Show account'}
                            onClick={() =>
                              toggleAccountMutation.mutate({
                                accountId: account.id,
                                isActive: !account.is_active,
                              })
                            }
                          />
                          <IconButton
                            icon={<EditIcon />}
                            size="sm"
                            variant="ghost"
                            aria-label="Edit account"
                            onClick={() => navigate(`/accounts/${account.id}`)}
                          />
                          <IconButton
                            icon={<DeleteIcon />}
                            size="sm"
                            variant="ghost"
                            colorScheme="red"
                            aria-label="Delete account"
                            onClick={() => handleDeleteClick(account.id)}
                          />
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
