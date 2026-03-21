/**
 * Dividend & Investment Income panel — shows income summary, monthly chart, and top payers.
 */

import {
  Box,
  Card,
  CardBody,
  Center,
  HStack,
  Heading,
  SimpleGrid,
  Spinner,
  Stat,
  StatHelpText,
  StatLabel,
  StatNumber,
  StatArrow,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Text,
  VStack,
  Badge,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import api from "../../../services/api";
import { HelpHint } from "../../../components/HelpHint";
import { helpContent } from "../../../constants/helpContent";

interface DividendByTicker {
  ticker: string;
  name: string | null;
  total_income: number;
  payment_count: number;
  avg_per_share: number | null;
  latest_ex_date: string | null;
  yield_on_cost: number | null;
}

interface DividendByMonth {
  month: string;
  total_income: number;
  dividend_count: number;
  by_type: Record<string, number>;
}

interface DividendSummary {
  total_income_ytd: number;
  total_income_trailing_12m: number;
  total_income_all_time: number;
  projected_annual_income: number;
  monthly_average: number;
  by_ticker: DividendByTicker[];
  by_month: DividendByMonth[];
  top_payers: DividendByTicker[];
  income_growth_pct: number | null;
}

const formatCurrency = (amount: number | null | undefined): string => {
  if (amount == null) return "$0.00";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(amount);
};

export const DividendIncomePanel: React.FC = () => {
  const { data: summary, isLoading } = useQuery<DividendSummary>({
    queryKey: ["dividend-summary"],
    queryFn: async () => {
      const res = await api.get("/api/v1/dividend-income/summary");
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <Center py={10}>
        <Spinner size="lg" />
      </Center>
    );
  }

  if (!summary) {
    return (
      <Center py={10}>
        <VStack spacing={3}>
          <Text fontSize="lg" color="gray.500">
            No dividend income recorded yet
          </Text>
          <Text fontSize="sm" color="gray.400">
            Dividend and interest payments will appear here as they are
            recorded.
          </Text>
        </VStack>
      </Center>
    );
  }

  // Prepare chart data (last 12 months)
  const chartData = (summary.by_month || []).slice(-12).map((m) => ({
    month: m.month.substring(5), // "MM" from "YYYY-MM"
    income: m.total_income,
    payments: m.dividend_count,
  }));

  return (
    <VStack spacing={6} align="stretch">
      {/* Summary Stats */}
      <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
        <Stat>
          <StatLabel>YTD Income</StatLabel>
          <StatNumber fontSize="xl">
            {formatCurrency(summary.total_income_ytd)}
          </StatNumber>
        </Stat>
        <Stat>
          <StatLabel>Trailing 12-Month</StatLabel>
          <StatNumber fontSize="xl">
            {formatCurrency(summary.total_income_trailing_12m)}
          </StatNumber>
          {summary.income_growth_pct != null && (
            <StatHelpText>
              <StatArrow
                type={summary.income_growth_pct >= 0 ? "increase" : "decrease"}
              />
              {Math.abs(summary.income_growth_pct).toFixed(1)}% YoY
            </StatHelpText>
          )}
        </Stat>
        <Stat>
          <StatLabel>Monthly Average</StatLabel>
          <StatNumber fontSize="xl">
            {formatCurrency(summary.monthly_average)}
          </StatNumber>
        </Stat>
        <Stat>
          <StatLabel>Projected Annual</StatLabel>
          <StatNumber fontSize="xl">
            {formatCurrency(summary.projected_annual_income)}
          </StatNumber>
        </Stat>
      </SimpleGrid>

      {/* Monthly Income Chart */}
      {chartData.length > 0 && (
        <Card variant="outline">
          <CardBody>
            <Heading size="sm" mb={4}>
              Monthly Dividend Income
            </Heading>
            <Box h="250px">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                  <Tooltip
                    formatter={(value: number) => formatCurrency(value)}
                    labelFormatter={(label: string) => `Month: ${label}`}
                  />
                  <Bar
                    dataKey="income"
                    fill="#38A169"
                    name="Dividend Income"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </Box>
          </CardBody>
        </Card>
      )}

      {/* Top Dividend Payers */}
      {summary.top_payers && summary.top_payers.length > 0 && (
        <Card variant="outline">
          <CardBody>
            <Heading size="sm" mb={4}>
              Top Dividend Payers (12-Month)
            </Heading>
            <Table size="sm">
              <Thead>
                <Tr>
                  <Th>Ticker</Th>
                  <Th>Name</Th>
                  <Th isNumeric>Total Income</Th>
                  <Th isNumeric>Payments</Th>
                  <Th isNumeric>
                    Yield on Cost
                    <HelpHint hint={helpContent.investments.yieldOnCost} />
                  </Th>
                </Tr>
              </Thead>
              <Tbody>
                {summary.top_payers.map((payer) => (
                  <Tr key={payer.ticker}>
                    <Td>
                      <Badge colorScheme="green">{payer.ticker}</Badge>
                    </Td>
                    <Td>
                      <Text fontSize="sm" noOfLines={1}>
                        {payer.name || "-"}
                      </Text>
                    </Td>
                    <Td isNumeric fontWeight="semibold">
                      {formatCurrency(payer.total_income)}
                    </Td>
                    <Td isNumeric>{payer.payment_count}</Td>
                    <Td isNumeric>
                      {payer.yield_on_cost != null
                        ? `${payer.yield_on_cost.toFixed(2)}%`
                        : "-"}
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </CardBody>
        </Card>
      )}

      {/* All-Time Total */}
      <HStack justify="flex-end">
        <Text fontSize="sm" color="gray.500">
          All-time dividend income:{" "}
          <Text as="span" fontWeight="bold">
            {formatCurrency(summary.total_income_all_time)}
          </Text>
        </Text>
      </HStack>
    </VStack>
  );
};

export default DividendIncomePanel;
