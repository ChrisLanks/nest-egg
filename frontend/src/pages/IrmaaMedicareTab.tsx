/**
 * IRMAA & Medicare Cost Projection tab — shows projected Medicare premiums
 * including income-related surcharges based on income trajectory.
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
  FormLabel,
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
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import api from "../services/api";
import { NumberInput, NumberInputField } from "@chakra-ui/react";

interface IrmaaYearPoint {
  calendar_year: number;
  age: number | null;
  projected_magi: number;
  irmaa_tier: number;
  tier_label: string;
  part_b_monthly: number;
  part_d_monthly: number;
  irmaa_surcharge_monthly: number;
  total_monthly_premium: number;
  total_annual_premium: number;
}

interface IrmaaResponse {
  current_tier: number;
  current_tier_label: string;
  years_until_medicare: number;
  current_age: number | null;
  assumed_magi: number;
  filing_status: string;
  projection: IrmaaYearPoint[];
  lifetime_premium_estimate: number;
  optimization_tip: string | null;
}

const TIER_COLORS = ["green", "yellow", "orange", "red", "red", "purple"];

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

export const IrmaaMedicareTab = () => {
  const [magi, setMagi] = useState<number>(120000);
  const [filingStatus, setFilingStatus] = useState("single");
  const [growthRate, setGrowthRate] = useState(3);

  const params = new URLSearchParams({
    current_magi: String(magi),
    filing_status: filingStatus,
    income_growth_rate: String(growthRate / 100),
    projection_years: "20",
  });

  const { data, isLoading, error } = useQuery<IrmaaResponse>({
    queryKey: ["irmaa-projection", magi, filingStatus, growthRate],
    queryFn: () => api.get(`/tax/irmaa-projection?${params}`).then((r) => r.data),
    enabled: magi > 0,
  });

  const chartData =
    data?.projection.slice(0, 15).map((pt) => ({
      year: pt.calendar_year,
      base: pt.total_monthly_premium - pt.irmaa_surcharge_monthly,
      irmaa: pt.irmaa_surcharge_monthly,
    })) ?? [];

  return (
    <VStack spacing={6} align="stretch">
      <Text fontSize="sm" color="text.secondary">
        IRMAA surcharges increase Medicare Part B and D premiums for higher earners. The surcharge
        is based on income from 2 years prior.
      </Text>

      <Card>
        <CardBody>
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
            <FormControl>
              <FormLabel fontSize="sm">Current MAGI ($)</FormLabel>
              <NumberInput
                value={magi}
                min={0}
                step={5000}
                onChange={(_, v) => !isNaN(v) && setMagi(v)}
                size="sm"
              >
                <NumberInputField />
              </NumberInput>
            </FormControl>
            <FormControl>
              <FormLabel fontSize="sm">Filing Status</FormLabel>
              <Select
                size="sm"
                value={filingStatus}
                onChange={(e) => setFilingStatus(e.target.value)}
              >
                <option value="single">Single</option>
                <option value="married">Married Filing Jointly</option>
              </Select>
            </FormControl>
            <FormControl>
              <FormLabel fontSize="sm">Income Growth Rate (%/yr)</FormLabel>
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
          </SimpleGrid>
        </CardBody>
      </Card>

      {isLoading && <Text color="text.secondary">Calculating…</Text>}
      {error && (
        <Alert status="error">
          <AlertIcon />
          Failed to load projection.
        </Alert>
      )}

      {data && (
        <>
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
            <Stat>
              <StatLabel fontSize="xs">Current IRMAA Tier</StatLabel>
              <StatNumber fontSize="lg">
                <Badge colorScheme={TIER_COLORS[data.current_tier] ?? "gray"}>
                  {data.current_tier_label}
                </Badge>
              </StatNumber>
            </Stat>
            <Stat>
              <StatLabel fontSize="xs">Years Until Medicare</StatLabel>
              <StatNumber fontSize="lg">{data.years_until_medicare}</StatNumber>
              <StatHelpText fontSize="xs">Eligible at age 65</StatHelpText>
            </Stat>
            <Stat>
              <StatLabel fontSize="xs">Current Annual Premium</StatLabel>
              <StatNumber fontSize="lg">{fmt(data.projection[0]?.total_annual_premium ?? 0)}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel fontSize="xs">Lifetime Premium Est.</StatLabel>
              <StatNumber fontSize="lg">{fmtCompact(data.lifetime_premium_estimate)}</StatNumber>
              <StatHelpText fontSize="xs">20-year projection</StatHelpText>
            </Stat>
          </SimpleGrid>

          {data.optimization_tip && (
            <Alert status="info">
              <AlertIcon />
              <AlertDescription fontSize="sm">{data.optimization_tip}</AlertDescription>
            </Alert>
          )}

          <Box>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                <YAxis tickFormatter={(v) => `$${v}`} tick={{ fontSize: 11 }} width={48} />
                <Tooltip formatter={(v: number | undefined) => v != null ? [`$${v.toFixed(0)}/mo`, ""] : ["—", ""]} />
                <Legend />
                <Bar dataKey="base" stackId="a" fill="#3182CE" name="Base Premium" />
                <Bar dataKey="irmaa" stackId="a" fill="#E53E3E" name="IRMAA Surcharge" />
              </BarChart>
            </ResponsiveContainer>
          </Box>

          <Alert status="warning" variant="subtle">
            <AlertIcon />
            <AlertDescription fontSize="xs">
              IRMAA is calculated using MAGI from 2 years prior. Plan Roth conversions and large
              income events with this 2-year lag in mind.
            </AlertDescription>
          </Alert>

          <Box overflowX="auto">
            <Table size="sm" variant="simple">
              <Thead>
                <Tr>
                  <Th>Year</Th>
                  <Th>Age</Th>
                  <Th isNumeric>MAGI</Th>
                  <Th>Tier</Th>
                  <Th isNumeric>Monthly</Th>
                  <Th isNumeric>IRMAA Surcharge</Th>
                  <Th isNumeric>Annual Total</Th>
                </Tr>
              </Thead>
              <Tbody>
                {data.projection.slice(0, 15).map((pt) => (
                  <Tr key={pt.calendar_year}>
                    <Td>{pt.calendar_year}</Td>
                    <Td>{pt.age ?? "—"}</Td>
                    <Td isNumeric>{fmt(pt.projected_magi)}</Td>
                    <Td>
                      <Badge size="sm" colorScheme={TIER_COLORS[pt.irmaa_tier] ?? "gray"}>
                        {pt.tier_label}
                      </Badge>
                    </Td>
                    <Td isNumeric>{fmt(pt.total_monthly_premium)}</Td>
                    <Td isNumeric color={pt.irmaa_surcharge_monthly > 0 ? "red.500" : undefined}>
                      {pt.irmaa_surcharge_monthly > 0 ? `+${fmt(pt.irmaa_surcharge_monthly)}` : "—"}
                    </Td>
                    <Td isNumeric fontWeight={pt.irmaa_tier > 0 ? "bold" : undefined}>
                      {fmt(pt.total_annual_premium)}
                    </Td>
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
