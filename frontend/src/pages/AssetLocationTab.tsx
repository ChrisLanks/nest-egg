/**
 * Asset Location tab — shows asset placement optimization across account tax treatments.
 */

import {
  Alert,
  AlertDescription,
  AlertIcon,
  Badge,
  Box,
  CircularProgress,
  CircularProgressLabel,
  HStack,
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
import api from "../services/api";
import { useCurrency } from "../contexts/CurrencyContext";
import { useUserView } from "../contexts/UserViewContext";

interface AssetLocationItem {
  account_id: string;
  account_name: string;
  account_type: string;
  tax_treatment: string;
  ticker?: string;
  asset_class?: string;
  name: string;
  current_value: number;
  is_optimal: boolean;
  recommended_location: string;
  reason: string;
}

interface AssetLocationResponse {
  items: AssetLocationItem[];
  total_value: number;
  optimal_count: number;
  suboptimal_count: number;
  optimization_score: number;
  summary_tip: string;
}

const locationColorScheme = (loc: string): string => {
  switch (loc) {
    case "pre_tax": return "blue";
    case "roth": return "purple";
    case "taxable": return "gray";
    case "tax_free": return "green";
    default: return "gray";
  }
};

const locationLabel = (loc: string): string => {
  switch (loc) {
    case "pre_tax": return "Pre-Tax";
    case "roth": return "Roth";
    case "taxable": return "Taxable";
    case "tax_free": return "Tax-Free";
    default: return loc;
  }
};

const scoreColor = (score: number): string => {
  if (score >= 75) return "green";
  if (score >= 50) return "yellow";
  return "red";
};

export const AssetLocationTab = () => {
  const { selectedUserId } = useUserView();
  const { formatCurrency } = useCurrency();

  const params = new URLSearchParams();
  if (selectedUserId) params.set("user_id", selectedUserId);

  const { data, isLoading, error } = useQuery<AssetLocationResponse>({
    queryKey: ["asset-location", selectedUserId],
    queryFn: () =>
      api.get(`/holdings/asset-location?${params}`).then((r) => r.data),
  });

  return (
    <VStack spacing={6} align="stretch">
      {isLoading && <Text color="text.secondary">Loading asset location data…</Text>}
      {error && (
        <Alert status="error">
          <AlertIcon />
          Failed to load asset location data.
        </Alert>
      )}

      {data && (
        <>
          {/* Score + counts */}
          <HStack spacing={8} align="center" flexWrap="wrap">
            <CircularProgress
              value={data.optimization_score}
              color={`${scoreColor(data.optimization_score)}.400`}
              size="100px"
              thickness="10px"
            >
              <CircularProgressLabel fontWeight="bold" fontSize="lg">
                {data.optimization_score}
              </CircularProgressLabel>
            </CircularProgress>
            <VStack align="flex-start" spacing={1}>
              <Text fontWeight="bold" fontSize="lg">Optimization Score</Text>
              <SimpleGrid columns={2} spacing={4}>
                <Stat size="sm">
                  <StatLabel fontSize="xs">Optimal</StatLabel>
                  <StatNumber fontSize="md" color="green.500">{data.optimal_count}</StatNumber>
                </Stat>
                <Stat size="sm">
                  <StatLabel fontSize="xs">Suboptimal</StatLabel>
                  <StatNumber fontSize="md" color="orange.400">{data.suboptimal_count}</StatNumber>
                </Stat>
              </SimpleGrid>
            </VStack>
          </HStack>

          {data.summary_tip && (
            <Alert status={data.optimization_score >= 75 ? "success" : "warning"}>
              <AlertIcon />
              <AlertDescription fontSize="sm">{data.summary_tip}</AlertDescription>
            </Alert>
          )}

          {/* Holdings table */}
          {data.items.length === 0 ? (
            <Alert status="info">
              <AlertIcon />
              No holdings found.
            </Alert>
          ) : (
            <Box overflowX="auto">
              <Table size="sm" variant="simple">
                <Thead>
                  <Tr>
                    <Th>Account</Th>
                    <Th>Asset</Th>
                    <Th>Asset Class</Th>
                    <Th>Current Location</Th>
                    <Th>Recommended</Th>
                    <Th>Status</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {data.items.map((item) => (
                    <Tr key={`${item.account_id}-${item.ticker ?? item.name}`}>
                      <Td>{item.account_name}</Td>
                      <Td>{item.ticker ?? item.name}</Td>
                      <Td>{item.asset_class ?? "—"}</Td>
                      <Td>
                        <Badge colorScheme={locationColorScheme(item.tax_treatment)}>
                          {locationLabel(item.tax_treatment)}
                        </Badge>
                      </Td>
                      <Td>
                        <Badge colorScheme={locationColorScheme(item.recommended_location)}>
                          {locationLabel(item.recommended_location)}
                        </Badge>
                      </Td>
                      <Td>
                        {item.is_optimal ? (
                          <Badge colorScheme="green">✓ Optimal</Badge>
                        ) : (
                          <Badge colorScheme="orange">Suboptimal</Badge>
                        )}
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </Box>
          )}

          <Text fontSize="sm" color="text.secondary">
            Total Portfolio Value: <strong>{formatCurrency(data.total_value)}</strong>
          </Text>
        </>
      )}
    </VStack>
  );
};
