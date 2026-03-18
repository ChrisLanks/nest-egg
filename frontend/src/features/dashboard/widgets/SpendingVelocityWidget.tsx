/**
 * Spending velocity widget — shows MoM spending trend with direction indicator.
 */

import { memo } from "react";
import {
  Badge,
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
import { useUserView } from "../../../contexts/UserViewContext";
import api from "../../../services/api";

interface MonthlyEntry {
  month: string;
  total_spending: number;
  transaction_count: number;
  mom_change_pct: number | null;
}

interface SpendingVelocityData {
  monthly_data: MonthlyEntry[];
  trend_direction: "accelerating" | "decelerating" | "stable";
  avg_monthly_spending: number;
  months_analyzed: number;
}

const fmt = (n: number): string =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);

const trendColor = (dir: string): string => {
  if (dir === "decelerating") return "green";
  if (dir === "accelerating") return "red";
  return "gray";
};

const trendLabel = (dir: string): string => {
  if (dir === "decelerating") return "Slowing down";
  if (dir === "accelerating") return "Speeding up";
  return "Stable";
};

const SpendingVelocityWidgetBase: React.FC = () => {
  const { selectedUserId } = useUserView();

  const { data, isLoading, isError } = useQuery<SpendingVelocityData>({
    queryKey: ["spending-velocity-widget", selectedUserId],
    queryFn: async () => {
      const params: Record<string, string> = { months: "6" };
      if (selectedUserId) params.user_id = selectedUserId;
      const res = await api.get("/trends/spending-velocity", {
        params,
      });
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

  if (isError || !data || data.monthly_data.length < 2) {
    return (
      <Card h="100%">
        <CardBody>
          <Heading size="md" mb={4}>
            Spending Velocity
          </Heading>
          <Text color="text.muted" fontSize="sm">
            Not enough data yet. At least 2 months of transactions are needed.
          </Text>
        </CardBody>
      </Card>
    );
  }

  const latest = data.monthly_data[data.monthly_data.length - 1];

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Spending Velocity</Heading>
          <Badge colorScheme={trendColor(data.trend_direction)} fontSize="xs">
            {trendLabel(data.trend_direction)}
          </Badge>
        </HStack>

        <SimpleGrid columns={2} spacing={3} mb={4}>
          <Stat size="sm">
            <StatLabel>This Month</StatLabel>
            <StatNumber fontSize="lg">{fmt(latest.total_spending)}</StatNumber>
            {latest.mom_change_pct != null && (
              <StatHelpText>
                <StatArrow
                  type={latest.mom_change_pct <= 0 ? "decrease" : "increase"}
                />
                {Math.abs(latest.mom_change_pct).toFixed(1)}% MoM
              </StatHelpText>
            )}
          </Stat>
          <Stat size="sm">
            <StatLabel>Monthly Avg</StatLabel>
            <StatNumber fontSize="lg">
              {fmt(data.avg_monthly_spending)}
            </StatNumber>
            <StatHelpText>{data.months_analyzed} months</StatHelpText>
          </Stat>
        </SimpleGrid>

        {/* Last 4 months mini trend */}
        <VStack align="stretch" spacing={1}>
          <Text fontSize="xs" fontWeight="semibold" color="text.secondary">
            Recent Months
          </Text>
          {data.monthly_data.slice(-4).map((m) => (
            <HStack key={m.month} justify="space-between">
              <Text fontSize="sm" color="text.muted">
                {m.month}
              </Text>
              <HStack spacing={2}>
                <Text fontSize="sm" fontWeight="medium">
                  {fmt(m.total_spending)}
                </Text>
                {m.mom_change_pct != null && (
                  <Text
                    fontSize="xs"
                    color={m.mom_change_pct <= 0 ? "green.500" : "red.500"}
                  >
                    {m.mom_change_pct > 0 ? "+" : ""}
                    {m.mom_change_pct.toFixed(1)}%
                  </Text>
                )}
              </HStack>
            </HStack>
          ))}
        </VStack>

        <Link
          as={RouterLink}
          to="/cash-flow"
          fontSize="xs"
          color="brand.500"
          mt={3}
          display="block"
        >
          View full analysis →
        </Link>
      </CardBody>
    </Card>
  );
};

export const SpendingVelocityWidget = memo(SpendingVelocityWidgetBase);
