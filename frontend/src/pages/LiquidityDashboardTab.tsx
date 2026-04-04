/**
 * Liquidity Dashboard tab — emergency fund coverage analysis with account breakdown.
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
  HStack,
  NumberInput,
  NumberInputField,
  Progress,
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
import { useCurrency } from "../contexts/CurrencyContext";
import { useUserView } from "../contexts/UserViewContext";
import * as AccountTypeGroups from "../constants/accountTypeGroups";
const ACCOUNT_TYPE_LABELS: Record<string, string> = AccountTypeGroups.ACCOUNT_TYPE_LABELS ?? {};

interface LiquidAccount {
  account_id: string;
  account_name: string;
  account_type: string;
  balance: number;
  institution?: string;
  is_accessible: boolean;
}

interface LiquidityDashboardResponse {
  liquid_accounts: LiquidAccount[];
  immediately_accessible: number;
  total_liquid: number;
  monthly_spending_used: number;
  emergency_months_immediate: number;
  emergency_months_total: number;
  target_months: number;
  coverage_gap: number;
  grade: string;
  grade_color: string;
  recommendations: string[];
  spending_is_estimated: boolean;
}

const gradeColorScheme = (grade: string): string => {
  switch (grade) {
    case "A": return "green";
    case "B": return "teal";
    case "C": return "yellow";
    case "D": return "orange";
    case "F": return "red";
    default: return "gray";
  }
};

const monthsColor = (months: number): string => {
  if (months >= 6) return "green.500";
  if (months >= 3) return "teal.500";
  if (months >= 1) return "yellow.500";
  if (months > 0) return "orange.400";
  return "red.500";
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

export const LiquidityDashboardTab = () => {
  const { formatCurrency } = useCurrency();
  const { selectedUserId } = useUserView();
  const [monthlySpending, setMonthlySpending] = useState<number | undefined>(undefined);

  const params = new URLSearchParams();
  if (monthlySpending !== undefined) params.set("monthly_spending", String(monthlySpending));
  if (selectedUserId) params.set("user_id", selectedUserId);

  const { data, isLoading, error } = useQuery<LiquidityDashboardResponse>({
    queryKey: ["liquidity-dashboard", monthlySpending, selectedUserId],
    queryFn: () =>
      api.get(`/dashboard/liquidity?${params}`).then((r) => r.data),
  });

  const progressPct = data
    ? Math.min(100, (data.emergency_months_immediate / data.target_months) * 100)
    : 0;

  return (
    <VStack spacing={6} align="stretch">
      {/* Spending input */}
      <Card>
        <CardBody>
          <FormControl maxW="300px">
            <FormLabel fontSize="sm">
              <Tooltip label="Your average monthly essential spending. Used to calculate how many months your liquid assets would cover. Leave blank to auto-estimate from your transaction history." hasArrow placement="top">
                <Text as="span">Monthly Spending ($)</Text>
              </Tooltip>
              <Text as="span" color="text.secondary" fontSize="xs" ml={1}>— optional override</Text>
            </FormLabel>
            <NumberInput
              value={monthlySpending ?? ""}
              min={0}
              onChange={(_, v) => setMonthlySpending(isNaN(v) ? undefined : v)}
              size="sm"
            >
              <NumberInputField placeholder="Auto-estimated if blank" />
            </NumberInput>
          </FormControl>
          {data?.spending_is_estimated && (
            <Alert status="info" mt={3} size="sm">
              <AlertIcon />
              <AlertDescription fontSize="xs">
                Monthly spending is estimated from your account data.
              </AlertDescription>
            </Alert>
          )}
        </CardBody>
      </Card>

      {isLoading && <Text color="text.secondary">Loading liquidity data…</Text>}
      {error && (
        <Alert status="error">
          <AlertIcon />
          Failed to load liquidity data.
        </Alert>
      )}

      {data && (
        <>
          {/* Emergency fund coverage */}
          <Box>
            <HStack spacing={6} align="center" mb={3}>
              <VStack align="flex-start" spacing={0}>
                <Text fontSize="xs" color="text.secondary">Emergency Fund Coverage</Text>
                <Text
                  fontSize="4xl"
                  fontWeight="bold"
                  color={monthsColor(data.emergency_months_immediate)}
                >
                  {data.emergency_months_immediate.toFixed(1)}
                </Text>
                <Text fontSize="sm" color="text.secondary">months (immediate access)</Text>
              </VStack>
              <Badge
                colorScheme={gradeColorScheme(data.grade)}
                fontSize="2xl"
                px={4}
                py={2}
                borderRadius="lg"
              >
                {data.grade}
              </Badge>
            </HStack>

            <HStack justify="space-between" mb={1}>
              <Text fontSize="xs" color="text.secondary">Current</Text>
              <Text fontSize="xs" color="text.secondary">Target: {data.target_months} months</Text>
            </HStack>
            <Progress
              value={progressPct}
              colorScheme={gradeColorScheme(data.grade)}
              size="lg"
              borderRadius="full"
            />
          </Box>

          {/* Key stats */}
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
            <Stat>
              <Tooltip label="Cash in checking, savings, and money market accounts you can access within 1–2 business days without penalties." hasArrow placement="top">
                <StatLabel fontSize="xs" cursor="default">Immediately Accessible</StatLabel>
              </Tooltip>
              <StatNumber fontSize="lg" color="green.500">{fmtCompact(data.immediately_accessible)}</StatNumber>
            </Stat>
            <Stat>
              <Tooltip label="All liquid assets including brokerage accounts and short-term investments that could be converted to cash within ~1 week." hasArrow placement="top">
                <StatLabel fontSize="xs" cursor="default">Total Liquid</StatLabel>
              </Tooltip>
              <StatNumber fontSize="lg">{fmtCompact(data.total_liquid)}</StatNumber>
            </Stat>
            <Stat>
              <Tooltip label="The monthly spending figure used to calculate months of coverage. Based on your input or auto-estimated from transaction history." hasArrow placement="top">
                <StatLabel fontSize="xs" cursor="default">Monthly Spending Used</StatLabel>
              </Tooltip>
              <StatNumber fontSize="lg">{fmt(data.monthly_spending_used)}</StatNumber>
              {data.spending_is_estimated && (
                <StatHelpText fontSize="xs">Estimated</StatHelpText>
              )}
            </Stat>
            <Stat>
              <Tooltip label={data.coverage_gap > 0 ? `Amount needed to reach your ${data.target_months}-month emergency fund target.` : `Amount above your ${data.target_months}-month emergency fund target.`} hasArrow placement="top">
                <StatLabel fontSize="xs" cursor="default">
                  {data.coverage_gap > 0 ? "Coverage Gap" : "Surplus"}
                </StatLabel>
              </Tooltip>
              <StatNumber fontSize="lg" color={data.coverage_gap > 0 ? "red.500" : "green.500"}>
                {fmtCompact(Math.abs(data.coverage_gap))}
              </StatNumber>
            </Stat>
          </SimpleGrid>

          {/* Liquid accounts table */}
          {data.liquid_accounts.length > 0 && (
            <Box overflowX="auto">
              <Table size="sm" variant="simple">
                <Thead>
                  <Tr>
                    <Th>Account</Th>
                    <Th>Type</Th>
                    <Th isNumeric>Balance</Th>
                    <Th>Accessible</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {data.liquid_accounts.map((acct) => (
                    <Tr key={acct.account_id}>
                      <Td>{acct.account_name}</Td>
                      <Td>{ACCOUNT_TYPE_LABELS[acct.account_type] ?? acct.account_type}</Td>
                      <Td isNumeric>{fmt(acct.balance)}</Td>
                      <Td>
                        {acct.is_accessible ? (
                          <Badge colorScheme="green" fontSize="xs">Accessible</Badge>
                        ) : (
                          <Badge colorScheme="gray" fontSize="xs">Locked</Badge>
                        )}
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </Box>
          )}

          {/* Recommendations */}
          {data.recommendations.length > 0 && (
            <Box>
              <Text fontWeight="medium" fontSize="sm" mb={2}>Recommendations</Text>
              <VStack align="stretch" spacing={1}>
                {data.recommendations.map((rec, idx) => (
                  <Text key={idx} fontSize="sm">• {rec}</Text>
                ))}
              </VStack>
            </Box>
          )}
        </>
      )}
    </VStack>
  );
};
