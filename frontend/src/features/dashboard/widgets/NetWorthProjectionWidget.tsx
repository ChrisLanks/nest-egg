/**
 * Net Worth Projection Widget
 *
 * Projects total net worth growth over 5/10/20 years using Monte Carlo simulation.
 * Extends the GrowthProjectionsChart with a monthly savings contribution input.
 */

import {
  Box,
  Card,
  CardBody,
  FormControl,
  FormLabel,
  Heading,
  HStack,
  NumberInput,
  NumberInputField,
  Spinner,
  Center,
  Text,
} from '@chakra-ui/react';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useUserView } from '../../../contexts/UserViewContext';
import { GrowthProjectionsChart } from '../../investments/components/GrowthProjectionsChart';
import api from '../../../services/api';

export const NetWorthProjectionWidget: React.FC = () => {
  const { selectedUserId } = useUserView();
  const [monthlySavings, setMonthlySavings] = useState('0');

  const { data: dashboardData, isLoading } = useQuery({
    queryKey: ['dashboard', selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const response = await api.get('/dashboard/', { params });
      return response.data;
    },
  });

  const netWorth: number = dashboardData?.summary?.net_worth ?? 0;
  const monthlyContribution = Math.max(0, parseFloat(monthlySavings) || 0);

  if (isLoading) {
    return (
      <Card>
        <CardBody>
          <Center py={8}>
            <Spinner />
          </Center>
        </CardBody>
      </Card>
    );
  }

  return (
    <Box>
      <HStack justify="space-between" mb={4} wrap="wrap" spacing={4}>
        <Heading size="md">Net Worth Projection</Heading>
        <FormControl maxW="200px">
          <FormLabel fontSize="sm" mb={1}>Monthly Savings ($)</FormLabel>
          <NumberInput
            value={monthlySavings}
            onChange={setMonthlySavings}
            min={0}
            precision={0}
            size="sm"
          >
            <NumberInputField placeholder="e.g., 1000" />
          </NumberInput>
        </FormControl>
      </HStack>

      {netWorth <= 0 ? (
        <Text color="text.muted" fontSize="sm">
          Net worth data not available. Add accounts to see projections.
        </Text>
      ) : (
        <GrowthProjectionsChart
          currentValue={netWorth}
          monthlyContribution={monthlyContribution}
        />
      )}
    </Box>
  );
};
