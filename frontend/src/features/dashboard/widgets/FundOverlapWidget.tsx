/**
 * Fund overlap widget — shows holding concentration and redundancy.
 */

import {
  Badge,
  Box,
  Card,
  CardBody,
  Heading,
  HStack,
  Link,
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

interface OverlapGroup {
  category: string;
  holdings: string[];
  total_value: number;
  suggestion: string;
}

interface FundOverlapData {
  overlaps: OverlapGroup[];
  total_overlap_value: number;
}

const fmt = (n: number): string =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);

export const FundOverlapWidget: React.FC = () => {
  const { selectedUserId } = useUserView();

  const { data, isLoading, isError } = useQuery<FundOverlapData>({
    queryKey: ["fund-overlap-widget", selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const res = await api.get("/holdings/fund-overlap", { params });
      return res.data;
    },
    retry: false,
    staleTime: 10 * 60 * 1000,
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

  if (isError || !data || data.overlaps.length === 0) {
    return (
      <Card h="100%">
        <CardBody>
          <Heading size="md" mb={4}>
            Fund Overlap
          </Heading>
          <Text color="text.muted" fontSize="sm">
            No significant fund overlap detected in your portfolio.
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
            <Heading size="md">Fund Overlap</Heading>
            <Badge colorScheme="orange" fontSize="xs">
              {data.overlaps.length} group{data.overlaps.length > 1 ? "s" : ""}
            </Badge>
          </HStack>
          <Link as={RouterLink} to="/holdings" fontSize="sm" color="brand.500">
            View portfolio →
          </Link>
        </HStack>

        <Stat size="sm" mb={4}>
          <StatLabel>Total Overlap Value</StatLabel>
          <StatNumber fontSize="lg" color="orange.500">
            {fmt(data.total_overlap_value)}
          </StatNumber>
        </Stat>

        <VStack align="stretch" spacing={3}>
          {data.overlaps.slice(0, 4).map((group) => (
            <Box
              key={group.category}
              p={2}
              borderRadius="md"
              bg="orange.50"
              _dark={{ bg: "orange.900" }}
            >
              <HStack justify="space-between" mb={1}>
                <Text fontSize="sm" fontWeight="semibold">
                  {group.category}
                </Text>
                <Text fontSize="sm" fontWeight="medium">
                  {fmt(group.total_value)}
                </Text>
              </HStack>
              <Text fontSize="xs" color="text.muted" mb={1}>
                {group.holdings.join(", ")}
              </Text>
              <Text
                fontSize="xs"
                color="orange.600"
                _dark={{ color: "orange.300" }}
              >
                {group.suggestion}
              </Text>
            </Box>
          ))}
        </VStack>
      </CardBody>
    </Card>
  );
};
