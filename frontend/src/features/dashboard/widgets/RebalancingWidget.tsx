/**
 * Rebalancing Widget — shows portfolio drift vs target allocation.
 * Links to /investments for full rebalancing tools.
 */

import {
  Badge,
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

interface DriftItem {
  asset_class: string;
  label: string;
  target_percent: number;
  current_percent: number;
  current_value: number;
  drift_percent: number;
  drift_value: number;
  status: "overweight" | "underweight" | "on_target";
}

interface TradeRecommendation {
  asset_class: string;
  label: string;
  action: "BUY" | "SELL";
  amount: number;
  current_value: number;
  target_value: number;
  current_percent: number;
  target_percent: number;
}

interface RebalancingAnalysis {
  target_allocation_id: string;
  target_allocation_name: string;
  portfolio_total: number;
  drift_items: DriftItem[];
  needs_rebalancing: boolean;
  max_drift_percent: number;
  trade_recommendations: TradeRecommendation[];
}

const fmtCurrency = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);

const fmtPct = (n: number) => `${Number(n).toFixed(1)}%`;

const RebalancingWidgetBase: React.FC = () => {
  const { selectedUserId, effectiveUserId } = useUserView();

  const { data, isLoading, error } = useQuery<RebalancingAnalysis>({
    queryKey: ["rebalancing-widget", effectiveUserId],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (selectedUserId) params.user_id = effectiveUserId;
      const res = await api.get("/rebalancing/analysis", { params });
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
    retry: (failureCount, err: unknown) => {
      // Do not retry on 404 — no target allocation set
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 404) return false;
      return failureCount < 2;
    },
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

  // 404 or no active allocation
  const is404 =
    !data &&
    (error as { response?: { status?: number } } | null)?.response?.status === 404;

  const noAllocation = is404 || !data;

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Portfolio Rebalancing</Heading>
          <Link
            as={RouterLink}
            to="/investments"
            fontSize="sm"
            color="brand.500"
          >
            View investments →
          </Link>
        </HStack>

        {noAllocation ? (
          <Text color="text.muted" fontSize="sm">
            Set a target allocation in the{" "}
            <Link as={RouterLink} to="/investments" color="brand.500">
              Investments tab
            </Link>{" "}
            to track portfolio drift.
          </Text>
        ) : data.needs_rebalancing === false ? (
          <VStack align="stretch" spacing={2}>
            <HStack>
              <Badge colorScheme="green" fontSize="sm" px={2} py={1}>
                ✓ Portfolio is balanced
              </Badge>
            </HStack>
            <Text fontSize="xs" color="text.secondary">
              Max drift: {fmtPct(data.max_drift_percent)}
            </Text>
          </VStack>
        ) : (
          <VStack align="stretch" spacing={4}>
            <HStack>
              <Badge colorScheme="orange" fontSize="sm" px={2} py={1}>
                Rebalancing Needed
              </Badge>
            </HStack>

            {/* Top 3 drifting items */}
            <VStack align="stretch" spacing={2}>
              {data.drift_items
                .filter((d) => d.status !== "on_target")
                .slice(0, 3)
                .map((d) => (
                  <HStack key={d.asset_class} justify="space-between">
                    <VStack align="start" spacing={0}>
                      <Text fontSize="xs" fontWeight="semibold">
                        {d.label}
                      </Text>
                      <Text fontSize="2xs" color="text.secondary">
                        {fmtPct(d.current_percent)} vs {fmtPct(d.target_percent)} target
                      </Text>
                    </VStack>
                    <Badge
                      colorScheme={d.status === "overweight" ? "red" : "blue"}
                      fontSize="2xs"
                    >
                      {d.status === "overweight" ? "Overweight" : "Underweight"}
                    </Badge>
                  </HStack>
                ))}
            </VStack>

            {/* Top 2 trade recommendations */}
            {data.trade_recommendations.length > 0 && (
              <VStack align="stretch" spacing={1}>
                {data.trade_recommendations.slice(0, 2).map((t) => (
                  <HStack key={t.asset_class} justify="space-between">
                    <Text fontSize="xs" color="text.secondary">
                      {t.action === "BUY" ? "BUY" : "SELL"} {fmtCurrency(t.amount)} of{" "}
                      {t.label}
                    </Text>
                    <Badge
                      colorScheme={t.action === "BUY" ? "green" : "red"}
                      fontSize="2xs"
                    >
                      {t.action}
                    </Badge>
                  </HStack>
                ))}
              </VStack>
            )}
          </VStack>
        )}
      </CardBody>
    </Card>
  );
};

export const RebalancingWidget = memo(RebalancingWidgetBase);
