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
import { FiEdit2, FiCheck, FiX, FiLock, FiRefreshCw, FiTrash2 } from 'react-icons/fi';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';
import api from '../services/api';
import { useAuthStore } from '../features/auth/stores/authStore';
import { useUserView } from '../contexts/UserViewContext';
import type { Transaction } from '../types/transaction';
import { ContributionsManager } from '../features/accounts/components/ContributionsManager';
import { AddTransactionModal } from '../features/accounts/components/AddTransactionModal';
import { AddHoldingModal } from '../features/accounts/components/AddHoldingModal';
import { holdingsApi, type Holding } from '../api/holdings';

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
  include_in_networth: boolean | null;
  plaid_item_hash: string | null;
  plaid_item_id: string | null;
  // Loan/mortgage fields
  interest_rate: number | null;
  loan_term_months: number | null;
  origination_date: string | null;
  minimum_payment: number | null;
  // Property auto-valuation fields
  property_address: string | null;
  property_zip: string | null;
  // Vehicle auto-valuation fields
  vehicle_vin: string | null;
  vehicle_mileage: number | null;
  last_auto_valued_at: string | null;
  // Employer match fields (401k / 403b)
  employer_match_percent: number | null;
  employer_match_limit_percent: number | null;
  annual_salary: number | null;
  // Sync status
  last_synced_at: string | null;
  last_error_code: string | null;
  last_error_message: string | null;
  needs_reauth: boolean | null;
}

const LOAN_ACCOUNT_TYPES = ['mortgage', 'loan', 'student_loan'];

/** Asset accounts track a value, not a transaction flow. */
const ASSET_ACCOUNT_TYPES = [
  'property', 'vehicle', 'collectibles', 'precious_metals',
  'business_equity', 'private_equity', 'private_debt', 'bond',
  'life_insurance_cash_value', 'pension', 'annuity',
];

/** Manual accounts that make sense to schedule recurring contributions for. */
const CONTRIBUTION_ACCOUNT_TYPES = [
  'savings', 'brokerage', 'retirement_401k', 'retirement_ira',
  'retirement_roth', 'retirement_529', 'hsa',
];

/** Debt account types — can update balance directly when manual. */
const DEBT_ACCOUNT_TYPES = ['credit_card', 'loan', 'student_loan', 'mortgage'];

/** Investment account types that support individual holdings (including crypto coins). */
const HOLDINGS_ACCOUNT_TYPES = [
  'brokerage', 'retirement_401k', 'retirement_ira', 'retirement_roth',
  'retirement_529', 'hsa', 'crypto',
];

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
  const { isOtherUserView, canWriteResource } = useUserView();
  const canEdit = canWriteResource('account');
  const [searchParams] = useSearchParams();
  const selectedUserId = searchParams.get('user');
  const isCombinedView = !selectedUserId;
  const { isOpen: isDeleteOpen, onOpen: onDeleteOpen, onClose: onDeleteClose } = useDisclosure();
  const { isOpen: isAddTxnOpen, onOpen: onAddTxnOpen, onClose: onAddTxnClose } = useDisclosure();
  const { isOpen: isAddHoldingOpen, onOpen: onAddHoldingOpen, onClose: onAddHoldingClose } = useDisclosure();
  const cancelRef = useRef<HTMLButtonElement>(null);
  const [transactionsCursor, setTransactionsCursor] = useState<string | null>(null);
  const [vehicleMileage, setVehicleMileage] = useState('');
  const [vehicleValue, setVehicleValue] = useState('');
  const [vehicleVin, setVehicleVin] = useState('');
  const [propertyAddress, setPropertyAddress] = useState('');
  const [propertyZip, setPropertyZip] = useState('');
  const [manualBalance, setManualBalance] = useState('');
  const [debtBalance, setDebtBalance] = useState('');
  const [isEditingName, setIsEditingName] = useState(false);
  const [editedName, setEditedName] = useState('');
  // Loan detail editing state
  const [loanInterestRate, setLoanInterestRate] = useState('');
  const [loanTermYears, setLoanTermYears] = useState('');
  const [loanOriginationDate, setLoanOriginationDate] = useState('');
  // Employer match editing state
  const [empMatchPct, setEmpMatchPct] = useState('');
  const [empMatchLimitPct, setEmpMatchLimitPct] = useState('');
  const [empAnnualSalary, setEmpAnnualSalary] = useState('');

  // Fetch account details
  const { data: account, isLoading } = useQuery<Account>({
    queryKey: ['account', accountId],
    queryFn: async () => {
      const response = await api.get(`/accounts/${accountId}`);
      return response.data;
    },
  });

  const isPropertyOrVehicle = account?.account_type === 'property' || account?.account_type === 'vehicle';

  // Fetch available valuation providers (only for property/vehicle accounts)
  const { data: valuationProviders } = useQuery<{ property: string[]; vehicle: string[] }>({
    queryKey: ['valuation-providers'],
    queryFn: async () => {
      const response = await api.get('/accounts/valuation-providers');
      return response.data;
    },
    enabled: isPropertyOrVehicle,
    staleTime: 5 * 60 * 1000, // provider config changes rarely
  });

  const availableProviders = account?.account_type === 'property'
    ? (valuationProviders?.property ?? [])
    : (valuationProviders?.vehicle ?? []);
  const [selectedProvider, setSelectedProvider] = useState<string>('');

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
    enabled: !!accountId && !ASSET_ACCOUNT_TYPES.includes(account?.account_type ?? ''),
  });

  // Fetch holdings for investment accounts
  const { data: accountHoldings } = useQuery<Holding[]>({
    queryKey: ['holdings', accountId],
    queryFn: () => holdingsApi.getAccountHoldings(accountId!),
    enabled: !!accountId && HOLDINGS_ACCOUNT_TYPES.includes(account?.account_type ?? ''),
  });

  // Update account mutation
  const updateAccountMutation = useMutation({
    mutationFn: async (data: { name?: string; account_type?: string; is_active?: boolean; exclude_from_cash_flow?: boolean; include_in_networth?: boolean | null; interest_rate?: number | null; loan_term_months?: number | null; origination_date?: string | null; current_balance?: number; employer_match_percent?: number | null; employer_match_limit_percent?: number | null; annual_salary?: number | null; property_address?: string | null; property_zip?: string | null; vehicle_vin?: string | null; vehicle_mileage?: number | null }) => {
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
    mutationFn: async (data: { mileage?: number; balance?: number; vin?: string }) => {
      const payload: any = {};
      if (data.mileage !== undefined) payload.vehicle_mileage = data.mileage;
      if (data.vin !== undefined) payload.vehicle_vin = data.vin.toUpperCase();
      if (data.balance !== undefined) payload.current_balance = data.balance;
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
      setVehicleVin('');
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

  // Refresh auto-valuation mutation (property + vehicle)
  const refreshValuationMutation = useMutation({
    mutationFn: async () => {
      const params = selectedProvider ? `?provider=${selectedProvider}` : '';
      const response = await api.post(`/accounts/${accountId}/refresh-valuation${params}`);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['account', accountId] });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      const fmt = (v: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(v);
      const rangeStr = data.low && data.high ? ` (range ${fmt(data.low)} – ${fmt(data.high)})` : '';
      const vinInfo = data.vin_info ? ` · ${data.vin_info.year} ${data.vin_info.make} ${data.vin_info.model}` : '';
      const providerLabel = data.provider ? ` via ${data.provider}` : '';
      toast({
        title: 'Valuation refreshed',
        description: `Updated to ${fmt(data.new_value)}${rangeStr}${vinInfo}${providerLabel}`,
        status: 'success',
        duration: 5000,
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Valuation refresh failed',
        description: error.response?.data?.detail || 'An error occurred',
        status: 'error',
        duration: 7000,
        isClosable: true,
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

  // Delete holding mutation
  const deleteHoldingMutation = useMutation({
    mutationFn: (holdingId: string) => holdingsApi.deleteHolding(holdingId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['holdings', accountId] });
      queryClient.invalidateQueries({ queryKey: ['portfolio-widget'] });
      toast({ title: 'Holding removed', status: 'success', duration: 3000 });
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to remove holding',
        description: error.response?.data?.detail || 'An error occurred',
        status: 'error',
        duration: 5000,
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

  const handleToggleIncludeInNetworth = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (account) {
      updateAccountMutation.mutate({ include_in_networth: e.target.checked });
    }
  };

  const handleDelete = () => {
    deleteAccountMutation.mutate();
    onDeleteClose();
  };

  const handleUpdateVehicle = () => {
    const updates: { mileage?: number; balance?: number; vin?: string } = {};

    if (vehicleMileage) {
      const mileage = parseInt(vehicleMileage);
      if (!isNaN(mileage) && mileage >= 0) updates.mileage = mileage;
    }

    if (vehicleValue) {
      const value = parseFloat(vehicleValue);
      if (!isNaN(value) && value >= 0) updates.balance = value;
    }

    if (vehicleVin.trim()) {
      updates.vin = vehicleVin.trim();
    }

    if (Object.keys(updates).length > 0) {
      updateVehicleMutation.mutate(updates);
    }
  };

  const handleUpdatePropertyDetails = () => {
    const payload: any = {};
    if (propertyAddress.trim()) payload.property_address = propertyAddress.trim();
    if (propertyZip.trim()) payload.property_zip = propertyZip.trim();
    if (Object.keys(payload).length > 0) {
      updateAccountMutation.mutate(payload, {
        onSuccess: () => {
          setPropertyAddress('');
          setPropertyZip('');
        },
      });
    }
  };

  const handleSaveLoanDetails = () => {
    const updates: { interest_rate?: number | null; loan_term_months?: number | null; origination_date?: string | null } = {};

    if (loanInterestRate !== '') {
      const rate = parseFloat(loanInterestRate);
      if (!isNaN(rate) && rate >= 0) updates.interest_rate = rate;
    }
    if (loanTermYears !== '') {
      const years = parseFloat(loanTermYears);
      if (!isNaN(years) && years > 0) updates.loan_term_months = Math.round(years * 12);
    }
    if (loanOriginationDate !== '') {
      updates.origination_date = loanOriginationDate;
    }

    if (Object.keys(updates).length > 0) {
      updateAccountMutation.mutate(updates, {
        onSuccess: () => {
          setLoanInterestRate('');
          setLoanTermYears('');
          setLoanOriginationDate('');
        },
      });
    }
  };

  const handleSaveEmployerMatch = () => {
    const updates: {
      employer_match_percent?: number | null;
      employer_match_limit_percent?: number | null;
      annual_salary?: number | null;
    } = {};
    if (empMatchPct !== '') {
      const v = parseFloat(empMatchPct);
      if (!isNaN(v) && v >= 0) updates.employer_match_percent = v;
    }
    if (empMatchLimitPct !== '') {
      const v = parseFloat(empMatchLimitPct);
      if (!isNaN(v) && v >= 0) updates.employer_match_limit_percent = v;
    }
    if (empAnnualSalary !== '') {
      const v = parseFloat(empAnnualSalary);
      if (!isNaN(v) && v >= 0) updates.annual_salary = v;
    }
    if (Object.keys(updates).length > 0) {
      updateAccountMutation.mutate(updates, {
        onSuccess: () => {
          setEmpMatchPct('');
          setEmpMatchLimitPct('');
          setEmpAnnualSalary('');
        },
      });
    }
  };

  const handleSaveBalance = (rawValue: string, clearInput: () => void) => {
    const value = parseFloat(rawValue);
    if (!isNaN(value) && value >= 0) {
      updateAccountMutation.mutate({ current_balance: value }, {
        onSuccess: clearInput,
      });
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
  // 1. User doesn't have edit permission (no ownership or grant), OR
  // 2. In combined view and user doesn't own the account
  //    (in other-user view, canEdit already validated the grant), OR
  // 3. Account is shared AND in combined view (must edit in individual user view)
  const canEditAccount = canEdit && (isOwner || !isCombinedView) && !isSharedAccount;

  const isAssetAccount = ASSET_ACCOUNT_TYPES.includes(account.account_type);
  const isManual = account.account_source === 'manual';

  // Asset accounts (property, vehicle, etc.) don't have transaction flows
  const showTransactions = !isAssetAccount;
  // Recurring contributions only make sense for investment/savings account types
  const showContributions =
    isManual && CONTRIBUTION_ACCOUNT_TYPES.includes(account.account_type);
  // Show a balance update form for any manual account that doesn't already have its
  // own dedicated balance section (vehicle has a vehicle section, debt has a debt
  // section — everything else, including checking/savings/brokerage/crypto, shows this)
  const showUpdateBalance =
    isManual
    && account.account_type !== 'vehicle'
    && !DEBT_ACCOUNT_TYPES.includes(account.account_type);
  // Manual debt accounts can have their balance set directly
  const showDebtBalanceUpdate =
    isManual && DEBT_ACCOUNT_TYPES.includes(account.account_type);
  // Investment account types support individual holdings
  const showHoldings = HOLDINGS_ACCOUNT_TYPES.includes(account.account_type);
  // "Add Transaction" button in the transactions panel for manual non-asset accounts
  const canAddTransaction = isManual && !isAssetAccount && canEditAccount;

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
            <Text color="text.secondary" mt={1}>
              {accountTypeLabels[account.account_type] || account.account_type}
              {account.mask && account.account_type !== 'vehicle' && ` ••${account.mask}`}
            </Text>
          </Box>
          <Box textAlign="right">
            <Text fontSize="sm" color="text.secondary">
              Current Balance
            </Text>
            <Text
              fontSize="3xl"
              fontWeight="bold"
              color={isNegative ? 'finance.negative' : 'brand.accent'}
            >
              {formatCurrency(balance)}
            </Text>
            <Text fontSize="xs" color="text.muted">
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
                  <Text fontSize="xs" color="text.muted" mt={0.5}>
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
                <Text fontSize="sm" fontWeight="medium" color="text.secondary">
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
                    <Text fontSize="sm" fontWeight="medium" color="text.secondary">
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
                      <Text fontSize="sm" color="text.secondary">Last synced:</Text>
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
                            <Text fontSize="xs" color="text.secondary" noOfLines={1}>
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
                <Text fontSize="xs" color="text.muted" mt={1}>
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
              <HStack justify="space-between" mb={4}>
                <Heading size="md">Vehicle Details</Heading>
                {canEditAccount && (
                  <HStack spacing={2}>
                    {availableProviders.length > 1 && (
                      <Select
                        size="sm"
                        value={selectedProvider}
                        onChange={(e) => setSelectedProvider(e.target.value)}
                        w="auto"
                      >
                        <option value="">Auto-select</option>
                        {availableProviders.map(p => (
                          <option key={p} value={p}>{p}</option>
                        ))}
                      </Select>
                    )}
                    <Tooltip
                      label={
                        !account.vehicle_vin ? 'Add VIN below to enable auto-valuation'
                        : availableProviders.length === 0 ? 'No valuation provider configured'
                        : 'Fetch current market value'
                      }
                      placement="top"
                    >
                      <Button
                        size="sm"
                        leftIcon={<FiRefreshCw />}
                        variant="outline"
                        onClick={() => refreshValuationMutation.mutate()}
                        isLoading={refreshValuationMutation.isPending}
                        isDisabled={!account.vehicle_vin || availableProviders.length === 0}
                      >
                        Refresh Valuation
                      </Button>
                    </Tooltip>
                  </HStack>
                )}
              </HStack>
              <VStack spacing={4} align="stretch">
                {/* Current info display */}
                <HStack spacing={6} wrap="wrap">
                  <Box>
                    <Text fontSize="xs" color="text.muted">Current Mileage</Text>
                    <Text fontWeight="semibold">
                      {account.vehicle_mileage != null ? `${account.vehicle_mileage.toLocaleString()} miles` : 'Not set'}
                    </Text>
                  </Box>
                  <Box>
                    <Text fontSize="xs" color="text.muted">VIN</Text>
                    <Text fontWeight="semibold" fontFamily="mono" fontSize="sm">
                      {account.vehicle_vin ?? 'Not set'}
                    </Text>
                  </Box>
                  {account.last_auto_valued_at && (
                    <Box>
                      <Text fontSize="xs" color="text.muted">Last Auto-Valued</Text>
                      <Text fontWeight="semibold" fontSize="sm">
                        {formatLastSynced(account.last_auto_valued_at)}
                      </Text>
                    </Box>
                  )}
                </HStack>

                <Divider />

                {/* Investment toggle */}
                <FormControl>
                  <HStack justify="space-between" align="center">
                    <FormLabel htmlFor="vehicle-networth-toggle" mb="0" fontSize="sm">
                      Count as Investment in Net Worth
                    </FormLabel>
                    <Tooltip
                      label={!canEditAccount ? "You can only edit your own accounts" : ""}
                      placement="top"
                      isDisabled={canEditAccount}
                    >
                      <Switch
                        id="vehicle-networth-toggle"
                        isChecked={account.include_in_networth ?? false}
                        onChange={handleToggleIncludeInNetworth}
                        colorScheme="blue"
                        isDisabled={!canEditAccount}
                      />
                    </Tooltip>
                  </HStack>
                  <Text fontSize="xs" color="text.muted" mt={1}>
                    Enable for classic or collectible vehicles you consider an investment.
                  </Text>
                </FormControl>

                <Divider />

                {!canEditAccount ? (
                  <Text fontSize="sm" color="text.secondary">
                    Vehicle details can only be updated by the account owner.
                  </Text>
                ) : (
                  <>
                    {/* Update VIN */}
                    <FormControl>
                      <FormLabel fontSize="sm">VIN (for auto-valuation)</FormLabel>
                      <Input
                        value={vehicleVin}
                        onChange={(e) => setVehicleVin(e.target.value.toUpperCase())}
                        placeholder={account.vehicle_vin ?? 'e.g., 1HGBH41JXMN109186'}
                        maxLength={17}
                        size="sm"
                        fontFamily="mono"
                      />
                      <Text fontSize="xs" color="text.muted" mt={1}>
                        17-character VIN enables automatic market value updates via MarketCheck API.
                      </Text>
                    </FormControl>

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
                          <NumberInputField placeholder={account.vehicle_mileage != null ? String(account.vehicle_mileage) : 'Enter mileage'} />
                        </NumberInput>
                        <Text fontSize="sm" color="text.secondary">
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
                      isDisabled={!vehicleMileage && !vehicleValue && !vehicleVin.trim()}
                    >
                      Save Updates
                    </Button>
                  </>
                )}
              </VStack>
            </CardBody>
          </Card>
        )}

        {/* Property Details Section - Only for property accounts */}
        {account.account_type === 'property' && (
          <Card>
            <CardBody>
              <HStack justify="space-between" mb={4}>
                <Heading size="md">Property Details</Heading>
                {canEditAccount && (
                  <HStack spacing={2}>
                    {availableProviders.length > 1 && (
                      <Select
                        size="sm"
                        value={selectedProvider}
                        onChange={(e) => setSelectedProvider(e.target.value)}
                        w="auto"
                      >
                        <option value="">Auto-select</option>
                        {availableProviders.map(p => (
                          <option key={p} value={p}>{p}</option>
                        ))}
                      </Select>
                    )}
                    <Tooltip
                      label={
                        !account.property_address || !account.property_zip ? 'Add address and ZIP below to enable auto-valuation'
                        : availableProviders.length === 0 ? 'No valuation provider configured'
                        : 'Fetch current estimated value'
                      }
                      placement="top"
                    >
                      <Button
                        size="sm"
                        leftIcon={<FiRefreshCw />}
                        variant="outline"
                        onClick={() => refreshValuationMutation.mutate()}
                        isLoading={refreshValuationMutation.isPending}
                        isDisabled={!account.property_address || !account.property_zip || availableProviders.length === 0}
                      >
                        Refresh Valuation
                      </Button>
                    </Tooltip>
                  </HStack>
                )}
              </HStack>
              <VStack spacing={4} align="stretch">
                {/* Current info display */}
                <HStack spacing={6} wrap="wrap">
                  <Box>
                    <Text fontSize="xs" color="text.muted">Address</Text>
                    <Text fontWeight="semibold" fontSize="sm">
                      {account.property_address
                        ? `${account.property_address}${account.property_zip ? `, ${account.property_zip}` : ''}`
                        : 'Not set'}
                    </Text>
                  </Box>
                  {account.last_auto_valued_at && (
                    <Box>
                      <Text fontSize="xs" color="text.muted">Last Auto-Valued</Text>
                      <Text fontWeight="semibold" fontSize="sm">
                        {formatLastSynced(account.last_auto_valued_at)}
                      </Text>
                    </Box>
                  )}
                </HStack>

                {!canEditAccount ? (
                  <Text fontSize="sm" color="text.secondary">
                    Property details can only be updated by the account owner.
                  </Text>
                ) : (
                  <>
                    <Divider />
                    <HStack spacing={4} align="start">
                      <FormControl flex={2}>
                        <FormLabel fontSize="sm">Street Address</FormLabel>
                        <Input
                          value={propertyAddress}
                          onChange={(e) => setPropertyAddress(e.target.value)}
                          placeholder={account.property_address ?? 'e.g., 123 Main St'}
                          size="sm"
                        />
                      </FormControl>
                      <FormControl flex={1}>
                        <FormLabel fontSize="sm">ZIP Code</FormLabel>
                        <Input
                          value={propertyZip}
                          onChange={(e) => setPropertyZip(e.target.value)}
                          placeholder={account.property_zip ?? 'e.g., 94102'}
                          maxLength={10}
                          size="sm"
                        />
                      </FormControl>
                    </HStack>
                    <Button
                      colorScheme="brand"
                      size="sm"
                      onClick={handleUpdatePropertyDetails}
                      isLoading={updateAccountMutation.isPending}
                      isDisabled={!propertyAddress.trim() && !propertyZip.trim()}
                    >
                      Save Property Details
                    </Button>
                    <Text fontSize="xs" color="text.muted">
                      Address and ZIP are used to fetch automated property valuations.
                    </Text>
                  </>
                )}
              </VStack>
            </CardBody>
          </Card>
        )}

        {/* Loan Details Section - For mortgage/loan/student_loan accounts */}
        {LOAN_ACCOUNT_TYPES.includes(account.account_type) && (
          <Card>
            <CardBody>
              <Heading size="md" mb={1}>
                Loan Details
              </Heading>
              <Text fontSize="sm" color="text.muted" mb={4}>
                {account.account_source !== 'manual'
                  ? 'Your bank may not provide these details. Enter them manually to enable cash flow projections and debt payoff planning.'
                  : 'Used for cash flow projections and debt payoff planning.'}
              </Text>
              <VStack spacing={4} align="stretch">
                {/* Current values display */}
                {(account.interest_rate || account.loan_term_months || account.origination_date) && (
                  <>
                    <HStack spacing={6} wrap="wrap">
                      {account.interest_rate != null && (
                        <Box>
                          <Text fontSize="xs" color="text.muted">Interest Rate</Text>
                          <Text fontWeight="semibold">{account.interest_rate}%</Text>
                        </Box>
                      )}
                      {account.loan_term_months != null && (
                        <Box>
                          <Text fontSize="xs" color="text.muted">Loan Term</Text>
                          <Text fontWeight="semibold">
                            {account.loan_term_months >= 12
                              ? `${Math.round(account.loan_term_months / 12)} years`
                              : `${account.loan_term_months} months`}
                          </Text>
                        </Box>
                      )}
                      {account.origination_date && (
                        <Box>
                          <Text fontSize="xs" color="text.muted">Loan Start</Text>
                          <Text fontWeight="semibold">
                            {new Date(account.origination_date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
                          </Text>
                        </Box>
                      )}
                    </HStack>
                    <Divider />
                  </>
                )}

                {!canEditAccount ? (
                  <Text fontSize="sm" color="text.secondary">
                    Loan details can only be updated by the account owner.
                  </Text>
                ) : (
                  <>
                    <FormControl>
                      <FormLabel fontSize="sm">Interest Rate (%)</FormLabel>
                      <NumberInput
                        value={loanInterestRate}
                        onChange={setLoanInterestRate}
                        precision={3}
                        step={0.125}
                        min={0}
                        max={100}
                        size="sm"
                      >
                        <NumberInputField placeholder={account.interest_rate != null ? String(account.interest_rate) : 'e.g., 6.75'} />
                      </NumberInput>
                    </FormControl>

                    <FormControl>
                      <FormLabel fontSize="sm">Loan Term (years)</FormLabel>
                      <NumberInput
                        value={loanTermYears}
                        onChange={setLoanTermYears}
                        precision={1}
                        step={1}
                        min={1}
                        max={50}
                        size="sm"
                      >
                        <NumberInputField placeholder={account.loan_term_months != null ? String(Math.round(account.loan_term_months / 12)) : 'e.g., 30'} />
                      </NumberInput>
                    </FormControl>

                    <FormControl>
                      <FormLabel fontSize="sm">Loan Start Date</FormLabel>
                      <Input
                        type="date"
                        size="sm"
                        value={loanOriginationDate}
                        onChange={(e) => setLoanOriginationDate(e.target.value)}
                        placeholder={account.origination_date ?? undefined}
                      />
                    </FormControl>

                    <Button
                      colorScheme="brand"
                      size="sm"
                      onClick={handleSaveLoanDetails}
                      isLoading={updateAccountMutation.isPending}
                      isDisabled={!loanInterestRate && !loanTermYears && !loanOriginationDate}
                    >
                      Save Loan Details
                    </Button>
                  </>
                )}
              </VStack>
            </CardBody>
          </Card>
        )}

        {/* Employer Match Section - For 401k / 403b accounts */}
        {['retirement_401k', 'retirement_403b'].includes(account.account_type) && (
          <Card>
            <CardBody>
              <Heading size="md" mb={1}>Employer Match</Heading>
              <Text fontSize="sm" color="text.secondary" mb={4}>
                Track how much your employer contributes to see your true total retirement savings rate.
              </Text>

              {/* Current values display */}
              {(account.employer_match_percent != null || account.employer_match_limit_percent != null || account.annual_salary != null) && (
                <>
                  <HStack spacing={6} wrap="wrap" mb={4}>
                    {account.employer_match_percent != null && (
                      <Box>
                        <Text fontSize="xs" color="text.muted">Employer Matches</Text>
                        <Text fontWeight="semibold">{account.employer_match_percent}% of your contribution</Text>
                      </Box>
                    )}
                    {account.employer_match_limit_percent != null && (
                      <Box>
                        <Text fontSize="xs" color="text.muted">On First</Text>
                        <Text fontWeight="semibold">{account.employer_match_limit_percent}% of salary</Text>
                      </Box>
                    )}
                    {account.annual_salary != null && (
                      <Box>
                        <Text fontSize="xs" color="text.muted">Annual Salary</Text>
                        <Text fontWeight="semibold">{formatCurrency(account.annual_salary)}</Text>
                      </Box>
                    )}
                    {/* Computed annual employer contribution */}
                    {account.employer_match_percent != null && account.employer_match_limit_percent != null && account.annual_salary != null && (() => {
                      const matchablePct = Math.min(account.employer_match_limit_percent, account.employer_match_limit_percent);
                      const annualMatch = (matchablePct / 100) * (account.employer_match_percent / 100) * account.annual_salary;
                      const monthlyMatch = annualMatch / 12;
                      return (
                        <Box bg="bg.success" px={3} py={2} borderRadius="md" borderWidth="1px" borderColor="green.200">
                          <Text fontSize="xs" color="green.700">Employer Contributes</Text>
                          <Text fontWeight="bold" color="green.700">
                            {formatCurrency(annualMatch)}/yr &nbsp;·&nbsp; {formatCurrency(monthlyMatch)}/mo
                          </Text>
                        </Box>
                      );
                    })()}
                  </HStack>
                  <Divider mb={4} />
                </>
              )}

              {!canEditAccount ? (
                <Text fontSize="sm" color="text.secondary">Employer match can only be updated by the account owner.</Text>
              ) : (
                <>
                  <HStack spacing={4} align="end" wrap="wrap">
                    <FormControl maxW="160px">
                      <FormLabel fontSize="sm">Employer Match (%)</FormLabel>
                      <NumberInput value={empMatchPct} onChange={setEmpMatchPct} min={0} max={200} precision={2} size="sm">
                        <NumberInputField placeholder={account.employer_match_percent != null ? String(account.employer_match_percent) : 'e.g., 50'} />
                      </NumberInput>
                    </FormControl>
                    <FormControl maxW="160px">
                      <FormLabel fontSize="sm">Up to (% of salary)</FormLabel>
                      <NumberInput value={empMatchLimitPct} onChange={setEmpMatchLimitPct} min={0} max={100} precision={2} size="sm">
                        <NumberInputField placeholder={account.employer_match_limit_percent != null ? String(account.employer_match_limit_percent) : 'e.g., 6'} />
                      </NumberInput>
                    </FormControl>
                    <FormControl maxW="200px">
                      <FormLabel fontSize="sm">Annual Salary ($)</FormLabel>
                      <NumberInput value={empAnnualSalary} onChange={setEmpAnnualSalary} min={0} precision={0} size="sm">
                        <NumberInputField placeholder={account.annual_salary != null ? String(account.annual_salary) : 'e.g., 100000'} />
                      </NumberInput>
                    </FormControl>
                  </HStack>
                  <Button
                    mt={4}
                    size="sm"
                    colorScheme="blue"
                    onClick={handleSaveEmployerMatch}
                    isLoading={updateAccountMutation.isPending}
                    isDisabled={!empMatchPct && !empMatchLimitPct && !empAnnualSalary}
                  >
                    Save Match Details
                  </Button>
                </>
              )}
            </CardBody>
          </Card>
        )}

        {/* Holdings Section - For investment account types (brokerage, IRA, 401k, HSA, 529) */}
        {showHoldings && (
          <Card>
            <CardBody>
              <HStack justify="space-between" mb={4}>
                <Heading size="md">Holdings</Heading>
                {canEditAccount && isManual && (
                  <Button
                    size="sm"
                    colorScheme="brand"
                    variant="outline"
                    onClick={onAddHoldingOpen}
                  >
                    Add Holding
                  </Button>
                )}
              </HStack>

              {accountHoldings && accountHoldings.length > 0 ? (
                <Table variant="simple" size="sm">
                  <Thead>
                    <Tr>
                      <Th>Symbol</Th>
                      <Th>Name</Th>
                      <Th isNumeric>{account.account_type === 'crypto' ? 'Coins' : 'Shares'}</Th>
                      <Th isNumeric>{account.account_type === 'crypto' ? 'Cost/Coin' : 'Cost Basis/Share'}</Th>
                      <Th isNumeric>Current Value</Th>
                      {canEditAccount && isManual && <Th />}
                    </Tr>
                  </Thead>
                  <Tbody>
                    {accountHoldings.map((h) => (
                      <Tr key={h.id}>
                        <Td fontWeight="bold">{h.ticker}</Td>
                        <Td color="text.secondary">{h.name || '—'}</Td>
                        <Td isNumeric>{Number(h.shares).toLocaleString(undefined, { maximumFractionDigits: 6 })}</Td>
                        <Td isNumeric>
                          {h.cost_basis_per_share != null
                            ? formatCurrency(Number(h.cost_basis_per_share))
                            : '—'}
                        </Td>
                        <Td isNumeric fontWeight="medium">
                          {h.current_value != null
                            ? formatCurrency(Number(h.current_value))
                            : '—'}
                        </Td>
                        {canEditAccount && isManual && (
                          <Td>
                            <Tooltip label="Remove holding" placement="top">
                              <IconButton
                                aria-label="Remove holding"
                                icon={<FiTrash2 />}
                                size="xs"
                                variant="ghost"
                                colorScheme="red"
                                onClick={() => deleteHoldingMutation.mutate(h.id)}
                                isLoading={deleteHoldingMutation.isPending && deleteHoldingMutation.variables === h.id}
                                isDisabled={deleteHoldingMutation.isPending && deleteHoldingMutation.variables !== h.id}
                              />
                            </Tooltip>
                          </Td>
                        )}
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              ) : (
                <Text color="text.muted" fontSize="sm" textAlign="center" py={6}>
                  {isManual
                    ? 'No holdings yet. Use "Add Holding" to record your positions.'
                    : 'Holdings are synced from your brokerage.'}
                </Text>
              )}
            </CardBody>
          </Card>
        )}

        {/* Update Balance for manual debt accounts */}
        {showDebtBalanceUpdate && (
          <Card>
            <CardBody>
              <Heading size="md" mb={1}>
                Update Balance
              </Heading>
              <Text fontSize="sm" color="text.muted" mb={4}>
                Set the current amount owed to keep your debt tracking accurate.
              </Text>
              <VStack spacing={4} align="stretch">
                {!canEditAccount ? (
                  <Text fontSize="sm" color="text.secondary">
                    Balance can only be updated by the account owner.
                  </Text>
                ) : (
                  <>
                    <FormControl>
                      <FormLabel fontSize="sm">Current Balance Owed ($)</FormLabel>
                      <HStack>
                        <Text fontSize="sm">$</Text>
                        <NumberInput
                          value={debtBalance}
                          onChange={setDebtBalance}
                          min={0}
                          precision={2}
                          size="sm"
                        >
                          <NumberInputField placeholder={Math.abs(balance).toFixed(2)} />
                        </NumberInput>
                      </HStack>
                    </FormControl>
                    <Button
                      colorScheme="brand"
                      size="sm"
                      onClick={() => handleSaveBalance(debtBalance, () => setDebtBalance(''))}
                      isLoading={updateAccountMutation.isPending}
                      isDisabled={!debtBalance}
                    >
                      Save Balance
                    </Button>
                  </>
                )}
              </VStack>
            </CardBody>
          </Card>
        )}

        {/* Update Balance Section - For all manual accounts except vehicle and debt */}
        {showUpdateBalance && (
          <Card>
            <CardBody>
              <Heading size="md" mb={1}>
                {isAssetAccount ? 'Update Value' : 'Update Balance'}
              </Heading>
              <Text fontSize="sm" color="text.muted" mb={4}>
                {isAssetAccount
                  ? 'Enter the current market value of this asset to keep your net worth up to date.'
                  : 'Set the current balance to keep your account accurate.'}
              </Text>
              <VStack spacing={4} align="stretch">
                {!canEditAccount ? (
                  <Text fontSize="sm" color="text.secondary">
                    {isAssetAccount
                      ? 'Value can only be updated by the account owner.'
                      : 'Balance can only be updated by the account owner.'}
                  </Text>
                ) : (
                  <>
                    <FormControl>
                      <FormLabel fontSize="sm">
                        {isAssetAccount ? 'Current Value ($)' : 'Current Balance ($)'}
                      </FormLabel>
                      <HStack>
                        <Text fontSize="sm">$</Text>
                        <NumberInput
                          value={manualBalance}
                          onChange={setManualBalance}
                          min={0}
                          precision={2}
                          size="sm"
                        >
                          <NumberInputField
                            placeholder={Math.abs(balance).toFixed(2)}
                          />
                        </NumberInput>
                      </HStack>
                    </FormControl>
                    <Button
                      colorScheme="brand"
                      size="sm"
                      onClick={() => handleSaveBalance(manualBalance, () => setManualBalance(''))}
                      isLoading={updateAccountMutation.isPending}
                      isDisabled={!manualBalance}
                    >
                      {isAssetAccount ? 'Save Value' : 'Save Balance'}
                    </Button>
                  </>
                )}
              </VStack>
            </CardBody>
          </Card>
        )}

        {/* Recurring Contributions Section - Only for investment/savings manual accounts */}
        {showContributions && (
          <Card>
            <CardBody>
              {canEditAccount ? (
                <ContributionsManager accountId={account.id} accountName={account.name} />
              ) : (
                <Box>
                  <Heading size="md" mb={2}>Recurring Contributions</Heading>
                  <Text fontSize="sm" color="text.secondary">
                    Contributions can only be managed by the account owner.
                  </Text>
                </Box>
              )}
            </CardBody>
          </Card>
        )}


        {/* Transactions Section - hidden for asset accounts (property, vehicle, etc.) */}
        {showTransactions && <Card>
          <CardBody>
            <HStack justify="space-between" mb={4}>
              <Heading size="md">Transactions</Heading>
              <HStack spacing={3}>
                {canAddTransaction && (
                  <Button
                    size="sm"
                    colorScheme="brand"
                    variant="outline"
                    onClick={onAddTxnOpen}
                  >
                    Add Transaction
                  </Button>
                )}
                {transactionsData && transactionsData.total > 0 && (
                  <Text fontSize="sm" color="text.secondary">
                    Showing {transactionsData.transactions?.length || 0} of {transactionsData.total}
                  </Text>
                )}
              </HStack>
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
                              color={isNegative ? 'finance.positive' : 'finance.negative'}
                            >
                              {isNegative ? '+' : '-'}
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
              <Text color="text.muted" fontSize="sm" textAlign="center" py={8}>
                No transactions found for this account.
              </Text>
            )}
          </CardBody>
        </Card>}
      </VStack>

      {/* Add Transaction Modal */}
      <AddTransactionModal
        isOpen={isAddTxnOpen}
        onClose={onAddTxnClose}
        accountId={account.id}
        accountName={account.name}
      />

      {/* Add Holding Modal */}
      <AddHoldingModal
        isOpen={isAddHoldingOpen}
        onClose={onAddHoldingClose}
        accountId={account.id}
        accountName={account.name}
        isCrypto={account.account_type === 'crypto'}
      />

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
