/**
 * Asset Location tab — shows asset placement optimization across account tax treatments.
 */

import {
  Alert,
  AlertDescription,
  AlertIcon,
  Badge,
  Box,
  Button,
  CircularProgress,
  CircularProgressLabel,
  Collapse,
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
  Tooltip,
  Tr,
  VStack,
} from "@chakra-ui/react";
import { useState } from "react";
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
  const { selectedUserId, effectiveUserId } = useUserView();
  const { formatCurrency } = useCurrency();
  const [showExplanation, setShowExplanation] = useState(false);

  const params = new URLSearchParams();
  if (effectiveUserId) params.set("user_id", effectiveUserId);

  const { data, isLoading, error } = useQuery<AssetLocationResponse>({
    queryKey: ["asset-location", effectiveUserId],
    queryFn: () =>
      api.get(`/holdings/asset-location?${params}`).then((r) => r.data),
  });

  return (
    <VStack spacing={6} align="stretch">
      {/* Expandable explanation */}
      <Box>
        <Button
          variant="link"
          size="sm"
          onClick={() => setShowExplanation((v) => !v)}
          color="blue.500"
          fontWeight="medium"
          mb={2}
        >
          {showExplanation ? "Why asset location matters ▲" : "Why asset location matters ▼"}
        </Button>
        <Collapse in={showExplanation} animateOpacity>
          <Box
            bg="blue.50"
            _dark={{ bg: "blue.900" }}
            borderRadius="md"
            px={4}
            py={3}
            fontSize="sm"
            color="text.primary"
          >
            Asset location is placing each investment in the most tax-efficient account. Tax-inefficient assets (bonds, REITs, high-dividend stocks) belong in pre-tax or Roth accounts where gains aren't taxed annually. Tax-efficient assets (index funds, growth stocks) are fine in taxable accounts since they generate little taxable income. Optimizing location can save thousands per year in taxes without changing your allocation.
          </Box>
        </Collapse>
      </Box>

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
                    <Th>
                      <Tooltip
                        label="The account type where this asset currently sits (taxable brokerage, pre-tax IRA/401k, Roth, etc.)"
                        hasArrow
                        placement="top"
                      >
                        <Box as="span" cursor="help" textDecoration="underline dotted">
                          Current Location
                        </Box>
                      </Tooltip>
                    </Th>
                    <Th>
                      <Tooltip
                        label="The most tax-efficient account type for this asset class"
                        hasArrow
                        placement="top"
                      >
                        <Box as="span" cursor="help" textDecoration="underline dotted">
                          Recommended
                        </Box>
                      </Tooltip>
                    </Th>
                    <Th>
                      <Tooltip
                        label="Whether this asset is in its optimal account for tax efficiency"
                        hasArrow
                        placement="top"
                      >
                        <Box as="span" cursor="help" textDecoration="underline dotted">
                          Status
                        </Box>
                      </Tooltip>
                    </Th>
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
                        <Tooltip label={item.reason} hasArrow placement="top" maxW="280px">
                          {item.is_optimal ? (
                            <Badge colorScheme="green" cursor="help">✓ Optimal</Badge>
                          ) : (
                            <Badge colorScheme="orange" cursor="help">Suboptimal</Badge>
                          )}
                        </Tooltip>
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
