/**
 * Account detail page with settings and transactions
 */

import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
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
  SimpleGrid,
  Collapse,
} from "@chakra-ui/react";
import {
  FiEdit2,
  FiCheck,
  FiX,
  FiLock,
  FiRefreshCw,
  FiTrash2,
  FiRepeat,
  FiPlus,
} from "react-icons/fi";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState, useEffect } from "react";
import api from "../services/api";
import { useUserView } from "../contexts/UserViewContext";
import type { Transaction } from "../types/transaction";
import { ContributionsManager } from "../features/accounts/components/ContributionsManager";
import { AddTransactionModal } from "../features/accounts/components/AddTransactionModal";
import { AddHoldingModal } from "../features/accounts/components/AddHoldingModal";
import { holdingsApi, type Holding } from "../api/holdings";
import { rentalPropertiesApi } from "../api/rental-properties";
import { TaxLotsPanel } from "../features/investments/components/TaxLotsPanel";
import { ReconciliationCard } from "../features/accounts/components/ReconciliationCard";
import { formatAccountType } from "../utils/formatAccountType";
import {
  ASSET_ACCOUNT_TYPES,
  CONTRIBUTION_ACCOUNT_TYPES,
  DEBT_ACCOUNT_TYPES,
  EMPLOYER_MATCH_TYPES,
  HOLDINGS_ACCOUNT_TYPES,
  TAX_TREATMENT_ACCOUNT_TYPES,
} from "../constants/accountTypeGroups";
import { HelpHint } from "../components/HelpHint";
import { helpContent } from "../constants/helpContent";

interface Account {
  id: string;
  user_id: string;
  name: string;
  account_type: string;
  tax_treatment: string | null;
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
  valuation_adjustment_pct: number | null;
  // Rental property fields
  is_rental_property: boolean | null;
  rental_monthly_income: number | null;
  rental_type?: string | null;
  // Employer match fields (401k / 403b)
  employer_match_percent: number | null;
  employer_match_limit_percent: number | null;
  annual_salary: number | null;
  // Equity fields (stock_options / private_equity)
  grant_type: string | null;
  quantity: number | null;
  strike_price: number | null;
  share_price: number | null;
  grant_date: string | null;
  company_status: string | null;
  valuation_method: string | null;
  vesting_schedule: string | null;
  // Sync status
  last_synced_at: string | null;
  last_error_code: string | null;
  last_error_message: string | null;
  needs_reauth: boolean | null;
}

const LOAN_ACCOUNT_TYPES = ["mortgage", "loan", "student_loan"];
const CASH_ACCOUNT_TYPES = ["checking", "savings", "money_market"];

export const AccountDetailPage = () => {
  const { accountId } = useParams<{ accountId: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { canWriteOwnedResource } = useUserView();
  const [searchParams] = useSearchParams();
  const selectedUserId = searchParams.get("user");
  const isCombinedView = !selectedUserId;
  const {
    isOpen: isDeleteOpen,
    onOpen: onDeleteOpen,
    onClose: onDeleteClose,
  } = useDisclosure();
  const {
    isOpen: isAddTxnOpen,
    onOpen: onAddTxnOpen,
    onClose: onAddTxnClose,
  } = useDisclosure();
  const {
    isOpen: isAddHoldingOpen,
    onOpen: onAddHoldingOpen,
    onClose: onAddHoldingClose,
  } = useDisclosure();
  const {
    isOpen: isMigrateOpen,
    onOpen: onMigrateOpen,
    onClose: onMigrateClose,
  } = useDisclosure();
  const cancelRef = useRef<HTMLButtonElement>(null);
  const migrateCancelRef = useRef<HTMLButtonElement>(null);
  const [migrateStep, setMigrateStep] = useState<1 | 2>(1);
  const [selectedTargetSource, setSelectedTargetSource] = useState<
    string | null
  >(null);
  const [showMigrationHistory, setShowMigrationHistory] = useState(false);
  const [transactionsCursor, setTransactionsCursor] = useState<string | null>(
    null,
  );
  const [vehicleMileage, setVehicleMileage] = useState("");
  const [vehicleValue, setVehicleValue] = useState("");
  const [vehicleVin, setVehicleVin] = useState("");
  const [propertyAddress, setPropertyAddress] = useState("");
  const [propertyZip, setPropertyZip] = useState("");
  const [isRentalProperty, setIsRentalProperty] = useState(false);
  const [rentalMonthlyIncome, setRentalMonthlyIncome] = useState("");
  const [rentalType, setRentalType] = useState<string>("");
  const [manualBalance, setManualBalance] = useState("");
  const [debtBalance, setDebtBalance] = useState("");
  const [isEditingName, setIsEditingName] = useState(false);
  const [editedName, setEditedName] = useState("");
  // Loan detail editing state
  const [loanInterestRate, setLoanInterestRate] = useState("");
  const [loanTermYears, setLoanTermYears] = useState("");
  const [loanOriginationDate, setLoanOriginationDate] = useState("");
  const [cashApyRate, setCashApyRate] = useState("");
  // Employer match editing state
  const [empMatchPct, setEmpMatchPct] = useState("");
  const [empMatchLimitPct, setEmpMatchLimitPct] = useState("");
  const [empAnnualSalary, setEmpAnnualSalary] = useState("");
  // Valuation adjustment state
  const [adjustmentPct, setAdjustmentPct] = useState("");
  // Equity detail editing state
  const [equityGrantType, setEquityGrantType] = useState("");
  const [equityQuantity, setEquityQuantity] = useState("");
  const [equityStrikePrice, setEquityStrikePrice] = useState("");
  const [equitySharePrice, setEquitySharePrice] = useState("");
  const [equityGrantDate, setEquityGrantDate] = useState("");
  const [equityCompanyStatus, setEquityCompanyStatus] = useState("");
  const [vestRows, setVestRows] = useState<{ date: string; quantity: string; notes: string }[]>([]);

  // Fetch account details
  const {
    data: account,
    isLoading,
    isError: accountError,
    refetch: refetchAccount,
  } = useQuery<Account>({
    queryKey: ["account", accountId],
    queryFn: async () => {
      const response = await api.get(`/accounts/${accountId}`);
      return response.data;
    },
  });

  const isPropertyOrVehicle =
    account?.account_type === "property" || account?.account_type === "vehicle";

  // Fetch available valuation providers (only for property/vehicle accounts)
  const { data: valuationProviders } = useQuery<{
    property: string[];
    vehicle: string[];
  }>({
    queryKey: ["valuation-providers"],
    queryFn: async () => {
      const response = await api.get("/accounts/valuation-providers");
      return response.data;
    },
    enabled: isPropertyOrVehicle,
    staleTime: 5 * 60 * 1000, // provider config changes rarely
  });

  const availableProviders =
    account?.account_type === "property"
      ? (valuationProviders?.property ?? [])
      : (valuationProviders?.vehicle ?? []);
  const [selectedProvider, setSelectedProvider] = useState<string>("");

  // Fetch all accounts to check if this account is shared (only in combined view)
  const { data: allAccounts } = useQuery<Account[]>({
    queryKey: ["accounts-check-shared", accountId],
    queryFn: async () => {
      const response = await api.get("/accounts");
      return response.data;
    },
    enabled: isCombinedView && !!account?.plaid_item_hash,
  });

  // Fetch transactions for this account
  const { data: transactionsData, isLoading: transactionsLoading } = useQuery({
    queryKey: ["transactions", accountId, transactionsCursor],
    queryFn: async () => {
      const params = new URLSearchParams({
        account_id: accountId!,
        page_size: "50",
      });
      if (transactionsCursor) {
        params.append("cursor", transactionsCursor);
      }
      const response = await api.get(`/transactions/?${params.toString()}`);
      return response.data;
    },
    enabled:
      !!accountId && !ASSET_ACCOUNT_TYPES.includes(account?.account_type ?? ""),
  });

  // Fetch holdings for investment accounts
  const { data: accountHoldings } = useQuery<Holding[]>({
    queryKey: ["holdings", accountId],
    queryFn: () => holdingsApi.getAccountHoldings(accountId!),
    enabled:
      !!accountId &&
      HOLDINGS_ACCOUNT_TYPES.includes(account?.account_type ?? ""),
  });

  // Update account mutation
  const updateAccountMutation = useMutation({
    mutationFn: async (data: {
      name?: string;
      account_type?: string;
      tax_treatment?: string | null;
      is_active?: boolean;
      exclude_from_cash_flow?: boolean;
      include_in_networth?: boolean | null;
      interest_rate?: number | null;
      loan_term_months?: number | null;
      origination_date?: string | null;
      current_balance?: number;
      employer_match_percent?: number | null;
      employer_match_limit_percent?: number | null;
      annual_salary?: number | null;
      property_address?: string | null;
      property_zip?: string | null;
      vehicle_vin?: string | null;
      vehicle_mileage?: number | null;
      valuation_adjustment_pct?: number | null;
    }) => {
      const response = await api.patch(`/accounts/${accountId}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["account", accountId] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      queryClient.invalidateQueries({ queryKey: ["accounts-admin"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["portfolio-summary"] });
      toast({
        title: "Account updated",
        status: "success",
        duration: 3000,
      });
    },
    onError: (error: any) => {
      toast({
        title: "Failed to update account",
        description: error.response?.data?.detail || "An error occurred",
        status: "error",
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
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      queryClient.invalidateQueries({ queryKey: ["accounts-admin"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["infinite-transactions"] });
      toast({
        title: "Account deleted",
        status: "success",
        duration: 3000,
      });
      navigate("/dashboard");
    },
    onError: (error: any) => {
      toast({
        title: "Failed to delete account",
        description: error.response?.data?.detail || "An error occurred",
        status: "error",
        duration: 5000,
      });
    },
  });

  // Migrate account provider mutation
  const migrateAccountMutation = useMutation({
    mutationFn: async (targetSource: string) => {
      const response = await api.post(`/accounts/${accountId}/migrate`, {
        target_source: targetSource,
        target_enrollment_id: null,
        target_external_account_id: null,
        confirm: true,
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["account", accountId] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      queryClient.invalidateQueries({ queryKey: ["accounts-admin"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({
        queryKey: ["migration-history", accountId],
      });
      toast({
        title: "Account migrated",
        description:
          data.message || `Provider changed to ${selectedTargetSource}`,
        status: "success",
        duration: 5000,
      });
      onMigrateClose();
      setMigrateStep(1);
      setSelectedTargetSource(null);
    },
    onError: (error: any) => {
      toast({
        title: "Migration failed",
        description: error.response?.data?.detail || "An error occurred",
        status: "error",
        duration: 5000,
      });
    },
  });

  // Fetch migration history
  interface MigrationLogEntry {
    id: string;
    source_provider: string;
    target_provider: string;
    status: string;
    initiated_at: string;
    completed_at: string | null;
    error_message: string | null;
  }

  const { data: migrationHistory } = useQuery<MigrationLogEntry[]>({
    queryKey: ["migration-history", accountId],
    queryFn: async () => {
      try {
        const response = await api.get(
          `/accounts/${accountId}/migration-history`,
        );
        return response.data;
      } catch {
        return [];
      }
    },
    enabled: !!accountId,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  // Salary estimate — only fetch for employer plan accounts without a salary set
  const isEmployerPlanAccount = account
    ? (EMPLOYER_MATCH_TYPES as readonly string[]).includes(account.account_type)
    : false;
  const { data: salaryEstimate } = useQuery<{
    estimated_annual_salary: number | null;
    source: string;
    note: string;
  }>({
    queryKey: ["salary-estimate", account?.user_id],
    queryFn: () =>
      api
        .get(
          `/retirement/salary-estimate${account?.user_id ? `?user_id=${account.user_id}` : ""}`,
        )
        .then((r) => r.data),
    enabled: isEmployerPlanAccount && !!account && account.annual_salary == null,
    staleTime: 5 * 60 * 1000,
  });

  // Update vehicle details mutation
  const updateVehicleMutation = useMutation({
    mutationFn: async (data: {
      mileage?: number;
      balance?: number;
      vin?: string;
      valuation_adjustment_pct?: number;
    }) => {
      const payload: any = {};
      if (data.mileage !== undefined) payload.vehicle_mileage = data.mileage;
      if (data.vin !== undefined) payload.vehicle_vin = data.vin.toUpperCase();
      if (data.balance !== undefined) payload.current_balance = data.balance;
      if (data.valuation_adjustment_pct !== undefined)
        payload.valuation_adjustment_pct = data.valuation_adjustment_pct;
      const response = await api.patch(`/accounts/${accountId}`, payload);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["account", accountId] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      toast({
        title: "Vehicle details updated",
        status: "success",
        duration: 3000,
      });
      setVehicleMileage("");
      setVehicleValue("");
      setVehicleVin("");
      setAdjustmentPct("");
    },
    onError: (error: any) => {
      toast({
        title: "Failed to update vehicle",
        description: error.response?.data?.detail || "An error occurred",
        status: "error",
        duration: 5000,
      });
    },
  });

  // Refresh auto-valuation mutation (property + vehicle)
  const refreshValuationMutation = useMutation({
    mutationFn: async () => {
      const params = selectedProvider ? `?provider=${selectedProvider}` : "";
      const response = await api.post(
        `/accounts/${accountId}/refresh-valuation${params}`,
      );
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["account", accountId] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      const fmt = (v: number) =>
        new Intl.NumberFormat("en-US", {
          style: "currency",
          currency: "USD",
          maximumFractionDigits: 0,
        }).format(v);
      const rangeStr =
        data.low && data.high
          ? ` (range ${fmt(data.low)} – ${fmt(data.high)})`
          : "";
      const vinInfo = data.vin_info
        ? ` · ${data.vin_info.year} ${data.vin_info.make} ${data.vin_info.model}`
        : "";
      const providerLabel = data.provider ? ` via ${data.provider}` : "";
      const adjStr =
        data.adjustment_pct && data.raw_value !== data.new_value
          ? ` (provider: ${fmt(data.raw_value)}, adjusted ${data.adjustment_pct > 0 ? "+" : ""}${data.adjustment_pct}%)`
          : "";
      toast({
        title: "Valuation refreshed",
        description: `Updated to ${fmt(data.new_value)}${adjStr}${rangeStr}${vinInfo}${providerLabel}`,
        status: "success",
        duration: 5000,
      });
    },
    onError: (error: any) => {
      toast({
        title: "Valuation refresh failed",
        description: error.response?.data?.detail || "An error occurred",
        status: "error",
        duration: 7000,
        isClosable: true,
      });
    },
  });

  // Equity price refresh mutation (stock_options + private_equity accounts)
  const equityRefreshMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post(`/accounts/${accountId}/equity-refresh`);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["account", accountId] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      const fmt = (v: number) =>
        new Intl.NumberFormat("en-US", {
          style: "currency",
          currency: "USD",
          maximumFractionDigits: 2,
        }).format(v);
      toast({
        title: "Price refreshed",
        description: `${data.symbol}: ${fmt(data.current_price)} × ${data.shares} shares = ${fmt(data.current_value)} via ${data.provider}`,
        status: "success",
        duration: 5000,
      });
    },
    onError: (error: any) => {
      toast({
        title: "Price refresh failed",
        description:
          error.response?.data?.detail ||
          "Could not fetch live price. Check that the ticker symbol is set in the account name.",
        status: "error",
        duration: 7000,
        isClosable: true,
      });
    },
  });

  // Sync transactions mutation
  const syncTransactionsMutation = useMutation({
    mutationFn: async (plaidItemId: string) => {
      const response = await api.post(
        `/plaid/sync-transactions/${plaidItemId}`,
      );
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["account", accountId] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      queryClient.invalidateQueries({ queryKey: ["accounts-admin"] });
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["infinite-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });

      const stats = data.stats;
      const message = stats
        ? `Synced: ${stats.added} added, ${stats.updated} updated, ${stats.skipped} skipped`
        : "Transactions synced successfully";

      toast({
        title: "Sync Complete",
        description: message,
        status: "success",
        duration: 5000,
        isClosable: true,
      });
    },
    onError: (error: any) => {
      const errorMessage =
        error?.response?.data?.detail || "Failed to sync transactions";
      toast({
        title: "Sync Failed",
        description: errorMessage,
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    },
  });

  // Delete holding mutation
  const deleteHoldingMutation = useMutation({
    mutationFn: (holdingId: string) => holdingsApi.deleteHolding(holdingId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["holdings", accountId] });
      queryClient.invalidateQueries({ queryKey: ["portfolio-widget"] });
      toast({ title: "Holding removed", status: "success", duration: 3000 });
    },
    onError: (error: any) => {
      toast({
        title: "Failed to remove holding",
        description: error.response?.data?.detail || "An error occurred",
        status: "error",
        duration: 5000,
      });
    },
  });

  // Update rental property fields mutation
  const updateRentalFieldsMutation = useMutation({
    mutationFn: (body: { is_rental_property?: boolean; rental_monthly_income?: number; rental_type?: string }) =>
      rentalPropertiesApi.updateRentalFields(account!.id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["account", accountId] });
      queryClient.invalidateQueries({ queryKey: ["rental-properties-summary"] });
      toast({ title: "Rental settings saved", status: "success", duration: 2000 });
    },
    onError: () => {
      toast({ title: "Failed to save rental settings", status: "error", duration: 3000 });
    },
  });

  // Sync rental state when account data changes
  useEffect(() => {
    if (account) {
      setIsRentalProperty(account.is_rental_property ?? false);
      setRentalMonthlyIncome(
        account.rental_monthly_income != null ? String(account.rental_monthly_income) : ""
      );
      setRentalType(account.rental_type ?? "");
    }
  }, [account?.is_rental_property, account?.rental_monthly_income, account?.rental_type]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "Never";
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "numeric",
    });
  };

  const formatLastSynced = (lastSyncedAt: string | null) => {
    if (!lastSyncedAt) return "Never synced";

    const date = new Date(lastSyncedAt);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: date.getFullYear() !== now.getFullYear() ? "numeric" : undefined,
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

  const handleToggleExcludeFromCashFlow = (
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    if (account) {
      updateAccountMutation.mutate({
        exclude_from_cash_flow: e.target.checked,
      });
    }
  };

  const handleToggleIncludeInNetworth = (
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    if (account) {
      updateAccountMutation.mutate({ include_in_networth: e.target.checked });
    }
  };

  const handleDelete = () => {
    deleteAccountMutation.mutate();
    onDeleteClose();
  };

  const handleUpdateVehicle = () => {
    const updates: {
      mileage?: number;
      balance?: number;
      vin?: string;
      valuation_adjustment_pct?: number;
    } = {};

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

    if (adjustmentPct) {
      const pct = parseFloat(adjustmentPct);
      if (!isNaN(pct)) updates.valuation_adjustment_pct = pct;
    }

    if (Object.keys(updates).length > 0) {
      updateVehicleMutation.mutate(updates);
    }
  };

  const handleUpdatePropertyDetails = () => {
    const payload: any = {};
    if (propertyAddress.trim())
      payload.property_address = propertyAddress.trim();
    if (propertyZip.trim()) payload.property_zip = propertyZip.trim();
    if (adjustmentPct) {
      const pct = parseFloat(adjustmentPct);
      if (!isNaN(pct)) payload.valuation_adjustment_pct = pct;
    }
    if (Object.keys(payload).length > 0) {
      updateAccountMutation.mutate(payload, {
        onSuccess: () => {
          setPropertyAddress("");
          setPropertyZip("");
          setAdjustmentPct("");
        },
      });
    }
  };

  const handleSaveLoanDetails = () => {
    const updates: {
      interest_rate?: number | null;
      loan_term_months?: number | null;
      origination_date?: string | null;
    } = {};

    if (loanInterestRate !== "") {
      const rate = parseFloat(loanInterestRate);
      if (!isNaN(rate) && rate >= 0) updates.interest_rate = rate;
    }
    if (loanTermYears !== "") {
      const years = parseFloat(loanTermYears);
      if (!isNaN(years) && years > 0)
        updates.loan_term_months = Math.round(years * 12);
    }
    if (loanOriginationDate !== "") {
      updates.origination_date = loanOriginationDate;
    }

    if (Object.keys(updates).length > 0) {
      updateAccountMutation.mutate(updates, {
        onSuccess: () => {
          setLoanInterestRate("");
          setLoanTermYears("");
          setLoanOriginationDate("");
        },
      });
    }
  };

  const handleSaveEquityDetails = () => {
    const updates: Record<string, unknown> = {};
    if (equityGrantType !== "") updates.grant_type = equityGrantType;
    if (equityQuantity !== "") {
      const v = parseFloat(equityQuantity);
      if (!isNaN(v) && v >= 0) updates.quantity = v;
    }
    if (equityStrikePrice !== "") {
      const v = parseFloat(equityStrikePrice);
      if (!isNaN(v) && v >= 0) updates.strike_price = v;
    }
    if (equitySharePrice !== "") {
      const v = parseFloat(equitySharePrice);
      if (!isNaN(v) && v >= 0) updates.share_price = v;
    }
    if (equityGrantDate !== "") updates.grant_date = equityGrantDate;
    if (equityCompanyStatus !== "") updates.company_status = equityCompanyStatus;
    // Merge vest rows with existing vesting schedule
    const allExistingRows: { date: string; quantity: number; notes?: string }[] = (() => {
      try { return account?.vesting_schedule ? JSON.parse(account.vesting_schedule) : []; }
      catch { return []; }
    })();
    const newValidRows = vestRows
      .filter((r) => r.date && r.quantity && !isNaN(parseFloat(r.quantity)))
      .map((r) => ({ date: r.date, quantity: parseFloat(r.quantity), ...(r.notes ? { notes: r.notes } : {}) }));
    if (newValidRows.length > 0) {
      updates.vesting_schedule = JSON.stringify([...allExistingRows, ...newValidRows]);
    }
    if (Object.keys(updates).length > 0) {
      updateAccountMutation.mutate(updates as Parameters<typeof updateAccountMutation.mutate>[0], {
        onSuccess: () => {
          setEquityGrantType("");
          setEquityQuantity("");
          setEquityStrikePrice("");
          setEquitySharePrice("");
          setEquityGrantDate("");
          setEquityCompanyStatus("");
          setVestRows([]);
        },
      });
    }
  };

  // Generate vesting rows from a common schedule template.
  // startDate: YYYY-MM-DD grant/cliff start, totalShares: total grant size.
  const applyVestTemplate = (
    template: string,
    startDate: string,
    totalShares: number,
  ) => {
    if (!startDate || !totalShares) return;
    const d = new Date(startDate + "T00:00:00");
    const addMonths = (base: Date, months: number): string => {
      const r = new Date(base);
      r.setMonth(r.getMonth() + months);
      return r.toISOString().slice(0, 10);
    };
    const fmt = (n: number) => String(Math.round(n * 10000) / 10000);

    type Row = { date: string; quantity: string; notes: string };
    let rows: Row[] = [];

    if (template === "4yr-1yr-cliff-monthly") {
      // 25% cliff at 12 months, then 1/48 per month for 36 more months
      const cliffShares = totalShares * 0.25;
      const remaining = totalShares - cliffShares;
      const monthly = remaining / 36;
      rows.push({ date: addMonths(d, 12), quantity: fmt(cliffShares), notes: "Cliff (1 year)" });
      for (let i = 1; i <= 36; i++) {
        rows.push({ date: addMonths(d, 12 + i), quantity: fmt(monthly), notes: `Month ${12 + i}` });
      }
    } else if (template === "4yr-quarterly") {
      // 16 quarterly events, equal shares, no cliff
      const perEvent = totalShares / 16;
      for (let i = 1; i <= 16; i++) {
        rows.push({ date: addMonths(d, i * 3), quantity: fmt(perEvent), notes: `Q${i}` });
      }
    } else if (template === "4yr-annual") {
      const perYear = totalShares / 4;
      for (let i = 1; i <= 4; i++) {
        rows.push({ date: addMonths(d, i * 12), quantity: fmt(perYear), notes: `Year ${i}` });
      }
    } else if (template === "3yr-annual") {
      const perYear = totalShares / 3;
      for (let i = 1; i <= 3; i++) {
        rows.push({ date: addMonths(d, i * 12), quantity: fmt(perYear), notes: `Year ${i}` });
      }
    } else if (template === "2yr-semi") {
      // Every 6 months for 2 years (4 events)
      const perEvent = totalShares / 4;
      for (let i = 1; i <= 4; i++) {
        rows.push({ date: addMonths(d, i * 6), quantity: fmt(perEvent), notes: `Semi-annual ${i}` });
      }
    } else if (template === "1yr-annual") {
      rows.push({ date: addMonths(d, 12), quantity: fmt(totalShares), notes: "Full vest" });
    } else if (template === "1yr-monthly") {
      // 12 equal monthly events over 1 year
      const perMonth = totalShares / 12;
      for (let i = 1; i <= 12; i++) {
        rows.push({ date: addMonths(d, i), quantity: fmt(perMonth), notes: `Month ${i}` });
      }
    } else if (template === "4yr-1yr-cliff-quarterly") {
      // 25% cliff at 12 months, then quarterly for 3 years (12 events)
      const cliffShares = totalShares * 0.25;
      const remaining = totalShares - cliffShares;
      const perQ = remaining / 12;
      rows.push({ date: addMonths(d, 12), quantity: fmt(cliffShares), notes: "Cliff (1 year)" });
      for (let i = 1; i <= 12; i++) {
        rows.push({ date: addMonths(d, 12 + i * 3), quantity: fmt(perQ), notes: `Q${i} post-cliff` });
      }
    }

    setVestRows(rows);
  };

  const handleSaveCashApy = () => {
    if (cashApyRate === "") return;
    const rate = parseFloat(cashApyRate);
    if (isNaN(rate) || rate < 0 || rate > 100) return;
    updateAccountMutation.mutate(
      { interest_rate: rate },
      { onSuccess: () => setCashApyRate("") },
    );
  };

  const handleSaveEmployerMatch = () => {
    const updates: {
      employer_match_percent?: number | null;
      employer_match_limit_percent?: number | null;
      annual_salary?: number | null;
    } = {};
    if (empMatchPct !== "") {
      const v = parseFloat(empMatchPct);
      if (!isNaN(v) && v >= 0) updates.employer_match_percent = v;
    }
    if (empMatchLimitPct !== "") {
      const v = parseFloat(empMatchLimitPct);
      if (!isNaN(v) && v >= 0) updates.employer_match_limit_percent = v;
    }
    if (empAnnualSalary !== "") {
      const v = parseFloat(empAnnualSalary);
      if (!isNaN(v) && v >= 0) updates.annual_salary = v;
    }
    if (Object.keys(updates).length > 0) {
      updateAccountMutation.mutate(updates, {
        onSuccess: () => {
          setEmpMatchPct("");
          setEmpMatchLimitPct("");
          setEmpAnnualSalary("");
        },
      });
    }
  };

  const handleSaveBalance = (rawValue: string, clearInput: () => void) => {
    const value = parseFloat(rawValue);
    if (!isNaN(value) && value >= 0) {
      updateAccountMutation.mutate(
        { current_balance: value },
        {
          onSuccess: clearInput,
        },
      );
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
    setEditedName("");
  };

  if (isLoading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" color="brand.500" />
      </Center>
    );
  }

  if (accountError) {
    return (
      <Container maxW="container.lg" py={8}>
        <Center py={16}>
          <VStack spacing={4}>
            <Alert status="error" borderRadius="md">
              <AlertIcon />
              <AlertTitle>Failed to load account.</AlertTitle>
              <AlertDescription>Please try again.</AlertDescription>
            </Alert>
            <Button colorScheme="blue" onClick={() => refetchAccount()}>
              Retry
            </Button>
          </VStack>
        </Center>
      </Container>
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
  const isSharedAccount =
    isCombinedView && account.plaid_item_hash && allAccounts
      ? allAccounts.filter(
          (acc) =>
            acc.plaid_item_hash === account.plaid_item_hash &&
            acc.plaid_item_hash !== null,
        ).length > 1
      : false;

  // Disable editing if:
  // 1. User doesn't own the account and has no write grant from the owner, OR
  // 2. Account is shared (linked by multiple users) — must edit in individual user view
  const canEditAccount =
    canWriteOwnedResource("account", account.user_id) && !isSharedAccount;

  const isAssetAccount = ASSET_ACCOUNT_TYPES.includes(account.account_type);
  const isManual = account.account_source === "manual";

  // Asset accounts (property, vehicle, etc.) don't have transaction flows
  const showTransactions = !isAssetAccount;
  // Recurring contributions only make sense for investment/savings account types
  const showContributions =
    isManual && CONTRIBUTION_ACCOUNT_TYPES.includes(account.account_type);
  // Show a balance update form for any manual account that doesn't already have its
  // own dedicated balance section (vehicle has a vehicle section, debt has a debt
  // section — everything else, including checking/savings/brokerage/crypto, shows this)
  const showUpdateBalance =
    isManual &&
    account.account_type !== "vehicle" &&
    !DEBT_ACCOUNT_TYPES.includes(account.account_type);
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
              onClick={() => {
                if (window.history.length > 1) {
                  navigate(-1);
                } else {
                  navigate("/accounts");
                }
              }}
              mb={2}
            >
              ← Back to Accounts
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
                    if (e.key === "Enter") {
                      handleSaveName();
                    } else if (e.key === "Escape") {
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
                    <Badge
                      colorScheme="gray"
                      display="flex"
                      alignItems="center"
                      gap={1}
                    >
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
              {formatAccountType(account.account_type, account.tax_treatment)}
              {account.mask &&
                account.account_type !== "vehicle" &&
                ` ••${account.mask}`}
            </Text>
          </Box>
          <Box textAlign="right">
            <Text fontSize="sm" color="text.secondary">
              Current Balance
            </Text>
            <Text
              fontSize="3xl"
              fontWeight="bold"
              color={isNegative ? "finance.negative" : "brand.accent"}
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
                  label={
                    !canEditAccount ? "You can only edit your own accounts" : ""
                  }
                  placement="top"
                  isDisabled={canEditAccount}
                >
                  <Select
                    value={account.account_type}
                    onChange={(e) => handleReclassify(e.target.value)}
                    size="sm"
                    isDisabled={!canEditAccount}
                  >
                    {[
                      "checking",
                      "savings",
                      "credit_card",
                      "brokerage",
                      "retirement_401k",
                      "retirement_403b",
                      "retirement_457b",
                      "retirement_ira",
                      "retirement_roth",
                      "retirement_sep_ira",
                      "retirement_simple_ira",
                      "retirement_529",
                      "hsa",
                      "loan",
                      "mortgage",
                      "student_loan",
                      "property",
                      "vehicle",
                      "crypto",
                      "stock_options",
                      "private_equity",
                      "business_equity",
                      "collectibles",
                      "precious_metals",
                      "manual",
                      "other",
                    ].map((value) => (
                      <option key={value} value={value}>
                        {formatAccountType(value)}
                      </option>
                    ))}
                  </Select>
                </Tooltip>
              </FormControl>

              {/* Tax Treatment — for retirement/investment accounts */}
              {(TAX_TREATMENT_ACCOUNT_TYPES as readonly string[]).includes(
                account.account_type,
              ) && (
                <FormControl>
                  <FormLabel fontSize="sm">Tax Treatment</FormLabel>
                  <Tooltip
                    label={
                      !canEditAccount
                        ? "You can only edit your own accounts"
                        : account.account_source !== "manual"
                          ? "Override the provider's default if incorrect"
                          : ""
                    }
                    placement="top"
                    isDisabled={
                      canEditAccount && account.account_source === "manual"
                    }
                  >
                    <Select
                      value={account.tax_treatment || ""}
                      onChange={(e) => {
                        updateAccountMutation.mutate({
                          tax_treatment: e.target.value || null,
                        });
                      }}
                      size="sm"
                      isDisabled={!canEditAccount}
                    >
                      <option value="">Not specified</option>
                      <option value="pre_tax">Traditional (Pre-Tax)</option>
                      <option value="roth">Roth (After-Tax)</option>
                      <option value="taxable">Taxable</option>
                      <option value="tax_free">Tax-Free (HSA/529)</option>
                    </Select>
                  </Tooltip>
                  {!account.tax_treatment && (
                    <Text fontSize="xs" color="text.muted" mt={1}>
                      Affects how this account is counted in your tax projections and retirement planning. Traditional = pre-tax contributions, taxed on withdrawal. Roth = after-tax contributions, tax-free growth. Taxable = brokerage/checking. Tax-Free = HSA/529.
                    </Text>
                  )}
                  {account.account_source === "mx" &&
                    !account.tax_treatment && (
                      <Text fontSize="xs" color="orange.500" mt={1}>
                        MX doesn't distinguish Roth vs Traditional. Please
                        select the correct tax treatment.
                      </Text>
                    )}
                </FormControl>
              )}

              {/* Hide from Reports */}
              <FormControl display="flex" alignItems="center">
                <FormLabel fontSize="sm" mb={0} flex={1}>
                  Hide from all reports
                </FormLabel>
                <Tooltip
                  label={
                    !canEditAccount ? "You can only edit your own accounts" : ""
                  }
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
                    <HelpHint hint={helpContent.accounts.excludeFromCashFlow} />
                  </FormLabel>
                  <Text fontSize="xs" color="text.muted" mt={0.5}>
                    Prevents double-counting (e.g., mortgage payments already
                    tracked in checking account)
                  </Text>
                </Box>
                <Tooltip
                  label={
                    !canEditAccount ? "You can only edit your own accounts" : ""
                  }
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

              {/* Include in Net Worth — shown for all non-vehicle accounts;
                  vehicle accounts have this toggle in their dedicated section */}
              {account.account_type !== "vehicle" && (
                <FormControl display="flex" alignItems="center">
                  <Box flex={1}>
                    <FormLabel fontSize="sm" mb={0}>
                      Include in Net Worth
                    </FormLabel>
                    <Text fontSize="xs" color="text.muted" mt={0.5}>
                      When off, this account's balance won't be counted in your
                      net worth
                    </Text>
                  </Box>
                  <Tooltip
                    label={
                      !canEditAccount
                        ? "You can only edit your own accounts"
                        : ""
                    }
                    placement="top"
                    isDisabled={canEditAccount}
                  >
                    <Switch
                      id="include-in-networth-toggle"
                      isChecked={account.include_in_networth ?? true}
                      onChange={handleToggleIncludeInNetworth}
                      colorScheme="brand"
                      isDisabled={!canEditAccount}
                    />
                  </Tooltip>
                </FormControl>
              )}

              {/* Account Info */}
              <Box>
                <HStack justify="space-between" align="start">
                  <Box>
                    <Text
                      fontSize="sm"
                      fontWeight="medium"
                      color="text.secondary"
                    >
                      Account Source
                    </Text>
                    <Text fontSize="sm">
                      {account.account_source.toUpperCase()}
                      {account.institution_name &&
                        ` - ${account.institution_name}`}
                    </Text>
                  </Box>
                  {canEditAccount && account.is_active && (
                    <Tooltip label="Change account provider" placement="top">
                      <Button
                        size="xs"
                        variant="outline"
                        leftIcon={<FiRepeat />}
                        onClick={() => {
                          setMigrateStep(1);
                          setSelectedTargetSource(null);
                          onMigrateOpen();
                        }}
                      >
                        Change Provider
                      </Button>
                    </Tooltip>
                  )}
                </HStack>
                {migrationHistory && migrationHistory.length > 0 && (
                  <Box mt={2}>
                    <Button
                      variant="link"
                      size="xs"
                      color="text.secondary"
                      onClick={() =>
                        setShowMigrationHistory(!showMigrationHistory)
                      }
                    >
                      {showMigrationHistory ? "Hide" : "Show"} migration history
                      ({migrationHistory.length})
                    </Button>
                    <Collapse in={showMigrationHistory} animateOpacity>
                      <VStack align="stretch" spacing={1} mt={2}>
                        {migrationHistory.map((entry) => (
                          <HStack
                            key={entry.id}
                            fontSize="xs"
                            color="text.secondary"
                            spacing={2}
                          >
                            <Text>
                              {new Date(
                                entry.initiated_at,
                              ).toLocaleDateString()}
                            </Text>
                            <Text>
                              {entry.source_provider.toUpperCase()} →{" "}
                              {entry.target_provider.toUpperCase()}
                            </Text>
                            <Badge
                              size="sm"
                              colorScheme={
                                entry.status === "completed"
                                  ? "green"
                                  : entry.status === "failed"
                                    ? "red"
                                    : "yellow"
                              }
                              fontSize="2xs"
                            >
                              {entry.status}
                            </Badge>
                          </HStack>
                        ))}
                      </VStack>
                    </Collapse>
                  </Box>
                )}
              </Box>

              {/* Sync Status - Only for Plaid accounts */}
              {account.plaid_item_id && (
                <Box>
                  <HStack justify="space-between" mb={2}>
                    <Text
                      fontSize="sm"
                      fontWeight="medium"
                      color="text.secondary"
                    >
                      Sync Status
                    </Text>
                    <Tooltip
                      label="Refresh transactions from bank"
                      placement="top"
                    >
                      <IconButton
                        icon={<FiRefreshCw />}
                        size="xs"
                        variant="ghost"
                        aria-label="Sync transactions"
                        onClick={() =>
                          syncTransactionsMutation.mutate(
                            account.plaid_item_id!,
                          )
                        }
                        isLoading={syncTransactionsMutation.isPending}
                        isDisabled={syncTransactionsMutation.isPending}
                      />
                    </Tooltip>
                  </HStack>
                  <VStack align="stretch" spacing={1}>
                    <HStack>
                      <Text fontSize="sm" color="text.secondary">
                        Last synced:
                      </Text>
                      <Text fontSize="sm" fontWeight="medium">
                        {formatLastSynced(account.last_synced_at)}
                      </Text>
                    </HStack>
                    {(account.last_error_code || account.needs_reauth) && (
                      <HStack>
                        <Badge
                          colorScheme={account.needs_reauth ? "orange" : "red"}
                          fontSize="xs"
                        >
                          {account.needs_reauth
                            ? "Reauthentication Required"
                            : "Sync Error"}
                        </Badge>
                        {account.last_error_message && (
                          <Tooltip
                            label={account.last_error_message}
                            placement="top"
                          >
                            <Text
                              fontSize="xs"
                              color="text.secondary"
                              noOfLines={1}
                            >
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
                  label={
                    !canEditAccount
                      ? "You can only delete your own accounts"
                      : ""
                  }
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
                  This will permanently delete this account and all associated
                  transactions.
                </Text>
              </Box>
            </VStack>
          </CardBody>
        </Card>

        {/* Vehicle Details Section - Only for vehicle accounts */}
        {account.account_type === "vehicle" && (
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
                        {availableProviders.map((p) => (
                          <option key={p} value={p}>
                            {p}
                          </option>
                        ))}
                      </Select>
                    )}
                    <Tooltip
                      label={
                        !account.vehicle_vin
                          ? "Add VIN below to enable auto-valuation"
                          : availableProviders.length === 0
                            ? "No valuation provider configured"
                            : "Fetch current market value"
                      }
                      placement="top"
                    >
                      <Button
                        size="sm"
                        leftIcon={<FiRefreshCw />}
                        variant="outline"
                        onClick={() => refreshValuationMutation.mutate()}
                        isLoading={refreshValuationMutation.isPending}
                        isDisabled={
                          !account.vehicle_vin ||
                          availableProviders.length === 0
                        }
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
                    <Text fontSize="xs" color="text.muted">
                      Current Mileage
                    </Text>
                    <Text fontWeight="semibold">
                      {account.vehicle_mileage != null
                        ? `${account.vehicle_mileage.toLocaleString()} miles`
                        : "Not set"}
                    </Text>
                  </Box>
                  <Box>
                    <Text fontSize="xs" color="text.muted">
                      VIN
                    </Text>
                    <Text fontWeight="semibold" fontFamily="mono" fontSize="sm">
                      {account.vehicle_vin ?? "Not set"}
                    </Text>
                  </Box>
                  {account.last_auto_valued_at && (
                    <Box>
                      <Text fontSize="xs" color="text.muted">
                        Last Auto-Valued
                      </Text>
                      <Text fontWeight="semibold" fontSize="sm">
                        {formatLastSynced(account.last_auto_valued_at)}
                      </Text>
                    </Box>
                  )}
                  <Box>
                    <Text fontSize="xs" color="text.muted">
                      Valuation Adjustment
                    </Text>
                    <Text
                      fontWeight="semibold"
                      fontSize="sm"
                      color={
                        account.valuation_adjustment_pct != null &&
                        account.valuation_adjustment_pct !== 0
                          ? account.valuation_adjustment_pct > 0
                            ? "finance.positive"
                            : "finance.negative"
                          : undefined
                      }
                    >
                      {account.valuation_adjustment_pct != null &&
                      account.valuation_adjustment_pct !== 0
                        ? `${account.valuation_adjustment_pct > 0 ? "+" : ""}${account.valuation_adjustment_pct}%`
                        : "None"}
                    </Text>
                  </Box>
                </HStack>

                <Divider />

                {/* Investment toggle */}
                <FormControl>
                  <HStack justify="space-between" align="center">
                    <FormLabel
                      htmlFor="vehicle-networth-toggle"
                      mb="0"
                      fontSize="sm"
                    >
                      Count as Investment in Net Worth
                    </FormLabel>
                    <Tooltip
                      label={
                        !canEditAccount
                          ? "You can only edit your own accounts"
                          : ""
                      }
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
                    Enable for classic or collectible vehicles you consider an
                    investment.
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
                      <FormLabel fontSize="sm">
                        VIN (for auto-valuation)
                      </FormLabel>
                      <Input
                        value={vehicleVin}
                        onChange={(e) =>
                          setVehicleVin(e.target.value.toUpperCase())
                        }
                        placeholder={
                          account.vehicle_vin ?? "e.g., 1HGBH41JXMN109186"
                        }
                        maxLength={17}
                        size="sm"
                        fontFamily="mono"
                      />
                      <Text fontSize="xs" color="text.muted" mt={1}>
                        17-character VIN enables automatic market value updates.
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
                          <NumberInputField
                            placeholder={
                              account.vehicle_mileage != null
                                ? String(account.vehicle_mileage)
                                : "Enter mileage"
                            }
                          />
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

                    {/* Valuation Adjustment */}
                    <FormControl>
                      <FormLabel fontSize="sm">
                        Valuation Adjustment (%)
                      </FormLabel>
                      <HStack>
                        <NumberInput
                          value={adjustmentPct}
                          onChange={setAdjustmentPct}
                          precision={2}
                          step={1}
                          size="sm"
                        >
                          <NumberInputField
                            placeholder={
                              account.valuation_adjustment_pct != null
                                ? String(account.valuation_adjustment_pct)
                                : "0"
                            }
                          />
                        </NumberInput>
                        <Text fontSize="sm" color="text.secondary">
                          %
                        </Text>
                      </HStack>
                      <Text fontSize="xs" color="text.muted" mt={1}>
                        Negative for damage/wear, positive for upgrades. Applied
                        on top of auto-valuation estimates.
                      </Text>
                    </FormControl>

                    {/* Save Button */}
                    <Button
                      colorScheme="brand"
                      size="sm"
                      onClick={handleUpdateVehicle}
                      isLoading={updateVehicleMutation.isPending}
                      isDisabled={
                        !vehicleMileage &&
                        !vehicleValue &&
                        !vehicleVin.trim() &&
                        !adjustmentPct
                      }
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
        {account.account_type === "property" && (
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
                        {availableProviders.map((p) => (
                          <option key={p} value={p}>
                            {p}
                          </option>
                        ))}
                      </Select>
                    )}
                    <Tooltip
                      label={
                        !account.property_address || !account.property_zip
                          ? "Add address and ZIP below to enable auto-valuation"
                          : availableProviders.length === 0
                            ? "No valuation provider configured"
                            : "Fetch current estimated value"
                      }
                      placement="top"
                    >
                      <Button
                        size="sm"
                        leftIcon={<FiRefreshCw />}
                        variant="outline"
                        onClick={() => refreshValuationMutation.mutate()}
                        isLoading={refreshValuationMutation.isPending}
                        isDisabled={
                          !account.property_address ||
                          !account.property_zip ||
                          availableProviders.length === 0
                        }
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
                    <Text fontSize="xs" color="text.muted">
                      Address
                    </Text>
                    <Text fontWeight="semibold" fontSize="sm">
                      {account.property_address
                        ? `${account.property_address}${account.property_zip ? `, ${account.property_zip}` : ""}`
                        : "Not set"}
                    </Text>
                  </Box>
                  {account.last_auto_valued_at && (
                    <Box>
                      <Text fontSize="xs" color="text.muted">
                        Last Auto-Valued
                      </Text>
                      <Text fontWeight="semibold" fontSize="sm">
                        {formatLastSynced(account.last_auto_valued_at)}
                      </Text>
                    </Box>
                  )}
                  <Box>
                    <Text fontSize="xs" color="text.muted">
                      Valuation Adjustment
                    </Text>
                    <Text
                      fontWeight="semibold"
                      fontSize="sm"
                      color={
                        account.valuation_adjustment_pct != null &&
                        account.valuation_adjustment_pct !== 0
                          ? account.valuation_adjustment_pct > 0
                            ? "finance.positive"
                            : "finance.negative"
                          : undefined
                      }
                    >
                      {account.valuation_adjustment_pct != null &&
                      account.valuation_adjustment_pct !== 0
                        ? `${account.valuation_adjustment_pct > 0 ? "+" : ""}${account.valuation_adjustment_pct}%`
                        : "None"}
                    </Text>
                  </Box>
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
                          placeholder={
                            account.property_address ?? "e.g., 123 Main St"
                          }
                          size="sm"
                        />
                      </FormControl>
                      <FormControl flex={1}>
                        <FormLabel fontSize="sm">ZIP Code</FormLabel>
                        <Input
                          value={propertyZip}
                          onChange={(e) => setPropertyZip(e.target.value)}
                          placeholder={account.property_zip ?? "e.g., 94102"}
                          maxLength={10}
                          size="sm"
                        />
                      </FormControl>
                    </HStack>
                    <FormControl>
                      <FormLabel fontSize="sm">
                        Valuation Adjustment (%)
                      </FormLabel>
                      <HStack>
                        <NumberInput
                          value={adjustmentPct}
                          onChange={setAdjustmentPct}
                          precision={2}
                          step={1}
                          size="sm"
                        >
                          <NumberInputField
                            placeholder={
                              account.valuation_adjustment_pct != null
                                ? String(account.valuation_adjustment_pct)
                                : "0"
                            }
                          />
                        </NumberInput>
                        <Text fontSize="sm" color="text.secondary">
                          %
                        </Text>
                      </HStack>
                      <Text fontSize="xs" color="text.muted" mt={1}>
                        Negative for damage/wear, positive for upgrades. Applied
                        on top of auto-valuation estimates.
                      </Text>
                    </FormControl>
                    <Button
                      colorScheme="brand"
                      size="sm"
                      onClick={handleUpdatePropertyDetails}
                      isLoading={updateAccountMutation.isPending}
                      isDisabled={
                        !propertyAddress.trim() &&
                        !propertyZip.trim() &&
                        !adjustmentPct
                      }
                    >
                      Save Property Details
                    </Button>
                    <Text fontSize="xs" color="text.muted">
                      Address and ZIP are used to fetch automated property
                      valuations.
                    </Text>
                    <Divider />
                    <HStack justify="space-between" align="center">
                      <Box>
                        <Text fontSize="sm" fontWeight="medium">Rental Property</Text>
                        <Text fontSize="xs" color="text.muted">Track this property in Rental Properties P&L</Text>
                      </Box>
                      <Switch
                        isChecked={isRentalProperty}
                        onChange={(e) => {
                          setIsRentalProperty(e.target.checked);
                          updateRentalFieldsMutation.mutate({ is_rental_property: e.target.checked });
                        }}
                        colorScheme="brand"
                      />
                    </HStack>
                    {isRentalProperty && (
                      <FormControl>
                        <FormLabel fontSize="sm">Monthly Rental Income ($)</FormLabel>
                        <HStack>
                          <NumberInput
                            value={rentalMonthlyIncome}
                            onChange={(val) => setRentalMonthlyIncome(val)}
                            min={0}
                            step={100}
                            size="sm"
                            maxW="180px"
                          >
                            <NumberInputField placeholder="e.g., 2500" />
                          </NumberInput>
                          <Button
                            size="sm"
                            colorScheme="brand"
                            variant="outline"
                            isLoading={updateRentalFieldsMutation.isPending}
                            onClick={() => {
                              const amount = parseFloat(rentalMonthlyIncome);
                              if (!isNaN(amount)) {
                                updateRentalFieldsMutation.mutate({ rental_monthly_income: amount });
                              }
                            }}
                          >
                            Save
                          </Button>
                        </HStack>
                        <Text fontSize="xs" color="text.muted" mt={1}>
                          Used for cap rate and P&amp;L calculations in Rental Properties.
                        </Text>
                      </FormControl>
                    )}
                    {isRentalProperty && (
                      <FormControl>
                        <FormLabel fontSize="sm">Rental Strategy</FormLabel>
                        <Select
                          size="sm"
                          value={rentalType}
                          onChange={(e) => {
                            setRentalType(e.target.value);
                            updateRentalFieldsMutation.mutate({ rental_type: e.target.value });
                          }}
                        >
                          <option value="">Not specified</option>
                          <option value="buy_and_hold">Buy and Hold</option>
                          <option value="long_term_rental">Long-Term Rental (12+ months)</option>
                          <option value="short_term_rental">Short-Term Rental (Airbnb/VRBO)</option>
                        </Select>
                        <Text fontSize="xs" color="text.muted" mt={1}>
                          STR may qualify for passive loss offset (IRC §469) if you materially participate.
                        </Text>
                      </FormControl>
                    )}
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
                {account.account_source !== "manual"
                  ? "Your bank may not provide these details. Enter them manually to enable cash flow projections and debt payoff planning."
                  : "Used for cash flow projections and debt payoff planning."}
              </Text>
              <VStack spacing={4} align="stretch">
                {/* Current values display */}
                {(account.interest_rate ||
                  account.loan_term_months ||
                  account.origination_date) && (
                  <>
                    <HStack spacing={6} wrap="wrap">
                      {account.interest_rate != null && (
                        <Box>
                          <Text fontSize="xs" color="text.muted">
                            Interest Rate
                          </Text>
                          <Text fontWeight="semibold">
                            {account.interest_rate}%
                          </Text>
                        </Box>
                      )}
                      {account.loan_term_months != null && (
                        <Box>
                          <Text fontSize="xs" color="text.muted">
                            Loan Term
                          </Text>
                          <Text fontWeight="semibold">
                            {account.loan_term_months >= 12
                              ? `${Math.round(account.loan_term_months / 12)} years`
                              : `${account.loan_term_months} months`}
                          </Text>
                        </Box>
                      )}
                      {account.origination_date && (
                        <Box>
                          <Text fontSize="xs" color="text.muted">
                            Loan Start
                          </Text>
                          <Text fontWeight="semibold">
                            {new Date(
                              account.origination_date,
                            ).toLocaleDateString("en-US", {
                              month: "short",
                              year: "numeric",
                            })}
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
                      <FormLabel fontSize="sm">
                        Interest Rate (%)
                        <HelpHint hint={helpContent.accounts.interestRate} />
                      </FormLabel>
                      <NumberInput
                        value={loanInterestRate}
                        onChange={setLoanInterestRate}
                        precision={3}
                        step={0.125}
                        min={0}
                        max={100}
                        size="sm"
                      >
                        <NumberInputField
                          placeholder={
                            account.interest_rate != null
                              ? String(account.interest_rate)
                              : "e.g., 6.75"
                          }
                        />
                      </NumberInput>
                    </FormControl>

                    <FormControl>
                      <FormLabel fontSize="sm">
                        Loan Term (years)
                        <HelpHint hint={helpContent.accounts.loanTerm} />
                      </FormLabel>
                      <NumberInput
                        value={loanTermYears}
                        onChange={setLoanTermYears}
                        precision={1}
                        step={1}
                        min={1}
                        max={50}
                        size="sm"
                      >
                        <NumberInputField
                          placeholder={
                            account.loan_term_months != null
                              ? String(
                                  Math.round(account.loan_term_months / 12),
                                )
                              : "e.g., 30"
                          }
                        />
                      </NumberInput>
                    </FormControl>

                    <FormControl>
                      <FormLabel fontSize="sm">
                        Loan Start Date
                        <HelpHint hint={helpContent.accounts.originationDate} />
                      </FormLabel>
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
                      isDisabled={
                        !loanInterestRate &&
                        !loanTermYears &&
                        !loanOriginationDate
                      }
                    >
                      Save Loan Details
                    </Button>
                  </>
                )}
              </VStack>
            </CardBody>
          </Card>
        )}

        {/* APY / Interest Rate Section - For cash accounts (checking, savings, money market) */}
        {CASH_ACCOUNT_TYPES.includes(account.account_type) && (
          <Card>
            <CardBody>
              <Heading size="md" mb={1}>
                APY / Interest Rate
              </Heading>
              <Text fontSize="sm" color="text.muted" mb={4}>
                Enter your account's annual percentage yield (APY). Used in
                retirement projections and cash-flow forecasts. Plaid, Teller,
                and MX don't always provide this — you can enter it manually.
              </Text>
              <VStack spacing={4} align="stretch">
                {account.interest_rate != null && (
                  <HStack>
                    <Box>
                      <Text fontSize="xs" color="text.muted">Current APY</Text>
                      <Text fontWeight="semibold">{account.interest_rate}%</Text>
                    </Box>
                  </HStack>
                )}
                {canEditAccount && (
                  <HStack>
                    <NumberInput
                      value={cashApyRate}
                      onChange={setCashApyRate}
                      precision={3}
                      step={0.1}
                      min={0}
                      max={100}
                      size="sm"
                      w="160px"
                    >
                      <NumberInputField placeholder={account.interest_rate != null ? `${account.interest_rate}` : "e.g. 4.50"} />
                    </NumberInput>
                    <Text fontSize="sm" color="text.muted">%</Text>
                    <Button
                      size="sm"
                      colorScheme="blue"
                      onClick={handleSaveCashApy}
                      isLoading={updateAccountMutation.isPending}
                      isDisabled={!cashApyRate}
                    >
                      Save
                    </Button>
                    {account.interest_rate != null && (
                      <Button
                        size="sm"
                        variant="ghost"
                        colorScheme="red"
                        onClick={() =>
                          updateAccountMutation.mutate({ interest_rate: null })
                        }
                        isLoading={updateAccountMutation.isPending}
                      >
                        Clear
                      </Button>
                    )}
                  </HStack>
                )}
              </VStack>
            </CardBody>
          </Card>
        )}

        {/* Employer Match Section - For 401k / 403b accounts */}
        {(EMPLOYER_MATCH_TYPES as readonly string[]).includes(
          account.account_type,
        ) && (
          <Card>
            <CardBody>
              <Heading size="md" mb={1}>
                Employer Match
              </Heading>
              <Text fontSize="sm" color="text.secondary" mb={4}>
                Track how much your employer contributes to see your true total
                retirement savings rate.
              </Text>

              {/* Current values display */}
              {(account.employer_match_percent != null ||
                account.employer_match_limit_percent != null ||
                account.annual_salary != null) && (
                <>
                  <HStack spacing={6} wrap="wrap" mb={4}>
                    {account.employer_match_percent != null && (
                      <Box>
                        <Text fontSize="xs" color="text.muted">
                          Employer Matches
                        </Text>
                        <Text fontWeight="semibold">
                          {account.employer_match_percent}% of your contribution
                        </Text>
                      </Box>
                    )}
                    {account.employer_match_limit_percent != null && (
                      <Box>
                        <Text fontSize="xs" color="text.muted">
                          On First
                        </Text>
                        <Text fontWeight="semibold">
                          {account.employer_match_limit_percent}% of salary
                        </Text>
                      </Box>
                    )}
                    {account.annual_salary != null && (
                      <Box>
                        <Text fontSize="xs" color="text.muted">
                          Annual Salary
                        </Text>
                        <Text fontWeight="semibold">
                          {formatCurrency(account.annual_salary)}
                        </Text>
                      </Box>
                    )}
                    {/* Computed annual employer contribution */}
                    {account.employer_match_percent != null &&
                      account.employer_match_limit_percent != null &&
                      account.annual_salary != null &&
                      (() => {
                        const matchablePct = Math.min(
                          account.employer_match_limit_percent,
                          account.employer_match_limit_percent,
                        );
                        const annualMatch =
                          (matchablePct / 100) *
                          (account.employer_match_percent / 100) *
                          account.annual_salary;
                        const monthlyMatch = annualMatch / 12;
                        return (
                          <Box
                            bg="bg.success"
                            px={3}
                            py={2}
                            borderRadius="md"
                            borderWidth="1px"
                            borderColor="green.200"
                          >
                            <Text fontSize="xs" color="green.700">
                              Employer Contributes
                            </Text>
                            <Text fontWeight="bold" color="green.700">
                              {formatCurrency(annualMatch)}/yr &nbsp;·&nbsp;{" "}
                              {formatCurrency(monthlyMatch)}/mo
                            </Text>
                          </Box>
                        );
                      })()}
                  </HStack>
                  <Divider mb={4} />
                </>
              )}

              {!canEditAccount ? (
                <Text fontSize="sm" color="text.secondary">
                  Employer match can only be updated by the account owner.
                </Text>
              ) : (
                <>
                  <HStack spacing={4} align="end" wrap="wrap">
                    <FormControl maxW="160px">
                      <FormLabel fontSize="sm" display="flex" alignItems="center">
                        Employer Match (%)
                        <HelpHint hint={helpContent.accounts.employerMatch} />
                      </FormLabel>
                      <NumberInput
                        value={empMatchPct}
                        onChange={setEmpMatchPct}
                        min={0}
                        max={200}
                        precision={2}
                        size="sm"
                      >
                        <NumberInputField
                          placeholder={
                            account.employer_match_percent != null
                              ? String(account.employer_match_percent)
                              : "e.g., 50"
                          }
                        />
                      </NumberInput>
                    </FormControl>
                    <FormControl maxW="160px">
                      <FormLabel fontSize="sm">
                        Up to (% of salary)
                        <HelpHint
                          hint={helpContent.accounts.employerMatchLimit}
                        />
                      </FormLabel>
                      <NumberInput
                        value={empMatchLimitPct}
                        onChange={setEmpMatchLimitPct}
                        min={0}
                        max={100}
                        precision={2}
                        size="sm"
                      >
                        <NumberInputField
                          placeholder={
                            account.employer_match_limit_percent != null
                              ? String(account.employer_match_limit_percent)
                              : "e.g., 6"
                          }
                        />
                      </NumberInput>
                    </FormControl>
                    <FormControl maxW="200px">
                      <FormLabel fontSize="sm">Annual Salary ($)</FormLabel>
                      <NumberInput
                        value={empAnnualSalary}
                        onChange={setEmpAnnualSalary}
                        min={0}
                        precision={0}
                        size="sm"
                      >
                        <NumberInputField
                          placeholder={
                            account.annual_salary != null
                              ? String(account.annual_salary)
                              : salaryEstimate?.estimated_annual_salary != null
                                ? `~${Math.round(salaryEstimate.estimated_annual_salary).toLocaleString()} (estimated)`
                                : "e.g., 100000"
                          }
                        />
                      </NumberInput>
                      {salaryEstimate?.estimated_annual_salary != null &&
                        account.annual_salary == null &&
                        empAnnualSalary === "" && (
                          <Text
                            fontSize="xs"
                            color="blue.500"
                            mt={1}
                            cursor="pointer"
                            onClick={() =>
                              setEmpAnnualSalary(
                                String(
                                  Math.round(
                                    salaryEstimate.estimated_annual_salary!,
                                  ),
                                ),
                              )
                            }
                          >
                            Use estimated: $
                            {Math.round(
                              salaryEstimate.estimated_annual_salary,
                            ).toLocaleString()}{" "}
                            (last 12 months income)
                          </Text>
                        )}
                    </FormControl>
                  </HStack>
                  <Button
                    mt={4}
                    size="sm"
                    colorScheme="blue"
                    onClick={handleSaveEmployerMatch}
                    isLoading={updateAccountMutation.isPending}
                    isDisabled={
                      !empMatchPct && !empMatchLimitPct && !empAnnualSalary
                    }
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
                      <Th isNumeric>
                        {account.account_type === "crypto" ? "Coins" : "Shares"}
                      </Th>
                      <Th isNumeric>
                        {account.account_type === "crypto"
                          ? "Cost/Coin"
                          : "Cost Basis/Share"}
                      </Th>
                      <Th isNumeric>Current Value</Th>
                      {canEditAccount && isManual && <Th />}
                    </Tr>
                  </Thead>
                  <Tbody>
                    {accountHoldings.map((h) => (
                      <Tr key={h.id}>
                        <Td fontWeight="bold">{h.ticker}</Td>
                        <Td color="text.secondary">{h.name || "—"}</Td>
                        <Td isNumeric>
                          {Number(h.shares).toLocaleString(undefined, {
                            maximumFractionDigits: 6,
                          })}
                        </Td>
                        <Td isNumeric>
                          {h.cost_basis_per_share != null
                            ? formatCurrency(Number(h.cost_basis_per_share))
                            : "—"}
                        </Td>
                        <Td isNumeric fontWeight="medium">
                          {h.current_value != null
                            ? formatCurrency(Number(h.current_value))
                            : "—"}
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
                                onClick={() =>
                                  deleteHoldingMutation.mutate(h.id)
                                }
                                isLoading={
                                  deleteHoldingMutation.isPending &&
                                  deleteHoldingMutation.variables === h.id
                                }
                                isDisabled={
                                  deleteHoldingMutation.isPending &&
                                  deleteHoldingMutation.variables !== h.id
                                }
                              />
                            </Tooltip>
                          </Td>
                        )}
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              ) : (
                <Text
                  color="text.muted"
                  fontSize="sm"
                  textAlign="center"
                  py={6}
                >
                  {isManual
                    ? 'No holdings yet. Use "Add Holding" to record your positions.'
                    : "Holdings are synced from your brokerage."}
                </Text>
              )}
            </CardBody>
          </Card>
        )}

        {/* Tax Lots & Gains - For investment accounts with holdings */}
        {showHoldings && accountHoldings && accountHoldings.length > 0 && (
          <TaxLotsPanel
            accountId={accountId!}
            holdings={accountHoldings.map((h) => ({
              id: h.id,
              ticker: h.ticker,
              name: h.name || null,
              shares: Number(h.shares),
            }))}
            canEdit={canEditAccount}
          />
        )}

        {/* Balance Reconciliation - For bank-connected accounts */}
        {account?.last_synced_at && (
          <ReconciliationCard accountId={accountId!} />
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
                      <FormLabel fontSize="sm">
                        Current Balance Owed ($)
                      </FormLabel>
                      <HStack>
                        <Text fontSize="sm">$</Text>
                        <NumberInput
                          value={debtBalance}
                          onChange={setDebtBalance}
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
                      onClick={() =>
                        handleSaveBalance(debtBalance, () => setDebtBalance(""))
                      }
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
                {isAssetAccount ? "Update Value" : "Update Balance"}
              </Heading>
              <Text fontSize="sm" color="text.muted" mb={4}>
                {isAssetAccount
                  ? "Enter the current market value of this asset to keep your net worth up to date."
                  : "Set the current balance to keep your account accurate."}
              </Text>
              <VStack spacing={4} align="stretch">
                {!canEditAccount ? (
                  <Text fontSize="sm" color="text.secondary">
                    {isAssetAccount
                      ? "Value can only be updated by the account owner."
                      : "Balance can only be updated by the account owner."}
                  </Text>
                ) : (
                  <>
                    <FormControl>
                      <FormLabel fontSize="sm">
                        {isAssetAccount
                          ? "Current Value ($)"
                          : "Current Balance ($)"}
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
                      onClick={() =>
                        handleSaveBalance(manualBalance, () =>
                          setManualBalance(""),
                        )
                      }
                      isLoading={updateAccountMutation.isPending}
                      isDisabled={!manualBalance}
                    >
                      {isAssetAccount ? "Save Value" : "Save Balance"}
                    </Button>
                  </>
                )}
              </VStack>
            </CardBody>
          </Card>
        )}

        {/* Equity Price Refresh - For stock_options and private_equity manual accounts */}
        {isManual &&
          (account.account_type === "stock_options" ||
            account.account_type === "private_equity") && (
            <Card>
              <CardBody>
                <Heading size="md" mb={1}>
                  Live Price Refresh
                </Heading>
                <Text fontSize="sm" color="text.muted" mb={4}>
                  Fetch the current market price for this equity and update the
                  account value. The ticker symbol is read from the account name
                  or institution (e.g. "AAPL" or "MSFT").
                </Text>
                <Button
                  leftIcon={<FiRefreshCw />}
                  colorScheme="brand"
                  size="sm"
                  onClick={() => equityRefreshMutation.mutate()}
                  isLoading={equityRefreshMutation.isPending}
                  isDisabled={!canEditAccount}
                >
                  Refresh Price
                </Button>
              </CardBody>
            </Card>
          )}

        {/* Equity Grant Details - For stock_options and private_equity accounts */}
        {(account.account_type === "stock_options" ||
          account.account_type === "private_equity") && (
          <Card>
            <CardBody>
              <Heading size="md" mb={1}>
                Grant Details
              </Heading>
              <Text fontSize="sm" color="text.muted" mb={4}>
                Update grant specifics used in net worth calculations, vesting
                schedules, and the Equity Compensation page.
              </Text>
              <VStack spacing={4} align="stretch">
                {/* Current values display */}
                {(account.grant_type || account.quantity != null || account.share_price != null || account.vesting_schedule) && (
                  <>
                    <HStack spacing={6} wrap="wrap">
                      {account.grant_type && (
                        <Box>
                          <Text fontSize="xs" color="text.muted">Grant Type</Text>
                          <Text fontWeight="semibold">{account.grant_type.toUpperCase()}</Text>
                        </Box>
                      )}
                      {account.quantity != null && (
                        <Box>
                          <Text fontSize="xs" color="text.muted">Shares / Options</Text>
                          <Text fontWeight="semibold">{account.quantity.toLocaleString()}</Text>
                        </Box>
                      )}
                      {account.strike_price != null && (
                        <Box>
                          <Text fontSize="xs" color="text.muted">Strike Price</Text>
                          <Text fontWeight="semibold">${account.strike_price}</Text>
                        </Box>
                      )}
                      {account.share_price != null && (
                        <Box>
                          <Text fontSize="xs" color="text.muted">Current Share Price</Text>
                          <Text fontWeight="semibold">${account.share_price}</Text>
                        </Box>
                      )}
                      {account.company_status && (
                        <Box>
                          <Text fontSize="xs" color="text.muted">Company Status</Text>
                          <Text fontWeight="semibold" textTransform="capitalize">{account.company_status}</Text>
                        </Box>
                      )}
                    </HStack>
                    {account.vesting_schedule && (() => {
                      try {
                        const rows: { date: string; quantity: number; notes?: string }[] =
                          JSON.parse(account.vesting_schedule);
                        if (!Array.isArray(rows) || rows.length === 0) return null;
                        return (
                          <Box>
                            <Text fontSize="xs" color="text.muted" mb={1}>Saved Vesting Events</Text>
                            <Table size="sm" variant="simple">
                              <Thead>
                                <Tr>
                                  <Th>Date</Th>
                                  <Th isNumeric>Shares</Th>
                                  <Th>Notes</Th>
                                </Tr>
                              </Thead>
                              <Tbody>
                                {rows.map((r, i) => (
                                  <Tr key={i}>
                                    <Td>{r.date}</Td>
                                    <Td isNumeric>{Number(r.quantity).toLocaleString()}</Td>
                                    <Td color="text.muted">{r.notes ?? ""}</Td>
                                  </Tr>
                                ))}
                              </Tbody>
                            </Table>
                          </Box>
                        );
                      } catch { return null; }
                    })()}
                    <Divider />
                  </>
                )}

                {!canEditAccount ? (
                  <Text fontSize="sm" color="text.secondary">
                    Grant details can only be updated by the account owner.
                  </Text>
                ) : (
                  <>
                    <FormControl>
                      <FormLabel fontSize="sm">Grant Type</FormLabel>
                      <Select
                        size="sm"
                        value={equityGrantType}
                        onChange={(e) => setEquityGrantType(e.target.value)}
                        placeholder={account.grant_type ? account.grant_type.toUpperCase() : "Select grant type"}
                      >
                        <option value="iso">ISO (Incentive Stock Option)</option>
                        <option value="nso">NSO (Non-Qualified Stock Option)</option>
                        <option value="rsu">RSU (Restricted Stock Unit)</option>
                        <option value="rsa">RSA (Restricted Stock Award)</option>
                        <option value="profit_interest">Profits Interest (LLC Units)</option>
                      </Select>
                    </FormControl>

                    <FormControl>
                      <FormLabel fontSize="sm">Company Status</FormLabel>
                      <Select
                        size="sm"
                        value={equityCompanyStatus}
                        onChange={(e) => setEquityCompanyStatus(e.target.value)}
                        placeholder={account.company_status ?? "Select status"}
                      >
                        <option value="private">Private</option>
                        <option value="public">Public</option>
                      </Select>
                    </FormControl>

                    <FormControl>
                      <FormLabel fontSize="sm">Quantity (shares / options)</FormLabel>
                      <NumberInput
                        value={equityQuantity}
                        onChange={setEquityQuantity}
                        precision={4}
                        min={0}
                        size="sm"
                      >
                        <NumberInputField
                          placeholder={account.quantity != null ? String(account.quantity) : "e.g., 10000"}
                        />
                      </NumberInput>
                    </FormControl>

                    {(equityGrantType === "iso" || equityGrantType === "nso" ||
                      account.grant_type === "iso" || account.grant_type === "nso") && (
                      <FormControl>
                        <FormLabel fontSize="sm">Strike Price (exercise price)</FormLabel>
                        <NumberInput
                          value={equityStrikePrice}
                          onChange={setEquityStrikePrice}
                          precision={4}
                          min={0}
                          size="sm"
                        >
                          <NumberInputField
                            placeholder={account.strike_price != null ? String(account.strike_price) : "e.g., 10.50"}
                          />
                        </NumberInput>
                      </FormControl>
                    )}

                    <FormControl>
                      <FormLabel fontSize="sm">Current Share Price</FormLabel>
                      <NumberInput
                        value={equitySharePrice}
                        onChange={setEquitySharePrice}
                        precision={4}
                        min={0}
                        size="sm"
                      >
                        <NumberInputField
                          placeholder={account.share_price != null ? String(account.share_price) : "e.g., 25.00"}
                        />
                      </NumberInput>
                    </FormControl>

                    <FormControl>
                      <FormLabel fontSize="sm">Grant Date</FormLabel>
                      <Input
                        type="date"
                        size="sm"
                        value={equityGrantDate}
                        onChange={(e) => setEquityGrantDate(e.target.value)}
                        placeholder={account.grant_date ?? undefined}
                      />
                    </FormControl>

                    <Divider />

                    {/* Vesting Schedule Editor */}
                    <Box>
                      <Text fontSize="sm" fontWeight="semibold" mb={2}>Vesting Schedule</Text>
                      {account.vesting_schedule && (() => {
                        try {
                          const rows = JSON.parse(account.vesting_schedule);
                          return Array.isArray(rows) && rows.length > 0 ? (
                            <Text fontSize="xs" color="text.muted" mb={3}>
                              {rows.length} existing event{rows.length !== 1 ? "s" : ""} — new events will be appended
                            </Text>
                          ) : null;
                        } catch { return null; }
                      })()}

                      {/* Template quick-fill */}
                      {(() => {
                        const templateStart = equityGrantDate || account.grant_date || "";
                        const templateShares =
                          parseFloat(equityQuantity) ||
                          (account.quantity != null ? account.quantity : 0);
                        const canTemplate = !!templateStart && templateShares > 0;
                        return (
                          <Box mb={3} p={3} borderWidth="1px" borderRadius="md" borderColor="border.subtle">
                            <Text fontSize="xs" fontWeight="semibold" mb={1} color="text.secondary">
                              Quick templates
                            </Text>
                            <Text fontSize="xs" color="text.muted" mb={3}>
                              Uses the Grant Date and Total Shares fields above.
                              {!templateStart && " Fill in a Grant Date to enable."}
                              {templateStart && !templateShares && " Fill in Total Shares to enable."}
                            </Text>
                            <HStack spacing={2} flexWrap="wrap">
                              {[
                                { id: "4yr-1yr-cliff-monthly",   label: "4yr / 1yr cliff (monthly)" },
                                { id: "4yr-1yr-cliff-quarterly", label: "4yr / 1yr cliff (quarterly)" },
                                { id: "4yr-quarterly",           label: "4yr quarterly" },
                                { id: "4yr-annual",              label: "4yr annual" },
                                { id: "3yr-annual",              label: "3yr annual" },
                                { id: "2yr-semi",                label: "2yr semi-annual" },
                                { id: "1yr-annual",              label: "1yr (single)" },
                                { id: "1yr-monthly",             label: "1yr monthly" },
                              ].map(({ id, label }) => (
                                <Button
                                  key={id}
                                  size="xs"
                                  variant="outline"
                                  isDisabled={!canTemplate}
                                  onClick={() => applyVestTemplate(id, templateStart, templateShares)}
                                >
                                  {label}
                                </Button>
                              ))}
                            </HStack>
                          </Box>
                        );
                      })()}

                      <HStack justify="space-between" mb={2}>
                        <Text fontSize="xs" color="text.muted">
                          {vestRows.length > 0
                            ? `${vestRows.length} event${vestRows.length !== 1 ? "s" : ""} — edit or add manually below`
                            : "Or add events manually:"}
                        </Text>
                        <HStack spacing={2}>
                          {vestRows.length > 0 && (
                            <Button size="xs" variant="ghost" colorScheme="red" onClick={() => setVestRows([])}>
                              Clear all
                            </Button>
                          )}
                          <Button
                            size="xs"
                            leftIcon={<FiPlus />}
                            variant="outline"
                            onClick={() => setVestRows((r) => [...r, { date: "", quantity: "", notes: "" }])}
                          >
                            Add row
                          </Button>
                        </HStack>
                      </HStack>

                      {vestRows.length === 0 ? (
                        <Text fontSize="xs" color="text.muted">
                          No events yet. Use a template above or add rows manually.
                        </Text>
                      ) : (
                        <Box overflowX="auto">
                          <Table size="sm" variant="simple">
                            <Thead>
                              <Tr>
                                <Th>Vest Date</Th>
                                <Th isNumeric>Shares</Th>
                                <Th>Notes (optional)</Th>
                                <Th />
                              </Tr>
                            </Thead>
                            <Tbody>
                              {vestRows.map((row, idx) => (
                                <Tr key={idx}>
                                  <Td minW="150px">
                                    <Input
                                      type="date"
                                      size="sm"
                                      value={row.date}
                                      onChange={(e) =>
                                        setVestRows((rows) =>
                                          rows.map((r, i) => i === idx ? { ...r, date: e.target.value } : r)
                                        )
                                      }
                                    />
                                  </Td>
                                  <Td minW="120px">
                                    <NumberInput
                                      size="sm"
                                      value={row.quantity}
                                      onChange={(v) =>
                                        setVestRows((rows) =>
                                          rows.map((r, i) => i === idx ? { ...r, quantity: v } : r)
                                        )
                                      }
                                      min={0}
                                      precision={4}
                                    >
                                      <NumberInputField placeholder="e.g. 250" />
                                    </NumberInput>
                                  </Td>
                                  <Td minW="140px">
                                    <Input
                                      size="sm"
                                      placeholder="e.g. Cliff"
                                      value={row.notes}
                                      onChange={(e) =>
                                        setVestRows((rows) =>
                                          rows.map((r, i) => i === idx ? { ...r, notes: e.target.value } : r)
                                        )
                                      }
                                    />
                                  </Td>
                                  <Td>
                                    <IconButton
                                      aria-label="Remove"
                                      icon={<FiTrash2 />}
                                      size="xs"
                                      variant="ghost"
                                      colorScheme="red"
                                      onClick={() => setVestRows((rows) => rows.filter((_, i) => i !== idx))}
                                    />
                                  </Td>
                                </Tr>
                              ))}
                            </Tbody>
                          </Table>
                        </Box>
                      )}
                    </Box>

                    <Button
                      colorScheme="brand"
                      size="sm"
                      onClick={handleSaveEquityDetails}
                      isLoading={updateAccountMutation.isPending}
                      isDisabled={
                        !equityGrantType &&
                        !equityQuantity &&
                        !equityStrikePrice &&
                        !equitySharePrice &&
                        !equityGrantDate &&
                        !equityCompanyStatus &&
                        vestRows.filter((r) => r.date && r.quantity).length === 0
                      }
                    >
                      Save Grant Details
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
                <ContributionsManager
                  accountId={account.id}
                  accountName={account.name}
                />
              ) : (
                <Box>
                  <Heading size="md" mb={2}>
                    Recurring Contributions
                  </Heading>
                  <Text fontSize="sm" color="text.secondary">
                    Contributions can only be managed by the account owner.
                  </Text>
                </Box>
              )}
            </CardBody>
          </Card>
        )}

        {/* Transactions Section - hidden for asset accounts (property, vehicle, etc.) */}
        {showTransactions && (
          <Card>
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
                      Showing {transactionsData.transactions?.length || 0} of{" "}
                      {transactionsData.total}
                    </Text>
                  )}
                </HStack>
              </HStack>

              {transactionsLoading ? (
                <Center py={8}>
                  <Spinner size="md" color="brand.500" />
                </Center>
              ) : transactionsData?.transactions &&
                transactionsData.transactions.length > 0 ? (
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
                                {new Date(txn.date).toLocaleDateString(
                                  "en-US",
                                  {
                                    month: "short",
                                    day: "numeric",
                                    year: "numeric",
                                  },
                                )}
                              </Text>
                            </Td>
                            <Td>
                              <VStack align="start" spacing={0}>
                                <Text fontSize="sm" fontWeight="medium">
                                  {txn.merchant_name || "Unknown"}
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
                                color={
                                  isNegative
                                    ? "finance.positive"
                                    : "finance.negative"
                                }
                              >
                                {isNegative ? "+" : "-"}
                                {formatCurrency(Math.abs(amount))}
                              </Text>
                            </Td>
                          </Tr>
                        );
                      })}
                    </Tbody>
                  </Table>

                  {transactionsData.has_more &&
                    transactionsData.next_cursor && (
                      <Button
                        size="sm"
                        variant="outline"
                        mt={4}
                        onClick={() =>
                          setTransactionsCursor(transactionsData.next_cursor)
                        }
                        width="full"
                      >
                        Load More
                      </Button>
                    )}
                </>
              ) : (
                <Text
                  color="text.muted"
                  fontSize="sm"
                  textAlign="center"
                  py={8}
                >
                  No transactions found for this account.
                </Text>
              )}
            </CardBody>
          </Card>
        )}
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
        isCrypto={account.account_type === "crypto"}
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
              Are you sure you want to close "{account.name}"? This will
              permanently delete the account and all associated transactions.
              This action cannot be undone.
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

      {/* Migrate Provider Dialog */}
      <AlertDialog
        isOpen={isMigrateOpen}
        leastDestructiveRef={migrateCancelRef}
        onClose={() => {
          onMigrateClose();
          setMigrateStep(1);
          setSelectedTargetSource(null);
        }}
        size="lg"
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            {migrateStep === 1 ? (
              <>
                <AlertDialogHeader fontSize="lg" fontWeight="bold">
                  Migrate Account Provider
                </AlertDialogHeader>

                <AlertDialogBody>
                  <VStack align="stretch" spacing={4}>
                    <Box>
                      <Text fontSize="sm" color="text.secondary" mb={1}>
                        Current provider
                      </Text>
                      <Badge colorScheme="blue" fontSize="sm" px={2} py={1}>
                        {account.account_source.toUpperCase()}
                        {account.institution_name &&
                          ` - ${account.institution_name}`}
                      </Badge>
                    </Box>

                    <Box>
                      <Text fontSize="sm" color="text.secondary" mb={2}>
                        Select target provider
                      </Text>
                      <SimpleGrid columns={2} spacing={3}>
                        {account.account_source !== "manual" && (
                          <Box
                            as="button"
                            p={3}
                            borderWidth="2px"
                            borderRadius="md"
                            borderColor={
                              selectedTargetSource === "manual"
                                ? "brand.500"
                                : "border.default"
                            }
                            bg={
                              selectedTargetSource === "manual"
                                ? "brand.50"
                                : "transparent"
                            }
                            _dark={
                              selectedTargetSource === "manual"
                                ? { bg: "brand.900" }
                                : undefined
                            }
                            onClick={() => setSelectedTargetSource("manual")}
                            textAlign="left"
                            _hover={{ borderColor: "brand.400" }}
                          >
                            <Text fontWeight="medium" fontSize="sm">
                              Manual
                            </Text>
                            <Text fontSize="xs" color="text.secondary">
                              Manage balance and transactions manually
                            </Text>
                          </Box>
                        )}
                        {account.account_source !== "plaid" && (
                          <Box
                            p={3}
                            borderWidth="2px"
                            borderRadius="md"
                            borderColor="border.default"
                            opacity={0.5}
                            cursor="not-allowed"
                          >
                            <Text fontWeight="medium" fontSize="sm">
                              Plaid
                            </Text>
                            <Text fontSize="xs" color="text.muted">
                              Requires active Plaid connection
                            </Text>
                          </Box>
                        )}
                        {account.account_source !== "teller" && (
                          <Box
                            p={3}
                            borderWidth="2px"
                            borderRadius="md"
                            borderColor="border.default"
                            opacity={0.5}
                            cursor="not-allowed"
                          >
                            <Text fontWeight="medium" fontSize="sm">
                              Teller
                            </Text>
                            <Text fontSize="xs" color="text.muted">
                              Requires active Teller connection
                            </Text>
                          </Box>
                        )}
                        {account.account_source !== "mx" && (
                          <Box
                            p={3}
                            borderWidth="2px"
                            borderRadius="md"
                            borderColor="border.default"
                            opacity={0.5}
                            cursor="not-allowed"
                          >
                            <Text fontWeight="medium" fontSize="sm">
                              MX
                            </Text>
                            <Text fontSize="xs" color="text.muted">
                              Requires active MX connection
                            </Text>
                          </Box>
                        )}
                      </SimpleGrid>
                    </Box>
                  </VStack>
                </AlertDialogBody>

                <AlertDialogFooter>
                  <Button
                    ref={migrateCancelRef}
                    onClick={() => {
                      onMigrateClose();
                      setMigrateStep(1);
                      setSelectedTargetSource(null);
                    }}
                  >
                    Cancel
                  </Button>
                  <Button
                    colorScheme="brand"
                    ml={3}
                    onClick={() => setMigrateStep(2)}
                    isDisabled={!selectedTargetSource}
                  >
                    Next
                  </Button>
                </AlertDialogFooter>
              </>
            ) : (
              <>
                <AlertDialogHeader fontSize="lg" fontWeight="bold">
                  Confirm Migration
                </AlertDialogHeader>

                <AlertDialogBody>
                  <VStack align="stretch" spacing={3}>
                    <HStack spacing={3} justify="center" py={2}>
                      <Badge colorScheme="gray" fontSize="sm" px={2} py={1}>
                        {account.account_source.toUpperCase()}
                      </Badge>
                      <Text fontSize="lg" color="text.secondary">
                        →
                      </Text>
                      <Badge colorScheme="brand" fontSize="sm" px={2} py={1}>
                        {selectedTargetSource?.toUpperCase()}
                      </Badge>
                    </HStack>

                    <Box bg="bg.subtle" p={3} borderRadius="md">
                      <VStack align="stretch" spacing={2} fontSize="sm">
                        <Text>
                          All transactions, holdings, and contributions will be
                          preserved.
                        </Text>
                        {selectedTargetSource === "manual" &&
                          account.account_source !== "manual" && (
                            <Text>
                              Automatic sync will stop. You will manage this
                              account manually going forward.
                            </Text>
                          )}
                        {selectedTargetSource !== "manual" &&
                          account.account_source === "manual" && (
                            <Text>
                              This account will begin syncing automatically with{" "}
                              {selectedTargetSource?.toUpperCase()}.
                            </Text>
                          )}
                        <Text color="text.secondary">
                          You can migrate again later if needed.
                        </Text>
                      </VStack>
                    </Box>
                  </VStack>
                </AlertDialogBody>

                <AlertDialogFooter>
                  <Button onClick={() => setMigrateStep(1)}>Back</Button>
                  <Button
                    colorScheme="brand"
                    ml={3}
                    onClick={() => {
                      if (selectedTargetSource) {
                        migrateAccountMutation.mutate(selectedTargetSource);
                      }
                    }}
                    isLoading={migrateAccountMutation.isPending}
                  >
                    Migrate Account
                  </Button>
                </AlertDialogFooter>
              </>
            )}
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </Container>
  );
};
