/**
 * Side-by-side comparison of tax-optimized vs simple rate withdrawal strategies.
 */

import {
  Badge,
  Box,
  HStack,
  SimpleGrid,
  Text,
  useColorModeValue,
  VStack,
} from '@chakra-ui/react';
import type { WithdrawalComparison } from '../types/retirement';

interface WithdrawalStrategyComparisonProps {
  comparison: WithdrawalComparison | null;
  withdrawalRate: number;
}

export function WithdrawalStrategyComparison({
  comparison,
  withdrawalRate,
}: WithdrawalStrategyComparisonProps) {
  const bgColor = useColorModeValue('white', 'gray.800');
  const labelColor = useColorModeValue('gray.500', 'gray.400');
  const winnerBg = useColorModeValue('green.50', 'green.900');

  if (!comparison) return null;

  const { tax_optimized, simple_rate } = comparison;

  const formatMoney = (amount: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(amount);

  const taxOptWins = tax_optimized.final_portfolio > simple_rate.final_portfolio;

  return (
    <Box bg={bgColor} p={5} borderRadius="xl" shadow="sm">
      <VStack spacing={4} align="stretch">
        <Text fontSize="lg" fontWeight="semibold">
          Withdrawal Strategy Comparison
        </Text>

        <SimpleGrid columns={2} spacing={4}>
          {/* Tax-Optimized Column */}
          <Box
            p={3}
            borderRadius="md"
            bg={taxOptWins ? winnerBg : 'transparent'}
            border="1px solid"
            borderColor={taxOptWins ? 'green.200' : useColorModeValue('gray.200', 'gray.600')}
          >
            <VStack spacing={2} align="stretch">
              <HStack justify="space-between">
                <Text fontSize="sm" fontWeight="bold">
                  Tax-Optimized
                </Text>
                {taxOptWins && (
                  <Badge colorScheme="green" size="sm">
                    Better
                  </Badge>
                )}
              </HStack>
              <Text fontSize="2xs" color={labelColor}>
                Taxable first, then pre-tax, Roth last
              </Text>

              <HStack justify="space-between" fontSize="xs">
                <Text color={labelColor}>Final Portfolio</Text>
                <Text fontWeight="medium">{formatMoney(tax_optimized.final_portfolio)}</Text>
              </HStack>
              <HStack justify="space-between" fontSize="xs">
                <Text color={labelColor}>Total Taxes</Text>
                <Text fontWeight="medium">{formatMoney(tax_optimized.total_taxes_paid)}</Text>
              </HStack>
              {tax_optimized.depleted_age && (
                <HStack justify="space-between" fontSize="xs">
                  <Text color="red.400">Depleted Age</Text>
                  <Text fontWeight="medium" color="red.400">
                    {tax_optimized.depleted_age}
                  </Text>
                </HStack>
              )}
            </VStack>
          </Box>

          {/* Simple Rate Column */}
          <Box
            p={3}
            borderRadius="md"
            bg={!taxOptWins ? winnerBg : 'transparent'}
            border="1px solid"
            borderColor={!taxOptWins ? 'green.200' : useColorModeValue('gray.200', 'gray.600')}
          >
            <VStack spacing={2} align="stretch">
              <HStack justify="space-between">
                <Text fontSize="sm" fontWeight="bold">
                  {withdrawalRate}% Rule
                </Text>
                {!taxOptWins && (
                  <Badge colorScheme="green" size="sm">
                    Better
                  </Badge>
                )}
              </HStack>
              <Text fontSize="2xs" color={labelColor}>
                Fixed {withdrawalRate}% of portfolio annually
              </Text>

              <HStack justify="space-between" fontSize="xs">
                <Text color={labelColor}>Final Portfolio</Text>
                <Text fontWeight="medium">{formatMoney(simple_rate.final_portfolio)}</Text>
              </HStack>
              <HStack justify="space-between" fontSize="xs">
                <Text color={labelColor}>Total Taxes</Text>
                <Text fontWeight="medium">{formatMoney(simple_rate.total_taxes_paid)}</Text>
              </HStack>
              {simple_rate.depleted_age && (
                <HStack justify="space-between" fontSize="xs">
                  <Text color="red.400">Depleted Age</Text>
                  <Text fontWeight="medium" color="red.400">
                    {simple_rate.depleted_age}
                  </Text>
                </HStack>
              )}
            </VStack>
          </Box>
        </SimpleGrid>

        {/* Tax savings summary */}
        {tax_optimized.total_taxes_paid !== simple_rate.total_taxes_paid && (
          <Text fontSize="xs" color={labelColor} textAlign="center">
            Tax-optimized saves{' '}
            {formatMoney(
              Math.abs(simple_rate.total_taxes_paid - tax_optimized.total_taxes_paid)
            )}{' '}
            in taxes over retirement
          </Text>
        )}
      </VStack>
    </Box>
  );
}
