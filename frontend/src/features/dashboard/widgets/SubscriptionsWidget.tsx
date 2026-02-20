import {
  Box,
  Card,
  CardBody,
  Divider,
  Heading,
  HStack,
  Link,
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
import { subscriptionsApi } from '../../../api/subscriptions';

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

const frequencyLabel = (freq: string) => {
  const map: Record<string, string> = {
    weekly: 'Weekly',
    biweekly: 'Biweekly',
    monthly: 'Monthly',
    quarterly: 'Quarterly',
    yearly: 'Yearly',
  };
  return map[freq] ?? freq;
};

export const SubscriptionsWidget: React.FC = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['subscriptions-widget'],
    queryFn: () => subscriptionsApi.get(),
  });

  if (isLoading) {
    return (
      <Card h="100%">
        <CardBody display="flex" alignItems="center" justifyContent="center">
          <Spinner />
        </CardBody>
      </Card>
    );
  }

  const subs = data?.subscriptions ?? [];

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Subscriptions</Heading>
          <Link as={RouterLink} to="/subscriptions" fontSize="sm" color="brand.500">
            View all →
          </Link>
        </HStack>

        {subs.length === 0 ? (
          <Text color="gray.500" fontSize="sm">
            No subscriptions detected yet. Import transactions to get started.
          </Text>
        ) : (
          <>
            <Stat mb={4}>
              <StatLabel>Monthly Cost</StatLabel>
              <StatNumber color="red.600">{formatCurrency(data?.monthly_cost ?? 0)}</StatNumber>
              <StatHelpText>{formatCurrency((data?.yearly_cost ?? 0))} / year</StatHelpText>
            </Stat>

            <VStack align="stretch" spacing={0}>
              {subs.slice(0, 5).map((sub, index) => (
                <Box key={sub.id}>
                  <HStack justify="space-between" py={2.5} px={1}>
                    <VStack align="start" spacing={0} flex={1} minW={0}>
                      <Text fontWeight="medium" fontSize="sm" noOfLines={1}>
                        {sub.merchant_name}
                      </Text>
                      <Text fontSize="xs" color="gray.500">
                        {frequencyLabel(sub.frequency)}
                      </Text>
                    </VStack>
                    <Text fontWeight="bold" fontSize="sm" flexShrink={0}>
                      {formatCurrency(sub.average_amount)}
                    </Text>
                  </HStack>
                  {index < Math.min(subs.length, 5) - 1 && <Divider />}
                </Box>
              ))}
            </VStack>
          </>
        )}
      </CardBody>
    </Card>
  );
};
