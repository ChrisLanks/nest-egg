/**
 * Contribution Headroom Widget — shows remaining tax-advantaged contribution
 * room for the current tax year across all household members.
 */

import {
  Box,
  Card,
  CardBody,
  Heading,
  HStack,
  Link,
  Progress,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { memo } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useUserView } from "../../../contexts/UserViewContext";
import api from "../../../services/api";

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

interface ContributionHeadroomResponse {
  tax_year: number;
  members: MemberHeadroom[];
}

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);

const ContributionHeadroomWidgetBase: React.FC = () => {
  useUserView(); // consumed for context consistency; API returns all household members

  const { data, isLoading } = useQuery<ContributionHeadroomResponse>({
    queryKey: ["contribution-headroom-widget"],
    queryFn: async () => {
      const res = await api.get("/contribution-headroom");
      return res.data;
    },
    staleTime: 60 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <Card h="100%">
        <CardBody display="flex" alignItems="center" justifyContent="center">
          <Spinner />
        </CardBody>
      </Card>
    );
  }

  const members = data?.members ?? [];
  const noData =
    members.length === 0 ||
    members.every((m) => m.accounts.length === 0);

  const allMaxed =
    !noData &&
    members.every((m) => m.total_remaining_headroom === 0);

  const multiMember = members.length > 1;

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={1}>
          <Heading size="md">Contribution Room</Heading>
          <Link
            as={RouterLink}
            to="/preferences"
            fontSize="sm"
            color="brand.500"
          >
            → Preferences
          </Link>
        </HStack>

        {data?.tax_year && (
          <Text fontSize="xs" color="text.secondary" mb={4}>
            {data.tax_year} tax-advantaged accounts
          </Text>
        )}

        {noData ? (
          <Text color="text.muted" fontSize="sm">
            Add retirement or HSA accounts to track contribution limits.
          </Text>
        ) : allMaxed ? (
          <Text fontSize="md" color="green.500" fontWeight="semibold">
            Maxed out! 🎉
          </Text>
        ) : (
          <VStack align="stretch" spacing={4}>
            {members.map((member) => {
              const pctUsed =
                member.total_limit > 0
                  ? Math.min(
                      (member.total_contributed_ytd / member.total_limit) * 100,
                      100,
                    )
                  : 0;
              const headroomColor =
                member.total_remaining_headroom > 0 ? "green.500" : "gray.400";

              return (
                <Box key={member.user_id}>
                  {multiMember && (
                    <Text
                      fontSize="xs"
                      fontWeight="semibold"
                      color="text.secondary"
                      mb={1}
                    >
                      {member.name}
                    </Text>
                  )}
                  <Text fontSize="2xl" fontWeight="bold" color={headroomColor}>
                    {fmt(member.total_remaining_headroom)}
                  </Text>
                  <Text fontSize="xs" color="text.muted" mb={2}>
                    remaining
                  </Text>
                  <Progress
                    value={pctUsed}
                    size="sm"
                    colorScheme={member.total_remaining_headroom > 0 ? "green" : "gray"}
                    borderRadius="full"
                    mb={1}
                  />
                  <Text fontSize="xs" color="text.secondary">
                    {fmt(member.total_contributed_ytd)} contributed of{" "}
                    {fmt(member.total_limit)} limit
                  </Text>
                </Box>
              );
            })}
          </VStack>
        )}

        {!noData && (
          <Link
            as={RouterLink}
            to="/accounts"
            fontSize="sm"
            color="brand.500"
            display="block"
            mt={4}
          >
            View accounts →
          </Link>
        )}
      </CardBody>
    </Card>
  );
};

export const ContributionHeadroomWidget = memo(ContributionHeadroomWidgetBase);
