/**
 * Net Worth Forecast tab — projects net worth to retirement under 3 scenarios.
 */

import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Card,
  CardBody,
  FormControl,
  FormLabel,
  HStack,
  NumberInput,
  NumberInputField,
  SimpleGrid,
  Stat,
  StatHelpText,
  StatLabel,
  StatNumber,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import api from "../services/api";
import { useCurrency } from "../contexts/CurrencyContext";
import { useUserView } from "../contexts/UserViewContext";

interface ForecastPoint {
  year: number;
  age: number | null;
  net_worth: number;
}

interface ForecastResponse {
  current_net_worth: number;
  current_age: number | null;
  retirement_age: number;
  years_to_retirement: number;
  baseline: ForecastPoint[];
  pessimistic: ForecastPoint[];
  optimistic: ForecastPoint[];
  retirement_target: number;
  on_track: boolean;
  annual_contribution_used: number;
  annual_return_used: number;
}

const fmt = (v: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(v);

interface FinancialDefaults {
  default_retirement_age: number;
  default_expected_return: number;
  default_annual_contribution: number;
}

export const NetWorthForecastTab = () => {
  const { selectedUserId } = useUserView();
  const { formatCurrency } = useCurrency();

  const { data: defaults } = useQuery<FinancialDefaults>({
    queryKey: ["financial-defaults"],
    queryFn: () => api.get("/settings/financial-defaults").then((r) => r.data),
    staleTime: Infinity,
  });

  const [retirementAge, setRetirementAge] = useState<number | null>(null);
  const [annualReturn, setAnnualReturn] = useState<number | null>(null);
  const [annualContrib, setAnnualContrib] = useState<number | null>(null);

  const effectiveRetirementAge = retirementAge ?? (defaults?.default_retirement_age ?? 67);
  const effectiveAnnualReturn = annualReturn ?? (defaults ? defaults.default_expected_return * 100 : 7);
  const effectiveAnnualContrib = annualContrib ?? (defaults?.default_annual_contribution ?? 24000);

  const params = new URLSearchParams({
    retirement_age: String(effectiveRetirementAge),
    annual_return: String(effectiveAnnualReturn / 100),
    annual_contribution: String(effectiveAnnualContrib),
  });
  if (selectedUserId) params.set("user_id", selectedUserId);

  const { data, isLoading, error } = useQuery<ForecastResponse>({
    queryKey: ["net-worth-forecast", effectiveRetirementAge, effectiveAnnualReturn, effectiveAnnualContrib, selectedUserId],
    queryFn: () => api.get(`/dashboard/net-worth-forecast?${params}`).then((r) => r.data),
    enabled: defaults !== undefined,
  });

  // Merge scenarios into chart data
  const chartData = data?.baseline.map((pt, i) => ({
    year: pt.year,
    age: pt.age,
    baseline: pt.net_worth,
    pessimistic: data.pessimistic[i]?.net_worth,
    optimistic: data.optimistic[i]?.net_worth,
  })) ?? [];

  return (
    <VStack spacing={6} align="stretch">
      {/* Assumption controls */}
      <Card>
        <CardBody>
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
            <FormControl>
              <FormLabel fontSize="sm">Retirement Age</FormLabel>
              <NumberInput
                value={effectiveRetirementAge}
                min={50}
                max={90}
                onChange={(_, v) => !isNaN(v) && setRetirementAge(v)}
                size="sm"
              >
                <NumberInputField />
              </NumberInput>
            </FormControl>
            <FormControl>
              <FormLabel fontSize="sm">Annual Return (%)</FormLabel>
              <NumberInput
                value={effectiveAnnualReturn}
                min={1}
                max={15}
                step={0.5}
                onChange={(_, v) => !isNaN(v) && setAnnualReturn(v)}
                size="sm"
              >
                <NumberInputField />
              </NumberInput>
            </FormControl>
            <FormControl>
              <FormLabel fontSize="sm">Annual Contribution ($)</FormLabel>
              <NumberInput
                value={effectiveAnnualContrib}
                min={0}
                max={500000}
                step={1000}
                onChange={(_, v) => !isNaN(v) && setAnnualContrib(v)}
                size="sm"
              >
                <NumberInputField />
              </NumberInput>
            </FormControl>
          </SimpleGrid>
        </CardBody>
      </Card>

      {/* Summary stats */}
      {data && (
        <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
          <Stat>
            <StatLabel fontSize="xs">Current Net Worth</StatLabel>
            <StatNumber fontSize="lg">{fmt(data.current_net_worth)}</StatNumber>
          </Stat>
          <Stat>
            <StatLabel fontSize="xs">Projected at Retirement</StatLabel>
            <StatNumber fontSize="lg">{fmt(data.baseline[data.baseline.length - 1]?.net_worth ?? 0)}</StatNumber>
          </Stat>
          <Stat>
            <StatLabel fontSize="xs">Retirement Target</StatLabel>
            <StatNumber fontSize="lg">{fmt(data.retirement_target)}</StatNumber>
            <StatHelpText fontSize="xs">25× annual spending (4% rule)</StatHelpText>
          </Stat>
          <Stat>
            <StatLabel fontSize="xs">Status</StatLabel>
            <StatNumber fontSize="lg">
              <Badge colorScheme={data.on_track ? "green" : "red"} fontSize="sm">
                {data.on_track ? "On Track" : "Needs Attention"}
              </Badge>
            </StatNumber>
            <StatHelpText fontSize="xs">{data.years_to_retirement} years to retirement</StatHelpText>
          </Stat>
        </SimpleGrid>
      )}

      {/* Chart */}
      {isLoading && <Text color="text.secondary">Loading forecast…</Text>}
      {error && (
        <Alert status="error">
          <AlertIcon />
          Failed to load forecast.
        </Alert>
      )}
      {data && chartData.length > 0 && (
        <Box>
          <ResponsiveContainer width="100%" height={340}>
            <AreaChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="gradOpt" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#48BB78" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#48BB78" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradBase" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3182CE" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#3182CE" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradPess" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#E53E3E" stopOpacity={0.1} />
                  <stop offset="95%" stopColor="#E53E3E" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
              <XAxis dataKey="year" tick={{ fontSize: 11 }} />
              <YAxis tickFormatter={(v) => fmt(v)} tick={{ fontSize: 11 }} width={64} />
              <Tooltip
                formatter={(v: number, name: string) => [fmt(v), name.charAt(0).toUpperCase() + name.slice(1)]}
                labelFormatter={(l) => `Year ${l}`}
              />
              <Legend />
              <Area type="monotone" dataKey="optimistic" stroke="#48BB78" fill="url(#gradOpt)" strokeDasharray="4 2" name="Optimistic (+2%)" />
              <Area type="monotone" dataKey="baseline" stroke="#3182CE" fill="url(#gradBase)" strokeWidth={2} name="Baseline" />
              <Area type="monotone" dataKey="pessimistic" stroke="#E53E3E" fill="url(#gradPess)" strokeDasharray="4 2" name="Pessimistic (−2%)" />
            </AreaChart>
          </ResponsiveContainer>
        </Box>
      )}
    </VStack>
  );
};
