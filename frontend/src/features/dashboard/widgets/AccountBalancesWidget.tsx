import {
  Badge,
  Card,
  CardBody,
  Heading,
  Table,
  Tbody,
  Td,
  Th,
  Thead,
  Tr,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { useUserView } from '../../../contexts/UserViewContext';
import api from '../../../services/api';

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);

export const AccountBalancesWidget: React.FC = () => {
  const { selectedUserId } = useUserView();

  const { data } = useQuery({
    queryKey: ['dashboard', selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const response = await api.get('/dashboard/', { params });
      return response.data;
    },
  });

  const sortedAccounts = useMemo(() => {
    if (!data?.account_balances) return [];
    return [...data.account_balances].sort(
      (a: { balance: number }, b: { balance: number }) => b.balance - a.balance
    );
  }, [data?.account_balances]);

  if (sortedAccounts.length === 0) return null;

  return (
    <Card>
      <CardBody>
        <Heading size="md" mb={4}>
          Account Balances
        </Heading>
        <Table variant="simple" size="sm">
          <Thead>
            <Tr>
              <Th>Account</Th>
              <Th>Type</Th>
              <Th>Institution</Th>
              <Th isNumeric>Balance</Th>
            </Tr>
          </Thead>
          <Tbody>
            {sortedAccounts.map((account: {
              id: string;
              name: string;
              type: string;
              institution: string;
              balance: number;
            }) => (
              <Tr key={account.id}>
                <Td fontWeight="medium">{account.name}</Td>
                <Td>
                  <Badge>{account.type.replace('_', ' ')}</Badge>
                </Td>
                <Td color="gray.600">{account.institution || 'Manual'}</Td>
                <Td isNumeric fontWeight="bold">
                  {formatCurrency(account.balance)}
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      </CardBody>
    </Card>
  );
};
