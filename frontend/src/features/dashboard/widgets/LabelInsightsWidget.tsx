/**
 * Label-based spending insights widget.
 */

import {
  Badge,
  Box,
  Card,
  CardBody,
  Divider,
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

interface LabelBreakdown {
  category: string;
  amount: number;
  count: number;
  percentage: number;
}

interface LabelSummaryData {
  total_income: number;
  total_expenses: number;
  net: number;
  income_categories: LabelBreakdown[];
  expense_categories: LabelBreakdown[];
}

const fmt = (n: number): string =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Math.abs(n));

const LabelInsightsWidgetBase: React.FC = () => {
  const { selectedUserId } = useUserView();

  const now = new Date();
  const startDate = new Date(now.getFullYear(), now.getMonth(), 1)
    .toISOString()
    .split("T")[0];
  const endDate = now.toISOString().split("T")[0];

  const { data, isLoading, isError } = useQuery<LabelSummaryData>({
    queryKey: ["label-summary-widget", selectedUserId, startDate],
    queryFn: async () => {
      const params: Record<string, string> = {
        start_date: startDate,
        end_date: endDate,
      };
      if (selectedUserId) params.user_id = selectedUserId;
      const res = await api.get("/income-expenses/label-summary", { params });
      return res.data;
    },
    retry: false,
    staleTime: 5 * 60 * 1000,
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

  const allLabels = [
    ...(data?.income_categories ?? []),
    ...(data?.expense_categories ?? []),
  ];

  if (isError || allLabels.length === 0) {
    return (
      <Card h="100%">
        <CardBody>
          <Heading size="md" mb={4}>
            Label Insights
          </Heading>
          <Text color="text.muted" fontSize="sm">
            No labeled transactions this month. Add labels to transactions or
            create rules to auto-label.
          </Text>
        </CardBody>
      </Card>
    );
  }

  const incomeLabels = data?.income_categories ?? [];
  const expenseLabels = data?.expense_categories ?? [];

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Label Insights</Heading>
          <Link
            as={RouterLink}
            to="/transactions"
            fontSize="sm"
            color="brand.500"
          >
            View transactions →
          </Link>
        </HStack>

        {incomeLabels.length > 0 && (
          <VStack
            align="stretch"
            spacing={1}
            mb={expenseLabels.length > 0 ? 4 : 0}
          >
            <Text fontSize="xs" fontWeight="semibold" color="text.secondary">
              Income Labels
            </Text>
            {incomeLabels.slice(0, 4).map((label, idx) => (
              <Box key={label.category}>
                <HStack justify="space-between" py={1}>
                  <HStack spacing={2}>
                    <Badge colorScheme="green" fontSize="2xs">
                      {label.count}
                    </Badge>
                    <Text fontSize="sm" fontWeight="medium">
                      {label.category}
                    </Text>
                  </HStack>
                  <Text fontSize="sm" color="green.500">
                    {fmt(label.amount)}
                  </Text>
                </HStack>
                {idx < incomeLabels.slice(0, 4).length - 1 && <Divider />}
              </Box>
            ))}
          </VStack>
        )}

        {expenseLabels.length > 0 && (
          <VStack align="stretch" spacing={1}>
            <Text fontSize="xs" fontWeight="semibold" color="text.secondary">
              Expense Labels
            </Text>
            {expenseLabels.slice(0, 4).map((label, idx) => (
              <Box key={label.category}>
                <HStack justify="space-between" py={1}>
                  <HStack spacing={2}>
                    <Badge colorScheme="red" fontSize="2xs">
                      {label.count}
                    </Badge>
                    <Text fontSize="sm" fontWeight="medium">
                      {label.category}
                    </Text>
                  </HStack>
                  <Text fontSize="sm" color="finance.negative">
                    {fmt(label.amount)}
                  </Text>
                </HStack>
                {idx < expenseLabels.slice(0, 4).length - 1 && <Divider />}
              </Box>
            ))}
          </VStack>
        )}
      </CardBody>
    </Card>
  );
};

export const LabelInsightsWidget = memo(LabelInsightsWidgetBase);
