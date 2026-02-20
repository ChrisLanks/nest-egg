import {
  Box,
  Button,
  ButtonGroup,
  Card,
  CardBody,
  FormControl,
  FormLabel,
  Heading,
  HStack,
  Input,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Spinner,
  useDisclosure,
  VStack,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import {
  AreaChart,
  Area,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import api from '../../../services/api';

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);

type TimeRange = '1M' | '3M' | '6M' | '1Y' | 'ALL' | 'CUSTOM';

export const NetWorthChartWidget: React.FC = () => {
  const [timeRange, setTimeRange] = useState<TimeRange>(() => {
    const saved = localStorage.getItem('dashboard-timeRange');
    return (saved as TimeRange) || '1Y';
  });
  const [customStartDate, setCustomStartDate] = useState<string>(() =>
    localStorage.getItem('dashboard-customStartDate') || ''
  );
  const [customEndDate, setCustomEndDate] = useState<string>(() =>
    localStorage.getItem('dashboard-customEndDate') || ''
  );
  const { isOpen, onOpen, onClose } = useDisclosure();

  const { data: historicalData, isFetching } = useQuery({
    queryKey: ['historical-net-worth', timeRange, customStartDate, customEndDate],
    queryFn: async () => {
      const now = new Date();
      let startDate: Date;
      let endDate: Date | null = null;

      switch (timeRange) {
        case '1M':
          startDate = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate());
          break;
        case '3M':
          startDate = new Date(now.getFullYear(), now.getMonth() - 3, now.getDate());
          break;
        case '6M':
          startDate = new Date(now.getFullYear(), now.getMonth() - 6, now.getDate());
          break;
        case '1Y':
          startDate = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
          break;
        case 'ALL':
          startDate = new Date(now.getFullYear() - 10, 0, 1);
          break;
        case 'CUSTOM':
          startDate = customStartDate
            ? new Date(customStartDate)
            : new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
          if (customEndDate) endDate = new Date(customEndDate);
          break;
        default:
          startDate = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
      }

      const params: Record<string, string> = {
        start_date: startDate.toISOString().split('T')[0],
      };
      if (endDate) params.end_date = endDate.toISOString().split('T')[0];

      const response = await api.get('/holdings/historical', { params });
      return response.data;
    },
  });

  const setRange = (range: TimeRange) => {
    setTimeRange(range);
    localStorage.setItem('dashboard-timeRange', range);
  };

  if (!historicalData || historicalData.length === 0) return null;

  const chartData = historicalData.map((s: { snapshot_date: string; total_value: number }) => ({
    date: new Date(s.snapshot_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    value: Number(s.total_value),
  }));

  return (
    <Card>
      <CardBody position="relative">
        {isFetching && (
          <Box
            position="absolute"
            top={0}
            left={0}
            right={0}
            bottom={0}
            bg="whiteAlpha.800"
            zIndex={1}
            display="flex"
            alignItems="center"
            justifyContent="center"
          >
            <Spinner size="lg" color="brand.500" />
          </Box>
        )}
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Net Worth Over Time</Heading>
          <ButtonGroup size="sm" isAttached variant="outline">
            {(['1M', '3M', '6M', '1Y', 'ALL'] as TimeRange[]).map((r) => (
              <Button key={r} onClick={() => setRange(r)} colorScheme={timeRange === r ? 'brand' : 'gray'}>
                {r}
              </Button>
            ))}
            <Button onClick={onOpen} colorScheme={timeRange === 'CUSTOM' ? 'brand' : 'gray'}>
              Custom
            </Button>
          </ButtonGroup>
        </HStack>

        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip
              formatter={(v: number) => formatCurrency(v)}
              contentStyle={{ backgroundColor: 'white', border: '1px solid #ccc' }}
            />
            <Legend />
            <defs>
              <linearGradient id="colorNetWorth" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3182CE" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#3182CE" stopOpacity={0.1} />
              </linearGradient>
            </defs>
            <Area
              type="monotone"
              dataKey="value"
              stroke="#3182CE"
              strokeWidth={2}
              fill="url(#colorNetWorth)"
              name="Net Worth"
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardBody>

      <Modal isOpen={isOpen} onClose={onClose} size="md">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Select Custom Date Range</ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            <VStack spacing={4}>
              <FormControl>
                <FormLabel>Start Date</FormLabel>
                <Input
                  type="date"
                  value={customStartDate}
                  onChange={(e) => {
                    setCustomStartDate(e.target.value);
                    localStorage.setItem('dashboard-customStartDate', e.target.value);
                  }}
                />
              </FormControl>
              <FormControl>
                <FormLabel>End Date (Optional)</FormLabel>
                <Input
                  type="date"
                  value={customEndDate}
                  onChange={(e) => {
                    setCustomEndDate(e.target.value);
                    localStorage.setItem('dashboard-customEndDate', e.target.value);
                  }}
                />
              </FormControl>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button
              colorScheme="brand"
              mr={3}
              isDisabled={!customStartDate}
              onClick={() => {
                localStorage.setItem('dashboard-timeRange', 'CUSTOM');
                setTimeRange('CUSTOM');
                onClose();
              }}
            >
              Apply
            </Button>
            <Button variant="ghost" onClick={onClose}>
              Cancel
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Card>
  );
};
