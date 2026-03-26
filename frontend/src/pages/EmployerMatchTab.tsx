/**
 * Employer Match tab — shows whether household members are capturing their full 401k/403b match.
 */

import {
  Alert,
  AlertDescription,
  AlertIcon,
  Badge,
  Box,
  Card,
  CardBody,
  CardHeader,
  Heading,
  HStack,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  Text,
  Tooltip,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import api from "../services/api";
import { useCurrency } from "../contexts/CurrencyContext";

interface EmployerMatchItem {
  account_id: string;
  account_name: string;
  account_type: string;
  user_name: string;
  employer_match_percent?: number;
  employer_match_limit_percent?: number;
  annual_salary?: number;
  annual_match_value?: number;
  required_employee_pct?: number;
  is_capturing_full_match?: boolean;
  estimated_left_on_table?: number;
  action: string;
}

interface EmployerMatchResponse {
  accounts: EmployerMatchItem[];
  total_potential_match: number;
  total_captured_match: number;
  total_left_on_table: number;
  fully_optimized: boolean;
  summary: string;
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

const matchStatusBadge = (isCapturing: boolean | undefined) => {
  if (isCapturing === true) return <Badge colorScheme="green">Full Match ✓</Badge>;
  if (isCapturing === false) return <Badge colorScheme="red">Match Gap</Badge>;
  return <Badge colorScheme="gray">Unknown</Badge>;
};

const matchAlertStatus = (isCapturing: boolean | undefined): "success" | "warning" | "info" => {
  if (isCapturing === true) return "success";
  if (isCapturing === false) return "warning";
  return "info";
};

export const EmployerMatchTab = () => {
  const { formatCurrency } = useCurrency();

  const { data, isLoading, error } = useQuery<EmployerMatchResponse>({
    queryKey: ["employer-match"],
    queryFn: () => api.get("/retirement/employer-match").then((r) => r.data),
  });

  return (
    <VStack spacing={6} align="stretch">
      {isLoading && <Text color="text.secondary">Loading employer match data…</Text>}
      {error && (
        <Alert status="error">
          <AlertIcon />
          Failed to load employer match data.
        </Alert>
      )}

      {data && data.accounts.length === 0 && (
        <Alert status="info">
          <AlertIcon />
          <AlertDescription fontSize="sm">
            No employer-matched accounts found. Add a 401(k) or 403(b) account with match details to use this tool.
          </AlertDescription>
        </Alert>
      )}

      {data && data.accounts.length > 0 && (
        <>
          {/* Summary banner */}
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
            <Stat>
              <Tooltip
                label="The maximum employer contribution if all employees contribute enough to get the full match"
                hasArrow
                placement="top"
              >
                <StatLabel fontSize="xs" cursor="help" textDecoration="underline dotted" display="inline-block">
                  Total Potential Match
                </StatLabel>
              </Tooltip>
              <StatNumber fontSize="lg">{fmtCompact(data.total_potential_match)}</StatNumber>
            </Stat>
            <Stat>
              <Tooltip
                label="Estimated employer contribution being received based on current contribution records"
                hasArrow
                placement="top"
              >
                <StatLabel fontSize="xs" cursor="help" textDecoration="underline dotted" display="inline-block">
                  Captured Match
                </StatLabel>
              </Tooltip>
              <StatNumber fontSize="lg" color="green.500">{fmtCompact(data.total_captured_match)}</StatNumber>
            </Stat>
            <Stat>
              <Tooltip
                label="Employer match being forfeited each year by not contributing enough"
                hasArrow
                placement="top"
              >
                <StatLabel fontSize="xs" cursor="help" textDecoration="underline dotted" display="inline-block">
                  Left on Table
                </StatLabel>
              </Tooltip>
              <StatNumber fontSize="lg" color={data.total_left_on_table > 0 ? "red.500" : "green.500"}>
                {fmtCompact(data.total_left_on_table)}
              </StatNumber>
            </Stat>
            <Stat>
              <Tooltip
                label="Whether all employer-matched accounts are capturing the full match"
                hasArrow
                placement="top"
              >
                <StatLabel fontSize="xs" cursor="help" textDecoration="underline dotted" display="inline-block">
                  Status
                </StatLabel>
              </Tooltip>
              <StatNumber fontSize="lg">
                <Badge colorScheme={data.fully_optimized ? "green" : "red"} fontSize="sm">
                  {data.fully_optimized ? "Fully Optimized" : "Needs Attention"}
                </Badge>
              </StatNumber>
            </Stat>
          </SimpleGrid>

          {/* Account cards */}
          {data.accounts.map((account) => (
            <Card key={account.account_id}>
              <CardHeader py={3} px={4}>
                <HStack justify="space-between" flexWrap="wrap" gap={2}>
                  <VStack align="flex-start" spacing={0}>
                    <Heading size="sm">{account.account_name}</Heading>
                    <Text fontSize="xs" color="text.secondary">{account.user_name}</Text>
                  </VStack>
                  <HStack spacing={2}>
                    <Badge colorScheme="blue" fontSize="xs">{account.account_type.toUpperCase()}</Badge>
                    {matchStatusBadge(account.is_capturing_full_match)}
                  </HStack>
                </HStack>
              </CardHeader>
              <CardBody pt={0} px={4} pb={4}>
                <VStack align="stretch" spacing={3}>
                  <SimpleGrid columns={{ base: 2, md: 4 }} spacing={3}>
                    {account.employer_match_percent != null && (
                      <Stat size="sm">
                        <Tooltip
                          label="The % of your contribution the employer matches (e.g. 50% match means they add $0.50 per $1 you contribute)"
                          hasArrow
                          placement="top"
                        >
                          <StatLabel fontSize="xs" cursor="help" textDecoration="underline dotted" display="inline-block">
                            Employer Match
                          </StatLabel>
                        </Tooltip>
                        <StatNumber fontSize="md">{account.employer_match_percent}%</StatNumber>
                      </Stat>
                    )}
                    {account.employer_match_limit_percent != null && (
                      <Stat size="sm">
                        <Tooltip
                          label="The maximum % of salary eligible for matching (e.g. 6% means match stops once you've contributed 6% of salary)"
                          hasArrow
                          placement="top"
                        >
                          <StatLabel fontSize="xs" cursor="help" textDecoration="underline dotted" display="inline-block">
                            Up To
                          </StatLabel>
                        </Tooltip>
                        <StatNumber fontSize="md">{account.employer_match_limit_percent}% of salary</StatNumber>
                      </Stat>
                    )}
                    {account.annual_match_value != null && (
                      <Stat size="sm">
                        <Tooltip
                          label="Maximum annual employer contribution if you contribute the required minimum percentage"
                          hasArrow
                          placement="top"
                        >
                          <StatLabel fontSize="xs" cursor="help" textDecoration="underline dotted" display="inline-block">
                            Annual Match Value
                          </StatLabel>
                        </Tooltip>
                        <StatNumber fontSize="md">{fmt(account.annual_match_value)}</StatNumber>
                      </Stat>
                    )}
                    {account.estimated_left_on_table != null && account.estimated_left_on_table > 0 && (
                      <Stat size="sm">
                        <Tooltip
                          label="Estimated annual employer match being forfeited"
                          hasArrow
                          placement="top"
                        >
                          <StatLabel fontSize="xs" cursor="help" textDecoration="underline dotted" display="inline-block">
                            Left on Table
                          </StatLabel>
                        </Tooltip>
                        <StatNumber fontSize="md" color="red.500">
                          {fmt(account.estimated_left_on_table)}
                        </StatNumber>
                      </Stat>
                    )}
                  </SimpleGrid>

                  <Alert status={matchAlertStatus(account.is_capturing_full_match)}>
                    <AlertIcon />
                    <AlertDescription fontSize="sm">{account.action}</AlertDescription>
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
