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
  Tr,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  financialPlanningApi,
  type MortgageAnalysisResponse,
} from "../api/financialPlanning";
import { useUserView } from "../contexts/UserViewContext";

// ── Helpers ───────────────────────────────────────────────────────────────

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);

const fmtPct = (n: number) => `${(n * 100).toFixed(2)}%`;

// ── Sub-components ────────────────────────────────────────────────────────

function SummaryCards({ data }: { data: MortgageAnalysisResponse }) {
  return (
    <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
      <Card variant="outline">
        <CardBody>
          <Stat>
            <StatLabel>Remaining Balance</StatLabel>
            <StatNumber fontSize="lg">{fmt(data.loan_balance)}</StatNumber>
          </Stat>
        </CardBody>
      </Card>
      <Card variant="outline">
        <CardBody>
          <Stat>
            <StatLabel>Interest Rate</StatLabel>
            <StatNumber fontSize="lg">{fmtPct(data.interest_rate)}</StatNumber>
          </Stat>
        </CardBody>
      </Card>
      <Card variant="outline">
        <CardBody>
          <Stat>
            <StatLabel>Monthly Payment</StatLabel>
            <StatNumber fontSize="lg">{fmt(data.monthly_payment)}</StatNumber>
          </Stat>
        </CardBody>
      </Card>
      <Card variant="outline">
        <CardBody>
          <Stat>
            <StatLabel>Payoff Date</StatLabel>
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
              <Text fontSize="xs" color="text.secondary">
                Monthly Savings
              </Text>
              <Text
                fontWeight="bold"
                color={savingsPositive ? "green.500" : "red.500"}
              >
                {savingsPositive ? "+" : ""}
                {fmt(rf.monthly_savings)}
              </Text>
            </Box>
            <Box>
              <Text fontSize="xs" color="text.secondary">
                Lifetime Interest Savings
              </Text>
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
              <Text fontSize="xs" color="text.secondary">
                Break-Even
              </Text>
              <Text fontWeight="bold">
                {rf.break_even_months} months ({rf.break_even_date})
              </Text>
            </Box>
            <Box>
              <Text fontSize="xs" color="text.secondary">
                New Payoff Date
              </Text>
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
        <Heading size="sm">Extra Payment Impact</Heading>
      </CardHeader>
      <CardBody>
        <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
          <Box>
            <Text fontSize="xs" color="text.secondary">
              Months Saved
            </Text>
            <Text fontWeight="bold" color="green.500">
              {ep.months_saved} months
            </Text>
          </Box>
          <Box>
            <Text fontSize="xs" color="text.secondary">
              Interest Saved
            </Text>
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
        <Heading size="sm">Equity Milestones</Heading>
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
          <Heading size="sm">Amortization Schedule</Heading>
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
              <Th isNumeric>Payment</Th>
              <Th isNumeric>Principal</Th>
              <Th isNumeric>Interest</Th>
              <Th isNumeric>Balance</Th>
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
  const { selectedUserId } = useUserView();
  const [refinanceRate, setRefinanceRate] = useState("");
  const [refinanceTerm, setRefinanceTerm] = useState("");
  const [closingCosts, setClosingCosts] = useState("");
  const [extraPayment, setExtraPayment] = useState("");

  const params = {
    user_id: selectedUserId || undefined,
    refinance_rate: refinanceRate ? parseFloat(refinanceRate) / 100 : undefined,
    refinance_term_months: refinanceTerm ? parseInt(refinanceTerm) : undefined,
    closing_costs: closingCosts ? parseFloat(closingCosts) : undefined,
    extra_monthly_payment: extraPayment ? parseFloat(extraPayment) : undefined,
  };

  const { data, isLoading, isError } = useQuery({
    queryKey: ["mortgage-analysis", selectedUserId, params],
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
            Analyse your loan, model a refinance, and see equity milestones.
          </Text>
        </Box>

        {/* Summary */}
        <SummaryCards data={data} />

        {/* Scenario inputs */}
        <Card variant="outline" w="full">
          <CardHeader pb={0}>
            <Heading size="sm">Model a Scenario</Heading>
          </CardHeader>
          <CardBody>
            <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4}>
              <FormControl>
                <FormLabel fontSize="xs">New Rate (%)</FormLabel>
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
                <FormLabel fontSize="xs">New Term (months)</FormLabel>
                <NumberInput size="sm" min={12} max={480}>
                  <NumberInputField
                    placeholder="e.g. 360"
                    value={refinanceTerm}
                    onChange={(e) => setRefinanceTerm(e.target.value)}
                  />
                </NumberInput>
              </FormControl>
              <FormControl>
                <FormLabel fontSize="xs">Closing Costs ($)</FormLabel>
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
                <FormLabel fontSize="xs">Extra Monthly Payment ($)</FormLabel>
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
