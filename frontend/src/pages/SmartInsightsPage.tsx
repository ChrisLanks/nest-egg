/**
 * Smart Insights page — proactive financial planning insights derived
 * entirely from the user's own account data. No manual input required.
 *
 * Groups insights by category (cash, investing, tax, retirement) and
 * shows actionable cards sorted by priority score.
 */

import {
  Badge,
  Box,
  Button,
  Card,
  CardBody,
  Center,
  Container,
  Heading,
  HStack,
  Icon,
  SimpleGrid,
  Spinner,
  Text,
  Tooltip,
  VStack,
  Alert,
  AlertIcon,
  Divider,
  Wrap,
  WrapItem,
} from "@chakra-ui/react";
import { FiLink } from "react-icons/fi";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { smartInsightsApi, type InsightItem } from "../api/smartInsights";
import { useUserView } from "../contexts/UserViewContext";
import api from "../services/api";
import { useCurrency } from "../contexts/CurrencyContext";

// ── Helpers ───────────────────────────────────────────────────────────────

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

const priorityColor: Record<string, string> = {
  high: "red",
  medium: "orange",
  low: "blue",
};

const categoryLabel: Record<string, string> = {
  cash: "Cash",
  investing: "Investing",
  tax: "Tax",
  retirement: "Retirement",
};

const categoryTooltip: Record<string, string> = {
  cash: "Liquid savings, emergency fund coverage, and cash management",
  investing: "Portfolio allocation, fees, diversification, and investment gaps",
  tax: "Tax optimization opportunities, deductions, and tax-efficient strategies",
  retirement: "Retirement readiness, contribution gaps, and long-term savings pace",
};

const categoryColor: Record<string, string> = {
  cash: "teal",
  investing: "purple",
  tax: "green",
  retirement: "blue",
};

// ── Insight Card ──────────────────────────────────────────────────────────

function InsightCard({ insight }: { insight: InsightItem }) {
  const showStaleBadge = insight.data_is_stale === true && insight.data_vintage != null;

  return (
    <Card
      variant="outline"
      borderLeftWidth={4}
      borderLeftColor={`${priorityColor[insight.priority]}.400`}
    >
      <CardBody>
        <VStack align="start" spacing={2}>
          <HStack justify="space-between" w="full" flexWrap="wrap" gap={2}>
            <HStack spacing={2} flexWrap="wrap">
              <Text fontSize="xl">{insight.icon}</Text>
              <Text fontWeight="semibold" fontSize="sm">
                {insight.title}
              </Text>
            </HStack>
            <HStack spacing={2} flexWrap="wrap">
              {showStaleBadge && (
                <Tooltip
                  label={`Benchmark data is from the ${insight.data_vintage} Federal Reserve Survey of Consumer Finances. New data is typically released every 3 years — an update may be in progress.`}
                  placement="top"
                  hasArrow
                >
                  <Badge
                    colorScheme="yellow"
                    size="sm"
                    variant="subtle"
                    cursor="help"
                    data-testid="stale-data-badge"
                  >
                    Data as of {insight.data_vintage} · update in progress
                  </Badge>
                </Tooltip>
              )}
              <Badge
                colorScheme={categoryColor[insight.category]}
                size="sm"
                variant="subtle"
              >
                {categoryLabel[insight.category] ?? insight.category}
              </Badge>
              <Badge colorScheme={priorityColor[insight.priority]} size="sm">
                {insight.priority}
              </Badge>
            </HStack>
          </HStack>

          <Text fontSize="sm" color="text.secondary" lineHeight="tall">
            {insight.message}
          </Text>

          {insight.amount !== null && (
            <HStack spacing={1}>
              <Text fontSize="xs" color="text.muted">
                Amount:
              </Text>
              <Text fontSize="xs" fontWeight="semibold" color="brand.500">
                {formatCurrency(insight.amount)}
              </Text>
            </HStack>
          )}

          <Divider />
          <Text fontSize="xs" color="text.secondary" fontStyle="italic">
            {insight.action}
          </Text>
        </VStack>
      </CardBody>
    </Card>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────

export const SmartInsightsPage = () => {
  const { selectedUserId, effectiveUserId } = useUserView();
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const navigate = useNavigate();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["smart-insights", effectiveUserId],
    queryFn: () =>
      smartInsightsApi.getInsights({
        user_id: effectiveUserId || undefined,
        max_insights: 20,
      }),
  });

  const { data: accounts } = useQuery({
    queryKey: ["accounts-insights-check"],
    queryFn: () => api.get("/accounts").then((r) => r.data as Array<unknown>),
    staleTime: 30_000,
  });

  if (isLoading) {
    return (
      <Center h="60vh">
        <Spinner size="xl" color="brand.500" thickness="4px" />
      </Center>
    );
  }

  if (isError) {
    return (
      <Container maxW="4xl" py={8}>
        <Alert status="error" borderRadius="lg">
          <AlertIcon />
          Failed to load insights. Please try again.
        </Alert>
      </Container>
    );
  }

  const insights = data?.insights ?? [];

  // Group by category, preserving priority-score order within each group
  const grouped: Record<string, InsightItem[]> = {};
  for (const insight of insights) {
    (grouped[insight.category] ??= []).push(insight);
  }

  const categoryOrder = ["cash", "tax", "retirement", "investing"] as const;

  // Categories that actually have insights (in display order)
  const activeCategories = categoryOrder.filter((c) => grouped[c]?.length);

  // Which categories to display — all, or only the selected one
  const visibleCategories =
    selectedCategory !== null
      ? activeCategories.filter((c) => c === selectedCategory)
      : activeCategories;

  const handlePillClick = (cat: string) => {
    setSelectedCategory((prev) => (prev === cat ? null : cat));
  };

  return (
    <Container maxW="5xl" py={6}>
      <VStack align="start" spacing={6}>
        {/* Header */}
        <Box>
          <Heading size="lg">Recommendations</Heading>
          <Text color="text.secondary" mt={1}>
            Automated tips for your spending, savings, taxes, and retirement — generated from your actual account data. No manual input needed; new insights appear as your data grows.
          </Text>
        </Box>

        {/* Category filter pills */}
        {insights.length > 0 && (
          <Wrap spacing={2}>
            {/* "All" pill */}
            <WrapItem>
              <Badge
                colorScheme={selectedCategory === null ? "brand" : "gray"}
                px={3}
                py={1}
                borderRadius="full"
                fontSize="xs"
                cursor="pointer"
                variant={selectedCategory === null ? "solid" : "outline"}
                onClick={() => setSelectedCategory(null)}
                data-testid="pill-all"
              >
                All · {insights.length}
              </Badge>
            </WrapItem>

            {activeCategories.map((cat) => (
              <WrapItem key={cat}>
                <Tooltip label={categoryTooltip[cat]} openDelay={400}>
                  <Badge
                    colorScheme={categoryColor[cat]}
                    px={3}
                    py={1}
                    borderRadius="full"
                    fontSize="xs"
                    cursor="pointer"
                    variant={selectedCategory === cat ? "solid" : "subtle"}
                    onClick={() => handlePillClick(cat)}
                    data-testid={`pill-${cat}`}
                  >
                    {categoryLabel[cat]} · {grouped[cat].length}
                  </Badge>
                </Tooltip>
              </WrapItem>
            ))}
          </Wrap>
        )}

        {/* Empty state — no accounts connected yet */}
        {insights.length === 0 && Array.isArray(accounts) && accounts.length === 0 && (
          <Box
            p={8}
            borderRadius="xl"
            bg="bg.surface"
            border="1px dashed"
            borderColor="border.default"
            textAlign="center"
          >
            <VStack spacing={4} maxW="sm" mx="auto">
              <Icon as={FiLink} boxSize={10} color="brand.500" />
              <VStack spacing={1}>
                <Text fontWeight="semibold">No insights yet</Text>
                <Text fontSize="sm" color="text.secondary">
                  Connect a bank or investment account and we'll automatically
                  generate personalized recommendations — no manual input needed.
                </Text>
              </VStack>
              <Button
                colorScheme="brand"
                size="sm"
                leftIcon={<FiLink />}
                onClick={() => navigate("/accounts")}
              >
                Connect an Account
              </Button>
            </VStack>
          </Box>
        )}

        {/* Empty state — has accounts but no insights triggered */}
        {insights.length === 0 && Array.isArray(accounts) && accounts.length > 0 && (
          <Alert status="success" borderRadius="lg">
            <AlertIcon />
            <VStack align="start" spacing={0}>
              <Text fontWeight="semibold">Looking good — no action items right now.</Text>
              <Text fontSize="sm">
                Insights appear automatically when our analysis detects an opportunity — like a high-fee fund, a savings gap, or a tax move. Add more accounts or transactions to unlock additional recommendations.
              </Text>
            </VStack>
          </Alert>
        )}

        {/* Insights grouped by category */}
        {visibleCategories.map((cat) => (
          <Box key={cat} w="full">
            <HStack spacing={2} mb={3}>
              <Text
                fontWeight="bold"
                fontSize="sm"
                textTransform="uppercase"
                letterSpacing="wider"
                color="text.secondary"
              >
                {categoryLabel[cat]}
              </Text>
              <Badge colorScheme={categoryColor[cat]} variant="subtle">
                {grouped[cat].length}
              </Badge>
            </HStack>
            <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={4}>
              {grouped[cat].map((insight, i) => (
                <InsightCard key={`${insight.type}-${i}`} insight={insight} />
              ))}
            </SimpleGrid>
          </Box>
        ))}
      </VStack>
    </Container>
  );
};

export default SmartInsightsPage;
