import {
  Box,
  Card,
  CardBody,
  CircularProgress,
  CircularProgressLabel,
  Heading,
  HStack,
  Link,
  Select,
  Spinner,
  Text,
  VStack,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
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

export const RetirementReadinessWidget: React.FC = () => {
  const [selectedId, setSelectedId] = useState<string | null>(null);

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

  const activeScenario = selectedId
    ? scenarios?.find((s) => s.id === selectedId)
    : (scenarios?.find((s) => s.is_default) ?? scenarios?.[0]);

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Retirement Readiness</Heading>
          <Link as={RouterLink} to="/retirement" fontSize="sm" color="brand.500">
            Plan details →
          </Link>
        </HStack>

        {!scenarios?.length ? (
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
            {/* Scenario selector */}
            {scenarios.length > 1 && (
              <Select
                size="xs"
                value={activeScenario?.id ?? ''}
                onChange={(e) => setSelectedId(e.target.value || null)}
                borderRadius="md"
              >
                {scenarios.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </Select>
            )}

            {activeScenario?.readiness_score !== null && activeScenario?.readiness_score !== undefined ? (
              <CircularProgress
                value={activeScenario.readiness_score}
                size="100px"
                thickness="10px"
                color={scoreColor(activeScenario.readiness_score)}
                trackColor="gray.100"
              >
                <CircularProgressLabel fontWeight="bold" fontSize="xl">
                  {activeScenario.readiness_score}
                </CircularProgressLabel>
              </CircularProgress>
            ) : (
              <Box py={2}>
                <Text color="text.muted" fontSize="sm" textAlign="center">
                  Run a simulation to see your score
                </Text>
              </Box>
            )}

            {activeScenario && (
              <VStack spacing={1}>
                {scenarios.length <= 1 && (
                  <Text fontWeight="medium" fontSize="sm">
                    {activeScenario.name}
                  </Text>
                )}
                <Text color="text.secondary" fontSize="xs">
                  Retire at {activeScenario.retirement_age}
                </Text>
                {activeScenario.success_rate !== null && (
                  <Text
                    fontSize="xs"
                    color={scoreColor(activeScenario.success_rate)}
                    fontWeight="medium"
                  >
                    {activeScenario.success_rate.toFixed(0)}% success rate
                  </Text>
                )}
              </VStack>
            )}
          </VStack>
        )}
      </CardBody>
    </Card>
  );
};
