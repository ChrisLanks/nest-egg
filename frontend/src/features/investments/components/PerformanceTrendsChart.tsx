import { useState, useMemo } from 'react';
import {
  Box,
  HStack,
  VStack,
  Button,
  ButtonGroup,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  SimpleGrid,
  Text,
  useColorModeValue,
  Spinner,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
} from '@chakra-ui/react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { useQuery } from '@tanstack/react-query';
import { format, subMonths, subYears } from 'date-fns';
import api from '../../../services/api';

interface Snapshot {
  id: string;
  organization_id: string;
  snapshot_date: string;
  total_value: number;
  total_cost_basis?: number;
  total_gain_loss?: number;
  total_gain_loss_percent?: number;
  created_at: string;
}

type TimeRange = '1M' | '3M' | '6M' | '1Y' | 'ALL';

interface PerformanceTrendsChartProps {
  currentValue: number;
}

// Generate mock snapshots for development/testing
const generateMockSnapshots = (currentValue: number, months: number = 12): Snapshot[] => {
  const snapshots: Snapshot[] = [];
  const today = new Date();

  for (let i = months; i >= 0; i--) {
    const date = subMonths(today, i);
    // 7% annualized growth with some volatility
    const monthsFactor = i / 12;
    const growthFactor = Math.pow(1.07, monthsFactor);
    const volatility = (Math.random() - 0.5) * 0.1; // ±5% random
    const value = currentValue * growthFactor * (1 + volatility);
    const costBasis = value * 0.85; // Assume 15% gain on average

    snapshots.push({
      id: `mock-${i}`,
      organization_id: 'mock-org',
      snapshot_date: format(date, 'yyyy-MM-dd'),
      total_value: value,
      total_cost_basis: costBasis,
      total_gain_loss: value - costBasis,
      total_gain_loss_percent: ((value - costBasis) / costBasis) * 100,
      created_at: date.toISOString(),
    });
  }

  return snapshots.reverse();
};

export default function PerformanceTrendsChart({ currentValue }: PerformanceTrendsChartProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>('1Y');

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  // Calculate date range
  const { startDate, endDate } = useMemo(() => {
    const end = new Date();
    let start = new Date();

    switch (timeRange) {
      case '1M':
        start = subMonths(end, 1);
        break;
      case '3M':
        start = subMonths(end, 3);
        break;
      case '6M':
        start = subMonths(end, 6);
        break;
      case '1Y':
        start = subYears(end, 1);
        break;
      case 'ALL':
        start = subYears(end, 10); // 10 years max
        break;
    }

    return {
      startDate: format(start, 'yyyy-MM-dd'),
      endDate: format(end, 'yyyy-MM-dd'),
    };
  }, [timeRange]);

  // Fetch historical snapshots
  const { data: snapshots, isLoading, error } = useQuery({
    queryKey: ['portfolio-snapshots', startDate, endDate],
    queryFn: async () => {
      try {
        const response = await api.get(`/holdings/historical`, {
          params: { start_date: startDate, end_date: endDate },
        });

        // If we have real data, use it
        if (response.data && response.data.length > 0) {
          return response.data as Snapshot[];
        }
      } catch (err) {
        console.warn('No historical data available, using mock data');
      }

      // Fall back to mock data
      const months = timeRange === '1M' ? 1 : timeRange === '3M' ? 3 : timeRange === '6M' ? 6 : 12;
      return generateMockSnapshots(currentValue, months);
    },
    staleTime: 15 * 60 * 1000, // 15 minutes
  });

  // Calculate performance metrics
  const metrics = useMemo(() => {
    if (!snapshots || snapshots.length < 2) {
      return {
        totalReturn: 0,
        totalReturnPercent: 0,
        cagr: 0,
        yoyGrowth: 0,
        isPositive: true,
      };
    }

    const firstSnapshot = snapshots[0];
    const lastSnapshot = snapshots[snapshots.length - 1];

    const startValue = firstSnapshot.total_value;
    const endValue = lastSnapshot.total_value;
    const totalReturn = endValue - startValue;
    const totalReturnPercent = (totalReturn / startValue) * 100;

    // Calculate CAGR
    const startDate = new Date(firstSnapshot.snapshot_date);
    const endDate = new Date(lastSnapshot.snapshot_date);
    const years = (endDate.getTime() - startDate.getTime()) / (365.25 * 24 * 60 * 60 * 1000);
    const cagr = years > 0 ? (Math.pow(endValue / startValue, 1 / years) - 1) * 100 : 0;

    // YoY Growth (if we have data >= 1 year apart)
    let yoyGrowth = 0;
    if (years >= 1) {
      const oneYearAgo = new Date(endDate);
      oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);
      const oneYearSnapshot = snapshots.find(s => {
        const snapDate = new Date(s.snapshot_date);
        return Math.abs(snapDate.getTime() - oneYearAgo.getTime()) < 7 * 24 * 60 * 60 * 1000; // Within 7 days
      });

      if (oneYearSnapshot) {
        yoyGrowth = ((endValue - oneYearSnapshot.total_value) / oneYearSnapshot.total_value) * 100;
      }
    }

    return {
      totalReturn,
      totalReturnPercent,
      cagr,
      yoyGrowth,
      isPositive: totalReturn >= 0,
    };
  }, [snapshots]);

  // Prepare chart data
  const chartData = useMemo(() => {
    if (!snapshots) return [];

    return snapshots.map(snapshot => ({
      date: format(new Date(snapshot.snapshot_date), 'MMM dd, yyyy'),
      value: Number(snapshot.total_value),
      costBasis: snapshot.total_cost_basis ? Number(snapshot.total_cost_basis) : undefined,
    }));
  }, [snapshots]);

  const isMockData = snapshots && snapshots.length > 0 && snapshots[0].id.startsWith('mock-');

  if (isLoading) {
    return (
      <Box textAlign="center" py={10}>
        <Spinner size="xl" />
        <Text mt={4}>Loading performance data...</Text>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert status="error">
        <AlertIcon />
        <AlertTitle>Error loading performance data</AlertTitle>
        <AlertDescription>Please try again later.</AlertDescription>
      </Alert>
    );
  }

  if (!snapshots || snapshots.length === 0) {
    return (
      <Alert status="info">
        <AlertIcon />
        <AlertTitle>No historical data yet</AlertTitle>
        <AlertDescription>
          Performance trends will appear once portfolio snapshots are captured.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <VStack spacing={6} align="stretch">
      {isMockData && (
        <Alert status="warning">
          <AlertIcon />
          <AlertDescription>
            Displaying mock data for visualization. Real historical data will appear once daily snapshots are captured.
          </AlertDescription>
        </Alert>
      )}

      <HStack justify="space-between" flexWrap="wrap">
        <Text fontSize="xl" fontWeight="bold">
          Performance Trends
        </Text>
        <ButtonGroup size="sm" isAttached variant="outline">
          {(['1M', '3M', '6M', '1Y', 'ALL'] as TimeRange[]).map((range) => (
            <Button
              key={range}
              onClick={() => setTimeRange(range)}
              colorScheme={timeRange === range ? 'brand' : 'gray'}
              variant={timeRange === range ? 'solid' : 'outline'}
            >
              {range}
            </Button>
          ))}
        </ButtonGroup>
      </HStack>

      {/* Performance Metrics */}
      <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
        <Box
          p={4}
          bg={bgColor}
          borderWidth="1px"
          borderColor={borderColor}
          borderRadius="md"
        >
          <Stat>
            <StatLabel>Total Return</StatLabel>
            <StatNumber>
              ${Math.abs(metrics.totalReturn).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </StatNumber>
            <StatHelpText>
              <StatArrow type={metrics.isPositive ? 'increase' : 'decrease'} />
              {Math.abs(metrics.totalReturnPercent).toFixed(2)}%
            </StatHelpText>
          </Stat>
        </Box>

        <Box
          p={4}
          bg={bgColor}
          borderWidth="1px"
          borderColor={borderColor}
          borderRadius="md"
        >
          <Stat>
            <StatLabel>CAGR</StatLabel>
            <StatNumber>{metrics.cagr.toFixed(2)}%</StatNumber>
            <StatHelpText>Compound Annual Growth Rate</StatHelpText>
          </Stat>
        </Box>

        <Box
          p={4}
          bg={bgColor}
          borderWidth="1px"
          borderColor={borderColor}
          borderRadius="md"
        >
          <Stat>
            <StatLabel>YoY Growth</StatLabel>
            <StatNumber>{metrics.yoyGrowth === 0 ? 'N/A' : `${metrics.yoyGrowth.toFixed(2)}%`}</StatNumber>
            <StatHelpText>Year over Year</StatHelpText>
          </Stat>
        </Box>
      </SimpleGrid>

      {/* Chart */}
      <Box
        p={4}
        bg={bgColor}
        borderWidth="1px"
        borderColor={borderColor}
        borderRadius="md"
      >
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12 }}
              angle={-45}
              textAnchor="end"
              height={80}
            />
            <YAxis
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
            />
            <Tooltip
              formatter={(value: number) => [
                `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
                'Value',
              ]}
              labelStyle={{ color: '#000' }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#3182CE"
              strokeWidth={2}
              name="Portfolio Value"
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
            />
            {chartData.some(d => d.costBasis !== undefined) && (
              <Line
                type="monotone"
                dataKey="costBasis"
                stroke="#48BB78"
                strokeWidth={2}
                strokeDasharray="5 5"
                name="Cost Basis"
                dot={{ r: 2 }}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </Box>
    </VStack>
  );
}
