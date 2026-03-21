/**
 * Compact tax insights widget — shows age-based tax action items.
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
import api from "../../../services/api";

interface TaxInsight {
  category: string;
  title: string;
  description: string;
  priority: "action" | "info";
  age_relevant: boolean;
}

interface TaxInsightsData {
  age: number;
  insights: TaxInsight[];
  contribution_limits: unknown[];
}

const priorityColor = (priority: string): string =>
  priority === "action" ? "orange" : "blue";

const TaxInsightsWidgetBase: React.FC = () => {
  const { data, isLoading, isError } = useQuery<TaxInsightsData>({
    queryKey: ["tax-insights-widget"],
    queryFn: async () => {
      const res = await api.get("/tax-advisor/insights");
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

  if (isError || !data || data.insights.length === 0) {
    return (
      <Card h="100%">
        <CardBody>
          <Heading size="md" mb={4}>
            Tax Insights
          </Heading>
          <Text color="text.muted" fontSize="sm">
            {!data || (data as { error?: string }).error
              ? "Add your birthdate in Settings to get personalized tax insights."
              : "No tax insights available at this time."}
          </Text>
        </CardBody>
      </Card>
    );
  }

  // Show action items first, then info items, limited to 4
  const sorted = [...data.insights].sort((a, b) => {
    if (a.priority === "action" && b.priority !== "action") return -1;
    if (b.priority === "action" && a.priority !== "action") return 1;
    return 0;
  });
  const displayed = sorted.slice(0, 4);
  const actionCount = data.insights.filter(
    (i) => i.priority === "action",
  ).length;

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <HStack spacing={2}>
            <Heading size="md">Tax Insights</Heading>
            {actionCount > 0 && (
              <Badge colorScheme="orange" fontSize="xs">
                {actionCount} action{actionCount > 1 ? "s" : ""}
              </Badge>
            )}
          </HStack>
          <Text fontSize="xs" color="text.muted">
            Age {data.age}
          </Text>
        </HStack>

        <VStack align="stretch" spacing={3}>
          {displayed.map((insight) => (
            <Box
              key={insight.category}
              p={2}
              borderRadius="md"
              bg={insight.priority === "action" ? "orange.50" : "gray.50"}
              _dark={{
                bg: insight.priority === "action" ? "orange.900" : "gray.700",
              }}
            >
              <HStack spacing={2} mb={1}>
                <Badge
                  colorScheme={priorityColor(insight.priority)}
                  fontSize="2xs"
                >
                  {insight.priority}
                </Badge>
                <Text fontSize="xs" fontWeight="semibold" noOfLines={1}>
                  {insight.title}
                </Text>
              </HStack>
              <Text fontSize="xs" color="text.muted" noOfLines={2}>
                {insight.description}
              </Text>
            </Box>
          ))}
        </VStack>

        {data.insights.length > 4 && (
          <Link
            as={RouterLink}
            to="/investments"
            fontSize="xs"
            color="brand.500"
            mt={3}
            display="block"
          >
            View all {data.insights.length} insights →
          </Link>
        )}
      </CardBody>
    </Card>
  );
};

export const TaxInsightsWidget = memo(TaxInsightsWidgetBase);
