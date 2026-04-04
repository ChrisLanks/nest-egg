/**
 * Mortgage Analyzer page.
 *
 * Fetches the user's mortgage account data automatically and renders:
 * - Loan summary (balance, rate, payment, payoff date)
 * - Optional refinance scenario comparison
 * - Extra payment impact calculator
 * - Equity milestone timeline
 * - Amortization schedule (first 24 months + total)
 */

import {
  Alert,
  AlertIcon,
  Badge,
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
  NumberInput,
  NumberInputField,
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
import { useEffect, useRef, useState } from "react";
import { FiInfo } from "react-icons/fi";
import {
  financialPlanningApi,
  type MortgageAnalysisResponse,
} from "../api/financialPlanning";
import { useUserView } from "../contexts/UserViewContext";
import { useLocalStorage } from "../hooks/useLocalStorage";

function useDebounce<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(id);
  }, [value, delayMs]);
  return debounced;
}

// ── Helpers ───────────────────────────────────────────────────────────────

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);

const fmtPct = (n: number) => `${(n * 100).toFixed(2)}%`;

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

// ── Sub-components ────────────────────────────────────────────────────────

function SummaryCards({ data }: { data: MortgageAnalysisResponse }) {
  return (
    <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
      <Card variant="outline">
        <CardBody>
          <Stat>
            <StatLabel>
              Remaining Balance
              <InfoTip label="How much principal you still owe on your mortgage — the amount that interest is calculated on each month." />
            </StatLabel>
            <StatNumber fontSize="lg">{fmt(data.loan_balance)}</StatNumber>
          </Stat>
        </CardBody>
      </Card>
      <Card variant="outline">
        <CardBody>
          <Stat>
            <StatLabel>
              Interest Rate
              <InfoTip label="Your annual interest rate. This is what the lender charges each year to borrow the money. Even a small difference (e.g. 0.5%) adds up to tens of thousands of dollars over the life of the loan." />
            </StatLabel>
            <StatNumber fontSize="lg">{fmtPct(data.interest_rate)}</StatNumber>
          </Stat>
        </CardBody>
      </Card>
      <Card variant="outline">
        <CardBody>
          <Stat>
            <StatLabel>
              Monthly Payment
              <InfoTip label="Your required minimum payment each month, covering both interest charged and principal repayment." />
            </StatLabel>
            <StatNumber fontSize="lg">{fmt(data.monthly_payment)}</StatNumber>
          </Stat>
        </CardBody>
      </Card>
      <Card variant="outline">
        <CardBody>
          <Stat>
            <StatLabel>
              Payoff Date
              <InfoTip label="The month and year your mortgage will be fully paid off if you make every scheduled payment on time with no extra payments." />
            </StatLabel>
            <StatNumber fontSize="lg">{data.summary.payoff_date}</StatNumber>
          </Stat>
        </CardBody>
      </Card>
    </SimpleGrid>
  );
}

function RefinanceSection({ data }: { data: MortgageAnalysisResponse }) {
  if (!data.refinance) return null;
  const rf = data.refinance;
  const savingsPositive = rf.monthly_savings > 0;

  return (
    <Card variant="outline">
      <CardHeader pb={0}>
        <Heading size="sm">Refinance Comparison</Heading>
      </CardHeader>
      <CardBody>
        <VStack align="start" spacing={4}>
          <Text fontSize="sm">{rf.recommendation}</Text>
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4} w="full">
            <Box>
              <HStack spacing={0}>
                <Text fontSize="xs" color="text.secondary">
                  Monthly Savings
                </Text>
                <InfoTip label="How much less (or more) you'd pay each month with the new rate. Positive = lower payment. Negative = higher payment — only worth it if you need to lower the rate long-term." />
              </HStack>
              <Text
                fontWeight="bold"
                color={savingsPositive ? "green.500" : "red.500"}
              >
                {savingsPositive ? "+" : ""}
                {fmt(rf.monthly_savings)}
              </Text>
            </Box>
            <Box>
              <HStack spacing={0}>
                <Text fontSize="xs" color="text.secondary">
                  Lifetime Interest Savings
                </Text>
                <InfoTip label="Total interest you'd save (or pay extra) over the full life of both loans. This is the real cost comparison — monthly savings can be misleading if the new term is much longer." />
              </HStack>
              <Text
                fontWeight="bold"
                color={
                  rf.lifetime_interest_savings > 0 ? "green.500" : "red.500"
                }
              >
                {fmt(rf.lifetime_interest_savings)}
              </Text>
            </Box>
            <Box>
              <HStack spacing={0}>
                <Text fontSize="xs" color="text.secondary">
                  Break-Even
                </Text>
                <InfoTip label="How long you need to stay in the home for the monthly savings to fully offset your closing costs. If you plan to move before this date, refinancing likely isn't worth it." />
              </HStack>
              <Text fontWeight="bold">
                {rf.break_even_months} months ({rf.break_even_date})
              </Text>
            </Box>
            <Box>
              <HStack spacing={0}>
                <Text fontSize="xs" color="text.secondary">
                  New Payoff Date
                </Text>
                <InfoTip label="When the refinanced loan would be fully paid off. A longer term lowers monthly payments but increases total interest paid." />
              </HStack>
              <Text fontWeight="bold">{rf.refinanced.payoff_date}</Text>
            </Box>
          </SimpleGrid>
        </VStack>
      </CardBody>
    </Card>
  );
}

function ExtraPaymentSection({ data }: { data: MortgageAnalysisResponse }) {
  if (!data.extra_payment) return null;
  const ep = data.extra_payment;

  return (
    <Card variant="outline">
      <CardHeader pb={0}>
        <Heading size="sm">
          Extra Payment Impact
          <InfoTip label="Adding even a small amount to your regular payment each month attacks the principal directly. Because your interest is calculated on the remaining balance, less principal = less interest charged next month. This compounds over time." />
        </Heading>
      </CardHeader>
      <CardBody>
        <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
          <Box>
            <HStack spacing={0}>
              <Text fontSize="xs" color="text.secondary">
                Months Saved
              </Text>
              <InfoTip label="How many fewer monthly payments you'll make. For example, saving 48 months means you pay off your mortgage 4 years early." />
            </HStack>
            <Text fontWeight="bold" color="green.500">
              {ep.months_saved} months
            </Text>
          </Box>
          <Box>
            <HStack spacing={0}>
              <Text fontSize="xs" color="text.secondary">
                Interest Saved
              </Text>
              <InfoTip label="Total interest you avoid paying by paying off the loan early. This money stays in your pocket instead of going to the bank." />
            </HStack>
            <Text fontWeight="bold" color="green.500">
              {fmt(ep.interest_saved)}
            </Text>
          </Box>
          <Box>
            <Text fontSize="xs" color="text.secondary">
              Original Payoff
            </Text>
            <Text fontWeight="bold">{ep.original_payoff_months} months</Text>
          </Box>
          <Box>
            <Text fontSize="xs" color="text.secondary">
              New Payoff
            </Text>
            <Text fontWeight="bold">{ep.new_payoff_months} months</Text>
          </Box>
        </SimpleGrid>
      </CardBody>
    </Card>
  );
}

function EquityMilestones({ data }: { data: MortgageAnalysisResponse }) {
  if (!data.equity_milestones.length) return null;

  return (
    <Card variant="outline">
      <CardHeader pb={0}>
        <Heading size="sm">
          Equity Milestones
          <InfoTip label="Equity is the portion of your home you actually own — your home's value minus what you owe. At 20% equity you can usually cancel PMI (Private Mortgage Insurance), saving $100–$200/month. At 100% you own your home free and clear." />
        </Heading>
      </CardHeader>
      <CardBody>
        <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
          {data.equity_milestones.map((m) => (
            <Box key={m.equity_pct}>
              <Badge colorScheme="brand" mb={1}>
                {m.equity_pct}% equity
              </Badge>
              <Text fontSize="sm" fontWeight="semibold">
                {m.date}
              </Text>
              <Text fontSize="xs" color="text.secondary">
                Balance: {fmt(m.balance_at_milestone)}
              </Text>
            </Box>
          ))}
        </SimpleGrid>
      </CardBody>
    </Card>
  );
}

function AmortizationPreview({ data }: { data: MortgageAnalysisResponse }) {
  const preview = data.amortization.slice(0, 24);
  if (!preview.length) return null;

  return (
    <Card variant="outline">
      <CardHeader pb={0}>
        <HStack justify="space-between">
          <HStack spacing={1}>
            <Heading size="sm">Amortization Schedule</Heading>
            <InfoTip label="A month-by-month breakdown of every payment. Early in the loan most of your payment goes to interest — not principal. This gradually shifts over time. It's why paying a little extra early has such a big impact." />
          </HStack>
          <Text fontSize="xs" color="text.secondary">
            First 24 months · Total interest: {fmt(data.summary.total_interest)}
          </Text>
        </HStack>
      </CardHeader>
      <CardBody overflowX="auto">
        <Table size="sm">
          <Thead>
            <Tr>
              <Th>Month</Th>
              <Th isNumeric>
                Payment
                <InfoTip label="Your total monthly payment (principal + interest)." />
              </Th>
              <Th isNumeric>
                Principal
                <InfoTip label="The portion of your payment that reduces your loan balance." />
              </Th>
              <Th isNumeric>
                Interest
                <InfoTip label="The portion that goes to the bank as the cost of borrowing. This decreases every month as your balance drops." />
              </Th>
              <Th isNumeric>
                Balance
                <InfoTip label="How much you still owe after this payment." />
              </Th>
            </Tr>
          </Thead>
          <Tbody>
            {preview.map((row) => (
              <Tr key={row.month}>
                <Td>{row.month}</Td>
                <Td isNumeric>{fmt(row.payment)}</Td>
                <Td isNumeric>{fmt(row.principal)}</Td>
                <Td isNumeric>{fmt(row.interest)}</Td>
                <Td isNumeric>{fmt(row.balance)}</Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      </CardBody>
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

export const MortgagePage = () => {
  const { selectedUserId, effectiveUserId } = useUserView();
  const [refinanceRate, setRefinanceRate] = useLocalStorage(
    "mortgage-refinance-rate",
    "",
  );
  const [refinanceTerm, setRefinanceTerm] = useLocalStorage(
    "mortgage-refinance-term",
    "",
  );
  const [closingCosts, setClosingCosts] = useLocalStorage(
    "mortgage-closing-costs",
    "",
  );
  const [extraPayment, setExtraPayment] = useLocalStorage(
    "mortgage-extra-payment",
    "",
  );

  // Debounce all user-editable numeric inputs so the API is only called
  // after the user stops typing (600 ms idle), not on every keystroke.
  const debouncedRefinanceRate = useDebounce(refinanceRate, 600);
  const debouncedRefinanceTerm = useDebounce(refinanceTerm, 600);
  const debouncedClosingCosts = useDebounce(closingCosts, 600);
  const debouncedExtraPayment = useDebounce(extraPayment, 600);

  const params = {
    user_id: effectiveUserId || undefined,
    refinance_rate: debouncedRefinanceRate ? parseFloat(debouncedRefinanceRate) / 100 : undefined,
    refinance_term_months: debouncedRefinanceTerm ? parseInt(debouncedRefinanceTerm) : undefined,
    closing_costs: debouncedClosingCosts ? parseFloat(debouncedClosingCosts) : undefined,
    extra_monthly_payment: debouncedExtraPayment ? parseFloat(debouncedExtraPayment) : undefined,
  };

  const { data, isLoading, isError } = useQuery({
    queryKey: ["mortgage-analysis", effectiveUserId, params],
    queryFn: () => financialPlanningApi.getMortgage(params),
  });

  if (isLoading) {
    return (
      <Center h="60vh">
        <Spinner size="xl" color="brand.500" thickness="4px" />
      </Center>
    );
  }

  if (isError) {
    return (
      <Container maxW="4xl" py={8}>
        <Alert status="error" borderRadius="lg">
          <AlertIcon />
          Failed to load mortgage data. Please try again.
        </Alert>
      </Container>
    );
  }

  if (!data?.has_mortgage) {
    return (
      <Container maxW="4xl" py={8}>
        <VStack spacing={4} align="start">
          <Heading size="lg">Mortgage Analyzer</Heading>
          <Alert status="info" borderRadius="lg">
            <AlertIcon />
            No active mortgage account found. Add a mortgage account to unlock
            this tool.
          </Alert>
        </VStack>
      </Container>
    );
  }

  return (
    <Container maxW="5xl" py={6}>
      <VStack align="start" spacing={6}>
        {/* Header */}
        <Box>
          <Heading size="lg">Mortgage Analyzer</Heading>
          <Text color="text.secondary" mt={1}>
            Understand your loan, model a refinance, and see what paying a
            little extra each month really does over time.
          </Text>
        </Box>

        {/* Summary */}
        <SummaryCards data={data} />

        {/* Scenario inputs */}
        <Card variant="outline" w="full">
          <CardHeader pb={0}>
            <HStack spacing={1}>
              <Heading size="sm">Model a Scenario</Heading>
              <InfoTip label="Fill in any of these fields to run a what-if calculation. Leave them blank to just view your current loan details." />
            </HStack>
          </CardHeader>
          <CardBody>
            <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4}>
              <FormControl>
                <FormLabel fontSize="xs">
                  New Rate (%)
                  <InfoTip label="Enter a potential refinance rate to see how it compares to your current rate. For example, if rates have dropped, type your new quoted rate here (e.g. 5.5)." />
                </FormLabel>
                <InputGroup size="sm">
                  <InputLeftAddon>%</InputLeftAddon>
                  <Input
                    type="number"
                    step="0.125"
                    placeholder="e.g. 5.5"
                    value={refinanceRate}
                    onChange={(e) => setRefinanceRate(e.target.value)}
                  />
                </InputGroup>
              </FormControl>
              <FormControl>
                <FormLabel fontSize="xs">
                  New Term (months)
                  <InfoTip label="How many months the new loan would run. 360 = 30 years, 180 = 15 years. A shorter term means higher payments but much less total interest." />
                </FormLabel>
                <NumberInput size="sm" min={12} max={480}>
                  <NumberInputField
                    placeholder="e.g. 360"
                    value={refinanceTerm}
                    onChange={(e) => setRefinanceTerm(e.target.value)}
                  />
                </NumberInput>
              </FormControl>
              <FormControl>
                <FormLabel fontSize="xs">
                  Closing Costs ($)
                  <InfoTip label="Upfront fees to refinance — typically 2–5% of the loan balance (appraisal, title, origination fees). This affects how long until the refinance pays for itself (break-even)." />
                </FormLabel>
                <InputGroup size="sm">
                  <InputLeftAddon>$</InputLeftAddon>
                  <Input
                    type="number"
                    placeholder="e.g. 5000"
                    value={closingCosts}
                    onChange={(e) => setClosingCosts(e.target.value)}
                  />
                </InputGroup>
              </FormControl>
              <FormControl>
                <FormLabel fontSize="xs">
                  Extra Monthly Payment ($)
                  <InfoTip label="Any amount you add on top of your required payment goes directly to principal. Even $100/month extra can shave years off your loan and save thousands in interest." />
                </FormLabel>
                <InputGroup size="sm">
                  <InputLeftAddon>$</InputLeftAddon>
                  <Input
                    type="number"
                    placeholder="e.g. 200"
                    value={extraPayment}
                    onChange={(e) => setExtraPayment(e.target.value)}
                  />
                </InputGroup>
              </FormControl>
            </SimpleGrid>
          </CardBody>
        </Card>

        <Divider />

        {/* Results */}
        <RefinanceSection data={data} />
        <ExtraPaymentSection data={data} />
        <EquityMilestones data={data} />
        <AmortizationPreview data={data} />
      </VStack>
    </Container>
  );
};

export default MortgagePage;
