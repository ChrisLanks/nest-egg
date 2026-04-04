/**
 * Portfolio fee analysis widget — shows expense ratios and annual fee drag.
 */

import {
  Badge,
  Box,
  Card,
  CardBody,
  Divider,
  Heading,
  HStack,
  Link,
  SimpleGrid,
  Spinner,
  Stat,
  StatLabel,
  StatNumber,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { memo } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useUserView } from "../../../contexts/UserViewContext";
import api from "../../../services/api";

interface HighFeeHolding {
  ticker: string;
  name: string | null;
  expense_ratio: number;
  annual_fee: number;
  value: number;
}

interface FeeAnalysisData {
  current_portfolio_value: number;
  weighted_avg_expense_ratio: number;
  total_annual_fees: number;
  high_fee_holdings: HighFeeHolding[];
  low_cost_alternatives: {
    original: string;
    original_er: number;
    alternative: string;
    alternative_er: number;
    annual_savings: number;
  }[];
}

const fmt = (n: number): string =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);

const fmtPct = (n: number): string => `${(n * 100).toFixed(2)}%`;

const FeeAnalysisWidgetBase: React.FC = () => {
  const { selectedUserId, effectiveUserId } = useUserView();

  const { data, isLoading, isError } = useQuery<FeeAnalysisData>({
    queryKey: ["fee-analysis-widget", effectiveUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: effectiveUserId } : {};
      const res = await api.get("/holdings/fee-analysis", { params });
      return res.data;
    },
    retry: false,
    staleTime: 10 * 60 * 1000,
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

  if (isError || !data || data.current_portfolio_value === 0) {
    return (
      <Card h="100%">
        <CardBody>
          <Heading size="md" mb={4}>
            Fee Analysis
          </Heading>
          <Text color="text.muted" fontSize="sm">
            No investment holdings to analyze. Link a brokerage account to see
            fee insights.
          </Text>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Fee Analysis</Heading>
          <Link as={RouterLink} to="/holdings" fontSize="sm" color="brand.500">
            View portfolio →
          </Link>
        </HStack>

        <SimpleGrid columns={3} spacing={3} mb={4}>
          <Stat size="sm">
            <StatLabel>Avg Expense Ratio</StatLabel>
            <StatNumber fontSize="lg">
              {fmtPct(data.weighted_avg_expense_ratio)}
            </StatNumber>
          </Stat>
          <Stat size="sm">
            <StatLabel>Annual Fees</StatLabel>
            <StatNumber fontSize="lg" color="finance.negative">
              {fmt(data.total_annual_fees)}
            </StatNumber>
          </Stat>
          <Stat size="sm">
            <StatLabel>Portfolio Value</StatLabel>
            <StatNumber fontSize="lg">
              {fmt(data.current_portfolio_value)}
            </StatNumber>
          </Stat>
        </SimpleGrid>

        {data.high_fee_holdings.length > 0 && (
          <VStack align="stretch" spacing={1}>
            <Text fontSize="xs" fontWeight="semibold" color="text.secondary">
              Highest Fee Holdings
            </Text>
            {data.high_fee_holdings.slice(0, 4).map((h, idx) => (
              <Box key={h.ticker}>
                <HStack justify="space-between" py={1}>
                  <Text fontSize="sm" fontWeight="medium">
                    {h.ticker}
                  </Text>
                  <HStack spacing={2}>
                    <Badge colorScheme="red" fontSize="2xs">
                      {fmtPct(h.expense_ratio)}
                    </Badge>
                    <Text fontSize="sm" color="finance.negative">
                      {fmt(h.annual_fee)}/yr
                    </Text>
                  </HStack>
                </HStack>
                {idx < data.high_fee_holdings.slice(0, 4).length - 1 && (
                  <Divider />
                )}
              </Box>
            ))}
          </VStack>
        )}
      </CardBody>
    </Card>
  );
};

export const FeeAnalysisWidget = memo(FeeAnalysisWidgetBase);
