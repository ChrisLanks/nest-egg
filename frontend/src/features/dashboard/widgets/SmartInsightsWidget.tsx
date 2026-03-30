/**
 * SmartInsightsWidget
 *
 * Dashboard widget showing top smart financial insights from /smart-insights.
 * Surfaces proactive alerts: emergency fund gaps, spending anomalies, budget
 * overruns, fund fee drag, IRMAA risk, and more — all derived from live data.
 */

import { memo } from "react";
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
import { Link as RouterLink } from "react-router-dom";
import { useUserView } from "../../../contexts/UserViewContext";
import api from "../../../services/api";

interface InsightItem {
  type: string;
  title: string;
  message: string;
  action: string;
  priority: string;
  category: string;
  icon: string;
  priority_score: number;
  amount: number | null;
  amount_label: string | null;
}

interface SmartInsightsResponse {
  insights: InsightItem[];
  has_retirement_accounts: boolean;
  has_taxable_investments: boolean;
  has_investment_holdings: boolean;
}

const priorityColor = (p: string): string => {
  if (p === "high") return "red";
  if (p === "medium") return "orange";
  return "gray";
};

const fmt = (n: number): string =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);

const SmartInsightsWidgetBase: React.FC = () => {
  const { selectedUserId } = useUserView();

  const { data, isLoading, isError } = useQuery<SmartInsightsResponse>({
    queryKey: ["smart-insights-widget", selectedUserId],
    queryFn: async () => {
      const params: Record<string, string | number> = { max_insights: 5 };
      if (selectedUserId) params.user_id = selectedUserId;
      const res = await api.get("/smart-insights", { params });
      return res.data;
    },
    staleTime: 10 * 60 * 1000,
    retry: false,
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
          <Heading size="md" mb={2}>Smart Insights</Heading>
          <Text color="text.muted" fontSize="sm">
            Not enough data yet to generate insights.
          </Text>
        </CardBody>
      </Card>
    );
  }

  const insights = data.insights;

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Smart Insights</Heading>
          {insights.length > 0 && (
            <Badge colorScheme={priorityColor(insights[0].priority)} fontSize="xs">
              {insights.filter((i) => i.priority === "high").length > 0
                ? `${insights.filter((i) => i.priority === "high").length} urgent`
                : `${insights.length} tip${insights.length !== 1 ? "s" : ""}`}
            </Badge>
          )}
        </HStack>

        {insights.length === 0 ? (
          <Text color="text.muted" fontSize="sm">
            Everything looks good — no action items right now.
          </Text>
        ) : (
          <VStack align="stretch" spacing={3}>
            {insights.map((insight) => (
              <Box
                key={insight.type}
                borderLeft="3px solid"
                borderLeftColor={`${priorityColor(insight.priority)}.400`}
                pl={3}
                py={1}
              >
                <HStack justify="space-between" mb={1}>
                  <Text fontSize="sm" fontWeight="semibold">
                    {insight.icon} {insight.title}
                  </Text>
                  <Badge
                    colorScheme={priorityColor(insight.priority)}
                    variant="subtle"
                    fontSize="xs"
                    flexShrink={0}
                  >
                    {insight.priority}
                  </Badge>
                </HStack>
                <Text fontSize="xs" color="text.secondary" noOfLines={2}>
                  {insight.message}
                </Text>
                {insight.amount != null && insight.amount_label && (
                  <Text fontSize="xs" color="text.muted" mt={0.5}>
                    {insight.amount_label}: <strong>{fmt(insight.amount)}</strong>
                  </Text>
                )}
              </Box>
            ))}
          </VStack>
        )}

        <Link
          as={RouterLink}
          to="/smart-insights"
          fontSize="xs"
          color="brand.500"
          mt={4}
          display="block"
        >
          View all insights →
        </Link>
      </CardBody>
    </Card>
  );
};

export const SmartInsightsWidget = memo(SmartInsightsWidgetBase);
