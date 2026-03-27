/**
 * PE Performance page — shows TVPI, DPI, RVPI, IRR for each PE account
 * with capital calls and distributions.
 */

import {
  Box,
  Heading,
  Spinner,
  Center,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  SimpleGrid,
  Text,
  Alert,
  AlertIcon,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import api from "../services/api";

interface PeAccount {
  account_id: string;
  account_name: string;
  tvpi: number;
  dpi: number;
  rvpi: number;
  irr: number | null;
  total_called: number;
  total_distributed: number;
  nav: number;
  transactions: {
    date: string;
    type: string;
    amount: number;
    notes: string | null;
  }[];
}

const fmt = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

const pct = (n: number | null) =>
  n !== null ? `${(n * 100).toFixed(1)}%` : "N/A";

export default function PePerformancePage() {
  const { data, isLoading, error } = useQuery<PeAccount[]>({
    queryKey: ["pe-performance"],
    queryFn: async () => {
      const res = await api.get("/pe-performance/summary");
      return res.data.accounts ?? res.data;
    },
  });

  if (isLoading)
    return (
      <Center h="60vh">
        <Spinner size="xl" />
      </Center>
    );

  if (error)
    return (
      <Alert status="error" mt={4}>
        <AlertIcon />
        Failed to load PE performance data.
      </Alert>
    );

  const accounts = data ?? [];

  if (accounts.length === 0)
    return (
      <Box p={6}>
        <Heading size="lg" mb={4}>
          Private Equity Performance
        </Heading>
        <Text>No PE accounts found. Add a private equity account to see performance metrics.</Text>
      </Box>
    );

  return (
    <Box p={6}>
      <Heading size="lg" mb={6}>
        Private Equity Performance
      </Heading>

      {accounts.map((acct) => (
        <Box key={acct.account_id} mb={8} p={4} borderWidth="1px" borderRadius="md">
          <Heading size="md" mb={4}>
            {acct.account_name}
          </Heading>

          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4} mb={4}>
            <Stat>
              <StatLabel>TVPI</StatLabel>
              <StatNumber>{acct.tvpi.toFixed(2)}x</StatNumber>
              <StatHelpText>Total Value to Paid-In</StatHelpText>
            </Stat>
            <Stat>
              <StatLabel>DPI</StatLabel>
              <StatNumber>{acct.dpi.toFixed(2)}x</StatNumber>
              <StatHelpText>Distributed to Paid-In</StatHelpText>
            </Stat>
            <Stat>
              <StatLabel>RVPI</StatLabel>
              <StatNumber>{acct.rvpi.toFixed(2)}x</StatNumber>
              <StatHelpText>Residual Value to Paid-In</StatHelpText>
            </Stat>
            <Stat>
              <StatLabel>IRR</StatLabel>
              <StatNumber>{pct(acct.irr)}</StatNumber>
              <StatHelpText>Internal Rate of Return</StatHelpText>
            </Stat>
          </SimpleGrid>

          <SimpleGrid columns={3} spacing={4} mb={4}>
            <Stat size="sm">
              <StatLabel>Total Called</StatLabel>
              <StatNumber fontSize="md">{fmt(acct.total_called)}</StatNumber>
            </Stat>
            <Stat size="sm">
              <StatLabel>Total Distributed</StatLabel>
              <StatNumber fontSize="md">{fmt(acct.total_distributed)}</StatNumber>
            </Stat>
            <Stat size="sm">
              <StatLabel>Current NAV</StatLabel>
              <StatNumber fontSize="md">{fmt(acct.nav)}</StatNumber>
            </Stat>
          </SimpleGrid>

          {acct.transactions && acct.transactions.length > 0 && (
            <Table size="sm" variant="simple">
              <Thead>
                <Tr>
                  <Th>Date</Th>
                  <Th>Type</Th>
                  <Th isNumeric>Amount</Th>
                  <Th>Notes</Th>
                </Tr>
              </Thead>
              <Tbody>
                {acct.transactions.map((tx, i) => (
                  <Tr key={i}>
                    <Td>{tx.date}</Td>
                    <Td>{tx.type}</Td>
                    <Td isNumeric>{fmt(tx.amount)}</Td>
                    <Td>{tx.notes || ""}</Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          )}
        </Box>
      ))}
    </Box>
  );
}
