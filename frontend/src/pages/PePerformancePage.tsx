/**
 * PE Performance page — shows TVPI, DPI, RVPI, IRR for each PE account
 * with capital calls and distributions.
 */

import {
  Box,
  Heading,
  Spinner,
  Center,
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
import { useUserView } from "../contexts/UserViewContext";

interface PeAccount {
  account_id: string;
  name: string;
  tvpi: number;
  dpi: number;
  moic: number;
  irr: number | null;
  irr_pct: number | null;
  total_called: number;
  total_distributions: number;
  current_nav: number;
  net_profit: number;
}

const fmt = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });


export default function PePerformancePage() {
  const { selectedUserId, effectiveUserId } = useUserView();
  const { data, isLoading, error } = useQuery<PeAccount[]>({
    queryKey: ["pe-performance", effectiveUserId],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (selectedUserId) params.user_id = effectiveUserId;
      const res = await api.get("/pe-performance/portfolio", { params });
      return res.data.accounts ?? [];
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
            {acct.name}
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
              <StatLabel>MOIC</StatLabel>
              <StatNumber>{acct.moic.toFixed(2)}x</StatNumber>
              <StatHelpText>Multiple on Invested Capital</StatHelpText>
            </Stat>
            <Stat>
              <StatLabel>IRR</StatLabel>
              <StatNumber>{acct.irr_pct !== null ? `${acct.irr_pct.toFixed(1)}%` : "N/A"}</StatNumber>
              <StatHelpText>Internal Rate of Return</StatHelpText>
            </Stat>
          </SimpleGrid>

          <SimpleGrid columns={3} spacing={4} mb={4}>
            <Stat size="sm">
              <StatLabel>Total Called</StatLabel>
              <StatNumber fontSize="md">{fmt(acct.total_called)}</StatNumber>
            </Stat>
            <Stat size="sm">
              <StatLabel>Total Distributions</StatLabel>
              <StatNumber fontSize="md">{fmt(acct.total_distributions)}</StatNumber>
            </Stat>
            <Stat size="sm">
              <StatLabel>Current NAV</StatLabel>
              <StatNumber fontSize="md">{fmt(acct.current_nav)}</StatNumber>
            </Stat>
          </SimpleGrid>
        </Box>
      ))}
    </Box>
  );
}
