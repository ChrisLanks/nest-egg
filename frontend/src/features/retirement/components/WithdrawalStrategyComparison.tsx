/**
 * Side-by-side comparison of tax-optimized vs simple rate withdrawal strategies.
 * Cards are clickable to select the active strategy.
 */

import {
  Badge,
  Box,
  HStack,
  SimpleGrid,
  Text,
  Tooltip,
  useColorModeValue,
  VStack,
} from '@chakra-ui/react';
import type { WithdrawalComparison, WithdrawalStrategy } from '../types/retirement';

interface WithdrawalStrategyComparisonProps {
  comparison: WithdrawalComparison | null;
  withdrawalRate: number;
  selectedStrategy?: WithdrawalStrategy;
  onStrategySelect?: (strategy: WithdrawalStrategy) => void;
  readOnly?: boolean;
}

export function WithdrawalStrategyComparison({
  comparison,
  withdrawalRate,
  selectedStrategy,
  onStrategySelect,
  readOnly,
}: WithdrawalStrategyComparisonProps) {
  const bgColor = useColorModeValue('white', 'gray.800');
  const labelColor = useColorModeValue('gray.500', 'gray.400');
  const winnerBg = useColorModeValue('green.50', 'green.900');
  const selectedBorder = useColorModeValue('blue.400', 'blue.300');
  const defaultBorder = useColorModeValue('gray.200', 'gray.600');

  if (!comparison) return null;

  const { tax_optimized, simple_rate } = comparison;

  const formatMoney = (amount: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(amount);

  const taxOptWins = tax_optimized.final_portfolio > simple_rate.final_portfolio;
  const isTaxOptSelected = selectedStrategy === 'tax_optimized';
  const isSimpleSelected = selectedStrategy === 'simple_rate';

  return (
    <Box bg={bgColor} p={5} borderRadius="xl" shadow="sm">
      <VStack spacing={4} align="stretch">
        <Tooltip
          label="Compare two approaches to taking money out in retirement. Click a card to use that strategy in your simulation."
          placement="top"
          hasArrow
        >
          <Text fontSize="lg" fontWeight="semibold" cursor="help">
            Withdrawal Strategy Comparison
          </Text>
        </Tooltip>

        <SimpleGrid columns={2} spacing={4}>
          {/* Tax-Optimized Column */}
          <Box
            p={3}
            borderRadius="md"
            bg={taxOptWins ? winnerBg : 'transparent'}
            border="2px solid"
            borderColor={isTaxOptSelected ? selectedBorder : taxOptWins ? 'green.200' : defaultBorder}
            cursor={readOnly ? 'default' : 'pointer'}
            onClick={readOnly ? undefined : () => onStrategySelect?.('tax_optimized')}
            _hover={readOnly ? undefined : { borderColor: selectedBorder, transition: 'border-color 0.2s' }}
          >
            <VStack spacing={2} align="stretch">
              <HStack justify="space-between">
                <Tooltip label="Withdraw from taxable accounts first, then pre-tax (401k/IRA), and preserve Roth accounts as long as possible to minimize lifetime taxes." placement="top" hasArrow>
                  <Text fontSize="sm" fontWeight="bold" cursor="help">
                    Tax-Optimized
                  </Text>
                </Tooltip>
                <HStack spacing={1}>
                  {isTaxOptSelected && (
                    <Badge colorScheme="blue" size="sm">
                      Selected
                    </Badge>
                  )}
                  {taxOptWins && (
                    <Badge colorScheme="green" size="sm">
                      Better
                    </Badge>
                  )}
                </HStack>
              </HStack>
              <Text fontSize="2xs" color={labelColor}>
                Taxable first, then pre-tax, Roth last
              </Text>

              <HStack justify="space-between" fontSize="xs">
                <Tooltip label="Projected portfolio value remaining at the end of your plan" placement="top" hasArrow>
                  <Text color={labelColor} cursor="help">Final Portfolio</Text>
                </Tooltip>
                <Text fontWeight="medium">{formatMoney(tax_optimized.final_portfolio)}</Text>
              </HStack>
              <HStack justify="space-between" fontSize="xs">
                <Tooltip label="Estimated total taxes paid on all withdrawals over the course of retirement" placement="top" hasArrow>
                  <Text color={labelColor} cursor="help">Total Taxes</Text>
                </Tooltip>
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
            border="2px solid"
            borderColor={isSimpleSelected ? selectedBorder : !taxOptWins ? 'green.200' : defaultBorder}
            cursor={readOnly ? 'default' : 'pointer'}
            onClick={readOnly ? undefined : () => onStrategySelect?.('simple_rate')}
            _hover={readOnly ? undefined : { borderColor: selectedBorder, transition: 'border-color 0.2s' }}
          >
            <VStack spacing={2} align="stretch">
              <HStack justify="space-between">
                <Tooltip label={`Withdraw a fixed ${withdrawalRate}% of your starting portfolio each year, adjusted for inflation. Simple and predictable, but doesn't optimize for taxes.`} placement="top" hasArrow>
                  <Text fontSize="sm" fontWeight="bold" cursor="help">
                    {withdrawalRate}% Rule
                  </Text>
                </Tooltip>
                <HStack spacing={1}>
                  {isSimpleSelected && (
                    <Badge colorScheme="blue" size="sm">
                      Selected
                    </Badge>
                  )}
                  {!taxOptWins && (
                    <Badge colorScheme="green" size="sm">
                      Better
                    </Badge>
                  )}
                </HStack>
              </HStack>
              <Text fontSize="2xs" color={labelColor}>
                Fixed {withdrawalRate}% of portfolio annually
              </Text>

              <HStack justify="space-between" fontSize="xs">
                <Tooltip label="Projected portfolio value remaining at the end of your plan" placement="top" hasArrow>
                  <Text color={labelColor} cursor="help">Final Portfolio</Text>
                </Tooltip>
                <Text fontWeight="medium">{formatMoney(simple_rate.final_portfolio)}</Text>
              </HStack>
              <HStack justify="space-between" fontSize="xs">
                <Tooltip label="Estimated total taxes paid on all withdrawals over the course of retirement" placement="top" hasArrow>
                  <Text color={labelColor} cursor="help">Total Taxes</Text>
                </Tooltip>
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
