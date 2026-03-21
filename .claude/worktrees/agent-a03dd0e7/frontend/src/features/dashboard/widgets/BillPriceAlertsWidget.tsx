/**
 * Bill Price Alerts Widget — subscriptions/bills with detected price increases.
 *
 * Shows merchants where the charge has gone up >5% vs 12 months ago.
 * Pulls from the subscription_insights_service price increases endpoint.
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
  Stat,
  StatLabel,
  StatNumber,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { memo } from "react";
import { FiTrendingUp } from "react-icons/fi";
import { Link as RouterLink } from "react-router-dom";
import { useUserView } from "../../../contexts/UserViewContext";
import api from "../../../services/api";

interface PriceIncrease {
  id: string;
  merchant_name: string;
  frequency: string;
  current_amount: number;
  previous_amount: number | null;
  amount_change_pct: number;
  annual_increase: number | null;
  annual_cost: number;
}

interface PriceAlertsData {
  price_increases: PriceIncrease[];
  total_annual_increase: number;
}

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);

const fmtPct = (n: number) => `+${n.toFixed(1)}%`;

const BillPriceAlertsWidgetBase: React.FC = () => {
  const { selectedUserId } = useUserView();

  const { data, isLoading } = useQuery<PriceAlertsData>({
    queryKey: ["bill-price-alerts-widget", selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const res = await api.get("/recurring/price-increases", { params });
      return res.data;
    },
    staleTime: 15 * 60 * 1000,
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

  const increases = data?.price_increases ?? [];

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <HStack spacing={2}>
            <Heading size="md">Bill Price Alerts</Heading>
            {increases.length > 0 && (
              <Badge colorScheme="red" borderRadius="full">
                {increases.length}
              </Badge>
            )}
          </HStack>
          <Link as={RouterLink} to="/recurring" fontSize="sm" color="brand.500">
            View recurring →
          </Link>
        </HStack>

        {increases.length === 0 ? (
          <VStack spacing={2} py={4}>
            <Text fontSize="2xl">✓</Text>
            <Text fontSize="sm" color="text.muted" textAlign="center">
              No price increases detected in the last year.
            </Text>
          </VStack>
        ) : (
          <>
            {data?.total_annual_increase != null &&
              data.total_annual_increase > 0 && (
                <Stat mb={4}>
                  <StatLabel>
                    <HStack spacing={1}>
                      <Box as={FiTrendingUp} color="red.400" />
                      <Text>Extra cost this year</Text>
                    </HStack>
                  </StatLabel>
                  <StatNumber color="red.500">
                    {fmt(data.total_annual_increase)}
                  </StatNumber>
                </Stat>
              )}

            <VStack align="stretch" spacing={0}>
              {increases.slice(0, 5).map((item, i) => (
                <Box key={item.id}>
                  <HStack justify="space-between" py={2} px={1}>
                    <VStack align="start" spacing={0} flex={1} minW={0}>
                      <Text fontSize="sm" fontWeight="medium" noOfLines={1}>
                        {item.merchant_name}
                      </Text>
                      {item.previous_amount != null && (
                        <Text fontSize="xs" color="text.muted">
                          {fmt(item.previous_amount)} →{" "}
                          {fmt(item.current_amount)}
                        </Text>
                      )}
                    </VStack>
                    <Badge colorScheme="red" fontSize="xs">
                      {fmtPct(item.amount_change_pct)}
                    </Badge>
                  </HStack>
                  {i < Math.min(increases.length, 5) - 1 && <Divider />}
                </Box>
              ))}
            </VStack>
          </>
        )}
      </CardBody>
    </Card>
  );
};

export const BillPriceAlertsWidget = memo(BillPriceAlertsWidgetBase);
