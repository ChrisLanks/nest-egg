/**
 * Beneficiary Coverage Audit — shows which accounts lack beneficiary designations.
 * Rendered at the top of EstatePage.
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
  CircularProgress,
  CircularProgressLabel,
  Collapse,
  HStack,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  Text,
  useDisclosure,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { FiChevronDown, FiChevronUp } from "react-icons/fi";
import api from "../services/api";
import { useUserView } from "../contexts/UserViewContext";

interface AuditAccount {
  account_id: string;
  account_name: string;
  account_type: string;
  current_balance: number;
  issues: string[];
  severity: "ok" | "warning" | "critical";
  beneficiaries: { name: string; designation_type: string; percentage: number }[];
}

interface AuditResponse {
  summary: {
    total_accounts_audited: number;
    fully_covered: number;
    missing_primary: number;
    missing_contingent: number;
    percentage_issues: number;
    overall_score: number;
  };
  accounts: AuditAccount[];
}

const ISSUE_LABELS: Record<string, string> = {
  missing_primary: "Missing primary beneficiary",
  missing_contingent: "No contingent beneficiary",
  primary_pct_not_100: "Primary % does not total 100%",
  minor_no_trust: "Minor beneficiary — no trust",
};

const SEVERITY_COLOR: Record<string, string> = {
  critical: "red",
  warning: "orange",
  ok: "green",
};

const fmt = (v: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(v);

export const BeneficiaryAuditCard = () => {
  const { selectedUserId } = useUserView();
  const { isOpen, onToggle } = useDisclosure({ defaultIsOpen: true });

  const { data, isLoading } = useQuery<AuditResponse>({
    queryKey: ["beneficiary-audit", selectedUserId],
    queryFn: () => api.get("/api/v1/estate/beneficiary-audit").then((r) => r.data),
  });

  if (isLoading) return null;
  if (!data || data.summary.total_accounts_audited === 0) return null;

  const { summary, accounts } = data;
  const hasIssues = summary.missing_primary > 0 || summary.missing_contingent > 0 || summary.percentage_issues > 0;
  const scoreColor = summary.overall_score >= 80 ? "green" : summary.overall_score >= 50 ? "yellow" : "red";

  return (
    <Card mb={6} borderColor={hasIssues ? "orange.200" : "border.default"} borderWidth={1}>
      <CardHeader
        onClick={onToggle}
        cursor="pointer"
        py={3}
        px={4}
      >
        <HStack justify="space-between">
          <HStack spacing={3}>
            <CircularProgress value={summary.overall_score} color={`${scoreColor}.400`} size="40px" thickness="8px">
              <CircularProgressLabel fontSize="10px" fontWeight="bold">{summary.overall_score}%</CircularProgressLabel>
            </CircularProgress>
            <Box>
              <Text fontWeight="bold" fontSize="sm">Beneficiary Coverage Audit</Text>
              <Text fontSize="xs" color="text.secondary">
                {summary.fully_covered} of {summary.total_accounts_audited} accounts fully covered
              </Text>
            </Box>
          </HStack>
          <HStack spacing={2}>
            {summary.missing_primary > 0 && (
              <Badge colorScheme="red">{summary.missing_primary} missing primary</Badge>
            )}
            {summary.missing_contingent > 0 && (
              <Badge colorScheme="orange">{summary.missing_contingent} no contingent</Badge>
            )}
            {isOpen ? <FiChevronUp /> : <FiChevronDown />}
          </HStack>
        </HStack>
      </CardHeader>

      <Collapse in={isOpen}>
        <CardBody pt={0}>
          <VStack align="stretch" spacing={2}>
            {accounts.map((acct) => (
              <HStack
                key={acct.account_id}
                justify="space-between"
                p={3}
                borderRadius="md"
                bg={acct.severity === "ok" ? "green.50" : acct.severity === "critical" ? "red.50" : "orange.50"}
                _dark={{
                  bg: acct.severity === "ok" ? "green.900" : acct.severity === "critical" ? "red.900" : "orange.900",
                }}
                flexWrap="wrap"
                gap={2}
              >
                <Box flex={1} minW="140px">
                  <Text fontWeight="medium" fontSize="sm">{acct.account_name}</Text>
                  <Text fontSize="xs" color="text.secondary">{fmt(acct.current_balance)}</Text>
                </Box>
                <VStack align="flex-end" spacing={1}>
                  {acct.issues.length === 0 ? (
                    <Badge colorScheme="green" fontSize="xs">Covered</Badge>
                  ) : (
                    acct.issues.map((issue) => (
                      <Badge key={issue} colorScheme={SEVERITY_COLOR[acct.severity]} fontSize="xs">
                        {ISSUE_LABELS[issue] ?? issue}
                      </Badge>
                    ))
                  )}
                  {acct.beneficiaries.length > 0 && (
                    <Text fontSize="xs" color="text.secondary">
                      {acct.beneficiaries.map((b) => `${b.name} (${b.percentage}%)`).join(", ")}
                    </Text>
                  )}
                </VStack>
              </HStack>
            ))}
          </VStack>
        </CardBody>
      </Collapse>
    </Card>
  );
};
