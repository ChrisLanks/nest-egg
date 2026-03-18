/**
 * Required Minimum Distributions planner widget.
 */

import { memo } from "react";
import {
  Badge,
  Box,
  Card,
  CardBody,
  Divider,
  Heading,
  HStack,
  Link,
  SimpleGrid,
  Spinner,
  Stat,
  StatLabel,
  StatNumber,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { Link as RouterLink } from "react-router-dom";
import { useUserView } from "../../../contexts/UserViewContext";
import api from "../../../services/api";

interface AccountRMD {
  account_id: string;
  account_name: string;
  account_type: string;
  account_balance: number;
  required_distribution: number;
  distribution_taken: number;
  remaining_required: number;
}

interface RMDData {
  user_age: number;
  requires_rmd: boolean;
  rmd_deadline: string | null;
  total_required_distribution: number;
  total_distribution_taken: number;
  total_remaining_required: number;
  accounts: AccountRMD[];
  penalty_if_missed: number | null;
}

const fmt = (n: number): string =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);

const RmdPlannerWidgetBase: React.FC = () => {
  const { selectedUserId } = useUserView();

  const { data, isLoading, isError } = useQuery<RMDData>({
    queryKey: ["rmd-widget", selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const res = await api.get("/holdings/rmd-summary", { params });
      return res.data;
    },
    retry: false,
    staleTime: 30 * 60 * 1000,
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

  if (isError || !data) {
    return (
      <Card h="100%">
        <CardBody>
          <Heading size="md" mb={4}>
            RMD Planner
          </Heading>
          <Text color="text.muted" fontSize="sm">
            Add your birthdate in Settings to see Required Minimum Distribution
            planning.
          </Text>
        </CardBody>
      </Card>
    );
  }

  if (!data.requires_rmd) {
    return (
      <Card h="100%">
        <CardBody>
          <Heading size="md" mb={4}>
            RMD Planner
          </Heading>
          <Text color="text.muted" fontSize="sm">
            RMDs not yet required (age {data.user_age}). Required starting at
            age 73.
          </Text>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <HStack spacing={2}>
            <Heading size="md">RMD Planner</Heading>
            {Number(data.total_remaining_required) > 0 && (
              <Badge colorScheme="orange" fontSize="xs">
                Action needed
              </Badge>
            )}
          </HStack>
          <Link
            as={RouterLink}
            to="/retirement"
            fontSize="sm"
            color="brand.500"
          >
            View details →
          </Link>
        </HStack>

        <SimpleGrid columns={2} spacing={3} mb={4}>
          <Stat size="sm">
            <StatLabel>Required</StatLabel>
            <StatNumber fontSize="lg">
              {fmt(Number(data.total_required_distribution))}
            </StatNumber>
          </Stat>
          <Stat size="sm">
            <StatLabel>Remaining</StatLabel>
            <StatNumber
              fontSize="lg"
              color={
                Number(data.total_remaining_required) > 0
                  ? "orange.500"
                  : "green.500"
              }
            >
              {fmt(Number(data.total_remaining_required))}
            </StatNumber>
          </Stat>
        </SimpleGrid>

        {data.rmd_deadline && (
          <Text fontSize="xs" color="text.muted" mb={3}>
            Deadline:{" "}
            {new Date(data.rmd_deadline).toLocaleDateString("en-US", {
              month: "long",
              day: "numeric",
              year: "numeric",
            })}
          </Text>
        )}

        {data.penalty_if_missed != null &&
          Number(data.total_remaining_required) > 0 && (
            <Text fontSize="xs" color="red.500" mb={3}>
              Penalty if missed: {fmt(Number(data.penalty_if_missed))}
            </Text>
          )}

        <VStack align="stretch" spacing={1}>
          {data.accounts.slice(0, 4).map((acct, idx) => (
            <Box key={acct.account_id}>
              <HStack justify="space-between" py={1}>
                <Text fontSize="sm" fontWeight="medium" noOfLines={1} flex={1}>
                  {acct.account_name}
                </Text>
                <Text
                  fontSize="sm"
                  color={
                    Number(acct.remaining_required) > 0
                      ? "orange.500"
                      : "green.500"
                  }
                  whiteSpace="nowrap"
                >
                  {fmt(Number(acct.remaining_required))} left
                </Text>
              </HStack>
              {idx < data.accounts.slice(0, 4).length - 1 && <Divider />}
            </Box>
          ))}
        </VStack>
      </CardBody>
    </Card>
  );
};

export const RmdPlannerWidget = memo(RmdPlannerWidgetBase);
