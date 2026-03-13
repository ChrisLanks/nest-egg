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
  VStack,
  Badge,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { fireApi, type FireMetricsResponse } from "../api/fire";
import { useUserView } from "../contexts/UserViewContext";
import { useMultiMemberFilter } from "../hooks/useMultiMemberFilter";
import { MemberMultiSelect } from "../components/MemberMultiSelect";

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;

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
  const { selectedUserId, isCombinedView } = useUserView();
  const {
    selectedIds,
    toggleMember,
    selectAll,
    isAllSelected,
    showFilter,
    members,
    effectiveUserId: multiEffectiveUserId,
    selectedIdsKey,
  } = useMultiMemberFilter();
  const [withdrawalRate, setWithdrawalRate] = useState(4);
  const [expectedReturn, setExpectedReturn] = useState(7);
  const [retirementAge, setRetirementAge] = useState(65);

  // In combined view, use multi-member filter; otherwise use the global selected user
  const effectiveUserId = isCombinedView
    ? multiEffectiveUserId
    : selectedUserId;

  const { data, isLoading, isError } = useQuery<FireMetricsResponse>({
    queryKey: [
      "fire-metrics",
      effectiveUserId,
      selectedIdsKey,
      withdrawalRate,
      expectedReturn,
      retirementAge,
    ],
    queryFn: () =>
      fireApi.getMetrics({
        user_id: effectiveUserId || undefined,
        withdrawal_rate: withdrawalRate / 100,
        expected_return: expectedReturn / 100,
        retirement_age: retirementAge,
      }),
  });

  if (isLoading) {
    return (
      <Container maxW="container.lg" py={8}>
        <Center py={20}>
          <Spinner size="xl" color="brand.500" />
        </Center>
      </Container>
    );
  }

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
            {showFilter && (
              <Box flexShrink={0}>
                <MemberMultiSelect
                  selectedIds={selectedIds}
                  members={members}
                  isAllSelected={isAllSelected}
                  onToggle={toggleMember}
                  onSelectAll={selectAll}
                  label=""
                  colorScheme="brand"
                />
              </Box>
            )}
          </HStack>
        </Box>

        {/* Parameter Controls */}
        <Box bg="bg.surface" p={6} borderRadius="lg" boxShadow="sm">
          <Text fontWeight="semibold" mb={4}>
            Assumptions
          </Text>
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
            <FormControl>
              <FormLabel fontSize="sm">Withdrawal Rate (%)</FormLabel>
              <NumberInput
                value={withdrawalRate}
                onChange={(_, v) => !isNaN(v) && setWithdrawalRate(v)}
                min={1}
                max={10}
                step={0.5}
                size="sm"
              >
                <NumberInputField />
              </NumberInput>
            </FormControl>
            <FormControl>
              <FormLabel fontSize="sm">Expected Return (%)</FormLabel>
              <NumberInput
                value={expectedReturn}
                onChange={(_, v) => !isNaN(v) && setExpectedReturn(v)}
                min={0}
                max={20}
                step={0.5}
                size="sm"
              >
                <NumberInputField />
              </NumberInput>
            </FormControl>
            <FormControl>
              <FormLabel fontSize="sm">Retirement Age</FormLabel>
              <NumberInput
                value={retirementAge}
                onChange={(_, v) => !isNaN(v) && setRetirementAge(v)}
                min={30}
                max={100}
                size="sm"
              >
                <NumberInputField />
              </NumberInput>
            </FormControl>
          </SimpleGrid>
        </Box>

        {isError || !data ? (
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
                  <Heading size="md">FI Ratio</Heading>
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
                          <StatLabel>Investable Assets</StatLabel>
                          <StatNumber fontSize="md">
                            {formatCurrency(data.fi_ratio.investable_assets)}
                          </StatNumber>
                        </Stat>
                        <Stat size="sm">
                          <StatLabel>FI Number</StatLabel>
                          <StatNumber fontSize="md">
                            {formatCurrency(data.fi_ratio.fi_number)}
                          </StatNumber>
                        </Stat>
                        <Stat size="sm">
                          <StatLabel>Annual Expenses</StatLabel>
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
                  <Heading size="md">Savings Rate</Heading>
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
                          <StatLabel>Income</StatLabel>
                          <StatNumber fontSize="md">
                            {formatCurrency(data.savings_rate.income)}
                          </StatNumber>
                          <StatHelpText>
                            Last {data.savings_rate.months} months
                          </StatHelpText>
                        </Stat>
                        <Stat size="sm">
                          <StatLabel>Spending</StatLabel>
                          <StatNumber fontSize="md">
                            {formatCurrency(data.savings_rate.spending)}
                          </StatNumber>
                        </Stat>
                        <Stat size="sm">
                          <StatLabel>Savings</StatLabel>
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
                  <Heading size="md">Years to FI</Heading>
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
                        <StatLabel>Annual Savings</StatLabel>
                        <StatNumber fontSize="md">
                          {formatCurrency(data.years_to_fi.annual_savings)}
                        </StatNumber>
                      </Stat>
                      <Stat size="sm">
                        <StatLabel>FI Number</StatLabel>
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
                  <Heading size="md">Coast FI</Heading>
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
                          <StatLabel>Coast FI Number</StatLabel>
                          <StatNumber fontSize="md">
                            {formatCurrency(data.coast_fi.coast_fi_number)}
                          </StatNumber>
                          <StatHelpText>Amount needed today</StatHelpText>
                        </Stat>
                        <Stat size="sm">
                          <StatLabel>Investable Assets</StatLabel>
                          <StatNumber fontSize="md">
                            {formatCurrency(data.coast_fi.investable_assets)}
                          </StatNumber>
                        </Stat>
                        <Stat size="sm">
                          <StatLabel>Years to Retirement</StatLabel>
                          <StatNumber fontSize="md">
                            {data.coast_fi.years_until_retirement}
                          </StatNumber>
                        </Stat>
                        <Stat size="sm">
                          <StatLabel>Retirement Age</StatLabel>
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
