/**
 * Monte Carlo fan chart showing portfolio value projections over age.
 * Percentile bands (p10-p90) with median line and retirement age marker.
 */

import { Box, Text, useColorModeValue } from '@chakra-ui/react';
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { ProjectionDataPoint } from '../types/retirement';

interface RetirementFanChartProps {
  projections: ProjectionDataPoint[];
  retirementAge: number;
  socialSecurityStartAge?: number;
  isLoading?: boolean;
}

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;

  const data = payload[0]?.payload as ProjectionDataPoint;
  if (!data) return null;

  return (
    <Box bg="gray.800" color="white" p={3} borderRadius="md" fontSize="sm" shadow="lg">
      <Text fontWeight="bold" mb={1}>Age {data.age}</Text>
      <Text>90th: {formatCurrency(data.p90)}</Text>
      <Text>75th: {formatCurrency(data.p75)}</Text>
      <Text fontWeight="bold">Median: {formatCurrency(data.p50)}</Text>
      <Text>25th: {formatCurrency(data.p25)}</Text>
      <Text>10th: {formatCurrency(data.p10)}</Text>
      {data.depletion_pct > 0 && (
        <Text color="red.300" mt={1}>
          {data.depletion_pct.toFixed(0)}% depleted
        </Text>
      )}
    </Box>
  );
}

export function RetirementFanChart({
  projections,
  retirementAge,
  socialSecurityStartAge,
  isLoading,
}: RetirementFanChartProps) {
  const bgColor = useColorModeValue('white', 'gray.800');
  const gridColor = useColorModeValue('#E2E8F0', '#2D3748');
  const textColor = useColorModeValue('#718096', '#A0AEC0');

  if (isLoading || !projections.length) {
    return (
      <Box bg={bgColor} p={6} borderRadius="xl" shadow="sm" h="400px">
        <Text color={textColor} textAlign="center" pt="150px">
          {isLoading ? 'Running simulation...' : 'No projection data yet'}
        </Text>
      </Box>
    );
  }

  // Prepare chart data with band areas
  const chartData = projections.map((p) => ({
    ...p,
    // For stacked area bands: recharts needs base + top for each band
    band_p10_p25: p.p25 - p.p10,
    band_p25_p75: p.p75 - p.p25,
    band_p75_p90: p.p90 - p.p75,
    base_p10: p.p10,
  }));

  return (
    <Box bg={bgColor} p={4} borderRadius="xl" shadow="sm">
      <Text fontSize="md" fontWeight="semibold" mb={3} color={textColor}>
        Portfolio Projection
      </Text>
      <ResponsiveContainer width="100%" height={380}>
        <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis
            dataKey="age"
            label={{ value: 'Age', position: 'insideBottom', offset: -5, fill: textColor }}
            stroke={textColor}
            tick={{ fill: textColor, fontSize: 12 }}
          />
          <YAxis
            tickFormatter={formatCurrency}
            stroke={textColor}
            tick={{ fill: textColor, fontSize: 12 }}
            width={70}
          />
          <Tooltip content={<CustomTooltip />} />

          {/* Invisible base area for stacking */}
          <Area
            type="monotone"
            dataKey="base_p10"
            stackId="band"
            fill="transparent"
            stroke="none"
          />

          {/* 10th-25th percentile band */}
          <Area
            type="monotone"
            dataKey="band_p10_p25"
            stackId="band"
            fill="#FC8181"
            fillOpacity={0.15}
            stroke="none"
            name="10th-25th"
          />

          {/* 25th-75th percentile band (main band) */}
          <Area
            type="monotone"
            dataKey="band_p25_p75"
            stackId="band"
            fill="#4299E1"
            fillOpacity={0.2}
            stroke="none"
            name="25th-75th"
          />

          {/* 75th-90th percentile band */}
          <Area
            type="monotone"
            dataKey="band_p75_p90"
            stackId="band"
            fill="#48BB78"
            fillOpacity={0.15}
            stroke="none"
            name="75th-90th"
          />

          {/* Median line */}
          <Line
            type="monotone"
            dataKey="p50"
            stroke="#3182CE"
            strokeWidth={2.5}
            dot={false}
            name="Median"
          />

          {/* 10th percentile line (dashed) */}
          <Line
            type="monotone"
            dataKey="p10"
            stroke="#FC8181"
            strokeWidth={1}
            strokeDasharray="4 4"
            dot={false}
            name="10th Percentile"
          />

          {/* 90th percentile line (dashed) */}
          <Line
            type="monotone"
            dataKey="p90"
            stroke="#48BB78"
            strokeWidth={1}
            strokeDasharray="4 4"
            dot={false}
            name="90th Percentile"
          />

          {/* Retirement age marker */}
          <ReferenceLine
            x={retirementAge}
            stroke="#ED8936"
            strokeWidth={2}
            strokeDasharray="6 3"
            label={{
              value: 'Retire',
              position: 'top',
              fill: '#ED8936',
              fontSize: 12,
            }}
          />

          {/* Social Security start marker */}
          {socialSecurityStartAge && (
            <ReferenceLine
              x={socialSecurityStartAge}
              stroke="#9F7AEA"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              label={{
                value: 'SS',
                position: 'top',
                fill: '#9F7AEA',
                fontSize: 11,
              }}
            />
          )}

          {/* Medicare at 65 marker */}
          {projections.some((p) => p.age === 65) && (
            <ReferenceLine
              x={65}
              stroke="#38B2AC"
              strokeWidth={1}
              strokeDasharray="3 3"
              label={{
                value: 'Medicare',
                position: 'insideTopRight',
                fill: '#38B2AC',
                fontSize: 10,
              }}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </Box>
  );
}
