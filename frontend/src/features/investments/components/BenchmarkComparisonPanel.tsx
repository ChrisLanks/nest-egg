/**
 * BenchmarkComparisonPanel
 *
 * Compares the user's portfolio total return against market benchmark indices.
 * Benchmark price history is fetched live from /market-data/historical/{symbol}.
 * No data is hardcoded — benchmark returns are computed from actual price data.
 */

import { useState, useMemo } from "react";
import {
  Box,
  Card,
  CardBody,
  Heading,
  HStack,
  VStack,
  Text,
  Badge,
  Button,
  ButtonGroup,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Spinner,
  Alert,
  AlertIcon,
  Select,
  Tooltip,
} from "@chakra-ui/react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { useQuery } from "@tanstack/react-query";
import { format, subMonths, subYears, parseISO } from "date-fns";
import api from "../../../services/api";

// ── Types ─────────────────────────────────────────────────────────────────────

interface PortfolioSnapshot {
  snapshot_date: string;
  total_net_worth: number;
  investments: number;
}

interface HistoricalPrice {
  date: string;
  close: number;
  adjusted_close?: number;
}

type TimeRange = "1M" | "3M" | "6M" | "1Y" | "3Y";

interface Benchmark {
  symbol: string;
  label: string;
  color: string;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const BENCHMARKS: Benchmark[] = [
  { symbol: "SPY", label: "S&P 500 (SPY)", color: "#3182CE" },
  { symbol: "QQQ", label: "NASDAQ 100 (QQQ)", color: "#805AD5" },
  { symbol: "AGG", label: "US Bonds (AGG)", color: "#38A169" },
  { symbol: "VT", label: "Global Stocks (VT)", color: "#DD6B20" },
];

const TIME_RANGES: { label: string; value: TimeRange }[] = [
  { label: "1M", value: "1M" },
  { label: "3M", value: "3M" },
  { label: "6M", value: "6M" },
  { label: "1Y", value: "1Y" },
  { label: "3Y", value: "3Y" },
];

function rangeStartDate(range: TimeRange): Date {
  const now = new Date();
  switch (range) {
    case "1M": return subMonths(now, 1);
    case "3M": return subMonths(now, 3);
    case "6M": return subMonths(now, 6);
    case "1Y": return subYears(now, 1);
    case "3Y": return subYears(now, 3);
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Index a price series to 100 at the first data point */
function indexSeries(prices: { date: string; value: number }[]): { date: string; value: number }[] {
  if (prices.length === 0) return [];
  const base = prices[0].value;
  if (!base) return prices;
  return prices.map((p) => ({ date: p.date, value: (p.value / base) * 100 }));
}

function fmtPct(n: number): string {
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}

// ── Component ─────────────────────────────────────────────────────────────────

interface BenchmarkComparisonPanelProps {
  userId?: string | null;
}

export function BenchmarkComparisonPanel({ userId }: BenchmarkComparisonPanelProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>("1Y");
  const [selectedBenchmarks, setSelectedBenchmarks] = useState<string[]>(["SPY", "AGG"]);

  const startDate = rangeStartDate(timeRange);
  const endDate = new Date();
  const startStr = format(startDate, "yyyy-MM-dd");
  const endStr = format(endDate, "yyyy-MM-dd");

  // ── Portfolio snapshots ───────────────────────────────────────────────────

  const { data: snapshots, isLoading: snapshotsLoading } = useQuery<PortfolioSnapshot[]>({
    queryKey: ["portfolio-snapshots-bench", userId, startStr],
    queryFn: async () => {
      const params: Record<string, string> = { start_date: startStr, end_date: endStr };
      if (userId) params.user_id = userId;
      const res = await api.get("/dashboard/net-worth-history", { params });
      return res.data; // returns list[NetWorthHistoryPoint]
    },
    staleTime: 5 * 60 * 1000,
  });

  // ── Benchmark price history ───────────────────────────────────────────────

  const benchmarkQueries = selectedBenchmarks.map((symbol) =>
    // eslint-disable-next-line react-hooks/rules-of-hooks
    useQuery<HistoricalPrice[]>({
      queryKey: ["benchmark-history", symbol, startStr, endStr],
      queryFn: async () => {
        const res = await api.get(`/market-data/historical/${symbol}`, {
          params: { start_date: startStr, end_date: endStr, interval: "1wk" },
        });
        return res.data;
      },
      staleTime: 60 * 60 * 1000, // 1h — benchmark data is stable
      retry: false,
    })
  );

  const benchmarksLoading = benchmarkQueries.some((q) => q.isLoading);

  // ── Build chart series ────────────────────────────────────────────────────

  const chartData = useMemo(() => {
    if (!snapshots || snapshots.length < 2) return null;

    // Index portfolio to 100 — use investments value for apples-to-apples vs equity benchmarks
    const portfolioSeries = snapshots
      .filter((s) => s.snapshot_date >= startStr)
      .map((s) => ({ date: s.snapshot_date.slice(0, 10), value: s.investments > 0 ? s.investments : s.total_net_worth }))
      .sort((a, b) => a.date.localeCompare(b.date));

    const indexedPortfolio = indexSeries(portfolioSeries);

    // Build a map by date for each benchmark
    const benchmarkMaps: Record<string, Record<string, number>> = {};
    selectedBenchmarks.forEach((symbol, i) => {
      const data = benchmarkQueries[i]?.data;
      if (!data) return;
      const series = data.map((p) => ({
        date: p.date.slice(0, 10),
        value: p.adjusted_close ?? p.close,
      })).sort((a, b) => a.date.localeCompare(b.date));
      const indexed = indexSeries(series);
      benchmarkMaps[symbol] = Object.fromEntries(indexed.map((p) => [p.date, p.value]));
    });

    // Merge onto portfolio dates
    return indexedPortfolio.map((p) => {
      const row: Record<string, number | string> = { date: p.date, Portfolio: p.value };
      for (const symbol of selectedBenchmarks) {
        if (benchmarkMaps[symbol]?.[p.date] != null) {
          row[symbol] = benchmarkMaps[symbol][p.date];
        }
      }
      return row;
    });
  }, [snapshots, benchmarkQueries, selectedBenchmarks, startStr]);

  // ── Summary returns ───────────────────────────────────────────────────────

  const returns = useMemo(() => {
    if (!chartData || chartData.length < 2) return null;
    const first = chartData[0];
    const last = chartData[chartData.length - 1];
    const result: Record<string, number> = {};
    result["Portfolio"] = (last["Portfolio"] as number) - 100;
    for (const symbol of selectedBenchmarks) {
      if (last[symbol] != null && first[symbol] != null) {
        result[symbol] = (last[symbol] as number) - 100;
      }
    }
    return result;
  }, [chartData, selectedBenchmarks]);

  const toggleBenchmark = (symbol: string) => {
    setSelectedBenchmarks((prev) =>
      prev.includes(symbol) ? prev.filter((s) => s !== symbol) : [...prev, symbol]
    );
  };

  const isLoading = snapshotsLoading || benchmarksLoading;

  if (isLoading) {
    return (
      <Card>
        <CardBody display="flex" alignItems="center" justifyContent="center" minH="200px">
          <Spinner />
        </CardBody>
      </Card>
    );
  }

  if (!snapshots || snapshots.length < 2) {
    return (
      <Card>
        <CardBody>
          <Heading size="md" mb={2}>Benchmark Comparison</Heading>
          <Alert status="info" borderRadius="md">
            <AlertIcon />
            Not enough portfolio history to compare. Portfolio snapshots are recorded
            as prices update — check back after a few weeks.
          </Alert>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card>
      <CardBody>
        <VStack align="stretch" spacing={4}>
          <HStack justify="space-between" wrap="wrap" gap={2}>
            <Heading size="md">Benchmark Comparison</Heading>
            <ButtonGroup size="sm" variant="outline" isAttached>
              {TIME_RANGES.map((r) => (
                <Button
                  key={r.value}
                  onClick={() => setTimeRange(r.value)}
                  colorScheme={timeRange === r.value ? "brand" : undefined}
                  variant={timeRange === r.value ? "solid" : "outline"}
                >
                  {r.label}
                </Button>
              ))}
            </ButtonGroup>
          </HStack>

          {/* Benchmark selector */}
          <HStack spacing={2} wrap="wrap">
            <Text fontSize="sm" color="text.secondary">Compare vs:</Text>
            {BENCHMARKS.map((b) => (
              <Tooltip key={b.symbol} label={b.label}>
                <Badge
                  cursor="pointer"
                  colorScheme={selectedBenchmarks.includes(b.symbol) ? "blue" : "gray"}
                  variant={selectedBenchmarks.includes(b.symbol) ? "solid" : "outline"}
                  onClick={() => toggleBenchmark(b.symbol)}
                  px={2}
                  py={1}
                >
                  {b.symbol}
                </Badge>
              </Tooltip>
            ))}
          </HStack>

          {/* Return summary cards */}
          {returns && (
            <SimpleGrid columns={{ base: 2, md: 4 }} spacing={3}>
              <Card variant="outline" borderColor="brand.500">
                <CardBody py={2} px={3}>
                  <Stat size="sm">
                    <StatLabel>Your Portfolio</StatLabel>
                    <StatNumber
                      fontSize="lg"
                      color={returns["Portfolio"] >= 0 ? "finance.positive" : "finance.negative"}
                    >
                      {fmtPct(returns["Portfolio"])}
                    </StatNumber>
                    <StatHelpText mb={0}>{timeRange} return</StatHelpText>
                  </Stat>
                </CardBody>
              </Card>
              {selectedBenchmarks.map((symbol) => {
                const bm = BENCHMARKS.find((b) => b.symbol === symbol);
                const ret = returns[symbol];
                if (ret == null || !bm) return null;
                const outperform = returns["Portfolio"] - ret;
                return (
                  <Card key={symbol} variant="outline">
                    <CardBody py={2} px={3}>
                      <Stat size="sm">
                        <StatLabel>{bm.symbol}</StatLabel>
                        <StatNumber fontSize="lg">{fmtPct(ret)}</StatNumber>
                        <StatHelpText mb={0} color={outperform >= 0 ? "green.500" : "red.500"}>
                          You {outperform >= 0 ? "beat by" : "lag by"} {Math.abs(outperform).toFixed(1)}%
                        </StatHelpText>
                      </Stat>
                    </CardBody>
                  </Card>
                );
              })}
            </SimpleGrid>
          )}

          {/* Chart */}
          {chartData && chartData.length > 1 ? (
            <Box h="260px">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11 }}
                    tickFormatter={(d) => {
                      try { return format(parseISO(d), timeRange === "3Y" ? "MMM yy" : "MMM d"); }
                      catch { return d; }
                    }}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v) => `${(v - 100).toFixed(0)}%`}
                    domain={["auto", "auto"]}
                  />
                  <RechartsTooltip
                    formatter={(value: number, name: string) => [
                      `${(value - 100).toFixed(2)}%`,
                      name === "Portfolio" ? "Your Portfolio" :
                        BENCHMARKS.find((b) => b.symbol === name)?.label ?? name,
                    ]}
                    labelFormatter={(label) => {
                      try { return format(parseISO(label as string), "MMM d, yyyy"); }
                      catch { return label; }
                    }}
                  />
                  <Legend
                    formatter={(value) =>
                      value === "Portfolio" ? "Your Portfolio" :
                        BENCHMARKS.find((b) => b.symbol === value)?.label ?? value
                    }
                  />
                  <Line
                    type="monotone"
                    dataKey="Portfolio"
                    stroke="#E53E3E"
                    strokeWidth={2.5}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                  {selectedBenchmarks.map((symbol) => {
                    const bm = BENCHMARKS.find((b) => b.symbol === symbol);
                    return (
                      <Line
                        key={symbol}
                        type="monotone"
                        dataKey={symbol}
                        stroke={bm?.color ?? "#718096"}
                        strokeWidth={1.5}
                        strokeDasharray="4 2"
                        dot={false}
                        activeDot={{ r: 3 }}
                        connectNulls
                      />
                    );
                  })}
                </LineChart>
              </ResponsiveContainer>
            </Box>
          ) : (
            <Alert status="info" borderRadius="md">
              <AlertIcon />
              No overlapping data for this time range. Try a shorter period.
            </Alert>
          )}

          <Text fontSize="xs" color="text.muted">
            All series indexed to 100 at start of period. Benchmark data from market data provider.
            Past performance does not guarantee future results.
          </Text>
        </VStack>
      </CardBody>
    </Card>
  );
}
