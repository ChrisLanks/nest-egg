/**
 * Budget suggestion cards shown when user has no/few budgets.
 * Analyzes spending history and suggests budget amounts and periods.
 */

import {
  Button,
  Card,
  CardBody,
  Heading,
  HStack,
  SimpleGrid,
  Text,
  VStack,
  Badge,
  Icon,
  Skeleton,
} from "@chakra-ui/react";
import { FiTrendingUp, FiPlus, FiZap } from "react-icons/fi";
import { useQuery } from "@tanstack/react-query";
import { budgetsApi } from "../../../api/budgets";
import type { BudgetSuggestion } from "../../../types/budget";

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

const periodLabel = (period: string): string => {
  switch (period) {
    case "monthly":
      return "Monthly";
    case "quarterly":
      return "Quarterly";
    case "semi_annual":
      return "Every 6 Months";
    case "yearly":
      return "Yearly";
    default:
      return period;
  }
};

const periodColor = (period: string): string => {
  switch (period) {
    case "monthly":
      return "blue";
    case "quarterly":
      return "purple";
    case "semi_annual":
      return "teal";
    case "yearly":
      return "orange";
    default:
      return "gray";
  }
};

interface BudgetSuggestionsProps {
  onAccept: (suggestion: BudgetSuggestion) => void;
}

export default function BudgetSuggestions({
  onAccept,
}: BudgetSuggestionsProps) {
  const { data: suggestions = [], isLoading } = useQuery({
    queryKey: ["budget-suggestions"],
    queryFn: () => budgetsApi.getSuggestions(),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });

  if (isLoading) {
    return (
      <VStack align="stretch" spacing={4}>
        <HStack>
          <Icon as={FiZap} color="yellow.500" />
          <Heading size="sm">Suggested Budgets</Heading>
        </HStack>
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={3}>
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} height="140px" borderRadius="md" />
          ))}
        </SimpleGrid>
      </VStack>
    );
  }

  if (suggestions.length === 0) {
    return null;
  }

  return (
    <VStack align="stretch" spacing={4}>
      <HStack>
        <Icon as={FiZap} color="yellow.500" />
        <Heading size="sm">Suggested Budgets</Heading>
        <Text fontSize="sm" color="text.secondary">
          Based on your spending history
        </Text>
      </HStack>
      <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={3}>
        {suggestions.map((s) => (
          <Card
            key={s.category_name}
            variant="outline"
            size="sm"
            _hover={{ borderColor: "blue.300", shadow: "sm" }}
            transition="all 0.15s"
          >
            <CardBody>
              <VStack align="stretch" spacing={2}>
                <HStack justify="space-between">
                  <Text fontWeight="semibold" fontSize="sm" noOfLines={1}>
                    {s.category_name}
                  </Text>
                  <Badge
                    colorScheme={periodColor(s.suggested_period)}
                    size="sm"
                  >
                    {periodLabel(s.suggested_period)}
                  </Badge>
                </HStack>

                <HStack spacing={3}>
                  <VStack align="start" spacing={0}>
                    <Text fontSize="lg" fontWeight="bold">
                      {formatCurrency(s.suggested_amount)}
                    </Text>
                    <Text fontSize="xs" color="text.secondary">
                      suggested budget
                    </Text>
                  </VStack>
                  <VStack align="start" spacing={0}>
                    <HStack spacing={1}>
                      <Icon
                        as={FiTrendingUp}
                        color="text.secondary"
                        boxSize={3}
                      />
                      <Text fontSize="sm" color="text.secondary">
                        {formatCurrency(s.avg_monthly_spend)}/mo
                      </Text>
                    </HStack>
                    <Text fontSize="xs" color="text.secondary">
                      avg from {s.transaction_count} transactions
                    </Text>
                  </VStack>
                </HStack>

                <Button
                  size="sm"
                  variant="outline"
                  colorScheme="blue"
                  leftIcon={<FiPlus />}
                  onClick={() => onAccept(s)}
                  w="full"
                >
                  Create Budget
                </Button>
              </VStack>
            </CardBody>
          </Card>
        ))}
      </SimpleGrid>
    </VStack>
  );
}
