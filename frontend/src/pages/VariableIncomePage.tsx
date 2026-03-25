/**
 * Variable Income Planner page.
 *
 * Helps freelancers and self-employed users smooth out income volatility,
 * set a minimum monthly floor, and stay on top of quarterly estimated taxes.
 *
 * Data source: /income-expenses/trend for the trailing 12 months.
 */

import {
  Badge,
  Box,
  Card,
  CardBody,
  CardHeader,
  Container,
  Divider,
  Heading,
  HStack,
  Icon,
  SimpleGrid,
  Skeleton,
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
  Tooltip,
  Tr,
  VStack,
} from "@chakra-ui/react";
import { FiInfo } from "react-icons/fi";
import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import api from "../services/api";
import { useUserView } from "../contexts/UserViewContext";

interface MonthlyTrend {
  month: string; // "YYYY-MM"
  income: number;
  expenses: number;
  net: number;
}

function InfoTip({ label }: { label: string }) {
  return (
    <Tooltip label={label} placement="top" hasArrow maxW="260px">
      <Box as="span" display="inline-flex" ml={1} verticalAlign="middle" cursor="help">
        <Icon as={FiInfo} boxSize={3} color="text.muted" />
      </Box>
    </Tooltip>
  );
}

function fmt(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function getQuarterlySchedule(year: number) {
  return [
    { quarter: `Q1 ${year}`, period: "Jan 1 – Mar 31", dueDate: `Apr 15, ${year}` },
    { quarter: `Q2 ${year}`, period: "Apr 1 – May 31", dueDate: `Jun 16, ${year}` },
    { quarter: `Q3 ${year}`, period: "Jun 1 – Aug 31", dueDate: `Sep 15, ${year}` },
    { quarter: `Q4 ${year}`, period: "Sep 1 – Dec 31", dueDate: `Jan 15, ${year + 1}` },
  ];
}

// Self-employment tax rate (15.3%) + approximate federal income tax rate (22%)
// Used for rough estimated-payment guidance only — not tax advice.
const SE_TAX_RATE = 0.153;
const FED_RATE_ESTIMATE = 0.22;
const COMBINED_RATE = SE_TAX_RATE + FED_RATE_ESTIMATE;

export const VariableIncomePage = () => {
  const { selectedUserId } = useUserView();
  const today = new Date();
  const currentYear = today.getFullYear();

  // Trailing 13 months so we always have a full 12 + current partial month
  const start = new Date(today.getFullYear() - 1, today.getMonth(), 1);
  const startStr = start.toISOString().slice(0, 10);
  const endStr = today.toISOString().slice(0, 10);

  const { data: trend = [], isLoading } = useQuery<MonthlyTrend[]>({
    queryKey: ["variable-income-trend", selectedUserId, startStr, endStr],
    queryFn: async () => {
      const params: Record<string, string> = { start_date: startStr, end_date: endStr };
      if (selectedUserId) params.user_id = selectedUserId;
      const res = await api.get("/income-expenses/trend", { params });
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
  });

  const stats = useMemo(() => {
    if (!trend.length) return null;

    const currentMonthKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;
    const currentMonthData = trend.find((t) => t.month === currentMonthKey);
    const thisMonthIncome = currentMonthData?.income ?? 0;
    const thisMonthSpend = currentMonthData ? Math.abs(currentMonthData.expenses) : 0;

    // Trailing 12 full months (exclude current partial month)
    const fullMonths = trend.filter((t) => t.month < currentMonthKey);
    const last12 = fullMonths.slice(-12);

    const avgMonthlyIncome =
      last12.length > 0 ? last12.reduce((s, m) => s + m.income, 0) / last12.length : 0;

    const avgMonthlySpend =
      last12.length > 0
        ? last12.reduce((s, m) => s + Math.abs(m.expenses), 0) / last12.length
        : 0;

    const lowestIncome =
      last12.length > 0 ? Math.min(...last12.map((m) => m.income)) : 0;

    const variance = thisMonthIncome - avgMonthlyIncome;

    // Safe spending floor: 80% of lowest monthly income
    const safeFloor = lowestIncome * 0.8;

    // Quarterly estimated tax: COMBINED_RATE × (annual income projection ÷ 4)
    const projectedAnnual = avgMonthlyIncome * 12;
    const quarterlyTaxEst = (projectedAnnual * COMBINED_RATE) / 4;

    return {
      thisMonthIncome,
      thisMonthSpend,
      avgMonthlyIncome,
      avgMonthlySpend,
      lowestIncome,
      variance,
      safeFloor,
      projectedAnnual,
      quarterlyTaxEst,
      monthsOfData: last12.length,
    };
  }, [trend, today]);

  const quarterlySchedule = getQuarterlySchedule(currentYear);

  const hasData = !isLoading && stats !== null && stats.monthsOfData > 0;

  return (
    <Container maxW="5xl" py={6}>
      <VStack align="start" spacing={6}>
        <Box>
          <Heading size="lg">Variable Income Planner</Heading>
          <Text color="text.secondary" mt={1}>
            Smooth out income volatility with rolling averages, set a minimum
            monthly floor, and stay on top of quarterly estimated tax payments.
          </Text>
        </Box>

        {/* Income Smoothing */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Income Smoothing
            <InfoTip label="The 12-month rolling average normalizes volatile income for consistent budgeting. The IRS safe harbor for avoiding underpayment penalties is paying 100% of prior-year tax (110% if AGI exceeded $150k) or 90% of current-year tax." />
          </Heading>
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} w="full">
            <Card variant="outline">
              <CardBody>
                <Stat>
                  <StatLabel>
                    This Month
                    <InfoTip label="Gross income recognized in the current calendar month." />
                  </StatLabel>
                  <Skeleton isLoaded={!isLoading}>
                    <StatNumber fontSize="lg">
                      {hasData ? fmt(stats!.thisMonthIncome) : "—"}
                    </StatNumber>
                  </Skeleton>
                  <StatHelpText>current month gross</StatHelpText>
                </Stat>
              </CardBody>
            </Card>
            <Card variant="outline">
              <CardBody>
                <Stat>
                  <StatLabel>
                    12-Month Rolling Avg
                    <InfoTip label="Average monthly gross income over the trailing 12 months. Use this as your budgeting baseline." />
                  </StatLabel>
                  <Skeleton isLoaded={!isLoading}>
                    <StatNumber fontSize="lg">
                      {hasData ? fmt(stats!.avgMonthlyIncome) : "—"}
                    </StatNumber>
                  </Skeleton>
                  <StatHelpText>
                    {hasData ? `based on ${stats!.monthsOfData} months` : "per month avg"}
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>
            <Card variant="outline">
              <CardBody>
                <Stat>
                  <StatLabel>
                    Variance vs Average
                    <InfoTip label="How much this month deviates from your 12-month average. Large positive swings are a good time to fund estimated taxes and savings goals." />
                  </StatLabel>
                  <Skeleton isLoaded={!isLoading}>
                    <StatNumber
                      fontSize="lg"
                      color={
                        !hasData
                          ? undefined
                          : stats!.variance >= 0
                          ? "green.500"
                          : "red.500"
                      }
                    >
                      {hasData
                        ? `${stats!.variance >= 0 ? "+" : ""}${fmt(stats!.variance)}`
                        : "—"}
                    </StatNumber>
                  </Skeleton>
                  <StatHelpText>this month vs avg</StatHelpText>
                </Stat>
              </CardBody>
            </Card>
          </SimpleGrid>
        </Box>

        <Divider />

        {/* Quarterly Tax Estimates */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Quarterly Tax Estimates
            <InfoTip label="Self-employed individuals must pay estimated taxes quarterly to avoid underpayment penalties. The safe harbor is the lesser of 90% of current-year tax or 100%/110% of prior-year tax." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}>
              <HStack justify="space-between">
                <Heading size="sm">Q1–Q4 Payment Schedule</Heading>
                {hasData && (
                  <Text fontSize="xs" color="text.secondary">
                    ~{fmt(stats!.quarterlyTaxEst)} / quarter estimated (
                    {Math.round(COMBINED_RATE * 100)}% combined rate)
                  </Text>
                )}
              </HStack>
            </CardHeader>
            <CardBody overflowX="auto">
              <Table size="sm">
                <Thead>
                  <Tr>
                    <Th>Quarter</Th>
                    <Th>Income Period</Th>
                    <Th>Due Date</Th>
                    <Th isNumeric>Est. Payment</Th>
                    <Th>Status</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {quarterlySchedule.map((q) => {
                    const due = new Date(q.dueDate);
                    const isPast = due < today;
                    const isCurrent =
                      !isPast && due.getTime() - today.getTime() < 60 * 24 * 60 * 60 * 1000;
                    return (
                      <Tr key={q.quarter}>
                        <Td fontWeight="medium">{q.quarter}</Td>
                        <Td color="text.secondary">{q.period}</Td>
                        <Td>{q.dueDate}</Td>
                        <Td isNumeric>
                          <Skeleton isLoaded={!isLoading} display="inline-block">
                            {hasData ? fmt(stats!.quarterlyTaxEst) : "—"}
                          </Skeleton>
                        </Td>
                        <Td>
                          <Badge
                            colorScheme={isPast ? "gray" : isCurrent ? "orange" : "blue"}
                          >
                            {isPast ? "past" : isCurrent ? "due soon" : "upcoming"}
                          </Badge>
                        </Td>
                      </Tr>
                    );
                  })}
                </Tbody>
              </Table>
              <Text fontSize="xs" color="text.secondary" mt={3}>
                Estimates assume {Math.round(SE_TAX_RATE * 100)}% self-employment tax +{" "}
                {Math.round(FED_RATE_ESTIMATE * 100)}% federal income tax applied to your
                projected annual income of{" "}
                {hasData ? fmt(stats!.projectedAnnual) : "—"}. Not tax advice — consult a
                CPA for your actual liability.
              </Text>
            </CardBody>
          </Card>
        </Box>

        <Divider />

        {/* Minimum Budget Floor */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Minimum Budget Floor
            <InfoTip label="Your safe spending floor is based on the lowest-income month in the trailing 12 months. Keeping monthly spending at or below this floor ensures you can cover expenses even in a dry month." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}>
              <Heading size="sm">Safe Spending Floor</Heading>
            </CardHeader>
            <CardBody>
              <VStack align="start" spacing={3} fontSize="sm">
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">
                    Lowest Monthly Income (trailing 12 mo)
                    <InfoTip label="The minimum monthly income in the past year. Used as the conservative baseline for setting your spending floor." />
                  </Text>
                  <Skeleton isLoaded={!isLoading} display="inline-block">
                    <Text fontWeight="semibold">
                      {hasData ? fmt(stats!.lowestIncome) : "—"}
                    </Text>
                  </Skeleton>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">
                    Recommended Monthly Spending Cap
                    <InfoTip label="80% of your lowest monthly income, leaving a 20% buffer for taxes and savings even in your worst month." />
                  </Text>
                  <Skeleton isLoaded={!isLoading} display="inline-block">
                    <Text fontWeight="semibold" color="green.500">
                      {hasData ? fmt(stats!.safeFloor) : "—"}
                    </Text>
                  </Skeleton>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">Your Average Monthly Spend</Text>
                  <Skeleton isLoaded={!isLoading} display="inline-block">
                    <Text
                      fontWeight="semibold"
                      color={
                        hasData && stats!.avgMonthlySpend > stats!.safeFloor
                          ? "red.500"
                          : undefined
                      }
                    >
                      {hasData ? fmt(stats!.avgMonthlySpend) : "—"}
                    </Text>
                  </Skeleton>
                </HStack>
                {hasData && stats!.avgMonthlySpend > stats!.safeFloor && (
                  <Text fontSize="xs" color="red.500">
                    Your average spending exceeds your safe floor by{" "}
                    {fmt(stats!.avgMonthlySpend - stats!.safeFloor)}/mo. Consider reducing
                    discretionary spend or building a larger buffer.
                  </Text>
                )}
                {hasData && stats!.avgMonthlySpend <= stats!.safeFloor && (
                  <Text fontSize="xs" color="green.600">
                    Your average spending is within your safe floor.
                  </Text>
                )}
                {!hasData && !isLoading && (
                  <Text fontSize="xs" color="text.secondary">
                    No transaction data found for the trailing 12 months.
                  </Text>
                )}
              </VStack>
            </CardBody>
          </Card>
        </Box>
      </VStack>
    </Container>
  );
};

export default VariableIncomePage;
