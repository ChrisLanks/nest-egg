/**
 * MemberSettlementWidget — per-member expense balance card.
 *
 * Shows how much each household member has been assigned from split
 * transactions, and whether they owe or are owed relative to an equal share.
 * Only rendered when the household has more than one active member.
 */

import {
  Box,
  Button,
  Card,
  CardBody,
  Heading,
  HStack,
  Text,
  VStack,
  Badge,
  Divider,
  Tooltip,
  Select,
  useToast,
} from "@chakra-ui/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { memo, useState } from "react";
import { transactionSplitsApi } from "../../../api/transaction-splits";
import { useHouseholdMembers } from "../../../hooks/useHouseholdMembers";
import type { MemberBalance } from "../../../types/transaction-split";

// Amounts within this band are treated as "even" — avoids noise from floating-
// point rounding on small household splits. Mirrors SMART_INSIGHTS.SETTLEMENT_EVEN_BAND
// in backend/app/constants/financial.py.
const SETTLEMENT_EVEN_BAND = 0.005;

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Math.abs(n));

function sinceDate(period: string): string | undefined {
  const now = new Date();
  if (period === "30d") {
    now.setDate(now.getDate() - 30);
  } else if (period === "90d") {
    now.setDate(now.getDate() - 90);
  } else if (period === "ytd") {
    now.setMonth(0, 1);
  } else {
    return undefined; // all time
  }
  return now.toISOString().split("T")[0];
}

const MemberSettlementWidgetBase: React.FC = () => {
  const [period, setPeriod] = useState("30d");
  const [settlingId, setSettlingId] = useState<string | null>(null);
  const toast = useToast();
  const queryClient = useQueryClient();

  const { data: members = [] } = useHouseholdMembers();

  const { data: balances = [], isLoading } = useQuery<MemberBalance[]>({
    queryKey: ["member-balances", period],
    queryFn: () => transactionSplitsApi.getMemberBalances(sinceDate(period)),
    staleTime: 60_000,
  });

  const settleMutation = useMutation({
    mutationFn: ({ memberId }: { memberId: string }) =>
      transactionSplitsApi.settleMember(memberId, sinceDate(period)),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["member-balances"] });
      toast({
        title: "Settled",
        description: `${data.settled_count} split(s) marked as settled.`,
        status: "success",
        duration: 3000,
        isClosable: true,
      });
      setSettlingId(null);
    },
    onError: () => {
      toast({
        title: "Settlement failed",
        description: "Could not mark splits as settled. Please try again.",
        status: "error",
        duration: 4000,
        isClosable: true,
      });
      setSettlingId(null);
    },
  });

  const handleSettle = (memberId: string) => {
    setSettlingId(memberId);
    settleMutation.mutate({ memberId });
  };

  // Only show widget when household has multiple members
  if (!isLoading && members.length < 2) return null;

  return (
    <Card variant="outline" h="100%">
      <CardBody>
        <VStack align="stretch" spacing={4}>
          <HStack justify="space-between" align="center">
            <Heading size="sm">Member Settlement</Heading>
            <Select
              size="xs"
              maxW="110px"
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
            >
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
              <option value="ytd">Year to date</option>
              <option value="all">All time</option>
            </Select>
          </HStack>

          {balances.length === 0 && !isLoading && (
            <Text fontSize="sm" color="text.muted" textAlign="center" py={4}>
              No assigned splits yet. Use "Split Transaction" on any expense
              and assign portions to household members to track who paid what.
            </Text>
          )}

          {balances.length > 0 && (
            <VStack align="stretch" spacing={2} divider={<Divider />}>
              {balances.map((b) => {
                const owes = b.net_owed < -SETTLEMENT_EVEN_BAND;
                const owed = b.net_owed > SETTLEMENT_EVEN_BAND;
                const isSettling = settlingId === b.member_id;
                return (
                  <HStack key={b.member_id} justify="space-between" align="center">
                    <Box>
                      <Text fontWeight="medium" fontSize="sm">
                        {b.member_name}
                      </Text>
                      <Text fontSize="xs" color="text.muted">
                        Total assigned: {fmt(b.total_assigned)}
                      </Text>
                    </Box>
                    <HStack spacing={2}>
                      <Tooltip
                        label={
                          owes
                            ? `${b.member_name} paid ${fmt(Math.abs(b.net_owed))} less than equal share`
                            : owed
                            ? `${b.member_name} paid ${fmt(b.net_owed)} more than equal share`
                            : "Balanced"
                        }
                      >
                        <Badge
                          colorScheme={owes ? "red" : owed ? "green" : "gray"}
                          fontSize="sm"
                          px={2}
                          py={1}
                        >
                          {owes && `owes ${fmt(Math.abs(b.net_owed))}`}
                          {owed && `+${fmt(b.net_owed)}`}
                          {!owes && !owed && "even"}
                        </Badge>
                      </Tooltip>
                      {owes && (
                        <Tooltip label={`Mark ${b.member_name}'s balance as settled`}>
                          <Button
                            size="xs"
                            colorScheme="teal"
                            variant="outline"
                            isLoading={isSettling}
                            onClick={() => handleSettle(b.member_id)}
                          >
                            Settle
                          </Button>
                        </Tooltip>
                      )}
                    </HStack>
                  </HStack>
                );
              })}
            </VStack>
          )}
        </VStack>
      </CardBody>
    </Card>
  );
};

export const MemberSettlementWidget = memo(MemberSettlementWidgetBase);
