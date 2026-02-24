/**
 * Cash flow forecast chart component
 */

import {
  Card,
  CardBody,
  Heading,
  HStack,
  Button,
  ButtonGroup,
  Text,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Box,
  Spinner,
  Center,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
} from 'recharts';
import api from '../services/api';

interface ForecastDataPoint {
  date: string;
  projected_balance: number;
  day_change: number;
  transaction_count: number;
}

export const ForecastChart = () => {
  const [timeRange, setTimeRange] = useState<30 | 60 | 90>(90);

  const { data: forecast, isLoading, isError } = useQuery({
    queryKey: ['cash-flow-forecast', timeRange],
    queryFn: async () => {
      const response = await api.get<ForecastDataPoint[]>('/dashboard/forecast', {
        params: { days_ahead: timeRange },
      });
      return response.data;
    },
  });

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  const formatFullDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  if (isLoading) {
    return (
      <Card>
        <CardBody>
          <Center py={8}>
            <Spinner size="lg" color="brand.500" />
          </Center>
        </CardBody>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card>
        <CardBody>
          <Alert status="error" borderRadius="md">
            <AlertIcon />
            <Text fontSize="sm">Unable to load cash flow forecast.</Text>
          </Alert>
        </CardBody>
      </Card>
    );
  }

  if (!forecast || forecast.length === 0) {
    return null;
  }

  // Find lowest balance day
  const lowestDay = forecast.reduce((min, day) =>
    day.projected_balance < min.projected_balance ? day : min
  );

  const hasNegativeProjection = lowestDay.projected_balance < 0;

  // Count days with transactions
  const daysWithTransactions = forecast.filter((d) => d.transaction_count > 0).length;

  return (
    <Card>
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">💰 Cash Flow Forecast</Heading>
          <ButtonGroup size="sm" isAttached variant="outline">
            <Button
              onClick={() => setTimeRange(30)}
              colorScheme={timeRange === 30 ? 'blue' : 'gray'}
              variant={timeRange === 30 ? 'solid' : 'outline'}
            >
              30 Days
            </Button>
            <Button
              onClick={() => setTimeRange(60)}
              colorScheme={timeRange === 60 ? 'blue' : 'gray'}
              variant={timeRange === 60 ? 'solid' : 'outline'}
            >
              60 Days
            </Button>
            <Button
              onClick={() => setTimeRange(90)}
              colorScheme={timeRange === 90 ? 'blue' : 'gray'}
              variant={timeRange === 90 ? 'solid' : 'outline'}
            >
              90 Days
            </Button>
          </ButtonGroup>
        </HStack>

        {hasNegativeProjection && (
          <Alert status="warning" mb={4} borderRadius="md">
            <AlertIcon />
            <Box>
              <AlertTitle>⚠️ Low Balance Alert</AlertTitle>
              <AlertDescription>
                Your balance is projected to go negative on{' '}
                <strong>{formatFullDate(lowestDay.date)}</strong> (
                <strong>{formatCurrency(lowestDay.projected_balance)}</strong>)
              </AlertDescription>
            </Box>
          </Alert>
        )}

        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={forecast}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              stroke="#718096"
              style={{ fontSize: '12px' }}
            />
            <YAxis
              tickFormatter={(value: number) => formatCurrency(value)}
              stroke="#718096"
              style={{ fontSize: '12px' }}
            />
            <Tooltip
              formatter={((value: number) => [formatCurrency(value), 'Balance']) as any}
              labelFormatter={((date: string) => formatFullDate(date)) as any}
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #E2E8F0',
                borderRadius: '8px',
                padding: '8px',
              }}
            />
            <Legend />
            <ReferenceLine y={0} stroke="#E53E3E" strokeDasharray="3 3" />
            <Area
              type="monotone"
              dataKey="projected_balance"
              stroke="#3182CE"
              fill="#3182CE"
              fillOpacity={0.3}
              name="Projected Balance"
            />
          </AreaChart>
        </ResponsiveContainer>

        <Text fontSize="xs" color="text.muted" mt={2}>
          Based on {daysWithTransactions} days with recurring transactions
        </Text>
      </CardBody>
    </Card>
  );
};
