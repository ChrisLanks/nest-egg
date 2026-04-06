/**
 * Cash Flow — unified page combining income/expense analysis and 30/60/90-day forecast.
 *
 * Tabs:
 *   - Overview: visual breakdown of income vs. spending (formerly /income-expenses)
 *   - Forecast: balance trajectory + income/expense charts + breakdown by category/label/merchant/account
 */

import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Badge,
  Box,
  Button,
  ButtonGroup,
  Center,
  Heading,
  HStack,
  SimpleGrid,
  Spinner,
  Stat,
  StatHelpText,
  StatLabel,
  StatNumber,
  Tab,
  Table,
  TabList,
  TabPanel,
  TabPanels,
  Tabs,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
  VStack,
  useColorModeValue,
  Tooltip as ChakraTooltip,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import api from "../services/api";
import { useUserView } from "../contexts/UserViewContext";
import { useCurrency } from "../contexts/CurrencyContext";
import { IncomeExpensesPage } from "../features/income-expenses/pages/IncomeExpensesPage";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ForecastTransaction {
  merchant: string | null;
  amount: number;
  category: string | null;
  label: string | null;
  account_id: string | null;
  account_name: string | null;
  event_type: string;
}

interface ForecastDataPoint {
  date: string;
  projected_balance: number;
  day_change: number;
  transaction_count: number;
  income: number;
  expenses: number;
  transactions: ForecastTransaction[];
}

interface ForecastBreakdownItem {
  name: string;
  amount: number;
}

interface ForecastSummary {
  total_income: number;
  total_expenses: number;
  net: number;
  by_category: ForecastBreakdownItem[];
  by_merchant: ForecastBreakdownItem[];
  by_label: ForecastBreakdownItem[];
  by_account: ForecastBreakdownItem[];
  by_member: ForecastBreakdownItem[];
}

type GroupBy = "category" | "merchant" | "label" | "account" | "member";

// ─── Helpers ─────────────────────────────────────────────────────────────────

const formatDate = (dateStr: string) => {
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

const formatShortDate = (dateStr: string) => {
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
};

// Thin the x-axis labels so they don't overlap
const tickInterval = (days: number) => (days <= 30 ? 4 : days <= 60 ? 9 : 14);

// ─── Breakdown Table ──────────────────────────────────────────────────────────

const BreakdownTable = ({
  items,
  formatCurrency,
}: {
  items: ForecastBreakdownItem[];
  formatCurrency: (n: number) => string;
}) => {
  if (items.length === 0) {
    return (
      <Text fontSize="sm" color="text.secondary">
        No data for this period.
      </Text>
    );
  }
  const maxAbs = Math.max(...items.map((i) => Math.abs(i.amount)));

  return (
    <Box overflowX="auto" borderWidth="1px" borderColor="border.subtle" borderRadius="lg">
      <Table size="sm">
        <Thead bg="bg.subtle">
          <Tr>
            <Th>Name</Th>
            <Th isNumeric>Amount</Th>
            <Th w="40%">Share</Th>
          </Tr>
        </Thead>
        <Tbody>
          {items.map((item) => {
            const pct = maxAbs > 0 ? (Math.abs(item.amount) / maxAbs) * 100 : 0;
            const isIncome = item.amount > 0;
            return (
              <Tr key={item.name}>
                <Td fontSize="sm" maxW="200px" overflow="hidden" textOverflow="ellipsis" whiteSpace="nowrap">
                  {item.name}
                </Td>
                <Td isNumeric>
                  <Badge colorScheme={isIncome ? "green" : "red"} fontSize="xs">
                    {isIncome ? "+" : ""}
                    {formatCurrency(item.amount)}
                  </Badge>
                </Td>
                <Td>
                  <Box
                    h="6px"
                    w={`${pct}%`}
                    minW="2px"
                    bg={isIncome ? "green.400" : "red.400"}
                    borderRadius="full"
                  />
                </Td>
              </Tr>
            );
          })}
        </Tbody>
      </Table>
    </Box>
  );
};

// ─── Forecast Tab ─────────────────────────────────────────────────────────────

const ForecastTab = () => {
  const { selectedUserId, effectiveUserId } = useUserView();
  const { formatCurrency } = useCurrency();
  const [timeRange, setTimeRange] = useState<30 | 60 | 90>(90);
  const [groupBy, setGroupBy] = useState<GroupBy>("category");

  const tooltipBg = useColorModeValue("#fff", "#2D3748");
  const tooltipBorder = useColorModeValue("#E2E8F0", "#4A5568");

  // Full daily forecast (balance trajectory + per-day income/expenses)
  const { data: forecast, isLoading, isError } = useQuery<ForecastDataPoint[]>({
    queryKey: ["cash-flow-forecast-page", timeRange, effectiveUserId],
    queryFn: async () => {
      const params: Record<string, unknown> = { days_ahead: timeRange };
      if (selectedUserId) params.user_id = effectiveUserId;
      const response = await api.get<ForecastDataPoint[]>("/dashboard/forecast", { params });
      return response.data;
    },
  });

  // Summary totals + breakdowns
  const { data: summary, isLoading: summaryLoading } = useQuery<ForecastSummary>({
    queryKey: ["cash-flow-forecast-summary", timeRange, effectiveUserId],
    queryFn: async () => {
      const params: Record<string, unknown> = { days_ahead: timeRange };
      if (selectedUserId) params.user_id = effectiveUserId;
      const response = await api.get<ForecastSummary>("/dashboard/forecast/summary", { params });
      return response.data;
    },
    enabled: !!forecast && forecast.length > 0,
  });

  // Fetch planning defaults so low-balance threshold isn't hardcoded in the UI
  const { data: planningDefaults } = useQuery<{ low_balance_warning_usd: number }>({
    queryKey: ["financial-defaults"],
    queryFn: async () => {
      const response = await api.get("/settings/financial-defaults");
      return response.data;
    },
    staleTime: Infinity,
  });

  // Derived values
  const currentBalance = forecast?.[0]?.projected_balance ?? null;
  const lowestDay = forecast?.reduce(
    (min, d) => (d.projected_balance < min.projected_balance ? d : min),
    forecast[0],
  );
  const highestDay = forecast?.reduce(
    (max, d) => (d.projected_balance > max.projected_balance ? d : max),
    forecast[0],
  );

  const LOW_BALANCE_THRESHOLD = planningDefaults?.low_balance_warning_usd ?? 500;
  const warningDays = forecast?.filter((d) => d.projected_balance < LOW_BALANCE_THRESHOLD) ?? [];
  const negativeDays = warningDays.filter((d) => d.projected_balance < 0);
  const transactionDays = forecast?.filter((d) => d.transaction_count > 0) ?? [];

  // Chart data — thin to every N days for readability
  const interval = tickInterval(timeRange);
  const balanceChartData = forecast?.filter((_, i) => i % interval === 0 || i === (forecast.length - 1)).map((d) => ({
    date: formatShortDate(d.date),
    balance: d.projected_balance,
  })) ?? [];

  // Income/expense bar chart: aggregate by week
  const incExpChartData = (() => {
    if (!forecast) return [];
    const weeks: Record<string, { week: string; income: number; expenses: number }> = {};
    forecast.forEach((d) => {
      const [y, m, day] = d.date.split("-").map(Number);
      const dt = new Date(y, m - 1, day);
      const weekStart = new Date(dt);
      weekStart.setDate(dt.getDate() - dt.getDay()); // Sunday
      const key = weekStart.toISOString().split("T")[0];
      if (!weeks[key]) {
        weeks[key] = {
          week: weekStart.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
          income: 0,
          expenses: 0,
        };
      }
      weeks[key].income += d.income;
      weeks[key].expenses += Math.abs(d.expenses);
    });
    return Object.values(weeks);
  })();

  const breakdownItems: ForecastBreakdownItem[] = summary
    ? (summary[`by_${groupBy}` as keyof ForecastSummary] as ForecastBreakdownItem[])
    : [];

  if (isLoading) {
    return (
      <Center py={16}>
        <Spinner size="lg" color="brand.500" />
      </Center>
    );
  }

  if (isError) {
    return (
      <Box pt={4} px={6}>
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          <Text>Unable to load cash flow forecast. Please try again.</Text>
        </Alert>
      </Box>
    );
  }

  if (!forecast || forecast.length === 0) {
    return (
      <Box pt={4} px={6}>
        <Alert status="info" borderRadius="md">
          <AlertIcon />
          <Box>
            <AlertTitle>No recurring transactions found</AlertTitle>
            <AlertDescription>
              Add recurring bills or income in{" "}
              <Text as="span" color="brand.500" fontWeight="medium">
                Recurring &amp; Bills
              </Text>{" "}
              to see a projected balance forecast.
            </AlertDescription>
          </Box>
        </Alert>
      </Box>
    );
  }

  return (
    <Box pt={4}>
      {/* Time range + group by controls */}
      <Box px={6} mb={4}>
        <HStack justify="space-between" align="center" flexWrap="wrap" gap={3}>
          <Text color="text.secondary" fontSize="sm">
            Projected balance and cash flow based on your recurring transactions.
          </Text>
          <ButtonGroup size="sm" isAttached variant="outline">
            {([30, 60, 90] as const).map((days) => (
              <Button
                key={days}
                onClick={() => setTimeRange(days)}
                colorScheme={timeRange === days ? "brand" : "gray"}
                variant={timeRange === days ? "solid" : "outline"}
              >
                {days}d
              </Button>
            ))}
          </ButtonGroup>
        </HStack>
      </Box>

      <Box px={6}>
        <VStack spacing={6} align="stretch">
          {/* Alerts */}
          {negativeDays.length > 0 && (
            <Alert status="error" borderRadius="md">
              <AlertIcon />
              <Box>
                <AlertTitle>Negative balance projected</AlertTitle>
                <AlertDescription fontSize="sm">
                  Your balance is projected to go negative on{" "}
                  <strong>{formatDate(negativeDays[0].date)}</strong> (
                  {formatCurrency(negativeDays[0].projected_balance)}). Review upcoming bills or
                  add funds.
                </AlertDescription>
              </Box>
            </Alert>
          )}
          {negativeDays.length === 0 && warningDays.length > 0 && (
            <Alert status="warning" borderRadius="md">
              <AlertIcon />
              <Box>
                <AlertTitle>Low balance ahead</AlertTitle>
                <AlertDescription fontSize="sm">
                  Your balance is projected below {formatCurrency(LOW_BALANCE_THRESHOLD)} on{" "}
                  <strong>{formatDate(warningDays[0].date)}</strong> (
                  {formatCurrency(warningDays[0].projected_balance)}).
                </AlertDescription>
              </Box>
            </Alert>
          )}

          {/* Summary stat cards */}
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
            <Stat bg="bg.card" borderRadius="lg" p={4} borderWidth="1px" borderColor="border.subtle">
              <ChakraTooltip label="Today's estimated balance based on your connected accounts and recurring transactions" hasArrow placement="top"><StatLabel fontSize="xs" color="text.secondary" cursor="help">Current Balance</StatLabel></ChakraTooltip>
              <StatNumber
                fontSize="xl"
                color={
                  (currentBalance ?? 0) < 0
                    ? "red.500"
                    : (currentBalance ?? 0) < LOW_BALANCE_THRESHOLD
                    ? "orange.500"
                    : "text.primary"
                }
              >
                {currentBalance !== null ? formatCurrency(currentBalance) : "—"}
              </StatNumber>
              <StatHelpText fontSize="xs">Today's projected</StatHelpText>
            </Stat>
            <Stat bg="bg.card" borderRadius="lg" p={4} borderWidth="1px" borderColor="border.subtle">
              <ChakraTooltip label="The lowest your balance is expected to drop during this period — if this is near zero, consider building a buffer" hasArrow placement="top"><StatLabel fontSize="xs" color="text.secondary" cursor="help">Lowest Projected</StatLabel></ChakraTooltip>
              <StatNumber
                fontSize="xl"
                color={
                  (lowestDay?.projected_balance ?? 0) < 0
                    ? "red.500"
                    : (lowestDay?.projected_balance ?? 0) < LOW_BALANCE_THRESHOLD
                    ? "orange.500"
                    : "green.500"
                }
              >
                {lowestDay ? formatCurrency(lowestDay.projected_balance) : "—"}
              </StatNumber>
              {lowestDay && <StatHelpText fontSize="xs">{formatShortDate(lowestDay.date)}</StatHelpText>}
            </Stat>
            <Stat bg="bg.card" borderRadius="lg" p={4} borderWidth="1px" borderColor="border.subtle">
              <StatLabel fontSize="xs" color="text.secondary">Total Income</StatLabel>
              <StatNumber fontSize="xl" color="green.500">
                {summary ? formatCurrency(summary.total_income) : "—"}
              </StatNumber>
              <StatHelpText fontSize="xs">Next {timeRange} days</StatHelpText>
            </Stat>
            <Stat bg="bg.card" borderRadius="lg" p={4} borderWidth="1px" borderColor="border.subtle">
              <StatLabel fontSize="xs" color="text.secondary">Total Expenses</StatLabel>
              <StatNumber fontSize="xl" color="red.500">
                {summary ? formatCurrency(summary.total_expenses) : "—"}
              </StatNumber>
              <StatHelpText fontSize="xs">Next {timeRange} days</StatHelpText>
            </Stat>
          </SimpleGrid>

          {/* Balance trajectory chart */}
          <Box bg="bg.card" borderRadius="lg" p={4} borderWidth="1px" borderColor="border.subtle">
            <Heading size="sm" mb={4}>Projected Balance</Heading>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={balanceChartData} margin={{ top: 4, right: 8, left: 8, bottom: 0 }}>
                <defs>
                  <linearGradient id="balanceGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#4F46E5" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--chakra-colors-border-subtle)" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) => formatCurrency(v)}
                  width={80}
                />
                <Tooltip
                  contentStyle={{
                    background: tooltipBg,
                    border: `1px solid ${tooltipBorder}`,
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                  formatter={(value: number) => [formatCurrency(value), "Projected Balance"]}
                />
                <Area
                  type="monotone"
                  dataKey="balance"
                  stroke="#4F46E5"
                  strokeWidth={2}
                  fill="url(#balanceGradient)"
                  dot={false}
                  activeDot={{ r: 4, strokeWidth: 0 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </Box>

          {/* Income vs Expenses bar chart */}
          <Box bg="bg.card" borderRadius="lg" p={4} borderWidth="1px" borderColor="border.subtle">
            <Heading size="sm" mb={4}>Income vs. Expenses by Week</Heading>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={incExpChartData} margin={{ top: 4, right: 8, left: 8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--chakra-colors-border-subtle)" />
                <XAxis dataKey="week" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                <YAxis
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) => formatCurrency(v)}
                  width={80}
                />
                <Tooltip
                  contentStyle={{
                    background: tooltipBg,
                    border: `1px solid ${tooltipBorder}`,
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                  formatter={(value: number, name: string) => [
                    formatCurrency(value),
                    name === "income" ? "Income" : "Expenses",
                  ]}
                />
                <Legend formatter={(v) => (v === "income" ? "Income" : "Expenses")} />
                <Bar dataKey="income" fill="#38A169" radius={[3, 3, 0, 0]} />
                <Bar dataKey="expenses" fill="#E53E3E" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Box>

          {/* Breakdown section */}
          <Box bg="bg.card" borderRadius="lg" p={4} borderWidth="1px" borderColor="border.subtle">
            <HStack justify="space-between" mb={4} flexWrap="wrap" gap={2}>
              <Heading size="sm">Breakdown</Heading>
              <ButtonGroup size="xs" isAttached variant="outline">
                {(["category", "merchant", "label", "account", "member"] as GroupBy[]).map((g) => (
                  <Button
                    key={g}
                    onClick={() => setGroupBy(g)}
                    colorScheme={groupBy === g ? "brand" : "gray"}
                    variant={groupBy === g ? "solid" : "outline"}
                    textTransform="capitalize"
                  >
                    {g}
                  </Button>
                ))}
              </ButtonGroup>
            </HStack>
            {summaryLoading ? (
              <Center py={6}>
                <Spinner size="sm" color="brand.500" />
              </Center>
            ) : (
              <BreakdownTable items={breakdownItems} formatCurrency={formatCurrency} />
            )}
          </Box>

          {/* Scheduled transactions table */}
          {transactionDays.length > 0 && (
            <Box>
              <Heading size="sm" mb={3}>
                Scheduled Transaction Days ({transactionDays.length})
              </Heading>
              <Box overflowX="auto" borderWidth="1px" borderColor="border.subtle" borderRadius="lg">
                <Table size="sm">
                  <Thead bg="bg.subtle">
                    <Tr>
                      <Th>Date</Th>
                      <Th isNumeric>Txns</Th>
                      <Th isNumeric>Income</Th>
                      <Th isNumeric>Expenses</Th>
                      <Th isNumeric>Net</Th>
                      <Th isNumeric>Projected Balance</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {transactionDays.map((day) => (
                      <Tr
                        key={day.date}
                        bg={
                          day.projected_balance < 0
                            ? "red.50"
                            : day.projected_balance < LOW_BALANCE_THRESHOLD
                            ? "orange.50"
                            : undefined
                        }
                        _dark={{
                          bg:
                            day.projected_balance < 0
                              ? "red.900"
                              : day.projected_balance < LOW_BALANCE_THRESHOLD
                              ? "orange.900"
                              : undefined,
                        }}
                      >
                        <Td fontSize="sm">{formatDate(day.date)}</Td>
                        <Td isNumeric>
                          <Badge colorScheme="gray" fontSize="xs">{day.transaction_count}</Badge>
                        </Td>
                        <Td isNumeric>
                          <Badge colorScheme="green" fontSize="xs">
                            {day.income > 0 ? `+${formatCurrency(day.income)}` : "—"}
                          </Badge>
                        </Td>
                        <Td isNumeric>
                          <Badge colorScheme="red" fontSize="xs">
                            {day.expenses < 0 ? formatCurrency(day.expenses) : "—"}
                          </Badge>
                        </Td>
                        <Td isNumeric>
                          <Badge
                            colorScheme={day.day_change >= 0 ? "green" : "red"}
                            fontSize="xs"
                          >
                            {day.day_change >= 0 ? "+" : ""}
                            {formatCurrency(day.day_change)}
                          </Badge>
                        </Td>
                        <Td
                          isNumeric
                          fontSize="sm"
                          fontWeight="medium"
                          color={
                            day.projected_balance < 0
                              ? "red.500"
                              : day.projected_balance < LOW_BALANCE_THRESHOLD
                              ? "orange.500"
                              : "text.primary"
                          }
                        >
                          {formatCurrency(day.projected_balance)}
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </Box>
            </Box>
          )}

          <Text fontSize="xs" color="text.muted">
            Projections are based on your recurring transactions and income. Actual balances may
            vary. The forecast covers {forecast.length} days starting today.
          </Text>
        </VStack>
      </Box>
    </Box>
  );
};

// ─── Tab indices ──────────────────────────────────────────────────────────────

const TAB_OVERVIEW = 0;
const TAB_FORECAST = 1;

const TAB_PARAM_MAP: Record<string, number> = {
  overview: TAB_OVERVIEW,
  forecast: TAB_FORECAST,
};

const TAB_NAME_MAP: Record<number, string> = {
  [TAB_OVERVIEW]: "overview",
  [TAB_FORECAST]: "forecast",
};

// ─── Main page ────────────────────────────────────────────────────────────────

export const CashFlowPage = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab") ?? "overview";
  const tabIndex = TAB_PARAM_MAP[tabParam] ?? TAB_OVERVIEW;

  const handleTabChange = (index: number) => {
    setSearchParams({ tab: TAB_NAME_MAP[index] ?? "overview" }, { replace: true });
  };

  return (
    <Box pt={4}>
      <Box px={6} mb={2}>
        <Heading size="lg">Cash Flow</Heading>
        <Text color="text.secondary" mt={1} fontSize="sm">
          Money in vs. money out — see what you earned, what you spent, and where your balance is headed over the next 90 days.
        </Text>
      </Box>
      <Tabs
        index={tabIndex}
        onChange={handleTabChange}
        colorScheme="brand"
        variant="line"
        isLazy
      >
        <TabList px={6} borderBottomWidth="1px" borderColor="border.subtle">
          <ChakraTooltip label="Income vs. spending breakdown — see your total money in vs. money out by week or month" hasArrow placement="bottom" openDelay={300}>
            <Tab fontSize="sm" fontWeight="medium">Overview</Tab>
          </ChakraTooltip>
          <ChakraTooltip label="30/60/90-day balance projection — see where your checking account balance is headed based on recent trends" hasArrow placement="bottom" openDelay={300}>
            <Tab fontSize="sm" fontWeight="medium">Forecast</Tab>
          </ChakraTooltip>
        </TabList>
        <TabPanels>
          <TabPanel p={0}>
            <IncomeExpensesPage embedded />
          </TabPanel>
          <TabPanel p={0}>
            <ForecastTab />
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Box>
  );
};
