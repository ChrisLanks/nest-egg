/**
 * Net Worth Percentile tab — compares user net worth to age-based SCF benchmarks.
 */

import {
  Alert,
  AlertDescription,
  AlertIcon,
  Badge,
  Box,
  Card,
  CardBody,
  CircularProgress,
  CircularProgressLabel,
  FormControl,
  FormHelperText,
  FormLabel,
  HStack,
  NumberInput,
  NumberInputField,
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
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import api from "../services/api";
import { useCurrency } from "../contexts/CurrencyContext";
import { useUserView } from "../contexts/UserViewContext";

interface PercentileBenchmark {
  label: string;
  value: number;
  is_above: boolean;
}

interface NetWorthPercentileResponse {
  current_net_worth: number;
  age?: number;
  age_bucket: string;
  estimated_percentile: number;
  percentile_label: string;
  benchmarks: PercentileBenchmark[];
  fidelity_target_multiplier: number;
  fidelity_target_amount?: number;
  median_for_age: number;
  data_source: string;
  encouragement: string;
}

const percentileColor = (pct: number): string => {
  if (pct >= 75) return "green";
  if (pct >= 50) return "teal";
  if (pct >= 25) return "yellow";
  return "orange";
};

const encouragementStatus = (pct: number): "success" | "info" | "warning" => {
  if (pct >= 75) return "success";
  if (pct >= 25) return "info";
  return "warning";
};

const fmt = (v: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(v);

const fmtCompact = (v: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(v);

export const NetWorthPercentileTab = () => {
  const { formatCurrency , currency } = useCurrency();
  const { selectedUserId, effectiveUserId } = useUserView();
  const [ageOverride, setAgeOverride] = useState<number | undefined>(undefined);

  const params = new URLSearchParams();
  if (ageOverride !== undefined) params.set("age", String(ageOverride));
  if (effectiveUserId) params.set("user_id", effectiveUserId);

  const { data, isLoading, error } = useQuery<NetWorthPercentileResponse>({
    queryKey: ["net-worth-percentile", ageOverride, effectiveUserId],
    queryFn: () =>
      api.get(`/dashboard/net-worth-percentile?${params}`).then((r) => r.data),
  });

  return (
    <VStack spacing={6} align="stretch">
      {/* Age override */}
      <Card>
        <CardBody>
          <FormControl maxW="250px">
            <FormLabel fontSize="sm">
              Age Override
              <Text as="span" color="text.secondary" fontSize="xs" ml={1}>— optional</Text>
            </FormLabel>
            <NumberInput
              value={ageOverride ?? ""}
              min={18}
              max={100}
              onChange={(_, v) => setAgeOverride(isNaN(v) ? undefined : v)}
              size="sm"
            >
              <NumberInputField placeholder="Uses profile age if blank" />
            </NumberInput>
            <FormHelperText fontSize="xs">
              For multi-member households, enter the primary account holder's age or
              leave blank to use your profile age.
            </FormHelperText>
          </FormControl>
        </CardBody>
      </Card>

      {isLoading && <Text color="text.secondary">Loading percentile data…</Text>}
      {error && (
        <Alert status="error">
          <AlertIcon />
          Failed to load percentile data.
        </Alert>
      )}

      {data && (
        <>
          {/* Percentile display */}
          <HStack spacing={8} align="center" flexWrap="wrap">
            <CircularProgress
              value={data.estimated_percentile}
              color={`${percentileColor(data.estimated_percentile)}.400`}
              trackColor="gray.100"
              size="120px"
              thickness="10px"
            >
              <CircularProgressLabel fontWeight="bold" fontSize="xl">
                {data.estimated_percentile}
                <Text as="span" fontSize="sm">th</Text>
              </CircularProgressLabel>
            </CircularProgress>
            <VStack align="flex-start" spacing={1}>
              <Text fontSize="xl" fontWeight="bold">{data.percentile_label}</Text>
              <Badge colorScheme="blue" fontSize="sm">{data.age_bucket}</Badge>
              <Text fontSize="sm" color="text.secondary">Your peer group: {data.age_bucket}</Text>
            </VStack>
          </HStack>

          {/* Encouragement */}
          <Alert status={encouragementStatus(data.estimated_percentile)}>
            <AlertIcon />
            <AlertDescription fontSize="sm">{data.encouragement}</AlertDescription>
          </Alert>

          {/* Current net worth stat */}
          <SimpleGrid columns={{ base: 2, md: 3 }} spacing={4}>
            <Stat>
              <StatLabel fontSize="xs">Your Net Worth</StatLabel>
              <StatNumber fontSize="lg">{fmtCompact(data.current_net_worth)}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel fontSize="xs">Median for Age Group</StatLabel>
              <StatNumber fontSize="lg">{fmtCompact(data.median_for_age)}</StatNumber>
            </Stat>
            {data.fidelity_target_amount != null && (
              <Stat>
                <StatLabel fontSize="xs">
                  Fidelity Target ({data.fidelity_target_multiplier}× salary)
                </StatLabel>
                <StatNumber fontSize="lg">{fmtCompact(data.fidelity_target_amount)}</StatNumber>
              </Stat>
            )}
          </SimpleGrid>

          {/* Benchmark table */}
          <Box overflowX="auto">
            <Table size="sm" variant="simple">
              <Thead>
                <Tr>
                  <Th>Benchmark</Th>
                  <Th isNumeric>Amount</Th>
                  <Th>Your Status</Th>
                </Tr>
              </Thead>
              <Tbody>
                {data.benchmarks.map((b) => (
                  <Tr key={b.label}>
                    <Td fontWeight="medium">{b.label}</Td>
                    <Td isNumeric>{fmt(b.value)}</Td>
                    <Td>
                      {b.is_above ? (
                        <Badge colorScheme="green">✓ Above</Badge>
                      ) : (
                        <Badge colorScheme="red">✗ Below</Badge>
                      )}
                    </Td>
                  </Tr>
                ))}
                <Tr bg="blue.50" _dark={{ bg: "blue.900" }}>
                  <Td fontWeight="bold">Your Net Worth</Td>
                  <Td isNumeric fontWeight="bold">{fmt(data.current_net_worth)}</Td>
                  <Td>
                    <Badge colorScheme="blue">You</Badge>
                  </Td>
                </Tr>
              </Tbody>
            </Table>
          </Box>

          {/* Fidelity target note */}
          <Text fontSize="sm" color="text.secondary">
            Fidelity suggests <strong>{data.fidelity_target_multiplier}×</strong> your salary saved by this age group.
            {data.fidelity_target_amount != null && (
              <> Based on your salary, target: <strong>{fmt(data.fidelity_target_amount)}</strong>.</>
            )}
          </Text>

          {/* Data source footnote */}
          <Text fontSize="xs" color="text.secondary" fontStyle="italic">
            Source: {data.data_source}
          </Text>
        </>
      )}
    </VStack>
  );
};
