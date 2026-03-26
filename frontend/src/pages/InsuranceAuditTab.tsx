/**
 * Insurance Audit tab — evaluates insurance coverage gaps across household.
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
  Collapse,
  Heading,
  HStack,
  List,
  ListIcon,
  ListItem,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  Text,
  UnorderedList,
  VStack,
  useDisclosure,
  Button,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import api from "../services/api";
import { useCurrency } from "../contexts/CurrencyContext";

interface InsuranceCoverageItem {
  insurance_type: string;
  display_name: string;
  description: string;
  recommended_coverage: string;
  existing_accounts: Array<{ name: string; balance: number }>;
  has_coverage: boolean;
  priority: string;
  tips: string[];
}

interface InsuranceAuditResponse {
  coverage_items: InsuranceCoverageItem[];
  critical_gaps: number;
  coverage_score: number;
  net_worth: number;
}

const priorityColorScheme = (priority: string): string => {
  switch (priority) {
    case "critical": return "red";
    case "important": return "orange";
    case "optional": return "gray";
    default: return "gray";
  }
};

const scoreColor = (score: number): string => {
  if (score >= 75) return "green.500";
  if (score >= 50) return "yellow.500";
  return "red.500";
};

interface InsuranceCardProps {
  item: InsuranceCoverageItem;
}

const InsuranceCard = ({ item }: InsuranceCardProps) => {
  const { isOpen, onToggle } = useDisclosure();
  const { formatCurrency } = useCurrency();

  return (
    <Card>
      <CardHeader py={3} px={4}>
        <HStack justify="space-between" flexWrap="wrap" gap={2}>
          <HStack spacing={2}>
            <Text fontSize="lg">{item.has_coverage ? "✓" : "✗"}</Text>
            <Heading size="sm">{item.display_name}</Heading>
            <Badge colorScheme={priorityColorScheme(item.priority)} fontSize="xs">
              {item.priority}
            </Badge>
          </HStack>
          <Badge colorScheme={item.has_coverage ? "green" : "red"} fontSize="sm">
            {item.has_coverage ? "Covered" : "Not Covered"}
          </Badge>
        </HStack>
      </CardHeader>
      <CardBody pt={0} px={4} pb={4}>
        <VStack align="stretch" spacing={3}>
          <Text fontSize="sm" color="text.secondary">{item.description}</Text>
          <Text fontSize="sm">
            <strong>Recommended:</strong> {item.recommended_coverage}
          </Text>

          {item.existing_accounts.length > 0 && (
            <Box>
              <Text fontSize="xs" fontWeight="bold" mb={1} color="text.secondary">Existing Accounts</Text>
              <VStack align="stretch" spacing={1}>
                {item.existing_accounts.map((acct, idx) => (
                  <HStack key={idx} justify="space-between">
                    <Text fontSize="sm">{acct.name}</Text>
                    <Text fontSize="sm" fontWeight="medium">{formatCurrency(acct.balance)}</Text>
                  </HStack>
                ))}
              </VStack>
            </Box>
          )}

          {item.tips.length > 0 && (
            <Box>
              <Button size="xs" variant="ghost" onClick={onToggle} px={0}>
                {isOpen ? "Hide tips ▲" : `Show tips (${item.tips.length}) ▼`}
              </Button>
              <Collapse in={isOpen}>
                <UnorderedList mt={2} spacing={1} pl={2}>
                  {item.tips.map((tip, idx) => (
                    <ListItem key={idx} fontSize="sm">{tip}</ListItem>
                  ))}
                </UnorderedList>
              </Collapse>
            </Box>
          )}
        </VStack>
      </CardBody>
    </Card>
  );
};

export const InsuranceAuditTab = () => {
  const { formatCurrency } = useCurrency();

  const { data, isLoading, error } = useQuery<InsuranceAuditResponse>({
    queryKey: ["insurance-audit"],
    queryFn: () => api.get("/api/v1/estate/insurance-audit").then((r) => r.data),
  });

  return (
    <VStack spacing={6} align="stretch">
      {isLoading && <Text color="text.secondary">Loading insurance audit…</Text>}
      {error && (
        <Alert status="error">
          <AlertIcon />
          Failed to load insurance audit.
        </Alert>
      )}

      {data && (
        <>
          {/* Header stats */}
          <SimpleGrid columns={{ base: 2, md: 3 }} spacing={4}>
            <Stat>
              <StatLabel fontSize="xs">Coverage Score</StatLabel>
              <StatNumber fontSize="2xl" color={scoreColor(data.coverage_score)}>
                {data.coverage_score}
              </StatNumber>
            </Stat>
            <Stat>
              <StatLabel fontSize="xs">Critical Gaps</StatLabel>
              <StatNumber fontSize="2xl">
                <Badge colorScheme={data.critical_gaps > 0 ? "red" : "green"} fontSize="xl" px={3} py={1}>
                  {data.critical_gaps}
                </Badge>
              </StatNumber>
            </Stat>
            <Stat>
              <StatLabel fontSize="xs">Net Worth Context</StatLabel>
              <StatNumber fontSize="lg">{formatCurrency(data.net_worth)}</StatNumber>
            </Stat>
          </SimpleGrid>

          {/* Coverage cards */}
          {data.coverage_items.map((item) => (
            <InsuranceCard key={item.insurance_type} item={item} />
          ))}
        </>
      )}
    </VStack>
  );
};
