/**
 * Roth conversion analysis widget.
 */

import {
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

interface RothAccount {
  id: string;
  name: string;
  balance: number;
  type: string;
  tax_treatment: string | null;
}

interface RothAnalysisData {
  traditional_balance: number;
  projected_rmd_at_73: number | null;
  current_age: number | null;
  accounts: RothAccount[];
}

const fmt = (n: number): string =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);

export const RothConversionWidget: React.FC = () => {
  const { selectedUserId } = useUserView();

  const { data, isLoading, isError } = useQuery<RothAnalysisData>({
    queryKey: ["roth-analysis-widget", selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const res = await api.get("/holdings/roth-analysis", { params });
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

  if (isError || !data || data.traditional_balance === 0) {
    return (
      <Card h="100%">
        <CardBody>
          <Heading size="md" mb={4}>
            Roth Conversion
          </Heading>
          <Text color="text.muted" fontSize="sm">
            No traditional IRA/401k balances found. Add retirement accounts to
            see Roth conversion analysis.
          </Text>
        </CardBody>
      </Card>
    );
  }

  const traditionalAccounts = data.accounts.filter(
    (a) => a.tax_treatment === "pre_tax" || a.type.includes("traditional"),
  );

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Roth Conversion</Heading>
          <Link
            as={RouterLink}
            to="/retirement"
            fontSize="sm"
            color="brand.500"
          >
            Plan conversion →
          </Link>
        </HStack>

        <SimpleGrid columns={2} spacing={3} mb={4}>
          <Stat size="sm">
            <StatLabel>Traditional Balance</StatLabel>
            <StatNumber fontSize="lg">
              {fmt(data.traditional_balance)}
            </StatNumber>
          </Stat>
          {data.projected_rmd_at_73 != null && (
            <Stat size="sm">
              <StatLabel>Projected RMD at 73</StatLabel>
              <StatNumber fontSize="lg" color="orange.500">
                {fmt(data.projected_rmd_at_73)}
              </StatNumber>
            </Stat>
          )}
        </SimpleGrid>

        {data.current_age != null && (
          <Box
            p={2}
            borderRadius="md"
            bg="blue.50"
            _dark={{ bg: "blue.900" }}
            mb={3}
          >
            <Text fontSize="xs" color="blue.700" _dark={{ color: "blue.200" }}>
              {data.current_age < 59
                ? "Consider converting in low-income years before age 59½ to minimize lifetime taxes."
                : data.current_age < 73
                  ? "You're in the Roth conversion window — conversions now can reduce future RMDs."
                  : "RMDs have begun. Partial conversions can still reduce future required distributions."}
            </Text>
          </Box>
        )}

        {traditionalAccounts.length > 0 && (
          <VStack align="stretch" spacing={1}>
            <Text fontSize="xs" fontWeight="semibold" color="text.secondary">
              Traditional Accounts
            </Text>
            {traditionalAccounts.slice(0, 4).map((acct, idx) => (
              <Box key={acct.id}>
                <HStack justify="space-between" py={1}>
                  <Text
                    fontSize="sm"
                    fontWeight="medium"
                    noOfLines={1}
                    flex={1}
                  >
                    {acct.name}
                  </Text>
                  <Text fontSize="sm" whiteSpace="nowrap">
                    {fmt(acct.balance)}
                  </Text>
                </HStack>
                {idx < traditionalAccounts.slice(0, 4).length - 1 && (
                  <Divider />
                )}
              </Box>
            ))}
          </VStack>
        )}
      </CardBody>
    </Card>
  );
};
