import {
  Card,
  CardBody,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  SimpleGrid,
  Text,
} from '@chakra-ui/react';
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

export const SummaryStatsWidget: React.FC = () => {
  const { selectedUserId } = useUserView();

  const { data } = useQuery({
    queryKey: ['dashboard', selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const response = await api.get('/dashboard/', { params });
      return response.data;
    },
  });

  const summary = data?.summary;
  const netWorth = summary?.net_worth ?? 0;
  const monthlyNet = summary?.monthly_net ?? 0;

  return (
    <>
      <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6} mb={6}>
        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Net Worth</StatLabel>
              <StatNumber color={netWorth >= 0 ? 'green.600' : 'red.600'}>
                {formatCurrency(netWorth)}
              </StatNumber>
              <StatHelpText>Assets - Debts</StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Total Assets</StatLabel>
              <StatNumber>{formatCurrency(summary?.total_assets ?? 0)}</StatNumber>
              <StatHelpText>Checking, Savings, Investments</StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Total Debts</StatLabel>
              <StatNumber color="red.600">
                {formatCurrency(summary?.total_debts ?? 0)}
              </StatNumber>
              <StatHelpText>Credit Cards, Loans</StatHelpText>
            </Stat>
          </CardBody>
        </Card>
      </SimpleGrid>

      <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Monthly Income</StatLabel>
              <StatNumber color="green.600">
                {formatCurrency(summary?.monthly_income ?? 0)}
              </StatNumber>
              <StatHelpText>This month</StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Monthly Spending</StatLabel>
              <StatNumber color="red.600">
                {formatCurrency(summary?.monthly_spending ?? 0)}
              </StatNumber>
              <StatHelpText>
                Net:{' '}
                <Text as="span" color={monthlyNet >= 0 ? 'green.600' : 'red.600'} fontWeight="bold">
                  {formatCurrency(monthlyNet)}
                </Text>
              </StatHelpText>
            </Stat>
          </CardBody>
        </Card>
      </SimpleGrid>
    </>
  );
};
