/**
 * Debt Cost Widget — true monthly interest cost across all debt accounts.
 *
 * Shows: total monthly interest, total annual interest, weighted avg rate,
 * and a per-account breakdown (top 5).
 */

import {
  Badge,
  Box,
  Card,
  CardBody,
  Divider,
  Heading,
  HStack,
  Link,
  Spinner,
  Stat,
  StatHelpText,
  StatLabel,
  StatNumber,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { memo } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useUserView } from "../../../contexts/UserViewContext";
import api from "../../../services/api";

interface DebtAccountCost {
  account_id: string;
  account_name: string;
  account_type: string;
  balance: number;
  interest_rate: number | null;
  monthly_interest_cost: number;
  annual_interest_cost: number;
  minimum_payment: number | null;
}

interface DebtCostData {
  total_debt: number;
  total_monthly_interest: number;
  total_annual_interest: number;
  accounts: DebtAccountCost[];
  weighted_avg_rate: number | null;
}

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);

const fmtPct = (r: number) => `${(r * 100).toFixed(2)}%`;

function typLabel(t: string) {
  return t.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

const DebtCostWidgetBase: React.FC = () => {
  const { selectedUserId } = useUserView();

  const { data, isLoading } = useQuery<DebtCostData>({
    queryKey: ["debt-cost-widget", selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const res = await api.get("/financial-planning/debt-cost", { params });
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <Card h="100%">
        <CardBody display="flex" alignItems="center" justifyContent="center">
          <Spinner />
        </CardBody>
      </Card>
    );
  }

  if (!data || data.total_debt === 0) return null;

  const topAccounts = data.accounts
    .filter((a) => a.monthly_interest_cost > 0)
    .slice(0, 5);

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Debt Interest Cost</Heading>
          <Link
            as={RouterLink}
            to="/debt-payoff"
            fontSize="sm"
            color="brand.500"
          >
            Payoff plan →
          </Link>
        </HStack>

        <HStack spacing={4} mb={4}>
          <Stat size="sm">
            <StatLabel>Monthly Interest</StatLabel>
            <StatNumber fontSize="xl" color="red.500">
              {fmt(data.total_monthly_interest)}
            </StatNumber>
            <StatHelpText mb={0}>
              {fmt(data.total_annual_interest)}/yr
            </StatHelpText>
          </Stat>
          {data.weighted_avg_rate != null && (
            <Stat size="sm">
              <StatLabel>Avg Rate</StatLabel>
              <StatNumber fontSize="xl">
                {fmtPct(data.weighted_avg_rate)}
              </StatNumber>
              <StatHelpText mb={0}>weighted</StatHelpText>
            </Stat>
          )}
        </HStack>

        {topAccounts.length > 0 && (
          <VStack align="stretch" spacing={0}>
            {topAccounts.map((acct, i) => (
              <Box key={acct.account_id}>
                <HStack justify="space-between" py={2} px={1}>
                  <VStack align="start" spacing={0} flex={1} minW={0}>
                    <Text fontSize="sm" fontWeight="medium" noOfLines={1}>
                      {acct.account_name}
                    </Text>
                    <HStack spacing={1}>
                      <Text fontSize="xs" color="text.muted">
                        {typLabel(acct.account_type)}
                      </Text>
                      {acct.interest_rate != null && (
                        <Badge colorScheme="orange" fontSize="2xs">
                          {fmtPct(acct.interest_rate)} APR
                        </Badge>
                      )}
                    </HStack>
                  </VStack>
                  <VStack align="end" spacing={0}>
                    <Text fontSize="sm" fontWeight="bold" color="red.500">
                      {fmt(acct.monthly_interest_cost)}/mo
                    </Text>
                    <Text fontSize="xs" color="text.muted">
                      {fmt(Math.abs(acct.balance))} balance
                    </Text>
                  </VStack>
                </HStack>
                {i < topAccounts.length - 1 && <Divider />}
              </Box>
            ))}
          </VStack>
        )}
      </CardBody>
    </Card>
  );
};

export const DebtCostWidget = memo(DebtCostWidgetBase);
