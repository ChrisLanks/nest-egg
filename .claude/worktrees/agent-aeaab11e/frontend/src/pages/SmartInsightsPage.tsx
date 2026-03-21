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
  Card,
  CardBody,
  Center,
  Container,
  Heading,
  HStack,
  SimpleGrid,
  Spinner,
  Text,
  VStack,
  Alert,
  AlertIcon,
  Divider,
  Wrap,
  WrapItem,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { smartInsightsApi, type InsightItem } from "../api/smartInsights";
import { useUserView } from "../contexts/UserViewContext";

// ── Helpers ───────────────────────────────────────────────────────────────

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
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

const categoryColor: Record<string, string> = {
  cash: "teal",
  investing: "purple",
  tax: "green",
  retirement: "blue",
};

// ── Insight Card ──────────────────────────────────────────────────────────

function InsightCard({ insight }: { insight: InsightItem }) {
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
            <HStack spacing={2}>
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
  const { selectedUserId } = useUserView();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["smart-insights", selectedUserId],
    queryFn: () =>
      smartInsightsApi.getInsights({
        user_id: selectedUserId || undefined,
        max_insights: 20,
      }),
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

  return (
    <Container maxW="5xl" py={6}>
      <VStack align="start" spacing={6}>
        {/* Header */}
        <Box>
          <Heading size="lg">Smart Insights</Heading>
          <Text color="text.secondary" mt={1}>
            Proactive recommendations based on your live account data — no
            manual input required.
          </Text>
        </Box>

        {/* Category filter pills (visual only) */}
        {insights.length > 0 && (
          <Wrap spacing={2}>
            {categoryOrder
              .filter((c) => grouped[c]?.length)
              .map((cat) => (
                <WrapItem key={cat}>
                  <Badge
                    colorScheme={categoryColor[cat]}
                    px={3}
                    py={1}
                    borderRadius="full"
                    fontSize="xs"
                  >
                    {categoryLabel[cat]} · {grouped[cat].length}
                  </Badge>
                </WrapItem>
              ))}
          </Wrap>
        )}

        {/* Empty state */}
        {insights.length === 0 && (
          <Alert status="success" borderRadius="lg">
            <AlertIcon />
            <VStack align="start" spacing={0}>
              <Text fontWeight="semibold">All clear!</Text>
              <Text fontSize="sm">
                No action items found. Add more accounts and transactions to
                unlock additional insights.
              </Text>
            </VStack>
          </Alert>
        )}

        {/* Insights grouped by category */}
        {categoryOrder
          .filter((cat) => grouped[cat]?.length)
          .map((cat) => (
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
