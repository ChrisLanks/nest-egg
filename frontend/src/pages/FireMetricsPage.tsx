/**
 * FIRE (Financial Independence, Retire Early) metrics dashboard page
 */

import {
  Box,
  Card,
  CardBody,
  CircularProgress,
  CircularProgressLabel,
  Container,
  FormControl,
  FormLabel,
  Heading,
  HStack,
  NumberInput,
  NumberInputField,
  SimpleGrid,
  Spinner,
  Center,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Text,
  Tooltip,
  VStack,
  Badge,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";
import { fireApi, type FireMetricsResponse } from "../api/fire";
import api from "../services/api";
import { useUserView } from "../contexts/UserViewContext";
import HelpHint from "../components/HelpHint";
import { helpContent } from "../constants/helpContent";
import { useCurrency } from "../contexts/CurrencyContext";

const STORAGE_KEY = "fire-assumptions";

function loadAssumptions(): {
  withdrawalRate: string;
  expectedReturn: string;
  retirementAge: string;
  _fromStorage: boolean;
} {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { ...JSON.parse(raw), _fromStorage: true };
  } catch {
    /* ignore */
  }
  // Fallback defaults — overridden by /settings/financial-defaults at runtime
  return { withdrawalRate: "4", expectedReturn: "7", retirementAge: "65", _fromStorage: false };
}

const formatPercent = (value: number) => {
  const pct = value * 100;
  // Drop unnecessary trailing ".0" (e.g. 100.0% → 100%)
  return `${pct % 1 === 0 ? pct.toFixed(0) : pct.toFixed(1)}%`;
};

const scoreColor = (ratio: number): string => {
  if (ratio >= 1) return "green.400";
  if (ratio >= 0.5) return "yellow.400";
  return "red.400";
};

/** Returns true when the backend returned all zeros — meaning no real financial data exists yet. */
const hasNoData = (data: FireMetricsResponse): boolean =>
  data.fi_ratio.investable_assets === 0 &&
  data.fi_ratio.annual_expenses === 0 &&
  data.savings_rate.income === 0 &&
  data.savings_rate.spending === 0;

const noDataHint =
  "Add accounts and categorize transactions so we can calculate this.";

export const FireMetricsPage = () => {
  const { currency } = useCurrency();

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  const {
    selectedUserId,
    isCombinedView,
    memberEffectiveUserId,
    selectedMemberIdsKey,
  } = useUserView();
  const multiEffectiveUserId = memberEffectiveUserId;
  const selectedIdsKey = selectedMemberIdsKey;
  const saved = loadAssumptions();
  const [withdrawalRate, setWithdrawalRate] = useState(saved.withdrawalRate);
  const [expectedReturn, setExpectedReturn] = useState(saved.expectedReturn);
  const [retirementAge, setRetirementAge] = useState(saved.retirementAge);

  // Seed defaults from backend when no localStorage value exists
  useEffect(() => {
    if (saved._fromStorage) return;
    api.get("/settings/financial-defaults").then((r) => {
      const d = r.data;
      setWithdrawalRate(String(Math.round((d.default_withdrawal_rate ?? 0.04) * 100)));
      setExpectedReturn(String(Math.round((d.default_expected_return ?? 0.07) * 100)));
      setRetirementAge(String(d.default_retirement_age ?? 67));
    }).catch(() => {/* keep hardcoded fallback */});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const persist = useCallback((wr: string, er: string, ra: string) => {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          withdrawalRate: wr,
          expectedReturn: er,
          retirementAge: ra,
        }),
      );
    } catch {
      /* ignore */
    }
  }, []);

  const handleWithdrawalRate = useCallback(
    (s: string) => {
      setWithdrawalRate(s);
      persist(s, expectedReturn, retirementAge);
    },
    [expectedReturn, retirementAge, persist],
  );

  const handleExpectedReturn = useCallback(
    (s: string) => {
      setExpectedReturn(s);
      persist(withdrawalRate, s, retirementAge);
    },
    [withdrawalRate, retirementAge, persist],
  );

  const handleRetirementAge = useCallback(
    (s: string) => {
      setRetirementAge(s);
      persist(withdrawalRate, expectedReturn, s);
    },
    [withdrawalRate, expectedReturn, persist],
  );

  // In combined view, use multi-member filter; otherwise use the global selected user
  const effectiveUserId = isCombinedView
    ? multiEffectiveUserId
    : effectiveUserId;

  const withdrawalNum = parseFloat(withdrawalRate) || 0;
  const returnNum = parseFloat(expectedReturn) || 0;
  const retirementNum = parseInt(retirementAge, 10) || 65;

  const { data, isLoading, isError } = useQuery<FireMetricsResponse>({
    queryKey: [
      "fire-metrics",
      effectiveUserId,
      selectedIdsKey,
      withdrawalNum,
      returnNum,
      retirementNum,
    ],
    queryFn: () =>
      fireApi.getMetrics({
        user_id: effectiveUserId || undefined,
        withdrawal_rate: withdrawalNum / 100,
        expected_return: returnNum / 100,
        retirement_age: retirementNum,
      }),
    placeholderData: (prev) => prev,
  });

  return (
    <Container maxW="container.lg" py={8}>
      <VStack spacing={8} align="stretch">
        <Box>
          <HStack justify="space-between" align="start">
            <Box>
              <Heading size="lg">FIRE Dashboard</Heading>
              <Text color="text.secondary" fontSize="sm" mt={1}>
                <strong>FIRE</strong> stands for{" "}
                <strong>Financial Independence, Retire Early</strong>. Track how
                close you are to having enough invested so that work becomes
                optional. For detailed retirement projections with life events
                and Monte Carlo simulations, visit{" "}
                <Text
                  as="a"
                  href="/retirement"
                  color="brand.500"
                  fontWeight="medium"
                >
                  Retirement Planning
                </Text>
                .
              </Text>
            </Box>
          </HStack>
        </Box>

        {/* Parameter Controls — always visible */}
        <Box bg="bg.surface" p={6} borderRadius="lg" boxShadow="sm">
          <Text fontWeight="semibold" mb={4}>
            Assumptions
          </Text>
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
            <FormControl>
              <Tooltip label="The percentage of your portfolio you plan to withdraw each year in retirement — 4% is a common starting point">
                <FormLabel fontSize="sm" cursor="help">
                  Withdrawal Rate (%)
                  <HelpHint hint={helpContent.fire.withdrawalRate} />
                </FormLabel>
              </Tooltip>
              <NumberInput
                value={withdrawalRate}
                onChange={handleWithdrawalRate}
                min={1}
                max={10}
                step={0.01}
                size="sm"
              >
                <NumberInputField />
              </NumberInput>
            </FormControl>
            <FormControl>
              <Tooltip label="The average annual growth you expect from your investments — historically stocks average ~7% after inflation">
                <FormLabel fontSize="sm" cursor="help">
                  Expected Return (%)
                </FormLabel>
              </Tooltip>
              <NumberInput
                value={expectedReturn}
                onChange={handleExpectedReturn}
                min={0}
                max={20}
                step={0.01}
                size="sm"
              >
                <NumberInputField />
              </NumberInput>
            </FormControl>
            <FormControl>
              <Tooltip label="The age you plan to stop working — used to calculate Coast FI and years remaining">
                <FormLabel fontSize="sm" cursor="help">
                  Retirement Age
                </FormLabel>
              </Tooltip>
              <NumberInput
                value={retirementAge}
                onChange={handleRetirementAge}
                min={30}
                max={100}
                size="sm"
              >
                <NumberInputField />
              </NumberInput>
            </FormControl>
          </SimpleGrid>
        </Box>

        {isLoading ? (
          <Center py={20}>
            <Spinner size="xl" color="brand.500" />
          </Center>
        ) : isError || !data ? (
          <Box bg="bg.surface" p={6} borderRadius="lg" boxShadow="sm">
            <Text color="text.muted" textAlign="center">
              Unable to calculate FIRE metrics. Make sure you have accounts and
              transactions set up.
            </Text>
          </Box>
        ) : hasNoData(data) ? (
          <Box
            bg="bg.surface"
            p={8}
            borderRadius="lg"
            boxShadow="sm"
            textAlign="center"
          >
            <Heading size="md" mb={2}>
              Not enough data yet
            </Heading>
            <Text color="text.secondary" mb={4}>
              To calculate your FIRE metrics, we need to know your income,
              expenses, and investable assets.
            </Text>
            <VStack spacing={2} align="center">
              <Text fontSize="sm" color="text.muted">
                1. Connect or add your bank and investment accounts
              </Text>
              <Text fontSize="sm" color="text.muted">
                2. Categorize your transactions as income or expenses
              </Text>
              <Text fontSize="sm" color="text.muted">
                3. Come back here to see your FIRE progress
              </Text>
            </VStack>
          </Box>
        ) : (
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
            {/* FI Ratio Card */}
            <Card>
              <CardBody>
                <VStack spacing={4}>
                  <Heading size="md">
                    FI Ratio
                    <HelpHint hint={helpContent.fire.fiRatio} />
                  </Heading>
                  <Text fontSize="xs" color="text.muted" textAlign="center">
                    How close your investments are to covering your annual
                    expenses forever
                  </Text>
                  {data.fi_ratio.annual_expenses === 0 ? (
                    <Text fontSize="sm" color="text.muted" py={4}>
                      {noDataHint}
                    </Text>
                  ) : (
                    <>
                      <CircularProgress
                        value={Math.min(data.fi_ratio.fi_ratio * 100, 100)}
                        size="120px"
                        thickness="10px"
                        color={scoreColor(data.fi_ratio.fi_ratio)}
                        trackColor="gray.100"
                      >
                        <CircularProgressLabel fontWeight="bold" fontSize="xl">
                          {formatPercent(data.fi_ratio.fi_ratio)}
                        </CircularProgressLabel>
                      </CircularProgress>
                      <SimpleGrid columns={2} spacing={4} w="full">
                        <Stat size="sm">
                          <Tooltip label="Total value of your investment and retirement accounts">
                            <StatLabel cursor="help">
                              Investable Assets
                            </StatLabel>
                          </Tooltip>
                          <StatNumber fontSize="md">
                            {formatCurrency(data.fi_ratio.investable_assets)}
                          </StatNumber>
                        </Stat>
                        <Stat size="sm">
                          <Tooltip label="The portfolio size needed to live off investments — your annual expenses divided by your withdrawal rate">
                            <StatLabel cursor="help">FI Number</StatLabel>
                          </Tooltip>
                          <StatNumber fontSize="md">
                            {formatCurrency(data.fi_ratio.fi_number)}
                          </StatNumber>
                        </Stat>
                        <Stat size="sm">
                          <Tooltip label="Your total spending over the last 12 months">
                            <StatLabel cursor="help">Annual Expenses</StatLabel>
                          </Tooltip>
                          <StatNumber fontSize="md">
                            {formatCurrency(data.fi_ratio.annual_expenses)}
                          </StatNumber>
                        </Stat>
                      </SimpleGrid>
                    </>
                  )}
                </VStack>
              </CardBody>
            </Card>

            {/* Savings Rate Card */}
            <Card>
              <CardBody>
                <VStack spacing={4}>
                  <Heading size="md">
                    Savings Rate
                    <HelpHint hint={helpContent.fire.savingsRate} />
                  </Heading>
                  <Text fontSize="xs" color="text.muted" textAlign="center">
                    What percentage of your income you're keeping
                  </Text>
                  {data.savings_rate.income === 0 &&
                  data.savings_rate.spending === 0 ? (
                    <Text fontSize="sm" color="text.muted" py={4}>
                      {noDataHint}
                    </Text>
                  ) : (
                    <>
                      <CircularProgress
                        value={Math.max(
                          0,
                          Math.min(data.savings_rate.savings_rate * 100, 100),
                        )}
                        size="120px"
                        thickness="10px"
                        color={
                          data.savings_rate.savings_rate >= 0.5
                            ? "green.400"
                            : data.savings_rate.savings_rate >= 0.2
                              ? "yellow.400"
                              : "red.400"
                        }
                        trackColor="gray.100"
                      >
                        <CircularProgressLabel fontWeight="bold" fontSize="xl">
                          {formatPercent(data.savings_rate.savings_rate)}
                        </CircularProgressLabel>
                      </CircularProgress>
                      <SimpleGrid columns={2} spacing={4} w="full">
                        <Stat size="sm">
                          <Tooltip label="Total income from all sources over the period">
                            <StatLabel cursor="help">Income</StatLabel>
                          </Tooltip>
                          <StatNumber fontSize="md">
                            {formatCurrency(data.savings_rate.income)}
                          </StatNumber>
                          <StatHelpText>
                            Last {data.savings_rate.months} months
                          </StatHelpText>
                        </Stat>
                        <Stat size="sm">
                          <Tooltip label="Total expenses across all categories over the period">
                            <StatLabel cursor="help">Spending</StatLabel>
                          </Tooltip>
                          <StatNumber fontSize="md">
                            {formatCurrency(data.savings_rate.spending)}
                          </StatNumber>
                        </Stat>
                        <Stat size="sm">
                          <Tooltip label="Income minus spending — the amount available to invest or save">
                            <StatLabel cursor="help">Savings</StatLabel>
                          </Tooltip>
                          <StatNumber fontSize="md">
                            {formatCurrency(data.savings_rate.savings)}
                          </StatNumber>
                        </Stat>
                      </SimpleGrid>
                    </>
                  )}
                </VStack>
              </CardBody>
            </Card>

            {/* Years to FI Card */}
            <Card>
              <CardBody>
                <VStack spacing={4}>
                  <Heading size="md">
                    Years to FI
                    <HelpHint hint={helpContent.fire.yearsToFi} />
                  </Heading>
                  <Text fontSize="xs" color="text.muted" textAlign="center">
                    Estimated time until your investments can sustain your
                    lifestyle
                  </Text>
                  {data.years_to_fi.fi_number === 0 &&
                  data.years_to_fi.investable_assets === 0 ? (
                    <Text fontSize="sm" color="text.muted" py={4}>
                      {noDataHint}
                    </Text>
                  ) : data.years_to_fi.already_fi &&
                    data.years_to_fi.investable_assets > 0 ? (
                    <Badge
                      colorScheme="green"
                      fontSize="2xl"
                      px={6}
                      py={3}
                      borderRadius="lg"
                    >
                      Financially Independent!
                    </Badge>
                  ) : (
                    <Text fontSize="5xl" fontWeight="bold" color="brand.500">
                      {data.years_to_fi.years_to_fi != null
                        ? data.years_to_fi.years_to_fi.toFixed(1)
                        : "N/A"}
                      <Text as="span" fontSize="xl" color="text.secondary">
                        {" "}
                        years
                      </Text>
                    </Text>
                  )}
                  {(data.years_to_fi.fi_number > 0 ||
                    data.years_to_fi.investable_assets > 0) && (
                    <SimpleGrid columns={2} spacing={4} w="full">
                      <Stat size="sm">
                        <Tooltip label="How much you save per year — higher savings means reaching FI faster">
                          <StatLabel cursor="help">Annual Savings</StatLabel>
                        </Tooltip>
                        <StatNumber fontSize="md">
                          {formatCurrency(data.years_to_fi.annual_savings)}
                        </StatNumber>
                      </Stat>
                      <Stat size="sm">
                        <Tooltip label="The total portfolio value you need to be financially independent">
                          <StatLabel cursor="help">FI Number</StatLabel>
                        </Tooltip>
                        <StatNumber fontSize="md">
                          {formatCurrency(data.years_to_fi.fi_number)}
                        </StatNumber>
                      </Stat>
                    </SimpleGrid>
                  )}
                </VStack>
              </CardBody>
            </Card>

            {/* Coast FI Card */}
            <Card>
              <CardBody>
                <VStack spacing={4}>
                  <Heading size="md">
                    Coast FI
                    <HelpHint hint={helpContent.fire.coastFi} />
                  </Heading>
                  <Text fontSize="xs" color="text.muted" textAlign="center">
                    Whether you could stop saving today and still retire on time
                    through investment growth alone
                  </Text>
                  {data.coast_fi.fi_number === 0 &&
                  data.coast_fi.investable_assets === 0 ? (
                    <Text fontSize="sm" color="text.muted" py={4}>
                      {noDataHint}
                    </Text>
                  ) : (
                    <>
                      <Badge
                        colorScheme={
                          data.coast_fi.is_coast_fi &&
                          data.coast_fi.investable_assets > 0
                            ? "green"
                            : "orange"
                        }
                        fontSize="lg"
                        px={4}
                        py={2}
                        borderRadius="lg"
                      >
                        {data.coast_fi.is_coast_fi &&
                        data.coast_fi.investable_assets > 0
                          ? "Coast FI Achieved!"
                          : "Not Yet Coast FI"}
                      </Badge>
                      <SimpleGrid columns={2} spacing={4} w="full">
                        <Stat size="sm">
                          <Tooltip label="The minimum portfolio value needed today so that investment growth alone reaches your FI number by retirement">
                            <StatLabel cursor="help">Coast FI Number</StatLabel>
                          </Tooltip>
                          <StatNumber fontSize="md">
                            {formatCurrency(data.coast_fi.coast_fi_number)}
                          </StatNumber>
                          <StatHelpText>Amount needed today</StatHelpText>
                        </Stat>
                        <Stat size="sm">
                          <Tooltip label="Your current investment and retirement account balances">
                            <StatLabel cursor="help">
                              Investable Assets
                            </StatLabel>
                          </Tooltip>
                          <StatNumber fontSize="md">
                            {formatCurrency(data.coast_fi.investable_assets)}
                          </StatNumber>
                        </Stat>
                        <Stat size="sm">
                          <Tooltip label="Years until your target retirement age, based on the oldest household member's birth year (set in profile) — the most conservative estimate for joint planning">
                            <StatLabel cursor="help">
                              Years to Retirement
                            </StatLabel>
                          </Tooltip>
                          <StatNumber fontSize="md">
                            {data.coast_fi.years_until_retirement}
                          </StatNumber>
                        </Stat>
                        <Stat size="sm">
                          <Tooltip label="The age you set in the Assumptions section above">
                            <StatLabel cursor="help">Retirement Age</StatLabel>
                          </Tooltip>
                          <StatNumber fontSize="md">
                            {data.coast_fi.retirement_age}
                          </StatNumber>
                        </Stat>
                      </SimpleGrid>
                    </>
                  )}
                </VStack>
              </CardBody>
            </Card>
          </SimpleGrid>
        )}
      </VStack>
    </Container>
  );
};
