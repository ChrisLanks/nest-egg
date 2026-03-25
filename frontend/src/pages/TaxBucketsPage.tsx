/**
 * Tax Bucket Analysis page.
 *
 * Shows the user's pre-tax / Roth / taxable / HSA balance breakdown and
 * projects the RMD "tax bomb" risk.  Uses the three-bucket strategy framework
 * to surface Roth conversion opportunities before RMDs begin.
 */

import {
  Alert,
  AlertIcon,
  Box,
  Card,
  CardBody,
  CardHeader,
  Center,
  Container,
  Divider,
  FormControl,
  FormLabel,
  Heading,
  HStack,
  Icon,
  Input,
  InputGroup,
  InputLeftAddon,
  Select,
  SimpleGrid,
  Spinner,
  Stat,
  StatLabel,
  StatNumber,
  Table,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tooltip,
  Tr,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { FiInfo } from "react-icons/fi";
import api from "../services/api";
import { useUserView } from "../contexts/UserViewContext";
import { useLocalStorage } from "../hooks/useLocalStorage";

// ── Types ──────────────────────────────────────────────────────────────────

interface BucketSummary {
  buckets: {
    pre_tax: number;
    roth: number;
    taxable: number;
    tax_free: number;
    other: number;
  };
  total: number;
  retirement_total: number;
  pre_tax_pct: number;
  imbalanced: boolean;
}

interface RmdEntry {
  age: number;
  rmd_amount: number;
  remaining_balance: number;
}

interface RothHeadroom {
  target_bracket: number;
  bracket_ceiling: number;
  current_income: number;
  conversion_headroom: number;
}

// ── Helpers ────────────────────────────────────────────────────────────────

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);

const fmtPct = (n: number) => `${(n * 100).toFixed(1)}%`;

function InfoTip({ label }: { label: string }) {
  return (
    <Tooltip label={label} placement="top" hasArrow maxW="260px">
      <Box
        as="span"
        display="inline-flex"
        ml={1}
        verticalAlign="middle"
        cursor="help"
      >
        <Icon as={FiInfo} boxSize={3} color="text.muted" />
      </Box>
    </Tooltip>
  );
}

// ── API helpers ────────────────────────────────────────────────────────────

async function fetchBucketSummary(userId?: string): Promise<BucketSummary> {
  const params = userId ? `?user_id=${userId}` : "";
  const res = await api.get(`/tax-buckets/summary${params}`);
  return res.data;
}

async function fetchRmdProjection(
  preTaxBalance: number,
  currentAge: number,
  growthRate: number,
): Promise<RmdEntry[]> {
  const res = await api.get(
    `/tax-buckets/rmd-projection?pre_tax_balance=${preTaxBalance}&current_age=${currentAge}&growth_rate=${growthRate}`,
  );
  return res.data;
}

async function fetchRothHeadroom(
  currentIncome: number,
  filingStatus: string,
): Promise<RothHeadroom> {
  const res = await api.get(
    `/tax-buckets/roth-headroom?current_income=${currentIncome}&filing_status=${filingStatus}`,
  );
  return res.data;
}

// ── Page ──────────────────────────────────────────────────────────────────

export const TaxBucketsPage = () => {
  const { selectedUserId } = useUserView();

  const [currentAge, setCurrentAge] = useLocalStorage("tax-buckets-age", "55");
  const [growthRate, setGrowthRate] = useLocalStorage(
    "tax-buckets-growth",
    "0.06",
  );
  const [currentIncome, setCurrentIncome] = useLocalStorage(
    "tax-buckets-income",
    "",
  );
  const [filingStatus, setFilingStatus] = useLocalStorage<"single" | "married">(
    "tax-buckets-filing",
    "single",
  );
  const [showRmdTable, setShowRmdTable] = useState(false);

  // Summary query
  const {
    data: summary,
    isLoading: summaryLoading,
    isError: summaryError,
  } = useQuery({
    queryKey: ["tax-bucket-summary", selectedUserId],
    queryFn: () => fetchBucketSummary(selectedUserId || undefined),
    placeholderData: (prev) => prev,
  });

  // RMD projection query — only fires once user toggles the section
  const ageNum = parseInt(currentAge, 10) || 55;
  const growthNum = parseFloat(growthRate) || 0.06;
  const preTaxBalance = summary?.buckets.pre_tax ?? 0;

  const { data: rmdSchedule, isLoading: rmdLoading } = useQuery({
    queryKey: ["rmd-projection", preTaxBalance, ageNum, growthNum],
    queryFn: () => fetchRmdProjection(preTaxBalance, ageNum, growthNum),
    enabled: showRmdTable && preTaxBalance > 0,
    placeholderData: (prev) => prev,
  });

  // Roth headroom query
  const incomeNum = parseFloat(currentIncome) || 0;
  const { data: rothHeadroom, isLoading: rothLoading } = useQuery({
    queryKey: ["roth-headroom", incomeNum, filingStatus],
    queryFn: () => fetchRothHeadroom(incomeNum, filingStatus),
    enabled: incomeNum > 0,
    placeholderData: (prev) => prev,
  });

  return (
    <Container maxW="5xl" py={6}>
      <VStack align="start" spacing={6}>
        {/* Header */}
        <Box>
          <Heading size="lg">Tax Bucket Analysis</Heading>
          <Text color="text.secondary" mt={1}>
            The three-bucket strategy spreads retirement savings across
            pre-tax, Roth, and taxable accounts, giving you tax flexibility
            in retirement. Too much in pre-tax (traditional 401k / IRA) creates
            an RMD tax bomb when Required Minimum Distributions begin at age 73.
          </Text>
        </Box>

        {/* Loading / error states */}
        {summaryLoading && (
          <Center w="full" py={8}>
            <Spinner size="lg" color="brand.500" />
          </Center>
        )}
        {summaryError && (
          <Alert status="error" borderRadius="lg" w="full">
            <AlertIcon />
            Failed to load tax bucket summary. Please try again.
          </Alert>
        )}

        {summary && (
          <>
            {/* Warning banner */}
            {summary.imbalanced && (
              <Alert status="warning" borderRadius="lg" w="full">
                <AlertIcon />
                <Text fontSize="sm">
                  Over 85% of your retirement assets are in pre-tax accounts.
                  Consider Roth conversions to reduce future RMD tax exposure.
                </Text>
              </Alert>
            )}

            {/* Bucket stat cards */}
            <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4} w="full">
              <Card variant="outline">
                <CardBody>
                  <Stat>
                    <StatLabel>
                      Pre-Tax
                      <InfoTip label="Traditional 401(k), Traditional IRA, SEP-IRA, and similar accounts. Contributions were tax-deductible; withdrawals are taxed as ordinary income. Subject to RMDs starting at age 73." />
                    </StatLabel>
                    <StatNumber fontSize="lg">
                      {fmt(summary.buckets.pre_tax)}
                    </StatNumber>
                  </Stat>
                </CardBody>
              </Card>
              <Card variant="outline">
                <CardBody>
                  <Stat>
                    <StatLabel>
                      Roth
                      <InfoTip label="Roth 401(k) and Roth IRA accounts. Contributions were after-tax; qualified withdrawals are completely tax-free. Not subject to RMDs during the owner's lifetime (Roth IRA)." />
                    </StatLabel>
                    <StatNumber fontSize="lg">
                      {fmt(summary.buckets.roth)}
                    </StatNumber>
                  </Stat>
                </CardBody>
              </Card>
              <Card variant="outline">
                <CardBody>
                  <Stat>
                    <StatLabel>
                      Taxable
                      <InfoTip label="Brokerage accounts, checking, and savings. Gains are taxed at capital gains rates; interest at ordinary income rates. No contribution limits and no withdrawal restrictions." />
                    </StatLabel>
                    <StatNumber fontSize="lg">
                      {fmt(summary.buckets.taxable)}
                    </StatNumber>
                  </Stat>
                </CardBody>
              </Card>
              <Card variant="outline">
                <CardBody>
                  <Stat>
                    <StatLabel>
                      HSA / Tax-Free
                      <InfoTip label="Health Savings Accounts (HSAs) offer triple tax advantage: tax-deductible contributions, tax-free growth, and tax-free qualified withdrawals. After age 65, withdrawals for any purpose are taxed as ordinary income (like a traditional IRA)." />
                    </StatLabel>
                    <StatNumber fontSize="lg">
                      {fmt(summary.buckets.tax_free)}
                    </StatNumber>
                  </Stat>
                </CardBody>
              </Card>
            </SimpleGrid>

            {/* Retirement totals summary */}
            <Card variant="outline" w="full">
              <CardBody>
                <VStack align="start" spacing={2} fontSize="sm">
                  <HStack justify="space-between" w="full">
                    <Text color="text.secondary">
                      Total Retirement Assets
                      <InfoTip label="Pre-tax + Roth + HSA/Tax-Free balances combined." />
                    </Text>
                    <Text fontWeight="semibold">
                      {fmt(summary.retirement_total)}
                    </Text>
                  </HStack>
                  <HStack justify="space-between" w="full">
                    <Text color="text.secondary">
                      Pre-Tax Concentration
                      <InfoTip label="Percentage of retirement assets in pre-tax accounts. Above 85% triggers the RMD tax bomb warning." />
                    </Text>
                    <Text
                      fontWeight="semibold"
                      color={summary.imbalanced ? "orange.500" : "green.600"}
                    >
                      {fmtPct(summary.pre_tax_pct)}
                    </Text>
                  </HStack>
                  <Divider />
                  <HStack justify="space-between" w="full">
                    <Text color="text.secondary">Total Net Worth (all accounts)</Text>
                    <Text fontWeight="semibold">{fmt(summary.total)}</Text>
                  </HStack>
                </VStack>
              </CardBody>
            </Card>

            <Divider />

            {/* RMD Projection section */}
            <Box w="full">
              <HStack justify="space-between" mb={3}>
                <Heading size="md">
                  RMD Projection
                  <InfoTip label="Projects Required Minimum Distributions from your pre-tax balance using the IRS Uniform Lifetime Table. RMDs begin at age 73 under SECURE 2.0." />
                </Heading>
                <Box
                  as="button"
                  fontSize="sm"
                  color="brand.500"
                  onClick={() => setShowRmdTable(!showRmdTable)}
                  _hover={{ textDecoration: "underline" }}
                >
                  {showRmdTable ? "Hide table" : "Show projection table"}
                </Box>
              </HStack>

              {/* RMD inputs */}
              <Card variant="outline" w="full" mb={4}>
                <CardHeader pb={0}>
                  <Heading size="sm">Projection Inputs</Heading>
                </CardHeader>
                <CardBody>
                  <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
                    <FormControl>
                      <FormLabel fontSize="xs">
                        Current Age
                        <InfoTip label="Your current age. The projection starts from RMD age (73) or your current age, whichever is later." />
                      </FormLabel>
                      <Input
                        size="sm"
                        type="number"
                        value={currentAge}
                        onChange={(e) => setCurrentAge(e.target.value)}
                        min={18}
                        max={100}
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel fontSize="xs">
                        Pre-Tax Balance
                        <InfoTip label="Auto-populated from your account balances above." />
                      </FormLabel>
                      <InputGroup size="sm">
                        <InputLeftAddon>$</InputLeftAddon>
                        <Input
                          value={fmt(preTaxBalance).replace("$", "").replace(/,/g, "")}
                          isReadOnly
                          bg="bg.subtle"
                        />
                      </InputGroup>
                    </FormControl>
                    <FormControl>
                      <FormLabel fontSize="xs">
                        Growth Rate
                        <InfoTip label="Assumed annual growth rate of your pre-tax accounts before RMDs are taken. Defaults to 6%." />
                      </FormLabel>
                      <InputGroup size="sm">
                        <Input
                          type="number"
                          step="0.01"
                          value={growthRate}
                          onChange={(e) => setGrowthRate(e.target.value)}
                          placeholder="0.06"
                        />
                      </InputGroup>
                    </FormControl>
                  </SimpleGrid>
                </CardBody>
              </Card>

              {showRmdTable && (
                <>
                  {rmdLoading && (
                    <Center py={4}>
                      <Spinner size="md" color="brand.500" />
                    </Center>
                  )}
                  {rmdSchedule && rmdSchedule.length > 0 && (
                    <Card variant="outline" w="full">
                      <CardHeader pb={0}>
                        <Heading size="sm">Annual RMD Schedule (age 73–100)</Heading>
                      </CardHeader>
                      <CardBody overflowX="auto">
                        <Table size="sm">
                          <Thead>
                            <Tr>
                              <Th>Age</Th>
                              <Th isNumeric>RMD Amount</Th>
                              <Th isNumeric>Remaining Balance</Th>
                            </Tr>
                          </Thead>
                          <Tbody>
                            {rmdSchedule.map((row) => (
                              <Tr key={row.age}>
                                <Td>{row.age}</Td>
                                <Td isNumeric>{fmt(row.rmd_amount)}</Td>
                                <Td isNumeric>{fmt(row.remaining_balance)}</Td>
                              </Tr>
                            ))}
                          </Tbody>
                        </Table>
                      </CardBody>
                    </Card>
                  )}
                  {preTaxBalance === 0 && (
                    <Alert status="info" borderRadius="lg">
                      <AlertIcon />
                      No pre-tax balance found. Add traditional 401(k) or IRA
                      accounts to see RMD projections.
                    </Alert>
                  )}
                </>
              )}
            </Box>

            <Divider />

            {/* Roth Conversion Headroom */}
            <Box w="full">
              <Heading size="md" mb={3}>
                Roth Conversion Headroom
                <InfoTip label="Shows how much you can convert from pre-tax to Roth while staying within the 22% federal bracket. Converting in lower-income years reduces future RMDs and long-term tax exposure." />
              </Heading>
              <Card variant="outline" w="full">
                <CardHeader pb={0}>
                  <Heading size="sm">Your Situation</Heading>
                </CardHeader>
                <CardBody>
                  <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4} mb={4}>
                    <FormControl>
                      <FormLabel fontSize="xs">
                        Current Taxable Income
                        <InfoTip label="Your estimated taxable income for this year (after deductions). Used to calculate how much room remains in the 22% bracket before the next bracket begins." />
                      </FormLabel>
                      <InputGroup size="sm">
                        <InputLeftAddon>$</InputLeftAddon>
                        <Input
                          type="number"
                          placeholder="e.g. 75000"
                          value={currentIncome}
                          onChange={(e) => setCurrentIncome(e.target.value)}
                        />
                      </InputGroup>
                    </FormControl>
                    <FormControl>
                      <FormLabel fontSize="xs">Filing Status</FormLabel>
                      <Select
                        size="sm"
                        value={filingStatus}
                        onChange={(e) =>
                          setFilingStatus(e.target.value as "single" | "married")
                        }
                      >
                        <option value="single">Single</option>
                        <option value="married">Married Filing Jointly</option>
                      </Select>
                    </FormControl>
                  </SimpleGrid>

                  {rothLoading && (
                    <Center py={2}>
                      <Spinner size="sm" color="brand.500" />
                    </Center>
                  )}

                  {rothHeadroom && incomeNum > 0 && (
                    <VStack align="start" spacing={2} fontSize="sm">
                      <Divider />
                      <HStack justify="space-between" w="full">
                        <Text color="text.secondary">
                          Target Bracket
                          <InfoTip label="The bracket ceiling we optimize for. Converting up to this ceiling keeps your marginal rate at 22% or below." />
                        </Text>
                        <Text fontWeight="semibold">
                          {fmtPct(rothHeadroom.target_bracket)}
                        </Text>
                      </HStack>
                      <HStack justify="space-between" w="full">
                        <Text color="text.secondary">22% Bracket Ceiling</Text>
                        <Text>{fmt(rothHeadroom.bracket_ceiling)}</Text>
                      </HStack>
                      <HStack justify="space-between" w="full">
                        <Text color="text.secondary">Current Taxable Income</Text>
                        <Text>{fmt(rothHeadroom.current_income)}</Text>
                      </HStack>
                      <Divider />
                      <HStack justify="space-between" w="full">
                        <Text fontWeight="semibold">
                          Roth Conversion Headroom
                          <InfoTip label="The maximum you can convert from pre-tax to Roth this year while remaining in the 22% bracket." />
                        </Text>
                        <Text
                          fontWeight="bold"
                          color={
                            rothHeadroom.conversion_headroom > 0
                              ? "green.600"
                              : "text.secondary"
                          }
                        >
                          {fmt(rothHeadroom.conversion_headroom)}
                        </Text>
                      </HStack>
                      {rothHeadroom.conversion_headroom > 0 && (
                        <Alert status="success" borderRadius="md" fontSize="sm">
                          <AlertIcon />
                          You can convert up to{" "}
                          <strong>
                            {fmt(rothHeadroom.conversion_headroom)}
                          </strong>{" "}
                          to Roth this year and stay within the 22% bracket.
                          This reduces your future RMD liability.
                        </Alert>
                      )}
                      {rothHeadroom.conversion_headroom === 0 && (
                        <Alert status="info" borderRadius="md" fontSize="sm">
                          <AlertIcon />
                          Your income already exceeds the 22% bracket ceiling.
                          Any Roth conversion will be taxed above 22%.
                        </Alert>
                      )}
                    </VStack>
                  )}

                  {incomeNum === 0 && (
                    <Text fontSize="sm" color="text.secondary">
                      Enter your current taxable income above to see your Roth
                      conversion headroom.
                    </Text>
                  )}
                </CardBody>
              </Card>
            </Box>
          </>
        )}
      </VStack>
    </Container>
  );
};

export default TaxBucketsPage;
