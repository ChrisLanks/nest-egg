/**
 * Healthcare cost estimator card.
 * Shows cost phases: pre-65 insurance, Medicare at 65, IRMAA, LTC at 85+.
 */

import {
  Box,
  HStack,
  Spinner,
  Text,
  useColorModeValue,
  VStack,
} from '@chakra-ui/react';
import { useHealthcareEstimate } from '../hooks/useRetirementScenarios';

interface HealthcareEstimatorProps {
  retirementIncome?: number;
  medicalInflationRate?: number;
}

export function HealthcareEstimator({
  retirementIncome = 50000,
  medicalInflationRate = 6.0,
}: HealthcareEstimatorProps) {
  const bgColor = useColorModeValue('white', 'gray.800');
  const labelColor = useColorModeValue('gray.500', 'gray.400');
  const { data: estimate, isLoading } = useHealthcareEstimate(
    retirementIncome,
    medicalInflationRate
  );

  const formatMoney = (amount: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(amount);

  const phaseColor = (phase: string) => {
    switch (phase) {
      case 'pre65':
        return 'blue.400';
      case 'medicare':
        return 'green.400';
      case 'ltc':
        return 'red.400';
      default:
        return 'gray.400';
    }
  };

  return (
    <Box bg={bgColor} p={5} borderRadius="xl" shadow="sm">
      <VStack spacing={4} align="stretch">
        <HStack justify="space-between">
          <Text fontSize="lg" fontWeight="semibold">
            Healthcare Costs
          </Text>
          {isLoading && <Spinner size="sm" />}
        </HStack>

        {estimate && (
          <>
            {/* Cost phases */}
            <VStack spacing={2} align="stretch">
              {estimate.pre_65_annual > 0 && (
                <HStack justify="space-between">
                  <HStack spacing={2}>
                    <Box w={2} h={2} borderRadius="full" bg={phaseColor('pre65')} />
                    <Text fontSize="sm" color={labelColor}>
                      Pre-65 Insurance
                    </Text>
                  </HStack>
                  <Text fontSize="sm" fontWeight="medium">
                    {formatMoney(estimate.pre_65_annual)}/yr
                  </Text>
                </HStack>
              )}

              <HStack justify="space-between">
                <HStack spacing={2}>
                  <Box w={2} h={2} borderRadius="full" bg={phaseColor('medicare')} />
                  <Text fontSize="sm" color={labelColor}>
                    Medicare (65+)
                  </Text>
                </HStack>
                <Text fontSize="sm" fontWeight="medium">
                  {formatMoney(estimate.medicare_annual)}/yr
                </Text>
              </HStack>

              {estimate.ltc_annual > 0 && (
                <HStack justify="space-between">
                  <HStack spacing={2}>
                    <Box w={2} h={2} borderRadius="full" bg={phaseColor('ltc')} />
                    <Text fontSize="sm" color={labelColor}>
                      Long-Term Care (85+)
                    </Text>
                  </HStack>
                  <Text fontSize="sm" fontWeight="medium">
                    {formatMoney(estimate.ltc_annual)}/yr
                  </Text>
                </HStack>
              )}
            </VStack>

            {/* Sample age breakdown */}
            {estimate.sample_ages.length > 0 && (
              <Box>
                <Text fontSize="xs" fontWeight="semibold" color={labelColor} mb={2}>
                  Annual Cost by Age
                </Text>
                <VStack spacing={1} align="stretch">
                  {estimate.sample_ages
                    .filter((s) => s.total > 0)
                    .slice(0, 5)
                    .map((sample) => (
                      <HStack key={sample.age} justify="space-between" fontSize="xs">
                        <Text color={labelColor}>Age {sample.age}</Text>
                        <Text fontWeight="medium">{formatMoney(sample.total)}</Text>
                      </HStack>
                    ))}
                </VStack>
              </Box>
            )}

            <Text fontSize="xs" color={labelColor} pt={1}>
              Assumes {medicalInflationRate}% medical inflation. Costs are in today's dollars.
            </Text>
          </>
        )}
      </VStack>
    </Box>
  );
}
