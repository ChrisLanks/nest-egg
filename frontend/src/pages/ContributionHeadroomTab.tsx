/**
 * Annual Contribution Headroom tab — shows remaining IRS contribution room
 * per tax-advantaged account for all household members.
 */

import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Card,
  CardBody,
  CardHeader,
  Heading,
  HStack,
  Progress,
  Select,
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
  Tr,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import api from "../services/api";
import { ACCOUNT_TYPE_LABELS } from "../constants/accountTypeGroups";
import { useUserView } from "../contexts/UserViewContext";

interface AccountHeadroom {
  account_id: string;
  account_name: string;
  account_type: string;
  limit: number;
  catch_up_limit: number;
  catch_up_eligible: boolean;
  contributed_ytd: number;
  remaining_headroom: number;
  pct_used: number;
}

interface MemberHeadroom {
  user_id: string;
  name: string;
  age: number | null;
  accounts: AccountHeadroom[];
  total_limit: number;
  total_contributed_ytd: number;
  total_remaining_headroom: number;
}

interface HeadroomResponse {
  tax_year: number;
  members: MemberHeadroom[];
}


const fmt = (v: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(v);

const progressColor = (pct: number) => {
  if (pct >= 90) return "red";
  if (pct >= 50) return "yellow";
  return "green";
};

export const ContributionHeadroomTab = () => {
  const { selectedUserId } = useUserView();
  const currentYear = new Date().getFullYear();
  const [taxYear, setTaxYear] = useState(currentYear);

  const { data, isLoading, error } = useQuery<HeadroomResponse>({
    queryKey: ["contribution-headroom", taxYear, selectedUserId],
    queryFn: () => {
      const params = new URLSearchParams({ tax_year: String(taxYear) });
      if (selectedUserId) params.set("user_id", selectedUserId);
      return api.get(`/tax/contribution-headroom?${params}`).then((r) => r.data);
    },
  });

  return (
    <VStack spacing={6} align="stretch">
      <HStack justify="space-between" flexWrap="wrap" gap={2}>
        <Text fontSize="sm" color="text.secondary">
          Track remaining IRS contribution room across all tax-advantaged accounts.
        </Text>
        <Select
          size="sm"
          width="auto"
          value={taxYear}
          onChange={(e) => setTaxYear(Number(e.target.value))}
        >
          <option value={currentYear}>{currentYear}</option>
          <option value={currentYear + 1}>{currentYear + 1}</option>
        </Select>
      </HStack>

      {isLoading && <Text color="text.secondary">Loading contribution data…</Text>}
      {error && (
        <Alert status="error">
          <AlertIcon />
          Failed to load contribution headroom.
        </Alert>
      )}

      {data && data.members.map((member) => (
        <Card key={member.user_id}>
          <CardHeader py={3} px={4}>
            <HStack justify="space-between">
              <Box>
                <Heading size="sm">{member.name}</Heading>
                {member.age && (
                  <Text fontSize="xs" color="text.secondary">Age {member.age}</Text>
                )}
              </Box>
              <SimpleGrid columns={3} spacing={4} textAlign="right">
                <Stat size="sm">
                  <StatLabel fontSize="xs">Annual Limit</StatLabel>
                  <StatNumber fontSize="md">{fmt(member.total_limit)}</StatNumber>
                </Stat>
                <Stat size="sm">
                  <StatLabel fontSize="xs">Contributed YTD</StatLabel>
                  <StatNumber fontSize="md">{fmt(member.total_contributed_ytd)}</StatNumber>
                </Stat>
                <Stat size="sm">
                  <StatLabel fontSize="xs">Remaining</StatLabel>
                  <StatNumber fontSize="md" color="green.500">
                    {fmt(member.total_remaining_headroom)}
                  </StatNumber>
                </Stat>
              </SimpleGrid>
            </HStack>
          </CardHeader>
          <CardBody pt={0}>
            <VStack align="stretch" spacing={3}>
              {member.accounts.length === 0 ? (
                <Text fontSize="sm" color="text.secondary">
                  No tax-advantaged accounts found for this member.
                </Text>
              ) : (
                member.accounts.map((acct) => (
                  <Box key={acct.account_id}>
                    <HStack justify="space-between" mb={1}>
                      <HStack spacing={2}>
                        <Text fontSize="sm" fontWeight="medium">
                          {ACCOUNT_TYPE_LABELS[acct.account_type] ?? acct.account_type}
                        </Text>
                        <Text fontSize="xs" color="text.secondary">{acct.account_name}</Text>
                        {acct.catch_up_eligible && (
                          <Badge colorScheme="purple" fontSize="xs">Catch-up eligible</Badge>
                        )}
                      </HStack>
                      <HStack spacing={2}>
                        <Text fontSize="xs" color="text.secondary">
                          {fmt(acct.contributed_ytd)} / {fmt(acct.catch_up_eligible ? acct.catch_up_limit : acct.limit)}
                        </Text>
                        <Badge
                          colorScheme={progressColor(acct.pct_used)}
                          fontSize="xs"
                        >
                          {acct.remaining_headroom > 0 ? `${fmt(acct.remaining_headroom)} left` : "Maxed"}
                        </Badge>
                      </HStack>
                    </HStack>
                    <Progress
                      value={acct.pct_used}
                      colorScheme={progressColor(acct.pct_used)}
                      size="sm"
                      borderRadius="full"
                    />
                  </Box>
                ))
              )}
            </VStack>
          </CardBody>
        </Card>
      ))}
    </VStack>
  );
};
