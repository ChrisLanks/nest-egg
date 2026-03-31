/**
 * Net Worth Attribution Widget — last 6 months breakdown of what drove net worth change.
 * Shows stacked contribution bars for savings, investment contributions, debt paydown.
 */

import {
  Badge,
  Box,
  Card,
  CardBody,
  Heading,
  HStack,
  Link,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { memo } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useUserView } from "../../../contexts/UserViewContext";
import api from "../../../services/api";

interface AttributionMonth {
  month: number;
  year: number;
  period_label: string;
  savings: number;
  investment_contributions: number;
  debt_paydown: number;
  attribution_note?: string;
}

const fmtSigned = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
    signDisplay: "exceptZero",
  }).format(n);

function totalChange(m: AttributionMonth): number {
  return m.savings + m.investment_contributions + m.debt_paydown;
}

/** Render a single proportional bar segment */
function BarSegment({
  value,
  total,
  color,
}: {
  value: number;
  total: number;
  color: string;
}) {
  if (total === 0 || value <= 0) return null;
  const pct = Math.min((value / total) * 100, 100);
  return (
    <div
      style={{
        width: `${pct}%`,
        height: "12px",
        background: color,
        borderRadius: "2px",
        transition: "width 0.3s",
        minWidth: value > 0 ? "4px" : "0",
      }}
    />
  );
}

const NetWorthAttributionWidgetBase: React.FC = () => {
  const { selectedUserId } = useUserView();

  const { data, isLoading } = useQuery<AttributionMonth[]>({
    queryKey: ["net-worth-attribution-widget", selectedUserId],
    queryFn: async () => {
      const params: Record<string, string> = { months: "6" };
      if (selectedUserId) params.user_id = selectedUserId;
      const res = await api.get("/net-worth-attribution/history", { params });
      return res.data;
    },
    staleTime: 15 * 60 * 1000,
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

  const months = data ?? [];
  const noData =
    months.length === 0 ||
    months.every(
      (m) =>
        m.savings === 0 &&
        m.investment_contributions === 0 &&
        m.debt_paydown === 0
    );

  if (noData) {
    return (
      <Card h="100%">
        <CardBody>
          <HStack justify="space-between" mb={4}>
            <Heading size="md">What Built Your Wealth?</Heading>
            <Link
              as={RouterLink}
              to="/net-worth-timeline"
              fontSize="sm"
              color="brand.500"
            >
              View timeline →
            </Link>
          </HStack>
          <Text color="text.muted" fontSize="sm">
            No net worth history yet. Add accounts and transactions to see
            attribution.
          </Text>
        </CardBody>
      </Card>
    );
  }

  // Most recent month is last in the array
  const latest = months[months.length - 1];
  const latestTotal =
    latest.savings + latest.investment_contributions + latest.debt_paydown;
  const recentRows = months.slice(-4, -1); // 3 months before the latest

  const barTotal = Math.max(
    latest.savings + latest.investment_contributions + latest.debt_paydown,
    0.01
  );

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">What Built Your Wealth?</Heading>
          <Link
            as={RouterLink}
            to="/net-worth-timeline"
            fontSize="sm"
            color="brand.500"
          >
            View timeline →
          </Link>
        </HStack>
        <Text fontSize="xs" color="text.secondary" mb={4}>
          Last 6 months — where net worth changes came from
        </Text>

        <VStack align="stretch" spacing={4}>
          {/* Most recent month — stacked bar breakdown */}
          <Box>
            <Text fontSize="sm" fontWeight="semibold" mb={2}>
              {latest.period_label}
            </Text>

            {/* Stacked bar */}
            {latestTotal > 0 && (
              <HStack spacing={0} h="12px" mb={3} borderRadius="2px" overflow="hidden">
                <BarSegment
                  value={latest.savings}
                  total={barTotal}
                  color="#38B2AC"
                />
                <BarSegment
                  value={latest.investment_contributions}
                  total={barTotal}
                  color="#4299E1"
                />
                <BarSegment
                  value={latest.debt_paydown}
                  total={barTotal}
                  color="#ED8936"
                />
              </HStack>
            )}

            {/* Legend rows */}
            <VStack align="stretch" spacing={1}>
              {latest.savings !== 0 && (
                <HStack justify="space-between">
                  <HStack spacing={2}>
                    <Box w="10px" h="10px" borderRadius="2px" bg="teal.400" flexShrink={0} />
                    <Text fontSize="xs" color="text.secondary">
                      Savings
                    </Text>
                  </HStack>
                  <Text
                    fontSize="xs"
                    fontWeight="bold"
                    color={latest.savings >= 0 ? "green.500" : "red.500"}
                  >
                    {fmtSigned(latest.savings)}
                  </Text>
                </HStack>
              )}
              {latest.investment_contributions !== 0 && (
                <HStack justify="space-between">
                  <HStack spacing={2}>
                    <Box w="10px" h="10px" borderRadius="2px" bg="blue.400" flexShrink={0} />
                    <Text fontSize="xs" color="text.secondary">
                      Investments
                    </Text>
                  </HStack>
                  <Text
                    fontSize="xs"
                    fontWeight="bold"
                    color="blue.500"
                  >
                    {fmtSigned(latest.investment_contributions)}
                  </Text>
                </HStack>
              )}
              {latest.debt_paydown !== 0 && (
                <HStack justify="space-between">
                  <HStack spacing={2}>
                    <Box w="10px" h="10px" borderRadius="2px" bg="orange.400" flexShrink={0} />
                    <Text fontSize="xs" color="text.secondary">
                      Debt Paydown
                    </Text>
                  </HStack>
                  <Text
                    fontSize="xs"
                    fontWeight="bold"
                    color="orange.500"
                  >
                    {fmtSigned(latest.debt_paydown)}
                  </Text>
                </HStack>
              )}
            </VStack>
          </Box>

          {/* Prior 3 months as compact rows */}
          {recentRows.length > 0 && (
            <VStack align="stretch" spacing={1}>
              {recentRows.map((m) => {
                const total = totalChange(m);
                const isPos = total >= 0;
                return (
                  <HStack key={`${m.year}-${m.month}`} justify="space-between">
                    <Text fontSize="xs" color="text.muted">
                      {m.period_label}
                    </Text>
                    <Badge
                      colorScheme={isPos ? "green" : "red"}
                      fontSize="2xs"
                    >
                      {fmtSigned(total)}
                    </Badge>
                  </HStack>
                );
              })}
            </VStack>
          )}
        </VStack>
      </CardBody>
    </Card>
  );
};

export const NetWorthAttributionWidget = memo(NetWorthAttributionWidgetBase);
