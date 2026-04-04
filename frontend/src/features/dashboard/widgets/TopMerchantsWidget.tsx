/**
 * Top merchants widget — shows highest spending by merchant this month.
 */

import { memo } from "react";
import {
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
import { Link as RouterLink } from "react-router-dom";
import { useUserView } from "../../../contexts/UserViewContext";
import api from "../../../services/api";

interface CategoryBreakdown {
  category: string;
  amount: number;
  count: number;
  percentage: number;
}

interface MerchantSummaryData {
  total_expenses: number;
  expense_categories: CategoryBreakdown[];
}

const fmt = (n: number): string =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Math.abs(n));

const TopMerchantsWidgetBase: React.FC = () => {
  const { selectedUserId, effectiveUserId } = useUserView();

  const now = new Date();
  const startDate = new Date(now.getFullYear(), now.getMonth(), 1)
    .toISOString()
    .split("T")[0];
  const endDate = now.toISOString().split("T")[0];

  const { data, isLoading, isError } = useQuery<MerchantSummaryData>({
    queryKey: ["merchant-summary-widget", effectiveUserId, startDate],
    queryFn: async () => {
      const params: Record<string, string> = {
        start_date: startDate,
        end_date: endDate,
      };
      if (selectedUserId) params.user_id = effectiveUserId;
      const res = await api.get("/income-expenses/merchant-summary", {
        params,
      });
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

  const merchants = data?.expense_categories ?? [];

  if (isError || merchants.length === 0) {
    return (
      <Card h="100%">
        <CardBody>
          <Heading size="md" mb={4}>
            Top Merchants
          </Heading>
          <Text color="text.muted" fontSize="sm">
            No spending data for this month yet.
          </Text>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Top Merchants</Heading>
          <Link
            as={RouterLink}
            to="/cash-flow"
            fontSize="sm"
            color="brand.500"
          >
            View all →
          </Link>
        </HStack>

        <VStack align="stretch" spacing={2}>
          {merchants.slice(0, 8).map((m, idx) => (
            <Box key={m.category}>
              <HStack justify="space-between" mb={1}>
                <Text fontWeight="medium" fontSize="sm" noOfLines={1} flex={1}>
                  {m.category}
                </Text>
                <Text
                  fontWeight="bold"
                  fontSize="sm"
                  color="finance.negative"
                  whiteSpace="nowrap"
                >
                  {fmt(m.amount)}
                </Text>
              </HStack>
              <Text fontSize="xs" color="text.muted">
                {m.count} transaction{m.count !== 1 ? "s" : ""} •{" "}
                {m.percentage.toFixed(0)}% of spending
              </Text>
              {idx < merchants.slice(0, 8).length - 1 && <Divider mt={2} />}
            </Box>
          ))}
        </VStack>
      </CardBody>
    </Card>
  );
};

export const TopMerchantsWidget = memo(TopMerchantsWidgetBase);
