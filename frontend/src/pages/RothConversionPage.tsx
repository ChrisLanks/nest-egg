/**
 * Roth Conversion Optimizer page
 *
 * Calculates the tax-optimal annual Roth conversion amount by modelling
 * bracket headroom, IRMAA tiers, and Required Minimum Distributions.
 * Balances are fetched automatically from connected accounts.
 */

import {
  Alert,
  AlertIcon,
  Box,
  Card,
  CardBody,
  Center,
  Container,
  FormControl,
  FormLabel,
  Heading,
  HStack,
  NumberInput,
  NumberInputField,
  Select,
  SimpleGrid,
  Spinner,
  Stat,
  StatHelpText,
  StatLabel,
  StatNumber,
  Switch,
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
import { useCallback, useEffect, useState } from "react";
import {
  smartInsightsApi,
  type RothConversionResponse,
} from "../api/smartInsights";
import api from "../services/api";
import { useUserView } from "../contexts/UserViewContext";
import { useCurrency } from "../contexts/CurrencyContext";

// ── Helpers ───────────────────────────────────────────────────────────────

const fmtPct = (n: number) => `${(n * 100).toFixed(0)}%`;

const STORAGE_KEY = "roth-conversion-assumptions";

function loadAssumptions(): {
  currentIncome: string;
  filingStatus: "single" | "married";
  expectedReturn: string;
  yearsToProject: string;
  respectIrmaa: boolean;
  _fromStorage: boolean;
} {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { ...JSON.parse(raw), _fromStorage: true };
  } catch {
    /* ignore */
  }
  // Fallback defaults — overridden by /settings/financial-defaults at runtime
  return {
    currentIncome: "80000",
    filingStatus: "single",
    expectedReturn: "7",
    yearsToProject: "20",
    respectIrmaa: true,
    _fromStorage: false,
  };
}

// ── Summary Stats ─────────────────────────────────────────────────────────

function SummaryStats({ data }: { data: RothConversionResponse }) {
  return (
    <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
      <Card variant="outline">
        <CardBody>
          <Stat>
            <StatLabel>Total to Convert</StatLabel>
            <StatNumber fontSize="xl">{fmt(data.total_converted)}</StatNumber>
            <StatHelpText>over projection period</StatHelpText>
          </Stat>
        </CardBody>
      </Card>

      <Card variant="outline">
        <CardBody>
          <Stat>
            <StatLabel>Tax Cost</StatLabel>
            <StatNumber fontSize="xl" color="orange.500">
              {fmt(data.total_tax_cost)}
            </StatNumber>
            <StatHelpText>conversion taxes</StatHelpText>
          </Stat>
        </CardBody>
      </Card>

      <Card variant="outline">
        <CardBody>
          <Stat>
            <StatLabel>Est. Tax Savings</StatLabel>
            <StatNumber fontSize="xl" color="green.500">
              {fmt(data.estimated_tax_savings)}
            </StatNumber>
            <StatHelpText>future taxes avoided</StatHelpText>
          </Stat>
        </CardBody>
      </Card>

      <Card variant="outline">
        <CardBody>
          <Stat>
            <StatLabel>Roth End Balance</StatLabel>
            <StatNumber fontSize="xl">
              {fmt(data.with_conversion_roth_end)}
            </StatNumber>
            <StatHelpText>
              vs {fmt(data.no_conversion_roth_end)} without
            </StatHelpText>
          </Stat>
        </CardBody>
      </Card>
    </SimpleGrid>
  );
}

// ── Year Table ────────────────────────────────────────────────────────────

function YearTable({
  years,
}: {
  data: RothConversionResponse;
  years: RothConversionResponse["years"];
}) {
  return (
    <Box overflowX="auto">
      <Table size="sm" variant="simple">
        <Thead>
          <Tr>
            <Th>Year</Th>
            <Th>Age</Th>
            <Th isNumeric>Trad. Start</Th>
            <Th isNumeric>Convert</Th>
            <Th isNumeric>RMD</Th>
            <Th isNumeric>Rate</Th>
            <Th isNumeric>Tax Cost</Th>
            <Th isNumeric>Trad. End</Th>
            <Th isNumeric>Roth End</Th>
          </Tr>
        </Thead>
        <Tbody>
          {years.map((yr) => (
            <Tr key={yr.year}>
              <Td>{yr.year}</Td>
              <Td>{yr.age}</Td>
              <Td isNumeric>{fmt(yr.traditional_balance_start)}</Td>
              <Td isNumeric>
                {yr.optimal_conversion > 0 ? (
                  <Text color="blue.500" fontWeight="semibold">
                    {fmt(yr.optimal_conversion)}
                  </Text>
                ) : (
                  <Text color="text.muted">—</Text>
                )}
              </Td>
              <Td isNumeric>
                {yr.rmd_amount > 0 ? (
                  <Tooltip label={yr.notes.find((n) => n.includes("RMD"))}>
                    <Text color="orange.500">{fmt(yr.rmd_amount)}</Text>
                  </Tooltip>
                ) : (
                  <Text color="text.muted">—</Text>
                )}
              </Td>
              <Td isNumeric>{fmtPct(yr.marginal_rate_at_conversion)}</Td>
              <Td isNumeric>
                {yr.tax_cost_of_conversion > 0
                  ? fmt(yr.tax_cost_of_conversion)
                  : "—"}
              </Td>
              <Td isNumeric>{fmt(yr.traditional_balance_end)}</Td>
              <Td isNumeric>{fmt(yr.roth_balance_end)}</Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
    </Box>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────

export const RothConversionPage = () => {
  const { currency } = useCurrency();

  const fmt = (n: number) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(n);
  const { selectedUserId, effectiveUserId } = useUserView();

  const saved = loadAssumptions();
  const [currentIncome, setCurrentIncome] = useState(saved.currentIncome);
  const [filingStatus, setFilingStatus] = useState<"single" | "married">(
    saved.filingStatus,
  );
  const [expectedReturn, setExpectedReturn] = useState(saved.expectedReturn);
  const [yearsToProject, setYearsToProject] = useState(saved.yearsToProject);
  const [respectIrmaa, setRespectIrmaa] = useState<boolean>(saved.respectIrmaa);
  const [assumedFutureRate, setAssumedFutureRate] = useState<string>("");

  // Seed defaults from backend when no localStorage value exists
  useEffect(() => {
    if (saved._fromStorage) return;
    api.get("/settings/financial-defaults").then((r) => {
      const d = r.data;
      setCurrentIncome(String(d.default_annual_spending ?? 80000));
      setExpectedReturn(String(Math.round((d.default_expected_return ?? 0.07) * 100)));
    }).catch(() => {/* keep hardcoded fallback */});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const persist = useCallback(
    (
      income: string,
      status: string,
      ret: string,
      years: string,
      irmaa: boolean,
    ) => {
      try {
        localStorage.setItem(
          STORAGE_KEY,
          JSON.stringify({
            currentIncome: income,
            filingStatus: status,
            expectedReturn: ret,
            yearsToProject: years,
            respectIrmaa: irmaa,
          }),
        );
      } catch {
        /* ignore */
      }
    },
    [],
  );

  const incomeNum = parseFloat(currentIncome) || 0;
  const returnNum = parseFloat(expectedReturn) || 7;
  const yearsNum = parseInt(yearsToProject) || 20;
  const futureRateNum = assumedFutureRate ? parseFloat(assumedFutureRate) / 100 : undefined;

  const { data, isLoading, isError } = useQuery<RothConversionResponse>({
    queryKey: [
      "roth-conversion", effectiveUserId,
      incomeNum,
      filingStatus,
      returnNum,
      yearsNum,
      respectIrmaa,
      futureRateNum,
    ],
    queryFn: () =>
      smartInsightsApi.getRothConversion({
        user_id: effectiveUserId || undefined,
        current_income: incomeNum,
        filing_status: filingStatus,
        expected_return: returnNum / 100,
        years_to_project: yearsNum,
        respect_irmaa: respectIrmaa,
        assumed_future_rate: futureRateNum,
      }),
    enabled: incomeNum > 0,
    placeholderData: (prev) => prev,
  });

  return (
    <Container maxW="6xl" py={6}>
      <VStack align="start" spacing={6}>
        {/* Header */}
        <Box>
          <Heading size="lg">Roth Conversion Optimizer</Heading>
          <Text color="text.secondary" mt={1}>
            See how much to convert each year to minimize lifetime taxes.
            Balances are pulled from your connected accounts automatically.
          </Text>
        </Box>

        {/* No retirement accounts */}
        {data && !data.has_retirement_accounts && (
          <Alert status="info" borderRadius="lg">
            <AlertIcon />
            No traditional IRA or 401(k) accounts found. Connect your retirement
            accounts to use this tool.
          </Alert>
        )}

        {/* Inputs */}
        <Card variant="outline" w="full">
          <CardBody>
            <SimpleGrid columns={{ base: 1, sm: 2, md: 3 }} spacing={4}>
              <FormControl>
                <FormLabel fontSize="sm">
                  Annual Income (excl. conversion)
                </FormLabel>
                <NumberInput
                  value={currentIncome}
                  onChange={(v) => {
                    setCurrentIncome(v);
                    persist(
                      v,
                      filingStatus,
                      expectedReturn,
                      yearsToProject,
                      respectIrmaa,
                    );
                  }}
                  min={0}
                >
                  <NumberInputField placeholder="80000" />
                </NumberInput>
              </FormControl>

              <FormControl>
                <FormLabel fontSize="sm">Filing Status</FormLabel>
                <Select
                  value={filingStatus}
                  onChange={(e) => {
                    const v = e.target.value as "single" | "married";
                    setFilingStatus(v);
                    persist(
                      currentIncome,
                      v,
                      expectedReturn,
                      yearsToProject,
                      respectIrmaa,
                    );
                  }}
                >
                  <option value="single">Single</option>
                  <option value="married">Married Filing Jointly</option>
                </Select>
              </FormControl>

              <FormControl>
                <FormLabel fontSize="sm">Expected Return (%)</FormLabel>
                <NumberInput
                  value={expectedReturn}
                  onChange={(v) => {
                    setExpectedReturn(v);
                    persist(
                      currentIncome,
                      filingStatus,
                      v,
                      yearsToProject,
                      respectIrmaa,
                    );
                  }}
                  min={0}
                  max={20}
                >
                  <NumberInputField placeholder="7" />
                </NumberInput>
              </FormControl>

              <FormControl>
                <FormLabel fontSize="sm">Years to Project</FormLabel>
                <NumberInput
                  value={yearsToProject}
                  onChange={(v) => {
                    setYearsToProject(v);
                    persist(
                      currentIncome,
                      filingStatus,
                      expectedReturn,
                      v,
                      respectIrmaa,
                    );
                  }}
                  min={1}
                  max={40}
                >
                  <NumberInputField placeholder="20" />
                </NumberInput>
              </FormControl>

              <FormControl>
                <FormLabel fontSize="sm">Respect IRMAA limits</FormLabel>
                <HStack mt={2}>
                  <Switch
                    isChecked={respectIrmaa}
                    onChange={(e) => {
                      const v = e.target.checked;
                      setRespectIrmaa(v);
                      persist(
                        currentIncome,
                        filingStatus,
                        expectedReturn,
                        yearsToProject,
                        v,
                      );
                    }}
                    colorScheme="brand"
                  />
                  <Text fontSize="sm" color="text.secondary">
                    Cap conversions to avoid Medicare surcharges
                  </Text>
                </HStack>
              </FormControl>

              <FormControl>
                <Tooltip label="Your assumed future marginal tax rate in retirement — used to estimate long-term tax savings. Leave blank to use your current-year bracket as the best guess." hasArrow placement="top">
                  <FormLabel fontSize="sm" cursor="help" textDecoration="underline dotted" display="inline-block">
                    Future Tax Rate (%) <Text as="span" color="text.secondary" fontSize="xs">— optional override</Text>
                  </FormLabel>
                </Tooltip>
                <NumberInput
                  value={assumedFutureRate}
                  onChange={(v) => setAssumedFutureRate(v)}
                  min={0}
                  max={60}
                  step={1}
                >
                  <NumberInputField placeholder={`Default: current bracket`} />
                </NumberInput>
              </FormControl>
            </SimpleGrid>
          </CardBody>
        </Card>

        {/* Loading */}
        {isLoading && (
          <Center w="full" py={12}>
            <Spinner size="xl" color="brand.500" thickness="4px" />
          </Center>
        )}

        {/* Error */}
        {isError && (
          <Alert status="error" borderRadius="lg">
            <AlertIcon />
            Failed to calculate Roth conversion. Please check your inputs and
            try again.
          </Alert>
        )}

        {/* Results */}
        {data && data.has_retirement_accounts && !isLoading && (
          <>
            <SummaryStats data={data} />

            {/* Summary text */}
            <Card
              variant="outline"
              w="full"
              bg="blue.50"
              _dark={{ bg: "blue.900" }}
            >
              <CardBody>
                <Text fontSize="sm">{data.summary}</Text>
              </CardBody>
            </Card>

            {/* Year-by-year table */}
            <Box w="full">
              <Heading size="sm" mb={3}>
                Year-by-Year Breakdown
              </Heading>
              <YearTable data={data} years={data.years} />
            </Box>

            {/* Disclaimer */}
            <Text fontSize="xs" color="text.muted">
              This is an educational estimate only — not tax advice. Consult a
              tax professional before making conversion decisions. Projections
              use {returnNum}% annual return and inflation-adjusted 2026
              brackets.
            </Text>
          </>
        )}
      </VStack>
    </Container>
  );
};

export default RothConversionPage;
