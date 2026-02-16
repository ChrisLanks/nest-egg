import {
  Container,
  VStack,
  Heading,
  Text,
  SimpleGrid,
  Card,
  CardBody,
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
  Badge,
  Button,
  Spinner,
  Center,
  Box,
  useToast,
} from '@chakra-ui/react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { EmptyState } from '../components/EmptyState';

interface Subscription {
  id: string;
  merchant_name: string;
  average_amount: number;
  frequency: string;
  next_expected_date: string | null;
  confidence_score: number;
  account_id: string;
  occurrence_count: number;
}

interface SubscriptionSummary {
  subscriptions: Subscription[];
  total_count: number;
  monthly_cost: number;
  yearly_cost: number;
}

export const SubscriptionsPage = () => {
  const queryClient = useQueryClient();
  const toast = useToast();

  const { data, isLoading } = useQuery({
    queryKey: ['subscriptions'],
    queryFn: async () => {
      const response = await api.get<SubscriptionSummary>('/subscriptions/');
      return response.data;
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: async (subscriptionId: string) => {
      await api.patch(`/subscriptions/${subscriptionId}/deactivate`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] });
      toast({
        title: 'Marked as not a subscription',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    },
    onError: () => {
      toast({
        title: 'Failed to update subscription',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    },
  });

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  if (isLoading) {
    return (
      <Center h="50vh">
        <Spinner size="xl" color="brand.500" />
      </Center>
    );
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={8} align="stretch">
        {/* Header */}
        <Box>
          <Heading>Subscriptions</Heading>
          <Text color="gray.600" mt={2}>
            Track your recurring charges and subscriptions
          </Text>
        </Box>

        {/* Summary Cards */}
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Active Subscriptions</StatLabel>
                <StatNumber>{data?.total_count || 0}</StatNumber>
                <StatHelpText>Detected automatically</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Monthly Cost</StatLabel>
                <StatNumber color="red.600">
                  {formatCurrency(data?.monthly_cost || 0)}
                </StatNumber>
                <StatHelpText>Recurring charges</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Yearly Cost</StatLabel>
                <StatNumber>{formatCurrency(data?.yearly_cost || 0)}</StatNumber>
                <StatHelpText>Annual total</StatHelpText>
              </Stat>
            </CardBody>
          </Card>
        </SimpleGrid>

        {/* Subscription List */}
        <Card>
          <CardBody>
            {data?.subscriptions && data.subscriptions.length > 0 ? (
              <Table variant="simple">
                <Thead>
                  <Tr>
                    <Th>Service</Th>
                    <Th isNumeric>Amount</Th>
                    <Th>Frequency</Th>
                    <Th>Next Charge</Th>
                    <Th>Confidence</Th>
                    <Th>Actions</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {data.subscriptions.map((sub) => (
                    <Tr key={sub.id}>
                      <Td fontWeight="medium">{sub.merchant_name}</Td>
                      <Td isNumeric>{formatCurrency(sub.average_amount)}</Td>
                      <Td>
                        <Badge colorScheme="purple" fontSize="xs">
                          {sub.frequency}
                        </Badge>
                      </Td>
                      <Td>{formatDate(sub.next_expected_date)}</Td>
                      <Td>
                        <Badge
                          colorScheme={sub.confidence_score > 0.85 ? 'green' : 'yellow'}
                          fontSize="xs"
                        >
                          {(sub.confidence_score * 100).toFixed(0)}%
                        </Badge>
                      </Td>
                      <Td>
                        <Button
                          size="sm"
                          variant="ghost"
                          colorScheme="red"
                          onClick={() => deactivateMutation.mutate(sub.id)}
                          isLoading={deactivateMutation.isPending}
                        >
                          Not a subscription
                        </Button>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            ) : (
              <EmptyState
                title="No subscriptions detected"
                description="We'll automatically detect recurring charges as transactions are imported. Subscriptions are identified by monthly or yearly payment patterns with high confidence."
                icon="💳"
              />
            )}
          </CardBody>
        </Card>
      </VStack>
    </Container>
  );
};
