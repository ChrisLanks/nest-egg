/**
 * Investments page showing portfolio overview and holdings
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
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Spinner,
  Center,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Button,
  useDisclosure,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import api from '../services/api';

interface HoldingSummary {
  ticker: string;
  name: string | null;
  total_shares: number;
  total_cost_basis: number | null;
  current_price_per_share: number | null;
  current_total_value: number | null;
  price_as_of: string | null;
  asset_type: string | null;
  gain_loss: number | null;
  gain_loss_percent: number | null;
}

interface PortfolioSummary {
  total_value: number;
  total_cost_basis: number | null;
  total_gain_loss: number | null;
  total_gain_loss_percent: number | null;
  holdings_by_ticker: HoldingSummary[];
  stocks_value: number;
  bonds_value: number;
  etf_value: number;
  mutual_funds_value: number;
  cash_value: number;
  other_value: number;
}

export const InvestmentsPage = () => {
  // Fetch portfolio summary
  const { data: portfolio, isLoading } = useQuery<PortfolioSummary>({
    queryKey: ['portfolio'],
    queryFn: async () => {
      const response = await api.get('/holdings/portfolio');
      return response.data;
    },
  });

  const formatCurrency = (amount: number | null) => {
    if (amount === null || amount === undefined) return 'N/A';
    const num = Number(amount);
    if (isNaN(num)) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num);
  };

  const formatPercent = (percent: number | null) => {
    if (percent === null || percent === undefined) return 'N/A';
    const num = Number(percent);
    if (isNaN(num)) return 'N/A';
    return `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`;
  };

  const formatShares = (shares: number) => {
    const num = Number(shares);
    if (isNaN(num)) return '0';
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 6,
    }).format(num);
  };

  if (isLoading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" color="brand.500" />
      </Center>
    );
  }

  if (!portfolio || portfolio.holdings_by_ticker.length === 0) {
    return (
      <Container maxW="container.lg" py={8}>
        <VStack spacing={6} align="stretch">
          <Heading size="lg">Investments</Heading>
          <Card>
            <CardBody>
              <VStack spacing={4}>
                <Text color="gray.500">No investment holdings found.</Text>
                <Text fontSize="sm" color="gray.600">
                  Add investment accounts with holdings to see your portfolio here.
                </Text>
              </VStack>
            </CardBody>
          </Card>
        </VStack>
      </Container>
    );
  }

  const totalGainIsPositive = portfolio.total_gain_loss !== null && portfolio.total_gain_loss >= 0;

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <Heading size="lg">Investments</Heading>

        {/* Portfolio Summary Cards */}
        <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4}>
          {/* Total Value */}
          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Total Portfolio Value</StatLabel>
                <StatNumber fontSize="2xl">{formatCurrency(portfolio.total_value)}</StatNumber>
                {portfolio.total_cost_basis && (
                  <StatHelpText fontSize="sm">
                    Cost Basis: {formatCurrency(portfolio.total_cost_basis)}
                  </StatHelpText>
                )}
              </Stat>
            </CardBody>
          </Card>

          {/* Total Gain/Loss */}
          {portfolio.total_gain_loss !== null && (
            <Card>
              <CardBody>
                <Stat>
                  <StatLabel>Total Gain/Loss</StatLabel>
                  <StatNumber
                    fontSize="2xl"
                    color={totalGainIsPositive ? 'green.600' : 'red.600'}
                  >
                    {formatCurrency(portfolio.total_gain_loss)}
                  </StatNumber>
                  {portfolio.total_gain_loss_percent !== null && (
                    <StatHelpText>
                      <StatArrow type={totalGainIsPositive ? 'increase' : 'decrease'} />
                      {formatPercent(portfolio.total_gain_loss_percent)}
                    </StatHelpText>
                  )}
                </Stat>
              </CardBody>
            </Card>
          )}

          {/* Stocks */}
          {portfolio.stocks_value > 0 && (
            <Card>
              <CardBody>
                <Stat>
                  <StatLabel>Stocks</StatLabel>
                  <StatNumber fontSize="xl">{formatCurrency(portfolio.stocks_value)}</StatNumber>
                  <StatHelpText>
                    {((portfolio.stocks_value / portfolio.total_value) * 100).toFixed(1)}%
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>
          )}

          {/* ETFs */}
          {portfolio.etf_value > 0 && (
            <Card>
              <CardBody>
                <Stat>
                  <StatLabel>ETFs</StatLabel>
                  <StatNumber fontSize="xl">{formatCurrency(portfolio.etf_value)}</StatNumber>
                  <StatHelpText>
                    {((portfolio.etf_value / portfolio.total_value) * 100).toFixed(1)}%
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>
          )}
        </SimpleGrid>

        {/* Holdings Table */}
        <Card>
          <CardBody>
            <Heading size="md" mb={4}>
              Holdings
            </Heading>
            <Box overflowX="auto">
              <Table variant="simple" size="sm">
                <Thead>
                  <Tr>
                    <Th>Ticker</Th>
                    <Th>Name</Th>
                    <Th isNumeric>Shares</Th>
                    <Th isNumeric>Price</Th>
                    <Th isNumeric>Current Value</Th>
                    <Th isNumeric>Cost Basis</Th>
                    <Th isNumeric>Gain/Loss</Th>
                    <Th>Type</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {portfolio.holdings_by_ticker.map((holding) => {
                    const gainIsPositive = holding.gain_loss !== null && holding.gain_loss >= 0;

                    return (
                      <Tr key={holding.ticker}>
                        <Td>
                          <Text fontWeight="bold">{holding.ticker}</Text>
                        </Td>
                        <Td>
                          <Text fontSize="sm" color="gray.600">
                            {holding.name || '-'}
                          </Text>
                        </Td>
                        <Td isNumeric>{formatShares(holding.total_shares)}</Td>
                        <Td isNumeric>
                          {holding.current_price_per_share
                            ? formatCurrency(holding.current_price_per_share)
                            : 'N/A'}
                        </Td>
                        <Td isNumeric>
                          <Text fontWeight="semibold">
                            {formatCurrency(holding.current_total_value)}
                          </Text>
                        </Td>
                        <Td isNumeric>{formatCurrency(holding.total_cost_basis)}</Td>
                        <Td isNumeric>
                          {holding.gain_loss !== null ? (
                            <VStack spacing={0} align="flex-end">
                              <Text
                                fontWeight="semibold"
                                color={gainIsPositive ? 'green.600' : 'red.600'}
                              >
                                {formatCurrency(holding.gain_loss)}
                              </Text>
                              {holding.gain_loss_percent !== null && (
                                <Text
                                  fontSize="xs"
                                  color={gainIsPositive ? 'green.600' : 'red.600'}
                                >
                                  {formatPercent(holding.gain_loss_percent)}
                                </Text>
                              )}
                            </VStack>
                          ) : (
                            'N/A'
                          )}
                        </Td>
                        <Td>
                          {holding.asset_type && (
                            <Badge colorScheme="blue" size="sm">
                              {holding.asset_type}
                            </Badge>
                          )}
                        </Td>
                      </Tr>
                    );
                  })}
                </Tbody>
              </Table>
            </Box>
          </CardBody>
        </Card>
      </VStack>
    </Container>
  );
};
