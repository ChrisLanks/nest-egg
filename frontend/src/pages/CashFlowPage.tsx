/**
 * Cash Flow — unified page combining income/expense analysis and 30/60/90-day forecast.
 *
 * Tabs:
 *   - Overview: visual breakdown of income vs. spending (formerly /income-expenses)
 *   - Forecast: 30/60/90-day projected balance based on recurring transactions (formerly /cash-flow-forecast)
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
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import api from "../services/api";
import { useUserView } from "../contexts/UserViewContext";
import { useCurrency } from "../contexts/CurrencyContext";
import { IncomeExpensesPage } from "../features/income-expenses/pages/IncomeExpensesPage";

// ─── Forecast tab ────────────────────────────────────────────────────────────

interface ForecastDataPoint {
  date: string;
  projected_balance: number;
  day_change: number;
  transaction_count: number;
}

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

const ForecastTab = () => {
  const { selectedUserId } = useUserView();
  const { formatCurrency } = useCurrency();
  const [timeRange, setTimeRange] = useState<30 | 60 | 90>(90);

  const { data: forecast, isLoading, isError } = useQuery<ForecastDataPoint[]>({
    queryKey: ["cash-flow-forecast-page", timeRange, selectedUserId],
    queryFn: async () => {
      const params: Record<string, unknown> = { days_ahead: timeRange };
      if (selectedUserId) params.user_id = selectedUserId;
      const response = await api.get<ForecastDataPoint[]>("/dashboard/forecast", { params });
      return response.data;
    },
  });

  const currentBalance = forecast?.[0]?.projected_balance ?? null;
  const lowestDay = forecast?.reduce(
    (min, d) => (d.projected_balance < min.projected_balance ? d : min),
    forecast[0],
  );
  const highestDay = forecast?.reduce(
    (max, d) => (d.projected_balance > max.projected_balance ? d : max),
    forecast[0],
  );

  const LOW_BALANCE_THRESHOLD = 500;
  const warningDays = forecast?.filter((d) => d.projected_balance < LOW_BALANCE_THRESHOLD) ?? [];
  const negativeDays = warningDays.filter((d) => d.projected_balance < 0);
  const transactionDays = forecast?.filter((d) => d.transaction_count > 0) ?? [];

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
      <Box px={6} mb={4}>
        <HStack justify="space-between" align="flex-start">
          <Text color="text.secondary" fontSize="sm">
            Projected account balance based on your recurring transactions.
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
          {negativeDays.length > 0 && (
            <Alert status="error" borderRadius="md">
              <AlertIcon />
              <Box>
                <AlertTitle>Negative balance projected</AlertTitle>
                <AlertDescription fontSize="sm">
                  Your balance is projected to go negative on{" "}
                  <strong>{formatDate(negativeDays[0].date)}</strong> (
                  {formatCurrency(negativeDays[0].projected_balance)}). Review
                  upcoming bills or add funds.
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
                  Your balance is projected below{" "}
                  {formatCurrency(LOW_BALANCE_THRESHOLD)} on{" "}
                  <strong>{formatDate(warningDays[0].date)}</strong> (
                  {formatCurrency(warningDays[0].projected_balance)}).
                </AlertDescription>
              </Box>
            </Alert>
          )}

          <SimpleGrid columns={{ base: 2, md: 3 }} spacing={4}>
            <Stat bg="bg.card" borderRadius="lg" p={4} borderWidth="1px" borderColor="border.subtle">
              <StatLabel fontSize="xs" color="text.secondary">Current Balance</StatLabel>
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
              <Text fontSize="xs" color="text.muted" mt={1}>Today's projected balance</Text>
            </Stat>
            <Stat bg="bg.card" borderRadius="lg" p={4} borderWidth="1px" borderColor="border.subtle">
              <StatLabel fontSize="xs" color="text.secondary">Lowest Projected</StatLabel>
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
              {lowestDay && (
                <Text fontSize="xs" color="text.muted" mt={1}>{formatShortDate(lowestDay.date)}</Text>
              )}
            </Stat>
            <Stat bg="bg.card" borderRadius="lg" p={4} borderWidth="1px" borderColor="border.subtle">
              <StatLabel fontSize="xs" color="text.secondary">Highest Projected</StatLabel>
              <StatNumber fontSize="xl" color="green.500">
                {highestDay ? formatCurrency(highestDay.projected_balance) : "—"}
              </StatNumber>
              {highestDay && (
                <Text fontSize="xs" color="text.muted" mt={1}>{formatShortDate(highestDay.date)}</Text>
              )}
            </Stat>
          </SimpleGrid>

          {transactionDays.length > 0 ? (
            <Box>
              <Heading size="sm" mb={3}>
                Scheduled Transactions ({transactionDays.length} days)
              </Heading>
              <Box overflowX="auto" borderWidth="1px" borderColor="border.subtle" borderRadius="lg">
                <Table size="sm">
                  <Thead bg="bg.subtle">
                    <Tr>
                      <Th>Date</Th>
                      <Th isNumeric>Transactions</Th>
                      <Th isNumeric>Day Change</Th>
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
          ) : (
            <Text fontSize="sm" color="text.secondary">
              No recurring transactions scheduled in this window.
            </Text>
          )}

          <Text fontSize="xs" color="text.muted">
            Projections are based on your recurring transactions and income. Actual
            balances may vary. The forecast covers {forecast.length} days starting today.
          </Text>
        </VStack>
      </Box>
    </Box>
  );
};

// ─── Tab indices ─────────────────────────────────────────────────────────────
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
      </Box>
      <Tabs
        index={tabIndex}
        onChange={handleTabChange}
        colorScheme="brand"
        variant="line"
        isLazy
      >
        <TabList px={6} borderBottomWidth="1px" borderColor="border.subtle">
          <Tab fontSize="sm" fontWeight="medium">Overview</Tab>
          <Tab fontSize="sm" fontWeight="medium">Forecast</Tab>
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
