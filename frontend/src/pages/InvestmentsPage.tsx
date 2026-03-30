/**
 * Investments page showing portfolio overview and holdings
 */

import {
  Alert,
  AlertIcon,
  Box,
  Container,
  Heading,
  Text,
  Tooltip,
  VStack,
  HStack,
  Card,
  CardBody,
  SimpleGrid,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Spinner,
  Center,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Button,
  useDisclosure,
  useToast,
  Checkbox,
  Stack,
  Divider,
  Collapse,
  IconButton,
  Menu,
  MenuButton,
  MenuList,
} from "@chakra-ui/react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import React, { useState, useEffect, useMemo, useRef, memo } from "react";
import {
  FiChevronDown,
  FiChevronUp,
  FiFilter,
  FiLink,
  FiRefreshCw,
} from "react-icons/fi";
import api from "../services/api";
import { useUserView } from "../contexts/UserViewContext";
import { AssetAllocationTreemap } from "../features/investments/components/AssetAllocationTreemap";
import { HoldingsDetailTable } from "../features/investments/components/HoldingsDetailTable";
import { GrowthProjectionsChart } from "../features/investments/components/GrowthProjectionsChart";
import { SectorBreakdownChart } from "../features/investments/components/SectorBreakdownChart";
import PerformanceTrendsChart from "../features/investments/components/PerformanceTrendsChart";
import RiskAnalysisPanel from "../features/investments/components/RiskAnalysisPanel";
import StyleBoxModal from "../features/investments/components/StyleBoxModal";
import { RMDAlert } from "../features/investments/components/RMDAlert";
import { RothConversionAnalyzer } from "../features/investments/components/RothConversionAnalyzer";
import TaxLossHarvestingPanel from "../features/investments/components/TaxLossHarvestingPanel";
import CapitalGainsHarvestingPanel from "../features/investments/components/CapitalGainsHarvestingPanel";
import StressTestPanel from "../features/investments/components/StressTestPanel";
import { RebalancingPanel } from "../features/investments/components/RebalancingPanel";
import { FeeAnalysisPanel } from "../features/investments/components/FeeAnalysisPanel";
import { DividendIncomePanel } from "../features/investments/components/DividendIncomePanel";
import { AllocationHistoryChart } from "../features/investments/components/AllocationHistoryChart";
import { BenchmarkComparisonPanel } from "../features/investments/components/BenchmarkComparisonPanel";
import { useRetirementAccountData } from "../features/retirement/hooks/useRetirementScenarios";
import HelpHint from "../components/HelpHint";
import { helpContent } from "../constants/helpContent";
import { AddAccountModal } from "../features/accounts/components/AddAccountModal";
import { useAuthStore } from "../features/auth/stores/authStore";

interface Holding {
  id: string;
  ticker: string;
  name: string | null;
  shares: number;
  cost_basis_per_share: number | null;
  total_cost_basis: number | null;
  current_price_per_share: number | null;
  current_total_value: number | null;
  price_as_of: string | null;
  asset_type: string | null;
}

interface AccountHoldings {
  account_id: string;
  account_name: string;
  account_type: string;
  account_value: number;
  holdings: Holding[];
}

interface HoldingSummary {
  ticker: string;
  name: string | null;
  total_shares: number;
  total_cost_basis: number | null;
  current_price_per_share: number | null;
  current_total_value: number | null;
  price_as_of: string | null;
  asset_type: string | null;
  expense_ratio: number | null;
  gain_loss: number | null;
  gain_loss_percent: number | null;
  annual_fee: number | null;
}

interface CategoryBreakdown {
  retirement_value: number;
  retirement_percent: number | null;
  taxable_value: number;
  taxable_percent: number | null;
  other_value: number;
  other_percent: number | null;
}

interface GeographicBreakdown {
  domestic_value: number;
  domestic_percent: number | null;
  international_value: number;
  international_percent: number | null;
  unknown_value: number;
  unknown_percent: number | null;
}

interface TreemapNode {
  name: string;
  value: number;
  percent: number;
  children?: TreemapNode[];
  color?: string;
  [key: string]: any; // Index signature for Recharts compatibility
}

interface PortfolioSummary {
  total_value: number;
  total_cost_basis: number | null;
  total_gain_loss: number | null;
  total_gain_loss_percent: number | null;
  holdings_by_ticker: HoldingSummary[];
  holdings_by_account: AccountHoldings[];
  stocks_value: number;
  bonds_value: number;
  etf_value: number;
  mutual_funds_value: number;
  cash_value: number;
  other_value: number;
  category_breakdown: CategoryBreakdown | null;
  geographic_breakdown: GeographicBreakdown | null;
  treemap_data: TreemapNode | null;
  total_annual_fees: number | null;
  holdings_truncated?: boolean;
  asset_classification_estimated?: boolean;
}

// ─── Memoized row components for .map() rendering ────────────────────────────

interface AccountHoldingsCardProps {
  account: AccountHoldings;
  isExpanded: boolean;
  onToggleExpand: (accountId: string) => void;
  formatCurrency: (amount: number | null) => string;
  formatShares: (shares: number) => string;
}

const AccountHoldingsCard = memo(
  ({
    account,
    isExpanded,
    onToggleExpand,
    formatCurrency,
    formatShares,
  }: AccountHoldingsCardProps) => (
    <Card variant="outline">
      <CardBody>
        <HStack
          justify="space-between"
          cursor="pointer"
          onClick={() => onToggleExpand(account.account_id)}
        >
          <VStack align="flex-start" spacing={0}>
            <HStack>
              <Heading size="sm">{account.account_name}</Heading>
              <Badge colorScheme="purple" size="sm">
                {account.account_type}
              </Badge>
            </HStack>
            <Text fontSize="lg" fontWeight="bold" color="brand.accent">
              {formatCurrency(account.account_value)}
            </Text>
          </VStack>
          <IconButton
            aria-label={isExpanded ? "Collapse" : "Expand"}
            icon={isExpanded ? <FiChevronUp /> : <FiChevronDown />}
            size="sm"
            variant="ghost"
          />
        </HStack>

        <Collapse in={isExpanded}>
          <Box mt={4} overflowX="auto">
            {account.holdings.length === 0 ? (
              <VStack spacing={2} py={4} align="center">
                <Text fontSize="sm" color="text.secondary">
                  Holdings details not available for this account.
                </Text>
                <Text fontSize="xs" color="text.muted">
                  Account balance: {formatCurrency(account.account_value)}
                </Text>
                <Text fontSize="xs" color="text.muted">
                  Sync holdings data from your provider to see detailed
                  breakdown.
                </Text>
              </VStack>
            ) : (
              <Table variant="simple" size="sm">
                <Thead>
                  <Tr>
                    <Th>Ticker</Th>
                    <Th>Name</Th>
                    <Th isNumeric>Shares</Th>
                    <Th isNumeric>Price</Th>
                    <Th isNumeric>Value</Th>
                    <Th isNumeric>What You Paid</Th>
                    <Th>Type</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {account.holdings.map((holding) => (
                    <Tr key={holding.id}>
                      <Td>
                        <Text fontWeight="bold">{holding.ticker}</Text>
                      </Td>
                      <Td>
                        <Text fontSize="sm" color="text.secondary">
                          {holding.name || "-"}
                        </Text>
                      </Td>
                      <Td isNumeric>{formatShares(holding.shares)}</Td>
                      <Td isNumeric>
                        {holding.current_price_per_share
                          ? formatCurrency(holding.current_price_per_share)
                          : "N/A"}
                      </Td>
                      <Td isNumeric>
                        <Text fontWeight="semibold">
                          {formatCurrency(holding.current_total_value)}
                        </Text>
                      </Td>
                      <Td isNumeric>
                        {formatCurrency(holding.total_cost_basis)}
                      </Td>
                      <Td>
                        {holding.asset_type && (
                          <Badge colorScheme="blue" size="sm">
                            {holding.asset_type}
                          </Badge>
                        )}
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            )}
          </Box>
        </Collapse>
      </CardBody>
    </Card>
  ),
);
AccountHoldingsCard.displayName = "AccountHoldingsCard";

export const InvestmentsPage = () => {
  // Use global user view context + multi-member filter
  const {
    selectedUserId,
    canWriteResource,
    isCombinedView,
    memberEffectiveUserId,
    selectedMemberIdsKey,
  } = useUserView();
  const canEdit = canWriteResource("holding");
  const currentUser = useAuthStore((s) => s.user);
  const onboardingGoal = localStorage.getItem("nest-egg-onboarding-goal") || currentUser?.onboarding_goal || "";
  const multiEffectiveUserId = memberEffectiveUserId;
  const selectedIdsKey = selectedMemberIdsKey;

  // In combined view, use multi-member filter; otherwise use global selectedUserId
  const activeUserId = isCombinedView
    ? (multiEffectiveUserId ?? null)
    : selectedUserId;

  // Retirement account data for monthly contribution in growth projections
  const { data: retirementAccountData } = useRetirementAccountData();
  const monthlyContribution = retirementAccountData
    ? (retirementAccountData.annual_contributions +
        retirementAccountData.employer_match_annual) /
      12
    : undefined;

  // Drilled-down treemap node
  const [selectedNode, setSelectedNode] = useState<TreemapNode | null>(null);

  // Expanded sections state
  const [expandedSections, setExpandedSections] = useState<string[]>([
    "summary",
    "breakdown",
    "treemap",
    "holdings",
  ]);

  // Expanded accounts state (default: all expanded)
  const [expandedAccounts, setExpandedAccounts] = useState<string[]>([]);

  // Style Box modal
  const { isOpen: isStyleBoxOpen, onClose: onStyleBoxClose } = useDisclosure();
  // Add account modal (shown from empty state)
  const {
    isOpen: isAddAccountOpen,
    onOpen: onAddAccountOpen,
    onClose: onAddAccountClose,
  } = useDisclosure();

  const toast = useToast();
  const queryClient = useQueryClient();

  const refreshPricesMutation = useMutation({
    mutationFn: async () => {
      const params = activeUserId ? { user_id: activeUserId } : {};
      const response = await api.post(
        "/market-data/holdings/refresh-all",
        null,
        { params },
      );
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["portfolio"] });
      toast({
        title: `Prices refreshed`,
        description: `Updated ${data.updated} of ${data.total} holdings via ${data.provider}`,
        status: "success",
        duration: 4000,
        isClosable: true,
      });
    },
    onError: () => {
      toast({
        title: "Failed to refresh prices",
        status: "error",
        duration: 3000,
      });
    },
  });

  // Hidden accounts state (persisted to localStorage)
  const [hiddenAccountIds, setHiddenAccountIds] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem("hiddenAccounts");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // Save hidden accounts to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem("hiddenAccounts", JSON.stringify(hiddenAccountIds));
  }, [hiddenAccountIds]);

  // Selected tab index (persisted to localStorage)
  const [selectedTabIndex, setSelectedTabIndex] = useState<number>(() => {
    const saved = localStorage.getItem("investmentsTabIndex");
    return saved ? parseInt(saved, 10) : 0;
  });

  // Save selected tab index to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem("investmentsTabIndex", selectedTabIndex.toString());
  }, [selectedTabIndex]);

  // Helper to convert string numbers to actual numbers in treemap data
  const convertTreemapNode = (node: any): TreemapNode => {
    return {
      name: node.name,
      value: Number(node.value),
      percent: Number(node.percent),
      children: node.children?.map(convertTreemapNode),
      color: node.color,
    };
  };

  // Fetch all accounts for filtering (backend deduplicates shared accounts)
  const { data: allAccounts } = useQuery({
    queryKey: ["accounts", activeUserId, selectedIdsKey],
    queryFn: async () => {
      const params = activeUserId ? { user_id: activeUserId } : {};
      const response = await api.get("/accounts", { params });
      return response.data;
    },
  });

  // Track if we've initialized default hidden accounts
  const hasInitializedDefaults = useRef(false);

  // Set default hidden accounts on first load (hide property and vehicles)
  /* eslint-disable react-hooks/set-state-in-effect -- intentional: one-time init from localStorage */
  useEffect(() => {
    if (allAccounts && !hasInitializedDefaults.current) {
      const savedState = localStorage.getItem("hiddenAccounts");
      const savedMigrationFlag = localStorage.getItem(
        "hiddenAccounts_migratedV1",
      );

      // Get non-investment property and vehicle account IDs to hide
      // Hide: personal residences, vacation homes, and vehicles
      // Show: investment properties (they're investments!)
      const nonInvestmentAssets = allAccounts
        .filter((account: any) => {
          // Hide all vehicles
          if (account.account_type === "vehicle") return true;

          // For properties, only hide personal residences and vacation homes
          if (account.account_type === "property") {
            return (
              account.property_type === "personal_residence" ||
              account.property_type === "vacation_home"
            );
          }

          return false;
        })
        .map((account: any) => account.id);

      // If no saved preferences, or if we haven't migrated yet, apply the new default
      if (!savedState || !savedMigrationFlag) {
        if (nonInvestmentAssets.length > 0) {
          setHiddenAccountIds(nonInvestmentAssets);
          localStorage.setItem("hiddenAccounts_migratedV1", "true");
        }
      }

      hasInitializedDefaults.current = true;
    }
  }, [allAccounts]);
  /* eslint-enable react-hooks/set-state-in-effect */

  // Fetch portfolio summary
  const { data: rawPortfolio, isLoading, isError } = useQuery<PortfolioSummary>({
    queryKey: ["portfolio", activeUserId, selectedIdsKey],
    queryFn: async () => {
      const params = activeUserId ? { user_id: activeUserId } : {};
      const response = await api.get("/holdings/portfolio", { params });

      // Convert treemap data to use numbers instead of strings
      if (response.data.treemap_data) {
        response.data.treemap_data = convertTreemapNode(
          response.data.treemap_data,
        );
        console.log("🗺️ Treemap Data (converted):", response.data.treemap_data);
      }

      return response.data;
    },
  });

  // Filter portfolio based on visible accounts
  const portfolio = useMemo(() => {
    if (!rawPortfolio || !allAccounts) return rawPortfolio;

    // If no accounts are hidden, return original data
    if (hiddenAccountIds.length === 0) {
      return rawPortfolio;
    }

    // Filter accounts
    const visibleAccounts = rawPortfolio.holdings_by_account.filter(
      (account) => !hiddenAccountIds.includes(account.account_id),
    );

    // Filter holdings by ticker to only include visible accounts
    const visibleHoldingsByTicker = rawPortfolio.holdings_by_ticker.filter(
      (holding) => {
        return visibleAccounts.some((account) =>
          account.holdings.some((h) => h.ticker === holding.ticker),
        );
      },
    );

    // Recalculate total value by subtracting hidden accounts from backend total
    // This avoids needing to replicate the backend's complex portfolio calculation logic

    // Start with the backend's correct total
    let newTotalValue = rawPortfolio.total_value;

    // Subtract value of hidden accounts
    if (hiddenAccountIds.length > 0 && allAccounts) {
      const hiddenAccounts = allAccounts.filter((account: any) =>
        hiddenAccountIds.includes(account.id),
      );

      hiddenAccounts.forEach((account: any) => {
        // For investment accounts, use account_value from holdings_by_account if available
        const holdingsAccount = rawPortfolio.holdings_by_account.find(
          (h) => h.account_id === account.id,
        );
        if (holdingsAccount) {
          newTotalValue -= Number(holdingsAccount.account_value || 0);
        } else {
          // For other accounts (crypto without holdings, property, vehicle, etc), use current_balance
          newTotalValue -= Number(account.current_balance || 0);
        }
      });
    }

    // Get visible accounts (all accounts minus hidden ones)
    const allVisibleAccounts =
      allAccounts?.filter(
        (account: any) => !hiddenAccountIds.includes(account.id),
      ) || [];

    // Recalculate treemap data based on visible accounts
    let newTreemapData = rawPortfolio.treemap_data;
    if (rawPortfolio.treemap_data && rawPortfolio.treemap_data.children) {
      // Get visible account names for filtering
      const visibleAccountNames = new Set(
        allVisibleAccounts.map((a: any) => a.name),
      );

      // Helper to recursively filter treemap nodes
      const filterTreemapNode = (node: any, categoryName: string): any => {
        if (!node.children) return node;

        // Filter children recursively
        const filteredChildren = node.children
          .map((child: any) => {
            // Base case: leaf node (individual account or ticker)
            if (!child.children) {
              // For Cash accounts, check if visible by name
              if (categoryName === "Cash") {
                return visibleAccountNames.has(child.name) ? child : null;
              }
              // For Investment Accounts, check if visible by name (strip "(Holdings Unknown)" suffix)
              if (categoryName === "Investment Accounts") {
                const accountName = child.name.replace(
                  " (Holdings Unknown)",
                  "",
                );
                return visibleAccountNames.has(accountName) ? child : null;
              }
              // For account-based leaves (Property, Vehicles), check if visible by name
              if (categoryName === "Property & Vehicles") {
                return visibleAccountNames.has(child.name) ? child : null;
              }
              // For Crypto, check if ticker is in visible crypto accounts
              if (categoryName === "Crypto") {
                const hasTicker = visibleAccounts.some((account) =>
                  account.holdings.some((h: any) => h.ticker === child.name),
                );
                return hasTicker ? child : null;
              }
              // For holdings-based leaves (tickers), check if in visible accounts
              return visibleAccounts.some((account) =>
                account.holdings.some((h: any) => h.ticker === child.name),
              )
                ? child
                : null;
            }

            // Recursive case: intermediate node (cap sizes, asset types, etc.)
            const filtered = filterTreemapNode(child, categoryName);
            return filtered && filtered.value > 0 ? filtered : null;
          })
          .filter((c: any) => c !== null);

        // Recalculate value and percent for this node
        const newValue = filteredChildren.reduce(
          (sum: number, c: any) => sum + c.value,
          0,
        );

        return {
          ...node,
          value: newValue,
          percent: node.percent, // Will be recalculated at parent level
          children: filteredChildren.length > 0 ? filteredChildren : undefined,
        };
      };

      // Filter each top-level category
      const filteredChildren = rawPortfolio.treemap_data.children
        .map((category) => {
          const filtered = filterTreemapNode(category, category.name);
          // Recalculate percent relative to new total
          return {
            ...filtered,
            percent:
              newTotalValue > 0 ? (filtered.value / newTotalValue) * 100 : 0,
          };
        })
        .filter((cat) => cat.value > 0); // Remove categories with 0 value

      newTreemapData = {
        ...rawPortfolio.treemap_data,
        value: newTotalValue,
        children: filteredChildren,
      };
    }

    // Return filtered portfolio data
    return {
      ...rawPortfolio,
      holdings_by_account: visibleAccounts,
      holdings_by_ticker: visibleHoldingsByTicker,
      total_value: newTotalValue,
      treemap_data: newTreemapData,
    };
  }, [rawPortfolio, allAccounts, hiddenAccountIds]);

  const formatCurrency = (amount: number | null) => {
    if (amount === null || amount === undefined) return "N/A";
    const num = Number(amount);
    if (isNaN(num)) return "N/A";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num);
  };

  const formatPercent = (percent: number | null) => {
    if (percent === null || percent === undefined) return "N/A";
    const num = Number(percent);
    if (isNaN(num)) return "N/A";
    return `${num >= 0 ? "+" : ""}${num.toFixed(2)}%`;
  };

  const formatShares = (shares: number) => {
    const num = Number(shares);
    if (isNaN(num)) return "0";
    return new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 6,
    }).format(num);
  };

  const toggleSection = (section: string) => {
    setExpandedSections((prev) =>
      prev.includes(section)
        ? prev.filter((s) => s !== section)
        : [...prev, section],
    );
  };

  const handleTreemapDrillDown = (node: TreemapNode | null) => {
    setSelectedNode(node);
  };

  // Group accounts by type for organized display
  const groupedAccounts = useMemo(() => {
    if (!allAccounts) return {};

    const groups: Record<string, any[]> = {};

    // Group all accounts dynamically by their type
    allAccounts.forEach((account: any) => {
      const type = account.account_type?.toLowerCase() || "other";
      if (!groups[type]) {
        groups[type] = [];
      }
      groups[type].push(account);
    });

    // Sort groups by preferred order
    const typeOrder = [
      "retirement",
      "taxable",
      "crypto",
      "property",
      "vehicle",
    ];
    const sortedGroups: Record<string, any[]> = {};

    typeOrder.forEach((type) => {
      if (groups[type]) {
        sortedGroups[type] = groups[type];
      }
    });

    // Add any remaining types not in the order
    Object.keys(groups).forEach((type) => {
      if (!typeOrder.includes(type)) {
        sortedGroups[type] = groups[type];
      }
    });

    return sortedGroups;
  }, [allAccounts]);

  // These useMemo hooks must stay ABOVE every early return (React rules of hooks).
  const oldestPriceAsOf = useMemo(() => {
    if (!portfolio) return null;
    const dates = portfolio.holdings_by_ticker
      .map((h) => h.price_as_of)
      .filter(Boolean)
      .map((d) => new Date(d!));
    if (dates.length === 0) return null;
    return dates.reduce((oldest, d) => (d < oldest ? d : oldest));
  }, [portfolio]);

  const [now] = useState(() => Date.now());
  const priceAgeLabel = useMemo(() => {
    if (!oldestPriceAsOf) return null;
    const diffMs = now - oldestPriceAsOf.getTime();
    const diffH = Math.floor(diffMs / 3_600_000);
    if (diffH < 1) return "Prices updated < 1h ago";
    if (diffH < 24) return `Prices updated ${diffH}h ago`;
    const diffD = Math.floor(diffH / 24);
    return `Prices updated ${diffD}d ago`;
  }, [oldestPriceAsOf, now]);

  if (isLoading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" color="brand.500" />
      </Center>
    );
  }

  if (isError) {
    return (
      <Container maxW="container.lg" py={8}>
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          Unable to load portfolio data. Please try again.
        </Alert>
      </Container>
    );
  }

  // Show empty state only if no portfolio data AND no accounts with balances
  if (
    !portfolio ||
    (portfolio.holdings_by_ticker.length === 0 &&
      portfolio.holdings_by_account.length === 0 &&
      portfolio.total_value === 0)
  ) {
    return (
      <Container maxW="container.lg" py={8}>
        <VStack spacing={6} align="stretch">
          <Heading size="lg">Investments</Heading>
          <Card>
            <CardBody>
              <VStack spacing={6} py={6}>
                <VStack spacing={2}>
                  <Heading size="md">
                    {onboardingGoal === "investments"
                      ? "Let's look at your investments"
                      : "No investment accounts yet"}
                  </Heading>
                  <Text color="text.secondary" textAlign="center" maxW="md">
                    {onboardingGoal === "investments"
                      ? "You said you want to understand your investments — connect a brokerage, 401(k), or IRA to see your portfolio, expense ratios, and how your money is split."
                      : "Connect a brokerage, 401(k), or IRA to see your complete investment picture in one place."}
                  </Text>
                </VStack>
                <SimpleGrid
                  columns={{ base: 1, sm: 3 }}
                  spacing={3}
                  w="full"
                  maxW="lg"
                >
                  {[
                    {
                      label:
                        "Your total invested amount and how much it's grown",
                      color: "blue",
                    },
                    {
                      label:
                        "How your money is split between stocks (growth) and bonds (stability)",
                      color: "green",
                    },
                    {
                      label:
                        "Hidden fees you're paying each year — and what they cost you long-term",
                      color: "orange",
                    },
                  ].map((item) => (
                    <Box
                      key={item.label}
                      p={3}
                      bg="bg.subtle"
                      borderRadius="md"
                      textAlign="center"
                    >
                      <Text fontSize="xs" color="text.secondary">
                        {item.label}
                      </Text>
                    </Box>
                  ))}
                </SimpleGrid>
                <Button
                  colorScheme="brand"
                  size="lg"
                  leftIcon={<FiLink />}
                  onClick={onAddAccountOpen}
                >
                  Connect an Investment Account
                </Button>
                <Text fontSize="xs" color="text.muted">
                  You can also add accounts from the Accounts page.
                </Text>
              </VStack>
            </CardBody>
          </Card>
        </VStack>
        <AddAccountModal
          isOpen={isAddAccountOpen}
          onClose={onAddAccountClose}
        />
      </Container>
    );
  }

  const totalGainIsPositive =
    portfolio.total_gain_loss !== null && portfolio.total_gain_loss >= 0;

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        {/* Plain-English portfolio summary */}
        {portfolio.total_value > 0 && (
          <Box
            bg="bg.subtle"
            borderRadius="lg"
            p={4}
            borderLeft="4px solid"
            borderLeftColor="brand.500"
          >
            {isCombinedView && (
              <Text fontSize="xs" color="text.muted" mb={1} fontWeight="medium">
                Combined portfolio across all selected members
              </Text>
            )}
            <Text fontSize="sm" color="text.secondary">
              {(() => {
                const parts: string[] = [];
                parts.push(
                  `Your portfolio is worth ${formatCurrency(portfolio.total_value)}.`,
                );
                if (portfolio.total_gain_loss_percent !== null) {
                  const pct = portfolio.total_gain_loss_percent;
                  const dir = pct >= 0 ? "up" : "down";
                  parts.push(
                    `You're ${dir} ${Math.abs(pct).toFixed(1)}% overall.`,
                  );
                }
                if (
                  portfolio.total_annual_fees !== null &&
                  portfolio.total_annual_fees > 0 &&
                  portfolio.total_value > 0
                ) {
                  const feePct = (
                    (portfolio.total_annual_fees / portfolio.total_value) *
                    100
                  ).toFixed(2);
                  if (Number(feePct) > 0.5) {
                    parts.push(
                      `Your funds cost about ${formatCurrency(portfolio.total_annual_fees)}/year in fees (${feePct}% of your portfolio) — consider switching to lower-cost index funds.`,
                    );
                  } else {
                    parts.push(
                      `Your fund fees are low at ${feePct}% annually — great job keeping costs down.`,
                    );
                  }
                }
                return parts.join(" ");
              })()}
            </Text>
          </Box>
        )}

        {/* Header with Date Filter and Category Toggles */}
        <HStack justify="space-between" align="flex-start">
          <VStack align="flex-start" spacing={0}>
            <HStack spacing={1}>
              <Heading size="lg">Investments</Heading>
              <HelpHint
                hint={helpContent.investments.accountExclusions}
                size="md"
              />
            </HStack>
            {priceAgeLabel && (
              <Text fontSize="xs" color="text.muted">
                {priceAgeLabel}
              </Text>
            )}
          </VStack>
          <HStack spacing={4}>
            {/* Account Filter */}
            {allAccounts && allAccounts.length > 0 && (
              <Menu closeOnSelect={false}>
                <MenuButton
                  as={Button}
                  size="sm"
                  variant="outline"
                  leftIcon={<FiFilter />}
                >
                  Filter Accounts
                  {hiddenAccountIds.length > 0 && (
                    <Badge ml={2} colorScheme="red" fontSize="xs">
                      {hiddenAccountIds.length} hidden
                    </Badge>
                  )}
                </MenuButton>
                <MenuList minWidth="280px" maxHeight="400px" overflowY="auto">
                  <Box px={3} py={2}>
                    <Text
                      fontSize="sm"
                      fontWeight="semibold"
                      mb={3}
                      color="text.heading"
                    >
                      Select accounts to display:
                    </Text>
                    <VStack align="stretch" spacing={3}>
                      {Object.entries(groupedAccounts).map(
                        ([type, accounts]: [string, any]) => (
                          <Box key={type}>
                            <Text
                              fontSize="xs"
                              fontWeight="bold"
                              textTransform="uppercase"
                              color="text.muted"
                              mb={2}
                              letterSpacing="wide"
                            >
                              {type === "retirement"
                                ? "Retirement"
                                : type === "taxable"
                                  ? "Taxable"
                                  : type === "crypto"
                                    ? "Crypto"
                                    : type === "property"
                                      ? "Property"
                                      : type === "vehicle"
                                        ? "Vehicles"
                                        : type.charAt(0).toUpperCase() +
                                          type.slice(1)}
                            </Text>
                            <Stack spacing={2} ml={2}>
                              {accounts.map((account: any) => (
                                <Checkbox
                                  key={account.id}
                                  isChecked={
                                    !hiddenAccountIds.includes(account.id)
                                  }
                                  onChange={(e) => {
                                    if (e.target.checked) {
                                      setHiddenAccountIds((prev) =>
                                        prev.filter((id) => id !== account.id),
                                      );
                                    } else {
                                      setHiddenAccountIds((prev) => [
                                        ...prev,
                                        account.id,
                                      ]);
                                    }
                                  }}
                                >
                                  <VStack align="flex-start" spacing={0}>
                                    <Text fontSize="sm" fontWeight="medium">
                                      {account.name}
                                    </Text>
                                    <Text fontSize="xs" color="text.secondary">
                                      {formatCurrency(
                                        Number(account.current_balance) || 0,
                                      )}
                                    </Text>
                                  </VStack>
                                </Checkbox>
                              ))}
                            </Stack>
                          </Box>
                        ),
                      )}
                    </VStack>
                    {hiddenAccountIds.length > 0 && (
                      <Button
                        size="sm"
                        variant="ghost"
                        colorScheme="blue"
                        mt={3}
                        width="100%"
                        onClick={() => setHiddenAccountIds([])}
                      >
                        Show All Accounts
                      </Button>
                    )}
                  </Box>
                </MenuList>
              </Menu>
            )}
            <Tooltip
              label={
                canEdit
                  ? "Fetch latest prices from Yahoo Finance"
                  : "Read-only: cannot refresh prices"
              }
            >
              <Button
                leftIcon={<FiRefreshCw />}
                size="sm"
                variant="outline"
                isLoading={refreshPricesMutation.isPending}
                onClick={() => refreshPricesMutation.mutate()}
                isDisabled={!canEdit}
              >
                Refresh Prices
              </Button>
            </Tooltip>
          </HStack>
        </HStack>

        {/* RMD Alert (if applicable) */}
        <RMDAlert userId={activeUserId} />

        {/* Portfolio Summary Cards */}
        <Card>
          <CardBody>
            <HStack justify="space-between" mb={4}>
              <Heading size="md">Portfolio Summary</Heading>
              <IconButton
                aria-label="Toggle summary"
                icon={
                  expandedSections.includes("summary") ? (
                    <FiChevronUp />
                  ) : (
                    <FiChevronDown />
                  )
                }
                size="sm"
                variant="ghost"
                onClick={() => toggleSection("summary")}
              />
            </HStack>
            <Collapse in={expandedSections.includes("summary")}>
              <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4}>
                {/* Total Value */}
                <Card>
                  <CardBody>
                    <Stat>
                      <StatLabel>Total Portfolio Value</StatLabel>
                      <StatNumber fontSize="2xl">
                        {formatCurrency(portfolio.total_value)}
                      </StatNumber>
                      {portfolio.total_cost_basis && (
                        <StatHelpText fontSize="sm">
                          What you paid:{" "}
                          {formatCurrency(portfolio.total_cost_basis)}
                        </StatHelpText>
                      )}
                    </Stat>
                  </CardBody>
                </Card>

                {/* Total Gain/Loss */}
                {portfolio.total_gain_loss !== null && (
                  <Card>
                    <CardBody>
                      <Stat>
                        <StatLabel>Total Gain/Loss</StatLabel>
                        <StatNumber
                          fontSize="2xl"
                          color={
                            totalGainIsPositive
                              ? "finance.positive"
                              : "finance.negative"
                          }
                        >
                          {formatCurrency(portfolio.total_gain_loss)}
                        </StatNumber>
                        {portfolio.total_gain_loss_percent !== null && (
                          <StatHelpText>
                            <StatArrow
                              type={
                                totalGainIsPositive ? "increase" : "decrease"
                              }
                            />
                            {formatPercent(portfolio.total_gain_loss_percent)}
                          </StatHelpText>
                        )}
                      </Stat>
                    </CardBody>
                  </Card>
                )}

                {/* Annual Fees */}
                {portfolio.total_annual_fees !== null &&
                  portfolio.total_annual_fees > 0 && (
                    <Card>
                      <CardBody>
                        <Stat>
                          <StatLabel>Annual Fees</StatLabel>
                          <StatNumber fontSize="2xl" color="orange.600">
                            {formatCurrency(portfolio.total_annual_fees)}
                          </StatNumber>
                          <StatHelpText>
                            {(
                              (portfolio.total_annual_fees /
                                portfolio.total_value) *
                              100
                            ).toFixed(3)}
                            % of portfolio
                          </StatHelpText>
                        </Stat>
                      </CardBody>
                    </Card>
                  )}

                {/* Stocks */}
                {portfolio.stocks_value > 0 && (
                  <Card>
                    <CardBody>
                      <Stat>
                        <StatLabel>Stocks</StatLabel>
                        <StatNumber fontSize="xl">
                          {formatCurrency(portfolio.stocks_value)}
                        </StatNumber>
                        <StatHelpText>
                          {(
                            (portfolio.stocks_value / portfolio.total_value) *
                            100
                          ).toFixed(1)}
                          %
                        </StatHelpText>
                      </Stat>
                    </CardBody>
                  </Card>
                )}

                {/* ETFs */}
                {portfolio.etf_value > 0 && (
                  <Card>
                    <CardBody>
                      <Stat>
                        <StatLabel>ETFs</StatLabel>
                        <StatNumber fontSize="xl">
                          {formatCurrency(portfolio.etf_value)}
                        </StatNumber>
                        <StatHelpText>
                          {(
                            (portfolio.etf_value / portfolio.total_value) *
                            100
                          ).toFixed(1)}
                          %
                        </StatHelpText>
                      </Stat>
                    </CardBody>
                  </Card>
                )}
              </SimpleGrid>
            </Collapse>
          </CardBody>
        </Card>

        {/* Category & Geographic Breakdown */}
        {portfolio.category_breakdown && (
          <Card>
            <CardBody>
              <HStack justify="space-between" mb={4}>
                <Heading size="md">Category Breakdown</Heading>
                <IconButton
                  aria-label="Toggle breakdown"
                  icon={
                    expandedSections.includes("breakdown") ? (
                      <FiChevronUp />
                    ) : (
                      <FiChevronDown />
                    )
                  }
                  size="sm"
                  variant="ghost"
                  onClick={() => toggleSection("breakdown")}
                />
              </HStack>
              <Collapse in={expandedSections.includes("breakdown")}>
                <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} mb={4}>
                  {/* Retirement */}
                  {portfolio.category_breakdown.retirement_value > 0 && (
                    <Card variant="outline">
                      <CardBody>
                        <Stat>
                          <StatLabel>Retirement Accounts</StatLabel>
                          <StatNumber fontSize="xl">
                            {formatCurrency(
                              portfolio.category_breakdown.retirement_value,
                            )}
                          </StatNumber>
                          <StatHelpText>
                            {portfolio.category_breakdown.retirement_percent
                              ? `${Number(portfolio.category_breakdown.retirement_percent).toFixed(1)}%`
                              : "N/A"}
                          </StatHelpText>
                        </Stat>
                      </CardBody>
                    </Card>
                  )}

                  {/* Taxable */}
                  {portfolio.category_breakdown.taxable_value > 0 && (
                    <Card variant="outline">
                      <CardBody>
                        <Stat>
                          <StatLabel>Taxable Accounts</StatLabel>
                          <StatNumber fontSize="xl">
                            {formatCurrency(
                              portfolio.category_breakdown.taxable_value,
                            )}
                          </StatNumber>
                          <StatHelpText>
                            {portfolio.category_breakdown.taxable_percent
                              ? `${Number(portfolio.category_breakdown.taxable_percent).toFixed(1)}%`
                              : "N/A"}
                          </StatHelpText>
                        </Stat>
                      </CardBody>
                    </Card>
                  )}

                  {/* Other */}
                  {portfolio.category_breakdown.other_value > 0 && (
                    <Card variant="outline">
                      <CardBody>
                        <Stat>
                          <StatLabel>Other Assets</StatLabel>
                          <StatNumber fontSize="xl">
                            {formatCurrency(
                              portfolio.category_breakdown.other_value,
                            )}
                          </StatNumber>
                          <StatHelpText>
                            {portfolio.category_breakdown.other_percent
                              ? `${Number(portfolio.category_breakdown.other_percent).toFixed(1)}%`
                              : "N/A"}
                          </StatHelpText>
                        </Stat>
                      </CardBody>
                    </Card>
                  )}
                </SimpleGrid>

                {/* Geographic Breakdown */}
                {portfolio.geographic_breakdown && (
                  <>
                    <Divider my={4} />
                    <Heading size="sm" mb={4}>
                      Geographic Allocation
                    </Heading>
                    <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
                      {/* Domestic */}
                      {portfolio.geographic_breakdown.domestic_value > 0 && (
                        <Card variant="outline">
                          <CardBody>
                            <Stat>
                              <StatLabel>Domestic</StatLabel>
                              <StatNumber fontSize="lg">
                                {formatCurrency(
                                  portfolio.geographic_breakdown.domestic_value,
                                )}
                              </StatNumber>
                              <StatHelpText>
                                {portfolio.geographic_breakdown.domestic_percent
                                  ? `${Number(portfolio.geographic_breakdown.domestic_percent).toFixed(1)}%`
                                  : "N/A"}
                              </StatHelpText>
                            </Stat>
                          </CardBody>
                        </Card>
                      )}

                      {/* International */}
                      {portfolio.geographic_breakdown.international_value >
                        0 && (
                        <Card variant="outline">
                          <CardBody>
                            <Stat>
                              <StatLabel>International</StatLabel>
                              <StatNumber fontSize="lg">
                                {formatCurrency(
                                  portfolio.geographic_breakdown
                                    .international_value,
                                )}
                              </StatNumber>
                              <StatHelpText>
                                {portfolio.geographic_breakdown
                                  .international_percent
                                  ? `${Number(portfolio.geographic_breakdown.international_percent).toFixed(1)}%`
                                  : "N/A"}
                              </StatHelpText>
                            </Stat>
                          </CardBody>
                        </Card>
                      )}

                      {/* Unknown */}
                      {portfolio.geographic_breakdown.unknown_value > 0 && (
                        <Card variant="outline">
                          <CardBody>
                            <Stat>
                              <StatLabel>Other/Unknown</StatLabel>
                              <StatNumber fontSize="lg">
                                {formatCurrency(
                                  portfolio.geographic_breakdown.unknown_value,
                                )}
                              </StatNumber>
                              <StatHelpText>
                                {portfolio.geographic_breakdown.unknown_percent
                                  ? `${Number(portfolio.geographic_breakdown.unknown_percent).toFixed(1)}%`
                                  : "N/A"}
                              </StatHelpText>
                            </Stat>
                          </CardBody>
                        </Card>
                      )}
                    </SimpleGrid>
                  </>
                )}
              </Collapse>
            </CardBody>
          </Card>
        )}

        {/* Investment Analysis Tabs */}
        <Card>
          <CardBody>
            {/* Row 1: Category headers — tab-bar style */}
            <SimpleGrid
              columns={3}
              borderBottom="2px solid"
              borderColor="border.muted"
            >
              {(
                [
                  {
                    key: "portfolio",
                    label: "Portfolio",
                    indexes: [0, 1, 5, 10],
                  },
                  {
                    key: "projections",
                    label: "Projections",
                    indexes: [2, 3, 4, 13],
                  },
                  {
                    key: "optimization",
                    label: "Optimization",
                    indexes: [6, 7, 8, 9, 11, 12],
                  },
                ] as const
              ).map((group) => {
                const isActive = group.indexes.includes(selectedTabIndex);
                return (
                  <Button
                    key={group.key}
                    size="lg"
                    variant="ghost"
                    borderRadius={0}
                    borderBottom="3px solid"
                    borderColor={isActive ? "brand.500" : "transparent"}
                    mb="-2px"
                    color={isActive ? "brand.500" : "text.secondary"}
                    bg={isActive ? "brand.50" : "transparent"}
                    fontWeight={isActive ? "bold" : "medium"}
                    fontSize="md"
                    _dark={{
                      bg: isActive ? "whiteAlpha.100" : "transparent",
                    }}
                    _hover={{
                      bg: isActive ? "brand.50" : "bg.subtle",
                      borderColor: isActive ? "brand.500" : "border.muted",
                      _dark: {
                        bg: isActive ? "whiteAlpha.100" : "bg.subtle",
                      },
                    }}
                    onClick={() => {
                      if (!isActive) {
                        setSelectedTabIndex(group.indexes[0]);
                      }
                    }}
                  >
                    {group.label}
                  </Button>
                );
              })}
            </SimpleGrid>

            {/* Row 2: Sub-navigation for active category */}
            <HStack spacing={8} mt={4} mb={5} pl={1}>
              {/* Portfolio sub-items */}
              {[0, 1, 5, 10].includes(selectedTabIndex) && (
                <>
                  {(
                    [
                      {
                        idx: 0,
                        label: "Asset Allocation",
                        hint: helpContent.investments.assetAllocation,
                      },
                      {
                        idx: 1,
                        label: "Sector Breakdown",
                        hint: helpContent.investments.sectorBreakdown,
                      },
                      {
                        idx: 5,
                        label: "Holdings Detail",
                        hint: helpContent.investments.holdingsDetail,
                      },
                      {
                        idx: 10,
                        label: "Dividend Income",
                        hint: helpContent.investments.dividendIncome,
                      },
                    ] as const
                  ).map((item) => (
                    <Text
                      key={item.idx}
                      as="button"
                      fontSize="md"
                      fontWeight={
                        selectedTabIndex === item.idx ? "semibold" : "normal"
                      }
                      color={
                        selectedTabIndex === item.idx
                          ? "brand.500"
                          : "text.secondary"
                      }
                      borderBottom="2px solid"
                      borderColor={
                        selectedTabIndex === item.idx
                          ? "brand.500"
                          : "transparent"
                      }
                      pb={2}
                      cursor="pointer"
                      _hover={{ color: "brand.500" }}
                      onClick={() => setSelectedTabIndex(item.idx)}
                    >
                      {item.label}
                      {"hint" in item && <HelpHint hint={item.hint} />}
                    </Text>
                  ))}
                </>
              )}

              {/* Projections sub-items */}
              {[2, 3, 4, 13].includes(selectedTabIndex) && (
                <>
                  {(
                    [
                      {
                        idx: 2,
                        label: "Monte Carlo Projection",
                        hint: helpContent.investments.futureGrowth,
                      },
                      {
                        idx: 3,
                        label: "Performance Trends",
                        hint: helpContent.investments.performanceTrends,
                      },
                      {
                        idx: 4,
                        label: "Risk Analysis",
                        hint: helpContent.investments.riskAnalysis,
                      },
                      {
                        idx: 13,
                        label: "Benchmark",
                      },
                    ] as const
                  ).map((item) => (
                    <Text
                      key={item.idx}
                      as="button"
                      fontSize="md"
                      fontWeight={
                        selectedTabIndex === item.idx ? "semibold" : "normal"
                      }
                      color={
                        selectedTabIndex === item.idx
                          ? "brand.500"
                          : "text.secondary"
                      }
                      borderBottom="2px solid"
                      borderColor={
                        selectedTabIndex === item.idx
                          ? "brand.500"
                          : "transparent"
                      }
                      pb={2}
                      cursor="pointer"
                      _hover={{ color: "brand.500" }}
                      onClick={() => setSelectedTabIndex(item.idx)}
                    >
                      {item.label}
                      {"hint" in item && <HelpHint hint={item.hint} />}
                    </Text>
                  ))}
                </>
              )}

              {/* Optimization sub-items */}
              {[6, 7, 8, 9, 11, 12].includes(selectedTabIndex) && (
                <>
                  {(
                    [
                      {
                        idx: 6,
                        label: "Fee Analyzer",
                        hint: helpContent.investments.feeAnalysis,
                      },
                      {
                        idx: 7,
                        label: "Roth Conversion",
                        hint: helpContent.investments.rothConversion,
                      },
                      {
                        idx: 8,
                        label: "Tax-Loss Harvesting",
                        hint: helpContent.investments.taxLossHarvesting,
                      },
                      {
                        idx: 9,
                        label: "Rebalancing",
                        hint: helpContent.investments.rebalancing,
                      },
                      {
                        idx: 11,
                        label: "Gain Harvesting",
                        hint: helpContent.investments.capitalGainsHarvesting,
                      },
                      {
                        idx: 12,
                        label: "Stress Test",
                        hint: helpContent.investments.stressTest,
                      },
                    ] as const
                  ).map((item) => (
                    <Text
                      key={item.idx}
                      as="button"
                      fontSize="md"
                      fontWeight={
                        selectedTabIndex === item.idx ? "semibold" : "normal"
                      }
                      color={
                        selectedTabIndex === item.idx
                          ? "brand.500"
                          : "text.secondary"
                      }
                      borderBottom="2px solid"
                      borderColor={
                        selectedTabIndex === item.idx
                          ? "brand.500"
                          : "transparent"
                      }
                      pb={2}
                      cursor="pointer"
                      _hover={{ color: "brand.500" }}
                      onClick={() => setSelectedTabIndex(item.idx)}
                    >
                      {item.label}
                      {"hint" in item && <HelpHint hint={item.hint} />}
                    </Text>
                  ))}
                </>
              )}
            </HStack>

            {/* Active panel content */}
            <Box>
              {selectedTabIndex === 0 && (
                <VStack align="stretch" spacing={6}>
                  {portfolio.asset_classification_estimated && (
                    <Alert status="info" borderRadius="md" fontSize="sm">
                      <AlertIcon />
                      Some holdings couldn't be confirmed with a financial data provider — asset type
                      classifications are estimated. For precise allocations, add a Polygon.io API key
                      in settings.
                    </Alert>
                  )}
                  {portfolio.treemap_data && (
                    <AssetAllocationTreemap
                      key={`treemap-${hiddenAccountIds.join("-")}`}
                      data={portfolio.treemap_data}
                      onDrillDown={handleTreemapDrillDown}
                    />
                  )}
                  <Box>
                    <Heading size="sm" mb={3}>
                      Allocation History
                    </Heading>
                    <AllocationHistoryChart userId={activeUserId} />
                  </Box>
                </VStack>
              )}
              {selectedTabIndex === 1 && (
                <SectorBreakdownChart holdings={portfolio.holdings_by_ticker} />
              )}
              {selectedTabIndex === 2 && (
                <GrowthProjectionsChart
                  currentValue={portfolio.total_value}
                  monthlyContribution={monthlyContribution}
                />
              )}
              {selectedTabIndex === 3 && (
                <PerformanceTrendsChart currentValue={portfolio.total_value} />
              )}
              {selectedTabIndex === 4 && (
                <RiskAnalysisPanel portfolio={portfolio} />
              )}
              {selectedTabIndex === 5 && (
                <HoldingsDetailTable holdings={portfolio.holdings_by_ticker} />
              )}
              {selectedTabIndex === 6 && (
                <FeeAnalysisPanel userId={activeUserId} />
              )}
              {selectedTabIndex === 7 && <RothConversionAnalyzer />}
              {selectedTabIndex === 8 && <TaxLossHarvestingPanel />}
              {selectedTabIndex === 9 && <RebalancingPanel />}
              {selectedTabIndex === 10 && <DividendIncomePanel />}
              {selectedTabIndex === 11 && <CapitalGainsHarvestingPanel />}
              {selectedTabIndex === 12 && <StressTestPanel />}
              {selectedTabIndex === 13 && <BenchmarkComparisonPanel userId={activeUserId} />}
            </Box>
          </CardBody>
        </Card>

        {/* Holdings by Account */}
        <Card>
          <CardBody>
            <HStack justify="space-between" mb={4}>
              <VStack align="flex-start" spacing={1}>
                <Heading size="md">Holdings by Account</Heading>
                {selectedNode && (
                  <Text fontSize="sm" color="text.secondary">
                    Filtered by: {selectedNode.name}
                  </Text>
                )}
              </VStack>
              <HStack>
                {selectedNode && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setSelectedNode(null)}
                  >
                    Clear Filter
                  </Button>
                )}
                <IconButton
                  aria-label="Toggle holdings"
                  icon={
                    expandedSections.includes("holdings") ? (
                      <FiChevronUp />
                    ) : (
                      <FiChevronDown />
                    )
                  }
                  size="sm"
                  variant="ghost"
                  onClick={() => toggleSection("holdings")}
                />
              </HStack>
            </HStack>
            <Collapse in={expandedSections.includes("holdings")}>
              <VStack spacing={4} align="stretch">
                {portfolio.holdings_by_account.map((account) => (
                  <AccountHoldingsCard
                    key={account.account_id}
                    account={account}
                    isExpanded={expandedAccounts.includes(account.account_id)}
                    onToggleExpand={(accountId) => {
                      setExpandedAccounts((prev) =>
                        prev.includes(accountId)
                          ? prev.filter((id) => id !== accountId)
                          : [...prev, accountId],
                      );
                    }}
                    formatCurrency={formatCurrency}
                    formatShares={formatShares}
                  />
                ))}
              </VStack>
            </Collapse>
          </CardBody>
        </Card>
      </VStack>

      {/* Style Box Modal */}
      <StyleBoxModal isOpen={isStyleBoxOpen} onClose={onStyleBoxClose} />
    </Container>
  );
};
