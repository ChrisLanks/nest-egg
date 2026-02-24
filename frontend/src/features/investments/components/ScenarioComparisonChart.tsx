/**
 * Scenario Comparison Chart
 *
 * Overlays 2-3 scenario median lines on a single Recharts ComposedChart.
 * Shows percentile bands only for the active/focused scenario.
 * Draws a vertical dashed line at the retirement year if set.
 */

import { Box, Text, Card, CardBody, useColorModeValue } from '@chakra-ui/react';
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts';
import type { ProjectionResult, SimulationSummary } from '../../../utils/monteCarloSimulation';

export interface ScenarioData {
  name: string;
  color: string;
  summary: SimulationSummary;
}

interface ScenarioComparisonChartProps {
  scenarios: ScenarioData[];
  activeIndex: number; // Which scenario shows percentile bands
  showInflationAdjusted: boolean;
  retirementYear?: number;
}

const SCENARIO_COLORS = ['#4299E1', '#ED8936', '#48BB78'];

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);

export const ScenarioComparisonChart = ({
  scenarios,
  activeIndex,
  showInflationAdjusted,
  retirementYear,
}: ScenarioComparisonChartProps) => {
  const gridColor = useColorModeValue('#e0e0e0', '#4A5568');
  const tooltipBg = useColorModeValue('white', 'gray.700');
  const tooltipBorder = useColorModeValue('gray.200', 'gray.600');

  // Merge all scenario projections into unified data keyed by year
  const maxYears = Math.max(...scenarios.map((s) => s.summary.projections.length));
  const chartData = Array.from({ length: maxYears }, (_, i) => {
    const row: Record<string, number> = { year: i };
    scenarios.forEach((s, si) => {
      const p = s.summary.projections[i];
      if (!p) return;
      const prefix = `s${si}`;
      if (showInflationAdjusted) {
        row[`${prefix}_median`] = p.medianInflationAdjusted;
        row[`${prefix}_p90`] = p.percentile90InflationAdjusted;
        row[`${prefix}_p10`] = p.percentile10InflationAdjusted;
      } else {
        row[`${prefix}_median`] = p.median;
        row[`${prefix}_p90`] = p.percentile90;
        row[`${prefix}_p10`] = p.percentile10;
        row[`${prefix}_p75`] = p.percentile75;
        row[`${prefix}_p25`] = p.percentile25;
      }
    });
    return row;
  });

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <Card size="sm" bg={tooltipBg} borderColor={tooltipBorder} borderWidth={1}>
        <CardBody py={2} px={3}>
          <Text fontWeight="bold" mb={1}>
            Year {label}
          </Text>
          {scenarios.map((s, si) => {
            const medianKey = `s${si}_median`;
            const entry = payload.find((p: any) => p.dataKey === medianKey);
            if (!entry) return null;
            return (
              <Text key={si} fontSize="sm" color={s.color || SCENARIO_COLORS[si]}>
                {s.name}: {formatCurrency(entry.value)}
              </Text>
            );
          })}
        </CardBody>
      </Card>
    );
  };

  const ap = `s${activeIndex}`; // Active prefix for bands

  return (
    <Box>
      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis
            dataKey="year"
            label={{ value: 'Years', position: 'insideBottom', offset: -5 }}
          />
          <YAxis
            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
            label={{ value: 'Portfolio Value', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />

          {/* Retirement year marker */}
          {retirementYear != null && (
            <ReferenceLine
              x={retirementYear}
              stroke="#A0AEC0"
              strokeDasharray="6 4"
              label={{ value: 'Retirement', position: 'top', fill: '#A0AEC0' }}
            />
          )}

          {/* Percentile bands for active scenario only */}
          <Area
            type="monotone"
            dataKey={`${ap}_p90`}
            stroke="transparent"
            fill={scenarios[activeIndex]?.color || SCENARIO_COLORS[activeIndex]}
            fillOpacity={0.1}
            name=""
            legendType="none"
          />
          <Area
            type="monotone"
            dataKey={`${ap}_p10`}
            stroke="transparent"
            fill={scenarios[activeIndex]?.color || SCENARIO_COLORS[activeIndex]}
            fillOpacity={0.05}
            name=""
            legendType="none"
          />

          {/* Median line for each scenario */}
          {scenarios.map((s, si) => (
            <Line
              key={si}
              type="monotone"
              dataKey={`s${si}_median`}
              stroke={s.color || SCENARIO_COLORS[si]}
              strokeWidth={si === activeIndex ? 3 : 2}
              strokeDasharray={si === activeIndex ? undefined : '5 5'}
              name={s.name}
              dot={false}
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </Box>
  );
};
