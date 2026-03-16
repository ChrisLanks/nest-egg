/**
 * Compact dividend income summary widget for the dashboard.
 */

import {
  Card,
  CardBody,
  Heading,
  HStack,
  Link,
  SimpleGrid,
  Spinner,
  Stat,
  StatArrow,
  StatHelpText,
  StatLabel,
  StatNumber,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { Link as RouterLink } from "react-router-dom";
import api from "../../../services/api";

interface DividendSummaryData {
  total_income_ytd: number;
  total_income_trailing_12m: number;
  projected_annual_income: number;
  monthly_average: number;
  income_growth_pct: number | null;
  top_payers: { ticker: string; total_income: number }[];
}

const fmt = (n: number | null | undefined): string => {
  if (n == null) return "$0";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);
};

export const DividendIncomeWidget: React.FC = () => {
  const { data, isLoading, isError } = useQuery<DividendSummaryData>({
    queryKey: ["dividend-summary-widget"],
    queryFn: async () => {
      const res = await api.get("/api/v1/dividend-income/summary");
      return res.data;
    },
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <Card h="100%">
        <CardBody display="flex" alignItems="center" justifyContent="center">
          <Spinner />
        </CardBody>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card h="100%">
        <CardBody>
          <Heading size="md" mb={4}>
            Dividend Income
          </Heading>
          <Text color="text.muted" fontSize="sm">
            No dividend income recorded yet. Track dividends from the
            Investments page.
          </Text>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Dividend Income</Heading>
          <Link
            as={RouterLink}
            to="/investments"
            fontSize="sm"
            color="brand.500"
          >
            View details →
          </Link>
        </HStack>

        <SimpleGrid columns={2} spacing={3} mb={4}>
          <Stat size="sm">
            <StatLabel>YTD</StatLabel>
            <StatNumber fontSize="lg">{fmt(data.total_income_ytd)}</StatNumber>
          </Stat>
          <Stat size="sm">
            <StatLabel>Trailing 12M</StatLabel>
            <StatNumber fontSize="lg">
              {fmt(data.total_income_trailing_12m)}
            </StatNumber>
            {data.income_growth_pct != null && (
              <StatHelpText>
                <StatArrow
                  type={data.income_growth_pct >= 0 ? "increase" : "decrease"}
                />
                {Math.abs(data.income_growth_pct).toFixed(1)}% YoY
              </StatHelpText>
            )}
          </Stat>
          <Stat size="sm">
            <StatLabel>Monthly Avg</StatLabel>
            <StatNumber fontSize="lg">{fmt(data.monthly_average)}</StatNumber>
          </Stat>
          <Stat size="sm">
            <StatLabel>Projected Annual</StatLabel>
            <StatNumber fontSize="lg" color="green.500">
              {fmt(data.projected_annual_income)}
            </StatNumber>
          </Stat>
        </SimpleGrid>

        {data.top_payers && data.top_payers.length > 0 && (
          <VStack align="stretch" spacing={1}>
            <Text fontSize="xs" fontWeight="semibold" color="text.secondary">
              Top Payers
            </Text>
            {data.top_payers.slice(0, 3).map((p) => (
              <HStack key={p.ticker} justify="space-between">
                <Text fontSize="sm" fontWeight="medium">
                  {p.ticker}
                </Text>
                <Text fontSize="sm" color="green.500">
                  {fmt(p.total_income)}
                </Text>
              </HStack>
            ))}
          </VStack>
        )}
      </CardBody>
    </Card>
  );
};
