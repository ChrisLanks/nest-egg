/**
 * Retirement healthcare cost projection widget.
 */

import {
  Box,
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
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { memo } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useUserView } from "../../../contexts/UserViewContext";
import api from "../../../services/api";

interface HealthcareCostBreakdown {
  age: number;
  total: number;
}

interface HealthcareCostData {
  pre_65_annual: number;
  medicare_annual: number;
  ltc_annual: number;
  total_lifetime: number;
  sample_ages: HealthcareCostBreakdown[];
}

const fmt = (n: number): string =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);

const HealthcareCostWidgetBase: React.FC = () => {
  const { selectedUserId, effectiveUserId } = useUserView();

  const { data, isLoading, isError } = useQuery<HealthcareCostData>({
    queryKey: ["healthcare-cost-widget", effectiveUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: effectiveUserId } : {};
      const res = await api.get("/retirement/healthcare-estimate", { params });
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
            Healthcare Costs
          </Heading>
          <Text color="text.muted" fontSize="sm">
            Unable to estimate healthcare costs. Add your birthdate in Settings
            for personalized projections.
          </Text>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Healthcare Costs</Heading>
          <Link
            as={RouterLink}
            to="/retirement"
            fontSize="sm"
            color="brand.500"
          >
            Plan retirement →
          </Link>
        </HStack>

        <Stat size="sm" mb={4}>
          <StatLabel>Est. Lifetime Total</StatLabel>
          <StatNumber fontSize="xl" color="finance.negative">
            {fmt(data.total_lifetime)}
          </StatNumber>
        </Stat>

        <SimpleGrid columns={3} spacing={3} mb={4}>
          <Stat size="sm">
            <StatLabel fontSize="xs">Pre-65 Annual</StatLabel>
            <StatNumber fontSize="md">{fmt(data.pre_65_annual)}</StatNumber>
          </Stat>
          <Stat size="sm">
            <StatLabel fontSize="xs">Medicare Annual</StatLabel>
            <StatNumber fontSize="md">{fmt(data.medicare_annual)}</StatNumber>
          </Stat>
          <Stat size="sm">
            <StatLabel fontSize="xs">Long-term Care</StatLabel>
            <StatNumber fontSize="md">{fmt(data.ltc_annual)}</StatNumber>
          </Stat>
        </SimpleGrid>

        {data.sample_ages.length > 0 && (
          <VStack align="stretch" spacing={1}>
            <Text fontSize="xs" fontWeight="semibold" color="text.secondary">
              Cost by Age
            </Text>
            <HStack justify="space-between">
              {data.sample_ages.slice(0, 4).map((s) => (
                <Box key={s.age} textAlign="center" flex={1}>
                  <Text fontSize="xs" color="text.muted">
                    Age {s.age}
                  </Text>
                  <Text fontSize="sm" fontWeight="medium">
                    {fmt(s.total)}
                  </Text>
                </Box>
              ))}
            </HStack>
          </VStack>
        )}
      </CardBody>
    </Card>
  );
};

export const HealthcareCostWidget = memo(HealthcareCostWidgetBase);
