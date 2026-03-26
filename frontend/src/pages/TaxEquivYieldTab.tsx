/**
 * Tax-Equivalent Yield tab — shows after-tax yield for fixed-income accounts.
 */

import {
  Alert,
  AlertDescription,
  AlertIcon,
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
import { useState } from "react";
import api from "../services/api";
import { useUserView } from "../contexts/UserViewContext";

interface YieldHolding {
  account_id: string;
  account_name: string;
  account_type: string;
  nominal_yield_pct: number;
  tax_equivalent_yield_pct: number;
  current_balance: number;
  annual_interest_income: number;
  annual_tax_cost: number;
  is_muni: boolean;
}

interface TaxEquivYieldResponse {
  assumed_federal_rate_pct: number;
  assumed_state_rate_pct: number;
  combined_marginal_rate_pct: number;
  holdings: YieldHolding[];
  portfolio_blended_nominal_yield_pct: number;
  portfolio_blended_tax_equiv_yield_pct: number;
  total_fixed_income_value: number;
  total_annual_interest: number;
  total_annual_tax_cost: number;
}

const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  cd: "CD",
  bond: "Bond",
  i_bond: "I-Bond",
  savings: "Savings",
  money_market: "Money Market",
};

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

export const TaxEquivYieldTab = () => {
  const { selectedUserId } = useUserView();
  const [federalRate, setFederalRate] = useState<number | undefined>(undefined);
  const [stateRate, setStateRate] = useState(5);

  const params = new URLSearchParams({ state_rate_pct: String(stateRate) });
  if (federalRate !== undefined) params.set("federal_rate_pct", String(federalRate));
  if (selectedUserId) params.set("user_id", selectedUserId);

  const { data, isLoading, error } = useQuery<TaxEquivYieldResponse>({
    queryKey: ["tax-equiv-yield", federalRate, stateRate, selectedUserId],
    queryFn: () => api.get(`/holdings/tax-equivalent-yield?${params}`).then((r) => r.data),
  });

  return (
    <VStack spacing={6} align="stretch">
      <Text fontSize="sm" color="text.secondary">
        Tax-equivalent yield shows what a taxable investment would need to earn to match the
        after-tax return of a given holding at your marginal tax rate.
      </Text>

      {/* Rate controls */}
      <Card>
        <CardBody>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
            <FormControl>
              <FormLabel fontSize="sm">
                Federal Marginal Rate (%)
                <Text as="span" color="text.secondary" fontSize="xs" ml={1}>— leave blank to use default</Text>
              </FormLabel>
              <NumberInput
                value={federalRate ?? ""}
                min={0}
                max={50}
                step={1}
                onChange={(_, v) => setFederalRate(isNaN(v) ? undefined : v)}
                size="sm"
              >
                <NumberInputField placeholder={`Default: ${data?.assumed_federal_rate_pct ?? 22}%`} />
              </NumberInput>
            </FormControl>
            <FormControl>
              <FormLabel fontSize="sm">State Rate (%)</FormLabel>
              <NumberInput
                value={stateRate}
                min={0}
                max={20}
                step={0.5}
                onChange={(_, v) => !isNaN(v) && setStateRate(v)}
                size="sm"
              >
                <NumberInputField />
              </NumberInput>
            </FormControl>
          </SimpleGrid>
          {data && (
            <Text fontSize="xs" color="text.secondary" mt={2}>
              Combined marginal rate: {data.combined_marginal_rate_pct.toFixed(1)}%
            </Text>
          )}
        </CardBody>
      </Card>

      {isLoading && <Text color="text.secondary">Loading yield data…</Text>}
      {error && (
        <Alert status="error">
          <AlertIcon />
          Failed to load yield data.
        </Alert>
      )}

      {data && data.holdings.length === 0 && (
        <Alert status="info">
          <AlertIcon />
          <AlertDescription fontSize="sm">
            No fixed-income accounts (CDs, bonds, money market, savings) found with an interest
            rate set. Add an interest rate to your accounts to see yield analysis.
          </AlertDescription>
        </Alert>
      )}

      {data && data.holdings.length > 0 && (
        <>
          {/* Summary */}
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
            <Stat>
              <StatLabel fontSize="xs">Total Fixed Income</StatLabel>
              <StatNumber fontSize="lg">{fmtCompact(data.total_fixed_income_value)}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel fontSize="xs">Blended Nominal Yield</StatLabel>
              <StatNumber fontSize="lg">{data.portfolio_blended_nominal_yield_pct.toFixed(2)}%</StatNumber>
            </Stat>
            <Stat>
              <StatLabel fontSize="xs">Tax-Equivalent Yield</StatLabel>
              <StatNumber fontSize="lg" color="green.500">
                {data.portfolio_blended_tax_equiv_yield_pct.toFixed(2)}%
              </StatNumber>
              <StatHelpText fontSize="xs">After-tax adjusted</StatHelpText>
            </Stat>
            <Stat>
              <StatLabel fontSize="xs">Annual Tax Cost</StatLabel>
              <StatNumber fontSize="lg" color="red.500">{fmt(data.total_annual_tax_cost)}</StatNumber>
              <StatHelpText fontSize="xs">of {fmt(data.total_annual_interest)} interest</StatHelpText>
            </Stat>
          </SimpleGrid>

          {/* Holdings table */}
          <Box overflowX="auto">
            <Table size="sm" variant="simple">
              <Thead>
                <Tr>
                  <Th>Account</Th>
                  <Th>Type</Th>
                  <Th isNumeric>Balance</Th>
                  <Th isNumeric>Nominal Yield</Th>
                  <Th isNumeric>
                    <Tooltip label="What a taxable investment would need to earn to match this holding after taxes.">
                      Tax-Equiv Yield
                    </Tooltip>
                  </Th>
                  <Th isNumeric>Annual Interest</Th>
                  <Th isNumeric>Annual Tax Cost</Th>
                </Tr>
              </Thead>
              <Tbody>
                {data.holdings.map((h) => (
                  <Tr key={h.account_id}>
                    <Td>{h.account_name}</Td>
                    <Td>{ACCOUNT_TYPE_LABELS[h.account_type] ?? h.account_type}</Td>
                    <Td isNumeric>{fmt(h.current_balance)}</Td>
                    <Td isNumeric>{h.nominal_yield_pct.toFixed(2)}%</Td>
                    <Td isNumeric fontWeight="bold" color="green.500">
                      {h.tax_equivalent_yield_pct.toFixed(2)}%
                    </Td>
                    <Td isNumeric>{fmt(h.annual_interest_income)}</Td>
                    <Td isNumeric color="red.400">{fmt(h.annual_tax_cost)}</Td>
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
