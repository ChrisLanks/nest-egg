/**
 * Compact FIRE metrics widget for the dashboard
 */

import {
  Card,
  CardBody,
  CircularProgress,
  CircularProgressLabel,
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
import { fireApi, type FireMetricsResponse } from "../../../api/fire";
import { useUserView } from "../../../contexts/UserViewContext";

const scoreColor = (ratio: number): string => {
  if (ratio >= 1) return "green.400";
  if (ratio >= 0.5) return "yellow.400";
  return "red.400";
};

const FireMetricsWidgetBase: React.FC = () => {
  const { selectedUserId } = useUserView();

  const { data, isLoading, isError } = useQuery<FireMetricsResponse>({
    queryKey: ["fire-metrics-widget", selectedUserId],
    queryFn: () =>
      fireApi.getMetrics(
        selectedUserId ? { user_id: selectedUserId } : undefined,
      ),
    retry: false,
    staleTime: 60_000,
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

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">FIRE Progress</Heading>
          <Link as={RouterLink} to="/fire" fontSize="sm" color="brand.500">
            View details →
          </Link>
        </HStack>

        {isError || !data ? (
          <VStack spacing={3} py={4}>
            <Text color="text.muted" fontSize="sm" textAlign="center">
              Add accounts and transactions to see FIRE metrics.
            </Text>
          </VStack>
        ) : data.fi_ratio.investable_assets === 0 &&
          data.fi_ratio.annual_expenses === 0 &&
          data.savings_rate.income === 0 &&
          data.savings_rate.spending === 0 ? (
          <VStack spacing={3} py={4}>
            <Text color="text.muted" fontSize="sm" textAlign="center">
              Not enough data yet. Add accounts and categorize transactions to
              see your FIRE progress.
            </Text>
            <Link
              as={RouterLink}
              to="/fire"
              fontSize="sm"
              color="brand.500"
              fontWeight="medium"
            >
              Learn more →
            </Link>
          </VStack>
        ) : (
          <HStack spacing={6} justify="center">
            <VStack spacing={1}>
              <CircularProgress
                value={Math.min(data.fi_ratio.fi_ratio * 100, 100)}
                size="80px"
                thickness="10px"
                color={scoreColor(data.fi_ratio.fi_ratio)}
                trackColor="gray.100"
              >
                <CircularProgressLabel fontWeight="bold" fontSize="md">
                  {(data.fi_ratio.fi_ratio * 100).toFixed(0)}%
                </CircularProgressLabel>
              </CircularProgress>
              <Text fontSize="xs" color="text.secondary">
                FI Ratio
              </Text>
            </VStack>
            <VStack spacing={2} align="start">
              {data.years_to_fi.already_fi &&
              data.years_to_fi.investable_assets > 0 ? (
                <Text fontWeight="bold" color="green.400" fontSize="sm">
                  Financially Independent!
                </Text>
              ) : (
                <>
                  <Text
                    fontSize="2xl"
                    fontWeight="bold"
                    color="brand.500"
                    lineHeight={1}
                  >
                    {data.years_to_fi.years_to_fi != null
                      ? data.years_to_fi.years_to_fi.toFixed(1)
                      : "—"}
                  </Text>
                  <Text fontSize="xs" color="text.secondary">
                    Years to FI
                  </Text>
                </>
              )}
              <Text fontSize="xs" color="text.secondary">
                Savings Rate:{" "}
                {(data.savings_rate.savings_rate * 100).toFixed(0)}%
              </Text>
            </VStack>
          </HStack>
        )}
      </CardBody>
    </Card>
  );
};

export const FireMetricsWidget = memo(FireMetricsWidgetBase);
