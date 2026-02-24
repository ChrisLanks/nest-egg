import { Box, Card, CardBody, Divider, Heading, HStack, Text, VStack } from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { useUserView } from '../../../contexts/UserViewContext';
import api from '../../../services/api';

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);

export const TopExpensesWidget: React.FC = () => {
  const { selectedUserId } = useUserView();

  const { data } = useQuery({
    queryKey: ['dashboard', selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const response = await api.get('/dashboard/', { params });
      return response.data;
    },
  });

  const topExpenses = data?.top_expenses;
  if (!topExpenses || topExpenses.length === 0) return null;

  return (
    <Card h="100%">
      <CardBody>
        <Heading size="md" mb={4}>
          Top Expense Categories
        </Heading>
        <VStack align="stretch" spacing={3}>
          {topExpenses.map((expense: { category: string; total: number; count: number }, index: number) => (
            <Box key={index}>
              <HStack justify="space-between" mb={1}>
                <Text fontWeight="medium">{expense.category}</Text>
                <Text fontWeight="bold" color="finance.negative">
                  {formatCurrency(expense.total)}
                </Text>
              </HStack>
              <Text fontSize="sm" color="text.secondary">
                {expense.count} transaction{expense.count !== 1 ? 's' : ''}
              </Text>
              {index < topExpenses.length - 1 && <Divider mt={3} />}
            </Box>
          ))}
        </VStack>
      </CardBody>
    </Card>
  );
};
