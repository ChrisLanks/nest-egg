/**
 * Dividend Calendar tab — shows dividend/income events organized by month for a given year.
 */

import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Collapse,
  Heading,
  HStack,
  Select,
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
  Tr,
  VStack,
  useDisclosure,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import api from "../services/api";
import { useCurrency } from "../contexts/CurrencyContext";
import { useUserView } from "../contexts/UserViewContext";

interface DividendEvent {
  id: string;
  ticker?: string;
  account_id: string;
  account_name: string;
  income_type: string;
  amount: number;
  ex_date?: string;
  pay_date?: string;
  shares?: number;
  per_share?: number;
}

interface MonthlyDividend {
  month: number;
  month_name: string;
  total: number;
  events: DividendEvent[];
}

interface TickerSummary {
  ticker: string;
  annual_total: number;
  event_count: number;
}

interface DividendCalendarResponse {
  year: number;
  months: MonthlyDividend[];
  annual_total: number;
  by_ticker: TickerSummary[];
  avg_monthly: number;
  best_month?: string;
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

interface MonthCellProps {
  month: MonthlyDividend;
  isBest: boolean;
}

const MonthCell = ({ month, isBest }: MonthCellProps) => {
  const { isOpen, onToggle } = useDisclosure();

  return (
    <Box
      border="1px"
      borderColor={isBest ? "green.300" : "gray.200"}
      borderRadius="md"
      p={3}
      bg={isBest ? "green.50" : undefined}
      _dark={{ bg: isBest ? "green.900" : undefined, borderColor: isBest ? "green.600" : "gray.600" }}
      cursor={month.events.length > 0 ? "pointer" : undefined}
      onClick={month.events.length > 0 ? onToggle : undefined}
    >
      <HStack justify="space-between" mb={1}>
        <Text fontSize="sm" fontWeight="medium">{month.month_name}</Text>
        {month.events.length > 0 && (
          <Badge colorScheme="blue" fontSize="xs">{month.events.length}</Badge>
        )}
      </HStack>
      <Text
        fontSize="lg"
        fontWeight="bold"
        color={month.total > 0 ? "green.500" : "gray.400"}
      >
        {month.total > 0 ? fmt(month.total) : "$0"}
      </Text>

      <Collapse in={isOpen}>
        <VStack align="stretch" spacing={1} mt={2} pt={2} borderTop="1px" borderColor="gray.200">
          {month.events.map((ev) => (
            <HStack key={ev.id} justify="space-between">
              <Text fontSize="xs" fontWeight="medium">{ev.ticker ?? ev.account_name}</Text>
              <Text fontSize="xs">{fmt(ev.amount)}</Text>
            </HStack>
          ))}
        </VStack>
      </Collapse>
    </Box>
  );
};

export const DividendCalendarTab = () => {
  const { formatCurrency } = useCurrency();
  const { selectedUserId, effectiveUserId } = useUserView();
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);

  const { data, isLoading, error } = useQuery<DividendCalendarResponse>({
    queryKey: ["dividend-calendar", year, effectiveUserId],
    queryFn: () => {
      const params = new URLSearchParams({ year: String(year) });
      if (effectiveUserId) params.set("user_id", effectiveUserId);
      return api.get(`/holdings/dividend-calendar?${params}`).then((r) => r.data);
    },
  });

  return (
    <VStack spacing={6} align="stretch">
      <HStack justify="space-between" flexWrap="wrap" gap={2}>
        <Text fontSize="sm" color="text.secondary">
          Dividend and income events by month.
        </Text>
        <Select
          size="sm"
          width="auto"
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
        >
          <option value={currentYear - 1}>{currentYear - 1}</option>
          <option value={currentYear}>{currentYear}</option>
          <option value={currentYear + 1}>{currentYear + 1}</option>
        </Select>
      </HStack>

      {isLoading && <Text color="text.secondary">Loading dividend calendar…</Text>}
      {error && (
        <Alert status="error">
          <AlertIcon />
          Failed to load dividend calendar.
        </Alert>
      )}

      {data && (
        <>
          {/* Annual summary */}
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
            <Stat>
              <StatLabel fontSize="xs">Annual Total</StatLabel>
              <StatNumber fontSize="lg" color="green.500">{fmtCompact(data.annual_total)}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel fontSize="xs">Avg Monthly</StatLabel>
              <StatNumber fontSize="lg">{fmt(data.avg_monthly)}</StatNumber>
            </Stat>
            {data.best_month && (
              <Stat>
                <StatLabel fontSize="xs">Best Month</StatLabel>
                <StatNumber fontSize="lg">{data.best_month}</StatNumber>
              </Stat>
            )}
          </SimpleGrid>

          {/* 12-month grid */}
          <SimpleGrid columns={{ base: 2, md: 3, lg: 4 }} spacing={3}>
            {data.months.map((month) => (
              <MonthCell
                key={month.month}
                month={month}
                isBest={month.month_name === data.best_month}
              />
            ))}
          </SimpleGrid>

          {/* By-ticker table */}
          {data.by_ticker.length > 0 && (
            <Box>
              <Heading size="xs" mb={3}>By Ticker / Source</Heading>
              <Box overflowX="auto">
                <Table size="sm" variant="simple">
                  <Thead>
                    <Tr>
                      <Th>Ticker</Th>
                      <Th isNumeric>Annual Total</Th>
                      <Th isNumeric># Events</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {data.by_ticker.map((t) => (
                      <Tr key={t.ticker}>
                        <Td fontWeight="medium">{t.ticker}</Td>
                        <Td isNumeric color="green.500">{fmt(t.annual_total)}</Td>
                        <Td isNumeric>{t.event_count}</Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </Box>
            </Box>
          )}
        </>
      )}
    </VStack>
  );
};
