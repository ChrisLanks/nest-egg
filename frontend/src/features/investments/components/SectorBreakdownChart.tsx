/**
 * Sector Breakdown Chart Component
 *
 * Displays portfolio holdings grouped by financial sector.
 * Phase 1: Uses heuristic classification
 * Phase 2: Will use real sector data from Alpha Vantage API
 */

import {
  Box,
  Alert,
  AlertIcon,
  AlertDescription,
  Text,
  HStack,
  Badge,
} from '@chakra-ui/react';
import { useMemo } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  Legend,
} from 'recharts';
import { aggregateBySector } from '../../../utils/sectorClassification';

// Sector colors for visualization
const SECTOR_COLORS: Record<string, string> = {
  'Technology': '#4299E1',
  'Financials': '#48BB78',
  'Healthcare': '#ED8936',
  'Consumer Discretionary': '#9F7AEA',
  'Consumer Staples': '#F56565',
  'Energy': '#ECC94B',
  'Industrials': '#38B2AC',
  'Communication Services': '#ED64A6',
  'Utilities': '#667EEA',
  'Real Estate': '#FC8181',
  'Materials': '#90CDF4',
  'Broad Market ETF': '#CBD5E0',
  'Diversified ETF': '#CBD5E0',
  'Diversified Fund': '#A0AEC0',
  'Bond ETF': '#718096',
  'Fixed Income': '#718096',
  'Cash & Equivalents': '#E2E8F0',
  'Other': '#A0AEC0',
};

interface Holding {
  ticker: string;
  name: string | null;
  asset_type: string | null;
  current_total_value: number | null;
  sector?: string | null; // From API in Phase 2
  industry?: string | null; // From API in Phase 2
}

interface ApiSectorBreakdown {
  sector: string;
  value: number;
  count: number;
  percentage: number;
}

interface SectorBreakdownChartProps {
  holdings: Holding[];
  sectorBreakdown?: ApiSectorBreakdown[] | null; // From API in Phase 2
}

export const SectorBreakdownChart = ({ holdings, sectorBreakdown }: SectorBreakdownChartProps) => {
  // Determine if we're using real API data or heuristics
  const isRealData = sectorBreakdown && sectorBreakdown.length > 0;

  // Calculate sector breakdown
  const chartData = useMemo(() => {
    if (isRealData) {
      // Phase 2: Use real API data
      return sectorBreakdown
        .map((s) => ({
          sector: s.sector,
          value: Number(s.value),
          count: s.count,
          percentage: Number(s.percentage),
        }))
        .sort((a, b) => b.value - a.value);
    } else {
      // Phase 1: Use heuristic classification
      return aggregateBySector(holdings);
    }
  }, [holdings, sectorBreakdown, isRealData]);

  // Format currency
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <Box
          bg="bg.surface"
          p={3}
          border="1px"
          borderColor="border.default"
          borderRadius="md"
          shadow="md"
        >
          <Text fontWeight="bold" mb={1}>
            {data.sector}
          </Text>
          <Text fontSize="sm" color="text.secondary">
            Value: {formatCurrency(data.value)}
          </Text>
          <Text fontSize="sm" color="text.secondary">
            {data.percentage.toFixed(1)}% of portfolio
          </Text>
          <Text fontSize="sm" color="text.secondary">
            {data.count} holding{data.count !== 1 ? 's' : ''}
          </Text>
        </Box>
      );
    }
    return null;
  };

  return (
    <Box>
      {/* Sector breakdown heading */}
      <HStack justify="space-between" mb={4}>
        <Text fontSize="lg" fontWeight="semibold">
          Portfolio by Sector
        </Text>
      </HStack>

      {/* Empty state */}
      {chartData.length === 0 ? (
        <Box textAlign="center" py={10} color="text.muted">
          <Text>No sector data available</Text>
        </Box>
      ) : (
        <>
          {/* Horizontal Bar Chart */}
          <ResponsiveContainer width="100%" height={Math.max(400, chartData.length * 50)}>
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ top: 5, right: 30, left: 150, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
              <XAxis
                type="number"
                tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
              />
              <YAxis type="category" dataKey="sector" width={140} />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Bar dataKey="value" name="Total Value" radius={[0, 8, 8, 0]}>
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={SECTOR_COLORS[entry.sector] || SECTOR_COLORS['Other']}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>

          {/* Summary table */}
          <Box mt={6} overflowX="auto">
            <table style={{ width: '100%', fontSize: '14px' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e2e8f0' }}>
                  <th style={{ textAlign: 'left', padding: '8px' }}>Sector</th>
                  <th style={{ textAlign: 'right', padding: '8px' }}>Value</th>
                  <th style={{ textAlign: 'right', padding: '8px' }}>% of Portfolio</th>
                  <th style={{ textAlign: 'right', padding: '8px' }}>Holdings</th>
                </tr>
              </thead>
              <tbody>
                {chartData.map((sector, index) => (
                  <tr
                    key={index}
                    style={{
                      borderBottom: '1px solid #e2e8f0',
                      backgroundColor: index % 2 === 0 ? '#f7fafc' : 'white',
                    }}
                  >
                    <td style={{ padding: '8px' }}>
                      <HStack spacing={2}>
                        <Box
                          w="12px"
                          h="12px"
                          borderRadius="2px"
                          bg={SECTOR_COLORS[sector.sector] || SECTOR_COLORS['Other']}
                        />
                        <Text fontWeight="medium">{sector.sector}</Text>
                      </HStack>
                    </td>
                    <td style={{ textAlign: 'right', padding: '8px', fontWeight: 600 }}>
                      {formatCurrency(sector.value)}
                    </td>
                    <td style={{ textAlign: 'right', padding: '8px' }}>
                      {sector.percentage.toFixed(1)}%
                    </td>
                    <td style={{ textAlign: 'right', padding: '8px', color: '#718096' }}>
                      {sector.count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Box>

          {/* Insights */}
          {chartData.length > 0 && (
            <Box mt={4} p={4} bg="bg.info" borderRadius="md">
              <Text fontSize="sm" color="text.heading">
                <strong>Diversification Insight:</strong> Your portfolio is most
                concentrated in <strong>{chartData[0].sector}</strong> (
                {chartData[0].percentage.toFixed(1)}%). Consider rebalancing if any
                single sector exceeds 25-30% to reduce concentration risk.
              </Text>
            </Box>
          )}
        </>
      )}
    </Box>
  );
};
