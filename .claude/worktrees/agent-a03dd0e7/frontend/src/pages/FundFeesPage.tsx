/**
 * Fund Fees (Investment Health) page
 *
 * Analyses expense ratios across all investment holdings, showing:
 * - Portfolio-level weighted ER and annual fee drag
 * - 10 and 20-year compounding impact vs a 0.03% benchmark
 * - Per-holding breakdown with flags and suggestions
 */

import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Card,
  CardBody,
  Center,
  Container,
  Heading,
  HStack,
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
import { smartInsightsApi, type HoldingFeeDetail } from "../api/smartInsights";
import { useUserView } from "../contexts/UserViewContext";

// ── Helpers ───────────────────────────────────────────────────────────────

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);

const fmtPct = (n: number, decimals = 2) => `${(n * 100).toFixed(decimals)}%`;

const flagColors: Record<HoldingFeeDetail["flag"], string> = {
  ok: "green",
  high_cost: "orange",
  extreme_cost: "red",
  no_data: "gray",
};

const flagLabels: Record<HoldingFeeDetail["flag"], string> = {
  ok: "Low Cost",
  high_cost: "High Cost",
  extreme_cost: "Extreme Cost",
  no_data: "No Data",
};

// ── Holdings Table ────────────────────────────────────────────────────────

function HoldingsTable({ holdings }: { holdings: HoldingFeeDetail[] }) {
  return (
    <Box overflowX="auto">
      <Table size="sm" variant="simple">
        <Thead>
          <Tr>
            <Th>Ticker / Name</Th>
            <Th isNumeric>Market Value</Th>
            <Th isNumeric>Expense Ratio</Th>
            <Th isNumeric>Annual Fee</Th>
            <Th isNumeric>10-yr Drag</Th>
            <Th isNumeric>20-yr Drag</Th>
            <Th>Flag</Th>
          </Tr>
        </Thead>
        <Tbody>
          {holdings.map((h, i) => (
            <Tr key={`${h.ticker ?? h.name ?? "unknown"}-${i}`}>
              <Td>
                <VStack align="start" spacing={0}>
                  <Text fontWeight="semibold" fontSize="sm">
                    {h.ticker ?? "—"}
                  </Text>
                  {h.name && (
                    <Text fontSize="xs" color="text.muted" noOfLines={1}>
                      {h.name}
                    </Text>
                  )}
                </VStack>
              </Td>
              <Td isNumeric>{fmt(h.market_value)}</Td>
              <Td isNumeric>
                {h.flag === "no_data" ? (
                  <Text color="text.muted" fontSize="xs">
                    N/A
                  </Text>
                ) : (
                  fmtPct(h.expense_ratio)
                )}
              </Td>
              <Td isNumeric>
                {h.annual_fee > 0 ? (
                  <Text color={h.flag === "ok" ? undefined : "orange.500"}>
                    {fmt(h.annual_fee)}
                  </Text>
                ) : (
                  <Text color="text.muted">—</Text>
                )}
              </Td>
              <Td isNumeric>
                {h.ten_year_drag > 0 ? (
                  fmt(h.ten_year_drag)
                ) : (
                  <Text color="text.muted">—</Text>
                )}
              </Td>
              <Td isNumeric>
                {h.twenty_year_drag > 0 ? (
                  fmt(h.twenty_year_drag)
                ) : (
                  <Text color="text.muted">—</Text>
                )}
              </Td>
              <Td>
                <Tooltip label={h.suggestion ?? undefined} hasArrow>
                  <Badge
                    colorScheme={flagColors[h.flag]}
                    size="sm"
                    cursor={h.suggestion ? "help" : "default"}
                  >
                    {flagLabels[h.flag]}
                  </Badge>
                </Tooltip>
              </Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
    </Box>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────

export const FundFeesPage = () => {
  const { selectedUserId } = useUserView();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["fund-fees", selectedUserId],
    queryFn: () =>
      smartInsightsApi.getFundFees({
        user_id: selectedUserId || undefined,
      }),
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
          Failed to load fund fee analysis. Please try again.
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxW="6xl" py={6}>
      <VStack align="start" spacing={6}>
        {/* Header */}
        <Box>
          <Heading size="lg">Investment Health</Heading>
          <Text color="text.secondary" mt={1}>
            Understand the true cost of your fund expense ratios and their
            long-term compounding impact on your portfolio.
          </Text>
        </Box>

        {/* No holdings */}
        {data && !data.has_investment_holdings && (
          <Alert status="info" borderRadius="lg">
            <AlertIcon />
            No investment holdings with price data found. Connect your brokerage
            or retirement accounts to see fee analysis.
          </Alert>
        )}

        {/* Summary stats */}
        {data && data.has_investment_holdings && (
          <>
            <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4} w="full">
              <Card variant="outline">
                <CardBody>
                  <Stat>
                    <StatLabel>Total Invested</StatLabel>
                    <StatNumber fontSize="xl">
                      {fmt(data.total_invested)}
                    </StatNumber>
                    <StatHelpText>
                      {data.holdings_with_er_data} holdings with ER data
                      {data.holdings_missing_er_data > 0 &&
                        ` · ${data.holdings_missing_er_data} missing`}
                    </StatHelpText>
                  </Stat>
                </CardBody>
              </Card>

              <Card variant="outline">
                <CardBody>
                  <Stat>
                    <StatLabel>Annual Fee Drag</StatLabel>
                    <StatNumber
                      fontSize="xl"
                      color={
                        data.annual_fee_drag > 1000 ? "orange.500" : undefined
                      }
                    >
                      {fmt(data.annual_fee_drag)}
                    </StatNumber>
                    <StatHelpText>
                      {fmtPct(data.weighted_avg_expense_ratio)} weighted avg ER
                    </StatHelpText>
                  </Stat>
                </CardBody>
              </Card>

              <Card variant="outline">
                <CardBody>
                  <Stat>
                    <StatLabel>10-yr vs Benchmark</StatLabel>
                    <StatNumber
                      fontSize="xl"
                      color={
                        data.ten_year_impact_vs_benchmark > 0
                          ? "red.500"
                          : "green.500"
                      }
                    >
                      {data.ten_year_impact_vs_benchmark > 0
                        ? `-${fmt(data.ten_year_impact_vs_benchmark)}`
                        : "—"}
                    </StatNumber>
                    <StatHelpText>
                      vs {fmtPct(data.benchmark_expense_ratio)} benchmark
                    </StatHelpText>
                  </Stat>
                </CardBody>
              </Card>

              <Card variant="outline">
                <CardBody>
                  <Stat>
                    <StatLabel>20-yr vs Benchmark</StatLabel>
                    <StatNumber
                      fontSize="xl"
                      color={
                        data.twenty_year_impact_vs_benchmark > 0
                          ? "red.500"
                          : "green.500"
                      }
                    >
                      {data.twenty_year_impact_vs_benchmark > 0
                        ? `-${fmt(data.twenty_year_impact_vs_benchmark)}`
                        : "—"}
                    </StatNumber>
                    <StatHelpText>compounding drag</StatHelpText>
                  </Stat>
                </CardBody>
              </Card>
            </SimpleGrid>

            {/* High cost count badge */}
            {data.high_cost_count > 0 && (
              <HStack>
                <Badge colorScheme="red" px={3} py={1} borderRadius="full">
                  {data.high_cost_count} high-cost holding
                  {data.high_cost_count > 1 ? "s" : ""} ({">"} 0.50% ER)
                </Badge>
                <Text fontSize="sm" color="text.secondary">
                  Hover any flagged row below for a replacement suggestion.
                </Text>
              </HStack>
            )}

            {/* Summary text */}
            <Card
              variant="outline"
              w="full"
              bg="purple.50"
              _dark={{ bg: "purple.900" }}
            >
              <CardBody>
                <Text fontSize="sm">{data.summary}</Text>
              </CardBody>
            </Card>

            {/* Holdings table */}
            <Box w="full">
              <Heading size="sm" mb={3}>
                Holdings Breakdown
              </Heading>
              <HoldingsTable holdings={data.holdings} />
            </Box>

            {/* Disclaimer */}
            <Text fontSize="xs" color="text.muted">
              Benchmark: Vanguard Total Stock Market ETF (VTI) at 0.03% ER. Drag
              calculated at 7% assumed annual return. This is not investment
              advice — consult a financial advisor.
            </Text>
          </>
        )}
      </VStack>
    </Container>
  );
};

export default FundFeesPage;
