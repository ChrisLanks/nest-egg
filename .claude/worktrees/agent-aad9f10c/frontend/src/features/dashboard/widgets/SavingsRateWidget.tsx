/**
 * Savings Rate Widget — monthly savings rate trend with sparkline.
 * Shows current month rate, trailing 12-month weighted average, and trend.
 */

import {
  Badge,
  Card,
  CardBody,
  Heading,
  HStack,
  Link,
  Spinner,
  Stat,
  StatHelpText,
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

interface MonthlySavingsRate {
  month: string;
  income: number;
  expenses: number;
  savings: number;
  savings_rate: number;
}

interface SavingsRateData {
  current_month_rate: number | null;
  trailing_3m_rate: number | null;
  trailing_12m_rate: number | null;
  monthly_trend: MonthlySavingsRate[];
  avg_monthly_savings: number;
  best_month: string | null;
  worst_month: string | null;
}

const fmtPct = (r: number) => `${(r * 100).toFixed(1)}%`;
const fmtCurrency = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);

function rateColor(rate: number | null): string {
  if (rate === null) return "text.secondary";
  if (rate >= 0.2) return "green.500";
  if (rate >= 0.1) return "yellow.500";
  return "red.500";
}

const SavingsRateWidgetBase: React.FC = () => {
  const { selectedUserId } = useUserView();

  const { data, isLoading } = useQuery<SavingsRateData>({
    queryKey: ["savings-rate-widget", selectedUserId],
    queryFn: async () => {
      const params: Record<string, string> = { months: "12" };
      if (selectedUserId) params.user_id = selectedUserId;
      const res = await api.get("/financial-planning/savings-rate", { params });
      return res.data;
    },
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

  const trend = data?.monthly_trend ?? [];
  const noData = trend.length === 0;

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Savings Rate</Heading>
          <Link
            as={RouterLink}
            to="/income-expenses"
            fontSize="sm"
            color="brand.500"
          >
            View cash flow →
          </Link>
        </HStack>

        {noData ? (
          <Text color="text.muted" fontSize="sm">
            No transaction data yet. Import transactions to see your savings
            rate.
          </Text>
        ) : (
          <VStack align="stretch" spacing={4}>
            <HStack spacing={6}>
              <Stat size="sm">
                <StatLabel>This Month</StatLabel>
                <StatNumber
                  fontSize="2xl"
                  color={rateColor(data?.current_month_rate ?? null)}
                >
                  {data?.current_month_rate != null
                    ? fmtPct(data.current_month_rate)
                    : "—"}
                </StatNumber>
                <StatHelpText mb={0}>of income saved</StatHelpText>
              </Stat>
              <Stat size="sm">
                <StatLabel>Trailing 12m</StatLabel>
                <StatNumber
                  fontSize="2xl"
                  color={rateColor(data?.trailing_12m_rate ?? null)}
                >
                  {data?.trailing_12m_rate != null
                    ? fmtPct(data.trailing_12m_rate)
                    : "—"}
                </StatNumber>
                <StatHelpText mb={0}>weighted avg</StatHelpText>
              </Stat>
            </HStack>

            {data?.avg_monthly_savings != null &&
              data.avg_monthly_savings !== 0 && (
                <HStack justify="space-between">
                  <Text fontSize="xs" color="text.secondary">
                    Avg monthly savings
                  </Text>
                  <Text
                    fontSize="xs"
                    fontWeight="bold"
                    color={
                      data.avg_monthly_savings >= 0 ? "green.500" : "red.500"
                    }
                  >
                    {fmtCurrency(data.avg_monthly_savings)}
                  </Text>
                </HStack>
              )}

            {/* Mini bar chart — last 6 months */}
            <VStack align="stretch" spacing={1}>
              {trend.slice(-6).map((m) => {
                const pct = Math.min(Math.abs(m.savings_rate) * 100, 100);
                const isNeg = m.savings_rate < 0;
                return (
                  <HStack key={m.month} spacing={2} align="center">
                    <Text
                      fontSize="2xs"
                      color="text.muted"
                      w="40px"
                      flexShrink={0}
                    >
                      {m.month.slice(5)}
                    </Text>
                    <HStack flex={1} spacing={0} h="8px" position="relative">
                      <div
                        style={{
                          width: `${pct}%`,
                          height: "8px",
                          borderRadius: "2px",
                          background: isNeg ? "#FC8181" : "#68D391",
                          transition: "width 0.3s",
                        }}
                      />
                    </HStack>
                    <Badge
                      colorScheme={isNeg ? "red" : "green"}
                      fontSize="2xs"
                      w="38px"
                      textAlign="right"
                    >
                      {fmtPct(m.savings_rate)}
                    </Badge>
                  </HStack>
                );
              })}
            </VStack>
          </VStack>
        )}
      </CardBody>
    </Card>
  );
};

export const SavingsRateWidget = memo(SavingsRateWidgetBase);
