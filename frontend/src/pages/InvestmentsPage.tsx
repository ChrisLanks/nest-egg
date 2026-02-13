/**
 * Investments page showing portfolio overview and holdings
 */

import {
  Box,
  Container,
  Heading,
  Text,
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
  Checkbox,
  CheckboxGroup,
  Stack,
  Divider,
  Collapse,
  IconButton,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { FiChevronDown, FiChevronUp, FiCalendar } from 'react-icons/fi';
import api from '../services/api';
import { AssetAllocationTreemap } from '../features/investments/components/AssetAllocationTreemap';

interface HoldingSummary {
  ticker: string;
  name: string | null;
  total_shares: number;
  total_cost_basis: number | null;
  current_price_per_share: number | null;
  current_total_value: number | null;
  price_as_of: string | null;
  asset_type: string | null;
  gain_loss: number | null;
  gain_loss_percent: number | null;
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
  stocks_value: number;
  bonds_value: number;
  etf_value: number;
  mutual_funds_value: number;
  cash_value: number;
  other_value: number;
  category_breakdown: CategoryBreakdown | null;
  geographic_breakdown: GeographicBreakdown | null;
  treemap_data: TreemapNode | null;
}

export const InvestmentsPage = () => {
  // Category visibility state (default: hide property)
  const [visibleCategories, setVisibleCategories] = useState<string[]>([
    'retirement',
    'taxable',
    'vehicles',
    'crypto',
  ]);

  // Date filter state
  const [dateFilter, setDateFilter] = useState<string>('all');

  // Drilled-down treemap node
  const [selectedNode, setSelectedNode] = useState<TreemapNode | null>(null);

  // Expanded sections state
  const [expandedSections, setExpandedSections] = useState<string[]>(['summary', 'breakdown', 'treemap', 'holdings']);

  // Fetch portfolio summary
  const { data: portfolio, isLoading } = useQuery<PortfolioSummary>({
    queryKey: ['portfolio'],
    queryFn: async () => {
      const response = await api.get('/holdings/portfolio');
      return response.data;
    },
  });

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

  const handleDateFilterChange = (filter: string) => {
    setDateFilter(filter);
    // TODO: Calculate date range and refetch with date parameters
  };

  const handleCategoryToggle = (categories: string[]) => {
    setVisibleCategories(categories);
  };

  if (isLoading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" color="brand.500" />
      </Center>
    );
  }

  if (!portfolio || portfolio.holdings_by_ticker.length === 0) {
    return (
      <Container maxW="container.lg" py={8}>
        <VStack spacing={6} align="stretch">
          <Heading size="lg">Investments</Heading>
          <Card>
            <CardBody>
              <VStack spacing={4}>
                <Text color="gray.500">No investment holdings found.</Text>
                <Text fontSize="sm" color="gray.600">
                  Add investment accounts with holdings to see your portfolio here.
                </Text>
              </VStack>
            </CardBody>
          </Card>
        </VStack>
      </Container>
    );
  }

  const totalGainIsPositive = portfolio.total_gain_loss !== null && portfolio.total_gain_loss >= 0;

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        {/* Header with Date Filter and Category Toggles */}
        <HStack justify="space-between" align="flex-start">
          <Heading size="lg">Investments</Heading>
          <HStack spacing={4}>
            {/* Date Filter Menu */}
            <Menu>
              <MenuButton
                as={Button}
                rightIcon={<FiCalendar />}
                size="sm"
                variant="outline"
              >
                {dateFilter === 'all' ? 'All Time' : dateFilter === 'today' ? 'Today' : dateFilter === 'week' ? 'This Week' : dateFilter === 'month' ? 'This Month' : dateFilter === 'year' ? 'This Year' : 'Custom'}
              </MenuButton>
              <MenuList>
                <MenuItem onClick={() => handleDateFilterChange('today')}>Today</MenuItem>
                <MenuItem onClick={() => handleDateFilterChange('week')}>This Week</MenuItem>
                <MenuItem onClick={() => handleDateFilterChange('month')}>This Month</MenuItem>
                <MenuItem onClick={() => handleDateFilterChange('year')}>This Year</MenuItem>
                <MenuItem onClick={() => handleDateFilterChange('all')}>All Time</MenuItem>
              </MenuList>
            </Menu>

            {/* Category Visibility Toggles */}
            <Box>
              <Menu closeOnSelect={false}>
                <MenuButton as={Button} size="sm" variant="outline">
                  Show/Hide Categories
                </MenuButton>
                <MenuList minWidth="200px">
                  <Box px={3} py={2}>
                    <CheckboxGroup
                      value={visibleCategories}
                      onChange={(values) => handleCategoryToggle(values as string[])}
                    >
                      <Stack spacing={2}>
                        <Checkbox value="retirement">Retirement</Checkbox>
                        <Checkbox value="taxable">Taxable</Checkbox>
                        <Checkbox value="crypto">Crypto</Checkbox>
                        <Checkbox value="property">Property</Checkbox>
                        <Checkbox value="vehicles">Vehicles</Checkbox>
                      </Stack>
                    </CheckboxGroup>
                  </Box>
                </MenuList>
              </Menu>
            </Box>
          </HStack>
        </HStack>

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
                  {visibleCategories.includes('retirement') && portfolio.category_breakdown.retirement_value > 0 && (
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
                  {visibleCategories.includes('taxable') && portfolio.category_breakdown.taxable_value > 0 && (
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

        {/* Asset Allocation Treemap */}
        {portfolio.treemap_data && (
          <Card>
            <CardBody>
              <HStack justify="space-between" mb={4}>
                <Heading size="md">Asset Allocation</Heading>
                <IconButton
                  aria-label="Toggle treemap"
                  icon={expandedSections.includes('treemap') ? <FiChevronUp /> : <FiChevronDown />}
                  size="sm"
                  variant="ghost"
                  onClick={() => toggleSection('treemap')}
                />
              </HStack>
              <Collapse in={expandedSections.includes('treemap')}>
                <AssetAllocationTreemap
                  data={portfolio.treemap_data}
                  onDrillDown={handleTreemapDrillDown}
                />
              </Collapse>
            </CardBody>
          </Card>
        )}

        {/* Holdings Table */}
        <Card>
          <CardBody>
            <HStack justify="space-between" mb={4}>
              <VStack align="flex-start" spacing={1}>
                <Heading size="md">Holdings</Heading>
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
              <Box overflowX="auto">
                <Table variant="simple" size="sm">
                  <Thead>
                    <Tr>
                      <Th>Ticker</Th>
                      <Th>Name</Th>
                      <Th isNumeric>Shares</Th>
                      <Th isNumeric>Price</Th>
                      <Th isNumeric>Current Value</Th>
                      <Th isNumeric>Cost Basis</Th>
                      <Th isNumeric>Gain/Loss</Th>
                      <Th>Type</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {portfolio.holdings_by_ticker
                      .filter((holding) => {
                        // Filter based on selected treemap node
                        if (!selectedNode) return true;

                        // If selected node is a specific ticker, match it
                        if (!selectedNode.children) {
                          return holding.ticker === selectedNode.name;
                        }

                        // If selected node is an asset type (Stocks, ETFs, etc.), match by asset type
                        if (selectedNode.name === 'Stocks') {
                          return holding.asset_type === 'stock';
                        }
                        if (selectedNode.name === 'ETFs') {
                          return holding.asset_type === 'etf';
                        }
                        if (selectedNode.name === 'Mutual Funds') {
                          return holding.asset_type === 'mutual_fund';
                        }

                        // Otherwise show all (for top-level categories like Retirement, Taxable)
                        return true;
                      })
                      .map((holding) => {
                    const gainIsPositive = holding.gain_loss !== null && holding.gain_loss >= 0;

                    return (
                      <Tr key={holding.ticker}>
                        <Td>
                          <Text fontWeight="bold">{holding.ticker}</Text>
                        </Td>
                        <Td>
                          <Text fontSize="sm" color="gray.600">
                            {holding.name || '-'}
                          </Text>
                        </Td>
                        <Td isNumeric>{formatShares(holding.total_shares)}</Td>
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
                        <Td isNumeric>
                          {holding.gain_loss !== null ? (
                            <VStack spacing={0} align="flex-end">
                              <Text
                                fontWeight="semibold"
                                color={gainIsPositive ? 'green.600' : 'red.600'}
                              >
                                {formatCurrency(holding.gain_loss)}
                              </Text>
                              {holding.gain_loss_percent !== null && (
                                <Text
                                  fontSize="xs"
                                  color={gainIsPositive ? 'green.600' : 'red.600'}
                                >
                                  {formatPercent(holding.gain_loss_percent)}
                                </Text>
                              )}
                            </VStack>
                          ) : (
                            'N/A'
                          )}
                        </Td>
                        <Td>
                          {holding.asset_type && (
                            <Badge colorScheme="blue" size="sm">
                              {holding.asset_type}
                            </Badge>
                          )}
                        </Td>
                      </Tr>
                    );
                      })}
                  </Tbody>
                </Table>
              </Box>
            </Collapse>
          </CardBody>
        </Card>
      </VStack>
    </Container>
  );
};
