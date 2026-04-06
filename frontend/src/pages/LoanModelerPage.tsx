/**
 * Loan Modeler page.
 *
 * Models any loan before the user takes it. Calculates affordability,
 * full amortization, buy vs lease comparison, and net worth impact.
 */

import {
  Badge,
  Box,
  Button,
  Card,
  CardBody,
  CardHeader,
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
  InputRightAddon,
  Select,
  SimpleGrid,
  Stat,
  StatHelpText,
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
import { useState } from "react";
import { FiInfo } from "react-icons/fi";
import { useQuery } from "@tanstack/react-query";
import api from "../services/api";
import { useUserView } from "../contexts/UserViewContext";
import { useCurrency } from "../contexts/CurrencyContext";

function InfoTip({ label }: { label: string }) {
  return (
    <Tooltip label={label} placement="top" hasArrow maxW="260px">
      <Box as="span" display="inline-flex" ml={1} verticalAlign="middle" cursor="help">
        <Icon as={FiInfo} boxSize={3} color="text.muted" />
      </Box>
    </Tooltip>
  );
}

function fmtPct(n: number) {
  return (n * 100).toFixed(1) + "%";
}

interface LoanCalcResult {
  monthly_payment: number;
  total_paid: number;
  total_interest: number;
  dti: {
    dti_before: number;
    dti_after: number;
    exceeds_conventional: boolean;
    exceeds_fha: boolean;
    recommendation: string;
  };
  net_worth_impact: {
    debt_added: number;
    monthly_cash_flow_before: number;
    monthly_cash_flow_after: number;
    cash_flow_delta: number;
    total_interest_cost: number;
  };
}

interface AmortRow {
  year: number;
  principal_paid: number;
  interest_paid: number;
  cumulative_interest: number;
  ending_balance: number;
}

interface BuyLeaseResult {
  buy_total_cost: number;
  lease_total_cost: number;
  buy_monthly: number;
  lease_monthly: number;
  recommendation: string;
  savings: number;
}

export const LoanModelerPage = () => {
  const { currency } = useCurrency();

  function fmt(n: number) {
    return n.toLocaleString("en-US", { style: "currency", currency, maximumFractionDigits: 0 });
  }
  const { selectedUserId, effectiveUserId } = useUserView();
  // ── Loan calculator inputs ──────────────────────────────────────────────────
  const [principal, setPrincipal] = useState("");
  const [rate, setRate] = useState("");
  const [termYears, setTermYears] = useState("30");
  const [annualIncome, setAnnualIncome] = useState("");
  const [existingDebt, setExistingDebt] = useState("");
  const [calcEnabled, setCalcEnabled] = useState(false);

  // ── Buy vs Lease inputs ─────────────────────────────────────────────────────
  const [vehiclePrice, setVehiclePrice] = useState("");
  const [downPayment, setDownPayment] = useState("");
  const [loanRate, setLoanRate] = useState("");
  const [loanTermYears, setLoanTermYears] = useState("5");
  const [leaseMonthly, setLeaseMonthly] = useState("");
  const [leaseTerm, setLeaseTerm] = useState("36");
  const [residualPct, setResidualPct] = useState("55");
  const [bvlEnabled, setBvlEnabled] = useState(false);

  // Pull existing monthly debt hint from linked accounts
  const { data: accounts = [] } = useQuery<{ account_type: string; current_balance: string | number | null }[]>({
    queryKey: ["accounts", effectiveUserId],
    queryFn: async () => {
      const p: Record<string, string> = {};
      if (effectiveUserId) p.user_id = effectiveUserId;
      const { data } = await api.get("/accounts/", { params: p });
      return data;
    },
    staleTime: 60_000,
  });
  const totalLoanBalance = accounts
    .filter((a) =>
      ["credit_card", "loan", "student_loan", "auto_loan", "mortgage"].includes(a.account_type)
    )
    .reduce((s, a) => s + Math.abs(Number(a.current_balance ?? 0)), 0);

  // ── Loan calculation query ──────────────────────────────────────────────────
  const termMonths = Math.round(Number(termYears) * 12);
  const rateDecimal = Number(rate) / 100;

  const { data: calcResult, isFetching: calcLoading } = useQuery<LoanCalcResult>({
    queryKey: ["loan-calc", principal, rate, termMonths, annualIncome, existingDebt, effectiveUserId],
    queryFn: async () => {
      const p: Record<string, string | number> = {
        principal: Number(principal),
        annual_rate: rateDecimal,
        term_months: termMonths,
        annual_gross_income: Number(annualIncome),
        existing_monthly_debt: Number(existingDebt) || 0,
      };
      if (effectiveUserId) p.user_id = effectiveUserId;
      const { data } = await api.get("/loan-modeling/calculate", { params: p });
      return data;
    },
    enabled: calcEnabled && !!principal && !!rate && !!annualIncome,
    staleTime: 30_000,
  });

  const { data: amortData } = useQuery<{ schedule: AmortRow[] }>({
    queryKey: ["loan-amort", principal, rate, termMonths, effectiveUserId],
    queryFn: async () => {
      const p: Record<string, string | number> = {
        principal: Number(principal),
        annual_rate: rateDecimal,
        term_months: termMonths,
      };
      if (effectiveUserId) p.user_id = effectiveUserId;
      const { data } = await api.get("/loan-modeling/amortization", { params: p });
      return data;
    },
    enabled: calcEnabled && !!principal && !!rate,
    staleTime: 30_000,
  });

  // ── Buy vs lease query ──────────────────────────────────────────────────────
  const { data: bvlResult } = useQuery<BuyLeaseResult>({
    queryKey: [
      "bvl",
      vehiclePrice, downPayment, loanRate, loanTermYears,
      leaseMonthly, leaseTerm, residualPct, effectiveUserId,
    ],
    queryFn: async () => {
      const p: Record<string, string | number> = {
        vehicle_price: Number(vehiclePrice),
        down_payment: Number(downPayment) || 0,
        loan_rate: Number(loanRate) / 100,
        loan_term_months: Math.round(Number(loanTermYears) * 12),
        lease_monthly: Number(leaseMonthly),
        lease_term_months: Number(leaseTerm),
        residual_value_pct: Number(residualPct) / 100,
      };
      if (effectiveUserId) p.user_id = effectiveUserId;
      const { data } = await api.get("/loan-modeling/buy-vs-lease", { params: p });
      return data;
    },
    enabled: bvlEnabled && !!vehiclePrice && !!loanRate && !!leaseMonthly,
    staleTime: 30_000,
  });

  const dtiColor = (v: number) =>
    v <= 0.28
      ? "green.600"
      : v <= 0.36
        ? "yellow.600"
        : v <= 0.43
          ? "orange.500"
          : "red.600";

  return (
    <Container maxW="5xl" py={6}>
      <VStack align="start" spacing={6}>
        <Box>
          <Heading size="lg">Loan Modeler</Heading>
          <Text color="text.secondary" mt={1}>
            Model any loan before you take it. Calculate affordability, full
            amortization, and compare buying vs leasing.
          </Text>
        </Box>

        {/* ── Loan Parameters ───────────────────────────────────────────── */}
        <Card variant="outline" w="full">
          <CardHeader pb={0}>
            <Heading size="sm">Loan Parameters</Heading>
          </CardHeader>
          <CardBody>
            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} mb={4}>
              <FormControl>
                <FormLabel fontSize="sm">Loan Amount</FormLabel>
                <InputGroup size="sm">
                  <InputLeftAddon>$</InputLeftAddon>
                  <Input
                    type="number"
                    placeholder="350000"
                    value={principal}
                    onChange={(e) => {
                      setPrincipal(e.target.value);
                      setCalcEnabled(false);
                    }}
                  />
                </InputGroup>
              </FormControl>
              <FormControl>
                <FormLabel fontSize="sm">
                  Interest Rate
                  <InfoTip label="Annual interest rate. Enter 6.5 for 6.5%." />
                </FormLabel>
                <InputGroup size="sm">
                  <Input
                    type="number"
                    placeholder="6.5"
                    value={rate}
                    onChange={(e) => {
                      setRate(e.target.value);
                      setCalcEnabled(false);
                    }}
                  />
                  <InputRightAddon>%</InputRightAddon>
                </InputGroup>
              </FormControl>
              <FormControl>
                <FormLabel fontSize="sm">Term</FormLabel>
                <Select
                  size="sm"
                  value={termYears}
                  onChange={(e) => {
                    setTermYears(e.target.value);
                    setCalcEnabled(false);
                  }}
                >
                  <option value="5">5 years</option>
                  <option value="10">10 years</option>
                  <option value="15">15 years</option>
                  <option value="20">20 years</option>
                  <option value="25">25 years</option>
                  <option value="30">30 years</option>
                </Select>
              </FormControl>
              <FormControl>
                <FormLabel fontSize="sm">
                  Gross Annual Income
                  <InfoTip label="Used to calculate your debt-to-income ratio." />
                </FormLabel>
                <InputGroup size="sm">
                  <InputLeftAddon>$</InputLeftAddon>
                  <Input
                    type="number"
                    placeholder="120000"
                    value={annualIncome}
                    onChange={(e) => {
                      setAnnualIncome(e.target.value);
                      setCalcEnabled(false);
                    }}
                  />
                </InputGroup>
              </FormControl>
              <FormControl>
                <FormLabel fontSize="sm">
                  Existing Monthly Debt
                  <InfoTip label="Current monthly debt payments (car loan, student loans, etc.)." />
                </FormLabel>
                <InputGroup size="sm">
                  <InputLeftAddon>$</InputLeftAddon>
                  <Input
                    type="number"
                    placeholder="0"
                    value={existingDebt}
                    onChange={(e) => {
                      setExistingDebt(e.target.value);
                      setCalcEnabled(false);
                    }}
                  />
                </InputGroup>
                {totalLoanBalance > 0 && !existingDebt && (
                  <Text fontSize="xs" color="text.secondary" mt={1}>
                    Linked loan balances: {fmt(totalLoanBalance)}
                  </Text>
                )}
              </FormControl>
            </SimpleGrid>
            <Button
              size="sm"
              colorScheme="blue"
              isLoading={calcLoading}
              onClick={() => setCalcEnabled(true)}
              isDisabled={!principal || !rate || !annualIncome}
            >
              Calculate
            </Button>
          </CardBody>
        </Card>

        {/* ── Affordability Check ────────────────────────────────────────── */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Affordability Check
            <InfoTip label="Lenders use two DTI thresholds: front-end (housing costs only, target below 28%) and back-end (all debts, target below 36%). FHA allows up to 43% back-end DTI." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}>
              <Heading size="sm">Monthly Payment + DTI Impact</Heading>
            </CardHeader>
            <CardBody>
              <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} mb={4}>
                <Stat>
                  <StatLabel>
                    Monthly Payment
                    <InfoTip label="Principal + interest. Does not include taxes, insurance, or PMI." />
                  </StatLabel>
                  <StatNumber fontSize="lg">
                    {calcResult ? fmt(calcResult.monthly_payment) : "—"}
                  </StatNumber>
                  <StatHelpText>
                    {calcResult
                      ? `Total interest: ${fmt(calcResult.total_interest)}`
                      : "enter loan details"}
                  </StatHelpText>
                </Stat>
                <Stat>
                  <StatLabel>
                    Front-End DTI
                    <InfoTip label="New payment ÷ gross monthly income. Conventional lenders prefer below 28%." />
                  </StatLabel>
                  <StatNumber
                    fontSize="lg"
                    color={calcResult ? dtiColor(calcResult.dti.dti_after) : undefined}
                  >
                    {calcResult ? fmtPct(calcResult.dti.dti_after) : "—"}
                  </StatNumber>
                  <StatHelpText>target: below 28%</StatHelpText>
                </Stat>
                <Stat>
                  <StatLabel>
                    Back-End DTI
                    <InfoTip label="All monthly debt including new loan ÷ gross income. Target: below 36%." />
                  </StatLabel>
                  <StatNumber
                    fontSize="lg"
                    color={calcResult ? dtiColor(calcResult.dti.dti_after) : undefined}
                  >
                    {calcResult ? fmtPct(calcResult.dti.dti_after) : "—"}
                  </StatNumber>
                  <StatHelpText>
                    {calcResult ? calcResult.dti.recommendation : "target: below 36%"}
                  </StatHelpText>
                </Stat>
              </SimpleGrid>

              {calcResult && (
                <Box borderRadius="md" bg="bg.subtle" px={4} py={3} fontSize="sm">
                  <Heading size="xs" mb={2}>Net Worth Impact</Heading>
                  <SimpleGrid columns={{ base: 1, md: 3 }} spacing={3}>
                    <HStack justify="space-between">
                      <Text color="text.secondary">Debt Added</Text>
                      <Text fontWeight="semibold" color="red.500">
                        {fmt(calcResult.net_worth_impact.debt_added)}
                      </Text>
                    </HStack>
                    <HStack justify="space-between">
                      <Text color="text.secondary">Monthly Cash Flow After</Text>
                      <Text
                        fontWeight="semibold"
                        color={
                          calcResult.net_worth_impact.monthly_cash_flow_after >= 0
                            ? "green.600"
                            : "red.500"
                        }
                      >
                        {fmt(calcResult.net_worth_impact.monthly_cash_flow_after)}
                      </Text>
                    </HStack>
                    <HStack justify="space-between">
                      <Text color="text.secondary">Total Interest Cost</Text>
                      <Text fontWeight="semibold" color="orange.500">
                        {fmt(calcResult.net_worth_impact.total_interest_cost)}
                      </Text>
                    </HStack>
                  </SimpleGrid>
                </Box>
              )}
            </CardBody>
          </Card>
        </Box>

        <Divider />

        {/* ── Amortization Schedule ──────────────────────────────────────── */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Amortization Schedule
            <InfoTip label="Shows how each payment splits between principal and interest. Early payments are mostly interest; later payments shift toward principal." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}>
              <Heading size="sm">Annual Summary</Heading>
            </CardHeader>
            <CardBody overflowX="auto">
              <Table size="sm">
                <Thead>
                  <Tr>
                    <Th>Year</Th>
                    <Th isNumeric>Principal Paid</Th>
                    <Th isNumeric>Interest Paid</Th>
                    <Th isNumeric>Cumulative Interest</Th>
                    <Th isNumeric>Remaining Balance</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {amortData?.schedule?.length ? (
                    amortData.schedule.map((row) => (
                      <Tr key={row.year}>
                        <Td>{row.year}</Td>
                        <Td isNumeric>{fmt(row.principal_paid)}</Td>
                        <Td isNumeric>{fmt(row.interest_paid)}</Td>
                        <Td isNumeric>{fmt(row.cumulative_interest)}</Td>
                        <Td isNumeric>{fmt(row.ending_balance)}</Td>
                      </Tr>
                    ))
                  ) : (
                    <Tr>
                      <Td colSpan={5}>
                        <Text
                          color="text.secondary"
                          fontSize="sm"
                          textAlign="center"
                          py={4}
                        >
                          Enter loan parameters above and click Calculate to generate
                          the amortization table.
                        </Text>
                      </Td>
                    </Tr>
                  )}
                </Tbody>
              </Table>
            </CardBody>
          </Card>
        </Box>

        <Divider />

        {/* ── Buy vs Lease ───────────────────────────────────────────────── */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Buy vs Lease
            <InfoTip label="Buying builds equity and avoids mileage penalties but has higher monthly payments. Leasing offers lower payments but you own nothing at end of term." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}>
              <Heading size="sm">Vehicle Parameters</Heading>
            </CardHeader>
            <CardBody>
              <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} mb={4}>
                <FormControl>
                  <FormLabel fontSize="sm">Vehicle Price</FormLabel>
                  <InputGroup size="sm">
                    <InputLeftAddon>$</InputLeftAddon>
                    <Input
                      type="number"
                      placeholder="45000"
                      value={vehiclePrice}
                      onChange={(e) => {
                        setVehiclePrice(e.target.value);
                        setBvlEnabled(false);
                      }}
                    />
                  </InputGroup>
                </FormControl>
                <FormControl>
                  <FormLabel fontSize="sm">Down Payment</FormLabel>
                  <InputGroup size="sm">
                    <InputLeftAddon>$</InputLeftAddon>
                    <Input
                      type="number"
                      placeholder="5000"
                      value={downPayment}
                      onChange={(e) => {
                        setDownPayment(e.target.value);
                        setBvlEnabled(false);
                      }}
                    />
                  </InputGroup>
                </FormControl>
                <FormControl>
                  <FormLabel fontSize="sm">Loan Interest Rate</FormLabel>
                  <InputGroup size="sm">
                    <Input
                      type="number"
                      placeholder="5.9"
                      value={loanRate}
                      onChange={(e) => {
                        setLoanRate(e.target.value);
                        setBvlEnabled(false);
                      }}
                    />
                    <InputRightAddon>%</InputRightAddon>
                  </InputGroup>
                </FormControl>
                <FormControl>
                  <FormLabel fontSize="sm">Loan Term</FormLabel>
                  <Select
                    size="sm"
                    value={loanTermYears}
                    onChange={(e) => {
                      setLoanTermYears(e.target.value);
                      setBvlEnabled(false);
                    }}
                  >
                    <option value="3">3 years</option>
                    <option value="4">4 years</option>
                    <option value="5">5 years</option>
                    <option value="6">6 years</option>
                    <option value="7">7 years</option>
                  </Select>
                </FormControl>
                <FormControl>
                  <FormLabel fontSize="sm">Lease Monthly Payment</FormLabel>
                  <InputGroup size="sm">
                    <InputLeftAddon>$</InputLeftAddon>
                    <Input
                      type="number"
                      placeholder="450"
                      value={leaseMonthly}
                      onChange={(e) => {
                        setLeaseMonthly(e.target.value);
                        setBvlEnabled(false);
                      }}
                    />
                  </InputGroup>
                </FormControl>
                <FormControl>
                  <FormLabel fontSize="sm">Lease Term</FormLabel>
                  <Select
                    size="sm"
                    value={leaseTerm}
                    onChange={(e) => {
                      setLeaseTerm(e.target.value);
                      setBvlEnabled(false);
                    }}
                  >
                    <option value="24">24 months</option>
                    <option value="36">36 months</option>
                    <option value="48">48 months</option>
                  </Select>
                </FormControl>
                <FormControl>
                  <FormLabel fontSize="sm">
                    Residual Value
                    <InfoTip label="Expected value at end of ownership period as % of purchase price. Typically 45–60% for 3-year periods." />
                  </FormLabel>
                  <InputGroup size="sm">
                    <Input
                      type="number"
                      placeholder="55"
                      value={residualPct}
                      onChange={(e) => {
                        setResidualPct(e.target.value);
                        setBvlEnabled(false);
                      }}
                    />
                    <InputRightAddon>%</InputRightAddon>
                  </InputGroup>
                </FormControl>
              </SimpleGrid>
              <Button
                size="sm"
                colorScheme="blue"
                onClick={() => setBvlEnabled(true)}
                isDisabled={!vehiclePrice || !loanRate || !leaseMonthly}
              >
                Compare
              </Button>
            </CardBody>
          </Card>

          {bvlResult && (
            <Card variant="outline" w="full" mt={3}>
              <CardHeader pb={0}>
                <Heading size="sm">Total Cost Comparison</Heading>
              </CardHeader>
              <CardBody>
                <HStack spacing={8} flexWrap="wrap" mb={3}>
                  <Stat>
                    <StatLabel>Buy — Total Cost</StatLabel>
                    <StatNumber fontSize="lg">{fmt(bvlResult.buy_total_cost)}</StatNumber>
                    <StatHelpText>{fmt(bvlResult.buy_monthly)}/mo payment</StatHelpText>
                  </Stat>
                  <Stat>
                    <StatLabel>Lease — Total Cost</StatLabel>
                    <StatNumber fontSize="lg">{fmt(bvlResult.lease_total_cost)}</StatNumber>
                    <StatHelpText>{fmt(bvlResult.lease_monthly)}/mo payment</StatHelpText>
                  </Stat>
                  <Stat>
                    <StatLabel>Better Option</StatLabel>
                    <StatNumber fontSize="lg">
                      <Badge
                        colorScheme={bvlResult.recommendation === "buy" ? "green" : "blue"}
                        fontSize="md"
                        px={3}
                        py={1}
                      >
                        {bvlResult.recommendation.toUpperCase()}
                      </Badge>
                    </StatNumber>
                    <StatHelpText>saves {fmt(bvlResult.savings)}</StatHelpText>
                  </Stat>
                </HStack>
              </CardBody>
            </Card>
          )}
        </Box>
      </VStack>
    </Container>
  );
};

export default LoanModelerPage;
