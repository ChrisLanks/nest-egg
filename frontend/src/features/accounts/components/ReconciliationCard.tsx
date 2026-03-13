/**
 * Balance reconciliation card showing bank vs computed balance
 */

import {
  Box,
  Heading,
  HStack,
  SimpleGrid,
  Spinner,
  Stat,
  StatLabel,
  StatNumber,
  Text,
  Badge,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import api from "../../../services/api";

interface ReconciliationData {
  account_id: string;
  account_name: string;
  bank_balance: number;
  computed_balance: number;
  discrepancy: number;
  last_synced_at: string | null;
  transaction_count: number;
}

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);

interface ReconciliationCardProps {
  accountId: string;
}

export const ReconciliationCard = ({ accountId }: ReconciliationCardProps) => {
  const { data, isLoading, isError } = useQuery<ReconciliationData>({
    queryKey: ["reconciliation", accountId],
    queryFn: async () => {
      const response = await api.get(`/accounts/${accountId}/reconciliation`);
      return response.data;
    },
  });

  if (isLoading) {
    return (
      <Box bg="bg.surface" p={6} borderRadius="lg" boxShadow="sm">
        <Spinner size="sm" />
      </Box>
    );
  }

  if (isError || !data) return null;

  const isReconciled = Math.abs(data.discrepancy) < 0.01;
  const isMinor = Math.abs(data.discrepancy) < 1;

  return (
    <Box bg="bg.surface" p={6} borderRadius="lg" boxShadow="sm">
      <HStack justify="space-between" mb={4}>
        <Heading size="md">Balance Reconciliation</Heading>
        <Badge
          colorScheme={isReconciled ? "green" : isMinor ? "yellow" : "red"}
          fontSize="xs"
          px={2}
          py={1}
        >
          {isReconciled
            ? "Reconciled"
            : isMinor
              ? "Minor Discrepancy"
              : "Discrepancy Found"}
        </Badge>
      </HStack>

      <SimpleGrid columns={3} spacing={4}>
        <Stat size="sm">
          <StatLabel>Bank Balance</StatLabel>
          <StatNumber fontSize="md">
            {formatCurrency(data.bank_balance)}
          </StatNumber>
        </Stat>
        <Stat size="sm">
          <StatLabel>Computed Balance</StatLabel>
          <StatNumber fontSize="md">
            {formatCurrency(data.computed_balance)}
          </StatNumber>
        </Stat>
        <Stat size="sm">
          <StatLabel>Discrepancy</StatLabel>
          <StatNumber
            fontSize="md"
            color={isReconciled ? "finance.positive" : "finance.negative"}
          >
            {formatCurrency(data.discrepancy)}
          </StatNumber>
        </Stat>
      </SimpleGrid>

      <HStack mt={3} spacing={4}>
        <Text fontSize="xs" color="text.muted">
          {data.transaction_count} transactions
        </Text>
        {data.last_synced_at && (
          <Text fontSize="xs" color="text.muted">
            Last synced: {new Date(data.last_synced_at).toLocaleString()}
          </Text>
        )}
      </HStack>
    </Box>
  );
};
