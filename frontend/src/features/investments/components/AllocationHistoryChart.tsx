/**
 * AllocationHistoryChart — stacked area chart showing how portfolio allocation
 * percentages (Stocks, ETFs, Bonds, Mutual Funds, Cash, Other) have changed
 * over time, sourced from daily portfolio snapshots.
 */

import React from "react";
import { Box, Text, Select, HStack, VStack } from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { holdingsApi } from "../../../api/holdings";

const COLORS = {
  stocks: "#4299E1", // blue
  etf: "#48BB78", // green
  bonds: "#ECC94B", // yellow
  mutual_funds: "#9F7AEA", // purple
  cash: "#68D391", // light green
  other: "#CBD5E0", // gray
};

interface Props {
  userId?: string | null;
}

export const AllocationHistoryChart: React.FC<Props> = ({ userId }) => {
  const [months, setMonths] = React.useState(12);

  const { data = [], isLoading } = useQuery({
    queryKey: ["allocation-history", months, userId ?? null],
    queryFn: () =>
      holdingsApi.getAllocationHistory(months, userId ?? undefined),
    staleTime: 5 * 60_000,
  });

  if (isLoading) {
    return (
      <Box p={4} textAlign="center">
        <Text color="text.muted" fontSize="sm">
          Loading allocation history...
        </Text>
      </Box>
    );
  }

  if (data.length === 0) {
    return (
      <Box p={4} textAlign="center">
        <Text color="text.muted" fontSize="sm">
          Allocation history will appear here after your portfolio has been
          tracked for a few days.
        </Text>
      </Box>
    );
  }

  // Format data for recharts — dates as short labels
  const chartData = data.map((d) => ({
    date: new Date(d.snapshot_date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
    Stocks: parseFloat(d.stocks_pct.toFixed(1)),
    ETFs: parseFloat(d.etf_pct.toFixed(1)),
    Bonds: parseFloat(d.bonds_pct.toFixed(1)),
    "Mutual Funds": parseFloat(d.mutual_funds_pct.toFixed(1)),
    Cash: parseFloat(d.cash_pct.toFixed(1)),
    Other: parseFloat(d.other_pct.toFixed(1)),
  }));

  return (
    <VStack align="stretch" spacing={3}>
      <HStack justify="space-between">
        <Text fontWeight="medium" fontSize="sm">
          Allocation Over Time
        </Text>
        <Select
          size="xs"
          value={months}
          onChange={(e) => setMonths(Number(e.target.value))}
          w="120px"
        >
          <option value={3}>3 months</option>
          <option value={6}>6 months</option>
          <option value={12}>1 year</option>
          <option value={24}>2 years</option>
        </Select>
      </HStack>
      <ResponsiveContainer width="100%" height={240}>
        <AreaChart
          data={chartData}
          margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11 }}
            interval="preserveStartEnd"
          />
          <YAxis
            tickFormatter={(v: number) => `${v}%`}
            tick={{ fontSize: 11 }}
            domain={[0, 100]}
          />
          <Tooltip formatter={(v: number) => `${v.toFixed(1)}%`} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Area
            type="monotone"
            dataKey="Stocks"
            stackId="1"
            stroke={COLORS.stocks}
            fill={COLORS.stocks}
            fillOpacity={0.7}
          />
          <Area
            type="monotone"
            dataKey="ETFs"
            stackId="1"
            stroke={COLORS.etf}
            fill={COLORS.etf}
            fillOpacity={0.7}
          />
          <Area
            type="monotone"
            dataKey="Bonds"
            stackId="1"
            stroke={COLORS.bonds}
            fill={COLORS.bonds}
            fillOpacity={0.7}
          />
          <Area
            type="monotone"
            dataKey="Mutual Funds"
            stackId="1"
            stroke={COLORS.mutual_funds}
            fill={COLORS.mutual_funds}
            fillOpacity={0.7}
          />
          <Area
            type="monotone"
            dataKey="Cash"
            stackId="1"
            stroke={COLORS.cash}
            fill={COLORS.cash}
            fillOpacity={0.7}
          />
          <Area
            type="monotone"
            dataKey="Other"
            stackId="1"
            stroke={COLORS.other}
            fill={COLORS.other}
            fillOpacity={0.7}
          />
        </AreaChart>
      </ResponsiveContainer>
    </VStack>
  );
};
