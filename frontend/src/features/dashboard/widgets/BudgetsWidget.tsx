import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Box,
  Button,
  Card,
  CardBody,
  Center,
  Heading,
  HStack,
  Link,
  Progress,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useQueries, useQuery } from "@tanstack/react-query";
import { memo } from "react";
import { Link as RouterLink } from "react-router-dom";
import { budgetsApi } from "../../../api/budgets";
import { useUserView } from "../../../contexts/UserViewContext";

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

const BudgetsWidgetBase: React.FC = () => {
  const { selectedUserId } = useUserView();

  const {
    data: budgets,
    isLoading,
    isError: budgetsError,
    refetch: refetchBudgets,
  } = useQuery({
    queryKey: ["budgets-widget", selectedUserId],
    queryFn: () =>
      budgetsApi.getAll({
        is_active: true,
        ...(selectedUserId ? { user_id: selectedUserId } : {}),
      }),
    staleTime: 60_000,
  });

  const topBudgets = (budgets ?? []).slice(0, 5);

  const spendingQueries = useQueries({
    queries: topBudgets.map((b) => ({
      queryKey: ["budget-spending", b.id],
      queryFn: () => budgetsApi.getSpending(b.id),
      enabled: topBudgets.length > 0,
    })),
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

  if (budgetsError) {
    return (
      <Card h="100%">
        <CardBody>
          <Center h="100%">
            <VStack spacing={3}>
              <Alert status="error" borderRadius="md">
                <AlertIcon />
                <AlertTitle>Failed to load budgets.</AlertTitle>
                <AlertDescription>Please try again.</AlertDescription>
              </Alert>
              <Button size="sm" colorScheme="blue" onClick={() => refetchBudgets()}>
                Retry
              </Button>
            </VStack>
          </Center>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Budgets</Heading>
          <Link as={RouterLink} to="/budgets" fontSize="sm" color="brand.500">
            View all →
          </Link>
        </HStack>

        {topBudgets.length === 0 ? (
          <Text color="text.muted" fontSize="sm">
            No active budgets. Add one to start tracking.
          </Text>
        ) : (
          <VStack align="stretch" spacing={4}>
            {topBudgets.map((budget, index) => {
              const spending = spendingQueries[index]?.data;
              const pct = spending
                ? Math.min(100, spending.percentage * 100)
                : 0;
              // Use budget's own alert_threshold (0–1 range) rather than a
              // hardcoded 80% — respects per-budget configuration
              const alertPct = (budget.alert_threshold ?? 0.8) * 100;
              const isOver = pct >= alertPct;

              return (
                <Box key={budget.id}>
                  <HStack justify="space-between" mb={1}>
                    <Text fontWeight="medium" fontSize="sm" noOfLines={1}>
                      {budget.name}
                    </Text>
                    <Text
                      fontSize="sm"
                      color={isOver ? "finance.negative" : "text.secondary"}
                      whiteSpace="nowrap"
                    >
                      {spending
                        ? `${formatCurrency(spending.spent)} / ${formatCurrency(budget.amount)}`
                        : formatCurrency(budget.amount)}
                    </Text>
                  </HStack>
                  <Progress
                    value={pct}
                    size="sm"
                    colorScheme={
                      pct >= 100 ? "red" : isOver ? "orange" : "green"
                    }
                    borderRadius="full"
                  />
                </Box>
              );
            })}
          </VStack>
        )}
      </CardBody>
    </Card>
  );
};

export const BudgetsWidget = memo(BudgetsWidgetBase);
