/**
 * Side-by-side scenario comparison view.
 * Overlays fan charts of 2-3 scenarios for comparison.
 */

import {
  Badge,
  Box,
  HStack,
  SimpleGrid,
  Text,
  useColorModeValue,
  VStack,
} from '@chakra-ui/react';
import {
  Area,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useMemo } from 'react';
import type { ScenarioComparisonItem } from '../types/retirement';

const SCENARIO_COLORS = ['#4299E1', '#ED8936', '#48BB78'];

interface ScenarioComparisonViewProps {
  scenarios: ScenarioComparisonItem[];
}

export function ScenarioComparisonView({ scenarios }: ScenarioComparisonViewProps) {
  const bgColor = useColorModeValue('white', 'gray.800');
  const labelColor = useColorModeValue('gray.500', 'gray.400');

  const formatCurrency = (value: number) => {
    if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
    if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
    return `$${value.toFixed(0)}`;
  };

  // Merge projections from all scenarios into a single dataset
  const chartData = useMemo(() => {
    if (!scenarios.length) return [];

    // Find the maximum age range across all scenarios
    const allAges = new Set<number>();
    scenarios.forEach((s) => s.projections.forEach((p) => allAges.add(p.age)));
    const sortedAges = Array.from(allAges).sort((a, b) => a - b);

    return sortedAges.map((age) => {
      const row: Record<string, number> = { age };
      scenarios.forEach((s, i) => {
        const point = s.projections.find((p) => p.age === age);
        if (point) {
          row[`s${i}_p50`] = point.p50;
          row[`s${i}_p10`] = point.p10;
          row[`s${i}_p90`] = point.p90;
        }
      });
      return row;
    });
  }, [scenarios]);

  if (scenarios.length < 2) return null;

  return (
    <Box bg={bgColor} p={5} borderRadius="xl" shadow="sm">
      <VStack spacing={4} align="stretch">
        <Text fontSize="lg" fontWeight="semibold">
          Scenario Comparison
        </Text>

        {/* Summary cards */}
        <SimpleGrid columns={{ base: 1, md: scenarios.length }} spacing={3}>
          {scenarios.map((s, i) => (
            <Box
              key={s.scenario_id}
              p={3}
              borderRadius="md"
              border="2px solid"
              borderColor={SCENARIO_COLORS[i]}
            >
              <VStack spacing={1} align="stretch">
                <HStack justify="space-between">
                  <Text fontSize="sm" fontWeight="bold" color={SCENARIO_COLORS[i]}>
                    {s.scenario_name}
                  </Text>
                  <Badge colorScheme={s.readiness_score >= 70 ? 'green' : s.readiness_score >= 40 ? 'yellow' : 'red'}>
                    {s.readiness_score}
                  </Badge>
                </HStack>
                <HStack justify="space-between" fontSize="xs">
                  <Text color={labelColor}>Success Rate</Text>
                  <Text fontWeight="medium">{s.success_rate.toFixed(1)}%</Text>
                </HStack>
                <HStack justify="space-between" fontSize="xs">
                  <Text color={labelColor}>Retire at</Text>
                  <Text fontWeight="medium">{s.retirement_age}</Text>
                </HStack>
                {s.median_portfolio_at_end !== null && (
                  <HStack justify="space-between" fontSize="xs">
                    <Text color={labelColor}>End Portfolio</Text>
                    <Text fontWeight="medium">{formatCurrency(s.median_portfolio_at_end)}</Text>
                  </HStack>
                )}
              </VStack>
            </Box>
          ))}
        </SimpleGrid>

        {/* Overlay chart */}
        <Box h="350px">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData}>
              <XAxis
                dataKey="age"
                tick={{ fontSize: 11 }}
                label={{ value: 'Age', position: 'insideBottom', offset: -5, fontSize: 12 }}
              />
              <YAxis
                tickFormatter={(v) => formatCurrency(v)}
                tick={{ fontSize: 11 }}
                width={65}
              />
              <Tooltip
                formatter={(value: number, name: string) => {
                  const idx = parseInt(name.split('_')[0].replace('s', ''), 10);
                  const scenarioName = scenarios[idx]?.scenario_name || `Scenario ${idx + 1}`;
                  return [formatCurrency(value), `${scenarioName} (Median)`];
                }}
                labelFormatter={(age) => `Age ${age}`}
              />
              <Legend />

              {/* Show p10-p90 band only for first scenario */}
              <Area
                type="monotone"
                dataKey="s0_p90"
                stroke="none"
                fill={SCENARIO_COLORS[0]}
                fillOpacity={0.1}
                name="s0_p90_area"
                legendType="none"
              />
              <Area
                type="monotone"
                dataKey="s0_p10"
                stroke="none"
                fill="white"
                fillOpacity={1}
                name="s0_p10_area"
                legendType="none"
              />

              {/* Median lines for all scenarios */}
              {scenarios.map((s, i) => (
                <Line
                  key={s.scenario_id}
                  type="monotone"
                  dataKey={`s${i}_p50`}
                  stroke={SCENARIO_COLORS[i]}
                  strokeWidth={2}
                  dot={false}
                  name={`s${i}_p50`}
                  legendType="none"
                />
              ))}
            </ComposedChart>
          </ResponsiveContainer>
        </Box>
      </VStack>
    </Box>
  );
}
