import { useMemo } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Badge,
  Progress,
  Flex,
  Circle,
  Alert,
  AlertIcon,
  AlertDescription,
  Tooltip,
} from '@chakra-ui/react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { useQuery } from '@tanstack/react-query';
import { format, subMonths } from 'date-fns';
import api from '../../../services/api';

interface Snapshot {
  id: string;
  snapshot_date: string;
  total_value: number;
}

interface HoldingSummary {
  ticker: string;
  name?: string;
  current_total_value?: number;
  asset_type?: string;
}

interface PortfolioSummary {
  total_value: number;
  stocks_value: number;
  bonds_value: number;
  etf_value: number;
  mutual_funds_value: number;
  cash_value: number;
  other_value: number;
  holdings_by_ticker: HoldingSummary[];
}

interface RiskAnalysisPanelProps {
  portfolio: PortfolioSummary;
}

// Calculate annualized volatility from daily returns
const calculateVolatility = (snapshots: Snapshot[]): number => {
  if (snapshots.length < 2) return 0;

  // Calculate daily returns
  const returns: number[] = [];
  for (let i = 1; i < snapshots.length; i++) {
    const prevValue = snapshots[i - 1].total_value;
    const currValue = snapshots[i].total_value;
    if (prevValue > 0) {
      returns.push((currValue - prevValue) / prevValue);
    }
  }

  if (returns.length === 0) return 0;

  // Calculate standard deviation
  const mean = returns.reduce((sum, r) => sum + r, 0) / returns.length;
  const squaredDiffs = returns.map(r => Math.pow(r - mean, 2));
  const variance = squaredDiffs.reduce((sum, sd) => sum + sd, 0) / returns.length;
  const stdDev = Math.sqrt(variance);

  // Annualize (√252 trading days)
  const annualizedVolatility = stdDev * Math.sqrt(252);

  return annualizedVolatility * 100; // Convert to percentage
};

// Calculate diversification score using Herfindahl-Hirschman Index (HHI)
const calculateDiversificationScore = (holdings: HoldingSummary[], totalValue: number): number => {
  if (holdings.length === 0 || totalValue === 0) return 0;

  // Calculate HHI (sum of squared market shares)
  let hhi = 0;
  holdings.forEach(holding => {
    if (holding.current_total_value) {
      const marketShare = holding.current_total_value / totalValue;
      hhi += Math.pow(marketShare, 2);
    }
  });

  // Ideal HHI for perfect diversification (equal weights)
  const numHoldings = holdings.filter(h => h.current_total_value && h.current_total_value > 0).length;
  const idealHHI = numHoldings > 0 ? 1 / numHoldings : 1;

  // Convert to score (0-100, where 100 is perfectly diversified)
  // Score = (1 - (HHI - ideal) / (1 - ideal)) × 100
  const diversificationScore = numHoldings > 1
    ? Math.max(0, Math.min(100, (1 - (hhi - idealHHI) / (1 - idealHHI)) * 100))
    : 0;

  return diversificationScore;
};

// Calculate overall risk score
const calculateRiskScore = (volatility: number, diversificationScore: number): number => {
  // Normalize volatility to 0-100 scale (assume 0-50% volatility range)
  const normalizedVolatility = Math.min(100, (volatility / 50) * 100);

  // Diversification risk is inverse of diversification score
  const diversificationRisk = 100 - diversificationScore;

  // Weighted risk: 60% volatility + 40% diversification risk
  const riskScore = (normalizedVolatility * 0.6) + (diversificationRisk * 0.4);

  return Math.round(riskScore);
};

// Get risk color and label
const getRiskLevel = (riskScore: number): { color: string; label: string; colorScheme: string } => {
  if (riskScore < 40) {
    return { color: '#48BB78', label: 'Low Risk', colorScheme: 'green' };
  } else if (riskScore < 70) {
    return { color: '#ECC94B', label: 'Moderate Risk', colorScheme: 'yellow' };
  } else {
    return { color: '#F56565', label: 'High Risk', colorScheme: 'red' };
  }
};

export default function RiskAnalysisPanel({ portfolio }: RiskAnalysisPanelProps) {
  // Fetch historical snapshots for volatility calculation
  const { data: snapshots } = useQuery({
    queryKey: ['portfolio-snapshots-risk'],
    queryFn: async () => {
      const startDate = format(subMonths(new Date(), 6), 'yyyy-MM-dd');
      const endDate = format(new Date(), 'yyyy-MM-dd');

      try {
        const response = await api.get(`/holdings/historical`, {
          params: { start_date: startDate, end_date: endDate },
        });
        return response.data as Snapshot[];
      } catch (err) {
        return [];
      }
    },
    staleTime: 15 * 60 * 1000,
  });

  // Check if we have any holdings data
  const hasHoldingsData = portfolio.holdings_by_ticker.length > 0;

  // Calculate metrics
  const metrics = useMemo(() => {
    const volatility = snapshots && snapshots.length >= 2 ? calculateVolatility(snapshots) : 0;
    const diversificationScore = calculateDiversificationScore(
      portfolio.holdings_by_ticker,
      portfolio.total_value
    );
    const riskScore = calculateRiskScore(volatility, diversificationScore);
    const riskLevel = getRiskLevel(riskScore);

    return {
      volatility,
      diversificationScore,
      riskScore,
      riskLevel,
    };
  }, [snapshots, portfolio]);

  // Asset allocation data for chart
  const assetAllocationData = useMemo(() => {
    const data = [
      { name: 'Stocks', value: Number(portfolio.stocks_value), color: '#3182CE' },
      { name: 'ETFs', value: Number(portfolio.etf_value), color: '#38B2AC' },
      { name: 'Mutual Funds', value: Number(portfolio.mutual_funds_value), color: '#805AD5' },
      { name: 'Bonds', value: Number(portfolio.bonds_value), color: '#48BB78' },
      { name: 'Cash', value: Number(portfolio.cash_value), color: '#ECC94B' },
      { name: 'Other', value: Number(portfolio.other_value), color: '#718096' },
    ].filter(item => item.value > 0);

    return data;
  }, [portfolio]);

  // Top concentrations (holdings > 20% of portfolio)
  const topConcentrations = useMemo(() => {
    return portfolio.holdings_by_ticker
      .filter(h => h.current_total_value && (h.current_total_value / portfolio.total_value) > 0.20)
      .map(h => ({
        ticker: h.ticker,
        name: h.name,
        value: h.current_total_value!,
        percentage: (h.current_total_value! / portfolio.total_value) * 100,
      }))
      .sort((a, b) => b.percentage - a.percentage);
  }, [portfolio]);

  const hasVolatilityData = snapshots && snapshots.length >= 2;

  return (
    <VStack spacing={6} align="stretch">
      {!hasVolatilityData && (
        <Alert status="info">
          <AlertIcon />
          <AlertDescription>
            Volatility metrics require at least 2 days of historical data. Diversification analysis is available now.
          </AlertDescription>
        </Alert>
      )}

      <HStack justify="space-between" flexWrap="wrap">
        <Text fontSize="xl" fontWeight="bold">
          Risk Analysis
        </Text>
      </HStack>

      <SimpleGrid columns={{ base: 1, lg: 3 }} spacing={6}>
        {/* Risk Score Circle */}
        <Box
          p={6}
          bg="bg.surface"
          borderWidth="1px"
          borderColor="border.default"
          borderRadius="md"
          textAlign="center"
        >
          <Text fontSize="sm" fontWeight="medium" mb={4}>
            Overall Risk Score
          </Text>
          <Flex justify="center" align="center" mb={4}>
            <Circle size="120px" borderWidth="8px" borderColor={metrics.riskLevel.color} position="relative">
              <VStack spacing={0}>
                <Text fontSize="3xl" fontWeight="bold" color={metrics.riskLevel.color}>
                  {metrics.riskScore}
                </Text>
                <Text fontSize="xs" color="text.muted">
                  out of 100
                </Text>
              </VStack>
            </Circle>
          </Flex>
          <Badge colorScheme={metrics.riskLevel.colorScheme} fontSize="md" px={3} py={1}>
            {metrics.riskLevel.label}
          </Badge>
          <Text fontSize="xs" color="text.muted" mt={2}>
            Based on volatility & diversification
          </Text>
        </Box>

        {/* Volatility */}
        <Box
          p={6}
          bg="bg.surface"
          borderWidth="1px"
          borderColor="border.default"
          borderRadius="md"
        >
          <Stat>
            <StatLabel>
              <Tooltip label="Annualized standard deviation of portfolio returns. Higher values indicate more price fluctuation.">
                <Text as="span" cursor="help" borderBottom="1px dotted">
                  Volatility
                </Text>
              </Tooltip>
            </StatLabel>
            <StatNumber>
              {hasVolatilityData ? `${metrics.volatility.toFixed(2)}%` : 'N/A'}
            </StatNumber>
            <StatHelpText>Annualized (6 months)</StatHelpText>
          </Stat>
          {hasVolatilityData && (
            <Box mt={4}>
              <Progress
                value={Math.min(100, (metrics.volatility / 50) * 100)}
                colorScheme={metrics.volatility < 15 ? 'green' : metrics.volatility < 25 ? 'yellow' : 'red'}
                size="sm"
                borderRadius="md"
              />
              <Text fontSize="xs" color="text.muted" mt={2}>
                {metrics.volatility < 15 ? 'Low volatility' : metrics.volatility < 25 ? 'Moderate volatility' : 'High volatility'}
              </Text>
            </Box>
          )}
        </Box>

        {/* Diversification */}
        <Box
          p={6}
          bg="bg.surface"
          borderWidth="1px"
          borderColor="border.default"
          borderRadius="md"
        >
          <Stat>
            <StatLabel>
              <Tooltip label="Measures how evenly distributed your investments are. Higher scores indicate better diversification.">
                <Text as="span" cursor="help" borderBottom="1px dotted">
                  Diversification Score
                </Text>
              </Tooltip>
            </StatLabel>
            <StatNumber>
              {hasHoldingsData ? metrics.diversificationScore.toFixed(0) : 'Unknown'}
            </StatNumber>
            <StatHelpText>
              {hasHoldingsData ? 'out of 100' : 'No holdings data'}
            </StatHelpText>
          </Stat>
          {hasHoldingsData && (
            <Box mt={4}>
              <Progress
                value={metrics.diversificationScore}
                colorScheme={metrics.diversificationScore > 70 ? 'green' : metrics.diversificationScore > 40 ? 'yellow' : 'red'}
                size="sm"
                borderRadius="md"
              />
              <Text fontSize="xs" color="text.muted" mt={2}>
                {portfolio.holdings_by_ticker.filter(h => h.current_total_value && h.current_total_value > 0).length} holdings
              </Text>
            </Box>
          )}
        </Box>
      </SimpleGrid>

      <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
        {/* Asset Allocation Chart */}
        <Box
          p={4}
          bg="bg.surface"
          borderWidth="1px"
          borderColor="border.default"
          borderRadius="md"
        >
          <Text fontSize="md" fontWeight="medium" mb={4}>
            Asset Class Allocation
          </Text>
          {assetAllocationData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={assetAllocationData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  type="number"
                  tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                  tick={{ fontSize: 12 }}
                />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} width={100} />
                <RechartsTooltip
                  formatter={(value: number) => [
                    `$${value.toLocaleString('en-US', { minimumFractionDigits: 2 })}`,
                    'Value',
                  ]}
                  labelStyle={{ color: '#000' }}
                />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {assetAllocationData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <Text color="text.muted" textAlign="center" py={10}>
              No asset allocation data available
            </Text>
          )}
        </Box>

        {/* Top Concentrations */}
        <Box
          p={4}
          bg="bg.surface"
          borderWidth="1px"
          borderColor="border.default"
          borderRadius="md"
        >
          <Text fontSize="md" fontWeight="medium" mb={4}>
            Top Concentrations
          </Text>
          {!hasHoldingsData ? (
            <Box textAlign="center" py={10}>
              <Text color="text.secondary" fontWeight="medium">
                Unknown
              </Text>
              <Text fontSize="sm" color="text.muted" mt={2}>
                No holdings data available
              </Text>
            </Box>
          ) : topConcentrations.length > 0 ? (
            <VStack spacing={3} align="stretch">
              <Alert status="warning" size="sm">
                <AlertIcon />
                <Text fontSize="xs">
                  These holdings each represent more than 20% of your portfolio
                </Text>
              </Alert>
              {topConcentrations.map((holding) => (
                <Box
                  key={holding.ticker}
                  p={3}
                  borderWidth="1px"
                  borderColor="orange.200"
                  borderRadius="md"
                  bg="bg.warning"
                >
                  <HStack justify="space-between">
                    <VStack align="start" spacing={0}>
                      <Text fontWeight="bold">{holding.ticker}</Text>
                      {holding.name && (
                        <Text fontSize="xs" color="text.secondary">
                          {holding.name}
                        </Text>
                      )}
                    </VStack>
                    <VStack align="end" spacing={0}>
                      <Badge colorScheme="orange">{holding.percentage.toFixed(1)}%</Badge>
                      <Text fontSize="xs" color="text.secondary">
                        ${holding.value.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                      </Text>
                    </VStack>
                  </HStack>
                </Box>
              ))}
            </VStack>
          ) : (
            <Box textAlign="center" py={10}>
              <Text color="finance.positive" fontWeight="medium">
                ✓ No excessive concentrations
              </Text>
              <Text fontSize="sm" color="text.muted" mt={2}>
                All holdings are below 20% of portfolio
              </Text>
            </Box>
          )}
        </Box>
      </SimpleGrid>
    </VStack>
  );
}
