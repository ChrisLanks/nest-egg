import { Card, CardBody, Heading, useColorModeValue } from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useUserView } from '../../../contexts/UserViewContext';
import api from '../../../services/api';

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);

export const CashFlowTrendWidget: React.FC = () => {
  const { selectedUserId } = useUserView();
  const tooltipBg = useColorModeValue('#FFFFFF', '#2D3748');
  const tooltipBorder = useColorModeValue('#E2E8F0', '#4A5568');

  const { data } = useQuery({
    queryKey: ['dashboard', selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const response = await api.get('/dashboard/', { params });
      return response.data;
    },
  });

  const cashFlowTrend = data?.cash_flow_trend;
  if (!cashFlowTrend || cashFlowTrend.length === 0) return null;

  return (
    <Card>
      <CardBody>
        <Heading size="md" mb={4}>
          Cash Flow Trend
        </Heading>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={cashFlowTrend}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis />
            <Tooltip
              formatter={(v: number) => formatCurrency(v)}
              contentStyle={{ backgroundColor: tooltipBg, border: `1px solid ${tooltipBorder}` }}
            />
            <Legend />
            <Bar dataKey="income" fill="#48BB78" name="Income" />
            <Bar dataKey="expenses" fill="#F56565" name="Expenses" />
          </BarChart>
        </ResponsiveContainer>
      </CardBody>
    </Card>
  );
};
