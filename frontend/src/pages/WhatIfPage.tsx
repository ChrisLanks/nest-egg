/**
 * What-If Scenarios hub page — scenario cards for mortgage vs invest,
 * salary change, relocation tax impact, and early retirement.
 */

import { useState } from "react";
import {
  Box,
  Button,
  Collapse,
  FormControl,
  FormLabel,
  Heading,
  Input,
  Select,
  SimpleGrid,
  Spinner,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Text,
  VStack,
  Alert,
  AlertIcon,
  useColorModeValue,
} from "@chakra-ui/react";
import { useMutation } from "@tanstack/react-query";
import api from "../services/api";
import { useCurrency } from "../contexts/CurrencyContext";

interface ScenarioCardProps {
  title: string;
  description: string;
  children: React.ReactNode;
}

function ScenarioCard({ title, description, children }: ScenarioCardProps) {
  const [isOpen, setIsOpen] = useState(false);
  const bg = useColorModeValue("white", "gray.700");

  return (
    <Box p={5} borderWidth="1px" borderRadius="lg" bg={bg} shadow="sm">
      <Heading size="md" mb={1}>
        {title}
      </Heading>
      <Text fontSize="sm" color="gray.500" mb={3}>
        {description}
      </Text>
      <Button size="sm" onClick={() => setIsOpen(!isOpen)} variant="outline">
        {isOpen ? "Collapse" : "Expand"}
      </Button>
      <Collapse in={isOpen} animateOpacity>
        <Box mt={4}>{children}</Box>
      </Collapse>
    </Box>
  );
}

function MortgageVsInvest() {
  const [form, setForm] = useState({
    remaining_balance: "300000",
    interest_rate: "0.065",
    monthly_payment: "1900",
    extra_monthly_payment: "500",
    expected_investment_return: "0.08",
  const { currency } = useCurrency();
  const fmt = (n: number) => n.toLocaleString("en-US", { style: "currency", currency, maximumFractionDigits: 0 });
    tax_bracket: "0.22",
  });

  const mutation = useMutation({
    mutationFn: async () => {
      const res = await api.post("/what-if/mortgage-vs-invest", {
        remaining_balance: parseFloat(form.remaining_balance),
        interest_rate: parseFloat(form.interest_rate),
        monthly_payment: parseFloat(form.monthly_payment),
        extra_monthly_payment: parseFloat(form.extra_monthly_payment),
        expected_investment_return: parseFloat(form.expected_investment_return),
        tax_bracket: parseFloat(form.tax_bracket),
      });
      return res.data;
    },
  });

  return (
    <VStack spacing={3} align="stretch">
      <SimpleGrid columns={2} spacing={3}>
        <FormControl size="sm">
          <FormLabel fontSize="sm">Balance</FormLabel>
          <Input size="sm" value={form.remaining_balance} onChange={(e) => setForm({ ...form, remaining_balance: e.target.value })} />
        </FormControl>
        <FormControl>
          <FormLabel fontSize="sm">Rate</FormLabel>
          <Input size="sm" value={form.interest_rate} onChange={(e) => setForm({ ...form, interest_rate: e.target.value })} />
        </FormControl>
        <FormControl>
          <FormLabel fontSize="sm">Monthly Payment</FormLabel>
          <Input size="sm" value={form.monthly_payment} onChange={(e) => setForm({ ...form, monthly_payment: e.target.value })} />
        </FormControl>
        <FormControl>
          <FormLabel fontSize="sm">Extra/mo</FormLabel>
          <Input size="sm" value={form.extra_monthly_payment} onChange={(e) => setForm({ ...form, extra_monthly_payment: e.target.value })} />
        </FormControl>
      </SimpleGrid>
      <Button size="sm" colorScheme="blue" onClick={() => mutation.mutate()} isLoading={mutation.isPending}>
        Calculate
      </Button>
      {mutation.data && (
        <Box mt={2}>
          <Text fontWeight="bold">{mutation.data.recommendation}</Text>
          <SimpleGrid columns={2} spacing={2} mt={2}>
            <Stat size="sm">
              <StatLabel>Interest Saved</StatLabel>
              <StatNumber fontSize="sm">{fmt(mutation.data.pay_off_early?.interest_saved ?? 0)}</StatNumber>
            </Stat>
            <Stat size="sm">
              <StatLabel>Portfolio Value</StatLabel>
              <StatNumber fontSize="sm">{fmt(mutation.data.invest_extra?.portfolio_value_at_payoff ?? 0)}</StatNumber>
            </Stat>
          </SimpleGrid>
        </Box>
      )}
    </VStack>
  );
}

function SalaryChange() {
  const [form, setForm] = useState({
    current_salary: "100000",
    new_salary: "120000",
    current_state: "CA",
  const { currency } = useCurrency();
  const fmt = (n: number) => n.toLocaleString("en-US", { style: "currency", currency, maximumFractionDigits: 0 });
    new_state: "TX",
    filing_status: "single",
  });

  const mutation = useMutation({
    mutationFn: async () => {
      const res = await api.post("/what-if/salary-change", {
        current_salary: parseFloat(form.current_salary),
        new_salary: parseFloat(form.new_salary),
        current_state: form.current_state,
        new_state: form.new_state,
        filing_status: form.filing_status,
      });
      return res.data;
    },
  });

  return (
    <VStack spacing={3} align="stretch">
      <SimpleGrid columns={2} spacing={3}>
        <FormControl>
          <FormLabel fontSize="sm">Current Salary</FormLabel>
          <Input size="sm" value={form.current_salary} onChange={(e) => setForm({ ...form, current_salary: e.target.value })} />
        </FormControl>
        <FormControl>
          <FormLabel fontSize="sm">New Salary</FormLabel>
          <Input size="sm" value={form.new_salary} onChange={(e) => setForm({ ...form, new_salary: e.target.value })} />
        </FormControl>
        <FormControl>
          <FormLabel fontSize="sm">Current State</FormLabel>
          <Input size="sm" value={form.current_state} onChange={(e) => setForm({ ...form, current_state: e.target.value })} />
        </FormControl>
        <FormControl>
          <FormLabel fontSize="sm">New State</FormLabel>
          <Input size="sm" value={form.new_state} onChange={(e) => setForm({ ...form, new_state: e.target.value })} />
        </FormControl>
      </SimpleGrid>
      <Button size="sm" colorScheme="blue" onClick={() => mutation.mutate()} isLoading={mutation.isPending}>
        Compare
      </Button>
      {mutation.data && (
        <Box mt={2}>
          <Text fontWeight="bold">{mutation.data.recommendation}</Text>
          <Stat size="sm" mt={2}>
            <StatLabel>Net Take-Home Change</StatLabel>
            <StatNumber fontSize="sm" color={mutation.data.net_take_home_change >= 0 ? "green.500" : "red.500"}>
              {fmt(mutation.data.net_take_home_change)}/yr
            </StatNumber>
          </Stat>
        </Box>
      )}
    </VStack>
  );
}

function RelocationTax() {
  const [form, setForm] = useState({
    current_state: "CA",
  const { currency } = useCurrency();
  const fmt = (n: number) => n.toLocaleString("en-US", { style: "currency", currency, maximumFractionDigits: 0 });
    target_state: "TX",
    annual_income: "150000",
  });

  const mutation = useMutation({
    mutationFn: async () => {
      const res = await api.post("/what-if/relocation-tax", {
        current_state: form.current_state,
        target_state: form.target_state,
        annual_income: parseFloat(form.annual_income),
      });
      return res.data;
    },
  });

  return (
    <VStack spacing={3} align="stretch">
      <SimpleGrid columns={3} spacing={3}>
        <FormControl>
          <FormLabel fontSize="sm">Current State</FormLabel>
          <Input size="sm" value={form.current_state} onChange={(e) => setForm({ ...form, current_state: e.target.value })} />
        </FormControl>
        <FormControl>
          <FormLabel fontSize="sm">Target State</FormLabel>
          <Input size="sm" value={form.target_state} onChange={(e) => setForm({ ...form, target_state: e.target.value })} />
        </FormControl>
        <FormControl>
          <FormLabel fontSize="sm">Annual Income</FormLabel>
          <Input size="sm" value={form.annual_income} onChange={(e) => setForm({ ...form, annual_income: e.target.value })} />
        </FormControl>
      </SimpleGrid>
      <Button size="sm" colorScheme="blue" onClick={() => mutation.mutate()} isLoading={mutation.isPending}>
        Compare
      </Button>
      {mutation.data && (
        <SimpleGrid columns={2} spacing={2} mt={2}>
          <Stat size="sm">
            <StatLabel>Annual Savings</StatLabel>
            <StatNumber fontSize="sm" color={mutation.data.annual_savings >= 0 ? "green.500" : "red.500"}>
              {fmt(mutation.data.annual_savings)}
            </StatNumber>
          </Stat>
          <Stat size="sm">
            <StatLabel>5-Year Savings</StatLabel>
            <StatNumber fontSize="sm">{fmt(mutation.data.five_year_savings)}</StatNumber>
          </Stat>
        </SimpleGrid>
      )}
    </VStack>
  );
}

function EarlyRetirement() {
  const { currency } = useCurrency();
  const fmt = (n: number) => n.toLocaleString("en-US", { style: "currency", currency, maximumFractionDigits: 0 });
  const [form, setForm] = useState({
    current_age: "35",
    target_retirement_age: "50",
    current_savings: "500000",
    annual_savings: "50000",
    annual_expenses: "60000",
  });

  const mutation = useMutation({
    mutationFn: async () => {
      const res = await api.post("/what-if/early-retirement", {
        current_age: parseInt(form.current_age),
        target_retirement_age: parseInt(form.target_retirement_age),
        current_savings: parseFloat(form.current_savings),
        annual_savings: parseFloat(form.annual_savings),
        annual_expenses: parseFloat(form.annual_expenses),
      });
      return res.data;
    },
  });

  return (
    <VStack spacing={3} align="stretch">
      <SimpleGrid columns={2} spacing={3}>
        <FormControl>
          <FormLabel fontSize="sm">Current Age</FormLabel>
          <Input size="sm" value={form.current_age} onChange={(e) => setForm({ ...form, current_age: e.target.value })} />
        </FormControl>
        <FormControl>
          <FormLabel fontSize="sm">Target Age</FormLabel>
          <Input size="sm" value={form.target_retirement_age} onChange={(e) => setForm({ ...form, target_retirement_age: e.target.value })} />
        </FormControl>
        <FormControl>
          <FormLabel fontSize="sm">Current Savings</FormLabel>
          <Input size="sm" value={form.current_savings} onChange={(e) => setForm({ ...form, current_savings: e.target.value })} />
        </FormControl>
        <FormControl>
          <FormLabel fontSize="sm">Annual Expenses</FormLabel>
          <Input size="sm" value={form.annual_expenses} onChange={(e) => setForm({ ...form, annual_expenses: e.target.value })} />
        </FormControl>
      </SimpleGrid>
      <Button size="sm" colorScheme="blue" onClick={() => mutation.mutate()} isLoading={mutation.isPending}>
        Analyze
      </Button>
      {mutation.data && (
        <Box mt={2}>
          <Text fontWeight="bold">{mutation.data.recommendation}</Text>
          <SimpleGrid columns={2} spacing={2} mt={2}>
            <Stat size="sm">
              <StatLabel>FIRE Number</StatLabel>
              <StatNumber fontSize="sm">{fmt(mutation.data.fire_number)}</StatNumber>
            </Stat>
            <Stat size="sm">
              <StatLabel>Projected at Target</StatLabel>
              <StatNumber fontSize="sm">{fmt(mutation.data.projected_at_target)}</StatNumber>
              <StatHelpText>{mutation.data.on_track ? "On track" : "Gap exists"}</StatHelpText>
            </Stat>
          </SimpleGrid>
        </Box>
      )}
    </VStack>
  );
}

export default function WhatIfPage() {
  return (
    <Box p={6}>
      <Heading size="lg" mb={6}>
        What-If Scenarios
      </Heading>

      <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
        <ScenarioCard
          title="Mortgage vs Invest"
          description="Should you pay off your mortgage early or invest the extra?"
        >
          <MortgageVsInvest />
        </ScenarioCard>

        <ScenarioCard
          title="Salary Change"
          description="Compare total compensation and net take-home after a job change."
        >
          <SalaryChange />
        </ScenarioCard>

        <ScenarioCard
          title="Relocation Tax Impact"
          description="How much would moving to a different state save or cost in taxes?"
        >
          <RelocationTax />
        </ScenarioCard>

        <ScenarioCard
          title="Early Retirement"
          description="Can you retire early? FIRE analysis with savings projections."
        >
          <EarlyRetirement />
        </ScenarioCard>
      </SimpleGrid>
    </Box>
  );
}
