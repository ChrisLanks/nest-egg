/**
 * Social Security estimate widget.
 */

import {
  Card,
  CardBody,
  Heading,
  HStack,
  Link,
  SimpleGrid,
  Spinner,
  Stat,
  StatLabel,
  StatNumber,
  Text,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { Link as RouterLink } from "react-router-dom";
import { useUserView } from "../../../contexts/UserViewContext";
import api from "../../../services/api";

interface SocialSecurityData {
  estimated_pia: number;
  monthly_at_62: number;
  monthly_at_fra: number;
  monthly_at_70: number;
  fra_age: number;
  claiming_age: number;
  monthly_benefit: number;
}

const fmt = (n: number): string =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);

export const SocialSecurityWidget: React.FC = () => {
  const { selectedUserId } = useUserView();

  const { data, isLoading, isError } = useQuery<SocialSecurityData>({
    queryKey: ["social-security-widget", selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const res = await api.get("/retirement/social-security-estimate", {
        params,
      });
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
            Social Security
          </Heading>
          <Text color="text.muted" fontSize="sm">
            Add your birthdate and income in Settings to see Social Security
            estimates.
          </Text>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Social Security</Heading>
          <Link
            as={RouterLink}
            to="/retirement"
            fontSize="sm"
            color="brand.500"
          >
            Plan retirement →
          </Link>
        </HStack>

        <SimpleGrid columns={2} spacing={3}>
          <Stat size="sm">
            <StatLabel>At Age 62</StatLabel>
            <StatNumber fontSize="lg">{fmt(data.monthly_at_62)}/mo</StatNumber>
          </Stat>
          <Stat size="sm">
            <StatLabel>At FRA ({data.fra_age})</StatLabel>
            <StatNumber fontSize="lg">{fmt(data.monthly_at_fra)}/mo</StatNumber>
          </Stat>
          <Stat size="sm">
            <StatLabel>At Age 70</StatLabel>
            <StatNumber fontSize="lg" color="green.500">
              {fmt(data.monthly_at_70)}/mo
            </StatNumber>
          </Stat>
          <Stat size="sm">
            <StatLabel>Estimated PIA</StatLabel>
            <StatNumber fontSize="lg">{fmt(data.estimated_pia)}/mo</StatNumber>
          </Stat>
        </SimpleGrid>
      </CardBody>
    </Card>
  );
};
