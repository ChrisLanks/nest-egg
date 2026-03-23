/**
 * Displays current account data relevant to retirement planning.
 * Shows portfolio breakdown by tax treatment bucket, with cash split out.
 * Optionally shows editable tax rates from the scenario.
 * Each account has an include/exclude toggle — excluded accounts are shown
 * greyed out and not counted in the simulation.
 */

import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Checkbox,
  HStack,
  IconButton,
  NumberInput,
  NumberInputField,
  Progress,
  Spinner,
  Text,
  Tooltip,
  useColorModeValue,
  VStack,
} from "@chakra-ui/react";
import { useCallback, useMemo, useState } from "react";
import { FiCheck, FiEdit2 } from "react-icons/fi";
import { useRetirementAccountData } from "../hooks/useRetirementScenarios";
import type { RetirementScenario } from "../types/retirement";

interface AccountDataSummaryProps {
  scenario?: RetirementScenario | null;
  userId?: string;
  onTaxRateChange?: (updates: {
    federal_tax_rate?: number;
    state_tax_rate?: number;
    capital_gains_rate?: number;
  }) => void;
  onExcludedAccountsChange?: (excludedIds: string[]) => void;
  readOnly?: boolean;
}

export function AccountDataSummary({
  scenario,
  userId,
  onTaxRateChange,
  onExcludedAccountsChange,
  readOnly,
}: AccountDataSummaryProps) {
  const bgColor = useColorModeValue("white", "gray.800");
  const labelColor = useColorModeValue("gray.500", "gray.400");
  const borderColor = useColorModeValue("gray.100", "gray.700");
  const editBg = useColorModeValue("gray.50", "gray.700");
  const excludedBg = useColorModeValue("gray.50", "gray.750");

  const [isEditingTax, setIsEditingTax] = useState(false);
  const [localFederal, setLocalFederal] = useState(0);
  const [localState, setLocalState] = useState(0);
  const [localCapGains, setLocalCapGains] = useState(0);

  // Locally track excluded accounts so toggle is immediate
  const [localExcluded, setLocalExcluded] = useState<Set<string>>(
    () => new Set(scenario?.excluded_account_ids ?? []),
  );

  const handleToggleTaxEdit = useCallback(() => {
    if (isEditingTax) {
      // Save changes
      const changes: {
        federal_tax_rate?: number;
        state_tax_rate?: number;
        capital_gains_rate?: number;
      } = {};
      if (scenario && localFederal !== Number(scenario.federal_tax_rate))
        changes.federal_tax_rate = localFederal;
      if (scenario && localState !== Number(scenario.state_tax_rate))
        changes.state_tax_rate = localState;
      if (scenario && localCapGains !== Number(scenario.capital_gains_rate))
        changes.capital_gains_rate = localCapGains;
      if (Object.keys(changes).length > 0) onTaxRateChange?.(changes);
    } else {
      // Enter edit mode — sync local state
      setLocalFederal(Number(scenario?.federal_tax_rate ?? 22));
      setLocalState(Number(scenario?.state_tax_rate ?? 5));
      setLocalCapGains(Number(scenario?.capital_gains_rate ?? 15));
    }
    setIsEditingTax(!isEditingTax);
  }, [
    isEditingTax,
    localFederal,
    localState,
    localCapGains,
    scenario,
    onTaxRateChange,
  ]);

  const handleToggleAccount = useCallback(
    (accountId: string, checked: boolean) => {
      setLocalExcluded((prev) => {
        const next = new Set(prev);
        if (checked) {
          next.delete(accountId); // include
        } else {
          next.add(accountId); // exclude
        }
        onExcludedAccountsChange?.([...next]);
        return next;
      });
    },
    [onExcludedAccountsChange],
  );

  const { data, isLoading, isError } = useRetirementAccountData(
    userId,
    scenario?.include_all_members,
    scenario?.household_member_ids ?? undefined,
  );

  const formatMoney = (amount: number) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(amount);

  const buckets = useMemo(() => {
    if (!data) return [];
    // Exclude excluded accounts from totals
    const includedAccounts = data.accounts?.filter((a) => !localExcluded.has(a.id)) ?? [];
    const total = includedAccounts.reduce((s, a) => s + (a.bucket !== "excluded" ? a.balance : 0), 0) || 1;
    const preTax = includedAccounts.filter((a) => a.bucket === "pre_tax").reduce((s, a) => s + a.balance, 0);
    const roth = includedAccounts.filter((a) => a.bucket === "roth").reduce((s, a) => s + a.balance, 0);
    const hsa = includedAccounts.filter((a) => a.bucket === "hsa").reduce((s, a) => s + a.balance, 0);
    const cash = includedAccounts.filter((a) => a.bucket === "cash").reduce((s, a) => s + a.balance, 0);
    const taxable = includedAccounts.filter((a) => a.bucket === "taxable").reduce((s, a) => s + a.balance, 0);
    const brokerage = taxable - cash;

    const items = [
      { key: "pre_tax", label: "Pre-Tax (401k, IRA)", value: preTax, pct: (preTax / total) * 100, color: "blue",
        tooltip: "Traditional 401(k), IRA, and similar accounts. Contributions were tax-deductible; withdrawals are taxed as ordinary income in retirement." },
      { key: "roth", label: "Roth", value: roth, pct: (roth / total) * 100, color: "green",
        tooltip: "Roth 401(k) and Roth IRA accounts. Contributions were after-tax; qualified withdrawals in retirement are completely tax-free." },
      { key: "taxable", label: "Taxable (Brokerage)", value: brokerage, pct: (brokerage / total) * 100, color: "orange",
        tooltip: "Regular brokerage accounts. No special tax advantages — gains are taxed each year and when you sell." },
      { key: "hsa", label: "HSA", value: hsa, pct: (hsa / total) * 100, color: "teal",
        tooltip: "Health Savings Account. Triple tax advantage: contributions are pre-tax, growth is tax-free, and withdrawals for qualified medical expenses are tax-free." },
      { key: "cash", label: "Cash (Checking/Savings)", value: cash, pct: (cash / total) * 100, color: "purple",
        tooltip: "Checking, savings, and money market accounts. Grows at the account's interest rate (shown per account), not the investment return rate." },
    ];
    return items.filter((b) => b.value > 0);
  }, [data, localExcluded]);

  return (
    <Box bg={bgColor} p={5} borderRadius="xl" shadow="sm">
      <VStack spacing={4} align="stretch">
        <HStack justify="space-between">
          <Tooltip
            label="Total value of all included investment and cash accounts. Toggle individual accounts below to include or exclude them from the simulation."
            placement="top"
            hasArrow
          >
            <Text fontSize="lg" fontWeight="semibold" cursor="help">
              Your Portfolio
            </Text>
          </Tooltip>
          {isLoading && <Spinner size="sm" />}
        </HStack>

        {data && (
          <>
            <Text fontSize="2xl" fontWeight="bold">
              {formatMoney(
                (data.accounts ?? [])
                  .filter((a) => !localExcluded.has(a.id) && a.bucket !== "excluded")
                  .reduce((s, a) => s + a.balance, 0),
              )}
            </Text>

            {/* Bucket breakdown with individual accounts + exclude toggles */}
            <VStack spacing={3} align="stretch">
              {buckets.map((bucket) => {
                const bucketAccounts =
                  data.accounts?.filter((a) => a.bucket === bucket.key) ?? [];
                return (
                  <Box key={bucket.key}>
                    <HStack justify="space-between" fontSize="xs" mb={1}>
                      <Tooltip label={bucket.tooltip} placement="top" hasArrow>
                        <Text color={labelColor} cursor="help">{bucket.label}</Text>
                      </Tooltip>
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
                        {bucketAccounts.map((acct) => {
                          const isExcluded = localExcluded.has(acct.id);
                          return (
                            <HStack
                              key={acct.id}
                              justify="space-between"
                              fontSize="2xs"
                              opacity={isExcluded ? 0.45 : 1}
                              bg={isExcluded ? excludedBg : undefined}
                              borderRadius="sm"
                              px={isExcluded ? 1 : 0}
                            >
                              {!readOnly && (
                                <Tooltip
                                  label={
                                    isExcluded
                                      ? "Include in simulation"
                                      : "Exclude from simulation"
                                  }
                                  placement="top"
                                  hasArrow
                                >
                                  <Checkbox
                                    size="xs"
                                    isChecked={!isExcluded}
                                    onChange={(e) =>
                                      handleToggleAccount(acct.id, e.target.checked)
                                    }
                                    mr={1}
                                  />
                                </Tooltip>
                              )}
                              <Text color={labelColor} noOfLines={1} flex={1}>
                                {acct.name}
                              </Text>
                              <HStack spacing={1} flexShrink={0}>
                                {acct.bucket === "cash" && acct.interest_rate != null && (
                                  <Tooltip
                                    label={
                                      acct.interest_rate > 0
                                        ? `Earns ${acct.interest_rate.toFixed(2)}% APR — used as growth rate`
                                        : "No interest rate set — grows at 0% (like cash under a sofa)"
                                    }
                                    placement="top"
                                    hasArrow
                                  >
                                    <Badge
                                      fontSize="2xs"
                                      colorScheme={acct.interest_rate > 0 ? "green" : "gray"}
                                      variant="subtle"
                                    >
                                      {acct.interest_rate > 0
                                        ? `${acct.interest_rate.toFixed(2)}%`
                                        : "0%"}
                                    </Badge>
                                  </Tooltip>
                                )}
                                <Text color={labelColor}>
                                  {formatMoney(acct.balance)}
                                </Text>
                              </HStack>
                            </HStack>
                          );
                        })}
                      </VStack>
                    )}
                  </Box>
                );
              })}

              {/* Excluded accounts section */}
              {data.accounts?.some((a) => localExcluded.has(a.id)) && (
                <Box>
                  <Tooltip label="These accounts are not counted in the simulation. Check the box next to any account to re-include it." placement="top" hasArrow>
                    <Text fontSize="2xs" color={labelColor} mb={1} cursor="help">
                      Excluded from simulation
                    </Text>
                  </Tooltip>
                  <VStack spacing={0} align="stretch" pl={3}>
                    {data.accounts
                      .filter((a) => localExcluded.has(a.id))
                      .map((acct) => (
                        <HStack
                          key={acct.id}
                          justify="space-between"
                          fontSize="2xs"
                        >
                          {!readOnly && (
                            <Tooltip
                              label="Re-include in simulation"
                              placement="top"
                              hasArrow
                            >
                              <Checkbox
                                size="sm"
                                isChecked={false}
                                onChange={(e) =>
                                  handleToggleAccount(acct.id, e.target.checked)
                                }
                                mr={1}
                                colorScheme="blue"
                              />
                            </Tooltip>
                          )}
                          <Text color={labelColor} noOfLines={1} flex={1} opacity={0.45}>
                            {acct.name}
                          </Text>
                          <Text color={labelColor} flexShrink={0} opacity={0.45}>
                            {formatMoney(acct.balance)}
                          </Text>
                        </HStack>
                      ))}
                  </VStack>
                </Box>
              )}
            </VStack>

            {/* Income & Contributions */}
            <VStack
              spacing={1}
              align="stretch"
              pt={2}
              borderTop="1px"
              borderColor={borderColor}
            >
              {data.annual_income > 0 && (
                <HStack justify="space-between" fontSize="xs">
                  <Tooltip label="Your current annual salary — used to estimate future contributions and Social Security benefits" placement="top" hasArrow>
                    <Text color={labelColor} cursor="help">Annual Income</Text>
                  </Tooltip>
                  <Text fontWeight="medium">
                    {formatMoney(data.annual_income)}
                  </Text>
                </HStack>
              )}
              {data.annual_contributions > 0 && (
                <HStack justify="space-between" fontSize="xs">
                  <Tooltip label="How much you're contributing to retirement accounts each year (401k, IRA, etc.)" placement="top" hasArrow>
                    <Text color={labelColor} cursor="help">Annual Contributions</Text>
                  </Tooltip>
                  <Text fontWeight="medium">
                    {formatMoney(data.annual_contributions)}
                  </Text>
                </HStack>
              )}
              {data.employer_match_annual > 0 && (
                <HStack justify="space-between" fontSize="xs">
                  <Tooltip label="Free money from your employer — added on top of your own contributions in the simulation" placement="top" hasArrow>
                    <Text color={labelColor} cursor="help">Employer Match</Text>
                  </Tooltip>
                  <Text fontWeight="medium">
                    {formatMoney(data.employer_match_annual)}
                  </Text>
                </HStack>
              )}
              {data.pension_monthly > 0 && (
                <HStack justify="space-between" fontSize="xs">
                  <Tooltip label="Guaranteed monthly income from a pension plan — added to your income in retirement alongside Social Security" placement="top" hasArrow>
                    <Text color={labelColor} cursor="help">Pension</Text>
                  </Tooltip>
                  <Text fontWeight="medium">
                    {formatMoney(data.pension_monthly)}/mo
                  </Text>
                </HStack>
              )}
              {data.annual_income > 0 && data.annual_contributions > 0 && (
                <HStack justify="space-between" fontSize="xs" pt={1}>
                  <Tooltip label="Percentage of income going toward retirement. 15%+ (including employer match) is generally recommended" placement="top" hasArrow>
                    <Text color={labelColor} cursor="help">Savings Rate</Text>
                  </Tooltip>
                  <Text
                    fontWeight="medium"
                    color={
                      (data.annual_contributions + data.employer_match_annual) /
                        data.annual_income >=
                      0.15
                        ? "green.400"
                        : "yellow.400"
                    }
                  >
                    {(
                      ((data.annual_contributions +
                        data.employer_match_annual) /
                        data.annual_income) *
                      100
                    ).toFixed(0)}
                    %
                  </Text>
                </HStack>
              )}
            </VStack>

            {/* Tax Rates from Scenario */}
            {scenario && (
              <VStack
                spacing={1}
                align="stretch"
                pt={2}
                borderTop="1px"
                borderColor={borderColor}
              >
                <HStack justify="space-between">
                  <Tooltip label="These rates are used to estimate taxes on withdrawals during retirement. They affect how much of each withdrawal you actually keep." placement="top" hasArrow>
                    <Text fontSize="xs" fontWeight="semibold" color={labelColor} cursor="help">
                      Tax Assumptions
                    </Text>
                  </Tooltip>
                  {!readOnly && (
                    <IconButton
                      aria-label={
                        isEditingTax ? "Save tax rates" : "Edit tax rates"
                      }
                      icon={isEditingTax ? <FiCheck /> : <FiEdit2 />}
                      size="xs"
                      variant="ghost"
                      onClick={handleToggleTaxEdit}
                    />
                  )}
                </HStack>
                {isEditingTax ? (
                  <VStack
                    spacing={2}
                    align="stretch"
                    p={2}
                    bg={editBg}
                    borderRadius="md"
                  >
                    <HStack justify="space-between" fontSize="xs">
                      <Tooltip label="Your expected federal income tax bracket in retirement. Pre-tax (401k/IRA) withdrawals are taxed at this rate." placement="top" hasArrow>
                        <Text color={labelColor} cursor="help">Federal Tax Rate</Text>
                      </Tooltip>
                      <NumberInput
                        value={localFederal}
                        min={0}
                        max={50}
                        step={0.5}
                        size="xs"
                        w="80px"
                        onChange={(_, val) => {
                          if (!isNaN(val)) setLocalFederal(val);
                        }}
                      >
                        <NumberInputField textAlign="right" pr={1} />
                      </NumberInput>
                    </HStack>
                    <HStack justify="space-between" fontSize="xs">
                      <Tooltip label="Your expected state income tax rate in retirement. Varies by state — some states have no income tax." placement="top" hasArrow>
                        <Text color={labelColor} cursor="help">State Tax Rate</Text>
                      </Tooltip>
                      <NumberInput
                        value={localState}
                        min={0}
                        max={20}
                        step={0.5}
                        size="xs"
                        w="80px"
                        onChange={(_, val) => {
                          if (!isNaN(val)) setLocalState(val);
                        }}
                      >
                        <NumberInputField textAlign="right" pr={1} />
                      </NumberInput>
                    </HStack>
                    <HStack justify="space-between" fontSize="xs">
                      <Tooltip label="Tax rate applied to investment gains in taxable (brokerage) accounts. Long-term capital gains are typically taxed at 0%, 15%, or 20% depending on income." placement="top" hasArrow>
                        <Text color={labelColor} cursor="help">Capital Gains Rate</Text>
                      </Tooltip>
                      <NumberInput
                        value={localCapGains}
                        min={0}
                        max={30}
                        step={0.5}
                        size="xs"
                        w="80px"
                        onChange={(_, val) => {
                          if (!isNaN(val)) setLocalCapGains(val);
                        }}
                      >
                        <NumberInputField textAlign="right" pr={1} />
                      </NumberInput>
                    </HStack>
                  </VStack>
                ) : (
                  <>
                    <HStack justify="space-between" fontSize="xs">
                      <Tooltip label="Your expected federal income tax bracket in retirement. Pre-tax (401k/IRA) withdrawals are taxed at this rate." placement="top" hasArrow>
                        <Text color={labelColor} cursor="help">Federal Tax Rate</Text>
                      </Tooltip>
                      <Text fontWeight="medium">
                        {scenario.federal_tax_rate}%
                      </Text>
                    </HStack>
                    <HStack justify="space-between" fontSize="xs">
                      <Tooltip label="Your expected state income tax rate in retirement. Varies by state — some states have no income tax." placement="top" hasArrow>
                        <Text color={labelColor} cursor="help">State Tax Rate</Text>
                      </Tooltip>
                      <Text fontWeight="medium">
                        {scenario.state_tax_rate}%
                      </Text>
                    </HStack>
                    <HStack justify="space-between" fontSize="xs">
                      <Tooltip label="Tax rate applied to investment gains in taxable (brokerage) accounts. Long-term capital gains are typically taxed at 0%, 15%, or 20% depending on income." placement="top" hasArrow>
                        <Text color={labelColor} cursor="help">Capital Gains Rate</Text>
                      </Tooltip>
                      <Text fontWeight="medium">
                        {scenario.capital_gains_rate}%
                      </Text>
                    </HStack>
                  </>
                )}
              </VStack>
            )}
          </>
        )}

        {isError && (
          <Alert status="error" borderRadius="md" fontSize="sm">
            <AlertIcon />
            Unable to load account data. Please refresh and try again.
          </Alert>
        )}

        {!data && !isLoading && !isError && (
          <Text fontSize="sm" color={labelColor}>
            No accounts found. Add accounts to see your portfolio breakdown.
          </Text>
        )}
      </VStack>
    </Box>
  );
}
