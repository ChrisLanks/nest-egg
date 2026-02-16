/**
 * Account detail page with settings and transactions
 */

import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Button,
  Card,
  CardBody,
  Select,
  Switch,
  FormControl,
  FormLabel,
  Divider,
  Spinner,
  Center,
  useToast,
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
  useDisclosure,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Input,
  NumberInput,
  NumberInputField,
  IconButton,
  Tooltip,
} from '@chakra-ui/react';
import { FiEdit2, FiCheck, FiX, FiLock, FiRefreshCw } from 'react-icons/fi';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';
import api from '../services/api';
import { useAuthStore } from '../features/auth/stores/authStore';
import { useUserView } from '../contexts/UserViewContext';
import type { Transaction } from '../types/transaction';
import { ContributionsManager } from '../features/accounts/components/ContributionsManager';

interface Account {
  id: string;
  user_id: string;
  name: string;
  account_type: string;
  account_source: string;
  current_balance: number;
  balance_as_of: string | null;
  institution_name: string | null;
  mask: string | null;
  is_active: boolean;
  exclude_from_cash_flow: boolean;
  plaid_item_hash: string | null;
  plaid_item_id: string | null;
  // Sync status
  last_synced_at: string | null;
  last_error_code: string | null;
  last_error_message: string | null;
  needs_reauth: boolean | null;
}

const accountTypeLabels: Record<string, string> = {
  checking: 'Checking',
  savings: 'Savings',
  credit_card: 'Credit Card',
  brokerage: 'Brokerage',
  retirement_401k: '401(k)',
  retirement_ira: 'IRA',
  retirement_roth: 'Roth IRA',
  hsa: 'HSA',
  loan: 'Loan',
  mortgage: 'Mortgage',
  property: 'Property',
  vehicle: 'Vehicle',
  crypto: 'Crypto',
  manual: 'Manual',
  other: 'Other',
};

export const AccountDetailPage = () => {
  const { accountId } = useParams<{ accountId: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const { isOtherUserView, canEdit } = useUserView();
  const [searchParams] = useSearchParams();
  const selectedUserId = searchParams.get('user');
  const isCombinedView = !selectedUserId;
  const { isOpen: isDeleteOpen, onOpen: onDeleteOpen, onClose: onDeleteClose } = useDisclosure();
  const cancelRef = useRef<HTMLButtonElement>(null);
  const [transactionsCursor, setTransactionsCursor] = useState<string | null>(null);
  const [vehicleMileage, setVehicleMileage] = useState('');
  const [vehicleValue, setVehicleValue] = useState('');
  const [isEditingName, setIsEditingName] = useState(false);
  const [editedName, setEditedName] = useState('');

  // Fetch account details
  const { data: account, isLoading } = useQuery<Account>({
    queryKey: ['account', accountId],
    queryFn: async () => {
      const response = await api.get(`/accounts/${accountId}`);
      return response.data;
    },
  });

  // Fetch all accounts to check if this account is shared (only in combined view)
  const { data: allAccounts } = useQuery<Account[]>({
    queryKey: ['accounts-check-shared', accountId],
    queryFn: async () => {
      const response = await api.get('/accounts');
      return response.data;
    },
    enabled: isCombinedView && !!account?.plaid_item_hash,
  });

  // Fetch transactions for this account
  const { data: transactionsData, isLoading: transactionsLoading } = useQuery({
    queryKey: ['transactions', accountId, transactionsCursor],
    queryFn: async () => {
      const params = new URLSearchParams({
        account_id: accountId!,
        page_size: '50',
      });
      if (transactionsCursor) {
        params.append('cursor', transactionsCursor);
      }
      const response = await api.get(`/transactions/?${params.toString()}`);
      return response.data;
    },
    enabled: !!accountId,
  });

  // Update account mutation
  const updateAccountMutation = useMutation({
    mutationFn: async (data: { name?: string; account_type?: string; is_active?: boolean; exclude_from_cash_flow?: boolean }) => {
      const response = await api.patch(`/accounts/${accountId}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['account', accountId] });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      queryClient.invalidateQueries({ queryKey: ['accounts-admin'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio-summary'] });
      toast({
        title: 'Account updated',
        status: 'success',
        duration: 3000,
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to update account',
        description: error.response?.data?.detail || 'An error occurred',
        status: 'error',
        duration: 5000,
      });
    },
  });

  // Delete account mutation
  const deleteAccountMutation = useMutation({
    mutationFn: async () => {
      await api.delete(`/accounts/${accountId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      queryClient.invalidateQueries({ queryKey: ['accounts-admin'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      queryClient.invalidateQueries({ queryKey: ['infinite-transactions'] });
      toast({
        title: 'Account deleted',
        status: 'success',
        duration: 3000,
      });
      navigate('/dashboard');
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to delete account',
        description: error.response?.data?.detail || 'An error occurred',
        status: 'error',
        duration: 5000,
      });
    },
  });

  // Update vehicle details mutation
  const updateVehicleMutation = useMutation({
    mutationFn: async (data: { mileage?: number; balance?: number }) => {
      const payload: any = {};
      if (data.mileage !== undefined) {
        // Store mileage in mask field for now
        payload.mask = data.mileage.toString();
      }
      if (data.balance !== undefined) {
        payload.current_balance = data.balance;
      }
      const response = await api.patch(`/accounts/${accountId}`, payload);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['account', accountId] });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      toast({
        title: 'Vehicle details updated',
        status: 'success',
        duration: 3000,
      });
      setVehicleMileage('');
      setVehicleValue('');
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to update vehicle',
        description: error.response?.data?.detail || 'An error occurred',
        status: 'error',
        duration: 5000,
      });
    },
  });

  // Sync transactions mutation
  const syncTransactionsMutation = useMutation({
    mutationFn: async (plaidItemId: string) => {
      const response = await api.post(`/plaid/sync-transactions/${plaidItemId}`);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['account', accountId] });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      queryClient.invalidateQueries({ queryKey: ['accounts-admin'] });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
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
    },
    onError: (error: any) => {
      const errorMessage = error?.response?.data?.detail || 'Failed to sync transactions';
      toast({
        title: 'Sync Failed',
        description: errorMessage,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    },
  });

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: 'numeric',
    });
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

  const handleReclassify = (newType: string) => {
    updateAccountMutation.mutate({ account_type: newType });
  };

  const handleToggleActive = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (account) {
      // Switch is "Hide from reports", so when checked (true), we want is_active=false
      const hideFromReports = e.target.checked;
      updateAccountMutation.mutate({ is_active: !hideFromReports });
    }
  };

  const handleToggleExcludeFromCashFlow = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (account) {
      updateAccountMutation.mutate({ exclude_from_cash_flow: e.target.checked });
    }
  };

  const handleDelete = () => {
    deleteAccountMutation.mutate();
    onDeleteClose();
  };

  const handleUpdateVehicle = () => {
    const updates: { mileage?: number; balance?: number } = {};

    if (vehicleMileage) {
      const mileage = parseInt(vehicleMileage);
      if (!isNaN(mileage) && mileage >= 0) {
        updates.mileage = mileage;
      }
    }

    if (vehicleValue) {
      const value = parseFloat(vehicleValue);
      if (!isNaN(value) && value >= 0) {
        updates.balance = value;
      }
    }

    if (Object.keys(updates).length > 0) {
      updateVehicleMutation.mutate(updates);
    }
  };

  const handleStartEditName = () => {
    if (account) {
      setEditedName(account.name);
      setIsEditingName(true);
    }
  };

  const handleSaveName = () => {
    if (editedName && editedName !== account?.name) {
      updateAccountMutation.mutate({ name: editedName });
    }
    setIsEditingName(false);
  };

  const handleCancelEditName = () => {
    setIsEditingName(false);
    setEditedName('');
  };

  if (isLoading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" color="brand.500" />
      </Center>
    );
  }

  if (!account) {
    return (
      <Container maxW="container.lg" py={8}>
        <Text>Account not found</Text>
      </Container>
    );
  }

  const balance = Number(account.current_balance);
  const isNegative = balance < 0;

  // Check if this account is shared (multiple household members have linked it)
  const isSharedAccount = isCombinedView && account.plaid_item_hash && allAccounts
    ? allAccounts.filter(acc =>
        acc.plaid_item_hash === account.plaid_item_hash &&
        acc.plaid_item_hash !== null
      ).length > 1
    : false;

  // Check if current user owns this account
  const isOwner = account.user_id === user?.id;

  // Disable editing if:
  // 1. User doesn't have edit permission, OR
  // 2. User doesn't own the account, OR
  // 3. Account is shared AND in combined view (multi accounts can only be edited in individual views)
  const canEditAccount = canEdit && isOwner && !isSharedAccount;

  return (
    <Container maxW="container.lg" py={8}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <HStack justify="space-between">
          <Box>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate(-1)}
              mb={2}
            >
              ← Back
            </Button>
            {isEditingName ? (
              <HStack spacing={2} mb={1}>
                <Input
                  value={editedName}
                  onChange={(e) => setEditedName(e.target.value)}
                  size="lg"
                  fontSize="2xl"
                  fontWeight="bold"
                  maxW="400px"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleSaveName();
                    } else if (e.key === 'Escape') {
                      handleCancelEditName();
                    }
                  }}
                />
                <IconButton
                  aria-label="Save name"
                  icon={<FiCheck />}
                  colorScheme="green"
                  size="sm"
                  onClick={handleSaveName}
                  isLoading={updateAccountMutation.isPending}
                />
                <IconButton
                  aria-label="Cancel"
                  icon={<FiX />}
                  size="sm"
                  onClick={handleCancelEditName}
                  isDisabled={updateAccountMutation.isPending}
                />
              </HStack>
            ) : (
              <HStack spacing={2}>
                <Heading size="lg">{account.name}</Heading>
                {!canEditAccount ? (
                  <Tooltip
                    label={
                      isSharedAccount
                        ? "Read-only: Shared accounts can only be edited in individual user views"
                        : "Read-only: This account belongs to another household member"
                    }
                    placement="top"
                  >
                    <Badge colorScheme="gray" display="flex" alignItems="center" gap={1}>
                      <FiLock size={12} /> Read-only
                    </Badge>
                  </Tooltip>
                ) : (
                  <Tooltip label="Edit account name" placement="top">
                    <IconButton
                      aria-label="Edit account name"
                      icon={<FiEdit2 />}
                      size="sm"
                      variant="ghost"
                      onClick={handleStartEditName}
                    />
                  </Tooltip>
                )}
              </HStack>
            )}
            <Text color="gray.600" mt={1}>
              {accountTypeLabels[account.account_type] || account.account_type}
              {account.mask && account.account_type !== 'vehicle' && ` ••${account.mask}`}
            </Text>
          </Box>
          <Box textAlign="right">
            <Text fontSize="sm" color="gray.600">
              Current Balance
            </Text>
            <Text
              fontSize="3xl"
              fontWeight="bold"
              color={isNegative ? 'red.600' : 'brand.600'}
            >
              {formatCurrency(balance)}
            </Text>
            <Text fontSize="xs" color="gray.500">
              Updated: {formatDate(account.balance_as_of)}
            </Text>
          </Box>
        </HStack>

        <Divider />

        {/* Account Settings */}
        <Card>
          <CardBody>
            <Heading size="md" mb={4}>
              Account Settings
            </Heading>
            <VStack spacing={4} align="stretch">
              {/* Reclassify Account */}
              <FormControl>
                <FormLabel fontSize="sm">Account Type</FormLabel>
                <Tooltip
                  label={!canEditAccount ? "You can only edit your own accounts" : ""}
                  placement="top"
                  isDisabled={canEditAccount}
                >
                  <Select
                    value={account.account_type}
                    onChange={(e) => handleReclassify(e.target.value)}
                    size="sm"
                    isDisabled={!canEditAccount}
                  >
                    {Object.entries(accountTypeLabels).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </Select>
                </Tooltip>
              </FormControl>

              {/* Hide from Reports */}
              <FormControl display="flex" alignItems="center">
                <FormLabel fontSize="sm" mb={0} flex={1}>
                  Hide from all reports
                </FormLabel>
                <Tooltip
                  label={!canEditAccount ? "You can only edit your own accounts" : ""}
                  placement="top"
                  isDisabled={canEditAccount}
                >
                  <Switch
                    isChecked={!account.is_active}
                    onChange={handleToggleActive}
                    colorScheme="brand"
                    isDisabled={!canEditAccount}
                  />
                </Tooltip>
              </FormControl>

              {/* Exclude from Cash Flow */}
              <FormControl display="flex" alignItems="center">
                <Box flex={1}>
                  <FormLabel fontSize="sm" mb={0}>
                    Exclude from cash flow
                  </FormLabel>
                  <Text fontSize="xs" color="gray.500" mt={0.5}>
                    Prevents double-counting (e.g., mortgage payments already tracked in checking account)
                  </Text>
                </Box>
                <Tooltip
                  label={!canEditAccount ? "You can only edit your own accounts" : ""}
                  placement="top"
                  isDisabled={canEditAccount}
                >
                  <Switch
                    isChecked={account.exclude_from_cash_flow}
                    onChange={handleToggleExcludeFromCashFlow}
                    colorScheme="brand"
                    isDisabled={!canEditAccount}
                  />
                </Tooltip>
              </FormControl>

              {/* Account Info */}
              <Box>
                <Text fontSize="sm" fontWeight="medium" color="gray.600">
                  Account Source
                </Text>
                <Text fontSize="sm">
                  {account.account_source.toUpperCase()}
                  {account.institution_name && ` - ${account.institution_name}`}
                </Text>
              </Box>

              {/* Sync Status - Only for Plaid accounts */}
              {account.plaid_item_id && (
                <Box>
                  <HStack justify="space-between" mb={2}>
                    <Text fontSize="sm" fontWeight="medium" color="gray.600">
                      Sync Status
                    </Text>
                    <Tooltip label="Refresh transactions from bank" placement="top">
                      <IconButton
                        icon={<FiRefreshCw />}
                        size="xs"
                        variant="ghost"
                        aria-label="Sync transactions"
                        onClick={() => syncTransactionsMutation.mutate(account.plaid_item_id!)}
                        isLoading={syncTransactionsMutation.isPending}
                        isDisabled={syncTransactionsMutation.isPending}
                      />
                    </Tooltip>
                  </HStack>
                  <VStack align="stretch" spacing={1}>
                    <HStack>
                      <Text fontSize="sm" color="gray.600">Last synced:</Text>
                      <Text fontSize="sm" fontWeight="medium">
                        {formatLastSynced(account.last_synced_at)}
                      </Text>
                    </HStack>
                    {(account.last_error_code || account.needs_reauth) && (
                      <HStack>
                        <Badge colorScheme={account.needs_reauth ? 'orange' : 'red'} fontSize="xs">
                          {account.needs_reauth ? 'Reauthentication Required' : 'Sync Error'}
                        </Badge>
                        {account.last_error_message && (
                          <Tooltip label={account.last_error_message} placement="top">
                            <Text fontSize="xs" color="gray.600" noOfLines={1}>
                              {account.last_error_message}
                            </Text>
                          </Tooltip>
                        )}
                      </HStack>
                    )}
                  </VStack>
                </Box>
              )}

              <Divider />

              {/* Delete Account */}
              <Box>
                <Tooltip
                  label={!canEditAccount ? "You can only delete your own accounts" : ""}
                  placement="top"
                  isDisabled={canEditAccount}
                >
                  <Button
                    colorScheme="red"
                    variant="outline"
                    size="sm"
                    onClick={onDeleteOpen}
                    isDisabled={!canEditAccount}
                  >
                    Close Account
                  </Button>
                </Tooltip>
                <Text fontSize="xs" color="gray.500" mt={1}>
                  This will permanently delete this account and all associated transactions.
                </Text>
              </Box>
            </VStack>
          </CardBody>
        </Card>

        {/* Vehicle Details Section - Only for vehicle accounts */}
        {account.account_type === 'vehicle' && (
          <Card>
            <CardBody>
              <Heading size="md" mb={4}>
                Vehicle Details
              </Heading>
              <VStack spacing={4} align="stretch">
                {/* Current Mileage Display */}
                <Box>
                  <Text fontSize="sm" fontWeight="medium" color="gray.600">
                    Current Mileage
                  </Text>
                  <Text fontSize="lg" fontWeight="semibold">
                    {account.mask ? `${parseInt(account.mask).toLocaleString()} miles` : 'Not set'}
                  </Text>
                </Box>

                <Divider />

                {!canEditAccount ? (
                  <Text fontSize="sm" color="gray.600">
                    Vehicle details can only be updated by the account owner.
                  </Text>
                ) : (
                  <>
                    {/* Update Mileage */}
                    <FormControl>
                      <FormLabel fontSize="sm">Update Mileage</FormLabel>
                      <HStack>
                        <NumberInput
                          value={vehicleMileage}
                          onChange={setVehicleMileage}
                          min={0}
                          size="sm"
                        >
                          <NumberInputField placeholder="Enter new mileage" />
                        </NumberInput>
                        <Text fontSize="sm" color="gray.600">
                          miles
                        </Text>
                      </HStack>
                    </FormControl>

                    {/* Update Value */}
                    <FormControl>
                      <FormLabel fontSize="sm">Update Vehicle Value</FormLabel>
                      <HStack>
                        <Text fontSize="sm">$</Text>
                        <NumberInput
                          value={vehicleValue}
                          onChange={setVehicleValue}
                          min={0}
                          precision={2}
                          size="sm"
                        >
                          <NumberInputField placeholder="Enter new value" />
                        </NumberInput>
                      </HStack>
                    </FormControl>

                    {/* Save Button */}
                    <Button
                      colorScheme="brand"
                      size="sm"
                      onClick={handleUpdateVehicle}
                      isLoading={updateVehicleMutation.isPending}
                      isDisabled={!vehicleMileage && !vehicleValue}
                    >
                      Save Updates
                    </Button>
                  </>
                )}
              </VStack>
            </CardBody>
          </Card>
        )}

        {/* Recurring Contributions Section - Only for manual accounts */}
        {account.account_source === 'manual' && (
          <Card>
            <CardBody>
              {canEditAccount ? (
                <ContributionsManager accountId={account.id} accountName={account.name} />
              ) : (
                <Box>
                  <Heading size="md" mb={2}>Recurring Contributions</Heading>
                  <Text fontSize="sm" color="gray.600">
                    Contributions can only be managed by the account owner.
                  </Text>
                </Box>
              )}
            </CardBody>
          </Card>
        )}

        {/* Transactions Section */}
        <Card>
          <CardBody>
            <HStack justify="space-between" mb={4}>
              <Heading size="md">Transactions</Heading>
              {transactionsData && transactionsData.total > 0 && (
                <Text fontSize="sm" color="gray.600">
                  Showing {transactionsData.transactions?.length || 0} of {transactionsData.total}
                </Text>
              )}
            </HStack>

            {transactionsLoading ? (
              <Center py={8}>
                <Spinner size="md" color="brand.500" />
              </Center>
            ) : transactionsData?.transactions && transactionsData.transactions.length > 0 ? (
              <>
                <Table variant="simple" size="sm">
                  <Thead>
                    <Tr>
                      <Th>Date</Th>
                      <Th>Merchant</Th>
                      <Th>Category</Th>
                      <Th isNumeric>Amount</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {transactionsData.transactions.map((txn: Transaction) => {
                      const amount = Number(txn.amount);
                      const isNegative = amount < 0;

                      return (
                        <Tr key={txn.id}>
                          <Td>
                            <Text fontSize="sm">
                              {new Date(txn.date).toLocaleDateString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                year: 'numeric',
                              })}
                            </Text>
                          </Td>
                          <Td>
                            <VStack align="start" spacing={0}>
                              <Text fontSize="sm" fontWeight="medium">
                                {txn.merchant_name || 'Unknown'}
                              </Text>
                              {txn.is_pending && (
                                <Badge colorScheme="orange" size="sm">
                                  Pending
                                </Badge>
                              )}
                            </VStack>
                          </Td>
                          <Td>
                            {txn.category_primary && (
                              <Badge colorScheme="blue" size="sm">
                                {txn.category_primary}
                              </Badge>
                            )}
                          </Td>
                          <Td isNumeric>
                            <Text
                              fontSize="sm"
                              fontWeight="semibold"
                              color={isNegative ? 'red.600' : 'green.600'}
                            >
                              {isNegative ? '-' : '+'}
                              {formatCurrency(Math.abs(amount))}
                            </Text>
                          </Td>
                        </Tr>
                      );
                    })}
                  </Tbody>
                </Table>

                {transactionsData.has_more && transactionsData.next_cursor && (
                  <Button
                    size="sm"
                    variant="outline"
                    mt={4}
                    onClick={() => setTransactionsCursor(transactionsData.next_cursor)}
                    width="full"
                  >
                    Load More
                  </Button>
                )}
              </>
            ) : (
              <Text color="gray.500" fontSize="sm" textAlign="center" py={8}>
                No transactions found for this account.
              </Text>
            )}
          </CardBody>
        </Card>
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
              Close Account
            </AlertDialogHeader>

            <AlertDialogBody>
              Are you sure you want to close "{account.name}"? This will permanently
              delete the account and all associated transactions. This action cannot be
              undone.
            </AlertDialogBody>

            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={onDeleteClose}>
                Cancel
              </Button>
              <Button
                colorScheme="red"
                onClick={handleDelete}
                ml={3}
                isLoading={deleteAccountMutation.isPending}
              >
                Delete
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </Container>
  );
};
