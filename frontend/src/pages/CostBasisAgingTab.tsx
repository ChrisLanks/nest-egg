/**
 * Cost Basis Aging tab — shows tax lots by holding period bucket for tax-loss harvesting decisions.
 */

import {
  Accordion,
  AccordionButton,
  AccordionIcon,
  AccordionItem,
  AccordionPanel,
  Alert,
  AlertDescription,
  AlertIcon,
  Badge,
  Box,
  HStack,
  SimpleGrid,
  Stat,
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
import api from "../services/api";
import { useCurrency } from "../contexts/CurrencyContext";

interface TaxLotItem {
  lot_id: string;
  account_id: string;
  account_name: string;
  ticker?: string;
  quantity: number;
  cost_basis_per_share: number;
  cost_basis_total: number;
  current_value?: number;
  unrealized_gain?: number;
  unrealized_gain_pct?: number;
  acquisition_date: string;
  days_held: number;
  holding_period: string;
  days_to_long_term: number;
  bucket: string;
}

interface CostBasisAgingResponse {
  lots: TaxLotItem[];
  approaching_count: number;
  approaching_value: number;
  short_term_gain: number;
  long_term_gain: number;
  short_term_loss: number;
  long_term_loss: number;
  total_open_lots: number;
  summary_tip: string;
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

interface LotTableProps {
  lots: TaxLotItem[];
}

const LotTable = ({ lots }: LotTableProps) => {
  if (lots.length === 0) {
    return <Text fontSize="sm" color="text.secondary" py={2}>No lots in this category.</Text>;
  }

  return (
    <Box overflowX="auto">
      <Table size="sm" variant="simple">
        <Thead>
          <Tr>
            <Th>Account</Th>
            <Th>Ticker</Th>
            <Th isNumeric>Qty</Th>
            <Th isNumeric>Cost Basis</Th>
            <Th isNumeric>
              <Tooltip
                label="Unrealized gain or loss based on current market price vs cost basis"
                hasArrow
                placement="top"
              >
                <Box as="span" cursor="help" textDecoration="underline dotted">
                  Gain / Loss
                </Box>
              </Tooltip>
            </Th>
            <Th isNumeric>
              <Tooltip
                label="Number of calendar days since acquisition date"
                hasArrow
                placement="top"
              >
                <Box as="span" cursor="help" textDecoration="underline dotted">
                  Days Held
                </Box>
              </Tooltip>
            </Th>
            <Th isNumeric>
              <Tooltip
                label="Days remaining before this lot qualifies for long-term capital gains tax rates (lower rates apply after 1 year)"
                hasArrow
                placement="top"
              >
                <Box as="span" cursor="help" textDecoration="underline dotted">
                  Days to LT
                </Box>
              </Tooltip>
            </Th>
          </Tr>
        </Thead>
        <Tbody>
          {lots.map((lot) => {
            const gainColor =
              lot.unrealized_gain == null
                ? undefined
                : lot.unrealized_gain >= 0
                ? "green.500"
                : "red.500";

            return (
              <Tr key={lot.lot_id}>
                <Td>{lot.account_name}</Td>
                <Td>{lot.ticker ?? "—"}</Td>
                <Td isNumeric>{lot.quantity.toFixed(3)}</Td>
                <Td isNumeric>{fmt(lot.cost_basis_total)}</Td>
                <Td isNumeric color={gainColor}>
                  {lot.unrealized_gain != null ? fmt(lot.unrealized_gain) : "—"}
                  {lot.unrealized_gain_pct != null && (
                    <Text as="span" fontSize="xs" ml={1}>
                      ({lot.unrealized_gain_pct >= 0 ? "+" : ""}{lot.unrealized_gain_pct.toFixed(1)}%)
                    </Text>
                  )}
                </Td>
                <Td isNumeric>{lot.days_held}</Td>
                <Td isNumeric color={lot.days_to_long_term <= 30 ? "orange.400" : undefined}>
                  {lot.days_to_long_term <= 0 ? "LT" : lot.days_to_long_term}
                </Td>
              </Tr>
            );
          })}
        </Tbody>
      </Table>
    </Box>
  );
};

export const CostBasisAgingTab = () => {
  const { formatCurrency } = useCurrency();

  const { data, isLoading, error } = useQuery<CostBasisAgingResponse>({
    queryKey: ["cost-basis-aging"],
    queryFn: () => api.get("/holdings/cost-basis-aging").then((r) => r.data),
  });

  const approachingLots = data?.lots.filter((l) => l.bucket === "approaching") ?? [];
  const shortTermLots = data?.lots.filter((l) => l.bucket === "short_term") ?? [];
  const longTermLots = data?.lots.filter((l) => l.bucket === "long_term") ?? [];

  return (
    <VStack spacing={6} align="stretch">
      {/* Holding period explanation */}
      <Alert status="info">
        <AlertIcon />
        <AlertDescription fontSize="sm">
          Lots held over 1 year qualify for lower long-term capital gains rates (0%, 15%, or 20% vs. ordinary income rates up to 37%). The &ldquo;Approaching&rdquo; bucket highlights lots within 30 days of crossing that threshold.
        </AlertDescription>
      </Alert>

      {isLoading && <Text color="text.secondary">Loading cost basis data…</Text>}
      {error && (
        <Alert status="error">
          <AlertIcon />
          Failed to load cost basis data.
        </Alert>
      )}

      {data && (
        <>
          {/* Summary stats */}
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
            <Stat>
              <StatLabel fontSize="xs">Approaching 1-Year</StatLabel>
              <StatNumber fontSize="lg">
                <Badge colorScheme={data.approaching_count > 0 ? "orange" : "gray"} fontSize="md" px={2}>
                  {data.approaching_count}
                </Badge>
              </StatNumber>
            </Stat>
            <Stat>
              <StatLabel fontSize="xs">Short-Term Gain</StatLabel>
              <StatNumber fontSize="lg" color="green.500">{fmtCompact(data.short_term_gain)}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel fontSize="xs">Long-Term Gain</StatLabel>
              <StatNumber fontSize="lg" color="green.500">{fmtCompact(data.long_term_gain)}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel fontSize="xs">Short-Term Loss</StatLabel>
              <StatNumber fontSize="lg" color="red.500">{fmtCompact(data.short_term_loss)}</StatNumber>
            </Stat>
          </SimpleGrid>

          {data.summary_tip && (
            <Alert status={data.approaching_count > 0 ? "warning" : "info"}>
              <AlertIcon />
              <AlertDescription fontSize="sm">{data.summary_tip}</AlertDescription>
            </Alert>
          )}

          {/* Accordion sections */}
          <Accordion allowMultiple defaultIndex={[0]}>
            <AccordionItem>
              <AccordionButton>
                <HStack flex={1} justify="space-between">
                  <HStack>
                    <Box w={3} h={3} bg="orange.400" borderRadius="full" />
                    <Text fontWeight="medium">Approaching 1-Year</Text>
                  </HStack>
                  <Badge colorScheme="orange">{approachingLots.length} lots</Badge>
                </HStack>
                <AccordionIcon />
              </AccordionButton>
              <AccordionPanel pb={4}>
                <LotTable lots={approachingLots} />
              </AccordionPanel>
            </AccordionItem>

            <AccordionItem>
              <AccordionButton>
                <HStack flex={1} justify="space-between">
                  <HStack>
                    <Box w={3} h={3} bg="yellow.400" borderRadius="full" />
                    <Text fontWeight="medium">Short-Term</Text>
                  </HStack>
                  <Badge colorScheme="yellow">{shortTermLots.length} lots</Badge>
                </HStack>
                <AccordionIcon />
              </AccordionButton>
              <AccordionPanel pb={4}>
                <LotTable lots={shortTermLots} />
              </AccordionPanel>
            </AccordionItem>

            <AccordionItem>
              <AccordionButton>
                <HStack flex={1} justify="space-between">
                  <HStack>
                    <Box w={3} h={3} bg="green.400" borderRadius="full" />
                    <Text fontWeight="medium">Long-Term</Text>
                  </HStack>
                  <Badge colorScheme="green">{longTermLots.length} lots</Badge>
                </HStack>
                <AccordionIcon />
              </AccordionButton>
              <AccordionPanel pb={4}>
                <LotTable lots={longTermLots} />
              </AccordionPanel>
            </AccordionItem>
          </Accordion>
        </>
      )}
    </VStack>
  );
};
