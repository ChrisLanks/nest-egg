/**
 * Investments page showing portfolio overview and holdings
 */

import {
  Alert,
  AlertIcon,
  Box,
  Container,
  Heading,
  Progress,
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
  MenuItem,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
} from '@chakra-ui/react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useEffect, useMemo, useRef } from 'react';
import { FiChevronDown, FiChevronUp, FiFilter, FiRefreshCw } from 'react-icons/fi';
import api from '../services/api';
import { useUserView } from '../contexts/UserViewContext';
import { AssetAllocationTreemap } from '../features/investments/components/AssetAllocationTreemap';
import { HoldingsDetailTable } from '../features/investments/components/HoldingsDetailTable';
import { GrowthProjectionsChart } from '../features/investments/components/GrowthProjectionsChart';
import { SectorBreakdownChart } from '../features/investments/components/SectorBreakdownChart';
import PerformanceTrendsChart from '../features/investments/components/PerformanceTrendsChart';
import RiskAnalysisPanel from '../features/investments/components/RiskAnalysisPanel';
import StyleBoxModal from '../features/investments/components/StyleBoxModal';
import { RMDAlert } from '../features/investments/components/RMDAlert';

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
}

export const InvestmentsPage = () => {
  // Use global user view context
  const { selectedUserId } = useUserView();

  // Drilled-down treemap node
  const [selectedNode, setSelectedNode] = useState<TreemapNode | null>(null);

  // Expanded sections state
  const [expandedSections, setExpandedSections] = useState<string[]>(['summary', 'breakdown', 'treemap', 'holdings']);

  // Expanded accounts state (default: all expanded)
  const [expandedAccounts, setExpandedAccounts] = useState<string[]>([]);

  // Style Box modal
  const { isOpen: isStyleBoxOpen, onOpen: onStyleBoxOpen, onClose: onStyleBoxClose } = useDisclosure();

  const toast = useToast();
  const queryClient = useQueryClient();

  const refreshPricesMutation = useMutation({
    mutationFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const response = await api.post('/market-data/holdings/refresh-all', null, { params });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
      toast({
        title: `Prices refreshed`,
        description: `Updated ${data.updated} of ${data.total} holdings via ${data.provider}`,
        status: 'success',
        duration: 4000,
        isClosable: true,
      });
    },
    onError: () => {
      toast({ title: 'Failed to refresh prices', status: 'error', duration: 3000 });
    },
  });

  // Hidden accounts state (persisted to localStorage)
  const [hiddenAccountIds, setHiddenAccountIds] = useState<string[]>(() => {
    const saved = localStorage.getItem('hiddenAccounts');
    return saved ? JSON.parse(saved) : [];
  });

  // Save hidden accounts to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('hiddenAccounts', JSON.stringify(hiddenAccountIds));
  }, [hiddenAccountIds]);

  // Selected tab index (persisted to localStorage)
  const [selectedTabIndex, setSelectedTabIndex] = useState<number>(() => {
    const saved = localStorage.getItem('investmentsTabIndex');
    return saved ? parseInt(saved, 10) : 0;
  });

  // Save selected tab index to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('investmentsTabIndex', selectedTabIndex.toString());
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
    queryKey: ['accounts', selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const response = await api.get('/accounts', { params });
      return response.data;
    },
  });

  // Track if we've initialized default hidden accounts
  const hasInitializedDefaults = useRef(false);

  // Set default hidden accounts on first load (hide property and vehicles)
  useEffect(() => {
    if (allAccounts && !hasInitializedDefaults.current) {
      const savedState = localStorage.getItem('hiddenAccounts');
      const savedMigrationFlag = localStorage.getItem('hiddenAccounts_migratedV1');

      // Get non-investment property and vehicle account IDs to hide
      // Hide: personal residences, vacation homes, and vehicles
      // Show: investment properties (they're investments!)
      const nonInvestmentAssets = allAccounts
        .filter((account: any) => {
          // Hide all vehicles
          if (account.account_type === 'vehicle') return true;

          // For properties, only hide personal residences and vacation homes
          if (account.account_type === 'property') {
            return account.property_type === 'personal_residence' ||
                   account.property_type === 'vacation_home';
          }

          return false;
        })
        .map((account: any) => account.id);

      // If no saved preferences, or if we haven't migrated yet, apply the new default
      if (!savedState || !savedMigrationFlag) {
        if (nonInvestmentAssets.length > 0) {
          setHiddenAccountIds(nonInvestmentAssets);
          localStorage.setItem('hiddenAccounts_migratedV1', 'true');
        }
      }

      hasInitializedDefaults.current = true;
    }
  }, [allAccounts]);

  // Fetch portfolio summary
  const { data: rawPortfolio, isLoading } = useQuery<PortfolioSummary>({
    queryKey: ['portfolio', selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const response = await api.get('/holdings/portfolio', { params });

      // Convert treemap data to use numbers instead of strings
      if (response.data.treemap_data) {
        response.data.treemap_data = convertTreemapNode(response.data.treemap_data);
        console.log('🗺️ Treemap Data (converted):', response.data.treemap_data);
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
      (account) => !hiddenAccountIds.includes(account.account_id)
    );

    // Filter holdings by ticker to only include visible accounts
    const visibleHoldingsByTicker = rawPortfolio.holdings_by_ticker.filter((holding) => {
      return visibleAccounts.some((account) =>
        account.holdings.some((h) => h.ticker === holding.ticker)
      );
    });

    // Recalculate total value by subtracting hidden accounts from backend total
    // This avoids needing to replicate the backend's complex portfolio calculation logic

    // Start with the backend's correct total
    let newTotalValue = rawPortfolio.total_value;

    // Subtract value of hidden accounts
    if (hiddenAccountIds.length > 0 && allAccounts) {
      const hiddenAccounts = allAccounts.filter((account: any) =>
        hiddenAccountIds.includes(account.id)
      );

      hiddenAccounts.forEach((account: any) => {
        // For investment accounts, use account_value from holdings_by_account if available
        const holdingsAccount = rawPortfolio.holdings_by_account.find(
          (h) => h.account_id === account.id
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
    const allVisibleAccounts = allAccounts?.filter(
      (account: any) => !hiddenAccountIds.includes(account.id)
    ) || [];

    // Recalculate treemap data based on visible accounts
    let newTreemapData = rawPortfolio.treemap_data;
    if (rawPortfolio.treemap_data && rawPortfolio.treemap_data.children) {
      // Get visible account IDs and names for filtering
      const visibleAccountIds = new Set(allVisibleAccounts.map((a: any) => a.id));
      const visibleAccountNames = new Set(allVisibleAccounts.map((a: any) => a.name));

      // Helper to recursively filter treemap nodes
      const filterTreemapNode = (node: any, categoryName: string): any => {
        if (!node.children) return node;

        // Filter children recursively
        const filteredChildren = node.children
          .map((child: any) => {
            // Base case: leaf node (individual account or ticker)
            if (!child.children) {
              // For Cash accounts, check if visible by name
              if (categoryName === 'Cash') {
                return visibleAccountNames.has(child.name) ? child : null;
              }
              // For Investment Accounts, check if visible by name (strip "(Holdings Unknown)" suffix)
              if (categoryName === 'Investment Accounts') {
                const accountName = child.name.replace(' (Holdings Unknown)', '');
                return visibleAccountNames.has(accountName) ? child : null;
              }
              // For account-based leaves (Property, Vehicles), check if visible by name
              if (categoryName === 'Property & Vehicles') {
                return visibleAccountNames.has(child.name) ? child : null;
              }
              // For Crypto, check if ticker is in visible crypto accounts
              if (categoryName === 'Crypto') {
                const hasTicker = visibleAccounts.some((account) =>
                  account.holdings.some((h: any) => h.ticker === child.name)
                );
                return hasTicker ? child : null;
              }
              // For holdings-based leaves (tickers), check if in visible accounts
              return visibleAccounts.some((account) =>
                account.holdings.some((h: any) => h.ticker === child.name)
              ) ? child : null;
            }

            // Recursive case: intermediate node (cap sizes, asset types, etc.)
            const filtered = filterTreemapNode(child, categoryName);
            return filtered && filtered.value > 0 ? filtered : null;
          })
          .filter((c: any) => c !== null);

        // Recalculate value and percent for this node
        const newValue = filteredChildren.reduce((sum: number, c: any) => sum + c.value, 0);

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
            percent: newTotalValue > 0 ? (filtered.value / newTotalValue) * 100 : 0,
          };
        })
        .filter(cat => cat.value > 0); // Remove categories with 0 value

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
    if (amount === null || amount === undefined) return 'N/A';
    const num = Number(amount);
    if (isNaN(num)) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num);
  };

  const formatPercent = (percent: number | null) => {
    if (percent === null || percent === undefined) return 'N/A';
    const num = Number(percent);
    if (isNaN(num)) return 'N/A';
    return `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`;
  };

  const formatShares = (shares: number) => {
    const num = Number(shares);
    if (isNaN(num)) return '0';
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 6,
    }).format(num);
  };

  const toggleSection = (section: string) => {
    setExpandedSections((prev) =>
      prev.includes(section) ? prev.filter((s) => s !== section) : [...prev, section]
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
      const type = account.account_type?.toLowerCase() || 'other';
      if (!groups[type]) {
        groups[type] = [];
      }
      groups[type].push(account);
    });

    // Sort groups by preferred order
    const typeOrder = ['retirement', 'taxable', 'crypto', 'property', 'vehicle'];
    const sortedGroups: Record<string, any[]> = {};

    typeOrder.forEach(type => {
      if (groups[type]) {
        sortedGroups[type] = groups[type];
      }
    });

    // Add any remaining types not in the order
    Object.keys(groups).forEach(type => {
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

  const priceAgeLabel = useMemo(() => {
    if (!oldestPriceAsOf) return null;
    const diffMs = Date.now() - oldestPriceAsOf.getTime();
    const diffH = Math.floor(diffMs / 3_600_000);
    if (diffH < 1) return 'Prices updated < 1h ago';
    if (diffH < 24) return `Prices updated ${diffH}h ago`;
    const diffD = Math.floor(diffH / 24);
    return `Prices updated ${diffD}d ago`;
  }, [oldestPriceAsOf]);

  const holdingsWithFees = useMemo(
    () =>
      (portfolio?.holdings_by_ticker ?? [])
        .filter((h) => h.expense_ratio !== null && h.annual_fee !== null)
        .sort((a, b) => (b.expense_ratio ?? 0) - (a.expense_ratio ?? 0)),
    [portfolio]
  );

  if (isLoading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" color="brand.500" />
      </Center>
    );
  }

  // Show empty state only if no portfolio data AND no accounts with balances
  if (!portfolio || (portfolio.holdings_by_ticker.length === 0 && portfolio.holdings_by_account.length === 0 && portfolio.total_value === 0)) {
    return (
      <Container maxW="container.lg" py={8}>
        <VStack spacing={6} align="stretch">
          <Heading size="lg">Investments</Heading>
          <Card>
            <CardBody>
              <VStack spacing={4}>
                <Text color="gray.500">No investment accounts found.</Text>
                <Text fontSize="sm" color="gray.600">
                  Add investment accounts to see your portfolio here.
                </Text>
              </VStack>
            </CardBody>
          </Card>
        </VStack>
      </Container>
    );
  }

  const totalGainIsPositive = portfolio.total_gain_loss !== null && portfolio.total_gain_loss >= 0;

  // --- Fee Analyzer helpers ---
  // 30-year opportunity cost of fees assuming 7% market growth
  const GROWTH_RATE = 0.07;
  const YEARS = 30;
  const FEE_DRAG_MULTIPLIER = ((Math.pow(1 + GROWTH_RATE, YEARS) - 1) / GROWTH_RATE); // ≈ 94.5
  const HIGH_FEE_THRESHOLD = 0.005; // 0.5% expense ratio
  const VANGUARD_BENCHMARK = 0.0005; // 0.05% — low-cost benchmark

  const totalAnnualFees = portfolio.total_annual_fees ?? 0;
  const feeDrag30yr = totalAnnualFees * FEE_DRAG_MULTIPLIER;
  const weightedAvgER =
    portfolio.total_value > 0
      ? holdingsWithFees.reduce(
          (sum, h) => sum + (h.expense_ratio ?? 0) * (h.current_total_value ?? 0),
          0
        ) / portfolio.total_value
      : 0;
  const benchmarkAnnualFees = portfolio.total_value * VANGUARD_BENCHMARK;
  const feeSavingsPotential = Math.max(0, totalAnnualFees - benchmarkAnnualFees);

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        {/* Header with Date Filter and Category Toggles */}
        <HStack justify="space-between" align="flex-start">
          <VStack align="flex-start" spacing={0}>
            <Heading size="lg">Investments</Heading>
            {priceAgeLabel && (
              <Text fontSize="xs" color="gray.500">{priceAgeLabel}</Text>
            )}
          </VStack>
          <HStack spacing={4}>
            {/* Account Filter */}
            {allAccounts && allAccounts.length > 0 && (
              <Menu closeOnSelect={false}>
                <MenuButton as={Button} size="sm" variant="outline" leftIcon={<FiFilter />}>
                  Filter Accounts
                  {hiddenAccountIds.length > 0 && (
                    <Badge ml={2} colorScheme="red" fontSize="xs">
                      {hiddenAccountIds.length} hidden
                    </Badge>
                  )}
                </MenuButton>
                <MenuList minWidth="280px" maxHeight="400px" overflowY="auto">
                  <Box px={3} py={2}>
                    <Text fontSize="sm" fontWeight="semibold" mb={3} color="gray.700">
                      Select accounts to display:
                    </Text>
                    <VStack align="stretch" spacing={3}>
                      {Object.entries(groupedAccounts).map(([type, accounts]: [string, any]) => (
                        <Box key={type}>
                          <Text
                            fontSize="xs"
                            fontWeight="bold"
                            textTransform="uppercase"
                            color="gray.500"
                            mb={2}
                            letterSpacing="wide"
                          >
                            {type === 'retirement' ? 'Retirement' :
                             type === 'taxable' ? 'Taxable' :
                             type === 'crypto' ? 'Crypto' :
                             type === 'property' ? 'Property' :
                             type === 'vehicle' ? 'Vehicles' :
                             type.charAt(0).toUpperCase() + type.slice(1)}
                          </Text>
                          <Stack spacing={2} ml={2}>
                            {accounts.map((account: any) => (
                              <Checkbox
                                key={account.id}
                                isChecked={!hiddenAccountIds.includes(account.id)}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setHiddenAccountIds((prev) =>
                                      prev.filter((id) => id !== account.id)
                                    );
                                  } else {
                                    setHiddenAccountIds((prev) => [...prev, account.id]);
                                  }
                                }}
                              >
                                <VStack align="flex-start" spacing={0}>
                                  <Text fontSize="sm" fontWeight="medium">
                                    {account.name}
                                  </Text>
                                  <Text fontSize="xs" color="gray.600">
                                    {formatCurrency(Number(account.current_balance) || 0)}
                                  </Text>
                                </VStack>
                              </Checkbox>
                            ))}
                          </Stack>
                        </Box>
                      ))}
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
            <Tooltip label="Fetch latest prices from Yahoo Finance">
              <Button
                leftIcon={<FiRefreshCw />}
                size="sm"
                variant="outline"
                isLoading={refreshPricesMutation.isPending}
                onClick={() => refreshPricesMutation.mutate()}
              >
                Refresh Prices
              </Button>
            </Tooltip>
          </HStack>
        </HStack>

        {/* RMD Alert (if applicable) */}
        <RMDAlert userId={selectedUserId} />

        {/* Portfolio Summary Cards */}
        <Card>
          <CardBody>
            <HStack justify="space-between" mb={4}>
              <Heading size="md">Portfolio Summary</Heading>
              <IconButton
                aria-label="Toggle summary"
                icon={expandedSections.includes('summary') ? <FiChevronUp /> : <FiChevronDown />}
                size="sm"
                variant="ghost"
                onClick={() => toggleSection('summary')}
              />
            </HStack>
            <Collapse in={expandedSections.includes('summary')}>
              <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4}>
          {/* Total Value */}
          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Total Portfolio Value</StatLabel>
                <StatNumber fontSize="2xl">{formatCurrency(portfolio.total_value)}</StatNumber>
                {portfolio.total_cost_basis && (
                  <StatHelpText fontSize="sm">
                    Cost Basis: {formatCurrency(portfolio.total_cost_basis)}
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
                    color={totalGainIsPositive ? 'green.600' : 'red.600'}
                  >
                    {formatCurrency(portfolio.total_gain_loss)}
                  </StatNumber>
                  {portfolio.total_gain_loss_percent !== null && (
                    <StatHelpText>
                      <StatArrow type={totalGainIsPositive ? 'increase' : 'decrease'} />
                      {formatPercent(portfolio.total_gain_loss_percent)}
                    </StatHelpText>
                  )}
                </Stat>
              </CardBody>
            </Card>
          )}

          {/* Annual Fees */}
          {portfolio.total_annual_fees !== null && portfolio.total_annual_fees > 0 && (
            <Card>
              <CardBody>
                <Stat>
                  <StatLabel>Annual Fees</StatLabel>
                  <StatNumber fontSize="2xl" color="orange.600">
                    {formatCurrency(portfolio.total_annual_fees)}
                  </StatNumber>
                  <StatHelpText>
                    {((portfolio.total_annual_fees / portfolio.total_value) * 100).toFixed(3)}% of portfolio
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
                  <StatNumber fontSize="xl">{formatCurrency(portfolio.stocks_value)}</StatNumber>
                  <StatHelpText>
                    {((portfolio.stocks_value / portfolio.total_value) * 100).toFixed(1)}%
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
                  <StatNumber fontSize="xl">{formatCurrency(portfolio.etf_value)}</StatNumber>
                  <StatHelpText>
                    {((portfolio.etf_value / portfolio.total_value) * 100).toFixed(1)}%
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
                  icon={expandedSections.includes('breakdown') ? <FiChevronUp /> : <FiChevronDown />}
                  size="sm"
                  variant="ghost"
                  onClick={() => toggleSection('breakdown')}
                />
              </HStack>
              <Collapse in={expandedSections.includes('breakdown')}>
                <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} mb={4}>
                  {/* Retirement */}
                  {portfolio.category_breakdown.retirement_value > 0 && (
                    <Card variant="outline">
                      <CardBody>
                        <Stat>
                          <StatLabel>Retirement Accounts</StatLabel>
                          <StatNumber fontSize="xl">
                            {formatCurrency(portfolio.category_breakdown.retirement_value)}
                          </StatNumber>
                          <StatHelpText>
                            {portfolio.category_breakdown.retirement_percent
                              ? `${Number(portfolio.category_breakdown.retirement_percent).toFixed(1)}%`
                              : 'N/A'}
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
                            {formatCurrency(portfolio.category_breakdown.taxable_value)}
                          </StatNumber>
                          <StatHelpText>
                            {portfolio.category_breakdown.taxable_percent
                              ? `${Number(portfolio.category_breakdown.taxable_percent).toFixed(1)}%`
                              : 'N/A'}
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
                            {formatCurrency(portfolio.category_breakdown.other_value)}
                          </StatNumber>
                          <StatHelpText>
                            {portfolio.category_breakdown.other_percent
                              ? `${Number(portfolio.category_breakdown.other_percent).toFixed(1)}%`
                              : 'N/A'}
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
                                {formatCurrency(portfolio.geographic_breakdown.domestic_value)}
                              </StatNumber>
                              <StatHelpText>
                                {portfolio.geographic_breakdown.domestic_percent
                                  ? `${Number(portfolio.geographic_breakdown.domestic_percent).toFixed(1)}%`
                                  : 'N/A'}
                              </StatHelpText>
                            </Stat>
                          </CardBody>
                        </Card>
                      )}

                      {/* International */}
                      {portfolio.geographic_breakdown.international_value > 0 && (
                        <Card variant="outline">
                          <CardBody>
                            <Stat>
                              <StatLabel>International</StatLabel>
                              <StatNumber fontSize="lg">
                                {formatCurrency(portfolio.geographic_breakdown.international_value)}
                              </StatNumber>
                              <StatHelpText>
                                {portfolio.geographic_breakdown.international_percent
                                  ? `${Number(portfolio.geographic_breakdown.international_percent).toFixed(1)}%`
                                  : 'N/A'}
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
                                {formatCurrency(portfolio.geographic_breakdown.unknown_value)}
                              </StatNumber>
                              <StatHelpText>
                                {portfolio.geographic_breakdown.unknown_percent
                                  ? `${Number(portfolio.geographic_breakdown.unknown_percent).toFixed(1)}%`
                                  : 'N/A'}
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
            <Tabs
              variant="enclosed"
              colorScheme="brand"
              index={selectedTabIndex}
              onChange={setSelectedTabIndex}
            >
              <TabList>
                <Tab>Asset Allocation</Tab>
                <Tab>Sector Breakdown</Tab>
                <Tab>Future Growth</Tab>
                <Tab>Performance Trends</Tab>
                <Tab>Risk Analysis</Tab>
                <Tab>Holdings Detail</Tab>
                <Tab>Fee Analyzer</Tab>
              </TabList>

              <TabPanels>
                {/* Tab 1: Asset Allocation */}
                <TabPanel>
                  {portfolio.treemap_data && (
                    <>
                      <AssetAllocationTreemap
                        key={`treemap-${hiddenAccountIds.join('-')}`}
                        data={portfolio.treemap_data}
                        onDrillDown={handleTreemapDrillDown}
                      />
                    </>
                  )}
                </TabPanel>

                {/* Tab 2: Sector Breakdown */}
                <TabPanel>
                  <SectorBreakdownChart
                    holdings={portfolio.holdings_by_ticker}
                  />
                </TabPanel>

                {/* Tab 3: Future Growth Projections */}
                <TabPanel>
                  <GrowthProjectionsChart
                    currentValue={portfolio.total_value}
                  />
                </TabPanel>

                {/* Tab 4: Performance Trends */}
                <TabPanel>
                  <PerformanceTrendsChart
                    currentValue={portfolio.total_value}
                  />
                </TabPanel>

                {/* Tab 5: Risk Analysis */}
                <TabPanel>
                  <RiskAnalysisPanel
                    portfolio={portfolio}
                  />
                </TabPanel>

                {/* Tab 6: Holdings Detail */}
                <TabPanel>
                  <HoldingsDetailTable
                    holdings={portfolio.holdings_by_ticker}
                  />
                </TabPanel>

                {/* Tab 7: Fee Analyzer */}
                <TabPanel>
                  {holdingsWithFees.length === 0 ? (
                    <Alert status="info">
                      <AlertIcon />
                      No expense ratio data available yet. Metadata is enriched daily — check back
                      after prices refresh.
                    </Alert>
                  ) : (
                    <VStack spacing={6} align="stretch">
                      {/* Summary stats */}
                      <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
                        <Card variant="outline">
                          <CardBody py={3}>
                            <Stat>
                              <StatLabel fontSize="xs">Annual Fees</StatLabel>
                              <StatNumber fontSize="lg" color="orange.600">
                                {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(totalAnnualFees)}
                              </StatNumber>
                              <StatHelpText fontSize="xs">
                                {(weightedAvgER * 100).toFixed(3)}% weighted avg ER
                              </StatHelpText>
                            </Stat>
                          </CardBody>
                        </Card>
                        <Card variant="outline">
                          <CardBody py={3}>
                            <Stat>
                              <StatLabel fontSize="xs">30-Year Fee Drag</StatLabel>
                              <Tooltip label={`Opportunity cost of fees compounded at 7%/yr over 30 years (${FEE_DRAG_MULTIPLIER.toFixed(1)}× annual fees)`}>
                                <StatNumber fontSize="lg" color="red.600">
                                  {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(feeDrag30yr)}
                                </StatNumber>
                              </Tooltip>
                              <StatHelpText fontSize="xs">vs investing those fees at 7%</StatHelpText>
                            </Stat>
                          </CardBody>
                        </Card>
                        <Card variant="outline">
                          <CardBody py={3}>
                            <Stat>
                              <StatLabel fontSize="xs">Low-Cost Benchmark</StatLabel>
                              <StatNumber fontSize="lg" color="green.600">
                                {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(benchmarkAnnualFees)}
                              </StatNumber>
                              <StatHelpText fontSize="xs">0.05% ER (Vanguard avg)</StatHelpText>
                            </Stat>
                          </CardBody>
                        </Card>
                        <Card variant="outline">
                          <CardBody py={3}>
                            <Stat>
                              <StatLabel fontSize="xs">Potential Savings</StatLabel>
                              <StatNumber fontSize="lg" color={feeSavingsPotential > 0 ? 'blue.600' : 'green.600'}>
                                {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(feeSavingsPotential)}
                              </StatNumber>
                              <StatHelpText fontSize="xs">
                                {feeSavingsPotential > 0 ? 'vs switching to low-cost index funds' : 'Already low-cost!'}
                              </StatHelpText>
                            </Stat>
                          </CardBody>
                        </Card>
                      </SimpleGrid>

                      {/* High-cost warning */}
                      {holdingsWithFees.some((h) => (h.expense_ratio ?? 0) > HIGH_FEE_THRESHOLD) && (
                        <Alert status="warning">
                          <AlertIcon />
                          Some holdings have expense ratios above 0.5%. Consider low-cost index fund
                          alternatives to reduce long-term drag.
                        </Alert>
                      )}

                      {/* Per-holding fee table */}
                      <Box overflowX="auto">
                        <Table size="sm" variant="simple">
                          <Thead>
                            <Tr>
                              <Th>Holding</Th>
                              <Th isNumeric>Value</Th>
                              <Th isNumeric>Expense Ratio</Th>
                              <Th isNumeric>Annual Fee</Th>
                              <Th isNumeric>30-Yr Drag</Th>
                              <Th>Cost</Th>
                            </Tr>
                          </Thead>
                          <Tbody>
                            {holdingsWithFees.map((h) => {
                              const er = h.expense_ratio ?? 0;
                              const annualFee = h.annual_fee ?? 0;
                              const drag = annualFee * FEE_DRAG_MULTIPLIER;
                              const isHigh = er > HIGH_FEE_THRESHOLD;
                              const isLow = er <= VANGUARD_BENCHMARK * 2;
                              // Progress bar: 0% at 0 ER, 100% at 1%+ ER
                              const progressVal = Math.min(er / 0.01, 1) * 100;
                              return (
                                <Tr key={h.ticker}>
                                  <Td>
                                    <VStack align="flex-start" spacing={0}>
                                      <Text fontWeight="medium" fontSize="sm">{h.ticker}</Text>
                                      {h.name && <Text fontSize="xs" color="gray.500" noOfLines={1}>{h.name}</Text>}
                                    </VStack>
                                  </Td>
                                  <Td isNumeric fontSize="sm">
                                    {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(h.current_total_value ?? 0)}
                                  </Td>
                                  <Td isNumeric>
                                    <VStack align="flex-end" spacing={1}>
                                      <Text fontSize="sm">{(er * 100).toFixed(3)}%</Text>
                                      <Progress
                                        value={progressVal}
                                        size="xs"
                                        width="60px"
                                        colorScheme={isHigh ? 'red' : isLow ? 'green' : 'yellow'}
                                      />
                                    </VStack>
                                  </Td>
                                  <Td isNumeric fontSize="sm" color="orange.600">
                                    {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(annualFee)}
                                  </Td>
                                  <Td isNumeric fontSize="sm" color="red.500">
                                    {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(drag)}
                                  </Td>
                                  <Td>
                                    <Badge
                                      colorScheme={isHigh ? 'red' : isLow ? 'green' : 'yellow'}
                                      fontSize="xs"
                                    >
                                      {isHigh ? 'High' : isLow ? 'Low' : 'Moderate'}
                                    </Badge>
                                  </Td>
                                </Tr>
                              );
                            })}
                          </Tbody>
                        </Table>
                      </Box>
                    </VStack>
                  )}
                </TabPanel>
              </TabPanels>
            </Tabs>
          </CardBody>
        </Card>

        {/* Holdings by Account */}
        <Card>
          <CardBody>
            <HStack justify="space-between" mb={4}>
              <VStack align="flex-start" spacing={1}>
                <Heading size="md">Holdings by Account</Heading>
                {selectedNode && (
                  <Text fontSize="sm" color="gray.600">
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
                  icon={expandedSections.includes('holdings') ? <FiChevronUp /> : <FiChevronDown />}
                  size="sm"
                  variant="ghost"
                  onClick={() => toggleSection('holdings')}
                />
              </HStack>
            </HStack>
            <Collapse in={expandedSections.includes('holdings')}>
              <VStack spacing={4} align="stretch">
                {portfolio.holdings_by_account.map((account) => {
                  const isExpanded = expandedAccounts.includes(account.account_id);

                  return (
                    <Card key={account.account_id} variant="outline">
                      <CardBody>
                        <HStack
                          justify="space-between"
                          cursor="pointer"
                          onClick={() => {
                            setExpandedAccounts((prev) =>
                              prev.includes(account.account_id)
                                ? prev.filter((id) => id !== account.account_id)
                                : [...prev, account.account_id]
                            );
                          }}
                        >
                          <VStack align="flex-start" spacing={0}>
                            <HStack>
                              <Heading size="sm">{account.account_name}</Heading>
                              <Badge colorScheme="purple" size="sm">
                                {account.account_type}
                              </Badge>
                            </HStack>
                            <Text fontSize="lg" fontWeight="bold" color="brand.600">
                              {formatCurrency(account.account_value)}
                            </Text>
                          </VStack>
                          <IconButton
                            aria-label={isExpanded ? 'Collapse' : 'Expand'}
                            icon={isExpanded ? <FiChevronUp /> : <FiChevronDown />}
                            size="sm"
                            variant="ghost"
                          />
                        </HStack>

                        <Collapse in={isExpanded}>
                          <Box mt={4} overflowX="auto">
                            {account.holdings.length === 0 ? (
                              <VStack spacing={2} py={4} align="center">
                                <Text fontSize="sm" color="gray.600">
                                  Holdings details not available for this account.
                                </Text>
                                <Text fontSize="xs" color="gray.500">
                                  Account balance: {formatCurrency(account.account_value)}
                                </Text>
                                <Text fontSize="xs" color="gray.500">
                                  Sync holdings data from your provider to see detailed breakdown.
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
                                    <Th isNumeric>Cost Basis</Th>
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
                                        <Text fontSize="sm" color="gray.600">
                                          {holding.name || '-'}
                                        </Text>
                                      </Td>
                                      <Td isNumeric>{formatShares(holding.shares)}</Td>
                                      <Td isNumeric>
                                        {holding.current_price_per_share
                                          ? formatCurrency(holding.current_price_per_share)
                                          : 'N/A'}
                                      </Td>
                                      <Td isNumeric>
                                        <Text fontWeight="semibold">
                                          {formatCurrency(holding.current_total_value)}
                                        </Text>
                                      </Td>
                                      <Td isNumeric>{formatCurrency(holding.total_cost_basis)}</Td>
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
                  );
                })}
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
