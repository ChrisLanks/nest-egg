/**
 * Multi-year trend analysis page with year-over-year comparisons
 */

import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Card,
  CardBody,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Spinner,
  Center,
  Select,
  Button,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  useToast,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import api from '../services/api';
import { useUserView } from '../contexts/UserViewContext';

interface YearOverYearData {
  month: number;
  month_name: string;
  data: {
    [year: string]: {
      income: number;
      expenses: number;
      net: number;
    };
  };
}

interface QuarterlySummary {
  quarter: number;
  quarter_name: string;
  data: {
    [year: string]: {
      income: number;
      expenses: number;
      net: number;
    };
  };
}

interface AnnualSummary {
  year: number;
  total_income: number;
  total_expenses: number;
  net: number;
  avg_monthly_income: number;
  avg_monthly_expenses: number;
  peak_expense_month: string | null;
  peak_expense_amount: number;
}

export default function TrendsPage() {
  const { selectedUserId } = useUserView();
  const toast = useToast();

  // Default to current year and 2 previous years
  const currentYear = new Date().getFullYear();
  const [selectedYears, setSelectedYears] = useState<number[]>([
    currentYear,
    currentYear - 1,
    currentYear - 2,
  ]);

  const [primaryYear, setPrimaryYear] = useState(currentYear);

  // Available years (last 5 years)
  const availableYears = useMemo(() => {
    const years = [];
    for (let i = 0; i < 5; i++) {
      years.push(currentYear - i);
    }
    return years;
  }, [currentYear]);

  // Fetch year-over-year comparison
  const { data: yoyData, isLoading: yoyLoading } = useQuery<YearOverYearData[]>({
    queryKey: ['year-over-year', selectedYears, selectedUserId],
    queryFn: async () => {
      const params: any = {
        years: selectedYears,
      };
      if (selectedUserId) params.user_id = selectedUserId;

      const response = await api.get('/income-expenses/year-over-year', { params });
      return response.data;
    },
    enabled: selectedYears.length > 0,
  });

  // Fetch quarterly summary
  const { data: quarterlyData, isLoading: quarterlyLoading } = useQuery<QuarterlySummary[]>({
    queryKey: ['quarterly-summary', selectedYears, selectedUserId],
    queryFn: async () => {
      const params: any = {
        years: selectedYears,
      };
      if (selectedUserId) params.user_id = selectedUserId;

      const response = await api.get('/income-expenses/quarterly-summary', { params });
      return response.data;
    },
    enabled: selectedYears.length > 0,
  });

  // Fetch annual summaries
  const { data: annualSummaries, isLoading: annualLoading } = useQuery<AnnualSummary[]>({
    queryKey: ['annual-summaries', selectedYears, selectedUserId],
    queryFn: async () => {
      const summaries = await Promise.all(
        selectedYears.map(async (year) => {
          const params: any = { year };
          if (selectedUserId) params.user_id = selectedUserId;

          const response = await api.get('/income-expenses/annual-summary', { params });
          return response.data;
        })
      );
      return summaries;
    },
    enabled: selectedYears.length > 0,
  });

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const handleYearToggle = (year: number) => {
    if (selectedYears.includes(year)) {
      if (selectedYears.length > 1) {
        setSelectedYears(selectedYears.filter((y) => y !== year));
        if (primaryYear === year) {
          setPrimaryYear(selectedYears.find((y) => y !== year) || currentYear);
        }
      } else {
        toast({
          title: 'At least one year required',
          description: 'You must select at least one year to compare.',
          status: 'warning',
          duration: 3000,
        });
      }
    } else {
      if (selectedYears.length < 3) {
        setSelectedYears([...selectedYears, year].sort((a, b) => b - a));
      } else {
        toast({
          title: 'Maximum 3 years',
          description: 'You can compare up to 3 years at once.',
          status: 'info',
          duration: 3000,
        });
      }
    }
  };

  // Calculate growth rates
  const calculateGrowthRate = (current: number, previous: number): number | null => {
    if (previous === 0) return null;
    return ((current - previous) / previous) * 100;
  };

  // Get primary year summary
  const primarySummary = annualSummaries?.find((s) => s.year === primaryYear);
  const comparisonYear = selectedYears.find((y) => y !== primaryYear);
  const comparisonSummary = annualSummaries?.find((s) => s.year === comparisonYear);

  const expenseGrowth =
    primarySummary && comparisonSummary
      ? calculateGrowthRate(primarySummary.total_expenses, comparisonSummary.total_expenses)
      : null;

  const incomeGrowth =
    primarySummary && comparisonSummary
      ? calculateGrowthRate(primarySummary.total_income, comparisonSummary.total_income)
      : null;

  // Prepare chart data for expenses trend
  const expensesTrendData = useMemo(() => {
    if (!yoyData) return [];

    return yoyData.map((month) => {
      const dataPoint: any = {
        month: month.month_name.substring(0, 3), // Short month names
      };

      selectedYears.forEach((year) => {
        const yearStr = String(year);
        dataPoint[yearStr] = month.data[yearStr]?.expenses || 0;
      });

      return dataPoint;
    });
  }, [yoyData, selectedYears]);

  // Color palette for years
  const yearColors = ['#3182CE', '#38A169', '#DD6B20'];

  if (yoyLoading || quarterlyLoading || annualLoading) {
    return (
      <Container maxW="container.xl" py={8}>
        <Center py={20}>
          <Spinner size="xl" color="brand.500" />
        </Center>
      </Container>
    );
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={8} align="stretch">
        {/* Header */}
        <Box>
          <Heading size="lg" mb={2}>
            📊 Multi-Year Trends
          </Heading>
          <Text color="gray.600">Year-over-year spending analysis and comparisons</Text>
        </Box>

        {/* Year Selector */}
        <Card>
          <CardBody>
            <VStack align="stretch" spacing={4}>
              <HStack justify="space-between">
                <Text fontWeight="semibold">Select Years to Compare</Text>
                <Text fontSize="sm" color="gray.600">
                  {selectedYears.length} of 3 selected
                </Text>
              </HStack>
              <HStack spacing={2} flexWrap="wrap">
                {availableYears.map((year) => (
                  <Button
                    key={year}
                    size="sm"
                    variant={selectedYears.includes(year) ? 'solid' : 'outline'}
                    colorScheme={selectedYears.includes(year) ? 'blue' : 'gray'}
                    onClick={() => handleYearToggle(year)}
                  >
                    {year}
                    {selectedYears.includes(year) && year === primaryYear && (
                      <Badge ml={2} colorScheme="green" fontSize="2xs">
                        Primary
                      </Badge>
                    )}
                  </Button>
                ))}
              </HStack>
              {selectedYears.length > 1 && (
                <HStack spacing={2} align="center">
                  <Text fontSize="sm" color="gray.600">
                    Primary year for comparisons:
                  </Text>
                  <Select
                    size="sm"
                    w="150px"
                    value={primaryYear}
                    onChange={(e) => setPrimaryYear(Number(e.target.value))}
                  >
                    {selectedYears.map((year) => (
                      <option key={year} value={year}>
                        {year}
                      </option>
                    ))}
                  </Select>
                </HStack>
              )}
            </VStack>
          </CardBody>
        </Card>

        {/* Overview Stats */}
        {primarySummary && (
          <SimpleGrid columns={{ base: 1, md: 4 }} spacing={6}>
            <Card>
              <CardBody>
                <Stat>
                  <StatLabel>Total Expenses ({primaryYear})</StatLabel>
                  <StatNumber>{formatCurrency(primarySummary.total_expenses)}</StatNumber>
                  {expenseGrowth !== null && comparisonYear && (
                    <StatHelpText>
                      <StatArrow type={expenseGrowth > 0 ? 'increase' : 'decrease'} />
                      {Math.abs(expenseGrowth).toFixed(1)}% vs {comparisonYear}
                    </StatHelpText>
                  )}
                </Stat>
              </CardBody>
            </Card>

            <Card>
              <CardBody>
                <Stat>
                  <StatLabel>Total Income ({primaryYear})</StatLabel>
                  <StatNumber color="green.600">
                    {formatCurrency(primarySummary.total_income)}
                  </StatNumber>
                  {incomeGrowth !== null && comparisonYear && (
                    <StatHelpText>
                      <StatArrow type={incomeGrowth > 0 ? 'increase' : 'decrease'} />
                      {Math.abs(incomeGrowth).toFixed(1)}% vs {comparisonYear}
                    </StatHelpText>
                  )}
                </Stat>
              </CardBody>
            </Card>

            <Card>
              <CardBody>
                <Stat>
                  <StatLabel>Avg Monthly Expenses</StatLabel>
                  <StatNumber>{formatCurrency(primarySummary.avg_monthly_expenses)}</StatNumber>
                  <StatHelpText>Per month in {primaryYear}</StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card>
              <CardBody>
                <Stat>
                  <StatLabel>Peak Expense Month</StatLabel>
                  <StatNumber fontSize="lg">
                    {primarySummary.peak_expense_month || 'N/A'}
                  </StatNumber>
                  <StatHelpText>
                    {primarySummary.peak_expense_amount > 0
                      ? formatCurrency(primarySummary.peak_expense_amount)
                      : 'No data'}
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>
          </SimpleGrid>
        )}

        {/* Monthly Expenses Trend Chart */}
        <Card>
          <CardBody>
            <VStack align="stretch" spacing={4}>
              <Box>
                <Heading size="md" mb={1}>
                  Monthly Expenses Comparison
                </Heading>
                <Text fontSize="sm" color="gray.600">
                  Track spending patterns month-by-month across years
                </Text>
              </Box>
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={expensesTrendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis
                    dataKey="month"
                    stroke="#718096"
                    style={{ fontSize: '12px' }}
                  />
                  <YAxis
                    tickFormatter={(value: number) => formatCurrency(value)}
                    stroke="#718096"
                    style={{ fontSize: '12px' }}
                  />
                  <Tooltip
                    formatter={(value: number) => formatCurrency(value)}
                    contentStyle={{
                      backgroundColor: 'white',
                      border: '1px solid #E2E8F0',
                      borderRadius: '8px',
                    }}
                  />
                  <Legend />
                  {selectedYears.map((year, index) => (
                    <Line
                      key={year}
                      type="monotone"
                      dataKey={String(year)}
                      stroke={yearColors[index]}
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      activeDot={{ r: 6 }}
                      name={`${year} Expenses`}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </VStack>
          </CardBody>
        </Card>

        {/* Quarterly Summary Table */}
        {quarterlyData && quarterlyData.length > 0 && (
          <Card>
            <CardBody>
              <VStack align="stretch" spacing={4}>
                <Box>
                  <Heading size="md" mb={1}>
                    Quarterly Breakdown
                  </Heading>
                  <Text fontSize="sm" color="gray.600">
                    Compare quarterly performance across years
                  </Text>
                </Box>
                <Box overflowX="auto">
                  <Table variant="simple" size="sm">
                    <Thead>
                      <Tr>
                        <Th>Quarter</Th>
                        {selectedYears.map((year) => (
                          <Th key={year} isNumeric>
                            {year}
                          </Th>
                        ))}
                      </Tr>
                    </Thead>
                    <Tbody>
                      {quarterlyData.map((quarter) => (
                        <Tr key={quarter.quarter}>
                          <Td fontWeight="medium">{quarter.quarter_name}</Td>
                          {selectedYears.map((year) => {
                            const yearStr = String(year);
                            const expenses = quarter.data[yearStr]?.expenses || 0;
                            return (
                              <Td key={year} isNumeric>
                                {formatCurrency(expenses)}
                              </Td>
                            );
                          })}
                        </Tr>
                      ))}
                      {/* Total Row */}
                      <Tr fontWeight="bold" bg="gray.50">
                        <Td>Total</Td>
                        {selectedYears.map((year) => {
                          const total = quarterlyData.reduce((sum, quarter) => {
                            const yearStr = String(year);
                            return sum + (quarter.data[yearStr]?.expenses || 0);
                          }, 0);
                          return (
                            <Td key={year} isNumeric>
                              {formatCurrency(total)}
                            </Td>
                          );
                        })}
                      </Tr>
                    </Tbody>
                  </Table>
                </Box>
              </VStack>
            </CardBody>
          </Card>
        )}
      </VStack>
    </Container>
  );
}
