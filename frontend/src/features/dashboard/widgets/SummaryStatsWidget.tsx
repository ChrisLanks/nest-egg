import { memo } from "react";
import {
  Badge,
  Card,
  CardBody,
  Divider,
  HStack,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  SimpleGrid,
  Text,
  Tooltip,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useUserView } from "../../../contexts/UserViewContext";
import { useCurrency } from "../../../contexts/CurrencyContext";
import api from "../../../services/api";

interface MemberSpending {
  member_id: string;
  member_name: string;
  spending: number;
}

const SummaryStatsWidgetBase: React.FC = () => {
  const { selectedUserId, effectiveUserId } = useUserView();
  const { formatCurrency } = useCurrency();

  const { data } = useQuery({
    queryKey: ["dashboard", effectiveUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: effectiveUserId } : {};
      const response = await api.get("/dashboard/", { params });
      return response.data;
    },
    staleTime: 60_000,
  });

  // Per-member spending from the summary endpoint (combined household view only)
  const { data: summaryData } = useQuery({
    queryKey: ["dashboard-summary", effectiveUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: effectiveUserId } : {};
      const response = await api.get("/dashboard/summary", { params });
      return response.data;
    },
    enabled: !selectedUserId, // only fetch in combined household view
    staleTime: 300_000,
  });

  const summary = data?.summary;
  const netWorth = summary?.net_worth ?? 0;
  const monthlyNet = summary?.monthly_net ?? 0;
  const spendingByMember: MemberSpending[] = summaryData?.spending_by_member ?? [];

  return (
    <>
      <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6} mb={6}>
        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Net Worth</StatLabel>
              <StatNumber
                color={netWorth >= 0 ? "finance.positive" : "finance.negative"}
              >
                {formatCurrency(netWorth)}
              </StatNumber>
              <StatHelpText>Assets - Debts</StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Total Assets</StatLabel>
              <StatNumber>
                {formatCurrency(summary?.total_assets ?? 0)}
              </StatNumber>
              <StatHelpText>Checking, Savings, Investments</StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Total Debts</StatLabel>
              <StatNumber color="finance.negative">
                {formatCurrency(summary?.total_debts ?? 0)}
              </StatNumber>
              <StatHelpText>Credit Cards, Loans</StatHelpText>
            </Stat>
          </CardBody>
        </Card>
      </SimpleGrid>

      <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Monthly Income</StatLabel>
              <StatNumber color="finance.positive">
                {formatCurrency(summary?.monthly_income ?? 0)}
              </StatNumber>
              <StatHelpText>This month</StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Monthly Spending</StatLabel>
              <StatNumber color="finance.negative">
                {formatCurrency(summary?.monthly_spending ?? 0)}
              </StatNumber>
              <StatHelpText>
                Net:{" "}
                <Text
                  as="span"
                  color={
                    monthlyNet >= 0 ? "finance.positive" : "finance.negative"
                  }
                  fontWeight="bold"
                >
                  {formatCurrency(monthlyNet)}
                </Text>
              </StatHelpText>
            </Stat>

            {/* Per-member spending breakdown — only shown in combined household view */}
            {spendingByMember.length > 1 && (
              <>
                <Divider my={3} />
                <VStack align="stretch" spacing={1}>
                  <Text fontSize="xs" color="text.muted" fontWeight="medium">
                    By member
                  </Text>
                  {spendingByMember.map((m) => (
                    <Tooltip
                      key={m.member_id}
                      label={`${m.member_name}: ${formatCurrency(m.spending)} spent this period`}
                    >
                      <HStack justify="space-between" cursor="default">
                        <Text fontSize="xs" color="text.secondary" noOfLines={1} maxW="120px">
                          {m.member_name}
                        </Text>
                        <Badge colorScheme="red" fontSize="xs">
                          {formatCurrency(m.spending)}
                        </Badge>
                      </HStack>
                    </Tooltip>
                  ))}
                </VStack>
              </>
            )}
          </CardBody>
        </Card>
      </SimpleGrid>
    </>
  );
};

export const SummaryStatsWidget = memo(SummaryStatsWidgetBase);
