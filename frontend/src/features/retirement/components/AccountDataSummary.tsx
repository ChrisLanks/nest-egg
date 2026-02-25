/**
 * Displays current account data relevant to retirement planning.
 * Shows portfolio breakdown by tax treatment bucket, with cash split out.
 * Optionally shows editable tax rates from the scenario.
 */

import {
  Box,
  HStack,
  IconButton,
  NumberInput,
  NumberInputField,
  Progress,
  Spinner,
  Text,
  useColorModeValue,
  VStack,
} from '@chakra-ui/react';
import { useCallback, useMemo, useState } from 'react';
import { FiCheck, FiEdit2 } from 'react-icons/fi';
import { useRetirementAccountData } from '../hooks/useRetirementScenarios';
import type { RetirementScenario } from '../types/retirement';

interface AccountDataSummaryProps {
  scenario?: RetirementScenario | null;
  userId?: string;
  onTaxRateChange?: (updates: { federal_tax_rate?: number; state_tax_rate?: number; capital_gains_rate?: number }) => void;
}

export function AccountDataSummary({ scenario, userId, onTaxRateChange }: AccountDataSummaryProps) {
  const bgColor = useColorModeValue('white', 'gray.800');
  const labelColor = useColorModeValue('gray.500', 'gray.400');
  const borderColor = useColorModeValue('gray.100', 'gray.700');
  const editBg = useColorModeValue('gray.50', 'gray.700');

  const [isEditingTax, setIsEditingTax] = useState(false);
  const [localFederal, setLocalFederal] = useState(0);
  const [localState, setLocalState] = useState(0);
  const [localCapGains, setLocalCapGains] = useState(0);

  const handleToggleTaxEdit = useCallback(() => {
    if (isEditingTax) {
      // Save changes
      const changes: { federal_tax_rate?: number; state_tax_rate?: number; capital_gains_rate?: number } = {};
      if (scenario && localFederal !== Number(scenario.federal_tax_rate)) changes.federal_tax_rate = localFederal;
      if (scenario && localState !== Number(scenario.state_tax_rate)) changes.state_tax_rate = localState;
      if (scenario && localCapGains !== Number(scenario.capital_gains_rate)) changes.capital_gains_rate = localCapGains;
      if (Object.keys(changes).length > 0) onTaxRateChange?.(changes);
    } else {
      // Enter edit mode — sync local state
      setLocalFederal(Number(scenario?.federal_tax_rate ?? 22));
      setLocalState(Number(scenario?.state_tax_rate ?? 5));
      setLocalCapGains(Number(scenario?.capital_gains_rate ?? 15));
    }
    setIsEditingTax(!isEditingTax);
  }, [isEditingTax, localFederal, localState, localCapGains, scenario, onTaxRateChange]);

  const { data, isLoading } = useRetirementAccountData(userId);

  const formatMoney = (amount: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(amount);

  const bucketKeyMap: Record<string, string> = {
    pre_tax: 'Pre-Tax (401k, IRA)',
    roth: 'Roth',
    taxable: 'Taxable (Brokerage)',
    hsa: 'HSA',
    cash: 'Cash (Checking/Savings)',
  };

  const bucketColorMap: Record<string, string> = {
    pre_tax: 'blue',
    roth: 'green',
    taxable: 'orange',
    hsa: 'teal',
    cash: 'gray',
  };

  const buckets = useMemo(() => {
    if (!data) return [];
    const total = data.total_portfolio || 1;
    const brokerageBalance = data.taxable_balance - (data.cash_balance || 0);
    const items = [
      { key: 'pre_tax', label: 'Pre-Tax (401k, IRA)', value: data.pre_tax_balance, pct: (data.pre_tax_balance / total) * 100, color: 'blue' },
      { key: 'roth', label: 'Roth', value: data.roth_balance, pct: (data.roth_balance / total) * 100, color: 'green' },
      { key: 'taxable', label: 'Taxable (Brokerage)', value: brokerageBalance, pct: (brokerageBalance / total) * 100, color: 'orange' },
      { key: 'hsa', label: 'HSA', value: data.hsa_balance, pct: (data.hsa_balance / total) * 100, color: 'teal' },
      { key: 'cash', label: 'Cash (Checking/Savings)', value: data.cash_balance || 0, pct: ((data.cash_balance || 0) / total) * 100, color: 'gray' },
    ];
    return items.filter((b) => b.value > 0);
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

            {/* Bucket breakdown with individual accounts */}
            <VStack spacing={3} align="stretch">
              {buckets.map((bucket) => {
                const bucketAccounts = data.accounts?.filter((a) => a.bucket === bucket.key) ?? [];
                return (
                  <Box key={bucket.key}>
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
                    {bucketAccounts.length > 0 && (
                      <VStack spacing={0} align="stretch" pl={3} mt={1}>
                        {bucketAccounts.map((acct, idx) => (
                          <HStack key={`${acct.name}-${idx}`} justify="space-between" fontSize="2xs">
                            <Text color={labelColor} noOfLines={1}>{acct.name}</Text>
                            <Text color={labelColor} flexShrink={0}>{formatMoney(acct.balance)}</Text>
                          </HStack>
                        ))}
                      </VStack>
                    )}
                  </Box>
                );
              })}
            </VStack>

            {/* Income & Contributions */}
            <VStack spacing={1} align="stretch" pt={2} borderTop="1px" borderColor={borderColor}>
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

            {/* Tax Rates from Scenario */}
            {scenario && (
              <VStack spacing={1} align="stretch" pt={2} borderTop="1px" borderColor={borderColor}>
                <HStack justify="space-between">
                  <Text fontSize="xs" fontWeight="semibold" color={labelColor}>
                    Tax Assumptions
                  </Text>
                  <IconButton
                    aria-label={isEditingTax ? 'Save tax rates' : 'Edit tax rates'}
                    icon={isEditingTax ? <FiCheck /> : <FiEdit2 />}
                    size="xs"
                    variant="ghost"
                    onClick={handleToggleTaxEdit}
                  />
                </HStack>
                {isEditingTax ? (
                  <VStack spacing={2} align="stretch" p={2} bg={editBg} borderRadius="md">
                    <HStack justify="space-between" fontSize="xs">
                      <Text color={labelColor}>Federal Tax Rate</Text>
                      <NumberInput
                        value={localFederal}
                        min={0}
                        max={50}
                        step={0.5}
                        size="xs"
                        w="80px"
                        onChange={(_, val) => { if (!isNaN(val)) setLocalFederal(val); }}
                      >
                        <NumberInputField textAlign="right" pr={1} />
                      </NumberInput>
                    </HStack>
                    <HStack justify="space-between" fontSize="xs">
                      <Text color={labelColor}>State Tax Rate</Text>
                      <NumberInput
                        value={localState}
                        min={0}
                        max={20}
                        step={0.5}
                        size="xs"
                        w="80px"
                        onChange={(_, val) => { if (!isNaN(val)) setLocalState(val); }}
                      >
                        <NumberInputField textAlign="right" pr={1} />
                      </NumberInput>
                    </HStack>
                    <HStack justify="space-between" fontSize="xs">
                      <Text color={labelColor}>Capital Gains Rate</Text>
                      <NumberInput
                        value={localCapGains}
                        min={0}
                        max={30}
                        step={0.5}
                        size="xs"
                        w="80px"
                        onChange={(_, val) => { if (!isNaN(val)) setLocalCapGains(val); }}
                      >
                        <NumberInputField textAlign="right" pr={1} />
                      </NumberInput>
                    </HStack>
                  </VStack>
                ) : (
                  <>
                    <HStack justify="space-between" fontSize="xs">
                      <Text color={labelColor}>Federal Tax Rate</Text>
                      <Text fontWeight="medium">{scenario.federal_tax_rate}%</Text>
                    </HStack>
                    <HStack justify="space-between" fontSize="xs">
                      <Text color={labelColor}>State Tax Rate</Text>
                      <Text fontWeight="medium">{scenario.state_tax_rate}%</Text>
                    </HStack>
                    <HStack justify="space-between" fontSize="xs">
                      <Text color={labelColor}>Capital Gains Rate</Text>
                      <Text fontWeight="medium">{scenario.capital_gains_rate}%</Text>
                    </HStack>
                  </>
                )}
              </VStack>
            )}
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
