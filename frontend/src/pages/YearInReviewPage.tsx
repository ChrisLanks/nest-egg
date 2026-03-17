/**
 * Year-in-Review page — comprehensive annual financial summary
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
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Spinner,
  Center,
  Select,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Progress,
  Alert,
  AlertIcon,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useState, useMemo, useEffect } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import api from "../services/api";
import { useUserView } from "../contexts/UserViewContext";

interface YearInReviewData {
  year: number;
  income: {
    total: number;
    avg_monthly: number;
    best_month: string | null;
    best_amount: number;
  };
  expenses: {
    total: number;
    avg_monthly: number;
    biggest_month: string | null;
    biggest_amount: number;
  };
  net_income: number;
  savings_rate: number | null;
  net_worth: {
    start: number | null;
    end: number | null;
    change: number | null;
    change_pct: number | null;
  };
  top_expense_categories: {
    category: string;
    total: number;
    pct_of_total: number;
  }[];
  top_merchants: {
    merchant: string;
    total: number;
    count: number;
  }[];
  milestones: string[];
  yoy_comparison: {
    income_change_pct: number | null;
    expense_change_pct: number | null;
    savings_rate_change: number | null;
  };
}

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

const CHART_COLORS = [
  "#3182CE",
  "#38A169",
  "#D69E2E",
  "#E53E3E",
  "#805AD5",
  "#DD6B20",
  "#319795",
  "#D53F8C",
  "#718096",
  "#2B6CB0",
];

export function YearInReviewPage() {
  const {
    selectedUserId,
    isCombinedView,
    memberEffectiveUserId,
    selectedMemberIdsKey,
  } = useUserView();
  const multiEffectiveUserId = memberEffectiveUserId;
  const selectedIdsKey = selectedMemberIdsKey;
  const activeUserId = isCombinedView
    ? (multiEffectiveUserId ?? null)
    : selectedUserId;

  // Default to previous year if we are in January, otherwise current year
  const currentDate = new Date();
  const defaultYear =
    currentDate.getMonth() === 0
      ? currentDate.getFullYear() - 1
      : currentDate.getFullYear();
  const [selectedYear, setSelectedYear] = useState(() => {
    try {
      const saved = localStorage.getItem("nest-egg-year-in-review-year");
      if (saved) return parseInt(saved, 10);
    } catch {
      /* ignore */
    }
    return defaultYear;
  });

  // Persist year selection
  useEffect(() => {
    localStorage.setItem("nest-egg-year-in-review-year", String(selectedYear));
  }, [selectedYear]);

  // Fetch available years from transaction data
  const { data: apiYears } = useQuery<number[]>({
    queryKey: ["available-years", activeUserId, selectedIdsKey],
    queryFn: async () => {
      const params: Record<string, unknown> = {};
      if (activeUserId) params.user_id = activeUserId;
      const response = await api.get("/income-expenses/available-years", {
        params,
      });
      return response.data;
    },
  });

  const availableYears = useMemo(() => {
    if (apiYears && apiYears.length > 0) return apiYears;
    const years = [];
    for (let i = 0; i < 6; i++) {
      years.push(currentDate.getFullYear() - i);
    }
    return years;
  }, [apiYears, currentDate]);

  const {
    data: reviewData,
    isLoading,
    isError,
  } = useQuery<YearInReviewData>({
    queryKey: ["year-in-review", selectedYear, activeUserId, selectedIdsKey],
    queryFn: async () => {
      const params: Record<string, unknown> = { year: selectedYear };
      if (activeUserId) params.user_id = activeUserId;
      const response = await api.get("/dashboard/year-in-review", { params });
      return response.data;
    },
  });

  if (isLoading) {
    return (
      <Container maxW="container.xl" py={8}>
        <Center py={20}>
          <Spinner size="xl" color="brand.500" />
        </Center>
      </Container>
    );
  }

  if (isError || !reviewData) {
    return (
      <Container maxW="container.xl" py={8}>
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          Failed to load year-in-review data. Please try again.
        </Alert>
      </Container>
    );
  }

  const {
    income,
    expenses,
    net_worth,
    top_expense_categories,
    top_merchants,
    milestones,
    yoy_comparison,
  } = reviewData;

  // Prepare category chart data
  const categoryChartData = top_expense_categories.map((cat) => ({
    name: cat.category,
    amount: cat.total,
    pct: cat.pct_of_total,
  }));

  // Find the max category total for the progress bars
  const maxCategoryTotal =
    top_expense_categories.length > 0
      ? Math.max(...top_expense_categories.map((c) => c.total))
      : 1;

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={8} align="stretch">
        {/* Header */}
        <HStack justify="space-between" align="center">
          <Box>
            <Heading size="lg">{selectedYear} Year in Review</Heading>
            <Text color="text.secondary">
              Your complete financial summary for {selectedYear}
            </Text>
          </Box>
          <Select
            value={selectedYear}
            onChange={(e) => setSelectedYear(Number(e.target.value))}
            w="140px"
          >
            {availableYears.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </Select>
        </HStack>

        {/* Milestones */}
        {milestones.length > 0 && (
          <Card bg="bg.success" borderWidth={1} borderColor="green.200">
            <CardBody>
              <VStack align="start" spacing={2}>
                <Text fontWeight="bold" fontSize="md" color="text.heading">
                  Milestones Achieved
                </Text>
                <HStack spacing={3} flexWrap="wrap">
                  {milestones.map((milestone, idx) => (
                    <Badge
                      key={idx}
                      colorScheme="green"
                      fontSize="sm"
                      px={3}
                      py={1}
                      borderRadius="full"
                    >
                      {milestone}
                    </Badge>
                  ))}
                </HStack>
              </VStack>
            </CardBody>
          </Card>
        )}

        {/* Top-level stat cards */}
        <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4}>
          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Total Income</StatLabel>
                <StatNumber color="finance.positive">
                  {formatCurrency(income.total)}
                </StatNumber>
                <StatHelpText>
                  {formatCurrency(income.avg_monthly)}/mo avg
                </StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Total Expenses</StatLabel>
                <StatNumber color="finance.negative">
                  {formatCurrency(expenses.total)}
                </StatNumber>
                <StatHelpText>
                  {formatCurrency(expenses.avg_monthly)}/mo avg
                </StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Net Saved</StatLabel>
                <StatNumber
                  color={
                    reviewData.net_income >= 0
                      ? "finance.positive"
                      : "finance.negative"
                  }
                >
                  {formatCurrency(reviewData.net_income)}
                </StatNumber>
                <StatHelpText>
                  {income.best_month
                    ? `Best month: ${income.best_month}`
                    : "No income data"}
                </StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Savings Rate</StatLabel>
                <StatNumber>
                  {reviewData.savings_rate !== null
                    ? `${reviewData.savings_rate.toFixed(1)}%`
                    : "N/A"}
                </StatNumber>
                <StatHelpText>
                  {expenses.biggest_month
                    ? `Biggest spend: ${expenses.biggest_month}`
                    : "No expense data"}
                </StatHelpText>
              </Stat>
            </CardBody>
          </Card>
        </SimpleGrid>

        {/* Net Worth and YoY Comparison row */}
        <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
          {/* Net Worth Change */}
          <Card>
            <CardBody>
              <VStack align="stretch" spacing={4}>
                <Heading size="sm">Net Worth Change</Heading>
                {net_worth.start !== null && net_worth.end !== null ? (
                  <>
                    <SimpleGrid columns={3} spacing={4}>
                      <Box>
                        <Text fontSize="sm" color="text.secondary">
                          Start of Year
                        </Text>
                        <Text fontSize="lg" fontWeight="bold">
                          {formatCurrency(net_worth.start)}
                        </Text>
                      </Box>
                      <Box>
                        <Text fontSize="sm" color="text.secondary">
                          End of Year
                        </Text>
                        <Text fontSize="lg" fontWeight="bold">
                          {formatCurrency(net_worth.end)}
                        </Text>
                      </Box>
                      <Box>
                        <Text fontSize="sm" color="text.secondary">
                          Change
                        </Text>
                        <Text
                          fontSize="lg"
                          fontWeight="bold"
                          color={
                            (net_worth.change ?? 0) >= 0
                              ? "finance.positive"
                              : "finance.negative"
                          }
                        >
                          {net_worth.change !== null
                            ? formatCurrency(net_worth.change)
                            : "N/A"}
                        </Text>
                        {net_worth.change_pct !== null && (
                          <Text
                            fontSize="sm"
                            color={
                              net_worth.change_pct >= 0
                                ? "finance.positive"
                                : "finance.negative"
                            }
                          >
                            {net_worth.change_pct >= 0 ? "+" : ""}
                            {net_worth.change_pct.toFixed(1)}%
                          </Text>
                        )}
                      </Box>
                    </SimpleGrid>
                    {/* Simple visual bar */}
                    <Box>
                      <HStack justify="space-between" mb={1}>
                        <Text fontSize="xs" color="text.muted">
                          Jan 1
                        </Text>
                        <Text fontSize="xs" color="text.muted">
                          Dec 31
                        </Text>
                      </HStack>
                      <Progress
                        value={
                          net_worth.start > 0
                            ? Math.min(
                                (net_worth.end / net_worth.start) * 50,
                                100,
                              )
                            : 50
                        }
                        colorScheme={
                          (net_worth.change ?? 0) >= 0 ? "green" : "red"
                        }
                        borderRadius="full"
                        size="lg"
                      />
                    </Box>
                  </>
                ) : (
                  <Text color="text.secondary" fontSize="sm">
                    No net worth snapshot data available for {selectedYear}.
                  </Text>
                )}
              </VStack>
            </CardBody>
          </Card>

          {/* Year-over-Year Comparison */}
          <Card>
            <CardBody>
              <VStack align="stretch" spacing={4}>
                <Heading size="sm">
                  Year-over-Year vs {selectedYear - 1}
                </Heading>
                <SimpleGrid columns={3} spacing={4}>
                  <Box>
                    <Text fontSize="sm" color="text.secondary">
                      Income Change
                    </Text>
                    {yoy_comparison.income_change_pct !== null ? (
                      <Stat size="sm">
                        <StatNumber fontSize="lg">
                          {yoy_comparison.income_change_pct >= 0 ? "+" : ""}
                          {yoy_comparison.income_change_pct.toFixed(1)}%
                        </StatNumber>
                        <StatHelpText>
                          <StatArrow
                            type={
                              yoy_comparison.income_change_pct >= 0
                                ? "increase"
                                : "decrease"
                            }
                          />
                          vs prior year
                        </StatHelpText>
                      </Stat>
                    ) : (
                      <Text fontSize="sm" color="text.muted">
                        N/A
                      </Text>
                    )}
                  </Box>
                  <Box>
                    <Text fontSize="sm" color="text.secondary">
                      Expense Change
                    </Text>
                    {yoy_comparison.expense_change_pct !== null ? (
                      <Stat size="sm">
                        <StatNumber fontSize="lg">
                          {yoy_comparison.expense_change_pct >= 0 ? "+" : ""}
                          {yoy_comparison.expense_change_pct.toFixed(1)}%
                        </StatNumber>
                        <StatHelpText>
                          <StatArrow
                            type={
                              yoy_comparison.expense_change_pct >= 0
                                ? "increase"
                                : "decrease"
                            }
                          />
                          vs prior year
                        </StatHelpText>
                      </Stat>
                    ) : (
                      <Text fontSize="sm" color="text.muted">
                        N/A
                      </Text>
                    )}
                  </Box>
                  <Box>
                    <Text fontSize="sm" color="text.secondary">
                      Savings Rate
                    </Text>
                    {yoy_comparison.savings_rate_change !== null ? (
                      <Stat size="sm">
                        <StatNumber fontSize="lg">
                          {yoy_comparison.savings_rate_change >= 0 ? "+" : ""}
                          {yoy_comparison.savings_rate_change.toFixed(1)}pp
                        </StatNumber>
                        <StatHelpText>
                          <StatArrow
                            type={
                              yoy_comparison.savings_rate_change >= 0
                                ? "increase"
                                : "decrease"
                            }
                          />
                          vs prior year
                        </StatHelpText>
                      </Stat>
                    ) : (
                      <Text fontSize="sm" color="text.muted">
                        N/A
                      </Text>
                    )}
                  </Box>
                </SimpleGrid>
              </VStack>
            </CardBody>
          </Card>
        </SimpleGrid>

        {/* Top Expense Categories */}
        <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
          {/* Chart */}
          <Card>
            <CardBody>
              <VStack align="stretch" spacing={4}>
                <Heading size="sm">Top Expense Categories</Heading>
                {categoryChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={350}>
                    <BarChart
                      data={categoryChartData}
                      layout="vertical"
                      margin={{ left: 20, right: 20 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        type="number"
                        tickFormatter={(v) => formatCurrency(v)}
                      />
                      <YAxis
                        type="category"
                        dataKey="name"
                        width={120}
                        tick={{ fontSize: 12 }}
                      />
                      <Tooltip
                        formatter={(value: number) => [
                          formatCurrency(value),
                          "Amount",
                        ]}
                      />
                      <Bar dataKey="amount" barSize={20}>
                        {categoryChartData.map((_entry, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={CHART_COLORS[index % CHART_COLORS.length]}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <Text color="text.secondary" fontSize="sm">
                    No expense category data for {selectedYear}.
                  </Text>
                )}
              </VStack>
            </CardBody>
          </Card>

          {/* Category breakdown list */}
          <Card>
            <CardBody>
              <VStack align="stretch" spacing={3}>
                <Heading size="sm">Category Breakdown</Heading>
                {top_expense_categories.map((cat, idx) => (
                  <Box key={cat.category}>
                    <HStack justify="space-between" mb={1}>
                      <HStack spacing={2}>
                        <Box
                          w={3}
                          h={3}
                          borderRadius="sm"
                          bg={CHART_COLORS[idx % CHART_COLORS.length]}
                        />
                        <Text fontSize="sm" fontWeight="medium">
                          {cat.category}
                        </Text>
                      </HStack>
                      <HStack spacing={3}>
                        <Text fontSize="sm" fontWeight="semibold">
                          {formatCurrency(cat.total)}
                        </Text>
                        <Badge colorScheme="gray" fontSize="xs">
                          {cat.pct_of_total.toFixed(1)}%
                        </Badge>
                      </HStack>
                    </HStack>
                    <Progress
                      value={(cat.total / maxCategoryTotal) * 100}
                      size="xs"
                      colorScheme="blue"
                      borderRadius="full"
                    />
                  </Box>
                ))}
                {top_expense_categories.length === 0 && (
                  <Text color="text.secondary" fontSize="sm">
                    No data available.
                  </Text>
                )}
              </VStack>
            </CardBody>
          </Card>
        </SimpleGrid>

        {/* Top Merchants */}
        <Card>
          <CardBody>
            <VStack align="stretch" spacing={4}>
              <Heading size="sm">Top Merchants</Heading>
              {top_merchants.length > 0 ? (
                <Box overflowX="auto">
                  <Table variant="simple" size="sm">
                    <Thead>
                      <Tr>
                        <Th>#</Th>
                        <Th>Merchant</Th>
                        <Th isNumeric>Total Spent</Th>
                        <Th isNumeric>Transactions</Th>
                        <Th isNumeric>Avg per Transaction</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {top_merchants.map((m, idx) => (
                        <Tr key={m.merchant}>
                          <Td>{idx + 1}</Td>
                          <Td fontWeight="medium">{m.merchant}</Td>
                          <Td isNumeric fontWeight="semibold">
                            {formatCurrency(m.total)}
                          </Td>
                          <Td isNumeric>{m.count}</Td>
                          <Td isNumeric>{formatCurrency(m.total / m.count)}</Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </Box>
              ) : (
                <Text color="text.secondary" fontSize="sm">
                  No merchant data for {selectedYear}.
                </Text>
              )}
            </VStack>
          </CardBody>
        </Card>
      </VStack>
    </Container>
  );
}

export default YearInReviewPage;
