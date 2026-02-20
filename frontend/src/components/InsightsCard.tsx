import {
  Card,
  CardBody,
  Heading,
  VStack,
  HStack,
  Text,
  Spinner,
  Center,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import api from '../services/api';

interface SpendingInsight {
  type: string;
  title: string;
  message: string;
  category?: string;
  amount?: number;
  percentage_change?: number;
  priority: string;
  icon: string;
}

export const InsightsCard = () => {
  const { data: insights, isLoading, isError } = useQuery({
    queryKey: ['spending-insights'],
    queryFn: async () => {
      const response = await api.get<SpendingInsight[]>('/dashboard/insights');
      return response.data;
    },
  });

  if (isLoading) {
    return (
      <Card>
        <CardBody>
          <Center py={4}>
            <Spinner />
          </Center>
        </CardBody>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card>
        <CardBody>
          <Alert status="error" borderRadius="md">
            <AlertIcon />
            <Text fontSize="sm">Unable to load spending insights.</Text>
          </Alert>
        </CardBody>
      </Card>
    );
  }

  if (!insights || insights.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardBody>
        <Heading size="md" mb={4}>
          💡 Spending Insights
        </Heading>
        <VStack align="stretch" spacing={3}>
          {insights.map((insight, idx) => (
            <HStack
              key={idx}
              p={3}
              bg={insight.priority === 'high' ? 'red.50' : insight.priority === 'medium' ? 'orange.50' : 'blue.50'}
              borderRadius="md"
              borderLeft="4px solid"
              borderLeftColor={
                insight.priority === 'high'
                  ? 'red.500'
                  : insight.priority === 'medium'
                  ? 'orange.500'
                  : 'blue.500'
              }
              transition="all 0.2s"
              _hover={{
                transform: 'translateX(2px)',
                shadow: 'sm',
              }}
            >
              <Text fontSize="2xl" flexShrink={0}>
                {insight.icon}
              </Text>
              <VStack align="start" spacing={0} flex={1}>
                <Text fontWeight="semibold" fontSize="sm" color="gray.800">
                  {insight.title}
                </Text>
                <Text fontSize="xs" color="gray.600">
                  {insight.message}
                </Text>
              </VStack>
            </HStack>
          ))}
        </VStack>
      </CardBody>
    </Card>
  );
};
