/**
 * Budget suggestions panel.
 *
 * Three modes:
 *  1. Guided walkthrough — user has 0 budgets AND spending history exists.
 *     Shows one suggestion at a time: "Here's your biggest spending category,
 *     create a budget for it?" with Skip / Create Budget buttons.
 *
 *  2. Suggestion grid — user has 1-3 budgets. Shows remaining data-driven
 *     suggestions in a card grid so they can fill out coverage.
 *
 *  3. No history, no budgets — a single prompt to create their first budget
 *     manually. No fake templates.
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
  Box,
  Progress,
} from "@chakra-ui/react";
import { FiTrendingUp, FiPlus, FiZap, FiArrowRight, FiSkipForward } from "react-icons/fi";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { budgetsApi } from "../../../api/budgets";
import { categoriesApi } from "../../../api/categories";
import type { BudgetSuggestion } from "../../../types/budget";
import { useCurrency } from "../../../contexts/CurrencyContext";

const periodLabel = (period: string): string => {
  switch (period) {
    case "monthly":      return "Monthly";
    case "quarterly":    return "Quarterly";
    case "semi_annual":  return "Every 6 Months";
    case "yearly":       return "Yearly";
    default:             return period;
  }
};

const periodColor = (period: string): string => {
  switch (period) {
    case "monthly":     return "blue";
    case "quarterly":   return "purple";
    case "semi_annual": return "teal";
    case "yearly":      return "orange";
    default:            return "gray";
  }
};

interface BudgetSuggestionsProps {
  onAccept: (suggestion: BudgetSuggestion) => void;
  /** Scope suggestions to a specific member's spending history */
  userId?: string | null;
  /** How many budgets the user already has (drives guided vs grid mode) */
  existingBudgetCount: number;
}

export default function BudgetSuggestions({
  onAccept,
  userId,
  existingBudgetCount,
}: BudgetSuggestionsProps) {
  const { formatCurrency } = useCurrency();
  const [skippedIndices, setSkippedIndices] = useState<Set<number>>(new Set());

  const { data: allSuggestions = [], isLoading } = useQuery({
    queryKey: ["budget-suggestions", userId ?? "all"],
    queryFn: () => budgetsApi.getSuggestions(userId ? { user_id: userId } : undefined),
    staleTime: 10 * 60 * 1000,
  });

  const { data: allCategories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: categoriesApi.getCategories,
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

  // Filter to suggestions we can reliably pre-select in the form:
  //   - Custom category (has UUID) → always valid
  //   - Provider category → only if category_primary_raw matches an allCategories entry
  const matchableSuggestions = allSuggestions.filter((s) => {
    if (s.category_id) return true;
    if (!s.category_primary_raw) return false;
    return allCategories.some(
      (c) => !c.id && c.name.toLowerCase() === s.category_primary_raw!.toLowerCase()
    );
  });

  // No data-driven suggestions at all
  if (matchableSuggestions.length === 0) {
    // If the user has budgets already, show nothing more
    if (existingBudgetCount > 0) return null;

    // Truly new user with no transaction history — simple prompt only
    return (
      <Box
        p={5}
        borderWidth="1px"
        borderRadius="md"
        borderColor="border.subtle"
        bg="bg.surface"
      >
        <VStack spacing={3} align="start">
          <Heading size="sm">Start Tracking Your Spending</Heading>
          <Text fontSize="sm" color="text.muted">
            Connect an account or add transactions to get personalised budget
            recommendations based on where your money actually goes.
          </Text>
        </VStack>
      </Box>
    );
  }

  // ── Guided walkthrough (0 budgets + history exists) ─────────────────────────
  if (existingBudgetCount === 0) {
    const available = matchableSuggestions.filter((_, i) => !skippedIndices.has(i));
    const current = available[0];

    if (!current) {
      // User skipped everything
      return (
        <Box p={5} borderWidth="1px" borderRadius="md" borderColor="border.subtle" bg="bg.surface">
          <VStack spacing={2} align="start">
            <Heading size="sm">You're all set for now</Heading>
            <Text fontSize="sm" color="text.muted">
              You can always create more budgets using the button above.
            </Text>
          </VStack>
        </Box>
      );
    }

    const currentIndex = matchableSuggestions.indexOf(current);
    const doneCount = skippedIndices.size;
    const totalCount = matchableSuggestions.length;

    return (
      <VStack align="stretch" spacing={4}>
        <HStack justify="space-between">
          <HStack>
            <Icon as={FiZap} color="yellow.500" />
            <Heading size="sm">Let's build your first budget</Heading>
          </HStack>
          <Text fontSize="xs" color="text.muted">
            {doneCount} of {totalCount} reviewed
          </Text>
        </HStack>

        <Progress
          value={(doneCount / totalCount) * 100}
          size="xs"
          colorScheme="brand"
          borderRadius="full"
        />

        <Card variant="outline" size="sm">
          <CardBody>
            <VStack align="stretch" spacing={3}>
              <Text fontSize="xs" color="text.muted" textTransform="uppercase" letterSpacing="wide">
                Your biggest unbudgeted category
              </Text>

              <HStack justify="space-between" align="start">
                <VStack align="start" spacing={0}>
                  <Text fontWeight="bold" fontSize="lg">
                    {current.category_name}
                  </Text>
                  <HStack spacing={1}>
                    <Icon as={FiTrendingUp} color="text.muted" boxSize={3} />
                    <Text fontSize="sm" color="text.muted">
                      {formatCurrency(current.avg_monthly_spend, {
                        minimumFractionDigits: 0,
                        maximumFractionDigits: 0,
                      })}
                      /mo avg · {current.transaction_count} transactions
                    </Text>
                  </HStack>
                </VStack>
                <Badge colorScheme={periodColor(current.suggested_period)}>
                  {periodLabel(current.suggested_period)}
                </Badge>
              </HStack>

              <HStack justify="space-between" align="center">
                <VStack align="start" spacing={0}>
                  <Text fontSize="2xl" fontWeight="bold">
                    {formatCurrency(current.suggested_amount, {
                      minimumFractionDigits: 0,
                      maximumFractionDigits: 0,
                    })}
                  </Text>
                  <Text fontSize="xs" color="text.muted">suggested budget (10% buffer included)</Text>
                </VStack>
              </HStack>

              <HStack spacing={3}>
                <Button
                  flex={1}
                  colorScheme="brand"
                  rightIcon={<FiArrowRight />}
                  onClick={() => onAccept(current)}
                >
                  Create Budget
                </Button>
                <Button
                  variant="ghost"
                  color="text.muted"
                  leftIcon={<FiSkipForward />}
                  onClick={() =>
                    setSkippedIndices((prev) => new Set([...prev, currentIndex]))
                  }
                >
                  Skip
                </Button>
              </HStack>

              {available.length > 1 && (
                <Text fontSize="xs" color="text.muted" textAlign="center">
                  {available.length - 1} more suggestion{available.length - 1 !== 1 ? "s" : ""} after this one
                </Text>
              )}
            </VStack>
          </CardBody>
        </Card>
      </VStack>
    );
  }

  // ── Grid mode (1–3 budgets, show remaining suggestions) ─────────────────────
  return (
    <VStack align="stretch" spacing={4}>
      <HStack>
        <Icon as={FiZap} color="yellow.500" />
        <Heading size="sm">More Suggestions</Heading>
        <Text fontSize="sm" color="text.muted">
          — based on your spending history
        </Text>
      </HStack>
      <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={3}>
        {matchableSuggestions.map((s) => (
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
                  <Badge colorScheme={periodColor(s.suggested_period)} size="sm">
                    {periodLabel(s.suggested_period)}
                  </Badge>
                </HStack>

                <HStack spacing={3}>
                  <VStack align="start" spacing={0}>
                    <Text fontSize="lg" fontWeight="bold">
                      {formatCurrency(s.suggested_amount, {
                        minimumFractionDigits: 0,
                        maximumFractionDigits: 0,
                      })}
                    </Text>
                    <Text fontSize="xs" color="text.muted">suggested budget</Text>
                  </VStack>
                  <VStack align="start" spacing={0}>
                    <HStack spacing={1}>
                      <Icon as={FiTrendingUp} color="text.muted" boxSize={3} />
                      <Text fontSize="sm" color="text.muted">
                        {formatCurrency(s.avg_monthly_spend, {
                          minimumFractionDigits: 0,
                          maximumFractionDigits: 0,
                        })}
                        /mo
                      </Text>
                    </HStack>
                    <Text fontSize="xs" color="text.muted">
                      avg · {s.transaction_count} transactions
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
