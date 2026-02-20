import { Badge, Box, Card, CardBody, Heading, HStack, Text, VStack } from '@chakra-ui/react';
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

const formatDate = (dateStr: string) => {
  const [year, month, day] = dateStr.split('-').map(Number);
  return new Date(year, month - 1, day).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
};

export const RecentTransactionsWidget: React.FC = () => {
  const { selectedUserId } = useUserView();

  const { data } = useQuery({
    queryKey: ['dashboard', selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const response = await api.get('/dashboard/', { params });
      return response.data;
    },
  });

  const recentTransactions = data?.recent_transactions;
  if (!recentTransactions || recentTransactions.length === 0) return null;

  return (
    <Card h="100%">
      <CardBody>
        <Heading size="md" mb={4}>
          Recent Transactions
        </Heading>
        <VStack align="stretch" spacing={3}>
          {recentTransactions.map((txn: {
            id: string;
            date: string;
            amount: number;
            merchant_name: string;
            category_primary: string;
            is_pending: boolean;
          }) => (
            <Box key={txn.id}>
              <HStack justify="space-between" mb={1}>
                <VStack align="start" spacing={0}>
                  <Text fontWeight="medium">{txn.merchant_name || 'Unknown'}</Text>
                  <HStack spacing={2}>
                    <Text fontSize="sm" color="gray.600">
                      {formatDate(txn.date)}
                    </Text>
                    {txn.is_pending && (
                      <Badge colorScheme="orange" size="sm">
                        Pending
                      </Badge>
                    )}
                  </HStack>
                </VStack>
                <Text fontWeight="bold" color={txn.amount >= 0 ? 'green.600' : 'red.600'}>
                  {txn.amount >= 0 ? '+' : ''}
                  {formatCurrency(txn.amount)}
                </Text>
              </HStack>
              {txn.category_primary && (
                <Badge colorScheme="blue" size="sm">
                  {txn.category_primary}
                </Badge>
              )}
            </Box>
          ))}
        </VStack>
      </CardBody>
    </Card>
  );
};
