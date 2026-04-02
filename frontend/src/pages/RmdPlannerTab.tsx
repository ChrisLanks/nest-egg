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
  FormLabel,
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
  Tooltip as ChakraTooltip,
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

  const params = new URLSearchParams({
    projection_years: "20",
    growth_rate: String(growthRate / 100),
    filing_status: filingStatus,
    other_annual_income: String(otherIncome),
  });
  if (selectedUserId) params.set("user_id", selectedUserId);

  const { data, isLoading, error } = useQuery<RmdPlannerResponse>({
    queryKey: ["rmd-planner", growthRate, filingStatus, otherIncome, selectedUserId],
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
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
            <FormControl>
              <ChakraTooltip label="Assumed annual return on your pre-tax retirement accounts before RMDs are taken. Affects projected account balances and future RMD amounts." hasArrow placement="top">
                <FormLabel fontSize="sm" cursor="default">Portfolio Growth Rate (%)</FormLabel>
              </ChakraTooltip>
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
              <ChakraTooltip label="Used to estimate the tax owed on your RMDs using IRS tax brackets. Note: RMD amounts are the same regardless of filing status — only the tax estimate changes." hasArrow placement="top">
                <FormLabel fontSize="sm" cursor="default">Filing Status</FormLabel>
              </ChakraTooltip>
              <Select size="sm" value={filingStatus} onChange={(e) => setFilingStatus(e.target.value)}>
                <option value="single">Single</option>
                <option value="married">Married Filing Jointly</option>
              </Select>
            </FormControl>
            <FormControl>
              <ChakraTooltip label="Non-RMD income (Social Security, pension, wages, etc.) in the RMD year. Used with your filing status to calculate the marginal tax rate on your RMDs." hasArrow placement="top">
                <FormLabel fontSize="sm" cursor="default">Other Annual Income ($)</FormLabel>
              </ChakraTooltip>
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

      {data && !data.current_age && (
        <Alert status="warning">
          <AlertIcon />
          <AlertDescription fontSize="sm">
            No birthdate set on your profile. Go to{" "}
            <strong>Preferences → Profile</strong> and add your date of birth
            so RMD projections can calculate your age and start year.
          </AlertDescription>
        </Alert>
      )}

      {data && data.accounts.length === 0 && (
        <Alert status="info">
          <AlertIcon />
          <AlertDescription fontSize="sm">
            No pre-tax retirement accounts found (401k, IRA, 403b, etc.).
            Add accounts under <strong>Accounts</strong> to see your RMD
            projections.
          </AlertDescription>
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
          {data.projection.filter((pt) => pt.total_rmd > 0).length === 0 ? (
            <Alert status="info" variant="subtle">
              <AlertIcon />
              <AlertDescription fontSize="sm">
                No RMDs fall within the {data.projection.length}-year projection window. RMDs begin at age {data.rmd_start_age}
                {data.current_age ? ` — ${data.years_until_rmd} year${data.years_until_rmd !== 1 ? "s" : ""} away` : ""}. Increase "Years to Project" above to see future RMD amounts.
              </AlertDescription>
            </Alert>
          ) : (
            <Box overflowX="auto">
              <Table size="sm" variant="simple">
                <Thead>
                  <Tr>
                    <Th>Year</Th>
                    <Th>Age</Th>
                    <ChakraTooltip label="Required Minimum Distribution — account balance ÷ IRS Uniform Lifetime Table factor. Does not change with filing status." hasArrow placement="top">
                      <Th isNumeric cursor="default">Annual RMD</Th>
                    </ChakraTooltip>
                    <ChakraTooltip label="Estimated tax on the RMD based on your filing status and other income using IRS marginal brackets. Changes when filing status changes." hasArrow placement="top">
                      <Th isNumeric cursor="default">Est. Tax</Th>
                    </ChakraTooltip>
                    <ChakraTooltip label="Marginal tax rate applied to the RMD portion of your income." hasArrow placement="top">
                      <Th isNumeric cursor="default">Eff. Rate</Th>
                    </ChakraTooltip>
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
          )}
        </>
      )}
    </VStack>
  );
};
