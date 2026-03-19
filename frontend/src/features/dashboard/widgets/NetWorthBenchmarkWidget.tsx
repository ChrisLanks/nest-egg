/**
 * Net Worth Benchmark Widget
 *
 * Compares the user's net worth against Federal Reserve SCF 2022 peers
 * in their age group, showing their approximate percentile rank and
 * the distance to the next milestone.
 */

import {
  Badge,
  Box,
  Card,
  CardBody,
  HStack,
  Progress,
  Skeleton,
  Text,
  Tooltip,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { memo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useUserView } from "../../../contexts/UserViewContext";
import api from "../../../services/api";

interface BenchmarkData {
  age_group: string;
  age_group_label: string;
  user_net_worth: number;
  median_net_worth: number;
  mean_net_worth: number;
  percentile: number;
  p25: number;
  p50: number;
  p75: number;
  p90: number;
  next_milestone_label: string | null;
  next_milestone_value: number | null;
  gap_to_next_milestone: number | null;
  all_age_groups: {
    age_group: string;
    age_group_label: string;
    median: number;
    mean: number;
    p25: number;
    p75: number;
  }[];
}

const fmt = (v: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(v);

const percentileColor = (pct: number): string => {
  if (pct >= 75) return "green";
  if (pct >= 50) return "blue";
  if (pct >= 25) return "yellow";
  return "orange";
};

const NetWorthBenchmarkWidgetBase: React.FC = () => {
  const { selectedUserId } = useUserView();

  const { data, isLoading, isError } = useQuery<BenchmarkData>({
    queryKey: ["net-worth-benchmark", selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const response = await api.get("/dashboard/net-worth-benchmark", {
        params,
      });
      return response.data;
    },
    staleTime: 1000 * 60 * 60, // 1 hour — SCF data is static
  });

  if (isLoading) {
    return (
      <Card h="100%">
        <CardBody>
          <VStack align="stretch" spacing={4}>
            <Skeleton height="20px" width="180px" />
            <Skeleton height="12px" width="120px" />
            <Skeleton height="60px" />
            <Skeleton height="140px" />
            <Skeleton height="16px" width="240px" />
          </VStack>
        </CardBody>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card h="100%">
        <CardBody>
          <VStack align="center" justify="center" h="100%" spacing={2} py={8}>
            <Text fontSize="sm" color="text.muted">
              Add a birthdate in your profile to see how your net worth compares
              to peers.
            </Text>
          </VStack>
        </CardBody>
      </Card>
    );
  }

  // Build chart data showing user's value alongside age group medians
  const chartData = data.all_age_groups.map((g) => ({
    label: g.age_group_label,
    median: g.median,
    isUserGroup: g.age_group === data.age_group,
    userValue: g.age_group === data.age_group ? data.user_net_worth : null,
  }));

  return (
    <Card h="100%">
      <CardBody>
        <VStack align="stretch" spacing={4}>
          {/* Header */}
          <HStack justify="space-between" align="start">
            <VStack align="start" spacing={0}>
              <Text fontWeight="semibold" fontSize="md">
                Net Worth vs. Peers
              </Text>
              <Text fontSize="xs" color="text.muted">
                Age group: {data.age_group_label} · Federal Reserve SCF 2022
              </Text>
            </VStack>
            <Tooltip
              label={`You are in approximately the ${data.percentile}th percentile for your age group`}
              hasArrow
            >
              <Badge
                colorScheme={percentileColor(data.percentile)}
                fontSize="sm"
                px={2}
                py={1}
                borderRadius="md"
                cursor="default"
              >
                Top {100 - data.percentile}%
              </Badge>
            </Tooltip>
          </HStack>

          {/* Percentile progress bar */}
          <Box>
            <HStack justify="space-between" mb={1}>
              <Text fontSize="xs" color="text.muted">
                Percentile rank in your age group
              </Text>
              <Text fontSize="xs" fontWeight="bold">
                {data.percentile}th
              </Text>
            </HStack>
            <Progress
              value={data.percentile}
              colorScheme={percentileColor(data.percentile)}
              size="md"
              borderRadius="full"
              bg="bg.subtle"
            />
            <HStack justify="space-between" mt={1}>
              <Text fontSize="xs" color="text.muted">
                0th
              </Text>
              <Text fontSize="xs" color="text.muted">
                50th (median)
              </Text>
              <Text fontSize="xs" color="text.muted">
                100th
              </Text>
            </HStack>
          </Box>

          {/* Key numbers */}
          <HStack spacing={4}>
            <VStack align="start" spacing={0} flex={1}>
              <Text fontSize="xs" color="text.muted">
                Your Net Worth
              </Text>
              <Text fontWeight="bold" fontSize="sm">
                {fmt(data.user_net_worth)}
              </Text>
            </VStack>
            <VStack align="start" spacing={0} flex={1}>
              <Text fontSize="xs" color="text.muted">
                Median (age {data.age_group_label})
              </Text>
              <Text fontWeight="bold" fontSize="sm">
                {fmt(data.median_net_worth)}
              </Text>
            </VStack>
            <VStack align="start" spacing={0} flex={1}>
              <Text fontSize="xs" color="text.muted">
                75th Percentile
              </Text>
              <Text fontWeight="bold" fontSize="sm">
                {fmt(data.p75)}
              </Text>
            </VStack>
          </HStack>

          {/* Age group comparison chart */}
          <Box>
            <Text fontSize="xs" color="text.muted" mb={2}>
              Median net worth by age group
            </Text>
            <ResponsiveContainer width="100%" height={120}>
              <BarChart
                data={chartData}
                margin={{ top: 0, right: 0, left: 0, bottom: 0 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  opacity={0.3}
                />
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis hide />
                <RechartsTooltip
                  formatter={(value: number) => [fmt(value), "Median"]}
                  contentStyle={{ fontSize: 12 }}
                />
                <Bar dataKey="median" radius={[3, 3, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell
                      key={index}
                      fill={
                        entry.isUserGroup
                          ? "var(--chakra-colors-brand-400, #4299E1)"
                          : "var(--chakra-colors-gray-300, #CBD5E0)"
                      }
                      opacity={entry.isUserGroup ? 1 : 0.6}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Box>

          {/* Next milestone */}
          {data.next_milestone_label && data.next_milestone_value && (
            <Box
              p={3}
              borderRadius="md"
              bg="bg.subtle"
              borderLeft="3px solid"
              borderColor="brand.400"
            >
              <Text fontSize="xs" color="text.muted">
                Next milestone: {data.next_milestone_label}
              </Text>
              <Text fontSize="sm" fontWeight="semibold" mt={0.5}>
                {fmt(data.next_milestone_value)}
                {data.gap_to_next_milestone && (
                  <Text
                    as="span"
                    fontWeight="normal"
                    color="text.muted"
                    fontSize="xs"
                    ml={1}
                  >
                    ({fmt(data.gap_to_next_milestone)} away)
                  </Text>
                )}
              </Text>
            </Box>
          )}

          {data.percentile >= 90 && (
            <Text fontSize="xs" color="green.500" fontWeight="medium">
              🎉 You're in the top 10% for your age group!
            </Text>
          )}
        </VStack>
      </CardBody>
    </Card>
  );
};

export const NetWorthBenchmarkWidget = memo(NetWorthBenchmarkWidgetBase);
