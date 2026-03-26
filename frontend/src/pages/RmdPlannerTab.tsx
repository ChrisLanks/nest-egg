/**
 * RMD Planner tab — multi-account Required Minimum Distribution projections.
 */

import {
  Alert,
  AlertDescription,
  AlertIcon,
  Badge,
  Box,
  Card,
  CardBody,
  FormControl,
  FormHelperText,
  FormLabel,
  HStack,
  NumberInput,
  NumberInputField,
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
  Tr,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import api from "../services/api";
import { useUserView } from "../contexts/UserViewContext";

interface RmdYearPoint {
  year: number;
  age: number;
  total_rmd: number;
  estimated_tax_on_rmd: number;
  effective_rate_on_rmd: number;
}

interface RmdPlannerResponse {
  current_age: number | null;
  rmd_start_age: number;
  years_until_rmd: number;
  total_current_rmd_balance: number;
  accounts: { account_id: string; name: string; account_type: string; current_balance: number }[];
  projection: RmdYearPoint[];
  total_lifetime_rmd_estimate: number;
  total_lifetime_tax_estimate: number;
}

const fmt = (v: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(v);

const fmtCompact = (v: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(v);

export const RmdPlannerTab = () => {
  const { selectedUserId } = useUserView();
  const [growthRate, setGrowthRate] = useState(6);
  const [filingStatus, setFilingStatus] = useState("single");
  const [otherIncome, setOtherIncome] = useState(50000);
  const [federalRate, setFederalRate] = useState(22);

  const params = new URLSearchParams({
    projection_years: "20",
    growth_rate: String(growthRate / 100),
    filing_status: filingStatus,
    other_annual_income: String(otherIncome),
    federal_rate_pct: String(federalRate),
  });
  if (selectedUserId) params.set("user_id", selectedUserId);

  const { data, isLoading, error } = useQuery<RmdPlannerResponse>({
    queryKey: ["rmd-planner", growthRate, filingStatus, otherIncome, federalRate, selectedUserId],
    queryFn: () => api.get(`/rmd/rmd-planner?${params}`).then((r) => r.data),
  });

  const chartData = data?.projection
    .filter((pt) => pt.total_rmd > 0)
    .map((pt) => ({
      year: pt.year,
      rmd: pt.total_rmd,
      tax: pt.estimated_tax_on_rmd,
    })) ?? [];

  return (
    <VStack spacing={6} align="stretch">
      <Text fontSize="sm" color="text.secondary">
        Required Minimum Distributions (RMDs) must begin at age 73 from all pre-tax retirement
        accounts. Failure to take RMDs results in a 25% penalty on the shortfall.
      </Text>

      {/* Controls */}
      <Card>
        <CardBody>
          <SimpleGrid columns={{ base: 1, md: 4 }} spacing={4}>
            <FormControl>
              <FormLabel fontSize="sm">Portfolio Growth Rate (%)</FormLabel>
              <NumberInput
                value={growthRate}
                min={0}
                max={15}
                step={0.5}
                onChange={(_, v) => !isNaN(v) && setGrowthRate(v)}
                size="sm"
              >
                <NumberInputField />
              </NumberInput>
            </FormControl>
            <FormControl>
              <FormLabel fontSize="sm">Filing Status</FormLabel>
              <Select size="sm" value={filingStatus} onChange={(e) => setFilingStatus(e.target.value)}>
                <option value="single">Single</option>
                <option value="married">Married Filing Jointly</option>
              </Select>
            </FormControl>
            <FormControl>
              <FormLabel fontSize="sm">Other Annual Income ($)</FormLabel>
              <NumberInput
                value={otherIncome}
                min={0}
                step={5000}
                onChange={(_, v) => !isNaN(v) && setOtherIncome(v)}
                size="sm"
              >
                <NumberInputField />
              </NumberInput>
            </FormControl>
            <FormControl>
              <FormLabel fontSize="sm">Federal Tax Rate (%)</FormLabel>
              <NumberInput
                value={federalRate}
                min={0}
                max={50}
                step={1}
                onChange={(_, v) => !isNaN(v) && setFederalRate(v)}
                size="sm"
              >
                <NumberInputField />
              </NumberInput>
              <FormHelperText fontSize="xs">
                Estimated from income — adjust as needed.
              </FormHelperText>
            </FormControl>
          </SimpleGrid>
        </CardBody>
      </Card>

      {isLoading && <Text color="text.secondary">Calculating RMD projections…</Text>}
      {error && (
        <Alert status="error">
          <AlertIcon />
          Failed to load RMD projections.
        </Alert>
      )}

      {data && (
        <>
          {/* Summary */}
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
            <Stat>
              <StatLabel fontSize="xs">Current Age</StatLabel>
              <StatNumber fontSize="lg">{data.current_age ?? "—"}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel fontSize="xs">Years Until RMDs</StatLabel>
              <StatNumber fontSize="lg">
                {data.years_until_rmd > 0 ? data.years_until_rmd : (
                  <Badge colorScheme="red">Active Now</Badge>
                )}
              </StatNumber>
              <StatHelpText fontSize="xs">Start at age {data.rmd_start_age}</StatHelpText>
            </Stat>
            <Stat>
              <StatLabel fontSize="xs">Total Pre-Tax Balance</StatLabel>
              <StatNumber fontSize="lg">{fmtCompact(data.total_current_rmd_balance)}</StatNumber>
              <StatHelpText fontSize="xs">{data.accounts.length} accounts</StatHelpText>
            </Stat>
            <Stat>
              <StatLabel fontSize="xs">Lifetime RMD Estimate</StatLabel>
              <StatNumber fontSize="lg">{fmtCompact(data.total_lifetime_rmd_estimate)}</StatNumber>
              <StatHelpText fontSize="xs">
                ~{fmtCompact(data.total_lifetime_tax_estimate)} in taxes
              </StatHelpText>
            </Stat>
          </SimpleGrid>

          {data.years_until_rmd > 0 && (
            <Alert status="info" variant="subtle">
              <AlertIcon />
              <AlertDescription fontSize="sm">
                RMDs begin at age {data.rmd_start_age}. You have {data.years_until_rmd} years
                to consider Roth conversions to reduce your future RMD burden.
              </AlertDescription>
            </Alert>
          )}

          {/* Chart */}
          {chartData.length > 0 && (
            <Box>
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                  <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                  <YAxis tickFormatter={(v) => fmtCompact(v)} tick={{ fontSize: 11 }} width={64} />
                  <Tooltip formatter={(v: number) => [fmt(v), ""]} />
                  <Legend />
                  <Line type="monotone" dataKey="rmd" stroke="#3182CE" name="Annual RMD" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="tax" stroke="#E53E3E" name="Est. Tax on RMD" strokeWidth={2} dot={false} strokeDasharray="4 2" />
                </LineChart>
              </ResponsiveContainer>
            </Box>
          )}

          {/* Projection table */}
          <Box overflowX="auto">
            <Table size="sm" variant="simple">
              <Thead>
                <Tr>
                  <Th>Year</Th>
                  <Th>Age</Th>
                  <Th isNumeric>Annual RMD</Th>
                  <Th isNumeric>Est. Tax</Th>
                  <Th isNumeric>Eff. Rate</Th>
                </Tr>
              </Thead>
              <Tbody>
                {data.projection.filter((pt) => pt.total_rmd > 0).slice(0, 20).map((pt) => (
                  <Tr key={pt.year}>
                    <Td>{pt.year}</Td>
                    <Td>{pt.age}</Td>
                    <Td isNumeric>{fmt(pt.total_rmd)}</Td>
                    <Td isNumeric color="red.500">{fmt(pt.estimated_tax_on_rmd)}</Td>
                    <Td isNumeric>{(pt.effective_rate_on_rmd * 100).toFixed(1)}%</Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>
        </>
      )}
    </VStack>
  );
};
