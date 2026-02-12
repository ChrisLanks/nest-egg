/**
 * Transactions page
 */

import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Spinner,
  Center,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { transactionApi } from '../services/transactionApi';

export const TransactionsPage = () => {
  const { data: transactions, isLoading } = useQuery({
    queryKey: ['transactions'],
    queryFn: () => transactionApi.listTransactions({ page_size: 50 }),
  });

  if (isLoading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" color="brand.500" />
      </Center>
    );
  }

  const formatCurrency = (amount: number) => {
    const isNegative = amount < 0;
    const formatted = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(Math.abs(amount));
    return { formatted, isNegative };
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        <Box>
          <Heading size="lg">Transactions</Heading>
          <Text color="gray.600" mt={2}>
            Showing {transactions?.transactions.length || 0} of{' '}
            {transactions?.total || 0} transactions
          </Text>
        </Box>

        <Box bg="white" borderRadius="lg" boxShadow="sm" overflow="hidden">
          <Table variant="simple">
            <Thead bg="gray.50">
              <Tr>
                <Th>Date</Th>
                <Th>Merchant</Th>
                <Th>Account</Th>
                <Th>Category</Th>
                <Th isNumeric>Amount</Th>
                <Th>Status</Th>
              </Tr>
            </Thead>
            <Tbody>
              {transactions?.transactions.map((txn) => {
                const { formatted, isNegative } = formatCurrency(txn.amount);
                return (
                  <Tr key={txn.id}>
                    <Td>{formatDate(txn.date)}</Td>
                    <Td>
                      <Text fontWeight="medium">{txn.merchant_name}</Text>
                      {txn.description && (
                        <Text fontSize="sm" color="gray.600">
                          {txn.description}
                        </Text>
                      )}
                    </Td>
                    <Td>
                      <Text fontSize="sm">
                        {txn.account_name}
                        {txn.account_mask && ` ****${txn.account_mask}`}
                      </Text>
                    </Td>
                    <Td>
                      {txn.category_primary && (
                        <Badge colorScheme="blue" fontSize="xs">
                          {txn.category_primary}
                        </Badge>
                      )}
                    </Td>
                    <Td isNumeric>
                      <Text
                        fontWeight="semibold"
                        color={isNegative ? 'red.600' : 'green.600'}
                      >
                        {isNegative ? '-' : '+'}
                        {formatted}
                      </Text>
                    </Td>
                    <Td>
                      {txn.is_pending && (
                        <Badge colorScheme="orange">Pending</Badge>
                      )}
                    </Td>
                  </Tr>
                );
              })}
            </Tbody>
          </Table>
        </Box>
      </VStack>
    </Container>
  );
};
