/**
 * Fee Analysis Panel
 *
 * Shows fee drag projections (line chart), benchmark comparison stats,
 * per-holding breakdown with flags, high-fee holdings table,
 * low-cost alternatives, and fund overlap detection.
 */

import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Card,
  CardBody,
  Heading,
  HStack,
  SimpleGrid,
  Spinner,
  Stat,
  StatHelpText,
  StatLabel,
  StatNumber,
  Table,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tooltip as ChakraTooltip,
  Tr,
  VStack,
  useColorModeValue,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import {
  ResponsiveContainer,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Area,
  ComposedChart,
} from "recharts";
import api from "../../../services/api";
import {
  smartInsightsApi,
  type HoldingFeeDetail,
} from "../../../api/smartInsights";
import { HelpHint } from "../../../components/HelpHint";
import { helpContent } from "../../../constants/helpContent";

// ── Types ────────────────────────────────────────────────────────────────────

interface FeeDragProjection {
  years: number[];
  with_fees: number[];
  without_fees: number[];
  fee_cost: number[];
}

interface HighFeeHolding {
  ticker: string;
  name: string | null;
  expense_ratio: number;
  annual_fee: number;
  value: number;
}

interface LowCostAlternative {
  original: string;
  original_er: number;
  alternative: string;
  alternative_er: number;
  annual_savings: number;
}

interface FeeAnalysisData {
  current_portfolio_value: number;
  weighted_avg_expense_ratio: number;
  total_annual_fees: number;
  fee_drag_projection: FeeDragProjection;
  high_fee_holdings: HighFeeHolding[];
  low_cost_alternatives: LowCostAlternative[];
}

interface OverlapGroup {
  category: string;
  holdings: string[];
  total_value: number;
  suggestion: string;
}

interface FundOverlapData {
  overlaps: OverlapGroup[];
  total_overlap_value: number;
}

interface FeeAnalysisPanelProps {
  userId: string | null;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const formatCurrency = (value: number): string =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);

const formatCurrencyFull = (value: number): string =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value);

// ── Component ────────────────────────────────────────────────────────────────

const flagColors: Record<HoldingFeeDetail["flag"], string> = {
  ok: "green",
  high_cost: "orange",
  extreme_cost: "red",
  no_data: "gray",
};

const flagLabels: Record<HoldingFeeDetail["flag"], string> = {
  ok: "Low Cost",
  high_cost: "High Cost",
  extreme_cost: "Extreme Cost",
  no_data: "No Data",
};

export const FeeAnalysisPanel = ({ userId }: FeeAnalysisPanelProps) => {
  const gridColor = useColorModeValue("#e0e0e0", "#4A5568");

  // Fetch fee analysis data (projections, high-fee, alternatives, overlap)
  const {
    data: feeData,
    isLoading: feeLoading,
    error: feeError,
  } = useQuery<FeeAnalysisData>({
    queryKey: ["fee-analysis", userId],
    queryFn: async () => {
      const params = userId ? { user_id: userId } : {};
      const response = await api.get("/holdings/fee-analysis", { params });
      return response.data;
    },
  });

  // Fetch benchmark comparison + per-holding breakdown (from smart-insights)
  const { data: fundFeesData, isLoading: fundFeesLoading } = useQuery({
    queryKey: ["fund-fees", userId],
    queryFn: () =>
      smartInsightsApi.getFundFees({ user_id: userId || undefined }),
  });

  // Fetch fund overlap data
  const {
    data: overlapData,
    isLoading: overlapLoading,
    error: overlapError,
  } = useQuery<FundOverlapData>({
    queryKey: ["fund-overlap", userId],
    queryFn: async () => {
      const params = userId ? { user_id: userId } : {};
      const response = await api.get("/holdings/fund-overlap", { params });
      return response.data;
    },
  });

  // Transform projection data for Recharts
  const chartData = useMemo(() => {
    if (!feeData) return [];
    const { years, with_fees, without_fees, fee_cost } =
      feeData.fee_drag_projection;
    // Start with year 0 = current value
    const data = [
      {
        year: 0,
        withFees: feeData.current_portfolio_value,
        withoutFees: feeData.current_portfolio_value,
        feeCost: 0,
      },
    ];
    for (let i = 0; i < years.length; i++) {
      data.push({
        year: years[i],
        withFees: with_fees[i],
        withoutFees: without_fees[i],
        feeCost: fee_cost[i],
      });
    }
    return data;
  }, [feeData]);

  const isLoading = feeLoading || overlapLoading || fundFeesLoading;

  if (isLoading) {
    return (
      <VStack py={10}>
        <Spinner size="lg" color="brand.500" />
        <Text color="text.muted">Loading fee analysis...</Text>
      </VStack>
    );
  }

  if (feeError && overlapError) {
    return (
      <Alert status="error">
        <AlertIcon />
        Failed to load fee analysis data. Please try again later.
      </Alert>
    );
  }

  if (!feeData || feeData.current_portfolio_value === 0) {
    return (
      <Alert status="info">
        <AlertIcon />
        No holdings with expense ratio data available. Fee analysis requires
        holdings with known expense ratios -- metadata is enriched daily.
      </Alert>
    );
  }

  const projectionYears = feeData.fee_drag_projection.years;
  const lastIdx = projectionYears.length - 1;
  const thirtyYearCost = feeData.fee_drag_projection.fee_cost[lastIdx] || 0;

  // Custom tooltip for the fee drag chart
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <Card size="sm">
          <CardBody>
            <Text fontWeight="bold" mb={1}>
              Year {label}
            </Text>
            {payload.map((entry: any, index: number) => (
              <Text key={index} fontSize="sm" color={entry.color}>
                {entry.name}: {formatCurrency(entry.value)}
              </Text>
            ))}
          </CardBody>
        </Card>
      );
    }
    return null;
  };

  return (
    <VStack spacing={6} align="stretch">
      {/* Summary Stats */}
      <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
        <Card variant="outline">
          <CardBody py={3}>
            <Stat>
              <StatLabel fontSize="xs">
                Portfolio Value
                <HelpHint hint={helpContent.investments.feePortfolioValue} />
              </StatLabel>
              <StatNumber fontSize="lg">
                {formatCurrency(feeData.current_portfolio_value)}
              </StatNumber>
            </Stat>
          </CardBody>
        </Card>

        <Card variant="outline">
          <CardBody py={3}>
            <Stat>
              <StatLabel fontSize="xs">
                Weighted Avg ER
                <HelpHint hint={helpContent.investments.weightedAvgER} />
              </StatLabel>
              <StatNumber fontSize="lg">
                {(feeData.weighted_avg_expense_ratio * 100).toFixed(3)}%
              </StatNumber>
              <StatHelpText fontSize="xs">
                {formatCurrencyFull(feeData.total_annual_fees)}/yr in fees
              </StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card variant="outline">
          <CardBody py={3}>
            <Stat>
              <StatLabel fontSize="xs">
                30-Year Fee Cost
                <HelpHint hint={helpContent.investments.thirtyYearFeeCost} />
              </StatLabel>
              <StatNumber fontSize="lg" color="finance.negative">
                {formatCurrency(thirtyYearCost)}
              </StatNumber>
              <StatHelpText fontSize="xs">
                Lost to fees vs. fee-free growth
              </StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card variant="outline">
          <CardBody py={3}>
            <Stat>
              <StatLabel fontSize="xs">
                Fund Overlaps
                <HelpHint hint={helpContent.investments.fundOverlaps} />
              </StatLabel>
              <StatNumber
                fontSize="lg"
                color={
                  overlapData && overlapData.overlaps.length > 0
                    ? "orange.500"
                    : "finance.positive"
                }
              >
                {overlapData ? overlapData.overlaps.length : 0}
              </StatNumber>
              <StatHelpText fontSize="xs">
                {overlapData && overlapData.overlaps.length > 0
                  ? `${formatCurrency(overlapData.total_overlap_value)} in overlapping funds`
                  : "No redundant holdings detected"}
              </StatHelpText>
            </Stat>
          </CardBody>
        </Card>
      </SimpleGrid>

      {/* Fee Drag Projection Chart */}
      <Card variant="outline">
        <CardBody>
          <Heading size="sm" mb={4}>
            Fee Drag Projection (7% Annual Return)
          </Heading>
          <Box>
            <ResponsiveContainer width="100%" height={350}>
              <ComposedChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                <XAxis
                  dataKey="year"
                  label={{
                    value: "Years",
                    position: "insideBottom",
                    offset: -5,
                  }}
                />
                <YAxis
                  tickFormatter={(value) => {
                    if (value >= 1000000)
                      return `$${(value / 1000000).toFixed(1)}M`;
                    return `$${(value / 1000).toFixed(0)}k`;
                  }}
                />
                {/* eslint-disable-next-line react-hooks/static-components */}
                <Tooltip content={<CustomTooltip />} />
                <Legend />

                {/* Shaded area between the two lines to highlight the gap */}
                <Area
                  type="monotone"
                  dataKey="withoutFees"
                  stroke="transparent"
                  fill="#48BB78"
                  fillOpacity={0.08}
                  name=""
                  legendType="none"
                />

                <Line
                  type="monotone"
                  dataKey="withoutFees"
                  stroke="#48BB78"
                  strokeWidth={2.5}
                  name="Growth Without Fees"
                  dot={{ r: 4 }}
                />
                <Line
                  type="monotone"
                  dataKey="withFees"
                  stroke="#4299E1"
                  strokeWidth={2.5}
                  name="Growth With Fees"
                  dot={{ r: 4 }}
                />
                <Line
                  type="monotone"
                  dataKey="feeCost"
                  stroke="#E53E3E"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  name="Cumulative Fee Cost"
                  dot={{ r: 3 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </Box>
          <Text fontSize="xs" color="text.muted" mt={2} textAlign="center">
            Projection assumes 7% annual return with current portfolio value and
            expense ratios held constant. Not financial advice.
          </Text>
        </CardBody>
      </Card>

      {/* Benchmark Comparison (from smart-insights) */}
      {fundFeesData && fundFeesData.has_investment_holdings && (
        <>
          <SimpleGrid columns={{ base: 2, md: 2 }} spacing={4}>
            <Card variant="outline">
              <CardBody py={3}>
                <Stat>
                  <StatLabel fontSize="xs">10-yr vs Benchmark</StatLabel>
                  <StatNumber
                    fontSize="lg"
                    color={
                      fundFeesData.ten_year_impact_vs_benchmark > 0
                        ? "red.500"
                        : "green.500"
                    }
                  >
                    {fundFeesData.ten_year_impact_vs_benchmark > 0
                      ? `-${new Intl.NumberFormat("en-US", {
                          style: "currency",
                          currency: "USD",
                          maximumFractionDigits: 0,
                        }).format(fundFeesData.ten_year_impact_vs_benchmark)}`
                      : "—"}
                  </StatNumber>
                  <StatHelpText fontSize="xs">
                    vs {(fundFeesData.benchmark_expense_ratio * 100).toFixed(2)}
                    % benchmark (VTI)
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card variant="outline">
              <CardBody py={3}>
                <Stat>
                  <StatLabel fontSize="xs">20-yr vs Benchmark</StatLabel>
                  <StatNumber
                    fontSize="lg"
                    color={
                      fundFeesData.twenty_year_impact_vs_benchmark > 0
                        ? "red.500"
                        : "green.500"
                    }
                  >
                    {fundFeesData.twenty_year_impact_vs_benchmark > 0
                      ? `-${new Intl.NumberFormat("en-US", {
                          style: "currency",
                          currency: "USD",
                          maximumFractionDigits: 0,
                        }).format(
                          fundFeesData.twenty_year_impact_vs_benchmark,
                        )}`
                      : "—"}
                  </StatNumber>
                  <StatHelpText fontSize="xs">
                    compounding drag vs low-cost index
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>
          </SimpleGrid>

          {fundFeesData.high_cost_count > 0 && (
            <HStack>
              <Badge colorScheme="red" px={3} py={1} borderRadius="full">
                {fundFeesData.high_cost_count} high-cost holding
                {fundFeesData.high_cost_count > 1 ? "s" : ""} (&gt; 0.50% ER)
              </Badge>
            </HStack>
          )}

          {/* Summary text */}
          <Card variant="outline" bg="purple.50" _dark={{ bg: "purple.900" }}>
            <CardBody>
              <Text fontSize="sm">{fundFeesData.summary}</Text>
            </CardBody>
          </Card>

          {/* Per-holding breakdown */}
          <Card variant="outline">
            <CardBody>
              <Heading size="sm" mb={3}>
                Holdings Breakdown
              </Heading>
              <Box overflowX="auto">
                <Table size="sm" variant="simple">
                  <Thead>
                    <Tr>
                      <Th>Ticker / Name</Th>
                      <Th isNumeric>Market Value</Th>
                      <Th isNumeric>Expense Ratio</Th>
                      <Th isNumeric>Annual Fee</Th>
                      <Th isNumeric>10-yr Drag</Th>
                      <Th isNumeric>20-yr Drag</Th>
                      <Th>Flag</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {fundFeesData.holdings.map((h, i) => (
                      <Tr key={`${h.ticker ?? h.name ?? "unknown"}-${i}`}>
                        <Td>
                          <VStack align="start" spacing={0}>
                            <Text fontWeight="semibold" fontSize="sm">
                              {h.ticker ?? "—"}
                            </Text>
                            {h.name && (
                              <Text
                                fontSize="xs"
                                color="text.muted"
                                noOfLines={1}
                              >
                                {h.name}
                              </Text>
                            )}
                          </VStack>
                        </Td>
                        <Td isNumeric fontSize="sm">
                          {new Intl.NumberFormat("en-US", {
                            style: "currency",
                            currency: "USD",
                            maximumFractionDigits: 0,
                          }).format(h.market_value)}
                        </Td>
                        <Td isNumeric fontSize="sm">
                          {h.flag === "no_data" ? (
                            <Text color="text.muted" fontSize="xs">
                              N/A
                            </Text>
                          ) : (
                            <ChakraTooltip
                              label={
                                h.is_estimated
                                  ? "Estimated based on asset class — no manual ER entered"
                                  : undefined
                              }
                              hasArrow
                            >
                              <Text
                                color={
                                  h.is_estimated ? "text.muted" : undefined
                                }
                                cursor={h.is_estimated ? "help" : undefined}
                              >
                                {(h.expense_ratio * 100).toFixed(2)}%
                                {h.is_estimated && " ~est"}
                              </Text>
                            </ChakraTooltip>
                          )}
                        </Td>
                        <Td isNumeric fontSize="sm">
                          {h.annual_fee > 0 ? (
                            <Text
                              color={h.flag === "ok" ? undefined : "orange.500"}
                            >
                              {new Intl.NumberFormat("en-US", {
                                style: "currency",
                                currency: "USD",
                                maximumFractionDigits: 0,
                              }).format(h.annual_fee)}
                            </Text>
                          ) : (
                            <Text color="text.muted">—</Text>
                          )}
                        </Td>
                        <Td isNumeric fontSize="sm">
                          {h.ten_year_drag > 0 ? (
                            new Intl.NumberFormat("en-US", {
                              style: "currency",
                              currency: "USD",
                              maximumFractionDigits: 0,
                            }).format(h.ten_year_drag)
                          ) : (
                            <Text color="text.muted">—</Text>
                          )}
                        </Td>
                        <Td isNumeric fontSize="sm">
                          {h.twenty_year_drag > 0 ? (
                            new Intl.NumberFormat("en-US", {
                              style: "currency",
                              currency: "USD",
                              maximumFractionDigits: 0,
                            }).format(h.twenty_year_drag)
                          ) : (
                            <Text color="text.muted">—</Text>
                          )}
                        </Td>
                        <Td>
                          <ChakraTooltip
                            label={h.suggestion ?? undefined}
                            hasArrow
                          >
                            <Badge
                              colorScheme={flagColors[h.flag]}
                              size="sm"
                              cursor={h.suggestion ? "help" : "default"}
                            >
                              {flagLabels[h.flag]}
                            </Badge>
                          </ChakraTooltip>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </Box>
              <Text fontSize="xs" color="text.muted" mt={2}>
                Benchmark: VTI at 0.03% ER. Drag at 7% assumed return.{" "}
                <em>~est</em> = expense ratio estimated from asset class (no
                manual data entered).
              </Text>
            </CardBody>
          </Card>
        </>
      )}

      {/* High-Fee Holdings */}
      {feeData.high_fee_holdings.length > 0 && (
        <Card variant="outline">
          <CardBody>
            <HStack mb={3}>
              <Heading size="sm">High-Fee Holdings</Heading>
              <Badge colorScheme="red" fontSize="xs">
                ER &gt; 0.50%
              </Badge>
            </HStack>
            <Box overflowX="auto">
              <Table size="sm" variant="simple">
                <Thead>
                  <Tr>
                    <Th>Holding</Th>
                    <Th isNumeric>Value</Th>
                    <Th isNumeric>Expense Ratio</Th>
                    <Th isNumeric>Annual Fee</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {feeData.high_fee_holdings.map((h) => (
                    <Tr key={h.ticker}>
                      <Td>
                        <VStack align="flex-start" spacing={0}>
                          <Text fontWeight="medium" fontSize="sm">
                            {h.ticker}
                          </Text>
                          {h.name && (
                            <Text
                              fontSize="xs"
                              color="text.muted"
                              noOfLines={1}
                            >
                              {h.name}
                            </Text>
                          )}
                        </VStack>
                      </Td>
                      <Td isNumeric fontSize="sm">
                        {formatCurrency(h.value)}
                      </Td>
                      <Td isNumeric fontSize="sm" color="red.500">
                        {(h.expense_ratio * 100).toFixed(2)}%
                      </Td>
                      <Td isNumeric fontSize="sm" color="orange.600">
                        {formatCurrencyFull(h.annual_fee)}
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </Box>
          </CardBody>
        </Card>
      )}

      {/* Low-Cost Alternatives */}
      {feeData.low_cost_alternatives.length > 0 && (
        <Card variant="outline">
          <CardBody>
            <Heading size="sm" mb={3}>
              Low-Cost Alternatives
            </Heading>
            <Box overflowX="auto">
              <Table size="sm" variant="simple">
                <Thead>
                  <Tr>
                    <Th>Current Fund</Th>
                    <Th isNumeric>Current ER</Th>
                    <Th>Alternative</Th>
                    <Th isNumeric>Alt ER</Th>
                    <Th isNumeric>Annual Savings</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {feeData.low_cost_alternatives.map((alt) => (
                    <Tr key={alt.original}>
                      <Td fontWeight="medium" fontSize="sm">
                        {alt.original}
                      </Td>
                      <Td isNumeric fontSize="sm" color="red.500">
                        {(alt.original_er * 100).toFixed(2)}%
                      </Td>
                      <Td fontWeight="medium" fontSize="sm" color="green.600">
                        {alt.alternative}
                      </Td>
                      <Td isNumeric fontSize="sm" color="green.600">
                        {(alt.alternative_er * 100).toFixed(2)}%
                      </Td>
                      <Td
                        isNumeric
                        fontSize="sm"
                        fontWeight="bold"
                        color="blue.600"
                      >
                        {formatCurrencyFull(alt.annual_savings)}
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </Box>
            <Text fontSize="xs" color="text.muted" mt={2}>
              Alternatives are suggestions based on common index fund
              replacements. Consider tax implications before switching.
            </Text>
          </CardBody>
        </Card>
      )}

      {/* Fund Overlap Detection */}
      {overlapData && overlapData.overlaps.length > 0 && (
        <Card variant="outline">
          <CardBody>
            <HStack mb={3}>
              <Heading size="sm">Fund Overlap Detection</Heading>
              <Badge colorScheme="orange" fontSize="xs">
                {overlapData.overlaps.length} overlap
                {overlapData.overlaps.length !== 1 ? "s" : ""}
              </Badge>
            </HStack>
            <VStack spacing={3} align="stretch">
              {overlapData.overlaps.map((group) => (
                <Card key={group.category} variant="outline" size="sm">
                  <CardBody py={3}>
                    <HStack justify="space-between" mb={1}>
                      <HStack>
                        <Text fontWeight="bold" fontSize="sm">
                          {group.category}
                        </Text>
                        <Badge colorScheme="purple" fontSize="xs">
                          {group.holdings.length} funds
                        </Badge>
                      </HStack>
                      <Text fontSize="sm" fontWeight="medium">
                        {formatCurrency(group.total_value)}
                      </Text>
                    </HStack>
                    <HStack spacing={2} mb={2} flexWrap="wrap">
                      {group.holdings.map((ticker) => (
                        <Badge key={ticker} variant="subtle" colorScheme="blue">
                          {ticker}
                        </Badge>
                      ))}
                    </HStack>
                    <Text fontSize="xs" color="text.muted">
                      {group.suggestion}
                    </Text>
                  </CardBody>
                </Card>
              ))}
            </VStack>
            <Text fontSize="xs" color="text.muted" mt={3}>
              Total value in overlapping funds:{" "}
              <strong>{formatCurrency(overlapData.total_overlap_value)}</strong>
            </Text>
          </CardBody>
        </Card>
      )}

      {/* No issues message */}
      {feeData.high_fee_holdings.length === 0 &&
        feeData.low_cost_alternatives.length === 0 &&
        (!overlapData || overlapData.overlaps.length === 0) && (
          <Alert status="success">
            <AlertIcon />
            Your portfolio looks well-optimized -- no high-fee holdings,
            alternatives, or overlapping funds detected.
          </Alert>
        )}
    </VStack>
  );
};

export default FeeAnalysisPanel;
