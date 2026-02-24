/**
 * Tax-Loss Harvesting panel for the Investments page
 */

import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Card,
  CardBody,
  HStack,
  SimpleGrid,
  Spinner,
  Center,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Text,
  VStack,
  Tooltip,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import api from '../../../services/api';
import { useUserView } from '../../../contexts/UserViewContext';

interface TaxLossOpportunity {
  holding_id: string;
  ticker: string;
  name: string | null;
  shares: number;
  cost_basis: number;
  current_value: number;
  unrealized_loss: number;
  loss_percentage: number;
  estimated_tax_savings: number;
  wash_sale_risk: boolean;
  wash_sale_reason: string | null;
  sector: string | null;
  suggested_replacements: string[];
}

interface TaxLossHarvestingSummary {
  opportunities: TaxLossOpportunity[];
  total_harvestable_losses: number;
  total_estimated_tax_savings: number;
}

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);

export default function TaxLossHarvestingPanel() {
  const { selectedUserId } = useUserView();

  const { data, isLoading, error } = useQuery<TaxLossHarvestingSummary>({
    queryKey: ['taxLossHarvesting', selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const response = await api.get('/reports/tax-loss-harvesting', { params });
      return response.data;
    },
  });

  if (isLoading) {
    return (
      <Center py={12}>
        <Spinner size="xl" />
      </Center>
    );
  }

  if (error) {
    return (
      <Alert status="error">
        <AlertIcon />
        Failed to load tax-loss harvesting data.
      </Alert>
    );
  }

  if (!data || data.opportunities.length === 0) {
    return (
      <VStack spacing={4} py={8}>
        <Alert status="info">
          <AlertIcon />
          No tax-loss harvesting opportunities found. All holdings are at a gain or missing cost basis data.
        </Alert>
        <Text fontSize="xs" color="text.muted">
          Cost basis data is required to identify harvesting opportunities. Ensure your holdings have cost basis entered.
        </Text>
      </VStack>
    );
  }

  return (
    <VStack spacing={6} align="stretch">
      {/* Disclaimer */}
      <Alert status="warning" variant="subtle" borderRadius="md">
        <AlertIcon />
        <Text fontSize="sm">
          This analysis is for informational purposes only and does not constitute tax advice.
          Consult a qualified tax professional before making investment decisions.
        </Text>
      </Alert>

      {/* Summary cards */}
      <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
        <Card variant="outline">
          <CardBody py={3}>
            <Stat>
              <StatLabel fontSize="xs">Total Harvestable Losses</StatLabel>
              <StatNumber fontSize="lg" color="finance.negative">
                {formatCurrency(data.total_harvestable_losses)}
              </StatNumber>
              <StatHelpText fontSize="xs">
                {data.opportunities.length} position{data.opportunities.length !== 1 ? 's' : ''} with unrealized losses
              </StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card variant="outline">
          <CardBody py={3}>
            <Stat>
              <StatLabel fontSize="xs">Estimated Tax Savings</StatLabel>
              <StatNumber fontSize="lg" color="finance.positive">
                {formatCurrency(data.total_estimated_tax_savings)}
              </StatNumber>
              <StatHelpText fontSize="xs">
                At 27% combined tax rate (22% federal + 5% state)
              </StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card variant="outline">
          <CardBody py={3}>
            <Stat>
              <StatLabel fontSize="xs">Largest Opportunity</StatLabel>
              <StatNumber fontSize="lg">
                {data.opportunities[0]?.ticker ?? 'N/A'}
              </StatNumber>
              <StatHelpText fontSize="xs">
                {data.opportunities[0]
                  ? `${formatCurrency(data.opportunities[0].estimated_tax_savings)} potential savings`
                  : ''}
              </StatHelpText>
            </Stat>
          </CardBody>
        </Card>
      </SimpleGrid>

      {/* Opportunities table */}
      <Box overflowX="auto">
        <Table size="sm" variant="simple">
          <Thead>
            <Tr>
              <Th>Holding</Th>
              <Th isNumeric>Shares</Th>
              <Th isNumeric>Cost Basis</Th>
              <Th isNumeric>Current Value</Th>
              <Th isNumeric>Unrealized Loss</Th>
              <Th isNumeric>Est. Tax Savings</Th>
              <Th>Wash Sale</Th>
              <Th>Replacements</Th>
            </Tr>
          </Thead>
          <Tbody>
            {data.opportunities.map((opp) => (
              <Tr key={opp.holding_id}>
                <Td>
                  <VStack align="flex-start" spacing={0}>
                    <Text fontWeight="medium" fontSize="sm">{opp.ticker}</Text>
                    {opp.name && (
                      <Text fontSize="xs" color="text.muted" noOfLines={1}>
                        {opp.name}
                      </Text>
                    )}
                    {opp.sector && (
                      <Badge fontSize="2xs" colorScheme="gray">{opp.sector}</Badge>
                    )}
                  </VStack>
                </Td>
                <Td isNumeric fontSize="sm">
                  {new Intl.NumberFormat('en-US', { maximumFractionDigits: 4 }).format(opp.shares)}
                </Td>
                <Td isNumeric fontSize="sm">{formatCurrency(opp.cost_basis)}</Td>
                <Td isNumeric fontSize="sm">{formatCurrency(opp.current_value)}</Td>
                <Td isNumeric>
                  <VStack align="flex-end" spacing={0}>
                    <Text fontSize="sm" color="finance.negative" fontWeight="medium">
                      -{formatCurrency(opp.unrealized_loss)}
                    </Text>
                    <Text fontSize="xs" color="finance.negative">
                      -{Number(opp.loss_percentage).toFixed(1)}%
                    </Text>
                  </VStack>
                </Td>
                <Td isNumeric>
                  <Text fontSize="sm" color="finance.positive" fontWeight="medium">
                    {formatCurrency(opp.estimated_tax_savings)}
                  </Text>
                </Td>
                <Td>
                  {opp.wash_sale_risk ? (
                    <Tooltip label={opp.wash_sale_reason || 'Potential wash sale violation'}>
                      <Badge colorScheme="red" fontSize="xs">Risk</Badge>
                    </Tooltip>
                  ) : (
                    <Badge colorScheme="green" fontSize="xs">Clear</Badge>
                  )}
                </Td>
                <Td>
                  {opp.suggested_replacements.length > 0 ? (
                    <HStack spacing={1} flexWrap="wrap">
                      {opp.suggested_replacements.map((r) => (
                        <Badge key={r} fontSize="2xs" variant="outline">
                          {r}
                        </Badge>
                      ))}
                    </HStack>
                  ) : (
                    <Text fontSize="xs" color="text.muted">-</Text>
                  )}
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      </Box>
    </VStack>
  );
}
