/**
 * Budget suggestion cards shown when user has no/few budgets.
 * Analyzes spending history and suggests budget amounts and periods.
 * Falls back to universal starter templates when no history exists.
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
import { FiTrendingUp, FiPlus, FiZap, FiBookOpen } from "react-icons/fi";
import { useQuery } from "@tanstack/react-query";
import { budgetsApi } from "../../../api/budgets";
import type { BudgetSuggestion } from "../../../types/budget";
import { useCurrency } from "../../../contexts/CurrencyContext";

// Starter budgets shown to brand-new users with no spending history.
// Amounts are conservative medians — users are prompted to adjust.
const STARTER_BUDGETS: BudgetSuggestion[] = [
  {
    category_name: "Groceries",
    category_id: null,
    suggested_amount: 400,
    suggested_period: "monthly",
    avg_monthly_spend: 0,
    total_spend: 0,
    month_count: 0,
    transaction_count: 0,
  },
  {
    category_name: "Dining Out",
    category_id: null,
    suggested_amount: 200,
    suggested_period: "monthly",
    avg_monthly_spend: 0,
    total_spend: 0,
    month_count: 0,
    transaction_count: 0,
  },
  {
    category_name: "Gas & Transportation",
    category_id: null,
    suggested_amount: 150,
    suggested_period: "monthly",
    avg_monthly_spend: 0,
    total_spend: 0,
    month_count: 0,
    transaction_count: 0,
  },
  {
    category_name: "Entertainment",
    category_id: null,
    suggested_amount: 100,
    suggested_period: "monthly",
    avg_monthly_spend: 0,
    total_spend: 0,
    month_count: 0,
    transaction_count: 0,
  },
  {
    category_name: "Shopping",
    category_id: null,
    suggested_amount: 200,
    suggested_period: "monthly",
    avg_monthly_spend: 0,
    total_spend: 0,
    month_count: 0,
    transaction_count: 0,
  },
  {
    category_name: "Subscriptions",
    category_id: null,
    suggested_amount: 50,
    suggested_period: "monthly",
    avg_monthly_spend: 0,
    total_spend: 0,
    month_count: 0,
    transaction_count: 0,
  },
];

// formatCurrency is obtained from CurrencyContext inside the component

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
  /** Scope suggestions to a specific member's spending history */
  userId?: string | null;
}

export default function BudgetSuggestions({
  onAccept,
  userId,
}: BudgetSuggestionsProps) {
  const { formatCurrency } = useCurrency();
  const { data: historySuggestions = [], isLoading } = useQuery({
    queryKey: ["budget-suggestions", userId ?? "all"],
    queryFn: () => budgetsApi.getSuggestions(userId ? { user_id: userId } : undefined),
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

  const isHistoryBased = historySuggestions.length > 0;
  const suggestions = isHistoryBased ? historySuggestions : STARTER_BUDGETS;

  return (
    <VStack align="stretch" spacing={4}>
      <HStack>
        <Icon
          as={isHistoryBased ? FiZap : FiBookOpen}
          color={isHistoryBased ? "yellow.500" : "brand.500"}
        />
        <Heading size="sm">Suggested Budgets</Heading>
        <Text fontSize="sm" color="text.muted">
          {isHistoryBased
            ? "— based on your spending history"
            : "— common starting points, adjust to match your life"}
        </Text>
      </HStack>
      <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={3}>
        {suggestions.map((s) => (
          <Card
            key={s.category_name}
            variant="outline"
            size="sm"
            _hover={{ borderColor: "brand.300", shadow: "sm" }}
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
                      {formatCurrency(s.suggested_amount, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                    </Text>
                    <Text fontSize="xs" color="text.muted">
                      suggested budget
                    </Text>
                  </VStack>
                  {isHistoryBased && (
                    <VStack align="start" spacing={0}>
                      <HStack spacing={1}>
                        <Icon
                          as={FiTrendingUp}
                          color="text.muted"
                          boxSize={3}
                        />
                        <Text fontSize="sm" color="text.muted">
                          {formatCurrency(s.avg_monthly_spend, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}/mo
                        </Text>
                      </HStack>
                      <Text fontSize="xs" color="text.muted">
                        avg from {s.transaction_count} transactions
                      </Text>
                    </VStack>
                  )}
                </HStack>

                <Button
                  size="sm"
                  variant="outline"
                  colorScheme="blue"
                  leftIcon={<FiPlus />}
                  onClick={() => onAccept(s)}
                  w="full"
                >
                  {isHistoryBased ? "Create Budget" : "Use This"}
                </Button>
              </VStack>
            </CardBody>
          </Card>
        ))}
      </SimpleGrid>
    </VStack>
  );
}
