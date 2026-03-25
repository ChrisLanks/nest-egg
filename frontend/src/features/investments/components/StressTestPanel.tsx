/**
 * Portfolio Stress Test panel for the Investments page.
 *
 * Runs all historical and hypothetical stress scenarios against the user's
 * current portfolio composition and shows pre/post values by asset class.
 */

import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Card,
  CardBody,
  Center,
  HStack,
  Progress,
  SimpleGrid,
  Spinner,
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
import { useQuery } from "@tanstack/react-query";
import api from "../../../services/api";
import { useUserView } from "../../../contexts/UserViewContext";

const fmt = (v: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(v);

const fmtPct = (v: number) =>
  `${(v * 100).toFixed(1)}%`;

interface AssetClassResult {
  before: number;
  after: number;
  change_pct: number;
}

interface ScenarioResult {
  scenario_key: string;
  scenario_label: string;
  portfolio_before: number;
  portfolio_after: number;
  dollar_change: number;
  pct_change: number;
  by_asset_class: {
    equity: AssetClassResult;
    bonds: AssetClassResult;
    other: AssetClassResult;
  };
}

interface Portfolio {
  equity: number;
  bonds: number;
  other: number;
  total: number;
}

function severityColor(pct: number): string {
  if (pct <= -0.40) return "red";
  if (pct <= -0.20) return "orange";
  if (pct <= -0.10) return "yellow";
  return "green";
}

export default function StressTestPanel() {
  const { selectedUserId } = useUserView();

  const params: Record<string, string> = {};
  if (selectedUserId) params.user_id = selectedUserId;

  const { data: results = [], isLoading, error } = useQuery<ScenarioResult[]>({
    queryKey: ["stress-test-all", selectedUserId],
    queryFn: async () => {
      const res = await api.get("/stress-test/run-all", { params });
      return res.data;
    },
  });

  // Derive portfolio composition from the first result (all use same portfolio)
  const portfolio: Portfolio | null =
    results.length > 0
      ? {
          equity: results[0].by_asset_class.equity.before,
          bonds: results[0].by_asset_class.bonds.before,
          other: results[0].by_asset_class.other.before,
          total: results[0].portfolio_before,
        }
      : null;

  if (isLoading) {
    return (
      <Center py={12}>
        <Spinner size="xl" />
      </Center>
    );
  }

  if (error) {
    return (
      <Alert status="error">
        <AlertIcon />
        Failed to load stress test results.
      </Alert>
    );
  }

  if (results.length === 0 || !portfolio || portfolio.total === 0) {
    return (
      <Alert status="info" variant="subtle" borderRadius="md">
        <AlertIcon />
        <Text fontSize="sm">
          No holdings found. Add investment accounts with holdings to run
          stress scenarios against your portfolio.
        </Text>
      </Alert>
    );
  }

  const equityPct = portfolio.total > 0 ? portfolio.equity / portfolio.total : 0;
  const bondPct = portfolio.total > 0 ? portfolio.bonds / portfolio.total : 0;
  const otherPct = portfolio.total > 0 ? portfolio.other / portfolio.total : 0;

  return (
    <VStack spacing={6} align="stretch">
      {/* Header */}
      <Box>
        <Text fontWeight="bold" fontSize="lg">Historical Stress Test</Text>
        <Text fontSize="sm" color="text.secondary" mt={1}>
          Applies real historical market crash returns to your <strong>current portfolio</strong> —
          showing the actual dollar impact if each crisis happened today.
          Unlike Monte Carlo Projection (which simulates future distributions), this uses
          fixed historical equity/bond drops from events like 2008 or COVID-19.
        </Text>
      </Box>

      {/* Disclaimer */}
      <Alert status="warning" variant="subtle" borderRadius="md">
        <AlertIcon />
        <Text fontSize="sm">
          Stress test results are hypothetical estimates based on historical
          market data. Past market crashes do not predict future performance.
          This is not investment advice.
        </Text>
      </Alert>

      {/* Portfolio Composition */}
      <Box>
        <Text fontWeight="semibold" mb={3}>
          Current Portfolio Composition
        </Text>
        <SimpleGrid columns={{ base: 1, md: 4 }} spacing={4} mb={4}>
          {[
            { label: "Total Portfolio", value: fmt(portfolio.total), help: "Market value of all holdings" },
            { label: "Equities", value: fmt(portfolio.equity), help: `${fmtPct(equityPct)} of portfolio` },
            { label: "Bonds", value: fmt(portfolio.bonds), help: `${fmtPct(bondPct)} of portfolio` },
            { label: "Other", value: fmt(portfolio.other), help: `${fmtPct(otherPct)} of portfolio` },
          ].map(({ label, value, help }) => (
            <Card key={label} variant="outline">
              <CardBody py={3}>
                <Stat>
                  <StatLabel fontSize="xs">{label}</StatLabel>
                  <StatNumber fontSize="lg">{value}</StatNumber>
                  <StatHelpText fontSize="xs">{help}</StatHelpText>
                </Stat>
              </CardBody>
            </Card>
          ))}
        </SimpleGrid>

        {/* Allocation bar */}
        <Box>
          <Text fontSize="xs" color="text.secondary" mb={1}>
            Allocation breakdown
          </Text>
          <HStack spacing={0} borderRadius="md" overflow="hidden" h={4}>
            {equityPct > 0 && (
              <Tooltip label={`Equity ${fmtPct(equityPct)}`}>
                <Box bg="purple.400" h="full" w={`${equityPct * 100}%`} />
              </Tooltip>
            )}
            {bondPct > 0 && (
              <Tooltip label={`Bonds ${fmtPct(bondPct)}`}>
                <Box bg="blue.300" h="full" w={`${bondPct * 100}%`} />
              </Tooltip>
            )}
            {otherPct > 0 && (
              <Tooltip label={`Other ${fmtPct(otherPct)}`}>
                <Box bg="gray.300" h="full" w={`${otherPct * 100}%`} />
              </Tooltip>
            )}
          </HStack>
          <HStack spacing={4} mt={1}>
            <HStack spacing={1}><Box w={2} h={2} borderRadius="sm" bg="purple.400" /><Text fontSize="xs">Equity</Text></HStack>
            <HStack spacing={1}><Box w={2} h={2} borderRadius="sm" bg="blue.300" /><Text fontSize="xs">Bonds</Text></HStack>
            <HStack spacing={1}><Box w={2} h={2} borderRadius="sm" bg="gray.300" /><Text fontSize="xs">Other</Text></HStack>
          </HStack>
        </Box>
      </Box>

      {/* Scenario Results */}
      <Box>
        <Text fontWeight="semibold" mb={1}>
          Scenario Results
        </Text>
        <Text fontSize="sm" color="text.secondary" mb={4}>
          Sorted from worst to best outcome. Results show estimated portfolio
          impact based on historical market behavior during each event.
        </Text>

        <Box overflowX="auto">
          <Table size="sm" variant="simple">
            <Thead>
              <Tr>
                <Th>Scenario</Th>
                <Th isNumeric>Before</Th>
                <Th isNumeric>After</Th>
                <Th isNumeric>Loss</Th>
                <Th isNumeric>Impact</Th>
                <Th>Severity</Th>
              </Tr>
            </Thead>
            <Tbody>
              {results.map((r) => (
                <Tr key={r.scenario_key}>
                  <Td>
                    <Text fontSize="sm" fontWeight="medium">
                      {r.scenario_label}
                    </Text>
                  </Td>
                  <Td isNumeric fontSize="sm">
                    {fmt(r.portfolio_before)}
                  </Td>
                  <Td isNumeric fontSize="sm">
                    {fmt(r.portfolio_after)}
                  </Td>
                  <Td isNumeric>
                    <Text
                      fontSize="sm"
                      fontWeight="medium"
                      color="finance.negative"
                    >
                      {fmt(r.dollar_change)}
                    </Text>
                  </Td>
                  <Td isNumeric>
                    <Text
                      fontSize="sm"
                      fontWeight="bold"
                      color={r.pct_change <= -0.20 ? "red.500" : r.pct_change <= -0.10 ? "orange.500" : "yellow.600"}
                    >
                      {fmtPct(r.pct_change)}
                    </Text>
                  </Td>
                  <Td>
                    <Badge
                      colorScheme={severityColor(r.pct_change)}
                      fontSize="xs"
                    >
                      {r.pct_change <= -0.40
                        ? "Severe"
                        : r.pct_change <= -0.20
                        ? "High"
                        : r.pct_change <= -0.10
                        ? "Moderate"
                        : "Low"}
                    </Badge>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      </Box>

      {/* Asset Class Breakdown for worst scenario */}
      {results.length > 0 && (
        <Box>
          <Text fontWeight="semibold" mb={1}>
            Worst Case Breakdown — {results[0].scenario_label}
          </Text>
          <Text fontSize="sm" color="text.secondary" mb={4}>
            How each asset class would be affected in the most severe scenario.
          </Text>
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
            {(
              [
                {
                  label: "Equities",
                  data: results[0].by_asset_class.equity,
                  color: "purple",
                },
                {
                  label: "Bonds",
                  data: results[0].by_asset_class.bonds,
                  color: "blue",
                },
                {
                  label: "Other",
                  data: results[0].by_asset_class.other,
                  color: "gray",
                },
              ] as const
            ).map(({ label, data, color }) => (
              <Card key={label} variant="outline">
                <CardBody py={3}>
                  <HStack justify="space-between" mb={2}>
                    <Text fontSize="sm" fontWeight="medium">
                      {label}
                    </Text>
                    <Badge colorScheme={color} fontSize="xs">
                      {fmtPct(data.change_pct)}
                    </Badge>
                  </HStack>
                  <HStack justify="space-between">
                    <VStack align="start" spacing={0}>
                      <Text fontSize="xs" color="text.secondary">Before</Text>
                      <Text fontSize="sm">{fmt(data.before)}</Text>
                    </VStack>
                    <Text color="text.muted">→</Text>
                    <VStack align="end" spacing={0}>
                      <Text fontSize="xs" color="text.secondary">After</Text>
                      <Text fontSize="sm" color="finance.negative">{fmt(data.after)}</Text>
                    </VStack>
                  </HStack>
                  <Progress
                    mt={2}
                    value={data.before > 0 ? (data.after / data.before) * 100 : 0}
                    colorScheme={color}
                    size="xs"
                    borderRadius="full"
                  />
                </CardBody>
              </Card>
            ))}
          </SimpleGrid>
        </Box>
      )}
    </VStack>
  );
}
