/**
 * Pension Modeler tab — analyzes pension/annuity accounts for break-even and lifetime value.
 */

import {
  Alert,
  AlertDescription,
  AlertIcon,
  Badge,
  Card,
  CardBody,
  CardHeader,
  Heading,
  HStack,
  SimpleGrid,
  Stat,
  StatHelpText,
  StatLabel,
  StatNumber,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import api from "../services/api";
import { useCurrency } from "../contexts/CurrencyContext";
import { useUserView } from "../contexts/UserViewContext";

interface PensionAnalysis {
  account_id: string;
  account_name: string;
  account_type: string;
  monthly_benefit?: number;
  annual_benefit?: number;
  lump_sum_value?: number;
  cola_rate?: number;
  survivor_monthly?: number;
  break_even_years?: number;
  lifetime_value_20yr?: number;
  lifetime_value_25yr?: number;
  years_of_service?: number;
  recommendation: string;
  recommendation_reason: string;
}

interface PensionModelerResponse {
  pensions: PensionAnalysis[];
  total_monthly_income: number;
  total_annual_income: number;
  total_lump_sum_value: number;
  has_cola_protection: boolean;
  summary: string;
}

const breakEvenColor = (years: number): string => {
  if (years < 15) return "green.500";
  if (years > 20) return "orange.400";
  return "yellow.500";
};

const breakEvenLabel = (years: number): string => {
  if (years < 15) return "Take annuity";
  if (years > 20) return "Consider lump sum";
  return "Borderline";
};

const recommendationStatus = (rec: string): "success" | "warning" | "info" => {
  const lower = rec.toLowerCase();
  if (lower.includes("annuity") || lower.includes("take") || lower.includes("recommended")) return "success";
  if (lower.includes("lump") || lower.includes("consider")) return "warning";
  return "info";
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

export const PensionModelerTab = () => {
  const { formatCurrency } = useCurrency();
  const { selectedUserId } = useUserView();

  const { data, isLoading, error } = useQuery<PensionModelerResponse>({
    queryKey: ["pension-modeler", selectedUserId],
    queryFn: () => {
      const params: Record<string, string> = {};
      if (selectedUserId) params.user_id = selectedUserId;
      return api.get("/retirement/pension-model", { params }).then((r) => r.data);
    },
  });

  return (
    <VStack spacing={6} align="stretch">
      {isLoading && <Text color="text.secondary">Loading pension data…</Text>}
      {error && (
        <Alert status="error">
          <AlertIcon />
          Failed to load pension data.
        </Alert>
      )}

      {data && data.pensions.length === 0 && (
        <Alert status="info">
          <AlertIcon />
          <AlertDescription fontSize="sm">
            No pension or annuity accounts found. Add a PENSION or ANNUITY account to use this tool.
          </AlertDescription>
        </Alert>
      )}

      {data && data.pensions.length > 0 && (
        <>
          {/* Summary stats */}
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
            <Stat>
              <StatLabel fontSize="xs">Total Monthly Income</StatLabel>
              <StatNumber fontSize="lg">{fmt(data.total_monthly_income)}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel fontSize="xs">Total Annual Income</StatLabel>
              <StatNumber fontSize="lg">{fmtCompact(data.total_annual_income)}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel fontSize="xs">Total Lump Sum Value</StatLabel>
              <StatNumber fontSize="lg">{fmtCompact(data.total_lump_sum_value)}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel fontSize="xs">COLA Protection</StatLabel>
              <StatNumber fontSize="lg">
                <Badge colorScheme={data.has_cola_protection ? "green" : "gray"} fontSize="sm">
                  {data.has_cola_protection ? "Yes" : "No"}
                </Badge>
              </StatNumber>
            </Stat>
          </SimpleGrid>

          {/* Pension cards */}
          {data.pensions.map((pension) => (
            <Card key={pension.account_id}>
              <CardHeader py={3} px={4}>
                <HStack justify="space-between" flexWrap="wrap" gap={2}>
                  <Heading size="sm">{pension.account_name}</Heading>
                  <Badge colorScheme="blue" fontSize="xs">{pension.account_type.toUpperCase()}</Badge>
                </HStack>
              </CardHeader>
              <CardBody pt={0} px={4} pb={4}>
                <VStack align="stretch" spacing={4}>
                  <SimpleGrid columns={{ base: 2, md: 3 }} spacing={4}>
                    {pension.monthly_benefit != null && (
                      <Stat size="sm">
                        <StatLabel fontSize="xs">Monthly Benefit</StatLabel>
                        <StatNumber fontSize="md">{fmt(pension.monthly_benefit)}</StatNumber>
                      </Stat>
                    )}
                    {pension.annual_benefit != null && (
                      <Stat size="sm">
                        <StatLabel fontSize="xs">Annual Benefit</StatLabel>
                        <StatNumber fontSize="md">{fmt(pension.annual_benefit)}</StatNumber>
                      </Stat>
                    )}
                    {pension.lump_sum_value != null && (
                      <Stat size="sm">
                        <StatLabel fontSize="xs">Lump Sum Value</StatLabel>
                        <StatNumber fontSize="md">{fmtCompact(pension.lump_sum_value)}</StatNumber>
                      </Stat>
                    )}
                    {pension.break_even_years != null && (
                      <Stat size="sm">
                        <StatLabel fontSize="xs">Break-Even</StatLabel>
                        <StatNumber fontSize="md" color={breakEvenColor(pension.break_even_years)}>
                          {pension.break_even_years.toFixed(1)} yrs
                        </StatNumber>
                        <StatHelpText fontSize="xs">{breakEvenLabel(pension.break_even_years)}</StatHelpText>
                      </Stat>
                    )}
                    {pension.lifetime_value_20yr != null && (
                      <Stat size="sm">
                        <StatLabel fontSize="xs">Lifetime Value (20yr)</StatLabel>
                        <StatNumber fontSize="md">{fmtCompact(pension.lifetime_value_20yr)}</StatNumber>
                      </Stat>
                    )}
                    {pension.lifetime_value_25yr != null && (
                      <Stat size="sm">
                        <StatLabel fontSize="xs">Lifetime Value (25yr)</StatLabel>
                        <StatNumber fontSize="md">{fmtCompact(pension.lifetime_value_25yr)}</StatNumber>
                      </Stat>
                    )}
                    {pension.survivor_monthly != null && (
                      <Stat size="sm">
                        <StatLabel fontSize="xs">Survivor Monthly</StatLabel>
                        <StatNumber fontSize="md">{fmt(pension.survivor_monthly)}</StatNumber>
                      </Stat>
                    )}
                  </SimpleGrid>

                  <Alert status={recommendationStatus(pension.recommendation)}>
                    <AlertIcon />
                    <AlertDescription fontSize="sm">
                      <strong>{pension.recommendation}</strong>
                      {pension.recommendation_reason && ` — ${pension.recommendation_reason}`}
                    </AlertDescription>
                  </Alert>
                </VStack>
              </CardBody>
            </Card>
          ))}
        </>
      )}
    </VStack>
  );
};
