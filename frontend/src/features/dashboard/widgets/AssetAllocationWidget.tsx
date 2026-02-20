import {
  Box,
  Card,
  CardBody,
  Heading,
  HStack,
  Spinner,
  Text,
  VStack,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import { holdingsApi } from '../../../api/holdings';

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

const SLICES = [
  { key: 'stocks_value', label: 'Stocks', color: '#3182CE' },
  { key: 'etf_value', label: 'ETFs', color: '#805AD5' },
  { key: 'bonds_value', label: 'Bonds', color: '#38A169' },
  { key: 'mutual_funds_value', label: 'Mutual Funds', color: '#D69E2E' },
  { key: 'cash_value', label: 'Cash', color: '#68D391' },
  { key: 'other_value', label: 'Other', color: '#CBD5E0' },
] as const;

export const AssetAllocationWidget: React.FC = () => {
  const { data: portfolio, isLoading } = useQuery({
    queryKey: ['portfolio-widget'],
    queryFn: () => holdingsApi.getPortfolioSummary(),
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

  const total = Number(portfolio?.total_value ?? 0);

  const chartData = SLICES
    .map((s) => ({
      ...s,
      value: Number(portfolio?.[s.key] ?? 0),
    }))
    .filter((s) => s.value > 0);

  if (total === 0 || chartData.length === 0) {
    return (
      <Card h="100%">
        <CardBody display="flex" alignItems="center" justifyContent="center">
          <Text color="gray.500" fontSize="sm">
            No investment holdings yet.
          </Text>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card h="100%">
      <CardBody>
        <Heading size="md" mb={4}>Asset Allocation</Heading>

        <ResponsiveContainer width="100%" height={180}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={80}
              dataKey="value"
              strokeWidth={2}
            >
              {chartData.map((entry) => (
                <Cell key={entry.key} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number) => [formatCurrency(value), '']}
              contentStyle={{ fontSize: '12px' }}
            />
          </PieChart>
        </ResponsiveContainer>

        <VStack align="stretch" spacing={1.5} mt={3}>
          {chartData.map((slice) => {
            const pct = total > 0 ? ((slice.value / total) * 100).toFixed(1) : '0';
            return (
              <HStack key={slice.key} justify="space-between">
                <HStack spacing={2}>
                  <Box w={3} h={3} borderRadius="sm" bg={slice.color} flexShrink={0} />
                  <Text fontSize="xs" color="gray.700">
                    {slice.label}
                  </Text>
                </HStack>
                <HStack spacing={2}>
                  <Text fontSize="xs" color="gray.500">
                    {pct}%
                  </Text>
                  <Text fontSize="xs" fontWeight="medium" minW="60px" textAlign="right">
                    {formatCurrency(slice.value)}
                  </Text>
                </HStack>
              </HStack>
            );
          })}
        </VStack>
      </CardBody>
    </Card>
  );
};
