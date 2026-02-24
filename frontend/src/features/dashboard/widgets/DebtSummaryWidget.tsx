import {
  Box,
  Card,
  CardBody,
  Divider,
  Heading,
  HStack,
  Link,
  Stat,
  StatLabel,
  StatNumber,
  Text,
  VStack,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { Link as RouterLink } from 'react-router-dom';
import { useUserView } from '../../../contexts/UserViewContext';
import api from '../../../services/api';

const DEBT_TYPES = new Set([
  'credit_card',
  'loan',
  'student_loan',
  'mortgage',
  'heloc',
  'personal_loan',
  'auto_loan',
  'line_of_credit',
  'private_debt',
]);

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

export const DebtSummaryWidget: React.FC = () => {
  const { selectedUserId } = useUserView();

  const { data } = useQuery({
    queryKey: ['dashboard', selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const response = await api.get('/dashboard/', { params });
      return response.data;
    },
  });

  const debtAccounts = (data?.account_balances ?? []).filter(
    (a: { type: string; balance: number }) => DEBT_TYPES.has(a.type) && a.balance < 0
  );

  const totalDebt = debtAccounts.reduce(
    (sum: number, a: { balance: number }) => sum + Math.abs(a.balance),
    0
  );

  if (debtAccounts.length === 0) return null;

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Debt Summary</Heading>
          <Link as={RouterLink} to="/accounts" fontSize="sm" color="brand.500">
            View accounts →
          </Link>
        </HStack>

        <Stat mb={4}>
          <StatLabel>Total Debt</StatLabel>
          <StatNumber color="finance.negative">{formatCurrency(totalDebt)}</StatNumber>
        </Stat>

        <VStack align="stretch" spacing={2}>
          {debtAccounts.slice(0, 5).map((account: {
            id: string;
            name: string;
            type: string;
            balance: number;
          }, index: number) => (
            <Box key={account.id}>
              <HStack justify="space-between">
                <VStack align="start" spacing={0}>
                  <Text fontWeight="medium" fontSize="sm" noOfLines={1}>
                    {account.name}
                  </Text>
                  <Text fontSize="xs" color="text.muted" textTransform="capitalize">
                    {account.type.replace(/_/g, ' ')}
                  </Text>
                </VStack>
                <Text fontWeight="bold" fontSize="sm" color="finance.negative" whiteSpace="nowrap">
                  {formatCurrency(Math.abs(account.balance))}
                </Text>
              </HStack>
              {index < debtAccounts.slice(0, 5).length - 1 && <Divider mt={2} />}
            </Box>
          ))}
        </VStack>
      </CardBody>
    </Card>
  );
};
