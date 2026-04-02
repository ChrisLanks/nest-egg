/**
 * Financial Ratios tab — scores key financial health ratios with grades.
 */

import {
  Alert,
  AlertDescription,
  AlertIcon,
  Badge,
  Box,
  Button,
  Card,
  CardBody,
  FormControl,
  FormHelperText,
  FormLabel,
  Heading,
  HStack,
  NumberInput,
  NumberInputField,
  Tooltip,
  Progress,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import api from "../services/api";
import { useCurrency } from "../contexts/CurrencyContext";

interface RatioMetric {
  name: string;
  value?: number;
  formatted: string;
  grade: string;
  grade_color: string;
  threshold_excellent: string;
  threshold_good: string;
  description: string;
}

interface FinancialRatiosResponse {
  metrics: RatioMetric[];
  overall_grade: string;
  overall_score: number;
  net_worth: number;
  liquid_assets: number;
  total_debt: number;
  income_provided: boolean;
  spending_provided: boolean;
  tips: string[];
}

interface DashboardSummary {
  monthly_income: number;
  monthly_spending: number;
  monthly_net: number;
  total_assets: number;
  total_debts: number;
}

const gradeColorScheme = (grade: string): string => {
  switch (grade) {
    case "A": return "green";
    case "B": return "teal";
    case "C": return "yellow";
    case "D": return "orange";
    case "F": return "red";
    default: return "gray";
  }
};

const gradeColor = (grade: string): string => {
  switch (grade) {
    case "A": return "green.500";
    case "B": return "teal.500";
    case "C": return "yellow.500";
    case "D": return "orange.400";
    case "F": return "red.500";
    default: return "gray.500";
  }
};

const fmtCompact = (v: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(v);


export const FinancialRatiosTab = () => {
  const { formatCurrency } = useCurrency();
  const [monthlyIncome, setMonthlyIncome] = useState<number | undefined>(undefined);
  const [monthlySpending, setMonthlySpending] = useState<number | undefined>(undefined);
  // Track whether the user has manually edited the fields so we don't overwrite edits
  const [incomeUserEdited, setIncomeUserEdited] = useState(false);
  const [spendingUserEdited, setSpendingUserEdited] = useState(false);

  // Fetch dashboard summary for auto-population
  const { data: summary } = useQuery<DashboardSummary>({
    queryKey: ["dashboard-summary-for-ratios"],
    queryFn: () => api.get("/dashboard/summary").then((r) => r.data),
    staleTime: 5 * 60_000,
  });

  const estimatedIncome = summary?.monthly_income && summary.monthly_income > 0
    ? summary.monthly_income
    : undefined;
  const estimatedSpending = summary?.monthly_spending && summary.monthly_spending > 0
    ? summary.monthly_spending
    : undefined;

  // Auto-populate fields from summary data when it first loads, unless user has edited
  useEffect(() => {
    if (estimatedIncome && !incomeUserEdited && monthlyIncome === undefined) {
      setMonthlyIncome(Math.round(estimatedIncome));
    }
  }, [estimatedIncome, incomeUserEdited]);

  useEffect(() => {
    if (estimatedSpending && !spendingUserEdited && monthlySpending === undefined) {
      setMonthlySpending(Math.round(estimatedSpending));
    }
  }, [estimatedSpending, spendingUserEdited]);

  const params = new URLSearchParams();
  if (monthlyIncome !== undefined) params.set("monthly_income", String(monthlyIncome));
  if (monthlySpending !== undefined) params.set("monthly_spending", String(monthlySpending));

  const { data, isLoading, error } = useQuery<FinancialRatiosResponse>({
    queryKey: ["financial-ratios", monthlyIncome, monthlySpending],
    queryFn: () =>
      api.get(`/dashboard/financial-ratios?${params}`).then((r) => r.data),
  });

  return (
    <VStack spacing={6} align="stretch">
      {/* Inputs */}
      <Card>
        <CardBody>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
            <FormControl>
              <FormLabel fontSize="sm">
                <Tooltip label="Your total gross monthly income from all sources. Used to calculate savings rate, debt-to-income ratio, and housing cost ratio." hasArrow placement="top">
                  <Text as="span">Monthly Income ($){" "}</Text>
                </Tooltip>
                <Text as="span" color="text.secondary" fontSize="xs">— optional</Text>
              </FormLabel>
              <NumberInput
                value={monthlyIncome ?? ""}
                min={0}
                onChange={(_, v) => { setIncomeUserEdited(true); setMonthlyIncome(isNaN(v) ? undefined : v); }}
                size="sm"
              >
                <NumberInputField
                  placeholder="e.g. 8000"
                />
              </NumberInput>
              {estimatedIncome && !incomeUserEdited && (
                <FormHelperText fontSize="xs" color="text.secondary">
                  Pre-filled from your recent transactions — edit to override
                </FormHelperText>
              )}
            </FormControl>
            <FormControl>
              <FormLabel fontSize="sm">
                <Tooltip label="Your total monthly essential and discretionary spending (excluding loan principal payments). Used to calculate savings rate and emergency fund coverage." hasArrow placement="top">
                  <Text as="span">Monthly Spending ($){" "}</Text>
                </Tooltip>
                <Text as="span" color="text.secondary" fontSize="xs">— optional</Text>
              </FormLabel>
              <NumberInput
                value={monthlySpending ?? ""}
                min={0}
                onChange={(_, v) => { setSpendingUserEdited(true); setMonthlySpending(isNaN(v) ? undefined : v); }}
                size="sm"
              >
                <NumberInputField
                  placeholder="e.g. 5000"
                />
              </NumberInput>
              {estimatedSpending && !spendingUserEdited && (
                <FormHelperText fontSize="xs" color="text.secondary">
                  Pre-filled from your recent transactions — edit to override
                </FormHelperText>
              )}
            </FormControl>
          </SimpleGrid>
        </CardBody>
      </Card>

      {isLoading && <Text color="text.secondary">Loading financial ratios…</Text>}
      {error && (
        <Alert status="error">
          <AlertIcon />
          Failed to load financial ratios.
        </Alert>
      )}

      {data && (!data.income_provided || !data.spending_provided) && (
        <Alert status="info">
          <AlertIcon />
          <AlertDescription fontSize="sm">
            {!data.income_provided && !data.spending_provided
              ? "Enter your monthly income and spending above to unlock your savings rate, debt-to-income ratio, and overall health score."
              : !data.income_provided
              ? "Enter your monthly income above to unlock your savings rate and debt-to-income ratio."
              : "Enter your monthly spending above to complete your savings rate calculation."}
          </AlertDescription>
        </Alert>
      )}

      {data && (
        <>
          {/* Overall grade */}
          <HStack spacing={6} align="center">
            <Tooltip label="A = 90–100 (excellent) · B = 80–89 (good) · C = 70–79 (fair) · D = 60–69 (needs work) · F = below 60 (at risk). Higher is better.">
              <Text fontSize="5xl" fontWeight="bold" color={gradeColor(data.overall_grade)} cursor="help">
                {data.overall_grade}
              </Text>
            </Tooltip>
            <VStack align="flex-start" spacing={1} flex={1}>
              <Text fontSize="sm" fontWeight="medium">Overall Financial Health Score</Text>
              <Progress
                value={data.overall_score}
                colorScheme={gradeColorScheme(data.overall_grade)}
                size="md"
                borderRadius="full"
                width="100%"
              />
              <Text fontSize="xs" color="text.secondary">{data.overall_score}/100</Text>
            </VStack>
          </HStack>

          {/* Context stats */}
          <SimpleGrid columns={{ base: 3 }} spacing={4}>
            <Stat size="sm">
              <StatLabel fontSize="xs">Net Worth</StatLabel>
              <StatNumber fontSize="md">{fmtCompact(data.net_worth)}</StatNumber>
            </Stat>
            <Stat size="sm">
              <StatLabel fontSize="xs">Liquid Assets</StatLabel>
              <StatNumber fontSize="md">{fmtCompact(data.liquid_assets)}</StatNumber>
            </Stat>
            <Stat size="sm">
              <StatLabel fontSize="xs">Total Debt</StatLabel>
              <StatNumber fontSize="md" color="red.400">{fmtCompact(data.total_debt)}</StatNumber>
            </Stat>
          </SimpleGrid>

          {/* Metric cards */}
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
            {data.metrics.map((metric) => (
              <Card key={metric.name}>
                <CardBody>
                  <HStack justify="space-between" mb={2}>
                    <Text fontSize="sm" fontWeight="medium">{metric.name}</Text>
                    <Badge colorScheme={gradeColorScheme(metric.grade)} fontSize="md" px={2}>
                      {metric.grade}
                    </Badge>
                  </HStack>
                  <Text fontSize="2xl" fontWeight="bold" color={gradeColor(metric.grade)} mb={1}>
                    {metric.formatted}
                  </Text>
                  <Text fontSize="xs" color="text.secondary" mb={2}>{metric.description}</Text>
                  <Box>
                    <Text fontSize="xs" color="green.500">Excellent: {metric.threshold_excellent}</Text>
                    <Text fontSize="xs" color="teal.500">Good: {metric.threshold_good}</Text>
                  </Box>
                </CardBody>
              </Card>
            ))}
          </SimpleGrid>

          {/* Tips */}
          {data.tips.length > 0 && (
            <Box>
              <Heading size="xs" mb={2}>Recommendations</Heading>
              <VStack align="stretch" spacing={1}>
                {data.tips.map((tip, idx) => (
                  <Text key={idx} fontSize="sm">• {tip}</Text>
                ))}
              </VStack>
            </Box>
          )}
        </>
      )}
    </VStack>
  );
};
