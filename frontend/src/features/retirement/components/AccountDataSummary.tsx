/**
 * Displays current account data relevant to retirement planning.
 * Shows portfolio breakdown by tax treatment bucket.
 */

import {
  Box,
  HStack,
  Progress,
  Spinner,
  Text,
  useColorModeValue,
  VStack,
} from '@chakra-ui/react';
import { useMemo } from 'react';
import { useRetirementAccountData } from '../hooks/useRetirementScenarios';

export function AccountDataSummary() {
  const bgColor = useColorModeValue('white', 'gray.800');
  const labelColor = useColorModeValue('gray.500', 'gray.400');

  const { data, isLoading } = useRetirementAccountData();

  const formatMoney = (amount: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(amount);

  const buckets = useMemo(() => {
    if (!data) return [];
    const total = data.total_portfolio || 1;
    return [
      {
        label: 'Pre-Tax (401k, IRA)',
        value: data.pre_tax_balance,
        pct: (data.pre_tax_balance / total) * 100,
        color: 'blue',
      },
      {
        label: 'Roth',
        value: data.roth_balance,
        pct: (data.roth_balance / total) * 100,
        color: 'green',
      },
      {
        label: 'Taxable (Brokerage)',
        value: data.taxable_balance,
        pct: (data.taxable_balance / total) * 100,
        color: 'orange',
      },
      {
        label: 'HSA',
        value: data.hsa_balance,
        pct: (data.hsa_balance / total) * 100,
        color: 'teal',
      },
    ].filter((b) => b.value > 0);
  }, [data]);

  return (
    <Box bg={bgColor} p={5} borderRadius="xl" shadow="sm">
      <VStack spacing={4} align="stretch">
        <HStack justify="space-between">
          <Text fontSize="lg" fontWeight="semibold">
            Your Portfolio
          </Text>
          {isLoading && <Spinner size="sm" />}
        </HStack>

        {data && (
          <>
            <Text fontSize="2xl" fontWeight="bold">
              {formatMoney(data.total_portfolio)}
            </Text>

            {/* Bucket breakdown */}
            <VStack spacing={2} align="stretch">
              {buckets.map((bucket) => (
                <Box key={bucket.label}>
                  <HStack justify="space-between" fontSize="xs" mb={1}>
                    <Text color={labelColor}>{bucket.label}</Text>
                    <Text fontWeight="medium">
                      {formatMoney(bucket.value)} ({bucket.pct.toFixed(0)}%)
                    </Text>
                  </HStack>
                  <Progress
                    value={bucket.pct}
                    size="xs"
                    colorScheme={bucket.color}
                    borderRadius="full"
                  />
                </Box>
              ))}
            </VStack>

            {/* Income & Contributions */}
            <VStack spacing={1} align="stretch" pt={2} borderTop="1px" borderColor={useColorModeValue('gray.100', 'gray.700')}>
              {data.annual_income > 0 && (
                <HStack justify="space-between" fontSize="xs">
                  <Text color={labelColor}>Annual Income</Text>
                  <Text fontWeight="medium">{formatMoney(data.annual_income)}</Text>
                </HStack>
              )}
              {data.annual_contributions > 0 && (
                <HStack justify="space-between" fontSize="xs">
                  <Text color={labelColor}>Annual Contributions</Text>
                  <Text fontWeight="medium">{formatMoney(data.annual_contributions)}</Text>
                </HStack>
              )}
              {data.employer_match_annual > 0 && (
                <HStack justify="space-between" fontSize="xs">
                  <Text color={labelColor}>Employer Match</Text>
                  <Text fontWeight="medium">{formatMoney(data.employer_match_annual)}</Text>
                </HStack>
              )}
              {data.pension_monthly > 0 && (
                <HStack justify="space-between" fontSize="xs">
                  <Text color={labelColor}>Pension</Text>
                  <Text fontWeight="medium">{formatMoney(data.pension_monthly)}/mo</Text>
                </HStack>
              )}
              {data.annual_income > 0 && data.annual_contributions > 0 && (
                <HStack justify="space-between" fontSize="xs" pt={1}>
                  <Text color={labelColor}>Savings Rate</Text>
                  <Text
                    fontWeight="medium"
                    color={
                      ((data.annual_contributions + data.employer_match_annual) / data.annual_income) >= 0.15
                        ? 'green.400'
                        : 'yellow.400'
                    }
                  >
                    {(((data.annual_contributions + data.employer_match_annual) / data.annual_income) * 100).toFixed(0)}%
                  </Text>
                </HStack>
              )}
            </VStack>
          </>
        )}

        {!data && !isLoading && (
          <Text fontSize="sm" color={labelColor}>
            No accounts found. Add accounts to see your portfolio breakdown.
          </Text>
        )}
      </VStack>
    </Box>
  );
}
