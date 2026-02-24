import {
  Badge,
  Box,
  Card,
  CardBody,
  Divider,
  Heading,
  HStack,
  Link,
  SimpleGrid,
  Spinner,
  Stat,
  StatHelpText,
  StatLabel,
  StatNumber,
  Text,
  VStack,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { Link as RouterLink } from 'react-router-dom';
import { holdingsApi } from '../../../api/holdings';

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

const formatPct = (pct: number) =>
  `${pct >= 0 ? '+' : ''}${Number(pct).toFixed(2)}%`;

export const InvestmentPerformanceWidget: React.FC = () => {
  const { data: portfolio, isLoading } = useQuery({
    queryKey: ['portfolio-widget'],
    queryFn: () => holdingsApi.getPortfolioSummary(),
  });

  if (isLoading) {
    return (
      <Card>
        <CardBody display="flex" alignItems="center" justifyContent="center" minH="200px">
          <Spinner />
        </CardBody>
      </Card>
    );
  }

  const totalValue = Number(portfolio?.total_value ?? 0);
  const gainLoss = portfolio?.total_gain_loss != null ? Number(portfolio.total_gain_loss) : null;
  const gainLossPct = portfolio?.total_gain_loss_percent != null ? Number(portfolio.total_gain_loss_percent) : null;
  const holdings: {
    ticker: string;
    name: string | null;
    current_total_value: string | number | null;
    gain_loss: string | number | null;
    gain_loss_percent: string | number | null;
  }[] = portfolio?.holdings_by_ticker ?? [];

  const topHoldings = [...holdings]
    .filter((h) => h.current_total_value != null)
    .sort((a, b) => Number(b.current_total_value) - Number(a.current_total_value))
    .slice(0, 5);

  if (totalValue === 0 && topHoldings.length === 0) {
    return (
      <Card>
        <CardBody display="flex" alignItems="center" justifyContent="center" minH="200px">
          <Text color="text.muted">No investment holdings tracked yet.</Text>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card>
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Investment Performance</Heading>
          <Link as={RouterLink} to="/holdings" fontSize="sm" color="brand.500">
            View portfolio →
          </Link>
        </HStack>

        <SimpleGrid columns={3} spacing={4} mb={6}>
          <Stat>
            <StatLabel>Portfolio Value</StatLabel>
            <StatNumber fontSize="lg">{formatCurrency(totalValue)}</StatNumber>
          </Stat>
          <Stat>
            <StatLabel>Total Gain / Loss</StatLabel>
            <StatNumber
              fontSize="lg"
              color={gainLoss == null ? 'text.muted' : gainLoss >= 0 ? 'finance.positive' : 'finance.negative'}
            >
              {gainLoss == null ? '—' : formatCurrency(gainLoss)}
            </StatNumber>
            {gainLossPct != null && (
              <StatHelpText color={gainLossPct >= 0 ? 'finance.positive' : 'finance.negative'}>
                {formatPct(gainLossPct)}
              </StatHelpText>
            )}
          </Stat>
          <Stat>
            <StatLabel>Annual Fees</StatLabel>
            <StatNumber fontSize="lg" color="text.secondary">
              {portfolio?.total_annual_fees != null
                ? formatCurrency(Number(portfolio.total_annual_fees))
                : '—'}
            </StatNumber>
          </Stat>
        </SimpleGrid>

        {topHoldings.length > 0 && (
          <>
            <Text fontSize="xs" fontWeight="semibold" color="text.muted" textTransform="uppercase" letterSpacing="wide" mb={2}>
              Top Holdings
            </Text>
            <VStack align="stretch" spacing={0}>
              {topHoldings.map((h, index) => {
                const glPct = h.gain_loss_percent != null ? Number(h.gain_loss_percent) : null;
                const isPositive = glPct != null && glPct >= 0;
                return (
                  <Box key={h.ticker}>
                    <HStack justify="space-between" py={2} px={1}>
                      <VStack align="start" spacing={0} flex={1} minW={0}>
                        <Text fontWeight="semibold" fontSize="sm">
                          {h.ticker}
                        </Text>
                        <Text fontSize="xs" color="text.muted" noOfLines={1}>
                          {h.name ?? ''}
                        </Text>
                      </VStack>
                      <HStack spacing={3} flexShrink={0}>
                        <Text fontWeight="medium" fontSize="sm">
                          {formatCurrency(Number(h.current_total_value))}
                        </Text>
                        {glPct != null && (
                          <Badge
                            colorScheme={isPositive ? 'green' : 'red'}
                            variant="subtle"
                            fontSize="xs"
                            px={2}
                            borderRadius="full"
                          >
                            {formatPct(glPct)}
                          </Badge>
                        )}
                      </HStack>
                    </HStack>
                    {index < topHoldings.length - 1 && <Divider />}
                  </Box>
                );
              })}
            </VStack>
          </>
        )}
      </CardBody>
    </Card>
  );
};
