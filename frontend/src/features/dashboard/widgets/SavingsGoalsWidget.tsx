import {
  Box,
  Card,
  CardBody,
  Heading,
  HStack,
  Link,
  Progress,
  Spinner,
  Text,
  VStack,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { Link as RouterLink } from 'react-router-dom';
import { savingsGoalsApi } from '../../../api/savings-goals';

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

export const SavingsGoalsWidget: React.FC = () => {
  const { data: goals, isLoading } = useQuery({
    queryKey: ['goals-widget'],
    queryFn: () => savingsGoalsApi.getAll({ is_completed: false }),
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

  const activeGoals = (goals ?? [])
    .filter((g) => !g.is_funded && !g.is_completed)
    .slice(0, 5);

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Savings Goals</Heading>
          <Link as={RouterLink} to="/goals" fontSize="sm" color="brand.500">
            View all →
          </Link>
        </HStack>

        {activeGoals.length === 0 ? (
          <Text color="gray.500" fontSize="sm">
            No active goals. Add one to get started.
          </Text>
        ) : (
          <VStack align="stretch" spacing={4}>
            {activeGoals.map((goal) => {
              const pct = goal.target_amount > 0
                ? Math.min(100, (goal.current_amount / goal.target_amount) * 100)
                : 0;
              return (
                <Box key={goal.id}>
                  <HStack justify="space-between" mb={1}>
                    <Text fontWeight="medium" fontSize="sm" noOfLines={1}>
                      {goal.name}
                    </Text>
                    <Text fontSize="sm" color="gray.600" whiteSpace="nowrap">
                      {formatCurrency(goal.current_amount)} / {formatCurrency(goal.target_amount)}
                    </Text>
                  </HStack>
                  <Progress
                    value={pct}
                    size="sm"
                    colorScheme={pct >= 100 ? 'green' : 'brand'}
                    borderRadius="full"
                  />
                </Box>
              );
            })}
          </VStack>
        )}
      </CardBody>
    </Card>
  );
};
