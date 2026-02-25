import {
  Box,
  Card,
  CardBody,
  CircularProgress,
  CircularProgressLabel,
  Heading,
  HStack,
  Link,
  Spinner,
  Text,
  VStack,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { Link as RouterLink } from 'react-router-dom';
import api from '../../../services/api';

interface ScenarioSummary {
  id: string;
  name: string;
  retirement_age: number;
  is_default: boolean;
  readiness_score: number | null;
  success_rate: number | null;
  updated_at: string;
}

const scoreColor = (score: number): string => {
  if (score >= 70) return 'green.400';
  if (score >= 40) return 'yellow.400';
  return 'red.400';
};

const scoreScheme = (score: number): string => {
  if (score >= 70) return 'green';
  if (score >= 40) return 'yellow';
  return 'red';
};

export const RetirementReadinessWidget: React.FC = () => {
  const { data: scenarios, isLoading } = useQuery<ScenarioSummary[]>({
    queryKey: ['retirement-scenarios-widget'],
    queryFn: async () => {
      const { data } = await api.get<ScenarioSummary[]>('/retirement/scenarios');
      return data;
    },
    retry: false,
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

  const defaultScenario = scenarios?.find((s) => s.is_default) ?? scenarios?.[0];

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Retirement Readiness</Heading>
          <Link as={RouterLink} to="/retirement" fontSize="sm" color="brand.500">
            Plan details →
          </Link>
        </HStack>

        {!defaultScenario ? (
          <VStack spacing={3} py={4}>
            <Text color="text.muted" fontSize="sm" textAlign="center">
              No retirement scenarios yet.
            </Text>
            <Link
              as={RouterLink}
              to="/retirement"
              fontSize="sm"
              color="brand.500"
              fontWeight="medium"
            >
              Create your first plan →
            </Link>
          </VStack>
        ) : (
          <VStack spacing={4}>
            {defaultScenario.readiness_score !== null ? (
              <CircularProgress
                value={defaultScenario.readiness_score}
                size="100px"
                thickness="10px"
                color={scoreColor(defaultScenario.readiness_score)}
                trackColor="gray.100"
              >
                <CircularProgressLabel fontWeight="bold" fontSize="xl">
                  {defaultScenario.readiness_score}
                </CircularProgressLabel>
              </CircularProgress>
            ) : (
              <Box py={2}>
                <Text color="text.muted" fontSize="sm" textAlign="center">
                  Run a simulation to see your score
                </Text>
              </Box>
            )}

            <VStack spacing={1}>
              <Text fontWeight="medium" fontSize="sm">
                {defaultScenario.name}
              </Text>
              <Text color="text.secondary" fontSize="xs">
                Retire at {defaultScenario.retirement_age}
              </Text>
              {defaultScenario.success_rate !== null && (
                <Text
                  fontSize="xs"
                  color={scoreColor(defaultScenario.success_rate)}
                  fontWeight="medium"
                >
                  {defaultScenario.success_rate.toFixed(0)}% success rate
                </Text>
              )}
            </VStack>
          </VStack>
        )}
      </CardBody>
    </Card>
  );
};
